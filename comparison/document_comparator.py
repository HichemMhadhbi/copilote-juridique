"""
Comparateur de documents juridiques TOP-JURIDIQUE.

Compare les données extraites de deux documents (pacte d'associés et statuts)
pour détecter les incohérences entre les parties, dates, montants et clauses.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Set, Tuple


# Mots génériques sans valeur discriminante pour l'identification d'une
# société ou d'une personne (formes juridiques, mots-outils, en-têtes).
_MOTS_GENERIQUES: Set[str] = {
    "SARL", "SAS", "SASU", "SA", "SNC", "EURL", "SCI", "SCA", "SCS",
    "LA", "LE", "LES", "DE", "DU", "DES", "D", "AU", "AUX", "ET", "A",
    "SOCIETE", "SOCIETES", "STATUTS", "PACTE", "ASSOCIES", "ASSOCIE",
    "CONSTITUTION", "CONSTITUE", "DENOMINATION", "SOCIALE", "SIEGE",
    "ARTICLES", "ARTICLE", "M", "MME", "MLLE", "MM", "MS",
}


def _tokens_significatifs(nom: str) -> Set[str]:
    """Normalise un nom et retourne ses mots significatifs (sans accents)."""
    nom = unicodedata.normalize("NFKD", nom or "").encode("ascii", "ignore").decode("utf-8")
    mots = re.findall(r"[A-Za-z0-9]+", nom.upper())
    return {m for m in mots if m not in _MOTS_GENERIQUES}


def _correspond(nom: str, noms_reference: Set[str]) -> bool:
    """True si `nom` correspond à au moins un nom de référence.

    Deux noms correspondent s'ils partagent un mot significatif commun
    (ou si l'un est inclus dans l'autre). Un nom sans mot significatif
    (ex. "SARL" seul) est considéré comme non informatif.
    """
    tokens = _tokens_significatifs(nom)
    if not tokens:
        return True
    for ref in noms_reference:
        tokens_ref = _tokens_significatifs(ref)
        if tokens_ref and (
            tokens & tokens_ref
            or tokens.issubset(tokens_ref)
            or tokens_ref.issubset(tokens)
        ):
            return True
    return False


def _cle_nom(nom: str) -> str:
    """Normalise un nom pour la comparaison orthographique.

    Enlève accents, civilités et mots génériques (SARL, M., STATUTS...)
    pour comparer uniquement la racine significative du nom.
    """
    n = unicodedata.normalize("NFKD", nom or "").encode("ascii", "ignore").decode("utf-8")
    n = n.upper()
    n = re.sub(r"\b(?:M|MME|MLLE|MAITRE)\.?\b", "", n)
    mots = re.findall(r"[A-Z0-9]+", n)
    return "".join(m for m in mots if m not in _MOTS_GENERIQUES)


def _levenshtein(a: str, b: str) -> int:
    """Distance de Levenshtein entre deux chaînes (édition minimale)."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        for j in range(1, lb + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (0 if a[i - 1] == b[j - 1] else 1))
        prev = cur
    return prev[lb]


