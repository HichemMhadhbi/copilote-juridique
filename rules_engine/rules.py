"""
Moteur de règles de contrôle juridique TOP-JURIDIQUE.

Chaque règle est une fonction pure prenant un dictionnaire `extracted_data`
et retournant une liste de *findings* (anomalies / alertes / observations).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

# ── Structure type d'un finding ───────────────────────────────────────────
# {
#   "type": str,              # catégorie de la règle
#   "priorite": str,          # "bloquant" | "important" | "alerte"
#   "explication": str,       # description textuelle du problème
#   "reference_juridique": str,  # article de loi / source
#   "correction_recommandee": str,
#   "document_concerne": str, # "statuts" | "pacte_associes" | "les deux"
#   "validation_requise": str # "juriste" | "relecture" | "automatique"
# }
# ──────────────────────────────────────────────────────────────────────────

_Finding = Dict[str, Any]


# ── Utilitaires ───────────────────────────────────────────────────────────


def _normaliser(texte: str) -> str:
    """Normalise un texte en minuscules sans accents.

    Les extractions PDF perdent souvent les accents ('gérant' devient 'gerant').
    Toutes les comparaisons du moteur de règles passent par cette normalisation
    pour eviter les faux positifs sur les documents scannes/extraits.
    """
    if not texte:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", texte.lower())
        if unicodedata.category(c) != "Mn"
    )


def _trouver_clause(data: Dict[str, Any], motif: str) -> Optional[str]:
    """Recherche dans les clauses extraites une clause dont le titre contient *motif*."""
    clauses = data.get("clauses", [])
    motif_norm = _normaliser(motif)
    for clause in clauses:
        titre = _normaliser(clause.get("titre", ""))
        if motif_norm in titre:
            return clause.get("contenu", "")
    return None


def _extraire_articles(data: Dict[str, Any]) -> List[str]:
    """Retourne la liste des références d'articles trouvés dans le document."""
    return [r.get("reference", "") for r in data.get("entites", {}).get("articles", [])]


def _texte_complet(data: Dict[str, Any]) -> str:
    """Retourne tout le texte disponible (texte brut + contenus de clauses)."""
    morceaux: List[str] = []
    if data.get("texte"):
        morceaux.append(str(data["texte"]))
    for clause in data.get("clauses", []):
        if clause.get("contenu"):
            morceaux.append(str(clause["contenu"]))
        if clause.get("titre"):
            morceaux.append(str(clause["titre"]))
    return " ".join(morceaux)


_FORME_PATTERNS: List[tuple[Any, str]] = [
    (re.compile(r"\bsarl\b|\bs\.?\s*a\s*r\s*l\b|societe a responsabilite limitee"), "SARL"),
    (re.compile(r"\beurl\b|sarl unipersonnelle"), "EURL"),
    (re.compile(r"\bsasu\b|sas unipersonnelle"), "SASU"),
    (re.compile(r"\bsas\b|societe par actions simplifiee"), "SAS"),
    (re.compile(r"\bsociete anonyme\b|\bsa\b(?!\s*a\s*r\s*l)"), "SA"),
    (re.compile(r"\bscs\b|societe en commandite"), "SCS"),
    (re.compile(r"\bsnc\b|societe en nom collectif"), "SNC"),
]


def _forme_sociale(data: Dict[str, Any]) -> str:
    """Détecte la forme juridique de la société (SARL, EURL, SAS, SA...)."""
    texte = _normaliser(_texte_complet(data))
    for pattern, forme in _FORME_PATTERNS:
        if pattern.search(texte):
            return forme
    return ""


def _article_agrement(form: str) -> str:
    """
    Article de référence pour la clause d'agrément selon la forme sociale.

    - SARL / EURL / sociétés de personnes : L223-14 (cession de parts).
    - SA / SAS / SASU (actions non cotées) : L228-23 (agrément des actions).
    """
    if form in ("SA", "SAS", "SASU"):
        return "Art. L228-23"
    return "Art. L223-14"


