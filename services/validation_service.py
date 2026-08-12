"""Service de validation humaine pour l'interface Streamlit.

Branche la classe `validation.validator.Validator` sur le rapport courant :
enregistre chaque anomalie comme "en attente", permet au juriste
d'approuver / rejeter / modifier. L'état est conservé en mémoire (session)
et persisté sur disque (`validation_sessions/`) pour survivre au
rechargement de la page et aux reprises de dossier.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Optional

from validation.validator import Validator, ValidationState

_VALIDATIONS_DIR = Path(__file__).resolve().parent.parent / "validation_sessions"

_ACTION_TO_STATE = {
    "approuver": ValidationState.APPROUVE,
    "rejeter": ValidationState.REJETE,
    "modifier": ValidationState.MODIFIE,
}


def _state_path(report_id: str) -> Path:
    return _VALIDATIONS_DIR / f"validation_{report_id}.json"


def _load_state(report_id: str) -> dict[str, dict[str, Any]]:
    path = _state_path(report_id)
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(report_id: str, state: dict[str, dict[str, Any]]) -> None:
    try:
        _VALIDATIONS_DIR.mkdir(parents=True, exist_ok=True)
        path = _state_path(report_id)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def reset_saved_state(report_id: str) -> None:
    """Supprime l'état de validation persisté pour un rapport."""
    try:
        path = _state_path(report_id)
        if path.exists():
            path.unlink()
    except Exception:
        pass


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

    new_state = validator.get_all()
    _save_state(report_id, new_state)
    return new_state


def apply_bulk_action(
    report_id: str,
    action: str,
    comment: str = "",
    current_state: Optional[dict[str, dict[str, Any]]] = None,
) -> dict[str, dict[str, Any]]:
    """
    Applique une action (approuver / rejeter) à toutes les anomalies encore
    en attente et retourne l'état complet. Permet au juriste de traiter un
    dossier en un clic, puis d'affiner au cas par cas.
    """
    validator = Validator(session_id=report_id)
    base: dict[str, dict[str, Any]] = {}
    if current_state:
        base.update(current_state)
    if base:
        validator._validations.update(base)

    if action not in ("approuver", "rejeter"):
        raise ValueError(f"Action de masse non supportée : {action}")

    for finding_id, val in list(base.items()):
        if val.get("statut") != ValidationState.EN_ATTENTE:
            continue
        if action == "approuver":
            validator.approve(finding_id, comment or "")
        else:
            validator.reject(finding_id, comment or "")
    new_state = validator.get_all()
    _save_state(report_id, new_state)
    return new_state


def merge_with_saved(report_id: str, current: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Fusionne l'état courant (re-findings "en attente") avec l'état persisté
    sur disque : les validations déjà faites sont conservées, les nouveaux
    findings sont ajoutés en "en attente".
    """
    merged = _load_state(report_id)
    for fid, val in (current or {}).items():
        merged.setdefault(fid, val)
    _save_state(report_id, merged)
    return merged


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
