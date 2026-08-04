"""
Moteur OCR pour TOP-JURIDIQUE.

Implémente un OCR réel pour les PDF scannés et les images, avec un
repli gracieux : si Tesseract (pytesseract) ou un convertisseur
PDF->image ne sont pas disponibles, le système retourne un message
explicite plutôt que d'échouer silencieusement.

Dépendances optionnelles :
- pytesseract + binaire Tesseract (avec pack langue 'fra')
- pdf2image + poppler OU PyMuPDF (conversion PDF -> images)

Le moteur localise automatiquement le binaire Tesseract et un dossier
tessdata contenant la langue française (même si installés hors du PATH,
par ex. dans AppData local).
"""

from __future__ import annotations

import io
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_MIN_AVG_CHARS = 80

# Chemins probables du binaire Tesseract sous Windows.
_TESSERACT_BINARIES = (
    "tesseract",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)

# Dossiers tessdata susceptibles de contenir le pack français.
def _tessdata_candidates() -> list[Path]:
    exe = _tesseract_binary()
    candidates: list[Path] = []
    env_td = os.environ.get("TESSDATA_PREFIX")
    if env_td:
        candidates.append(Path(env_td))
    if exe:
        exe_path = Path(exe)
        candidates.extend([exe_path.parent / "tessdata", exe_path.parent.parent / "tessdata"])
    candidates.extend(
        [
            Path(r"C:\Program Files\Tesseract-OCR\tessdata"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Tesseract-OCR" / "tessdata",
        ]
    )
    return candidates


def _tesseract_binary() -> str | None:
    """Retrouve le chemin du binaire Tesseract (PATH puis chemins connus)."""
    exe = shutil.which("tesseract")
    if exe:
        return exe
    for candidate in _TESSERACT_BINARIES:
        if Path(candidate).exists():
            return candidate
    return None


def _tessdata_dir() -> str | None:
    """Retrouve un dossier tessdata contenant le pack français."""
    for candidate in _tessdata_candidates():
        try:
            if candidate.is_dir() and (candidate / "fra.traineddata").exists():
                return str(candidate)
        except OSError:
            continue
    return None


def _tess_config() -> str:
    """Configure pytesseract (binaire + dossier tessdata) et renvoie la config."""
    exe = _tesseract_binary()
    if exe:
        try:
            import pytesseract

            pytesseract.pytesseract.tesseract_cmd = exe
        except ImportError:
            return ""
    tessdata = _tessdata_dir()
    if not tessdata:
        return ""
    tessdata_posix = tessdata.replace(os.sep, "/")
    os.environ["TESSDATA_PREFIX"] = tessdata
    return f"--tessdata-dir {tessdata_posix}"


def tesseract_available() -> bool:
    """Vrai si Tesseract est trouvé avec le pack français."""
    return bool(_tesseract_binary() and _tessdata_dir())


class OCREngine:
    """
    Moteur de reconnaissance optique de caractères (OCR).
    """

    def process_image(self, image_path: str) -> str:
        """
        Traite une image (fichier) et en extrait le texte (français).

        Returns:
            Texte extrait, ou message d'erreur explicite entre crochets.
        """
        try:
            with open(image_path, "rb") as fh:
                return self.process_image_bytes(fh.read())
        except Exception as exc:
            logger.exception("Erreur OCR image %s", image_path)
            return f"[Erreur OCR : {exc}]"

    def process_image_bytes(self, image_bytes: bytes) -> str:
        """
        Traite des octets d'image et en extrait le texte (français).

        Returns:
            Texte extrait, ou message d'erreur explicite entre crochets.
        """
        try:
            from PIL import Image
            import pytesseract

            img = Image.open(io.BytesIO(image_bytes))
            config = _tess_config()
            return pytesseract.image_to_string(img, lang="fra", config=config).strip()
        except ImportError:
            return "[OCR indisponible : installer pytesseract]"
        except Exception as exc:
            logger.exception("Erreur OCR image")
            return f"[Erreur OCR : {exc}]"

    def process_scanned_pdf(self, pdf_path: str) -> str:
        """
        Traite un PDF scanné : convertit chaque page en image puis applique l'OCR.

        Returns:
            Texte OCRisé assemblé, ou message d'erreur explicite entre crochets.
        """
        images = self._pdf_to_images(pdf_path)
        if not images:
            return (
                "[OCR indisponible : conversion PDF->image impossible. "
                "Installez pdf2image + poppler ou PyMuPDF, ou fournissez le PDF sous forme textuelle.]"
            )

        texts: list[str] = []
        for img in images:
            text = self._ocr_pil_image(img)
            if text and not text.startswith("["):
                texts.append(text)

        if not texts:
            return (
                "[OCR indisponible : Tesseract (langue 'fra') n'est pas installé "
                "ou n'a rien pu lire. Installez tesseract-ocr et son pack langue français.]"
            )
        return "\n\n".join(texts)

    def _pdf_to_images(self, pdf_path: str):
        """
        Convertit un PDF en liste d'images PIL.

        Essaie pdf2image (poppler) puis PyMuPDF (fitz) en secours.
        Returns:
            Liste d'images, ou None si aucune conversion n'est possible.
        """
        try:
            from pdf2image import convert_from_path

            return convert_from_path(pdf_path, dpi=200)
        except ImportError:
            pass
        except Exception:
            # poppler absent ou indisponible : on tente PyMuPDF en secours.
            logger.debug("pdf2image indisponible pour %s, bascule sur PyMuPDF", pdf_path)

        try:
            import fitz

            images: list = []
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    pix = page.get_pixmap(dpi=200)
                    images.append(pix.tobytes("png"))
            from PIL import Image

            return [Image.open(io.BytesIO(raw)) for raw in images]
        except ImportError:
            return None
        except Exception as exc:
            logger.exception("Conversion PyMuPDF impossible pour %s", pdf_path)
            return None

    def _ocr_pil_image(self, image) -> str:
        """Applique l'OCR sur une image PIL."""
        try:
            import pytesseract

            config = _tess_config()
            return pytesseract.image_to_string(image, lang="fra", config=config).strip()
        except ImportError:
            return "[pytesseract manquant]"
        except Exception as exc:
            logger.exception("Erreur OCR page")
            return f"[Erreur OCR : {exc}]"

    def is_scanned_pdf(self, pdf_path: str) -> bool:
        """
        Détermine si un PDF est scanné (peu de texte extractible par page).

        Returns:
            True si le PDF semble être un scan.
        """
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(pdf_path)
            pages = list(reader.pages or [])
            if not pages:
                return True
            total_chars = sum(len((p.extract_text() or "").strip()) for p in pages)
            avg = total_chars / max(len(pages), 1)
            return avg < _MIN_AVG_CHARS
        except Exception:
            return False
