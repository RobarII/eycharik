"""Turning uploaded files into corpus text.

Three responsibilities, three modules:

* a **reader** knows one container format (``pdf.py``, ``pptx.py``) and never recognizes anything;
* a **recognizer** turns pixels into text (``ocr.py``) and never decides what to keep;
* the **router** (``router.py``) joins them and applies the pure decisions from
  ``onboarding.core.extraction``.

The quality gate (``quality.py``) measures the raster, because that is the artifact a recognizer
actually consumes. Nothing here writes to the database, and nothing here is imported by ``core/``.
"""