def _article_decisions(form: str) -> str:
    """
    Article de référence pour les décisions / majorités selon la forme sociale.

    - SARL / EURL : L223-29 (décisions et majorités).
    - SAS / SASU : L227-9 (décisions collectives).
    - SA : L225-96 / L225-98 (assemblées générales).
    """
    if form in ("SARL", "EURL"):
        return "Art. L223-29"
    if form in ("SAS", "SASU"):
        return "Art. L227-9"
    return "Art. L225-96"


# ── Règles ────────────────────────────────────────────────────────────────


def check_clause_agrement(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°1 — Vérifie la présence et la conformité de la clause d'agrément."""
    findings: List[_Finding] = []
    clause = _trouver_clause(extracted_data, "agrément")
    if clause is None:
        forme = _forme_sociale(extracted_data)
        article = _article_agrement(forme)
        details = (
            " (cession de parts sociales, article L.223-14 du Code de commerce)" if forme in ("SARL", "EURL") else ""
        )
        findings.append({
            "type": "clause_manquante",
            "priorite": "bloquant",
            "explication": f"Aucune clause d'agrément trouvée dans le document.{details}",
            "reference_juridique": article,
            "correction_recommandee": "Ajouter une clause d'agrément précisant la majorité requise pour l'entrée d'un nouvel associé.",
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })
    return findings


def check_clause_sortie(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°2 — Vérifie la présence d'un mécanisme de sortie (drag / tag-along)."""
    findings: List[_Finding] = []
    motif_sortie = _trouver_clause(extracted_data, "sortie")
    if motif_sortie is None:
        findings.append({
            "type": "clause_manquante",
            "priorite": "important",
            "explication": "Aucune clause de sortie (drag-along / tag-along) identifiée.",
            "reference_juridique": "Art. 1103 C. civ",
            "correction_recommandee": "Envisager l'ajout d'une clause de sortie conjointe pour protéger les associés minoritaires.",
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })
    return findings


def check_droit_veto(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°3 — Vérifie l'existence et la licéité d'un droit de veto."""
    findings: List[_Finding] = []
    clause = _trouver_clause(extracted_data, "veto")
    if clause is not None:
        # Alerte si le veto semble trop large (mots indicatifs)
        if "toute decision" in _normaliser(clause):
            article = _article_decisions(_forme_sociale(extracted_data))
            findings.append({
                "type": "conformité",
                "priorite": "bloquant",
                "explication": "Le droit de veto semble couvrir 'toute décision', ce qui peut paralyser la gestion courante.",
                "reference_juridique": article,
                "correction_recommandee": "Limiter le veto aux décisions stratégiques listées dans les statuts.",
                "document_concerne": extracted_data.get("type_document", "non spécifié"),
                "validation_requise": "juriste",
            })
    return findings


def check_majorite_decisions(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°4 — Vérifie que les majorités pour les décisions importantes sont conformes."""
    findings: List[_Finding] = []
    clauses = extracted_data.get("clauses", [])
    article = _article_decisions(_forme_sociale(extracted_data))
    for clause in clauses:
        texte = _normaliser(clause.get("contenu", ""))
        if "majorite" in texte:
            if "unanimite" not in texte and "2/3" not in texte and "majorite simple" in texte:
                findings.append({
                    "type": "conformité",
                    "priorite": "important",
                    "explication": "Une décision stratégique ne devrait pas requérir seulement la majorité simple.",
                    "reference_juridique": article,
                    "correction_recommandee": "Prévoir une majorité renforcée (2/3 ou unanimité) pour les décisions stratégiques.",
                    "document_concerne": extracted_data.get("type_document", "non spécifié"),
                    "validation_requise": "relecture",
                })
    return findings


def check_clause_non_concurrence(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°5 — Évalue le risque lié à une clause de non-concurrence."""
    findings: List[_Finding] = []
    clause = _trouver_clause(extracted_data, "non-concurrence")
    if clause is not None:
        # Vérification simple de durée excessive (5 ans, en chiffres ou en lettres)
        clause_norm = _normaliser(clause)
        duree_excessive = any(
            motif in clause_norm
            for motif in ("5 ans", "5 annees", "cinq ans", "cinq annees", "duree de cinq")
        )
        if duree_excessive:
            findings.append({
                "type": "proportionnalité",
                "priorite": "important",
                "explication": "La durée de la clause de non-concurrence (5 ans) semble excessive.",
                "reference_juridique": "Art. 1103 C. civ",
                "correction_recommandee": "Réduire la durée à 2 ans maximum pour respecter le principe de proportionnalité.",
                "document_concerne": extracted_data.get("type_document", "non spécifié"),
                "validation_requise": "juriste",
            })
    return findings


def check_conflict_pacte_statuts(
    data_pacte: Dict[str, Any],
    data_statuts: Dict[str, Any],
) -> List[_Finding]:
    """Règle n°6 — Détecte les contradictions entre pacte d'associés et statuts."""
    findings: List[_Finding] = []

    def _extraire_valeurs(data: Dict[str, Any], champ: str) -> List[str]:
        """Extrait les valeurs d'un champ donné dans les clauses."""
        valeurs = set()
        for clause in data.get("clauses", []):
            contenu = _normaliser(clause.get("contenu", ""))
            titre = clause.get("titre", "")
            if _normaliser(champ) in contenu:
                valeurs.add(titre)
        return list(valeurs)

    for champ in ["agrément", "cession", "majorité"]:
        valeurs_pacte = _extraire_valeurs(data_pacte, champ)
        valeurs_statuts = _extraire_valeurs(data_statuts, champ)
        if valeurs_pacte and valeurs_statuts and valeurs_pacte != valeurs_statuts:
            findings.append({
                "type": "contradiction",
                "priorite": "bloquant",
                "explication": f"Contradiction détectée sur le sujet '{champ}' entre le pacte et les statuts.",
                "reference_juridique": "Principes généraux du droit des sociétés",
                "correction_recommandee": f"Harmoniser les dispositions relatives à {champ} dans les deux documents.",
                "document_concerne": "les deux",
                "validation_requise": "juriste",
            })
    return findings


def check_clause_blocage(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°7 — Vérifie la présence d'un mécanisme en cas de blocage décisionnel."""
    findings: List[_Finding] = []
    mediation = _trouver_clause(extracted_data, "médiation")
    arbitrage = _trouver_clause(extracted_data, "arbitrage")
    if mediation is None and arbitrage is None:
        findings.append({
            "type": "clause_manquante",
            "priorite": "important",
            "explication": "Aucun mécanisme de résolution de blocage (médiation / arbitrage) trouvé.",
            "reference_juridique": "Art. 1530 C. proc. civ",
            "correction_recommandee": "Ajouter une clause de médiation préalable et une clause compromissoire.",
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })
    return findings


def check_responsabilite_gerant(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°8 — Vérifie la définition des pouvoirs du gérant et sa responsabilité."""
    findings: List[_Finding] = []
    clauses = extracted_data.get("clauses", [])
    pouvoirs_trouves = False
    for clause in clauses:
        texte = _normaliser(clause.get("contenu", ""))
        if "pouvoir" in texte and "gerant" in texte:
            pouvoirs_trouves = True
            if "limite" not in texte and "restriction" not in texte:
                findings.append({
                    "type": "vérification",
                    "priorite": "alerte",
                    "explication": "Les pouvoirs du gérant sont mentionnés mais aucune limitation n'est précisée.",
                    "reference_juridique": "Art. L223-22",
                    "correction_recommandee": "Ajouter les limitations de pouvoirs du gérant (emprunts, cautions, cessions).",
                    "document_concerne": extracted_data.get("type_document", "non spécifié"),
                    "validation_requise": "relecture",
                })
    if not pouvoirs_trouves:
        findings.append({
            "type": "clause_manquante",
            "priorite": "bloquant",
            "explication": "Aucune définition des pouvoirs du gérant trouvée dans le document.",
            "reference_juridique": "Art. L223-18",
            "correction_recommandee": "Ajouter un article définissant les pouvoirs et les limitations du gérant.",
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })
    return findings


def check_pv_quorum(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°9 — Vérifie que le procès-verbal mentionne quorum et majorité."""
    findings: List[_Finding] = []
    texte_brut = extracted_data.get("texte", "")
    for clause in extracted_data.get("clauses", []):
        texte_brut += " " + clause.get("contenu", "")
    texte_brut = _normaliser(texte_brut)

    if texte_brut and not any(mot in texte_brut for mot in ("quorum", "majorite")):
        findings.append({
            "type": "vérification",
            "priorite": "important",
            "explication": "Le procès-verbal ne mentionne ni quorum ni majorité : impossible de vérifier "
                           "la validité des décisions prises.",
            "reference_juridique": "Art. L223-29",
            "correction_recommandee": "Indiquer le quorum constaté et la majorité requise pour chaque résolution.",
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })
    return findings


def check_pv_resolutions(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°10 — Vérifie la présence de résolutions numérotées et d'une feuille de présence."""
    findings: List[_Finding] = []
    texte_brut = extracted_data.get("texte", "")
    for clause in extracted_data.get("clauses", []):
        texte_brut += " " + clause.get("contenu", "")
    texte_brut = _normaliser(texte_brut)

    if texte_brut and "resolution" not in texte_brut:
        findings.append({
            "type": "clause_manquante",
            "priorite": "important",
            "explication": "Aucune résolution numérotée n'a été trouvée dans le procès-verbal.",
            "reference_juridique": "Art. R223-24",
            "correction_recommandee": "Numéroter chaque résolution et indiquer le résultat du vote (pour/contre/abstention).",
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })

    if texte_brut and not any(mot in texte_brut for mot in ("feuille de presence", "presents", "presence")):
        findings.append({
            "type": "vérification",
            "priorite": "alerte",
            "explication": "Aucune feuille de présence ou liste des participants mentionnée.",
            "reference_juridique": "Art. R223-24",
            "correction_recommandee": "Joindre la feuille de présence signée avec les nom, prénom et nombre de parts de chaque associé.",
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "relecture",
        })
    return findings


def check_modification_statutaire(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°11 — Vérifie les mentions obligatoires d'une modification statutaire."""
    findings: List[_Finding] = []
    texte_brut = extracted_data.get("texte", "")
    for clause in extracted_data.get("clauses", []):
        texte_brut += " " + clause.get("contenu", "")
    texte_brut = _normaliser(texte_brut)

    decision_extraordinaire = any(mot in texte_brut for mot in (
        "assemblee generale extraordinaire",
        "assemblee extraordinaire", "decision des associes",
        "decision de l'associe unique", "acte modifiant les statuts",
    ))
    if texte_brut and not decision_extraordinaire:
        findings.append({
            "type": "vérification",
            "priorite": "important",
            "explication": "Aucune mention d'une assemblée générale extraordinaire : une modification "
                           "des statuts exige une décision extraordinaire des associés.",
            "reference_juridique": "Art. L223-30",
            "correction_recommandee": "Préciser l'organe décisionnel (AGE) et la majorité requise.",
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })

    depot_formalite = any(mot in texte_brut for mot in (
        "depot au greffe", "greffe du tribunal", "greffe", "rcs", "inscription modificative", "publication",
    ))
    if texte_brut and not depot_formalite:
        findings.append({
            "type": "vérification",
            "priorite": "alerte",
            "explication": "Aucune mention des formalités de publicité (dépôt au greffe / RCS).",
            "reference_juridique": "Art. R123-102",
            "correction_recommandee": "Rappeler que la modification doit être publiée et déposée au greffe (RCS).",
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "relecture",
        })
    return findings
