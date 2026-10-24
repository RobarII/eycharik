"""Run the OCR golden set: does the pipeline read a page, and does it refuse a bad one?

The cases are rendered from known text, so the reference is exact and no binary is committed. That
makes this a floor for the engine — a clean render is not a photograph of a printout, and a pass
here does not mean field accuracy on real scans. It does prove three things: the recognizer is wired
to the right language route, typography survives normalization, and acceptance still refuses a
document too short to answer from.

The quality gate is not exercised here: its thresholds ship unset on purpose, because a glare score
is dishonest (white paper is "100% glare") and a blur proxy depends on resolution and ink coverage.
Calibrate one with a measurement before turning it on; the gate then changes the profile's
fingerprint and invalidates the cache by itself.

Usage:

    make eval-ocr                       # table, exit 1 on a gate failure
    make eval-ocr ARGS="--write"        # also write docs/measurements/<date>-eval-ocr.md
"""

from __future__ import annotations

import argparse
import io
import json
import platform
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

from onboarding.app.knowledge.extract.ocr import build_ocr
from onboarding.app.knowledge.extract.profiles import ExtractionProfileLibrary
from onboarding.app.knowledge.extract.quality import ImageUnreadableError, measure_image
from onboarding.core.extraction import accept, assemble, assess, normalize
from onboarding.core.models import (
    Accepted,
    ExtractionRoute,
    Rejected,
    RejectionReason,
)
from onboarding.evals.artifact import commit_hash
from onboarding.ports import ExtractionProfile, ExtractionUnavailableError, Ocr

ROOT = Path(__file__).resolve().parents[4]
CASES = ROOT / "docs" / "evals" / "ocr.yaml"
PROFILES = ROOT / "apps" / "api" / "model-profiles" / "extract"
SCHEMA = ROOT / "docs" / "contracts" / "extraction-profile.schema.json"

PAGE = (1240, 1754)  # A4 at 150 dpi
MARGIN = 96
FONT_SIZE = 34
LINE_HEIGHT = 1.45


CER_GATE = 0.05
VERDICT_GATE = 1.0

_FONTS = (
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)


class OcrEvalError(RuntimeError):
    """The set cannot run: a bad case, a broken profile, or no font to render with."""


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    kind: str
    lang: str
    expect: str
    text: str
    reason: RejectionReason | None = None


@dataclass(frozen=True, slots=True)
class Outcome:
    case: Case
    accepted: bool
    reason: RejectionReason | None
    cer: float
    words: int
    word_errors: int
    confidence: float

    @property
    def verdict_correct(self) -> bool:
        if self.case.expect == "accepted":
            return self.accepted
        return not self.accepted and self.reason is self.case.reason


@dataclass(frozen=True, slots=True)
class Report:
    engine: str
    profile: str
    outcomes: tuple[Outcome, ...]
    thresholds: dict[str, float]

    @property
    def character_error_rate(self) -> float:
        scored = [item for item in self.outcomes if item.case.expect == "accepted"]
        return sum(item.cer for item in scored) / len(scored) if scored else 0.0

    @property
    def verdict_correctness(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(1 for item in self.outcomes if item.verdict_correct) / len(self.outcomes)

    @property
    def failures(self) -> tuple[str, ...]:
        failed: list[str] = []
        if self.character_error_rate > CER_GATE:
            failed.append("character_error_rate")
        if self.verdict_correctness < VERDICT_GATE:
            failed.append("verdict_correctness")
        return tuple(failed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="onboarding.evals.ocr")
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--profile", default="doc-scan")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "measurements")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--label", default="")
    parser.add_argument("--note", default="")
    args = parser.parse_args(argv)

    try:
        profile = _load_profile(args.profile)
        cases = tuple(item for item in load_cases(args.cases) if item.lang == profile.lang)
        if not cases:
            raise OcrEvalError(
                f"no cases for language {profile.lang!r} in {args.cases}; "
                f"the profile {profile.name} reads {profile.lang!r}"
            )
        report = _run(
            cases[: args.limit] if args.limit else cases,
            profile,
            build_ocr(profile.family),
            _font(),
        )
    except (OcrEvalError, ExtractionUnavailableError) as error:
        print(f"ocr eval cannot run: {error}", file=sys.stderr)
        return 2

    print(_table(report))
    if args.write:
        _write(report, args)
    return 1 if report.failures else 0


