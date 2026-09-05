"""Text extraction helpers for PDF and image lab reports.

Text-based PDFs work with PyMuPDF only. Scanned PDFs and image uploads use
Tesseract when available and can optionally fall back to EasyOCR.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
from io import BytesIO

SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
SUPPORTED_PDF_EXTS = {".pdf"}

_easyocr_reader = None


class OCRUnavailableError(RuntimeError):
    """Raised when an uploaded scan needs OCR but no OCR engine is ready."""


def ocr_capabilities() -> dict:
    """Return lightweight runtime capability information for the UI."""
    tesseract_binary = shutil.which("tesseract")
    return {
        "text_pdf": True,
        "tesseract": bool(tesseract_binary),
        "easyocr": importlib.util.find_spec("easyocr") is not None,
        "image_ocr": bool(tesseract_binary) or importlib.util.find_spec("easyocr") is not None,
    }


def _ocr_pil_image(image) -> str:
    """OCR a Pillow image using Tesseract first, then EasyOCR if installed."""
    if shutil.which("tesseract"):
        import pytesseract

        return pytesseract.image_to_string(image)

    if importlib.util.find_spec("easyocr") is not None:
        global _easyocr_reader
        import numpy as np
        import easyocr

        if _easyocr_reader is None:
            _easyocr_reader = easyocr.Reader(["en"], gpu=False)
        results = _easyocr_reader.readtext(np.array(image), detail=0)
        return "\n".join(results)

    raise OCRUnavailableError(
        "This file needs OCR, but no OCR engine is ready. Install Tesseract OCR "
        "and restart the app, or install the optional EasyOCR requirements."
    )


def extract_text_from_pdf(file_path: str) -> str:
    """Extract embedded PDF text; OCR pages automatically when it is a scan."""
    import fitz

    with fitz.open(file_path) as doc:
        embedded = "\n".join(page.get_text("text") for page in doc).strip()
        if len(embedded) >= 20:
            return embedded

        # Scanned/image-only PDF. Render at 2x resolution and OCR each page.
        from PIL import Image

        chunks = []
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.open(BytesIO(pix.tobytes("png"))).convert("RGB")
            chunks.append(_ocr_pil_image(image))
        return "\n".join(chunks).strip()


def extract_text_from_image(file_path: str) -> str:
    from PIL import Image

    with Image.open(file_path) as image:
        return _ocr_pil_image(image.convert("RGB")).strip()


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SUPPORTED_PDF_EXTS:
        return extract_text_from_pdf(file_path)
    if ext in SUPPORTED_IMAGE_EXTS:
        return extract_text_from_image(file_path)
    raise ValueError(f"Unsupported file type: {ext}")
