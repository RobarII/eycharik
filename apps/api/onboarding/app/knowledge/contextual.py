"""Contextual retrieval: give every chunk back the sentence it lost.

The contextual-retrieval recipe applied to the ingest path: before a chunk is embedded, a small
model writes one or two sentences placing the chunk inside its document. A chunk that says
«Заявление подаётся не позднее чем за три рабочих дня» is weak on its own; with «Отпуск без
сохранения заработной платы: оформление заявления» in front of it, it competes with the sections
that named the topic.

Two rules make this safe:

- the generated context is prepended for embedding and lexical indexing only; ``Chunk.text`` stays
  the quotable source, so a citation can never start quoting a model;
- a failure aborts the batch instead of indexing half a corpus with context and half without. A
  mixed index is worse than no context at all.
"""

from __future__ import annotations

from dataclasses import dataclass

from onboarding.app.prompts import PromptLibrary
from onboarding.core.models import Chunk, Document
from onboarding.core.prompting import render
from onboarding.ports import LLM, Completion, CompletionRequest, Message

PROMPT_NAME = "context"
PROMPT_VERSION = 1
MAX_CONTEXT_CHARS = 400
DOCUMENT_CHAR_LIMIT = 6000


class ContextualizationError(RuntimeError):
    """The model did not produce a usable context for a chunk."""


@dataclass(frozen=True, slots=True)
class LlmContextualizer:
    """One completion per chunk, at ingest time only. Never in the request path."""

    llm: LLM
    prompts: PromptLibrary
    prompt_version: int = PROMPT_VERSION
    max_context_chars: int = MAX_CONTEXT_CHARS
    document_char_limit: int = DOCUMENT_CHAR_LIMIT

    async def context_for(self, document: Document, chunk: Chunk) -> str:
        prompt = self.prompts.load(PROMPT_NAME, self.prompt_version)
        body = render(
            prompt.template,
            {
                "title": document.title,
                "document_text": document.text[: self.document_char_limit],
                "chunk_text": chunk.text,
            },
        )
        try:
            completion = await self.llm.complete(
                CompletionRequest(
                    messages=(Message(role="user", content=body),),
                    temperature=prompt.temperature,
                    max_tokens=prompt.max_tokens,
                    prompt_name=PROMPT_NAME,
                    prompt_version=self.prompt_version,
                    response_format="text",
                )
            )
        except Exception as error:
            raise ContextualizationError(f"{document.id}#{chunk.index}: {error}") from error
        return clean(completion, document=document, chunk=chunk, limit=self.max_context_chars)


def clean(completion: Completion, *, document: Document, chunk: Chunk, limit: int) -> str:
    """One line, capped: a model that writes a paragraph must not shift the embedding."""
    text = " ".join(completion.text.split())
    if not text:
        raise ContextualizationError(f"{document.id}#{chunk.index}: empty context")
    return text[:limit]
