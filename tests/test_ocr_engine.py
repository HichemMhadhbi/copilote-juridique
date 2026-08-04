"""Tests du moteur OCR réel (Tesseract + pack fra).

Les tests sont ignorés automatiquement si Tesseract (avec la langue
française) n'est pas disponible sur la machine.
"""

import io

import pytest

from ingestion.ocr_engine import OCREngine, tesseract_available

pytestmark = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract (langue fra) indisponible",
)


def _make_image(text: str, height: int = 120) -> bytes:
    """Génère une image PNG contenant le texte demandé (font Arial Windows)."""
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 26)
    img = Image.new("RGB", (850, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 40), text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_ocr_image_francais():
    """L'OCR d'une image doit retrouver les mots-clefs du texte."""
    raw = _make_image("PACTE D'ASSOCIES - Capital social 50 000 euros")
    text = OCREngine().process_image_bytes(raw)
    assert "PACTE" in text.upper()
    assert "CAPITAL" in text.upper()
    assert "50 000" in text


def test_ocr_scanned_pdf():
    """Un PDF scanné (image embarquée) doit être OCRisé sans poppler."""
    import fitz
    import tempfile
    import os

    raw = _make_image("Cession de parts soumise a agreement")
    path = os.path.join(tempfile.gettempdir(), "scan_test.pdf")
    doc = fitz.open()
    page = doc.new_page(width=850, height=120)
    page.insert_image(page.rect, stream=raw)
    doc.save(path)
    doc.close()
    try:
        text = OCREngine().process_scanned_pdf(path)
    finally:
        os.unlink(path)
    assert "CESSION" in text.upper()
