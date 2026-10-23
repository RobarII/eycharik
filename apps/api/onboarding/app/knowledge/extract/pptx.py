"""PPTX: slides are already text, so a deck never needs recognition.

Company policies arrive as presentations, and their text lives in shapes. ``inspect`` reads every
text frame and table in visual order. ``rasterize`` returns the embedded pictures: a deck that is
nothing but screenshots of a document still reaches the recognizer, but a deck of text does not pay
for a rendering pipeline that this project does not have.
"""

from __future__ import annotations

import io

from pptx import Presentation
from pptx.shapes.base import BaseShape
from pptx.shapes.graphfrm import GraphicFrame
from pptx.shapes.picture import Picture
from pptx.slide import Slide

from onboarding.core.models import DocumentSniff

MEDIA_TYPES = frozenset(
    {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
    }
)
CELL_SEPARATOR = " | "


class PptxReader:
    engine = "python-pptx"

    def supports(self, media_type: str) -> bool:
        normalized = media_type.split(";", maxsplit=1)[0].strip().lower()
        if normalized in MEDIA_TYPES:
            return True
        # Browsers send an empty or generic type for a deck picked from disk.
        return normalized in {"", "application/octet-stream"}

    def inspect(self, content: bytes) -> DocumentSniff:
        try:
            presentation = Presentation(io.BytesIO(content))
        except Exception:  # noqa: BLE001 - any parse failure means "not a readable deck"
            return DocumentSniff(page_count=0)
        slides = tuple(_slide_text(slide) for slide in presentation.slides)
        return DocumentSniff(page_count=len(slides), pages=slides)

    def rasterize(self, content: bytes, *, dpi: int) -> tuple[bytes, ...]:
        del dpi  # embedded pictures keep their own resolution; upscaling adds no information
        try:
            presentation = Presentation(io.BytesIO(content))
        except Exception:  # noqa: BLE001
            return ()
        images: list[bytes] = []
        for slide in presentation.slides:
            for shape in _ordered(slide):
                if isinstance(shape, Picture):
                    images.append(bytes(shape.image.blob))
        return tuple(images)


def _ordered(slide: Slide) -> list[BaseShape]:
    """Shapes top-to-bottom, then left-to-right. A missing position sorts first."""
    return sorted(
        slide.shapes,
        key=lambda shape: (
            shape.top if shape.top is not None else 0,
            shape.left if shape.left is not None else 0,
        ),
    )


def _slide_text(slide: Slide) -> str:
    blocks: list[str] = []
    for shape in _ordered(slide):
        frame = getattr(shape, "text_frame", None)  # not every shape type owns one
        if frame is not None:
            text = frame.text.strip()
            if text:
                blocks.append(text)
        elif isinstance(shape, GraphicFrame) and shape.has_table:
            for row in shape.table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    blocks.append(CELL_SEPARATOR.join(cells))
    return "\n\n".join(blocks)
