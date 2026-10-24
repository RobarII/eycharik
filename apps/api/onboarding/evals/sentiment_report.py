"""How a sentiment run becomes a reviewable file.

The summary is prose a reviewer reads; the artifact is one JSON line per case, and the header line
carries the commit. Both are rendered from the same ``Report`` object the run produced, so a file
cannot claim a metric the run lacks.

Rendering lives here rather than next to the run so the module that talks to providers stays about
providers. The imports under ``TYPE_CHECKING`` are annotations only: a report renderer needs the
report's shape, not the code that built it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from onboarding.app.settings import Settings
from onboarding.core.models import Sentiment
from onboarding.evals.artifact import commit_hash

if TYPE_CHECKING:
    from onboarding.evals.sentiment import Comparison, Report
    from onboarding.evals.sentiment_cases import Case


def render_markdown(
    report: Report,
    *,
    command: str,
    note: str,
    comparison: Comparison | None = None,
) -> str:
    cases = report.cases
    intervals = {
        "sentiment_accuracy": report.sentiment_accuracy_ci,
        "escalation_recall": report.escalation_recall_ci,
    }
    lines = [
        f"# Оценка риска — {report.provider}",
        "",
        f"- команда: `{command}`",
        f"- коммит: `{commit_hash()}`",
        f"- окружение: `{Settings().environment}`",
        f"- выборка: `{report.split}`",
        f"- модель: `{report.model or 'deterministic'}`",
        f"- рубрика: `{report.rubric or '—'}`",
        f"- кейсов: {len(cases)} ({_split_counts(cases)})",
        f"- повторов на кейс: {report.repeat}",
        f"- вызовов: {len(report.results)}",
        "",
        "## Качество",
        "",
        "| метрика | значение | 95% CI |",
        "|---|---|---|",
        f"| `sentiment_accuracy` | {report.sentiment_accuracy:.3f} | "
        f"{intervals['sentiment_accuracy'].render()} |",
        f"| `case_accuracy` | {report.case_accuracy:.3f} | majority over repetitions |",
        f"| `sentiment_macro_f1` | {report.macro_f1:.3f} | — |",
        f"| `tag_precision` | {report.tag_precision:.3f} | — |",
        f"| `tag_recall` | {report.tag_recall:.3f} | — |",
        f"| `tag_f1` | {report.tag_f1:.3f} | — |",
        f"| `escalation_recall` | {report.escalation_recall:.3f} | "
        f"{intervals['escalation_recall'].render()} |",
        f"| `false_alarm_rate` | {report.false_alarm_rate:.3f} | — |",
        f"| `fallback_rate` | {report.fallback_rate:.3f} | — |",
        f"| `format_error_rate` | {report.format_error_rate:.3f} | — |",
        "",
        "## Стоимость",
        "",
        "| метрика | значение |",
        "|---|---|",
        f"| `cost_rub_total` | {report.cost_rub:.4f} |",
        f"| `cost_rub_per_1k_calls` | {report.cost_per_1k_calls:.4f} |",
        f"| `input_tokens_total` | {report.input_tokens} |",
        f"| `output_tokens_total` | {report.output_tokens} |",
        f"| `cost_usd_total` | {report.cost_usd:.6f} |",
        f"| `cost_usd_per_1k_calls` | {report.cost_usd_per_1k_calls:.6f} |",
        f"| `priced_calls` | {report.priced_calls} / {len(report.results)} |",
        "",
        "## Задержка",
        "",
        "| метрика | значение |",
        "|---|---|",
        f"| `p50_latency_ms` | {report.p50_latency_ms:.1f} |",
        f"| `p95_latency_ms` | {report.p95_latency_ms:.1f} |",
        f"| `p99_latency_ms` | {report.p99_latency_ms:.1f} |",
        "",
        "## Полнота по тону",
        "",
        "| тон | полнота | кейсов с меткой |",
        "|---|---|---|",
    ]
    for sentiment, recall in report.per_class_recall.items():
        expected = sum(1 for result in report.results if result.case.sentiment is sentiment)
        lines.append(f"| `{sentiment.value}` | {recall:.3f} | {expected} |")
    lines += [
        "",
        "## Матрица ошибок",
        "",
        "Строки — метка, столбцы — предсказание.",
        "",
        "| метка \\ предсказание | " + " | ".join(item.value for item in Sentiment) + " |",
        "|---|" + "---|" * len(Sentiment),
    ]
    for label in Sentiment:
        row = [str(report.confusion.get((label, predicted), 0)) for predicted in Sentiment]
        lines.append(f"| `{label.value}` | " + " | ".join(row) + " |")
    lines += [
        "",
        "## Полнота по тегу",
        "",
        "| тег | полнота | кейсов с меткой |",
        "|---|---|---|",
    ]
    for tag, recall in report.per_tag_recall.items():
        expected = sum(1 for result in report.results if tag in result.case.tags)
        lines.append(f"| `{tag.value}` | {recall:.3f} | {expected} |")
    if note:
        lines += ["", f"Заметка: {note}"]
    if comparison is not None:
        lines += ["", "## Сравнение", "", _comparison_markdown(comparison)]
    if report.flaky_cases:
        lines += [
            "",
            "## Нестабильные кейсы",
            "",
            "Кейс, вердикт которого сменился между повторами. Гейт не может быть строже этого.",
            "",
            "| кейс | вердикты |",
            "|---|---|",
        ]
        for case_id in report.flaky_cases:
            seen = sorted(
                {
                    result.signal.sentiment.value
                    for result in report.results
                    if result.case.id == case_id
                }
            )
            lines.append(f"| `{case_id}` | {', '.join(seen)} |")
    if report.missed_escalations:
        lines += [
            "",
            "## Пропущенные эскалации",
            "",
            "Рекрутёра надо было предупредить, а его не предупредили. Этот список важнее",
            "любого среднего.",
            "",
            "| кейс | ожидаемый тон | предсказанный тон | теги |",
            "|---|---|---|---|",
        ]
        for result in report.missed_escalations:
            tags = ", ".join(tag.value for tag in result.signal.tags)
            lines.append(
                f"| `{result.case.id}` | {result.case.sentiment.value} | "
                f"{result.signal.sentiment.value} | {tags} |"
            )
    if report.failures:
        lines += [
            "",
            "## Ошибки разметки",
            "",
            "| кейс | ожидалось | получено | теги |",
            "|---|---|---|---|",
        ]
        for failure in report.failures:
            tags = ", ".join(tag.value for tag in failure.signal.tags)
            lines.append(
                f"| `{failure.case.id}` | {failure.case.sentiment.value} | "
                f"{failure.signal.sentiment.value} | {tags} |"
            )
    lines.append("")
    return "\n".join(lines)

def _comparison_markdown(comparison: Comparison) -> str:
    verdict = (
        "разница неотличима от шума"
        if comparison.interval.low <= 0.0 <= comparison.interval.high
        else ("кандидат лучше" if comparison.delta > 0 else "кандидат хуже")
    )
    return "\n".join(
        [
            f"- метрика: `{comparison.metric}`",
            f"- парных кейсов: {comparison.paired_cases}",
            f"- базовый: {comparison.baseline:.3f}",
            f"- кандидат: {comparison.candidate:.3f}",
            f"- дельта: {comparison.delta:+.3f} (95% бутстрэп-CI {comparison.interval.render()})",
            f"- p(дельта <= 0): {comparison.p_value:.3f}",
            f"- чтение: {verdict}",
        ]
    )

def _split_counts(cases: tuple[Case, ...]) -> str:
    dev = sum(1 for case in cases if case.split == "dev")
    test = len(cases) - dev
    return f"dev {dev}, test {test}"

def render_artifact(report: Report, *, command: str) -> str:
    header = {
        "kind": "run",
        "provider": report.provider,
        "split": report.split,
        "repeat": report.repeat,
        "commit": commit_hash(),
        "environment": Settings().environment,
        "prompt_version": report.prompt_version,
        "rubric": report.rubric or None,
        "model": report.model or None,
        "input_tokens": report.input_tokens,
        "output_tokens": report.output_tokens,
        "cost_rub": round(report.cost_rub, 6),
        "cost_usd": round(report.cost_usd, 9),
        "priced_calls": report.priced_calls,
        "command": command,
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "cases": len(report.cases),
        "fallbacks": report.fallbacks,
        "format_errors": report.format_errors,
        "fallback_reasons": [list(item) for item in report.fallback_reasons],
    }
    lines = [json.dumps(header, ensure_ascii=False)]
    for result in report.results:
        lines.append(
            json.dumps(
                {
                    "kind": "case",
                    "id": result.case.id,
                    "rep": result.rep,
                    "expected_sentiment": result.case.sentiment.value,
                    "predicted_sentiment": result.signal.sentiment.value,
                    "expected_tags": [tag.value for tag in result.case.tags],
                    "predicted_tags": [tag.value for tag in result.signal.tags],
                    "confidence": result.signal.confidence,
                    "expect_escalation": result.case.expect_escalation,
                    "escalated": result.level_escalates,
                    "latency_ms": round(result.latency_ms, 1),
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines) + "\n"
