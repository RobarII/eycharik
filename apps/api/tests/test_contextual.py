"""Contextual retrieval: what the index sees, what the citation quotes, what a failure does."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import pytest

from onboarding.app.knowledge.contextual import (
    ContextualizationError,
    LlmContextualizer,
    clean,
)
from onboarding.app.knowledge.embedding import HashingEmbedder
from onboarding.app.knowledge.pipeline import ingest
from onboarding.app.prompts import PromptLibrary
from onboarding.app.settings import REPO_ROOT
from onboarding.core.models import Chunk, ChunkId, DocId, Document
from onboarding.ports import Completion, CompletionRequest
from tests.fakes import RecordingKnowledgeWriter, ScriptedLLM

SCHEMA = REPO_ROOT / "docs" / "contracts" / "doc.schema.json"
PROMPTS = REPO_ROOT / "docs" / "prompts"
CONTEXT = "Отпуск без сохранения: оформление заявления."


def document() -> Document:
    return Document(
        id=DocId("hr/unpaid-leave"),
        title="Отпуск без сохранения заработной платы",
        text="Отпуск без сохранения заработной платы.\n\nЗаявление подаётся за три рабочих дня.",
        audience=("all",),
        valid_from=date(2026, 1, 1),
        owner="hr",
    )


def chunk(*, context: str = "") -> Chunk:
    return Chunk(
        id=ChunkId("hr/unpaid-leave#1"),
        doc_id=DocId("hr/unpaid-leave"),
        index=1,
        text="Заявление подаётся за три рабочих дня.",
        context=context,
    )


class RecordingContextualizer:
    def __init__(self, context: str = CONTEXT) -> None:
        self.context = context
        self.seen: list[tuple[str, int]] = []

    async def context_for(self, document: Document, chunk: Chunk) -> str:
        self.seen.append((str(document.id), chunk.index))
        return self.context


class RecordingEmbedder(HashingEmbedder):
    """A real embedder that remembers the texts it was asked to embed."""

    def __init__(self, dim: int = 8) -> None:
        super().__init__(dim=dim)
        self.seen: list[str] = []

    async def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        self.seen.extend(texts)
        return await super().embed(texts)


def test_a_chunk_without_context_embeds_its_own_text() -> None:
    assert chunk().embedding_text == chunk().text


def test_context_is_prepended_for_the_index_and_kept_out_of_the_text() -> None:
    contextual = chunk(context=CONTEXT)

    assert contextual.embedding_text == f"{CONTEXT}\n\n{contextual.text}"
    assert contextual.text == "Заявление подаётся за три рабочих дня."


async def test_ingest_embeds_the_context_and_stores_the_quote_separately() -> None:
    writer = RecordingKnowledgeWriter()
    embedder = RecordingEmbedder()
    contextualizer = RecordingContextualizer()

    report = await ingest(
        directory=REPO_ROOT / "knowledge",
        schema_path=SCHEMA,
        writer=writer,
        embedder=embedder,
        contextualizer=contextualizer,
    )

    assert report.contextualized == report.chunks > 0
    assert len(contextualizer.seen) == report.chunks
    assert all(CONTEXT in text for text in embedder.seen)
    stored = [piece for _, pieces in writer.documents for piece in pieces]
    assert all(piece.context == CONTEXT for piece in stored)
    assert all(CONTEXT not in piece.text for piece in stored)


async def test_ingest_without_a_contextualizer_leaves_the_column_empty() -> None:
    writer = RecordingKnowledgeWriter()
    embedder = RecordingEmbedder()

    report = await ingest(
        directory=REPO_ROOT / "knowledge",
        schema_path=SCHEMA,
        writer=writer,
        embedder=embedder,
    )

    assert report.contextualized == 0
    assert embedder.seen, "the embedder must still run"
    assert all(not piece.context for _, pieces in writer.documents for piece in pieces)


def test_the_prompt_renders_every_placeholder() -> None:
    prompt = PromptLibrary(PROMPTS).load("context", 1)

    assert prompt.max_tokens == 160
    for placeholder in ("{{title}}", "{{document_text}}", "{{chunk_text}}"):
        assert placeholder in prompt.template


async def test_the_contextualizer_sends_one_prompt_and_caps_the_answer() -> None:
    llm = ScriptedLLM(["  Контекст  " * 200])
    contextualizer = LlmContextualizer(
        llm=llm, prompts=PromptLibrary(PROMPTS), max_context_chars=120
    )

    context = await contextualizer.context_for(document(), chunk())

    assert len(context) == 120
    assert "\n" not in context
    request = llm.requests[0]
    assert isinstance(request, CompletionRequest)
    assert "Отпуск без сохранения заработной платы" in request.messages[0].content


async def test_a_provider_failure_stops_the_batch() -> None:
    llm = ScriptedLLM([RuntimeError("provider down")])
    contextualizer = LlmContextualizer(llm=llm, prompts=PromptLibrary(PROMPTS))

    with pytest.raises(ContextualizationError, match="hr/unpaid-leave#1"):
        await contextualizer.context_for(document(), chunk())


def test_an_empty_answer_is_a_failure_not_an_empty_prefix() -> None:
    with pytest.raises(ContextualizationError, match="empty context"):
        clean(Completion(text="   "), document=document(), chunk=chunk(), limit=100)
