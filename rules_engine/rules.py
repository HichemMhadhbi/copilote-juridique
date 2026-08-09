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


def _detecter_plus_tot(texte: str) -> str:
    """Retourne la forme dont la mention est la plus précoce dans le texte.

    Les documents réels citent souvent plusieurs formes sociales (clauses de
    transformation, remarques, renvois) : la forme réellement déclarée figure
    généralement en tête de document (dénomination, « FORME »). Le simple
    « premier pattern qui matche » est donc trompeur ; on privilégie la
    mention la plus tôt dans le texte.
    """
    meilleur = None  # (forme, position)
    for pattern, forme in _FORME_PATTERNS:
        m = pattern.search(texte)
        if m and (meilleur is None or m.start() < meilleur[1]):
            meilleur = (forme, m.start())
    return meilleur[0] if meilleur else ""


def _forme_sociale(data: Dict[str, Any]) -> str:
    """Détecte la forme juridique de la société (SARL, EURL, SAS, SA...)."""
    texte = _normaliser(_texte_complet(data))
    return _detecter_plus_tot(texte)


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


def a_mecanisme_blocage(data: Dict[str, Any]) -> bool:
    """Indique si le document prévoit un mécanisme de résolution de blocage.

    Recherche dans le texte complet (normalisé) les termes médiation,
    arbitrage, conciliation ou règlement amiable.
    """
    texte = _normaliser(data.get("texte", ""))
    for clause in data.get("clauses", []):
        texte += " " + _normaliser(clause.get("contenu", ""))
    return any(
        mot in texte
        for mot in ("mediation", "arbitrage", "conciliation", "reglement amiable")
    )


def a_mecanisme_agrement(data: Dict[str, Any]) -> bool:
    """Indique si le document prévoit un mécanisme d'agrément.

    Recherche dans le texte complet (normalisé) : le terme « agrément » peut
    apparaître dans une clause dédiée ou être couvert par renvoi aux statuts
    (ex. « toute cession demeure soumise à l'agrément prévu par les statuts »).
    """
    texte = _normaliser(data.get("texte", ""))
    for clause in data.get("clauses", []):
        texte += " " + _normaliser(clause.get("contenu", ""))
    return "agrement" in texte


# ── Règles ────────────────────────────────────────────────────────────────


