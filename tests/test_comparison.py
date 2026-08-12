"""
Tests pytest pour le comparateur de documents.

Vérifie la détection des incohérences entre documents
(dates différentes, clauses manquantes, mêmes parties).
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comparison.document_comparator import DocumentComparator


def _make_extraction(dates=None, montants=None, parties=None, personnes=None, clauses=None, placeholders=None):
    """Helper pour créer une extraction structurée."""
    return {
        "entites": {
            "dates": [{"valeur": d, "position": 0} for d in (dates or [])],
            "montants": [{"valeur": m, "devise": "EUR", "position": 0} for m in (montants or [])],
            "parties": [{"nom": p, "type": "societe", "position": 0} for p in (parties or [])],
            "personnes": [{"civilite": "M.", "nom": p, "position": 0} for p in (personnes or [])],
            "articles": [],
            "placeholders": [{"valeur": p, "position": 0} for p in (placeholders or [])],
        },
        "clauses": [{"titre": c, "contenu": "", "position": 0} for c in (clauses or [])],
    }


class TestIdenticalDocumentsNoInconsistencies:
    """Teste que deux documents identiques ne génèrent pas d'incohérences."""

    def test_identical_extractions(self) -> None:
        """Vérifie l'absence d'incohérence pour des extractions identiques."""
        extraction = _make_extraction(
            dates=["15/03/2024"],
            montants=["50000"],
            parties=["SAS INNOV-TECH"],
            clauses=["agrément", "capital"],
        )
        comp = DocumentComparator(extraction, extraction)
        result = comp.compare_all()
        # Pas d'incohérence de type "montant" ou "partie" attendue
        types_incoherences = [inc["type"] for inc in result]
        assert "montant" not in types_incoherences