def load_cases(path: Path) -> tuple[Case, ...]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise OcrEvalError(f"{path}: expected a non-empty list of cases")
    cases: list[Case] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise OcrEvalError(f"{path}: every case must be a mapping")
        try:
            expect = str(entry["expect"])
            reason = RejectionReason(entry["reason"]) if entry.get("reason") else None
            case = Case(
                id=str(entry["id"]),
                kind=str(entry["kind"]),
                lang=str(entry.get("lang", "ru")),
                expect=expect,
                text=str(entry["text"]),
                reason=reason,
            )
        except (KeyError, ValueError) as error:
            raise OcrEvalError(f"{path}: case {entry.get('id')!r}: {error}") from None
        if expect not in {"accepted", "rejected"}:
            raise OcrEvalError(f"{path}: case {case.id}: expect must be accepted or rejected")
        if expect == "rejected" and reason is None:
            raise OcrEvalError(f"{path}: case {case.id}: a rejected case names its reason")
        cases.append(case)
    return tuple(cases)


def render(case: Case, font_path: Path) -> bytes:
    """Draw the reference text on a page. Same text, same font, same layout every run."""
    image = Image.new("RGB", PAGE, "white")
    font = ImageFont.truetype(str(font_path), FONT_SIZE)
    draw = ImageDraw.Draw(image)
    top = MARGIN
    for line in case.text.strip("\n").splitlines():
        for wrapped in _wrap(draw, line, font, PAGE[0] - 2 * MARGIN):
            draw.text((MARGIN, top), wrapped, fill="black", font=font)
            top += int(FONT_SIZE * LINE_HEIGHT)

    if case.kind != "clean":
        raise OcrEvalError(f"case {case.id}: unknown kind {case.kind!r}")

    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def _run(cases: Sequence[Case], profile: ExtractionProfile, ocr: Ocr, font_path: Path) -> Report:
    outcomes: list[Outcome] = []
    for case in cases:
        image = render(case, font_path)
        try:
            metrics = measure_image(image, dpi=profile.dpi)
        except ImageUnreadableError as error:  # pragma: no cover - rendering is deterministic
            raise OcrEvalError(f"case {case.id}: rendered page is unreadable: {error}") from None

        verdict = assess(metrics, profile.quality)
        if not verdict.ok:
            outcomes.append(_refused(case, verdict.reason, confidence=0.0))
            continue

        pages = ocr.recognize((image,), lang=profile.lang, model=profile.model)
        document = assemble(
            pages,
            engine=ocr.engine,
            content_hash="eval",
            route=ExtractionRoute.OCR,
            profile=profile.name,
        )
        outcome = accept(document, profile.acceptance)
        if isinstance(outcome, Rejected):
            outcomes.append(_refused(case, outcome.reason, confidence=0.0))
            continue

        assert isinstance(outcome, Accepted)
        reference = normalize(case.text)
        hypothesis = normalize(outcome.text)
        outcomes.append(
            Outcome(
                case=case,
                accepted=True,
                reason=None,
                cer=_distance(list(reference), list(hypothesis)) / max(len(reference), 1),
                words=len(reference.split()),
                word_errors=_distance(reference.split(), hypothesis.split()),
                confidence=outcome.min_confidence,
            )
        )
    return Report(
        engine=ocr.engine,
        profile=profile.name,
        outcomes=tuple(outcomes),
        thresholds={
            "min_confidence": profile.acceptance.min_confidence,
            "min_chars": float(profile.acceptance.min_chars),
        },
    )


def _refused(case: Case, reason: RejectionReason | None, *, confidence: float) -> Outcome:
    words = len(case.text.split())
    return Outcome(
        case=case,
        accepted=False,
        reason=reason,
        cer=1.0,
        words=words,
        word_errors=words,
        confidence=confidence,
    )


