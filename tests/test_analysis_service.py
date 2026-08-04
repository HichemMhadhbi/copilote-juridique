"""Tests du pipeline d'analyse (analysis_service).

Verifie notamment que le champ documents_a_verifier des anomalies contient
le nom du fichier concerne (et non 'non spécifié').
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analysis_service import analyze_documents


def _pacte_texte() -> str:
    return (
        "PACTE D'ASSOCIES SARL TOP LEGAL CONSEIL\n"
        "Article 1 - Objet du pacte\n"
        "Le present pacte a pour objet de regir les relations entre les associes.\n"
        "Article 2 - Capital social\n"
        "Le capital social est fixe a 50 000 euros, divise en 500 parts sociales.\n"
        "Article 3 - Agrement des cessions de parts\n"
        "Toute cession de parts a un tiers est soumise a l'agrement de la majorite des deux tiers.\n"
        "Article 4 - Non-concurrence\n"
        "Chaque associe s'engage a ne pas concurrencer la societe pendant 2 ans.\n"
        "Article 5 - Mediation\n"
        "Les parties conviennent de recourir a une mediation avant toute action judiciaire.\n"
    )


def _statuts_texte() -> str:
    return (
        "STATUTS DE LA SOCIETE TOP LEGAL CONSEIL (SARL)\n"
        "Article 1 - Forme juridique\n"
        "La societe est une SARL regie par le Code de commerce.\n"
        "Article 2 - Capital social\n"
        "Le capital social est fixe a 50 000 euros, divise en 500 parts sociales.\n"
        "Article 3 - Gerance\n"
        "La societe est geree par un gerant dont les pouvoirs sont limites aux actes courants.\n"
    )


def test_pacte_seul_documents_a_verifier():
    """Les anomalies d'un pacte seul portent le nom du fichier."""
    texte = _pacte_texte()
    rapport = analyze_documents({"pacte_test.pdf": texte}, {"pacte_test.pdf": "natif"})

    types = [d["type"] for d in rapport["documents_analyses"]]
    assert "pacte d'associes" in types

    assert len(rapport["anomalies_juridiques"]) >= 1
    for a in rapport["anomalies_juridiques"]:
        assert "pacte_test.pdf" in a["documents_a_verifier"], (
            f"documents_a_verifier inattendu : {a['documents_a_verifier']}"
        )
        assert "non spécifié" not in str(a["documents_a_verifier"])


def test_statuts_seuls_documents_a_verifier():
    """Les anomalies des statuts seuls portent le nom du fichier."""
    texte = _statuts_texte()
    rapport = analyze_documents({"statuts_test.pdf": texte}, {"statuts_test.pdf": "natif"})

    types = [d["type"] for d in rapport["documents_analyses"]]
    assert "statuts de societe" in types

    assert len(rapport["anomalies_juridiques"]) >= 1
    for a in rapport["anomalies_juridiques"]:
        assert "statuts_test.pdf" in a["documents_a_verifier"], (
            f"documents_a_verifier inattendu : {a['documents_a_verifier']}"
        )
        assert "non spécifié" not in str(a["documents_a_verifier"])
