"""Measure a sentiment classifier against the labeled survey answers.

The answer evals prove grounding; this one proves the risk radar. Three providers share the same
cases: the deterministic keyword classifier, the versioned chat prompt, and the Jev rubric. A
provider that is not configured is skipped with a clear message, never silently scored as zero.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from onboarding.app.clock import SystemClock
from onboarding.app.llm.gateway import build_llm
from onboarding.app.llm.jev import build_jev_classifier
from onboarding.app.llm.sentiment import SentimentClassifier
from onboarding.app.prompts import PromptLibrary
from onboarding.app.settings import Settings
from onboarding.core.models import RiskSignal, Sentiment, SignalTag
from onboarding.core.risk import keyword_signal
from onboarding.ports import AuditLog, SentimentAnalysis

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CASES = ROOT / "docs" / "evals" / "sentiment.yaml"
DEFAULT_OUT = ROOT / "docs" / "measurements"
PROVIDERS = ("keyword", "prompt", "jev")


class SentimentSetError(ValueError):
    """The labeled set does not satisfy the schema this runner reads."""


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    text: str
    sentiment: Sentiment
    tags: tuple[SignalTag, ...]


@dataclass(frozen=True, slots=True)
class CaseResult:
    case: Case
    signal: RiskSignal
    latency_ms: float

    @property
    def sentiment_ok(self) -> bool:
        return self.signal.sentiment is self.case.sentiment


@dataclass(frozen=True, slots=True)
class Report:
    provider: str
    results: tuple[CaseResult, ...]
    fallbacks: int
    format_errors: int

    @property
    def sentiment_accuracy(self) -> float:
        return _ratio(sum(result.sentiment_ok for result in self.results), len(self.results))

    @property
    def tag_precision(self) -> float:
        matched = sum(len(_tags(result)) for result in self.results)
        predicted = sum(len(result.signal.tags) for result in self.results)
        return _ratio(matched, predicted)

    @property
    def tag_recall(self) -> float:
        matched = sum(len(_tags(result)) for result in self.results)
        expected = sum(len(result.case.tags) for result in self.results)
        return _ratio(matched, expected)

    @property
    def p95_latency_ms(self) -> float:
        values = sorted(result.latency_ms for result in self.results)
        if not values:
            return 0.0
        index = min(len(values) - 1, math.ceil(0.95 * len(values)) - 1)
        return values[index]

    @property
    def fallback_rate(self) -> float:
        return _ratio(self.fallbacks, len(self.results))

    @property
    def failures(self) -> tuple[CaseResult, ...]:
        return tuple(
            result
            for result in self.results
            if not result.sentiment_ok or len(_tags(result)) < len(result.case.tags)
        )


def _tags(result: CaseResult) -> tuple[SignalTag, ...]:
    return tuple(tag for tag in result.case.tags if tag in result.signal.tags)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def load_cases(path: Path) -> tuple[Case, ...]:
    if not path.is_file():
        raise SentimentSetError(f"missing sentiment set {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise SentimentSetError(f"{path}: expected a cases list")
    cases: list[Case] = []
    seen: set[str] = set()
    for item in payload["cases"]:
        if not isinstance(item, dict):
            raise SentimentSetError(f"{path}: every case must be a mapping")
        case_id = item.get("id")
        text = item.get("text")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise SentimentSetError(f"{path}: id must be a unique non-empty string")
        if not isinstance(text, str) or not text.strip():
            raise SentimentSetError(f"{path}: {case_id}: text must be a non-empty string")
        try:
            sentiment = Sentiment(str(item.get("sentiment")))
        except ValueError:
            raise SentimentSetError(f"{path}: {case_id}: unknown sentiment") from None
        raw_tags = item.get("tags", [])
        if not isinstance(raw_tags, list):
            raise SentimentSetError(f"{path}: {case_id}: tags must be a list")
        tags: list[SignalTag] = []
        for raw in raw_tags:
            try:
                tags.append(SignalTag(str(raw)))
            except ValueError:
                raise SentimentSetError(f"{path}: {case_id}: unknown tag {raw!r}") from None
        seen.add(case_id)
        cases.append(Case(id=case_id, text=text, sentiment=sentiment, tags=tuple(tags)))
    if not cases:
        raise SentimentSetError(f"{path}: no cases")
    return tuple(cases)


class CountingAudit:
    """Count what the classifier did to itself, so a fallback is visible in the report."""

    def __init__(self) -> None:
        self.fallbacks = 0
        self.format_errors = 0

    async def record(self, name: str, **fields: Any) -> None:
        if name == "sentiment_fallback":
            self.fallbacks += 1
        if name == "sentiment_format_error":
            self.format_errors += 1


async def evaluate(
    cases: tuple[Case, ...],
    classifier: SentimentAnalysis,
    *,
    provider: str,
    audit: CountingAudit,
) -> Report:
    results: list[CaseResult] = []
    for case in cases:
        started = time.perf_counter()
        signal = await classifier.classify(case.text, source=case.id)
        elapsed = (time.perf_counter() - started) * 1000
        results.append(CaseResult(case=case, signal=signal, latency_ms=elapsed))
    return Report(
        provider=provider,
        results=tuple(results),
        fallbacks=audit.fallbacks,
        format_errors=audit.format_errors,
    )


def render_markdown(report: Report, *, command: str, note: str) -> str:
    results = report.results
    lines = [
        f"# Sentiment eval — {report.provider}",
        "",
        f"- command: `{command}`",
        f"- commit: `{_commit()}`",
        f"- environment: `{Settings().environment}`",
        f"- cases: {len(results)}",
        "",
        "| metric | value |",
        "|---|---|",
        f"| `sentiment_accuracy` | {report.sentiment_accuracy:.3f} |",
        f"| `tag_precision` | {report.tag_precision:.3f} |",
        f"| `tag_recall` | {report.tag_recall:.3f} |",
        f"| `fallback_rate` | {report.fallback_rate:.3f} |",
        f"| `p95_latency_ms` | {report.p95_latency_ms:.1f} |",
        "",
    ]
    if note:
        lines += [f"Note: {note}", ""]
    if report.failures:
        lines += ["| case | expected | got | tags |", "|---|---|---|---|"]
        for failure in report.failures:
            tags = ", ".join(tag.value for tag in failure.signal.tags)
            lines.append(
                f"| `{failure.case.id}` | {failure.case.sentiment.value} | "
                f"{failure.signal.sentiment.value} | {tags} |"
            )
        lines.append("")
    return "\n".join(lines)


def _commit() -> str:
    try:
        return subprocess.run(
            ["/usr/bin/env", "git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _classifier(
    provider: str, settings: Settings, http: httpx.AsyncClient, audit: AuditLog
) -> SentimentAnalysis:
    if provider == "prompt":
        if not settings.is_llm_configured:
            raise SentimentSetError("LLM_API_KEY is not set; the prompt provider cannot run")
        return SentimentClassifier(
            llm=build_llm(settings, SystemClock(), http),
            prompts=PromptLibrary(settings.prompts_dir),
            audit=audit,
        )
    if provider == "jev":
        if not settings.jev_api_key.get_secret_value():
            raise SentimentSetError("JEV_API_KEY is not set; the jev provider cannot run")
        return build_jev_classifier(
            client=http,
            endpoint=f"{settings.jev_base_url.rstrip('/')}/systemone",
            api_key=settings.jev_api_key,
            rubric_path=settings.prompts_dir / "sentiment-jev" / "v1.yaml",
            audit=audit,
            timeout_s=settings.jev_timeout_s,
            max_retries=settings.jev_max_retries,
        )

    class KeywordClassifier:
        async def classify(self, text: str, *, source: str) -> RiskSignal:
            return keyword_signal(text, source=source)

    return KeywordClassifier()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="onboarding.evals.sentiment")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--provider", choices=PROVIDERS, default="keyword")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--label", default="")
    parser.add_argument("--note", default="")
    args = parser.parse_args(argv)
    return asyncio.run(_run(args))


async def _run(args: argparse.Namespace) -> int:
    try:
        cases = load_cases(args.cases)
    except SentimentSetError as error:
        print(f"sentiment set error: {error}", file=sys.stderr)
        return 2
    settings = Settings()
    audit = CountingAudit()
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as http:
        try:
            classifier = _classifier(args.provider, settings, http, audit)
        except SentimentSetError as error:
            print(str(error), file=sys.stderr)
            return 2
        report = await evaluate(cases, classifier, provider=args.provider, audit=audit)
    if report.fallbacks or report.format_errors:
        print(
            f"warnings: {report.fallbacks} fallbacks, {report.format_errors} format errors",
            file=sys.stderr,
        )
    command = " ".join(
        ["python -m onboarding.evals.sentiment", f"--provider {args.provider}"]
        + (["--write"] if args.write else [])
        + ([f"--label {args.label}"] if args.label else [])
    )
    markdown = render_markdown(report, command=command, note=args.note)
    print(markdown)
    if args.write:
        suffix = f"-{args.label}" if args.label else ""
        path = args.out_dir / f"{datetime.now(UTC):%Y-%m-%d}-sentiment-{args.provider}{suffix}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown + "\n", encoding="utf-8")
        print(f"wrote {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
