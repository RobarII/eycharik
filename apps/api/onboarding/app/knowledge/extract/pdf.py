"""PDF: read the text layer first, render pages only when recognition is genuinely needed.

A digital PDF is the common case for company regulations, and rendering it costs seconds per page.
``inspect`` is therefore cheap — it extracts the text layer and stops. ``rasterize`` is a separate
call that the router makes only after the pure route function has chosen OCR.
"""

from __future__ import annotations

import io

import pypdfium2 as pdfium
from pypdfium2 import PdfiumError

from onboarding.core.models import DocumentSniff

MEDIA_TYPES = frozenset({"application/pdf", "application/x-pdf"})
POINTS_PER_INCH = 72.0
PNG = "PNG"


class PdfReader:
    """One container format. Stateless, so several documents can share it."""

    engine = "pdfium"

    def supports(self, media_type: str) -> bool:
        return media_type.split(";", maxsplit=1)[0].strip().lower() in MEDIA_TYPES

    def inspect(self, content: bytes) -> DocumentSniff:
        try:
            document = pdfium.PdfDocument(content)
        except PdfiumError as error:
            return DocumentSniff(page_count=0, encrypted=_is_password_error(error))
        try:
            pages = tuple(_page_text(document, index) for index in range(len(document)))
        except PdfiumError:
            return DocumentSniff(page_count=0)
        finally:
            document.close()
        return DocumentSniff(page_count=len(pages), pages=pages)

    def rasterize(self, content: bytes, *, dpi: int) -> tuple[bytes, ...]:
        document = pdfium.PdfDocument(content)
        try:
            scale = dpi / POINTS_PER_INCH
            return tuple(_page_png(document, index, scale) for index in range(len(document)))
        finally:
            document.close()


def _page_text(document: pdfium.PdfDocument, index: int) -> str:
    return str(document[index].get_textpage().get_text_range())


def _page_png(document: pdfium.PdfDocument, index: int, scale: float) -> bytes:
    bitmap = document[index].render(scale=scale)
    buffer = io.BytesIO()
    bitmap.to_pil().save(buffer, format=PNG)
    return buffer.getvalue()


def _is_password_error(error: PdfiumError) -> bool:
    """pdfium reports an encrypted document as a password failure; nothing else means that."""
    return "password" in str(error).lower()
