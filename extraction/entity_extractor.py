"""
Extracteur d'entités juridiques TOP-JURIDIQUE.

Identifie dans un texte brut les dates, montants, noms de parties,
références d'articles et autres entités pertinentes pour l'analyse.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# ── Patterns de reconnaissance ────────────────────────────────────────────

_PATTERN_DATE_ISO = re.compile(
    r"\b(\d{2}/\d{2}/\d{4})\b"
)

_PATTERN_DATE_LONG = re.compile(
    r"\ble\s+(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|"
    r"juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+(\d{4})\b",
    re.IGNORECASE,
)

_PATTERN_MONTANT = re.compile(
    r"\b(\d[\d\s]*\d?)\s*(euros?|€)\b",
    re.IGNORECASE,
)

_PATTERN_MONTANT_LONG = re.compile(
    r"montant\s+(?:de\s+)?(\d[\d\s]*\d?)\s*(euros?|€)",
    re.IGNORECASE,
)

_PATTERN_PARTIE = re.compile(
    r"\b((?:SARL|SAS|SA|SCI|SASU|EURL|SNC)[A-Z\s]*|[A-Z][A-Z\s]{2,}(?:SARL|SAS|SA|SCI)?)\b"
)

_PATTERN_PERSONNE = re.compile(
    r"\b(M\.|Mme\.?|Maître|Maître)\s+([A-Z][A-Za-zéèêëàâùûôöçï\-]+)\b"
)

_PATTERN_ARTICLE_REF = re.compile(
    r"(?:Art(?:icle)?\.?\s*)(L\.?\s*)?(\d{3,}(?:-\d{1,3})?(?:-[a-z]+)?)",
    re.IGNORECASE,
)


class EntityExtractor:
    """
    Extrait les entités nommées d'un texte juridique brut.
    """

    def __init__(self, raw_text: str) -> None:
        """
        Args:
            raw_text: Texte brut du document.
        """
        self._raw_text = raw_text

    def extract_all(self) -> Dict[str, Any]:
        """
        Lance toutes les extractions et retourne un dictionnaire structuré.

        Retourne :
        {
            "dates": [{"valeur": "25/12/2024", "position": 123}, ...],
            "montants": [{"valeur": "50000", "devise": "euros", "position": 456}, ...],
            "parties": [{"nom": "SARL EXEMPLE", "type": "societe", "position": 78}, ...],
            "personnes": [{"civilite": "M.", "nom": "DUPONT", "position": 90}, ...],
            "articles": [{"reference": "L223-18", "position": 200}, ...],
        }
        """
        return {
            "dates": self._extract_dates(),
            "montants": self._extract_montants(),
            "parties": self._extract_parties(),
            "personnes": self._extract_personnes(),
            "articles": self._extract_articles(),
        }

    def _extract_dates(self) -> List[Dict[str, Any]]:
        """Extrait les dates au format JJ/MM/AAAA et 'le JJ mois AAAA'."""
        result: List[Dict[str, Any]] = []
        for m in _PATTERN_DATE_ISO.finditer(self._raw_text):
            result.append({"valeur": m.group(1), "position": m.start()})
        for m in _PATTERN_DATE_LONG.finditer(self._raw_text):
            jour, mois_text, annee = m.group(1), m.group(2), m.group(3)
            # Normalisation mesis
            mois_map = {
                "janvier": "01", "février": "02", "fevrier": "02",
                "mars": "03", "avril": "04", "mai": "05", "juin": "06",
                "juillet": "07", "août": "08", "aout": "08",
                "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12",
                "decembre": "12",
            }
            mois = mois_map.get(mois_text.lower(), "??")
            result.append({
                "valeur": f"{jour.zfill(2)}/{mois}/{annee}",
                "position": m.start(),
            })
        return result

    def _extract_montants(self) -> List[Dict[str, Any]]:
        """Extrait les montants en euros."""
        result: List[Dict[str, Any]] = []
        vus: set[str] = set()
        for m in _PATTERN_MONTANT.finditer(self._raw_text):
            cle = f"{m.start()}_{m.group(1)}"
            if cle not in vus:
                vus.add(cle)
                result.append({
                    "valeur": m.group(1).replace(" ", ""),
                    "devise": "EUR",
                    "position": m.start(),
                })
        return result

    def _extract_parties(self) -> List[Dict[str, Any]]:
        """Extrait les noms de sociétés / entités."""
        result: List[Dict[str, Any]] = []
        vus: set[str] = set()
        for m in _PATTERN_PARTIE.finditer(self._raw_text):
            nom = m.group(1).strip()
            if len(nom) > 3 and nom not in vus:
                vus.add(nom)
                result.append({
                    "nom": nom,
                    "type": "societe",
                    "position": m.start(),
                })
        return result

    def _extract_personnes(self) -> List[Dict[str, Any]]:
        """Extrait les mentions de personnes physiques (M., Mme, Maître)."""
        result: List[Dict[str, Any]] = []
        vus: set[str] = set()
        for m in _PATTERN_PERSONNE.finditer(self._raw_text):
            cle = f"{m.group(1)}_{m.group(2)}"
            if cle not in vus:
                vus.add(cle)
                result.append({
                    "civilite": m.group(1),
                    "nom": m.group(2),
                    "position": m.start(),
                })
        return result

    def _extract_articles(self) -> List[Dict[str, Any]]:
        """Extrait les références d'articles de loi ou de contrat."""
        result: List[Dict[str, Any]] = []
        vus: set[str] = set()
        for m in _PATTERN_ARTICLE_REF.finditer(self._raw_text):
            ref = (m.group(1) or "") + m.group(2)
            if ref not in vus:
                vus.add(ref)
                result.append({
                    "reference": ref,
                    "position": m.start(),
                })
        return result
