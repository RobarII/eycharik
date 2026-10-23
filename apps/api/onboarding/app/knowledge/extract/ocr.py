"""Recognizers: the only place a heavy optional dependency is allowed to exist.

Two implementations, one protocol. ``UnavailableOcr`` is not a stub — it is the honest answer of a
deployment that reads digital documents only: scans are refused with a reason a recruiter can act
on, instead of being guessed at.

The rapid engine runs PP-OCRv5 weights through ONNX Runtime. That is the same model family as
PaddleOCR, without the Paddle runtime: it installs on any CPU, including Apple Silicon, and it ships
its weights, so a test does not need the network. A different engine is one more class here and one
more value in the profile schema; nothing else changes (ADR 0014).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from onboarding.core.models import ExtractedPage, ExtractionRoute
from onboarding.ports import ExtractionUnavailableError

# Paddle's PP-OCRv5 recognition routes are script groups, not ISO codes: Russian weights live under
# "cyrillic". An unknown language fails loudly instead of silently using the wrong dictionary.
_CYRILLIC = frozenset({"ru", "uk", "be", "bg", "mk", "kk", "ky", "mn", "sr", "tg"})
_LATIN = frozenset(
    {
        "en",
        "de",
        "fr",
        "es",
        "it",
        "pt",
        "nl",
        "pl",
        "cs",
        "sk",
        "sv",
        "da",
        "fi",
        "nb",
        "tr",
        "ro",
        "hu",
        "lt",
        "lv",
        "et",
        "sl",
        "hr",
        "ca",
        "id",
        "vi",
    }
)
_EN = frozenset({"en"})


class UnavailableOcr:
    """No recognizer configured. Digital documents still work; scans are refused, never invented."""

    engine = "none"

    def recognize(
        self, images: Sequence[bytes], *, lang: str, model: str
    ) -> tuple[ExtractedPage, ...]:
        del images, lang, model
        raise ExtractionUnavailableError(
            "no recognizer is configured: choose an extraction profile with "
            "family=rapid and install the ocr extra"
        )


class RapidOcr:
    """Blocking ONNX inference. The caller runs it off the event loop, one document at a time."""

    engine = "rapidocr"

    def __init__(self) -> None:
        self._engines: dict[tuple[str, str], Any] = {}

    def recognize(
        self, images: Sequence[bytes], *, lang: str, model: str
    ) -> tuple[ExtractedPage, ...]:
        engine = self._engine(lang, model)
        pages: list[ExtractedPage] = []
        for index, image in enumerate(images):
            result = engine(image)
            texts = [str(text) for text in (result.txts or ()) if str(text).strip()]
            scores = [float(score) for score in (result.scores or ())]
            pages.append(
                ExtractedPage(
                    index=index,
                    text="\n".join(texts),
                    # The worst line decides the page: one unreadable row is a wrong contract.
                    confidence=min(scores) if scores else 0.0,
                    engine=self.engine,
                    route=ExtractionRoute.OCR,
                )
            )
        return tuple(pages)

    def _engine(self, lang: str, model: str) -> Any:
        key = (lang, model)
        if key not in self._engines:
            self._engines[key] = self._build(lang)
        return self._engines[key]

    def _build(self, lang: str) -> Any:
        try:
            # Deliberate local import: the ocr extra is optional and may be absent at runtime.
            from rapidocr import ModelType, OCRVersion, RapidOCR  # noqa: PLC0415
        except ImportError as error:
            raise ExtractionUnavailableError(
                "the ocr extra is not installed: uv sync --extra ocr"
            ) from error
        route = _route_for(lang)
        if route is None:
            raise ExtractionUnavailableError(
                f"no recognizer route for language {lang!r}; add it to extraction/ocr.py"
            )
        try:
            return RapidOCR(
                params={
                    "Rec.ocr_version": OCRVersion.PPOCRV5,
                    "Rec.lang_type": route,
                    "Rec.model_type": ModelType.MOBILE,
                }
            )
        except Exception as error:
            raise ExtractionUnavailableError(
                f"recognizer for {lang!r} failed to start: {error}"
            ) from error


def _route_for(lang: str) -> str | None:
    if lang in _EN:
        return "en"
    if lang in _CYRILLIC:
        return "cyrillic"
    if lang in _LATIN:
        return "latin"
    return None


def build_ocr(family: str) -> RapidOcr | UnavailableOcr:
    """The one place a profile family becomes a class. Everywhere else, family is data."""
    if family == "rapid":
        return RapidOcr()
    return UnavailableOcr()
