"""Service de validation humaine pour l'interface Streamlit.

Branche la classe `validation.validator.Validator` sur le rapport courant :
enregistre chaque anomalie comme "en attente", permet au juriste
d'approuver / rejeter / modifier. L'état est conservé en mémoire (session),
il n'est pas persisté sur disque.
"""

from __future__ import annotations

import datetime
from typing import Any, Optional

from validation.validator import Validator, ValidationState

_ACTION_TO_STATE = {
    "approuver": ValidationState.APPROUVE,
    "rejeter": ValidationState.REJETE,
    "modifier": ValidationState.MODIFIE,
}


def _finding_id(index: int) -> str:
    """Identifiant stable d'une anomalie dans l'interface (anomalie_N)."""
    return f"anomalie_{index}"


def build_finding_ids(report: dict[str, Any]) -> list[str]:
    """Retourne la liste des identifiants de findings du rapport."""
    return [_finding_id(i) for i in range(1, len(report.get("anomalies_juridiques", [])) + 1)]


def register_report_findings(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Enregistre toutes les anomalies du rapport comme "en attente" et
    retourne l'état de validation initial.
    """
    validator = Validator(session_id=report.get("rapport_id", "session"))
    validator.register_findings(build_finding_ids(report))
    return validator.get_all()


def apply_action(
    report_id: str,
    finding_id: str,
    action: str,
    comment: str = "",
    reason: str = "",
    new_content: Optional[dict[str, Any]] = None,
    current_state: Optional[dict[str, dict[str, Any]]] = None,
) -> dict[str, dict[str, Any]]:
    """
    Apply actionne une action de validation sur un finding et retourne le nouvel état.

    L'état existant (validations déjà faites) est conservé : on repart de
    l'état courant fourni en paramètre, on applique l'action demandée puis
    on retourne l'état complet.

    Actions possibles : 'approuver', 'rejeter', 'modifier'.

    Args:
        report_id: Identifiant du rapport.
        finding_id: Identifiant du finding (ex. "anomalie_1").
        action: Action à appliquer.
        comment: Commentaire du juriste (optionnel).
        reason: Motif de rejet (requis pour 'rejeter').
        new_content: Nouveau contenu (requis pour 'modifier').
        current_state: État en mémoire (session), prioritaire sur le disque.

    Returns:
        État de validation complet (dict {finding_id: validation}).
    """
    validator = Validator(session_id=report_id)
    base: dict[str, dict[str, Any]] = {}
    if current_state:
        base.update(current_state)
    if base:
        validator._validations.update(base)

    if action == "approuver":
        validator.approve(finding_id, comment or "")
    elif action == "rejeter":
        validator.reject(finding_id, reason or "")
    elif action == "modifier":
        validator.modify(finding_id, new_content or {})
    else:
        raise ValueError(f"Action inconnue : {action}")

    return validator.get_all()


def merge_with_saved(report_id: str, current: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Retourne l'état de validation courant (la validation n'est pas persistée
    sur disque : l'état reste en mémoire pour la session en cours).
    """
    return current


def summary(report_id: str, state: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Retourne un résumé lisible de l'état de validation."""
    total = len(state)
    approuves = sum(1 for v in state.values() if v.get("statut") == ValidationState.APPROUVE)
    rejetes = sum(1 for v in state.values() if v.get("statut") == ValidationState.REJETE)
    modifies = sum(1 for v in state.values() if v.get("statut") == ValidationState.MODIFIE)
    en_attente = total - approuves - rejetes - modifies
    taux = round((approuves / total) * 100, 1) if total else 0.0
    return {
        "total": total,
        "approuves": approuves,
        "rejetes": rejetes,
        "modifies": modifies,
        "en_attente": en_attente,
        "taux_validation": taux,
    }
