"""Tests de la normalisation des références juridiques (legal_source_service).

Vérifie la forme canonique Légifrance : « Art. L. 227-1 et s. » doit devenir
« L227-1 » (sans point ni espace) afin que la recherche EXACTE de l'API
PISTE puisse retrouver l'article. Aucun appel réseau : tests hors ligne.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.legal_source_service import legifrance_search_url, normalize_reference


class TestNormalizeReference:
    def test_article_avec_et_s(self) -> None:
        """Le suffixe « et s. » doit être ignoré."""
        assert normalize_reference("Art. L.227-1 et s.") == "L227-1"

    def test_article_avec_source_complete(self) -> None:
        assert normalize_reference("Code de commerce, art. L.227-1 et s.") == "L227-1"

    def test_point_apres_lettre_supprime(self) -> None:
        """« L.227-1 » et « L227-1 » doivent désigner le même article."""
        assert normalize_reference("L.227-1") == "L227-1"

    def test_numero_compose(self) -> None:
        """Les numéros composés (L. 225-18-1) ne sont pas tronqués."""
        assert normalize_reference("L. 225-18-1") == "L225-18-1"

    def test_article_civil_seul(self) -> None:
        assert normalize_reference("1103 C. civ") == "1103"

    def test_article_sans_point(self) -> None:
        assert normalize_reference("L223-14") == "L223-14"

    def test_article_deja_canonique(self) -> None:
        assert normalize_reference("Art. L227-9") == "L227-9"

    def test_chaine_vide(self) -> None:
        assert normalize_reference("") == ""
        assert normalize_reference(None) == ""


class TestLegifranceUrl:
    def test_url_recherche_normalisee(self) -> None:
        url = legifrance_search_url("Code de commerce, art. L.227-1 et s.")
        assert "L227-1" in url

    def test_url_sans_reference(self) -> None:
        assert legifrance_search_url("") == ""
