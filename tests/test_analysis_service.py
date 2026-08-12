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


def test_pacte_seul_documents_manquants():
    """Un pacte sans statuts : les statuts sont signalés manquants."""
    texte = _pacte_texte()
    rapport = analyze_documents({"pacte_test.pdf": texte}, {"pacte_test.pdf": "natif"})

    assert rapport["documents_manquants"], (
        "Un dossier ne contenant qu'un pacte doit signaler les statuts manquants"
    )
    assert any("Statuts" in d for d in rapport["documents_manquants"])


def test_dossier_complet_aucun_document_manquant():
    """Pacte + statuts : dossier complet, rien de manquant."""
    rapport = analyze_documents(
        {"pacte_test.pdf": _pacte_texte(), "statuts_test.pdf": _statuts_texte()},
        {"pacte_test.pdf": "natif", "statuts_test.pdf": "natif"},
    )
    assert rapport["documents_manquants"] == []


def test_statuts_seuls_aucun_document_manquant():
    """Des statuts seuls : rien de manquant (le pacte est optionnel)."""
    rapport = analyze_documents(
        {"statuts_test.pdf": _statuts_texte()},
        {"statuts_test.pdf": "natif"},
    )
    assert rapport["documents_manquants"] == []


def test_documents_non_societe_aucun_document_manquant():
    """Des documents non-société (cours/manuels) : aucune complétude exigée."""
    rapport = analyze_documents(
        {"cours.pdf": "Introduction au droit des contrats, chapitre 1."},
        {"cours.pdf": "natif"},
    )
    assert rapport["documents_manquants"] == []


def _statuts_texte_transports() -> str:
    return (
        "STATUTS DE LA SOCIETE TRANSPORTS EXPRESS (SARL)\n"
        "Article 1 - Forme juridique\n"
        "La societe est une SARL. La denomination de la SARL est TRANSPORTS EXPRESS.\n"
        "Article 2 - Objet social\n"
        "La societe a pour objet le transport routier de marchandises.\n"
        "Article 3 - Siege social\n"
        "Le siege social est fixe a Paris.\n"
        "Article 4 - Duree de la societe\n"
        "La duree de la societe est fixee a 99 ans.\n"
        "Article 5 - Capital social\n"
        "Le capital social est fixe a 50 000 euros, divise en 500 parts sociales.\n"
        "Article 6 - Gerance\n"
        "La societe est administree par un gerant.\n"
        "Article 7 - Cession de parts\n"
        "Toute cession de parts est soumise a agrement.\n"
        "Article 8 - Affectation des resultats\n"
        "Les resultats sont affectes selon la loi.\n"
        "Article 9 - Dissolution\n"
        "La societe peut etre dissoute.\n"
        "Article 10 - Liquidation\n"
        "La liquidation est regie par la loi.\n"
    )


def test_societes_differentes_comparaison_ecartee():
    """Un pacte de société A et des statuts de société B ne sont pas comparés."""
    rapport = analyze_documents(
        {"pacte_test.pdf": _pacte_texte(), "statuts_test.pdf": _statuts_texte_transports()},
        {"pacte_test.pdf": "natif", "statuts_test.pdf": "natif"},
    )
    assert rapport.get("comparaison_ecartee"), (
        "Des documents de sociétés différentes doivent lever un avertissement"
    )
    assert "sociétés différentes" in rapport["comparaison_ecartee"]
    assert rapport["incoherences"] == [], (
        "Aucune incohérence ne doit être produite entre deux sociétés différentes"
    )


def test_societes_differentes_types_corrects():
    """Chaque document garde son type détecté (pacte + statuts)."""
    rapport = analyze_documents(
        {"pacte_test.pdf": _pacte_texte(), "statuts_test.pdf": _statuts_texte_transports()},
        {"pacte_test.pdf": "natif", "statuts_test.pdf": "natif"},
    )
    types = {d["nom"]: d["type"] for d in rapport["documents_analyses"]}
    assert types["pacte_test.pdf"] == "pacte d'associes"
    assert types["statuts_test.pdf"] == "statuts de societe"


def test_meme_societe_comparaison_conservee():
    """Deux documents de la même société sont bien comparés."""
    rapport = analyze_documents(
        {
            "pacte_test.pdf": _pacte_texte(),
            "statuts_test.pdf": (
                "STATUTS DE LA SOCIETE TOP LEGAL CONSEIL (SARL)\n"
                "Article 1 - Forme juridique\n"
                "La denomination de la SARL est TOP LEGAL CONSEIL.\n"
                "Article 2 - Capital social\n"
                "Le capital social est fixe a 50 000 euros.\n"
            ),
        },
        {"pacte_test.pdf": "natif", "statuts_test.pdf": "natif"},
    )
    assert not rapport.get("comparaison_ecartee"), (
        "Deux documents de la même société doivent rester comparés"
    )
