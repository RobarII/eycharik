from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from onboarding.app.copy import load_copy
from onboarding.app.llm.gateway import LLMResponseError
from onboarding.app.prompts import PromptLibrary
from onboarding.app.settings import Settings
from onboarding.app.worker.answerer import PROMPT_NAME, PROMPT_VERSION, Answerer
from onboarding.core.models import ChunkId, EmployeeId, EscalationReason
from onboarding.ports import LLMUnavailableError

from .fakes import FakeKnowledgeBase, RecordingAudit, ScriptedLLM, profile, scored_chunk

ROOT = Path(__file__).resolve().parents[3]
PROMPTS = ROOT / "docs" / "prompts"
COPY = ROOT / "docs" / "product" / "copy.yaml"
ON_DATE = date(2026, 10, 23)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        prompts_dir=PROMPTS,
        copy_path=COPY,
        answer_min_confidence=0.45,
    )


def build(
    responses: list[str | Exception],
    chunks: tuple[object, ...] = (),
    audit: RecordingAudit | None = None,
) -> tuple[Answerer, ScriptedLLM, FakeKnowledgeBase, RecordingAudit]:
    llm = ScriptedLLM(responses=list(responses))
    kb = FakeKnowledgeBase(chunks=chunks)  # type: ignore[arg-type]
    recorder = audit or RecordingAudit()
    answerer = Answerer(
        knowledge=kb,
        llm=llm,
        prompts=PromptLibrary(PROMPTS),
        copy=load_copy(COPY),
        settings=settings(),
        audit=recorder,
    )
    return answerer, llm, kb, recorder


def answer_json(citation: str = "hr/leave-policy#0", confidence: float = 0.9) -> str:
    return json.dumps(
        {
            "answer": f"Отпуск — 28 дней [{citation}]",
            "citations": [citation],
            "confidence": confidence,
            "escalate": False,
            "reason": "answered",
        }
    )


async def test_answers_from_a_grounded_chunk() -> None:
    answerer, llm, kb, audit = build([answer_json()], (scored_chunk(),))

    outcome = await answerer.answer("Сколько дней отпуска?", profile(), ON_DATE)

    assert not outcome.escalated
    assert "28" in outcome.text
    assert outcome.citations == (ChunkId("hr/leave-policy#0"),)
    assert kb.queries[0].audience == ("all", "dept:it")
    prompt = llm.requests[0].messages[0].content
    assert 'id="hr/leave-policy#0"' in prompt
    assert "28 календарных дней" in prompt
    assert "Сколько дней отпуска?" in prompt
    assert "answer_completed" in audit.names()


async def test_no_retrieval_escalates_without_calling_the_model() -> None:
    answerer, llm, _, _ = build([answer_json()], ())

    outcome = await answerer.answer("Кто мой наставник?", profile(), ON_DATE)

    assert outcome.escalated
    assert outcome.reason == EscalationReason.NO_SOURCES.value
    assert llm.requests == []


async def test_citation_outside_the_retrieved_set_is_refused() -> None:
    answerer, _, _, audit = build([answer_json("hr/secret#9")], (scored_chunk(),))

    outcome = await answerer.answer("Сколько дней отпуска?", profile(), ON_DATE)

    assert outcome.escalated
    assert outcome.reason == EscalationReason.NO_SOURCES.value
    assert outcome.citations == ()
    assert "answer_completed" in audit.names()


async def test_low_confidence_escalates_with_its_own_reason() -> None:
    answerer, _, _, _ = build([answer_json(confidence=0.1)], (scored_chunk(),))

    outcome = await answerer.answer("Сколько дней отпуска?", profile(), ON_DATE)

    assert outcome.escalated
    assert outcome.reason == EscalationReason.LOW_CONFIDENCE.value


async def test_malformed_output_escalates() -> None:
    answerer, _, _, _ = build(["Извините, я не могу ответить"], (scored_chunk(),))

    outcome = await answerer.answer("Сколько дней отпуска?", profile(), ON_DATE)

    assert outcome.escalated
    assert outcome.reason == EscalationReason.NO_SOURCES.value


async def test_model_escalation_is_respected() -> None:
    payload = json.dumps(
        {
            "answer": "Передаю HR.",
            "citations": [],
            "confidence": 0.2,
            "escalate": True,
            "reason": "restricted",
        }
    )
    answerer, _, _, _ = build([payload], (scored_chunk(),))

    outcome = await answerer.answer("Какая у меня зарплата?", profile(), ON_DATE)

    assert outcome.escalated
    assert outcome.reason == EscalationReason.RESTRICTED.value


async def test_provider_outage_escalates_as_unavailable() -> None:
    answerer, _, _, _ = build([LLMUnavailableError("down")], (scored_chunk(),))

    outcome = await answerer.answer("Сколько дней отпуска?", profile(), ON_DATE)

    assert outcome.escalated
    assert outcome.reason == EscalationReason.UNAVAILABLE.value


async def test_malformed_provider_response_escalates_as_unavailable() -> None:
    answerer, _, _, _ = build([LLMResponseError("empty")], (scored_chunk(),))

    outcome = await answerer.answer("Сколько дней отпуска?", profile(), ON_DATE)

    assert outcome.escalated
    assert outcome.reason == EscalationReason.UNAVAILABLE.value


async def test_question_is_truncated() -> None:
    answerer, llm, kb, _ = build([answer_json()], (scored_chunk(),))

    await answerer.answer("а" * 5000, profile(), ON_DATE)

    assert len(kb.queries[0].text) == settings().max_question_chars
    assert len(llm.requests[0].messages[0].content) > 0


async def test_empty_question_escalates() -> None:
    answerer, llm, _, _ = build([answer_json()], (scored_chunk(),))

    outcome = await answerer.answer("   ", profile(), ON_DATE)

    assert outcome.escalated
    assert llm.requests == []


async def test_audience_follows_the_profile() -> None:
    answerer, _, kb, _ = build([answer_json()], (scored_chunk(),))
    hr_profile = profile(EmployeeId("hr-1"), department="HR", audience=("all", "hr_only"))

    await answerer.answer("отпуск", hr_profile, ON_DATE)

    assert kb.queries[0].audience == ("all", "hr_only")


@pytest.mark.parametrize("citation", ["hr/leave-policy#0"])
async def test_citation_is_kept_in_the_outcome(citation: str) -> None:
    answerer, _, _, _ = build([answer_json(citation)], (scored_chunk(citation),))

    outcome = await answerer.answer("отпуск", profile(), ON_DATE)

    assert outcome.citations == (ChunkId(citation),)


def test_the_answerer_uses_an_existing_prompt_version() -> None:
    prompt = PromptLibrary(PROMPTS).load(PROMPT_NAME, PROMPT_VERSION)

    assert prompt.version == PROMPT_VERSION
