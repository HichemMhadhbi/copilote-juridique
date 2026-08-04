"""
Module d'accès à la base de connaissance juridique TOP-JURIDIQUE.

La classe LegalKnowledgeBase charge les fichiers JSON présents dans
legal_kb/data/ et offre des méthodes de recherche par domaine, type de
document, mots-clés, et article.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

_KB_DIR = Path(__file__).resolve().parent / "data"


class LegalKnowledgeBase:
    """Base de connaissance juridique alimentée par des fichiers JSON."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """
        Initialise la base en chargeant tous les fichiers .json du répertoire data.

        Args:
            data_dir: Chemin vers le répertoire contenant les fichiers JSON.
                      Par défaut, utilise legal_kb/data/.
        """
        self._entries: List[Dict[str, Any]] = []
        self._data_dir = data_dir or _KB_DIR
        self._load_all()

    def _load_all(self) -> None:
        """Parcourt tous les fichiers *.json du répertoire et les charge en mémoire."""
        if not self._data_dir.exists():
            return
        for filepath in sorted(self._data_dir.glob("*.json")):
            with open(filepath, encoding="utf-8") as fh:
                data = json.load(fh)
                # Certains fichiers contiennent une liste, d'autres un objet unique
                if isinstance(data, list):
                    self._entries.extend(data)
                else:
                    self._entries.append(data)
        self._entries.sort(key=lambda e: e.get("id", ""))

    def search_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Retourne les entrées dont le domaine contient la chaîne donnée (insensible
        à la casse).

        Args:
            domain: Domaine juridique recherché (ex. "droit des sociétés").

        Returns:
            Liste des entrées correspondantes.
        """
        domain_lower = domain.lower()
        return [
            e for e in self._entries
            if domain_lower in e.get("domaine", "").lower()
        ]

    def search_by_document_type(self, doc_type: str) -> List[Dict[str, Any]]:
        """
        Retourne les entrées qui s'appliquent au type de document donné.

        Args:
            doc_type: Type de document (ex. "statuts", "pacte_associes").

        Returns:
            Liste des entrées correspondantes.
        """
        doc_lower = doc_type.lower()
        return [
            e for e in self._entries
            if any(doc_lower == t.lower() for t in e.get("types_documents_concernes", []))
        ]

    def search_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Retourne les entrées dont les mots-clés ou le titre contiennent
        au moins un des termes donnés.

        Args:
            keywords: Liste de mots-clés à rechercher.

        Returns:
            Liste des entrées pertinentes.
        """
        kw_lower = [k.lower() for k in keywords]
        results: List[Dict[str, Any]] = []
        for entry in self._entries:
            mots = [m.lower() for m in entry.get("mots_cles", [])]
            titre = entry.get("titre_texte", "").lower()
            if any(k in mots or k in titre for k in kw_lower):
                results.append(entry)
        return results

    def get_rule_for_article(self, article_id: str) -> List[Dict[str, Any]]:
        """
        Retourne les règles de contrôle associées à un article donné.

        Args:
            article_id: Identifiant de l'article (ex. "Art. L223-18").

        Returns:
            Liste des règles de contrôle.
        """
        for entry in self._entries:
            if entry.get("numero_article", "").lower() == article_id.lower():
                return entry.get("regles_controle", [])
        return []

    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Retourne l'intégralité des entrées chargées."""
        return self._entries.copy()
