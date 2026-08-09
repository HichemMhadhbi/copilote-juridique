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
    r"\b((?:SARL|SAS|SA|SCI|SASU|EURL|SNC)[A-Z ]*|[A-Z][A-Z ]{2,}(?:SARL|SAS|SA|SCI)?)\b"
)

# Mots sans valeur pour identifier une partie : formes juridiques, mots-outils,
# en-têtes de document, placeholders de modèles (« [SEUIL] », « [DATE] »...) et
# communes. Un candidat ne contenant que ces mots n'est pas une partie.
_MOTS_PARTIE_NON_INFORMATIFS: set[str] = {
    "SARL", "SAS", "SASU", "SA", "SNC", "EURL", "SCI", "SCA", "SCS",
    "LA", "LE", "LES", "DE", "DU", "DES", "D", "AU", "AUX", "ET", "A", "OU",
    "SOCIETE", "SOCIETES", "STATUTS", "PACTE", "ASSOCIES", "ASSOCIE",
    "CONSTITUTION", "CONSTITUE", "DENOMINATION", "SOCIALE", "SOCIAL",
    "SIEGE", "MAJ", "EN",
    "ARTICLES", "ARTICLE", "PRESENT", "SOUSSIGNES", "SIGNATAIRES",
    "ACTIONNAIRES", "SIGNATURE", "AVERTISSEMENT",
    "DATE", "FIXER", "LIEU", "SEUIL", "MAJORITE", "IDENTITE", "NOMBRE",
    "POURCENTAGE", "PROJET", "MODELE", "COMPLETER", "COMPLETE",
    "PRESIDENT", "GERANT", "DIRECTEUR",
    "PARIS", "LYON", "MARSEILLE", "TOULOUSE", "BORDEAUX", "LILLE", "NANTES",
    "BONDY", "BOBIGNY", "NICE", "STRASBOURG", "MONTPELLIER", "RENNES", "GRENOBLE",
    "SAINT", "SAINTE", "VIII", "ETIENNE", "DIJON", "ANGERS", "AMIENS",
    "CLERMONT", "ROUEN", "REIMS", "ORLEANS", "METZ", "TOURS", "LIMOGES",
    "PAU", "PERPIGNAN", "AVIGNON", "LAVAL", "BREST", "CANNES", "BAYONNE",
    "COLMAR", "LENS", "MULHOUSE", "DOUAI", "VALENCIENNES", "VILLE",
    # En-têtes de clauses de statuts / pactes
    "FORME", "OBJET", "DUREE", "GERANCE", "CESSION", "DECISIONS",
    "COLLECTIVES", "COMMISSAIRES", "EXERCICE", "COMPTES", "SOCIAUX",
    "PROROGATION", "DISSOLUTION", "LIQUIDATION", "CONTESTATIONS",
    "PUBLICITE", "TRANSFORMATION", "INDIVISIBILITE", "TRANSMISSION",
    "ADHESION", "CAPITAL", "APPORTS", "BENEFICES", "AFFECTATION",
    "REPARTITION", "POUVOIRS", "ENGAGEMENT", "DIVERS",
    "ACTIONS", "ACTION", "UNIQUE", "DROITS", "DROIT", "OBLIGATIONS",
    "ATTACHES", "COMMUNICATION", "COURANTS", "DECES", "INFORMATIONS",
    "INFORMATION", "CONTROLE", "CONTRÔLE", "MODIFICATION", "SOUSCRIPTION",
    "REPRESENTATION", "ENREGISTREMENT", "MOITIE", "PROPRES", "INFERIEURS",
    "FAILLITE", "PRESIDENCE", "ANTERIEUREMENT", "ORDINAIRES",
    "EXTRAORDINAIRES", "EXCEPTIONNELLES", "VOIX", "VOTE", "OPERATIONS",
    "RESOLUTIONS", "NOMINATION", "REVOCATION", "REMUNERATION", "GARANTIES",
    "DECLARATIONS", "CONDITIONS", "ENTRE", "AUCUN", "TIERS", "PRISES",
    "PRIS", "PARTS", "PART", "SOCIALES", "STATU", "ACTIONNAIRE",
    "CONVENTIONS", "CAPITAUX", "ORDI", "NAIRES", "EXTRAORDINAIRE",
    "MIS", "JOUR", "SOUSSIGNE",
    # Fragments OCR d'en-têtes de clauses
    "ARTI", "INTER", "DICTION", "MANDE", "ETE", "INFORMATTON", "CTIONNAIRE",
    "ARIA", "CLE", "E", "O", "L", "ASSOCI",
    # Communes et lieux supplémentaires
    "TUNISIE", "FRANCE", "SEINE", "VITRY", "ARIANA", "MENZAH", "EL",
    "TUNIS", "WATTRELOS", "ROUBAIX", "MEGRINE", "BOSNE", "NEW", "YORK",
    "CTOBRE",
    "SEPTEMBRE", "JANVIER", "FEVRIER", "MARS", "AVRIL", "MAI", "JUIN",
    "JUILLET", "AOUT", "OCTOBRE", "NOVEMBRE", "DECEMBRE",
    # Montants en toutes lettres / phrases d'en-tête
    "QUATRE", "VINGT", "DIX", "NEUF", "TROIS", "MILLE", "SEPT", "EUROS",
    "ANNEES", "LIBERATION", "INTERDICTION", "REPRISE", "ENGAGEMENTS",
    "ANTERIEURS", "IMMATRICULATION",
    "UN", "AS", "S", "I", "V", "TS",
    # Marqueurs binaires d'images embarquées (signatures scannées) résiduels
    # lors de la lecture brute des fichiers .doc sans Microsoft Word
    "JFIF", "JPG", "JPEG", "EXIF", "IHDR", "IEND", "PNG", "IDAT", "ICCP",
    "GAMA", "SRGB", "JVNO", "UOZD",
}

# Phrases d'en-tête de documents : un candidat partie qui les contient est un
# titre (ex. « ACTIONNAIRES ASSUFLEX SAS PROJET DE PACTE », « ASSUR TIME SAS
# MAJ STATUTS EN DATE DU »), pas un nom de partie.
_PHRASES_TITRE_NON_INFORMATIVES: set[str] = {
    "PROJET DE PACTE",
    "MAJ STATUTS EN DATE DU",
    "MAJ STATUTS",
    "STATUTS MIS A JOUR",
    "PACTE D'ACTIONNAIRES",
    "PACTE D'ASSOCIES",
    "EN DATE DU",
}

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
        """Extrait les noms de sociétés / entités.

        Les candidats qui ne contiennent aucun mot significatif (formes
        juridiques, mots-outils, en-têtes, placeholders de modèles, communes)
        sont ignorés : « PROJET DE PACTE », « [SEUIL] » ou « PARIS » ne sont
        pas des parties.
        """
        result: List[Dict[str, Any]] = []
        vus: set[str] = set()
        for m in _PATTERN_PARTIE.finditer(self._raw_text):
            nom = m.group(1).strip()
            norm = nom.upper().replace("’", "'")
            if any(phrase in norm for phrase in _PHRASES_TITRE_NON_INFORMATIVES):
                continue
            mots = re.findall(r"[A-Z0-9]+", nom.upper())
            if not any(mot not in _MOTS_PARTIE_NON_INFORMATIFS for mot in mots):
                continue
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
