"""Tests de l'analyse de clauses (repli local deterministe).

L'analyse de clause doit toujours retourner un resultat structure, meme
sans cle LLM valide : c'est le socle deterministe garantissant un rendu
utilisable hors ligne.
"""

from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import llm_service


class TestAnalyseClauseLocale:
    """Verifie le repli local sans cle LLM (neutralise globalement par conftest)."""

    def test_clause_conforme(self) -> None:
        """Une clause sans risque connu est notee faible."""
        resultat = llm_service.analyser_clause(
            "Article 1 — Objet", "Le pacte a pour objet de regir les relations entre les associes."
        )
        assert resultat["niveau_risque"] == "faible"
        assert resultat["titre"]
        assert resultat["analyse"]

    def test_clause_veto_eleve(self) -> None:
        """Un droit de veto est note a risque eleve avec fondement."""
        resultat = llm_service.analyser_clause(
            "Droit de veto",
            "L'associe A dispose d'un droit de veto sur toute decision.",
        )
        assert resultat["niveau_risque"] == "eleve"
        assert "L223-27" in resultat["fondement"]
        assert resultat["amelioration_argmentee"]

    def test_clause_valorisation(self) -> None:
        """La valorisation sans methode objective est rattachee a l'art. 1843-4."""
        resultat = llm_service.analyser_clause(
            "Sortie conjointe",
            "La valorisation des titres en cas de cession est fixee par les cedants.",
        )
        # Le risque de valorisation (eleve) prime sur celui de sortie (modere)
        assert resultat["niveau_risque"] == "eleve"
        assert "1843-4" in resultat["fondement"]

    def test_clause_sortie_sans_valorisation_explicite(self) -> None:
        """Une sortie sans terme de valorisation retombe sur la regle sortie."""
        resultat = llm_service.analyser_clause(
            "Sortie conjointe",
            "En cas de vente de la majorite du capital, les associes cedent leurs titres.",
        )
        assert resultat["niveau_risque"] == "modere"
        assert "1103" in resultat["fondement"]

    def test_clause_sans_accent_robuste(self) -> None:
        """L'analyse supporte les textes sans accents (extractions PDF)."""
        resultat = llm_service.analyser_clause(
            "Non concurrence", "Clause de non concurrence pour une duree de 5 ans."
        )
        assert resultat["niveau_risque"] == "modere"

    def test_structure_du_resultat(self) -> None:
        """Le resultat expose toujours les 5 champs attendus."""
        resultat = llm_service.analyser_clause("Titre", "Contenu")
        for champ in ("titre", "niveau_risque", "analyse", "amelioration_argmentee", "fondement"):
            assert champ in resultat, f"Champ manquant : {champ}"


class TestParseClauseJson:
    """Verifie le parse de la reponse JSON du LLM."""

    def test_json_brut(self) -> None:
        brut = '{"niveau_risque": "eleve", "analyse": "a", "amelioration_argmentee": "b", "fondement": "c"}'
        data = llm_service._parse_clause_json(brut)
        assert data is not None
        assert data["niveau_risque"] == "eleve"

    def test_json_dans_bloc_markdown(self) -> None:
        brut = '```json\n{"niveau_risque": "modere", "analyse": "a", "amelioration_argmentee": "b", "fondement": ""}\n```'
        data = llm_service._parse_clause_json(brut)
        assert data is not None
        assert data["niveau_risque"] == "modere"

    def test_niveau_invalide(self) -> None:
        brut = '{"niveau_risque": "critique", "analyse": "a", "amelioration_argmentee": "b", "fondement": ""}'
        assert llm_service._parse_clause_json(brut) is None

    def test_texte_non_json(self) -> None:
        assert llm_service._parse_clause_json("pas du json") is None
