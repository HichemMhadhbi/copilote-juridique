"""Service de gestion des documents - extraction de texte depuis PDF, Word, images."""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Any

from PyPDF2 import PdfReader


def extract_text_from_pdf(file_bytes: bytes, filename: str = "document.pdf") -> str:
    """Extrait le texte d'un PDF natif (avec repli OCR si le PDF est scanné)."""
    text, _status = _extract_text_from_pdf_with_status(file_bytes, filename)
    return text


def extract_text_from_pdf_with_status(
    file_bytes: bytes, filename: str = "document.pdf"
) -> tuple[str, str]:
    """Extrait le texte d'un PDF et renvoie (texte, statut de lecture).
    Statuts : 'natif', 'ocr', 'ocr_indisponible', 'erreur'."""
    return _extract_text_from_pdf_with_status(file_bytes, filename)


def _is_scanned_pdf(reader: PdfReader, min_chars: int = 80) -> bool:
    """Detecte si un PDF est scanne (tres peu de texte extractible par page)."""
    try:
        pages = list(reader.pages or [])
        if not pages:
            return True
        total_chars = sum(len((p.extract_text() or "").strip()) for p in pages)
        avg = total_chars / max(len(pages), 1)
        return avg < min_chars
    except Exception:
        return False


def _extract_text_from_pdf_with_status(
    file_bytes: bytes, filename: str = "document.pdf"
) -> tuple[str, str]:
    """Extrait le texte d'un PDF et renvoie (texte, statut).
    Statuts possibles : 'natif', 'ocr', 'ocr_indisponible', 'erreur'."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        text = _clean_pdf_text(text).strip()

        if _is_scanned_pdf(reader):
            ocr_text = _ocr_scanned_pdf(file_bytes, filename)
            if ocr_text and not ocr_text.startswith("[OCR"):
                return ocr_text, "ocr"
            return text, "ocr_indisponible"

        if not text:
            return "", "erreur"
        return text, "natif"
    except Exception as e:
        return f"[Erreur extraction PDF: {e}]", "erreur"


def _ocr_scanned_pdf(file_bytes: bytes, filename: str) -> str:
    """Applique un OCR reel sur un PDF scanne (repli gracieux si Tesseract absent)."""
    try:
        from ingestion.ocr_engine import OCREngine

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            return OCREngine().process_scanned_pdf(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception as e:
        return f"[OCR indisponible : {e}]"


def _clean_pdf_text(text: str) -> str:
    """Nettoie le texte extrait d'un PDF."""
    import re
    text = re.sub(r'\d{13}_\d{3}_\d{3}\.indd\s*\d+\s*', '', text)
    text = re.sub(r'_\d{3}_\d{3}\.indd\s*\d+\s*', '', text)
    text = re.sub(r'\.indd\s*\d+\s*', '', text)
    text = re.sub(r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}\s*', '', text)
    text = re.sub(r'978\d[\d\-]+', '', text)
    text = re.sub(r'978\d+', '', text)
    text = re.sub(r'\d{10,}', '', text)
    text = text.replace('\x97', ' ')
    text = text.replace('\x92', "'")
    text = text.replace('\x93', '"').replace('\x94', '"')
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(?i)(?<=\S)fiche\s*\d+\s*', '\n', text)
    text = re.sub(r'\.(\s)', r'.\n', text)
    return text.strip()

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extrait le texte d'un fichier Word."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return text.strip()
    except ImportError:
        return "[python-docx non installe]"
    except Exception as e:
        return f"[Erreur extraction Word: {e}]"


def extract_text_from_image(file_bytes: bytes) -> str:
    """Extrait le texte d'une image via OCR."""
    try:
        from ingestion.ocr_engine import OCREngine

        return OCREngine().process_image_bytes(file_bytes)
    except Exception as e:
        return f"[Erreur OCR: {e}]"


