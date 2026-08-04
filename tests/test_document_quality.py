"""Tests de la détection de la qualité de lecture des documents."""

from services.document_service import assess_document_quality


def test_document_propre():
    """Un document d'entreprise complet n'est pas signalé."""
    texte = "STATUTS DE LA SOCIETE XYZ\n\n" + "\n".join(
        f"Article {i} - Objet\nLa societe a pour objet le conseil juridique. "
        "Les statuts sont regis par le code de commerce."
        for i in range(1, 8)
    ) + "\nFait a Paris le 15 mars 2024."
    q = assess_document_quality(texte, "natif")
    assert q["detail"] == "lecture correcte"


def test_illisible_vide():
    """Un texte vide ou presque est illisible."""
    q = assess_document_quality("   ", "natif")
    assert q["illisible"] is True


def test_illisible_erreur():
    """Un message d'erreur OCR est considéré illisible."""
    q = assess_document_quality("[OCR indisponible : Tesseract manquant]", "ocr_indisponible")
    assert q["illisible"] is True


def test_ocr_faible():
    """Un résultat OCR trop court est jugé peu fiable."""
    q = assess_document_quality("quelques mots", "ocr")
    assert q["ocr_faible"] is True


def test_page_manquante():
    """Une saut de numérotation de page (Page 1 puis Page 3) est détecté."""
    texte = "Page 1\ncontenu\nPage 3\ncontenu"
    q = assess_document_quality(texte, "natif")
    assert q["page_manquante"] is True


def test_page_sans_trou():
    """Une numérotation continue ne déclenche pas d'alerte."""
    texte = "Page 1\nPage 2\nPage 3"
    q = assess_document_quality(texte, "natif")
    assert q["page_manquante"] is False


def test_incomplet_court():
    """Des statuts très courts sont jugés incomplets."""
    q = assess_document_quality("Statuts de la societe. Capital social.", "natif")
    assert q["incomplet"] is True
