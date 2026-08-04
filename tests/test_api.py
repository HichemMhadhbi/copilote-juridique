"""Tests de l'API FastAPI TOP-JURIDIQUE.

Couvre les endpoints documentés dans `docs/06_integration.md` :
/health, /analyze (fichiers multiples), /report/{report_id} et
/validate/{report_id}/{finding_id}.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from api.endpoints import app

client = TestClient(app)


def _pdf_statuts_bytes() -> bytes:
    """Génère un petit PDF avec du texte exploitable (rapportlab)."""
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    texte = (
        "STATUTS DE LA SOCIETE TEST (SARL). Article 1 - Forme juridique. "
        "La societe est une societe a responsabilite limitee regie par le "
        "Code de commerce. Article 5 - Capital social fixe a 1000 euros divise "
        "en 100 parts sociales de 10 euros. Article 6 - Gerance : la societe "
        "est geree par un gerant nomme par les associes, qui dispose des "
        "pouvoirs les plus etendus pour agir au nom de la societe."
    )
    c.drawString(72, 720, texte[:100])
    c.drawString(72, 700, texte[100:200])
    c.drawString(72, 680, texte[200:])
    c.save()
    return buffer.getvalue()


PDF_VALIDE = _pdf_statuts_bytes()
PDF_VIDE = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["statut"] == "operational"
    assert data["version"] == "1.0.0"
    assert "fournisseurs_disponibles" in data


def test_analyze_un_fichier() -> None:
    resp = client.post(
        "/analyze",
        files={"files": ("statuts_test.pdf", PDF_VALIDE, "application/pdf")},
        data={"mode": "rapide"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["statut"] == "termine"
    assert data["nombre_documents"] == 1
    assert data["report_id"]


def test_analyze_plusieurs_fichiers() -> None:
    resp = client.post(
        "/analyze",
        files=[
            ("files", ("statuts_a.pdf", PDF_VALIDE, "application/pdf")),
            ("files", ("statuts_b.pdf", PDF_VALIDE, "application/pdf")),
        ],
        data={"mode": "rapide"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["nombre_documents"] == 2


def test_analyze_aucun_fichier() -> None:
    resp = client.post("/analyze", data={"mode": "rapide"})
    assert resp.status_code == 400


def test_analyze_fichier_illisible() -> None:
    resp = client.post(
        "/analyze",
        files={"files": ("vide.pdf", PDF_VIDE, "application/pdf")},
        data={"mode": "rapide"},
    )
    assert resp.status_code == 400
    assert "Aucun document exploitable" in resp.json()["detail"]


def test_get_report_cycle_complet() -> None:
    resp = client.post(
        "/analyze",
        files={"files": ("statuts_test.pdf", PDF_VALIDE, "application/pdf")},
    )
    report_id = resp.json()["report_id"]

    detail = client.get(f"/report/{report_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["rapport_id"] == report_id
    assert "informations_principales" in data
    assert "anomalies_juridiques" in data


def test_get_report_inconnu() -> None:
    resp = client.get("/report/rapport-inconnu")
    assert resp.status_code == 404


def test_validate_approuver() -> None:
    resp = client.post(
        "/analyze",
        files={"files": ("statuts_test.pdf", PDF_VALIDE, "application/pdf")},
    )
    report_id = resp.json()["report_id"]

    resp = client.post(
        f"/validate/{report_id}/anomalie-1",
        json={"action": "approuver", "comment": "Conforme."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["finding_id"] == "anomalie-1"
    assert data["statut"] == "approuver"


def test_validate_rejeter_sans_motif() -> None:
    resp = client.post(
        "/analyze",
        files={"files": ("statuts_test.pdf", PDF_VALIDE, "application/pdf")},
    )
    report_id = resp.json()["report_id"]

    resp = client.post(
        f"/validate/{report_id}/anomalie-1",
        json={"action": "rejeter"},
    )
    assert resp.status_code == 400


def test_validate_modifier_sans_contenu() -> None:
    resp = client.post(
        "/analyze",
        files={"files": ("statuts_test.pdf", PDF_VALIDE, "application/pdf")},
    )
    report_id = resp.json()["report_id"]

    resp = client.post(
        f"/validate/{report_id}/anomalie-1",
        json={"action": "modifier"},
    )
    assert resp.status_code == 400


def test_validate_action_invalide() -> None:
    resp = client.post(
        "/analyze",
        files={"files": ("statuts_test.pdf", PDF_VALIDE, "application/pdf")},
    )
    report_id = resp.json()["report_id"]

    resp = client.post(
        f"/validate/{report_id}/anomalie-1",
        json={"action": "transformer"},
    )
    assert resp.status_code == 400


def test_validate_rapport_inconnu() -> None:
    resp = client.post(
        "/validate/rapport-inconnu/anomalie-1",
        json={"action": "approuver"},
    )
    assert resp.status_code == 404
