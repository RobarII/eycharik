"""Quality metrics for one raster, measured before an engine sees it.

A recognizer never confesses: a blurred page produces confident nonsense. The gate therefore runs on
the artifact the engine will consume, and a refusal is cheaper than an answer built on garbage.

The blur proxy is the mean absolute high-frequency detail: the difference between the raster and
itself after a one-pixel blur. Sharp glyph edges survive that difference, a defocused page does not,
and a blank page scores exactly zero. It is a proxy, not a calibrated blur score — the number
depends on resolution and ink coverage, so it may only be compared within one reader and one
profile. The profile therefore ships with the threshold unset until a measurement justifies one.

There is no glare score on purpose. "Share of saturated pixels" is ~0.96 on a perfect page of text,
because paper is white; it would refuse every document. Overexposure is caught where it is
measurable instead — by the recognizer's per-line confidence.
"""

from __future__ import annotations

import io

from PIL import Image, ImageChops, ImageFilter, ImageStat, UnidentifiedImageError

from onboarding.core.models import ImageMetrics


class ImageUnreadableError(ValueError):
    """The bytes are not an image any decoder understands."""


def measure_image(content: bytes, *, dpi: int | None = None) -> ImageMetrics:
    """One raster in, quality metrics out. Deterministic and side-effect free."""
    try:
        with Image.open(io.BytesIO(content)) as opened:
            gray = opened.convert("L")
            width, height = gray.size
            # The frame of the page is not content: crop it, or a blank scan scores as "sharp"
            # from its own border alone.
            inset = max(1, int(min(width, height) * 0.01))
            inner = gray.crop((inset, inset, width - inset, height - inset))
            detail = ImageChops.difference(inner, inner.filter(ImageFilter.GaussianBlur(1.0)))
            energy = ImageStat.Stat(detail).mean[0]
    except (UnidentifiedImageError, OSError) as error:
        raise ImageUnreadableError(str(error)) from None
    return ImageMetrics(
        dpi=dpi,
        edge_energy=round(float(energy), 3),
        width=width,
        height=height,
    )