def check_clause_agrement(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°1 — Vérifie la présence et la conformité de la clause d'agrément.

    La clause peut être dédiée ou figurer par renvoi (loi / statuts) ; on
    recherche donc dans le texte complet et pas seulement dans les titres.
    """
    findings: List[_Finding] = []
    if a_mecanisme_agrement(extracted_data):
        return findings
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
    """Règle n°7 — Vérifie la présence d'un mécanisme en cas de blocage décisionnel.

    Recherche dans le texte complet (titres et contenus) une clause de
    médiation, d'arbitrage ou de conciliation.
    """
    findings: List[_Finding] = []
    texte_brut = extracted_data.get("texte", "")
    for clause in extracted_data.get("clauses", []):
        texte_brut += " " + clause.get("contenu", "")
    texte_brut = _normaliser(texte_brut)
    if texte_brut and not a_mecanisme_blocage({"texte": texte_brut, "clauses": []}):
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
    """Règle n°8 — Vérifie la définition des pouvoirs du gérant et sa responsabilité.

    Règle propre aux formes à gérant (SARL / EURL / SCI) : dans une SAS ou une
    SA, la direction est assurée par un président / directeur général et la
    notion de « gérant » n'est pas applicable.
    """
    findings: List[_Finding] = []
    if _forme_sociale(extracted_data) not in ("SARL", "EURL", "SCI", ""):
        return findings
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


def check_champs_a_completer(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°12 — Vérifie que le document ne contient pas de champs à compléter.

    Détecte les placeholders entre crochets comportant des lettres (ex.
    « [SEUIL] », « [MAJORITÉ À FIXER] », « [DÉNOMINATION À COMPLÉTER] »).
    Les durées entre crochets sans lettres (« [24] mois ») ne sont pas
    considérées comme des champs à compléter.
    """
    findings: List[_Finding] = []
    texte = _normaliser(extracted_data.get("texte", ""))
    for clause in extracted_data.get("clauses", []):
        texte += " " + _normaliser(clause.get("contenu", ""))
    placeholders = set(re.findall(r"\[[^\]\n]{1,40}\]", texte))
    champs = [
        p for p in placeholders
        if re.search(r"[a-zà-ÿ]", p) and not re.fullmatch(r"\[\d+\]", p)
    ]
    if champs:
        findings.append({
            "type": "clause_incomplete",
            "priorite": "alerte",
            "explication": "Champs à compléter détectés : " + ", ".join(sorted(champs)) + ".",
            "reference_juridique": "Modèle de pacte",
            "correction_recommandee": "Renseigner chaque champ avant signature (seuils, majorités, dénomination, durées...).",
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "relecture",
        })
    return findings


def check_formulations_forme(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°13 — Détecte les formulations propres à une autre forme sociale.

    Dans des statuts ou un pacte de SAS / SA, la présence des termes « parts
    sociales » ou « gérant » (propres à la SARL) révèle une incohérence de
    rédaction avec la forme sociale déclarée.
    """
    findings: List[_Finding] = []
    forme = _forme_sociale(extracted_data)
    if forme not in ("SAS", "SASU", "SA"):
        return findings
    texte = _normaliser(extracted_data.get("texte", ""))
    for clause in extracted_data.get("clauses", []):
        texte += " " + _normaliser(clause.get("contenu", ""))
    a_parts = re.search(r"part\s*s?\s*sociale", texte) is not None
    a_gerant = "gerant" in texte or "cogerant" in texte
    motifs = []
    if a_parts:
        motifs.append("« parts sociales »")
    if a_gerant:
        motifs.append("« gérant »")
    if motifs:
        findings.append({
            "type": "incohérence",
            "priorite": "alerte",
            "explication": (
                f"Terminologie propre à la SARL employée dans un document de {forme} : "
                f"{', '.join(motifs)}. Ces notions ne correspondent pas à la forme sociale "
                "(actions / président ou directeur général)."
            ),
            "reference_juridique": "Code de commerce, art. L.227-1 et s.",
            "correction_recommandee": "Remplacer la terminologie (parts sociales → actions, gérant → président / directeur général).",
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })
    return findings


def check_valorisation_sortie(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°14 — Risque futur : vérifie la définition d'une méthode de valorisation.

    Dès que le document organise une sortie / cession / rachat de parts, le prix
    doit pouvoir être déterminé objectivement (renvoi à l'art. 1843-4 C. civ,
    expert indépendant, formule de valorisation). Sans cela, tout litige sur le
    prix se règle au tribunal, ce qui constitue un risque futur réel.
    """
    findings: List[_Finding] = []
    texte = _normaliser(_texte_complet(extracted_data))
    a_sortie = any(
        mot in texte
        for mot in ("sortie", "cession", "rachat", "retrait", "vente de parts", "drag-along", "tag-along")
    )
    if not a_sortie:
        return findings
    a_valorisation = any(
        mot in texte
        for mot in (
            "valorisation", "evaluation", "expert", "1843-4", "valeur des parts",
            "prix de cession", "audit", "juste valeur",
        )
    )
    if not a_valorisation:
        findings.append({
            "type": "risque_futur",
            "priorite": "important",
            "explication": ("Le document organise une sortie ou une cession de parts mais ne définit "
                            "pas la méthode de valorisation des titres : tout désaccord sur le prix "
                            "devra être tranché judiciairement (risque futur)."),
            "reference_juridique": "Art. 1843-4 C. civ",
            "correction_recommandee": ("Définir la méthode de valorisation (renvoi à l'art. 1843-4 "
                                       "C. civ ou recours à un expert indépendant) et la procédure à "
                                       "suivre en cas de désaccord sur le prix."),
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })
    return findings


def check_clause_deces_incapacite(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°15 — Risque futur : vérifie le sort des parts en cas de décès/incapacité.

    Règle propre au pacte d'associés : les statuts couvrent en général la
    transmission par succession (L223-13 pour la SARL), mais le pacte doit
    organiser le devenir du partenaire décédé ou frappé d'incapacité
    (agrément des héritiers ou rachat forcé) pour éviter une paralysie.
    """
    findings: List[_Finding] = []
    if extracted_data.get("type_document") != "pacte_associes":
        return findings
    texte = _normaliser(_texte_complet(extracted_data))
    couvert = any(
        mot in texte
        for mot in ("deces", "deceder", "incapacite", "heritier", "succession", "dece de l'associe")
    )
    if couvert:
        return findings
    forme = _forme_sociale(extracted_data)
    article = "Art. L227-9" if forme in ("SA", "SAS", "SASU") else "Art. L223-13"
    findings.append({
        "type": "risque_futur",
        "priorite": "alerte",
        "explication": ("Le pacte ne prévoit pas le sort des parts en cas de décès ou d'incapacité "
                        "d'un associé : la société peut se retrouver bloquée avec un associé "
                        "incapable ou des héritiers imprévus."),
        "reference_juridique": article,
        "correction_recommandee": ("Prévoir le sort des parts en cas de décès ou d'incapacité "
                                   "(agrément des héritiers ou rachat forcé) et les modalités "
                                   "d'évaluation associées."),
        "document_concerne": extracted_data.get("type_document", "non spécifié"),
        "validation_requise": "juriste",
    })
    return findings


def check_clause_impaye(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°16 — Risque futur : vérifie l'existence d'une sanction en cas de non-paiement.

    Lorsque le document impose des paiements (appel de fonds, prix de cession,
    pénalités, complément d'apport), l'absence de clause de défaillance
    (mise en demeure, clause résolutoire) laisse l'associé défaillant sans
    sanction concrète.
    """
    findings: List[_Finding] = []
    texte = _normaliser(_texte_complet(extracted_data))
    a_paiement = any(
        mot in texte
        for mot in ("paiement", "appel de fonds", "contribution", "versement", "reglement du prix", "tranche", "impaye")
    )
    if not a_paiement:
        return findings
    couvert = any(
        mot in texte
        for mot in ("impaye", "non-paiement", "resolutoire", "mise en demeure", "defaut", "defaillance")
    )
    if not couvert:
        findings.append({
            "type": "risque_futur",
            "priorite": "alerte",
            "explication": ("Le document prévoit des obligations de paiement mais aucune sanction "
                            "en cas de défaillance (mise en demeure, clause résolutoire) : "
                            "l'associé défaillant n'est pas incité à exécuter."),
            "reference_juridique": "Art. 1225 C. civ",
            "correction_recommandee": ("Prévoir une mise en demeure restée sans effet dans un délai "
                                       "déterminé, puis une clause résolutoire ou une pénalité de "
                                       "retard, conformément à l'art. 1225 C. civ."),
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })
    return findings


def check_clause_confidentialite(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°17 — Risque futur : vérifie l'existence d'une clause de confidentialité.

    Dès qu'un pacte échange des informations sensibles (données financières,
    savoir-faire, stratégie, chiffre d'affaires), l'absence d'une clause de
    confidentialité laisse ces informations sans protection : la divulgation
    par un associé est alors sans sanction (risque de fuite du savoir-faire).
    """
    findings: List[_Finding] = []
    if extracted_data.get("type_document") != "pacte_associes":
        return findings
    texte = _normaliser(_texte_complet(extracted_data))
    a_infos = any(
        mot in texte
        for mot in (
            "donnees financieres", "informations financieres", "chiffre d'affaires",
            "savoir-faire", "secrets commerciaux", "informations strategiques",
            "informations privees", "strategie de la societe",
        )
    )
    if not a_infos:
        return findings
    couvert = any(
        mot in texte
        for mot in (
            "confidentialite", "secret des affaires", "discretion",
            "non-divulgation", "divulguer", "secret professionnel",
            "informations confidentielles",
        )
    )
    if not couvert:
        findings.append({
            "type": "risque_futur",
            "priorite": "alerte",
            "explication": ("Le pacte échange des informations sensibles (financières, "
                            "stratégie, savoir-faire) mais ne comporte aucune clause de "
                            "confidentialité : une divulgation par un associé resterait "
                            "sans sanction (risque futur de fuite)."),
            "reference_juridique": "Art. L151-1 C. com",
            "correction_recommandee": ("Prévoir une clause de confidentialité (obligation de "
                                       "non-divulgation, durée de l'engagement, sanctions) "
                                       "conformément au régime du secret des affaires."),
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })
    return findings


def check_clause_resiliation(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°18 — Risque futur : engagement à durée/irrévocable sans issue.

    Lorsque le pacte est conclu pour une durée déterminée ou contient des
    engagements irrévocables, il doit organiser sa propre sortie (résiliation,
    préavis, terme). Un engagement perpétuel ou sans issue verrouille les
    associés et génère un risque futur de blocage.
    """
    findings: List[_Finding] = []
    if extracted_data.get("type_document") != "pacte_associes":
        return findings
    texte = _normaliser(_texte_complet(extracted_data))
    a_engagement = any(
        mot in texte
        for mot in (
            "conclu pour une duree", "pour une duree de", "duree indeterminee",
            "duree determinee", "irrevocable", "engagement irrevocable",
            "ferme et irrevocable", "le present pacte est conclu",
        )
    )
    if not a_engagement:
        return findings
    couvert = any(
        mot in texte
        for mot in ("resiliation", "rupture", "preavis", "denonciation", "terminaison")
    )
    if not couvert:
        findings.append({
            "type": "risque_futur",
            "priorite": "alerte",
            "explication": ("Le pacte prévoit une durée ou des engagements irrévocables "
                            "mais aucune issue (résiliation, préavis, terme) : les associés "
                            "restent verrouillés et toute sortie devra être négociée "
                            "judiciairement (risque futur)."),
            "reference_juridique": "Art. 1210 C. civ",
            "correction_recommandee": ("Prévoir la durée du pacte et un mécanisme de sortie "
                                       "(résiliation avec préavis, terme, clause de survie), "
                                       "les engagements perpétuels étant prohibés (art. 1210 C. civ)."),
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })
    return findings


def check_desequilibre_pouvoirs(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°19 — Risque futur : pouvoirs unilatéraux sans protection minoritaire.

    Un droit de veto ou des droits spéciaux concentrés sur un associé créent un
    déséquilibre de gouvernance si aucune protection du minoritaire n'existe
    (tag-along, sortie conjointe, droit de sortie) : risque futur d'abus.
    """
    findings: List[_Finding] = []
    if extracted_data.get("type_document") != "pacte_associes":
        return findings
    texte = _normaliser(_texte_complet(extracted_data))
    a_pouvoir_unilateral = any(
        mot in texte
        for mot in (
            "veto", "veto exclusif", "droits speciaux", "actions de preference",
            "majorite de blocage", "pouvoir de blocage",
        )
    )
    if not a_pouvoir_unilateral:
        return findings
    protection = any(
        mot in texte
        for mot in (
            "tag-along", "tag along", "sortie conjointe", "drag-along", "drag along",
            "protection", "droit de sortie", "minoritaire",
        )
    )
    if not protection:
        findings.append({
            "type": "risque_futur",
            "priorite": "important",
            "explication": ("Le pacte concentre des pouvoirs unilatéraux (veto, droits "
                            "spéciaux) sur un associé sans aucune protection du minoritaire "
                            "(tag-along, sortie conjointe) : déséquilibre de gouvernance "
                            "et risque futur d'abus."),
            "reference_juridique": "Art. 1104 C. civ",
            "correction_recommandee": ("Équilibrer la gouvernance : prévoir des droits de "
                                       "protection du minoritaire (tag-along, sortie conjointe, "
                                       "quorum de protection), le tout de bonne foi "
                                       "(art. 1104 C. civ)."),
            "document_concerne": extracted_data.get("type_document", "non spécifié"),
            "validation_requise": "juriste",
        })
    return findings


def check_modification_statutaire(extracted_data: Dict[str, Any]) -> List[_Finding]:
    """Règle n°11 — Vérifie les mentions obligatoires d'une modification statutaire."""
    findings: List[_Finding] = []
    texte_brut = extracted_data.get("texte", "")
    for clause in extracted_data.get("clauses", []):
        texte_brut += " " + clause.get("contenu", "")
    texte_brut = _normaliser(texte_brut)
    forme = _forme_sociale(extracted_data)

    decision_extraordinaire = any(mot in texte_brut for mot in (
        "assemblee generale extraordinaire",
        "assemblee extraordinaire",
        "decision des associes",
        "decision de l'associe unique",
        "decision de la collectivite des actionnaires",
        "collectivite des actionnaires",
        "acte modifiant les statuts",
    ))
    if texte_brut and not decision_extraordinaire:
        # L'organe décisionnel d'une modification statutaire dépend de la forme :
        # SARL/EURL = décision extraordinaire des associés (L223-30),
        # SA = AGE (L225-96), SAS/SASU = décisions fixées librement par les statuts (L227-9).
        if forme in ("SARL", "EURL"):
            article_age = "Art. L223-30"
            explication = ("Aucune mention d'une assemblée générale extraordinaire : une modification "
                           "des statuts exige une décision extraordinaire des associés.")
        elif forme in ("SA",):
            article_age = "Art. L225-96"
            explication = ("Aucune mention d'une assemblée générale extraordinaire : pour une société "
                           "anonyme, la modification des statuts relève de l'assemblée générale "
                           "extraordinaire.")
        else:
            article_age = None
        if article_age is not None:
            findings.append({
                "type": "vérification",
                "priorite": "important",
                "explication": explication,
                "reference_juridique": article_age,
                "correction_recommandee": "Préciser l'organe décisionnel et la majorité requise.",
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
