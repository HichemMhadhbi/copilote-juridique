"""Tests de la base de connaissance juridique (legal_kb).

Verifie le chargement des entrees JSON, la recherche RAG-lite par
pertinence (search_relevant) et l'integration avec le pipeline d'analyse.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from legal_kb.knowledge_base import LegalKnowledgeBase


def _kb() -> LegalKnowledgeBase:
    return LegalKnowledgeBase()


class TestChargement:
    """Verifie le chargement des entrees."""

    def test_chargement_non_vide(self) -> None:
        """La base charge au moins les fichiers societes.json et pactes.json."""
        entries = _kb().get_all_entries()
        assert len(entries) >= 18
        ids = {e["id"] for e in entries}
        assert {"SOC-001", "PACT-001"}.issubset(ids)

    def test_entrees_triees(self) -> None:
        """Les entrees sont triees par identifiant."""
        entries = _kb().get_all_entries()
        ids = [e["id"] for e in entries]
        assert ids == sorted(ids)

    def test_entree_schema(self) -> None:
        """Chaque entree expose les champs attendus par le rapport."""
        for e in _kb().get_all_entries():
            for champ in ("id", "source", "titre_texte", "numero_article",
                          "domaine", "mots_cles", "types_documents_concernes",
                          "regles_controle"):
                assert champ in e, f"Champ manquant {champ} sur {e.get('id')}"


class TestSearchRelevant:
    """Verifie la recherche par pertinence (RAG-lite)."""

    def test_recherche_par_type_de_document(self) -> None:
        """Une requete sans termes retombe sur les entrees du type demande."""
        entries = _kb().search_relevant([], doc_type="pacte_associes", top_k=5)
        assert entries
        for e in entries:
            assert "pacte_associes" in e["types_documents_concernes"]

    def test_recherche_par_article(self) -> None:
        """La reference 'L223-14' remonte l'entree SOC-003 (cession de parts)."""
        entries = _kb().search_relevant(["l223-14"], doc_type="statuts", top_k=5)
        ids = {e["id"] for e in entries}
        assert "SOC-003" in ids

    def test_recherche_par_mot_cle(self) -> None:
        """Le terme 'agrement' remonte les entrees relatives a l'agrement."""
        entries = _kb().search_relevant(["agrement"], top_k=10)
        ids = {e["id"] for e in entries}
        assert {"SOC-003", "SOC-005"}.issubset(ids)

    def test_classement_pertinence_type(self) -> None:
        """Les entrees du bon type de document sont classees en premier."""
        entries = _kb().search_relevant(["cession"], doc_type="pacte_associes", top_k=5)
        assert entries
        assert "PACT-001" == entries[0]["id"]  # drag-along : le plus pertinent

    def test_aucun_resultat_sans_correspondance(self) -> None:
        """Une requete sans correspondance ne renvoie pas tout le monde."""
        entries = _kb().search_relevant(["zzzzzzzz"], top_k=5)
        # Repli : sans type ni domaine, aucune entree pertinente
        assert entries == []

    def test_repli_domaine(self) -> None:
        """Sans termes, le domaine seul suffit a restreindre la recherche."""
        entries = _kb().search_relevant([], domain="droit des sociétés", top_k=5)
        assert entries
        for e in entries:
            assert "droit des sociétés" in e["domaine"]


class TestIntegrationPipeline:
    """Verifie que le rapport d'analyse mobilise reellement la base."""

    def test_anomalies_avec_base_juridique(self) -> None:
        from services.analysis_service import analyze_documents

        texte = (
            "PACTE D'ASSOCIES SARL TEST\n"
            "Article 1 - Objet\nLe pacte regit les relations entre les associes.\n"
            "Article 2 - Capital\nLe capital est fixe a 10 000 euros en 100 parts.\n"
        )
        rapport = analyze_documents({"pacte.pdf": texte}, {"pacte.pdf": "natif"})

        assert "base_juridique_utilisee" in rapport["informations_principales"]
        # Au moins une anomalie porte des references de la base
        avec_refs = [
            a for a in rapport["anomalies_juridiques"]
            if a.get("base_juridique")
        ]
        assert avec_refs, "Au moins une anomalie doit mobiliser la base juridique."
        for a in avec_refs:
            for ref in a["base_juridique"]:
                assert ref.get("id"), "Chaque reference doit avoir un id"
                assert "regles_controle" in ref

    def test_rapport_indique_entrees_mobilisees(self) -> None:
        from services.analysis_service import analyze_documents

        texte = (
            "STATUTS SARL TEST\n"
            "Article 1 - Forme\nLa societe est une SARL.\n"
            "Article 2 - Capital\nLe capital est fixe a 10 000 euros en 100 parts.\n"
        )
        rapport = analyze_documents({"statuts.pdf": texte}, {"statuts.pdf": "natif"})
        infos = rapport["informations_principales"]
        assert "mobilisees par RAG-lite" in infos["base_juridique"]
