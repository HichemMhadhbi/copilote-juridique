"""Tests du service d'export (Markdown, JSON, PDF, conversation)."""

from __future__ import annotations

import json
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import export_service  # noqa: E402


def _sample_report() -> dict:
    return {
        "rapport_id": "rid-export",
        "niveau_risque_global": "eleve",
        "documents_analyses": [{"nom": "pacte.pdf", "type": "pacte_associes", "statut": "lu"}],
        "informations_principales": {
            "regles_controle_appliquees": True,
            "entites_extraites": {
                "pacte.pdf": {
                    "dates": [{"valeur": "01/01/2024"}],
                    "parties": [{"nom": "TOP LEGAL CONSEIL"}],
                    "montants": [{"valeur": "50000"}],
                }
            },
        },
        "synthese_intelligente": "Synthèse de test.",
        "anomalies_juridiques": [
            {
                "nature_controle": "clause_manquante",
                "priorite": "bloquant",
                "explication": "Aucune clause d'agrement.",
                "source_juridique": "Art. L223-14",
                "source_statut": "verifiee",
                "legifrance_url": "https://www.legifrance.gouv.fr/",
                "correction_recommandee": "Ajouter une clause d'agrement.",
                "documents_a_verifier": ["statuts.pdf"],
            }
        ],
        "incoherences": [],
    }


class TestExportRapport:
    def test_json(self) -> None:
        data = export_service.export_report_as_json(_sample_report())
        parsed = json.loads(data.decode("utf-8"))
        assert parsed["rapport_id"] == "rid-export"

    def test_markdown(self) -> None:
        data = export_service.export_report_as_markdown(_sample_report())
        assert b"Anomalies juridiques" in data or b"Rapport" in data

    def test_pdf_non_vide(self) -> None:
        data = export_service.export_report_as_pdf(_sample_report())
        assert data.startswith(b"%PDF")
        assert len(data) > 1000


class TestExportConversation:
    def _conv(self) -> list[dict]:
        return [
            {"question": "Quels risques ?", "answer": "Risque eleve.", "timestamp": "12:00"}
        ]

    def test_texte(self) -> None:
        data = export_service.export_conversation_as_text(self._conv())
        assert b"Question : Quels risques ?" in data
        assert b"Reponse : Risque eleve." in data

    def test_pdf_non_vide(self) -> None:
        data = export_service.export_conversation_as_pdf(self._conv())
        assert data.startswith(b"%PDF")
        assert len(data) > 500
