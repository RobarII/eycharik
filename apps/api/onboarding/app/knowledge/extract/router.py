"""The composite adapter: bytes in, pages or a refusal out.

Everything that decides lives in ``onboarding.core.extraction``; this module only sequences effects.
Blocking work runs in a worker thread, so one large scan does not stall the job loop for other
employees.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable, Sequence

from onboarding.app.knowledge.extract.quality import ImageUnreadableError, measure_image
from onboarding.core.extraction import assemble, assess, refusal, refused, route
from onboarding.core.models import (
    DocumentSniff,
    ExtractedDocument,
    ExtractedPage,
    ExtractionRoute,
    ImageMetrics,
    RejectionReason,
)
from onboarding.ports import DocumentReader, DocumentRef, ExtractionProfile, Ocr

DEFAULT_MAX_PAGES = 200


class RoutingExtraction:
    """Reads a file with the cheapest reader that owns its format, and recognizes only if needed."""

    def __init__(
        self,
        *,
        readers: Sequence[DocumentReader],
        ocr: Ocr,
        max_pages: int = DEFAULT_MAX_PAGES,
        measure: Callable[..., ImageMetrics] = measure_image,
    ) -> None:
        self._readers = tuple(readers)
        self._ocr = ocr
        self._max_pages = max_pages
        self._measure = measure

    async def extract(
        self, content: bytes, ref: DocumentRef, profile: ExtractionProfile
    ) -> ExtractedDocument:
        return await asyncio.to_thread(self._extract, content, ref, profile)

    def _extract(
        self, content: bytes, ref: DocumentRef, profile: ExtractionProfile
    ) -> ExtractedDocument:
        content_hash = hashlib.sha256(content).hexdigest()
        reader = self._reader(ref.media_type)
        if reader is None:
            return refused(
                RejectionReason.UNSUPPORTED,
                engine="none",
                content_hash=content_hash,
                profile=profile.name,
                profile_hash=profile.fingerprint(),
            )

        sniff = reader.inspect(content)
        reason = refusal(sniff)
        if reason is not None:
            return self._refused(reason, reader, content_hash, profile)

        if route(sniff, min_text_chars=profile.min_text_chars) is ExtractionRoute.NATIVE_TEXT:
            pages = tuple(
                ExtractedPage(index=index, text=text, engine=reader.engine)
                for index, text in enumerate(sniff.pages)
            )
            return assemble(
                pages,
                engine=reader.engine,
                content_hash=content_hash,
                route=ExtractionRoute.NATIVE_TEXT,
                profile=profile.name,
                profile_hash=profile.fingerprint(),
            )

        return self._recognize(content, reader, sniff, content_hash, profile)

    def _recognize(
        self,
        content: bytes,
        reader: DocumentReader,
        sniff: DocumentSniff,
        content_hash: str,
        profile: ExtractionProfile,
    ) -> ExtractedDocument:
        del sniff  # pages are re-read as rasters; the text layer here is empty by definition
        images = reader.rasterize(content, dpi=profile.dpi)
        if not images:
            return self._refused(RejectionReason.NO_PAGES, reader, content_hash, profile)
        if len(images) > self._max_pages:
            return self._refused(RejectionReason.TOO_MANY_PAGES, reader, content_hash, profile)

        for image in images:
            try:
                verdict = assess(self._measure(image, dpi=profile.dpi), profile.quality)
            except ImageUnreadableError:
                return self._refused(RejectionReason.UNREADABLE, reader, content_hash, profile)
            if not verdict.ok:
                reason = verdict.reason or RejectionReason.UNREADABLE
                return self._refused(reason, reader, content_hash, profile)

        pages = self._ocr.recognize(images, lang=profile.lang, model=profile.model)
        return assemble(
            pages,
            engine=self._ocr.engine,
            content_hash=content_hash,
            route=ExtractionRoute.OCR,
            profile=profile.name,
            profile_hash=profile.fingerprint(),
        )

    def _reader(self, media_type: str) -> DocumentReader | None:
        for reader in self._readers:
            if reader.supports(media_type):
                return reader
        return None

    def _refused(
        self,
        reason: RejectionReason,
        reader: DocumentReader,
        content_hash: str,
        profile: ExtractionProfile,
    ) -> ExtractedDocument:
        return refused(
            reason,
            engine=reader.engine,
            content_hash=content_hash,
            profile=profile.name,
            profile_hash=profile.fingerprint(),
        )
