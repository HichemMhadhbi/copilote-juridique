"""Tests du service de chat (repli local déterministe).

La fixture autouse de conftest neutralise le LLM : toutes les réponses
viennent de la logique locale basée sur les entités extraites et le texte.
"""

from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.chat_service import answer_question_from_report  # noqa: E402


def _sample_report() -> dict:
    return {
        "rapport_id": "rid-chat",
        "niveau_risque_global": "eleve",
        "documents_analyses": [{"nom": "pacte.pdf", "type": "pacte_associes", "statut": "lu"}],
        "informations_principales": {
            "document_text": (
                "Le pacte d'associes de la societe TOP LEGAL CONSEIL est conclu pour une "
                "duree de dix annees. Le siege social est fixe a Paris. Le capital social "
                "est de 50000 euros, divise en 500 parts de 100 euros."
            ),
            "entites_extraites": {
                "pacte.pdf": {
                    "parties": [{"nom": "TOP LEGAL CONSEIL"}],
                    "dates": [{"valeur": "01/01/2024"}],
                    "montants": [{"valeur": "50000"}, {"valeur": "100"}],
                }
            },
        },
        "anomalies_juridiques": [
            {
                "priorite": "bloquant",
                "explication": "Aucune clause d'agrement.",
                "source_juridique": "Art. L223-14",
                "correction_recommandee": "Ajouter une clause d'agrement.",
            }
        ],
        "incoherences": [
            {"type": "capital_social", "severite": "majeure", "description": "Montant different."}
        ],
    }


class TestReponsesLocales:
    def test_parties(self) -> None:
        reponse = answer_question_from_report("Quelles sont les parties au pacte ?", _sample_report())
        assert "TOP LEGAL CONSEIL" in reponse

    def test_dates(self) -> None:
        reponse = answer_question_from_report("Quelles sont les dates importantes ?", _sample_report())
        assert "Dates identifiees" in reponse
        assert "01/01/2024" in reponse

    def test_montants(self) -> None:
        reponse = answer_question_from_report("Quel est le capital social ?", _sample_report())
        assert "Montants identifies" in reponse
        assert "50000" in reponse

    def test_risques(self) -> None:
        reponse = answer_question_from_report("Quels sont les risques ?", _sample_report())
        assert "Niveau de risque global : ELEVE" in reponse

    def test_incoherences(self) -> None:
        reponse = answer_question_from_report("Y a-t-il des incoherences ?", _sample_report())
        assert "Incoherences detectees" in reponse
        assert "capital_social" in reponse

    def test_recommandations(self) -> None:
        reponse = answer_question_from_report("Donne des recommandations", _sample_report())
        assert "Recommandations" in reponse
        assert "clause d'agrement" in reponse

    def test_resume(self) -> None:
        reponse = answer_question_from_report("Fais un resume du document", _sample_report())
        assert "Resume" in reponse
        assert "1 document(s) analyse(s)" in reponse

    def test_references_juridiques(self) -> None:
        reponse = answer_question_from_report("Quelles sont les references legales ?", _sample_report())
        assert "References juridiques" in reponse
        assert "L223-14" in reponse

    def test_conformite_bloquant(self) -> None:
        reponse = answer_question_from_report("Le document est-il conforme ?", _sample_report())
        assert "1 anomalie(s) bloquante(s)" in reponse

    def test_fallback_generique(self) -> None:
        reponse = answer_question_from_report("zzz qqqx", _sample_report())
        assert "Je n'ai pas trouve de reponse precise" in reponse

    def test_reponse_toujours_non_vide(self) -> None:
        for question in [
            "parties", "dates", "capital", "risques", "incoherences",
            "recommandations", "resume", "references", "conforme", "blabla",
        ]:
            reponse = answer_question_from_report(question, _sample_report())
            assert reponse and reponse.strip(), f"réponse vide pour : {question}"
