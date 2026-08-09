"""Service de persistance des rapports d'analyse TOP-JURIDIQUE.

Sauvegarde chaque rapport en JSON dans le dossier `reports/` (à la racine
du projet) pour pouvoir le retrouver, le relire ou le ré-analyser plus tard.

La persistance sur disque est désactivée par défaut : aucune analyse ne
génère de fichier automatiquement. Pour la réactiver, définir la variable
d'environnement `SAVE_REPORTS_TO_DISK=1` avant de lancer l'application.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def _reports_enabled() -> bool:
    """True si la persistance des rapports sur disque est activée."""
    return os.getenv("SAVE_REPORTS_TO_DISK", "0").strip().lower() in ("1", "true", "yes", "on")


def reports_enabled() -> bool:
    """API publique : indique si la persistance des rapports est activée."""
    return _reports_enabled()


def _reports_dir() -> Path:
    """Retourne le dossier des rapports (créé si nécessaire)."""
    if _reports_enabled():
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def _report_path(report_id: str) -> Path:
    return _reports_dir() / f"report_{report_id}.json"


def save_report(report: dict[str, Any]) -> str:
    """
    Sauvegarde un rapport en JSON (uniquement si la persistance est
    activée via `SAVE_REPORTS_TO_DISK`).

    Args:
        report: Rapport d'analyse (dictionnaire).

    Returns:
        Chemin du fichier sauvegardé, ou chaîne vide si la persistance
        est désactivée.
    """
    if not _reports_enabled():
        return ""
    report_id = str(report.get("rapport_id") or "unknown")
    path = _report_path(report_id)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return str(path)


def load_report(report_id: str) -> Optional[dict[str, Any]]:
    """
    Charge un rapport par son identifiant.

    Args:
        report_id: Identifiant du rapport.

    Returns:
        Rapport (dict) ou None si introuvable.
    """
    path = _report_path(report_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        logger.exception("Lecture impossible du rapport %s", report_id)
        return None


def list_reports() -> list[dict[str, Any]]:
    """
    Liste les rapports sauvegardés (du plus récent au plus ancien).

    Returns:
        Liste de métadonnées : {rapport_id, date_analyse, niveau_risque,
        nombre_documents, nom_fichiers, chemin}.
    """
    if not _reports_enabled() or not REPORTS_DIR.exists():
        return []
    reports: list[dict[str, Any]] = []
    for path in sorted(REPORTS_DIR.glob("report_*.json"), reverse=True):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue
        docs = data.get("documents_analyses", [])
        infos = data.get("informations_principales", {})
        reports.append({
            "rapport_id": data.get("rapport_id", path.stem),
            "date_analyse": data.get("date_analyse", ""),
            "niveau_risque": data.get("niveau_risque_global", "non_evalue"),
            "nombre_documents": len(docs),
            "nom_fichiers": [d.get("nom", "") for d in docs if isinstance(d, dict)],
            "nombre_anomalies": len(data.get("anomalies_juridiques", [])),
            "nombre_incoherences": len(data.get("incoherences", [])),
            "statut_ocr": infos.get("statut_lecture", {}),
            "chemin": str(path),
        })
    return reports


def delete_report(report_id: str) -> bool:
    """Supprime un rapport sauvegardé. Retourne True si supprimé."""
    path = _report_path(report_id)
    if path.exists():
        try:
            path.unlink()
            return True
        except OSError:
            logger.exception("Suppression impossible de %s", report_id)
    return False
