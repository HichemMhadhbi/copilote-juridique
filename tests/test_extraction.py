"""
Tests pytest pour l'extracteur d'entités.

Vérifie l'extraction des dates, montants, parties
et clauses depuis le texte des documents juridiques.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extraction.entity_extractor import EntityExtractor


class TestExtractDates:
    """Teste l'extraction des dates depuis le texte."""

    def test_extract_french_date(self) -> None:
        """Vérifie l'extraction d'une date au format français."""
        texte = "Le contrat a été signé le 15 mars 2024 à Paris."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        dates = [d["valeur"] for d in result["dates"]]
        assert len(dates) > 0
        assert any("15" in d and "03" in d and "2024" in d for d in dates)

    def test_extract_multiple_dates(self) -> None:
        """Vérifie l'extraction de plusieurs dates."""
        texte = """
        Date de signature : le 15 mars 2024.
        Date d'effet : 01/06/2024.
        """
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        assert len(result["dates"]) >= 2

    def test_extract_iso_date(self) -> None:
        """Vérifie l'extraction d'une date au format JJ/MM/AAAA."""
        texte = "La date limite est fixée au 20/09/2024."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        assert len(result["dates"]) > 0

    def test_no_dates(self) -> None:
        """Vérifie qu'aucune date n'est extraite d'un texte sans date."""
        texte = "Ce document ne contient aucune date."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        assert len(result["dates"]) == 0


class TestExtractAmounts:
    """Teste l'extraction des montants monétaires."""

    def test_extract_euros(self) -> None:
        """Vérifie l'extraction de montants en euros."""
        texte = "Le capital social est de 50 000 euros. Le loyer est de 1 500 euros."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        montants = [m["valeur"] for m in result["montants"]]
        assert len(montants) >= 2

    def test_extract_euro_symbol(self) -> None:
        """Vérifie l'extraction avec 'euros' (symbole € nécessite un mot-chractère après)."""
        texte = "Le montant est de 25 000 euros."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        assert len(result["montants"]) > 0

    def test_extract_capital_social(self) -> None:
        """Vérifie l'extraction du capital social."""
        texte = "Capital social de 100 000 euros, divisé en 1000 actions."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        assert len(result["montants"]) > 0

    def test_no_amounts(self) -> None:
        """Vérifie qu'aucun montant n'est extrait d'un texte sans montant."""
        texte = "Ce document traite de la gouvernance de la société."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        assert len(result["montants"]) == 0


class TestExtractParties:
    """Teste l'extraction des parties (personnes physiques et morales)."""

    def test_extract_company(self) -> None:
        """Vérifie l'extraction du nom d'une société."""
        texte = "La SAS INNOV-TECH est représentée par son président."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        noms = [p["nom"] for p in result["parties"]]
        assert len(noms) > 0
        assert any("INNOV" in n for n in noms)

    def test_extract_multiple_parties(self) -> None:
        """Vérifie l'extraction de plusieurs parties."""
        texte = """
        SAS INNOV-TECH représentée par M. Jean DUPONT.
        Mme Sophie MARTIN associée.
        SARL CONSULT-EXPERT représentée par M. Paul BERNARD.
        """
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        total = len(result["parties"]) + len(result["personnes"])
        assert total >= 2

    def test_extract_person_with_title(self) -> None:
        """Vérifie l'extraction d'une personne avec titre."""
        texte = "Le M. Jean DUPONT signe le contrat."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        assert len(result["personnes"]) > 0

    def test_no_parties(self) -> None:
        """Vérifie qu'aucune partie n'est extraite d'un texte sans mention."""
        texte = "Le présent document traite de la procédure interne."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        assert len(result["parties"]) == 0
        assert len(result["personnes"]) == 0


class TestExtractArticles:
    """Teste l'extraction des références à des articles."""

    def test_extract_article_references(self) -> None:
        """Vérifie l'extraction de références à des articles de loi (3+ chiffres)."""
        texte = "Conformément à l'article L223-18 du Code de commerce."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        assert len(result["articles"]) > 0

    def test_extract_art_l_ref(self) -> None:
        """Vérifie l'extraction de références de type Art. L."""
        texte = "Conformément à l'Art. L223-18 du Code de commerce."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        assert len(result["articles"]) > 0

    def test_no_articles(self) -> None:
        """Vérifie qu'aucune référence n'est extraite d'un texte sans article."""
        texte = "La société est enregistrée au RCS de Paris."
        ext = EntityExtractor(texte)
        result = ext.extract_all()
        assert len(result["articles"]) == 0


class TestClauseExtractor:
    """Teste l'extraction des clauses (articles) du document."""

    def test_articles_sur_lignes(self) -> None:
        """Les articles séparés par des retours à la ligne sont extraits."""
        from extraction.clause_extractor import ClauseExtractor

        texte = (
            "STATUTS DE LA SOCIETE XYZ\n"
            "Article 1 - Forme juridique\nLa societe est une SARL.\n"
            "Article 2 - Capital social\nLe capital est fixe a 50 000 euros.\n"
        )
        clauses = ClauseExtractor(texte).extract_all()
        assert len(clauses) >= 2

    def test_articles_en_milieu_de_ligne(self) -> None:
        """Les articles sans retour à la ligne (PDF compact) sont extraits."""
        from extraction.clause_extractor import ClauseExtractor

        texte = (
            "Page 1 STATUTS DE LA SOCIETE XYZ Article 1 - Forme juridique "
            "La societe est une SARL. Article 2 - Objet social La societe a pour "
            "objet le conseil juridique. Article 5 - Capital social Le capital est "
            "fixe a 50 000 euros."
        )
        clauses = ClauseExtractor(texte).extract_all()
        titres = [c["titre"] for c in clauses]
        assert any("Forme juridique" in t for t in titres)
        assert any("Objet social" in t for t in titres)
        assert any("Capital social" in t for t in titres)
        assert len(clauses) >= 3