def _noms_similaires(nom_a: str, nom_b: str) -> bool:
    """True si deux noms sont probablement le même nom avec une variante.

    Seuil conservateur (distance 1, ou similarité >= 75 % pour les noms
    longs) pour éviter les faux rapprochements (« Hichem » / « Hicham »
    oui, « Mohamed » / « Mehdi » non).
    """
    na = _cle_nom(nom_a)
    nb = _cle_nom(nom_b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    taille_max = max(len(na), len(nb))
    if taille_max < 4:
        return False
    dist = _levenshtein(na, nb)
    if dist <= 1 and taille_max >= 4:
        return True
    return taille_max >= 5 and (1 - dist / taille_max) >= 0.75


def _placeholders_date(extraction: Dict[str, Any]) -> List[str]:
    """Placeholders de type date (ex. [date], [jj/mm/aaaa]) présents dans un document."""
    result: List[str] = []
    for ph in extraction.get("entites", {}).get("placeholders", []):
        v = str(ph.get("valeur", "")).lower()
        if (
            "date" in v
            or re.search(r"\d{1,2}[\s/.\-]{1,2}\d{1,2}[\s/.\-]{1,2}\d{2,4}", v)
            or re.search(r"jj[\s/.\-]*mm|aaaa", v)
        ):
            result.append(str(ph.get("valeur", "")))
    return result


class DocumentComparator:
    """
    Compare deux extractions structurées (pacte et statuts) et produit une
    liste d'incohérences avec leur sévérité.
    """

    def __init__(
        self,
        extraction_pacte: Dict[str, Any],
        extraction_statuts: Dict[str, Any],
    ) -> None:
        """
        Args:
            extraction_pacte: Données extraites du pacte d'associés.
            extraction_statuts: Données extraites des statuts.
        """
        self._pacte = extraction_pacte
        self._statuts = extraction_statuts

    def compare_all(self) -> List[Dict[str, Any]]:
        """
        Lance l'ensemble des comparaisons et retourne les incohérences.

        Chaque incohérence est un dict avec les clés :
        - type (str) : "date", "montant", "partie", "clause", "autre"
        - severite (str) : "bloquant" | "important" | "alerte"
        - description (str) : explication du problème
        - valeur_pacte (str) : valeur dans le pacte
        - valeur_statuts (str) : valeur dans les statuts
        - document_reference (str) : document de référence (le cas échéant)
        """
        incoherences: List[Dict[str, Any]] = []
        incoherences.extend(self._compare_dates())
        incoherences.extend(self._compare_montants())
        incoherences.extend(self._compare_parties())
        incoherences.extend(self._compare_clauses())
        return incoherences

    def _compare_dates(self) -> List[Dict[str, Any]]:
        """Compare les dates extraites des deux documents."""
        incoherences: List[Dict[str, Any]] = []
        dates_pacte = self._pacte.get("entites", {}).get("dates", [])
        dates_statuts = self._statuts.get("entites", {}).get("dates", [])

        valeurs_pacte = {d["valeur"] for d in dates_pacte}
        valeurs_statuts = {d["valeur"] for d in dates_statuts}

        # Dates présentes dans un document mais absentes de l'autre
        seulement_pacte = valeurs_pacte - valeurs_statuts
        seulement_statuts = valeurs_statuts - valeurs_pacte

        ph_statuts = _placeholders_date(self._statuts)
        ph_pacte = _placeholders_date(self._pacte)

        if seulement_pacte:
            if ph_statuts:
                description = (
                    f"Le pacte mentionne la/les date(s) {', '.join(sorted(seulement_pacte))} "
                    f"mais les statuts contiennent un champ date non renseigné "
                    f"({', '.join(ph_statuts)}). À compléter."
                )
            else:
                description = (
                    f"Date(s) présente(s) dans le pacte mais absente(s) des statuts : "
                    f"{', '.join(sorted(seulement_pacte))}."
                )
            incoherences.append({
                "type": "date",
                "severite": "alerte",
                "description": description,
                "valeur_pacte": ", ".join(sorted(seulement_pacte)),
                "valeur_statuts": ", ".join(ph_statuts) if ph_statuts else "absente",
                "document_reference": "pacte_associes",
            })
        if seulement_statuts:
            if ph_pacte:
                description = (
                    f"Les statuts mentionnent la/les date(s) {', '.join(sorted(seulement_statuts))} "
                    f"mais le pacte contient un champ date non renseigné "
                    f"({', '.join(ph_pacte)}). À compléter."
                )
            else:
                description = (
                    f"Date(s) présente(s) dans les statuts mais absente(s) du pacte : "
                    f"{', '.join(sorted(seulement_statuts))}."
                )
            incoherences.append({
                "type": "date",
                "severite": "alerte",
                "description": description,
                "valeur_pacte": ", ".join(ph_pacte) if ph_pacte else "absente",
                "valeur_statuts": ", ".join(sorted(seulement_statuts)),
                "document_reference": "statuts",
            })
        return incoherences

    def _compare_montants(self) -> List[Dict[str, Any]]:
        """Compare les montants extraits des deux documents."""
        incoherences: List[Dict[str, Any]] = []
        montants_pacte = self._pacte.get("entites", {}).get("montants", [])
        montants_statuts = self._statuts.get("entites", {}).get("montants", [])

        valeurs_pacte = {m["valeur"] for m in montants_pacte}
        valeurs_statuts = {m["valeur"] for m in montants_statuts}

        if not valeurs_pacte or not valeurs_statuts:
            return incoherences

        if valeurs_pacte == valeurs_statuts:
            return incoherences

        # Un ensemble est un sous-ensemble de l'autre : simple détail en plus
        # (ex. le pacte mentionne le capital ET la valeur de la part) — pas une
        # contradiction, mais un point à vérifier.
        if valeurs_pacte.issubset(valeurs_statuts) or valeurs_statuts.issubset(valeurs_pacte):
            plus_detail = "pacte" if len(valeurs_pacte) > len(valeurs_statuts) else "statuts"
            incoherences.append({
                "type": "montant",
                "severite": "alerte",
                "description": (
                    f"Les montants sont plus détaillés dans le {plus_detail} "
                    f"(pacte : {', '.join(sorted(valeurs_pacte))} / "
                    f"statuts : {', '.join(sorted(valeurs_statuts))}) "
                    "- aucune contradiction apparente, à vérifier."
                ),
                "valeur_pacte": ", ".join(sorted(valeurs_pacte)),
                "valeur_statuts": ", ".join(sorted(valeurs_statuts)),
                "document_reference": plus_detail,
            })
        else:
            incoherences.append({
                "type": "montant",
                "severite": "bloquant",
                "description": (
                    f"Montants différents entre le pacte et les statuts : "
                    f"pacte : {', '.join(sorted(valeurs_pacte))} / "
                    f"statuts : {', '.join(sorted(valeurs_statuts))}."
                ),
                "valeur_pacte": ", ".join(sorted(valeurs_pacte)),
                "valeur_statuts": ", ".join(sorted(valeurs_statuts)),
                "document_reference": "",
            })
        return incoherences

    def _compare_parties(self) -> List[Dict[str, Any]]:
        """Compare les parties (sociétés, personnes) entre les deux documents.

        Les noms sont normalisés (accents, mots génériques tels que "SARL",
        "SOCIETE", en-têtes de document) afin d'éviter les faux positifs
        quand le même acteur est libellé différemment dans le pacte et les
        statuts (ex. "SARL TOP LEGAL CONSEIL" vs
        "STATUTS DE LA SOCIETE TOP LEGAL CONSEIL").
        """
        incoherences: List[Dict[str, Any]] = []

        def _noms_parties(extraction: Dict[str, Any]) -> Set[str]:
            noms: Set[str] = set()
            entites = extraction.get("entites", {})
            for p in entites.get("parties", []):
                noms.add(p.get("nom", ""))
            for p in entites.get("personnes", []):
                noms.add(f"{p.get('civilite', '')} {p.get('nom', '')}".strip())
            return {n for n in noms if n}

        parties_pacte = _noms_parties(self._pacte)
        parties_statuts = _noms_parties(self._statuts)

        seulement_pacte = sorted(
            n for n in parties_pacte if not _correspond(n, parties_statuts)
        )
        seulement_statuts = sorted(
            n for n in parties_statuts if not _correspond(n, parties_pacte)
        )

        # Variantes orthographiques : même nom écrit différemment (ex. « Hichem »
        # vs « Hicham »). Rapprochées en une alerte au lieu de deux fausses
        # « absences ». Le verdict reste « à vérifier ».
        similaires: List[Tuple[str, str]] = []
        restants_pacte = list(seulement_pacte)
        restants_statuts = list(seulement_statuts)
        for p in list(restants_pacte):
            for s in list(restants_statuts):
                if _noms_similaires(p, s):
                    similaires.append((p, s))
                    restants_pacte.remove(p)
                    restants_statuts.remove(s)
                    break
        for p, s in similaires:
            incoherences.append({
                "type": "partie",
                "severite": "alerte",
                "description": (
                    f"'{p}' (pacte) et '{s}' (statuts) sont probablement le même nom "
                    f"avec une variante orthographique — à vérifier."
                ),
                "valeur_pacte": p,
                "valeur_statuts": s,
                "document_reference": "",
            })

        seulement_pacte = restants_pacte
        seulement_statuts = restants_statuts

        if seulement_pacte:
            incoherences.append({
                "type": "partie",
                "severite": "important",
                "description": f"Partie(s) présente(s) dans le pacte mais absente(s) des statuts : {', '.join(seulement_pacte)}.",
                "valeur_pacte": ", ".join(seulement_pacte),
                "valeur_statuts": "absente",
                "document_reference": "pacte_associes",
            })

        if seulement_statuts:
            incoherences.append({
                "type": "partie",
                "severite": "important",
                "description": f"Partie(s) présente(s) dans les statuts mais absente(s) du pacte : {', '.join(seulement_statuts)}.",
                "valeur_pacte": "absente",
                "valeur_statuts": ", ".join(seulement_statuts),
                "document_reference": "statuts",
            })
        return incoherences

    def _compare_clauses(self) -> List[Dict[str, Any]]:
        """Compare les titres de clauses entre les deux documents."""
        incoherences: List[Dict[str, Any]] = []

        def _titres_clauses(extraction: Dict[str, Any]) -> List[str]:
            return [
                c.get("titre", "").lower().strip()
                for c in extraction.get("clauses", [])
            ]

        titres_pacte = set(_titres_clauses(self._pacte))
        titres_statuts = set(_titres_clauses(self._statuts))

        # Thèmes importants qui devraient être dans les deux
        themes_importants = [
            "agrément", "cession", "capital", "gérance", "dissolution",
            "majorité", "assemblée", "non-concurrence",
        ]
        for theme in themes_importants:
            dans_pacte = any(theme in t for t in titres_pacte)
            dans_statuts = any(theme in t for t in titres_statuts)
            if dans_pacte and not dans_statuts:
                incoherences.append({
                    "type": "clause",
                    "severite": "important",
                    "description": f"Le thème '{theme}' figure dans le pacte mais est absent des statuts.",
                    "valeur_pacte": "présent",
                    "valeur_statuts": "absent",
                    "document_reference": "statuts",
                })
            elif dans_statuts and not dans_pacte:
                incoherences.append({
                    "type": "clause",
                    "severite": "alerte",
                    "description": f"Le thème '{theme}' figure dans les statuts mais est absent du pacte.",
                    "valeur_pacte": "absent",
                    "valeur_statuts": "présent",
                    "document_reference": "pacte_associes",
                })
        return incoherences
