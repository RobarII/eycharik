from __future__ import annotations

import json

import pytest

from onboarding.app.llm.output import AnswerFormatError, parse_answer, parse_json_object
from onboarding.core.models import ChunkId

VALID = """{
  "answer": "Отпуск — 28 дней [hr/leave-policy#0]",
  "citations": ["hr/leave-policy#0"],
  "confidence": 0.9,
  "escalate": false,
  "reason": "answered"
}"""


def test_parses_a_fenced_object() -> None:
    payload = parse_json_object('```json\n{"a": 1}\n```')

    assert payload == {"a": 1}


def test_repairs_a_trailing_comma() -> None:
    assert parse_json_object('{"a": 1,}') == {"a": 1}


def test_rejects_text_without_an_object() -> None:
    with pytest.raises(AnswerFormatError, match="no JSON object"):
        parse_json_object("Извините, не могу ответить")


def test_parses_a_valid_answer() -> None:
    draft = parse_answer(VALID)

    assert draft.answer.startswith("Отпуск")
    assert draft.citations == (ChunkId("hr/leave-policy#0"),)
    assert draft.confidence == pytest.approx(0.9)
    assert draft.escalate is False


def test_deduplicates_citations() -> None:
    payload = {
        "answer": "Отпуск — 28 дней",
        "citations": ["hr/leave-policy#0", "hr/leave-policy#0"],
        "confidence": 0.9,
        "escalate": False,
        "reason": "answered",
    }

    draft = parse_answer(json.dumps(payload))

    assert draft.citations == (ChunkId("hr/leave-policy#0"),)


def _payload(**overrides: object) -> str:
    base: dict[str, object] = {
        "answer": "x",
        "citations": [],
        "confidence": 0.5,
        "escalate": False,
        "reason": "answered",
    }
    return json.dumps({**base, **overrides})


@pytest.mark.parametrize(
    "payload",
    [
        _payload(answer=""),
        _payload(citations=["secret"]),
        _payload(confidence=1.5),
        _payload(escalate="no"),
        _payload(reason="guess"),
    ],
)
def test_rejects_contract_violations(payload: str) -> None:
    with pytest.raises(AnswerFormatError):
        parse_answer(payload)


def test_rejects_oversized_output() -> None:
    with pytest.raises(AnswerFormatError, match="long"):
        parse_json_object("{" + " " * 20_000 + "}")
