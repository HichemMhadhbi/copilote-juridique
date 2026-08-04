"""
Extracteur de clauses juridiques TOP-JURIDIQUE.

Analyse le texte brut d'un document et isole les clauses (articles) à l'aide
de motifs regex typiques des documents juridiques français.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

_PATTERN_ARTICLE = re.compile(
    r"(?:^|\n)\s*(?:Article|ART\.?)\s+[IVXLCDM\d]+[.\-–—\s]*(.*?)(?=\n\s*(?:Article|ART\.?)|\Z)",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)

_PATTERN_TITRE = re.compile(
    r"(?:^|\n)\s*(TITRE\s+[IVXLCDM]+[.\-–—\s]*.*?)(?=\n\s*(?:TITRE|Article|ART\.?)|\Z)",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)

_PATTERN_CHAPITRE = re.compile(
    r"(?:^|\n)\s*(Chapitre\s+[IVXLCDM\d]+[.\-–—\s]*.*?)(?=\n\s*(?:Chapitre|TITRE|Article|ART\.?)|\Z)",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)

# Marquage "Article N" apparaissant en milieu de ligne (PDF sans retours propres).
_RE_MIDLINE_ARTICLE = re.compile(
    r"(?<=\S)\s+(?=(?:Article|ART\.?)\s+[IVXLCDM\d]+[.\-–—\s])",
    re.IGNORECASE,
)


def _normalize_article_markers(raw_text: str) -> str:
    """Insère un retour à la ligne avant chaque marqueur 'Article N' en milieu de ligne."""
    return _RE_MIDLINE_ARTICLE.sub("\n", raw_text)


class ClauseExtractor:
    """
    Extrait les clauses structurées d'un texte juridique brut.
    """

    def __init__(self, raw_text: str) -> None:
        """
        Args:
            raw_text: Texte brut du document juridique.
        """
        self._raw_text = _normalize_article_markers(raw_text)

    def extract_all(self) -> List[Dict[str, Any]]:
        """
        Extrait toutes les clauses (articles, titres, chapitres) et les retourne
        sous forme de dictionnaires ordonnés par position d'apparition.

        Chaque clause possède les clés :
        - "titre"        : intitulé de l'article / section
        - "contenu"      : texte complet de la clause
        - "type"         : "article" | "titre" | "chapitre"
        - "position"     : index de début dans le texte original
        """
        clauses: List[Dict[str, Any]] = []

        # Extraction des articles (les plus fins en premier)
        for match in _PATTERN_ARTICLE.finditer(self._raw_text):
            titre = match.group(1).strip().split("\n")[0][:120]
            clauses.append({
                "titre": titre.strip(".-–— "),
                "contenu": match.group(1).strip(),
                "type": "article",
                "position": match.start(),
            })

        # Extraction des chapitres
        for match in _PATTERN_CHAPITRE.finditer(self._raw_text):
            titre = match.group(1).strip().split("\n")[0][:120]
            clauses.append({
                "titre": titre.strip(".-–— "),
                "contenu": match.group(1).strip(),
                "type": "chapitre",
                "position": match.start(),
            })

        # Extraction des titres
        for match in _PATTERN_TITRE.finditer(self._raw_text):
            titre = match.group(1).strip().split("\n")[0][:120]
            clauses.append({
                "titre": titre.strip(".-–— "),
                "contenu": match.group(1).strip(),
                "type": "titre",
                "position": match.start(),
            })

        # Tri par position d'apparition dans le texte
        clauses.sort(key=lambda c: c["position"])
        return clauses