_SOCIETE_KEYWORDS = {
    "pacte d'associes": 3, "pacte d'associés": 3, "statuts": 2,
    "sarl": 3, "sas": 3, "societe anonyme": 3, "société anonyme": 3,
    "capital social": 3, "parts sociales": 3, "associes": 2, "associés": 2,
    "gerant": 2, "gérant": 2, "agrement": 3, "agrément": 3,
    "cession de parts": 3, "cession d'actions": 3, "preemption": 3, "préemption": 3,
    "non-concurrence": 3, "clause de sortie": 3, "tag-along": 3, "drag-along": 3,
    "droit de veto": 3, "droit de vote": 2, "votation": 2,
    "assemblee generale": 3, "assemblee generale": 3, "assemblée générale": 3,
    "conseil d'administration": 3, "apports en capital": 3, "actionnaire": 3,
    "immatriculation": 2, "forme juridique": 2, "gerant associe": 3,
    "objet social": 3, "denomination sociale": 3, "dénomination sociale": 3,
    "siege social": 3, "siège social": 3, "clause d'agrement": 3,
    "clause d'agrément": 3, "blocage": 2, "mediation": 1, "arbitrage": 1,
    # Procès-verbaux / décisions sociales
    "procès-verbal": 4, "proces-verbal": 4, "feuille de présence": 3,
    "feuille de presence": 3, "résolution": 3, "resolution": 3,
    "quorum": 3, "délibération": 3, "deliberation": 3, "décision des associés": 3,
    "decision des associés": 3, "décision collective": 3, "decision collective": 3,
    # Modifications statutaires
    "assemblée générale extraordinaire": 4, "assemblee generale extraordinaire": 4,
    "assemblée extraordinaire": 3, "assemblee extraordinaire": 3,
    "modification des statuts": 4, "modification du capital": 4,
    "dépôt au greffe": 3, "depot au greffe": 3, "inscription modificative": 3,
    "greffe du tribunal": 2, "mise à jour des statuts": 4, "mise a jour des statuts": 4,
    "nomination du président": 2, "transfert de siège": 3, "transfert du siège": 3,
}


def _score_societe(text: str) -> int:
    """Score de rattachement au droit des sociétés (associés, capital, gérance...)."""
    low = text.lower()
    score = 0
    for keyword, weight in _SOCIETE_KEYWORDS.items():
        score += weight * low.count(keyword)
    return score


def detect_document_type(text: str) -> str:
    """
    Detecte le type de document juridique.

    Types reconnus : 'pacte', 'statuts', 'proces_verbal',
    'modification_statutaire' ou 'autre'.

    Les documents de type 'autre' (cours, manuels, contrats hors societe...)
    ne doivent pas passer par les regles de controle specifiques aux pactes
    et statuts, sinon on obtient de faux positifs.
    """
    low = text.lower()
    if not text or not text.strip():
        return "autre"

    # 1) Signaux forts de modification statutaire (plus specifique qu'un PV)
    modification_marks = (
        low.count("modification des statuts") + low.count("modification du capital")
        + low.count("mise à jour des statuts") + low.count("mise a jour des statuts")
        + low.count("transfert de siège") + low.count("transfert du siège")
        + low.count("augmentation du capital") + low.count("augmentation de capital")
    )
    age = (
        "assemblée générale extraordinaire" in low
        or "assemblee generale extraordinaire" in low
        or "assemblée extraordinaire" in low or "assemblee extraordinaire" in low
        or "décision des associés" in low or "decision des associes" in low
        or "décision de l'associé unique" in low or "decision de l'associe unique" in low
    )
    depot_greffe = (
        "dépôt au greffe" in low or "depot au greffe" in low
        or "inscription modificative" in low or "greffe" in low
    )
    if (modification_marks >= 1 and age) or (
        modification_marks >= 1 and _score_societe(text) >= 8
    ) or (modification_marks >= 1 and depot_greffe):
        return "modification_statutaire"

    # 2) Signaux forts de procès-verbal / décision sociale
    pv_marks = low.count("procès-verbal") + low.count("proces-verbal")
    pv_signaux = (
        "résolution" in low or "resolution" in low
        or "feuille de présence" in low or "feuille de presence" in low
        or "quorum" in low
        or "majorité" in low or "majorite" in low
        or "séance" in low or "seance" in low
        or "quitus" in low
        or "assemblée" in low or "assemblee" in low
        or "vote" in low
        or "adoptée" in low or "adoptee" in low or "adopté" in low or "adopte" in low
    )
    pv_strong = pv_marks >= 1 and pv_signaux
    decision_collective = (
        ("décision des associés" in low or "decision des associés" in low
         or "decision des associes" in low
         or "décision collective" in low or "decision collective" in low)
        and pv_marks >= 1
    )
    if pv_strong or decision_collective:
        return "proces_verbal"

    # 3) Pacte d'associés
    pacte_marks = low.count("pacte")
    if pacte_marks and _score_societe(text) >= 4:
        return "pacte"

    # 4) Statuts
    if _score_societe(text) >= 4:
        return "statuts"

    return "autre"


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extrait le texte d'un fichier brut."""
    try:
        return file_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1").strip()


# ── Qualite de lecture des documents ────────────────────────────────────────

_PONCTUATION_FIN = set(".!?»\"'…")