def _table(report: Report) -> str:
    lines = [f"{'метрика':<24}{'значение':>10}", "-" * 34]
    lines.append(f"{'character_error_rate':<24}{report.character_error_rate:>10.4f}")
    lines.append(f"{'verdict_correctness':<24}{report.verdict_correctness:>10.3f}")
    accepted = [item for item in report.outcomes if item.accepted]
    if accepted:
        mean = sum(item.confidence for item in accepted) / len(accepted)
        lines.append(f"{'mean_confidence':<24}{mean:>10.3f}")
    lines.append("")
    lines.append(f"{'кейс':<26}{'вердикт':>12}{'cer':>9}{'ошибок в словах':>17}")
    for item in report.outcomes:
        verdict = "принят" if item.accepted else (item.reason.value if item.reason else "отказ")
        errors = f"{item.word_errors}/{item.words}"
        lines.append(f"{item.case.id:<26}{verdict:>12}{item.cer:>9.4f}{errors:>13}")
    if report.failures:
        lines.append(f"{'ПРОВАЛЕНО':<24}{', '.join(report.failures)}")
    else:
        lines.append(f"{'итог':<24}{'ПРОЙДЕНО':>10}")
    return "\n".join(lines)


def _write(report: Report, args: argparse.Namespace) -> None:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    on_date = datetime.now(UTC).date()
    suffix = f"-{args.label}" if args.label else ""
    path = args.out_dir / f"{on_date.isoformat()}-eval-ocr{suffix}.md"
    command = " ".join(["python -m onboarding.evals.ocr", *sys.argv[1:]]).strip()
    note = args.note.strip() or (
        "кейсы отрисованы известным текстом системным шрифтом, поэтому это нижняя граница для "
        "распознавания: проверяются маршрут, языковой путь и приёмка, а не точность на фотографиях "
        "бумаги"
    )
    limits = (
        f"`min_confidence={report.thresholds['min_confidence']}`, "
        f"`min_chars={int(report.thresholds['min_chars'])}`"
    )
    directory = args.out_dir
    artifact = directory / f"{on_date.isoformat()}-eval-ocr{suffix}.jsonl"
    artifact.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": item.case.id,
                    "verdict": "accepted"
                    if item.accepted
                    else (item.reason.value if item.reason else "refused"),
                    "cer": round(item.cer, 4),
                    "word_errors": item.word_errors,
                    "words": item.words,
                    "confidence": round(item.confidence, 4),
                },
                ensure_ascii=False,
            )
            for item in report.outcomes
        )
        + "\n",
        encoding="utf-8",
    )
    path.write_text(
        f"""# Оценка {on_date.isoformat()} — {"провалена" if report.failures else "пройдена"}

- команда: `{command}`
- коммит: `{commit_hash()}`
- окружение: `{_platform()}`
- движок: `{report.engine}`
- профиль: `{report.profile}`
- пороги: {limits}
- артефакт: `{artifact.name}`
- кейсов: {len(report.outcomes)}
- заметка: {note}

| метрика | значение | гейт |
|---|---|---|
| `character_error_rate` | {report.character_error_rate:.4f} | <= {CER_GATE:.2f} |
| `verdict_correctness` | {report.verdict_correctness:.3f} | = {VERDICT_GATE:.2f} |
""",
        encoding="utf-8",
    )
    print(f"wrote {path}")


def _platform() -> str:
    return f"{platform.system()} {platform.machine()}, Python {platform.python_version()}"


def _font() -> Path:
    for candidate in _FONTS:
        path = Path(candidate)
        if path.is_file():
            return path
    raise OcrEvalError(
        "no system font to render the cases: install DejaVu Sans or run on a machine that has one"
    )


def _load_profile(name: str) -> ExtractionProfile:
    try:
        return ExtractionProfileLibrary(PROFILES, SCHEMA).load(name)
    except ValueError as error:
        raise OcrEvalError(str(error)) from None


def _wrap(
    draw: ImageDraw.ImageDraw, line: str, font: ImageFont.FreeTypeFont, width: int
) -> list[str]:
    if not line:
        return [""]
    words = line.split(" ")
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textlength(candidate, font=font) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _distance(left: Sequence[str], right: Sequence[str]) -> int:
    """Levenshtein distance over any sequence, two rows of memory. Characters or words."""
    if list(left) == list(right):
        return 0
    if not left:
        return len(right)
    previous = list(range(len(right) + 1))
    for row, item in enumerate(left, start=1):
        current = [row]
        for column, other in enumerate(right, start=1):
            current.append(
                min(
                    previous[column] + 1,
                    current[column - 1] + 1,
                    previous[column - 1] + (item != other),
                )
            )
        previous = current
    return previous[-1]


if __name__ == "__main__":
    sys.exit(main())