class TestDifferentDatesDetected:
    """Teste la détection de dates différentes entre deux documents."""

    def test_dates_differentes(self) -> None:
        """Vérifie que des dates différentes sont détectées."""
        ext1 = _make_extraction(dates=["15/03/2024"])
        ext2 = _make_extraction(dates=["20/06/2024"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        dates_incoherences = [inc for inc in result if inc["type"] == "date"]
        assert len(dates_incoherences) > 0, "Les dates différentes devraient être détectées."

    def test_dates_identiques(self) -> None:
        """Vérifie que des dates identiques ne génèrent pas d'incohérence de date."""
        ext1 = _make_extraction(dates=["15/03/2024"])
        ext2 = _make_extraction(dates=["15/03/2024"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        dates_incoherences = [inc for inc in result if inc["type"] == "date"]
        assert len(dates_incoherences) == 0


class TestMissingClauseDetected:
    """Teste la détection de clauses absentes dans un document."""

    def test_clause_manquante_dans_statuts(self) -> None:
        """Vérifie qu'une clause présente dans le pacte mais absente des statuts est signalée."""
        ext1 = _make_extraction(clauses=["agrément", "tag-along", "capital"])
        ext2 = _make_extraction(clauses=["capital"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        clause_incoherences = [inc for inc in result if inc["type"] == "clause"]
        assert len(clause_incoherences) > 0

    def test_different_montants(self) -> None:
        """Vérifie la détection de montants différents."""
        ext1 = _make_extraction(montants=["50000"])
        ext2 = _make_extraction(montants=["100000"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        montants_incoherences = [inc for inc in result if inc["type"] == "montant"]
        assert len(montants_incoherences) > 0, "Les montants différents devraient être détectés."


class TestSameParties:
    """Teste la détection des parties communes."""

    def test_same_parties_detected(self) -> None:
        """Vérifie que les mêmes parties ne génèrent pas d'incohérence."""
        ext1 = _make_extraction(parties=["SAS INNOV-TECH"], personnes=["DUPONT", "MARTIN"])
        ext2 = _make_extraction(parties=["SAS INNOV-TECH"], personnes=["DUPONT", "MARTIN"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        partie_incoherences = [inc for inc in result if inc["type"] == "partie"]
        assert len(partie_incoherences) == 0, "Les mêmes parties ne devraient pas générer d'incohérence."

    def test_different_parties(self) -> None:
        """Vérifie que des parties différentes sont signalées."""
        ext1 = _make_extraction(parties=["SAS INNOV-TECH"], personnes=["DUPONT"])
        ext2 = _make_extraction(parties=["SARL CONSULT-EXPERT"], personnes=["BERNARD"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        partie_incoherences = [inc for inc in result if inc["type"] == "partie"]
        assert len(partie_incoherences) > 0, "Des parties différentes devraient être détectées."


class TestNormalisationParties:
    """Teste la normalisation des noms de parties (anti faux positifs)."""

    def test_meme_societe_libelle_different(self) -> None:
        """La même société libellée différemment ne doit pas être signalée."""
        ext1 = _make_extraction(parties=["SARL TOP LEGAL CONSEIL"])
        ext2 = _make_extraction(parties=["STATUTS DE LA SOCIETE TOP LEGAL CONSEIL"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        partie_incoherences = [inc for inc in result if inc["type"] == "partie"]
        assert partie_incoherences == [], (
            "Le même acteur avec un libellé différent ne devrait pas générer d'incohérence."
        )

    def test_nom_generique_seul_ignore(self) -> None:
        """Une partie 'SARL' seule (sans mot significatif) est ignorée."""
        ext1 = _make_extraction(parties=["SARL"])
        ext2 = _make_extraction(parties=[])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        partie_incoherences = [inc for inc in result if inc["type"] == "partie"]
        assert partie_incoherences == []

    def test_personne_correspond(self) -> None:
        """Les personnes identiques (avec ou sans civilité) correspondent."""
        ext1 = _make_extraction(personnes=["DUPONT"])
        ext2 = _make_extraction(personnes=["DUPONT"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        partie_incoherences = [inc for inc in result if inc["type"] == "partie"]
        assert partie_incoherences == []

    def test_personne_absente_detectee(self) -> None:
        """Une personne absente d'un des documents est signalée."""
        ext1 = _make_extraction(personnes=["DUPONT"])
        ext2 = _make_extraction(personnes=["MARTIN"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        partie_incoherences = [inc for inc in result if inc["type"] == "partie"]
        assert len(partie_incoherences) > 0


class TestPlaceholderDateDetected:
    """Teste la détection d'un champ date non renseigné ([date]) en comparaison."""

    def test_placeholder_au_lieu_de_date_absente(self) -> None:
        """Un '[date]' dans les statuts est signalé comme champ non renseigné."""
        ext1 = _make_extraction(dates=["01/01/2025"])
        ext2 = _make_extraction(dates=[], placeholders=["[date]"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        date_incoherences = [inc for inc in result if inc["type"] == "date"]
        assert len(date_incoherences) == 1
        assert "non renseigné" in date_incoherences[0]["description"]
        assert date_incoherences[0]["severite"] == "alerte"

    def test_sans_placeholder_message_original(self) -> None:
        """Sans placeholder, le message original est conservé."""
        ext1 = _make_extraction(dates=["01/01/2025"])
        ext2 = _make_extraction(dates=[])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        date_incoherences = [inc for inc in result if inc["type"] == "date"]
        assert "absente(s) des statuts" in date_incoherences[0]["description"]
        assert "non renseigné" not in date_incoherences[0]["description"]


class TestVariantesOrthographiques:
    """Teste le rapprochement des variantes orthographiques de noms."""

    def test_hichem_hicham_rapproches(self) -> None:
        """'HICHEM' et 'HICHAM' sont rapprochés en une alerte, pas deux absences."""
        ext1 = _make_extraction(personnes=["HICHEM"])
        ext2 = _make_extraction(personnes=["HICHAM"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        partie_incoherences = [inc for inc in result if inc["type"] == "partie"]
        assert len(partie_incoherences) == 1
        assert partie_incoherences[0]["severite"] == "alerte"
        assert "variante orthographique" in partie_incoherences[0]["description"]

    def test_noms_vraiment_differents_inchanges(self) -> None:
        """Des noms très différents restent deux absences 'important'."""
        ext1 = _make_extraction(personnes=["MOHAMED"])
        ext2 = _make_extraction(personnes=["MARTIN"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        partie_incoherences = [inc for inc in result if inc["type"] == "partie"]
        severites = [inc["severite"] for inc in partie_incoherences]
        assert severites == ["important", "important"]
        assert all("variante" not in inc["description"] for inc in partie_incoherences)


class TestMontantsSubset:
    """Teste la comparaison des montants quand l'un est un sous-ensemble."""

    def test_sous_ensemble_alerte_pas_bloquant(self) -> None:
        """Un montant plus détaillé n'est pas une contradiction bloquante."""
        ext1 = _make_extraction(montants=["50000", "100"])
        ext2 = _make_extraction(montants=["50000"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        montants_incoherences = [inc for inc in result if inc["type"] == "montant"]
        assert len(montants_incoherences) == 1
        assert montants_incoherences[0]["severite"] == "alerte"

    def test_montants_contradictoires_bloquants(self) -> None:
        """Des montants contradictoires restent bloquants."""
        ext1 = _make_extraction(montants=["50000"])
        ext2 = _make_extraction(montants=["100000"])
        comp = DocumentComparator(ext1, ext2)
        result = comp.compare_all()
        montants_incoherences = [inc for inc in result if inc["type"] == "montant"]
        assert len(montants_incoherences) == 1
        assert montants_incoherences[0]["severite"] == "bloquant"