def _detect_missing_page(text: str) -> bool:
    """Detecte une page manquante via les marqueurs de page (Page N, p. N)."""
    import re

    pages: list[int] = []
    for pat in (r"(?i)\bpage\s*(\d+)\b", r"(?i)\bp\.\s*(\d+)\b", r"(?i)\bp\s*(\d+)\b"):
        pages.extend(int(m) for m in re.findall(pat, text))
    uniq = sorted(set(pages))
    if len(uniq) < 2:
        return False
    return any(b - a > 1 for a, b in zip(uniq, uniq[1:]))


def _detect_incomplete(text: str, n_chars: int) -> bool:
    """Heuristiques de document incomplet (trop court / fin tronquee)."""
    low = text.lower()
    is_corporate = any(
        k in low
        for k in (
            "statuts",
            "pacte d'associés",
            "pacte d'associes",
            "capital social",
            "objet social",
        )
    )
    if is_corporate and n_chars < 600:
        return True
    last_char = text.rstrip()[-1:] if text.strip() else ""
    if 300 < n_chars < 1500 and last_char and last_char not in _PONCTUATION_FIN:
        return True
    return False


def assess_document_quality(text: str, status: str = "natif") -> dict:
    """
    Evalue la qualite de lecture d'un document.

    Retourne un dict avec les drapeaux : illisible, ocr_faible,
    page_manquante, incomplet, ainsi qu'un champ 'detail' lisible.
    """
    text = (text or "").strip()
    n_chars = len(text)
    alpha = sum(c.isalpha() for c in text)
    ratio = alpha / max(n_chars, 1) if n_chars else 0.0

    illisible = not text or text.startswith("[") or (n_chars < 120 and ratio < 0.5)
    ocr_faible = status in ("ocr", "ocr_indisponible") and (n_chars < 500 or ratio < 0.6)
    page_manquante = _detect_missing_page(text)
    incomplet = False if illisible else _detect_incomplete(text, n_chars)

    issues = []
    if illisible:
        issues.append("illisible")
    if ocr_faible:
        issues.append("ocr_faible")
    if page_manquante:
        issues.append("page_manquante")
    if incomplet:
        issues.append("incomplet")

    return {
        "illisible": illisible,
        "ocr_faible": ocr_faible,
        "page_manquante": page_manquante,
        "incomplet": incomplet,
        "detail": "; ".join(issues) if issues else "lecture correcte",
    }


def extract_document_text(uploaded_file) -> tuple[str, str]:
    """
    Extrait le texte depuis un fichier upload.
    Retourne (nom_du_fichier, texte_extrait).
    """
    filename = uploaded_file.name
    file_bytes = uploaded_file.read()
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        text = extract_text_from_pdf(file_bytes, filename)
    elif ext == ".docx":
        text = extract_text_from_docx(file_bytes)
    elif ext in (".png", ".jpg", ".jpeg"):
        text = extract_text_from_image(file_bytes)
    elif ext == ".txt":
        text = extract_text_from_txt(file_bytes)
    else:
        text = f"[Format non supporte: {ext}]"

    return filename, text


def extract_all_documents(uploaded_files: list) -> dict[str, str]:
    """
    Extrait le texte de tous les fichiers upload.
    Retourne {nom_fichier: texte}.
    """
    documents, _statuses = extract_all_documents_with_status(uploaded_files)
    return documents


def extract_all_documents_with_status(uploaded_files: list) -> tuple[dict[str, str], dict[str, str]]:
    """
    Extrait le texte de tous les fichiers upload avec leur statut de lecture.

    Retourne ({nom_fichier: texte}, {nom_fichier: statut}).
    Statuts : 'natif', 'ocr', 'ocr_indisponible', 'erreur', 'nettoye'.
    """
    documents: dict[str, str] = {}
    statuses: dict[str, str] = {}
    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        file_bytes = uploaded_file.read()
        ext = Path(filename).suffix.lower()

        if ext == ".pdf":
            text, status = _extract_text_from_pdf_with_status(file_bytes, filename)
        elif ext == ".docx":
            text = extract_text_from_docx(file_bytes)
            status = "natif"
        elif ext in (".png", ".jpg", ".jpeg"):
            text = extract_text_from_image(file_bytes)
            status = "ocr" if not text.startswith("[") else "ocr_indisponible"
        elif ext == ".txt":
            text = extract_text_from_txt(file_bytes)
            status = "natif"
        else:
            text = f"[Format non supporte: {ext}]"
            status = "erreur"

        documents[filename] = text
        statuses[filename] = status
    return documents, statuses
