"""
Module de validation humaine pour TOP-JURIDIQUE.

Gère l'état de validation de chaque recommandation/anomalie
et permet aux juristes d'approuver, rejeter ou modifier les résultats.
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Optional


class ValidationState:
    """État de validation d'un finding individuel."""
    EN_ATTENTE = "en_attente"
    APPROUVE = "approuve"
    REJETE = "rejete"
    MODIFIE = "modifie"


class Validator:
    """
    Gestionnaire de validation pour les résultats d'analyse.

    Permet aux juristes de valider, rejeter ou modifier chaque
    finding (anomalie, incohérence, recommandation) du rapport.
    """

    def __init__(self, session_id: str, storage_path: Optional[str] = None) -> None:
        """
        Initialise le validateur.

        Args:
            session_id: Identifiant unique de la session d'analyse.
            storage_path: Chemin optionnel pour persister les résultats.
                          Si None, utilisation de la mémoire uniquement.
        """
        self._session_id = session_id
        self._storage_path = storage_path
        self._validations: dict[str, dict[str, Any]] = {}

        # Chargement depuis le disque si disponible
        if storage_path:
            self._load_from_disk()

    # ── Gestion des validations ─────────────────────────────────────────────

    def approve(
        self, finding_id: str, jurist_comment: str = ""
    ) -> dict[str, Any]:
        """
        Approuve un finding.

        Args:
            finding_id: Identifiant du finding à approuver.
            jurist_comment: Commentaire optionnel du juriste.

        Returns:
            État de validation mis à jour.
        """
        validation = {
            "finding_id": finding_id,
            "statut": ValidationState.APPROUVE,
            "date_validation": datetime.datetime.now().isoformat(),
            "commentaire_juriste": jurist_comment,
            "action": "approuve",
        }
        self._validations[finding_id] = validation
        self._save_to_disk()
        return validation

    def reject(
        self, finding_id: str, reason: str = ""
    ) -> dict[str, Any]:
        """
        Rejette un finding.

        Args:
            finding_id: Identifiant du finding à rejeter.
            reason: Motif du rejet.

        Returns:
            État de validation mis à jour.
        """
        validation = {
            "finding_id": finding_id,
            "statut": ValidationState.REJETE,
            "date_validation": datetime.datetime.now().isoformat(),
            "motif_rejet": reason,
            "action": "rejete",
        }
        self._validations[finding_id] = validation
        self._save_to_disk()
        return validation

    def modify(
        self, finding_id: str, new_content: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Modifie le contenu d'un finding.

        Args:
            finding_id: Identifiant du finding à modifier.
            new_content: Nouveau contenu remplaçant l'original.

        Returns:
            État de validation mis à jour avec le nouveau contenu.
        """
        validation = {
            "finding_id": finding_id,
            "statut": ValidationState.MODIFIE,
            "date_validation": datetime.datetime.now().isoformat(),
            "nouveau_contenu": new_content,
            "action": "modifie",
        }
        self._validations[finding_id] = validation
        self._save_to_disk()
        return validation

    # ── Consultation ────────────────────────────────────────────────────────

    def get_pending(self) -> list[dict[str, Any]]:
        """
        Retourne la liste des findings en attente de validation.

        Returns:
            Liste des validations avec statut "en_attente".
        """
        pending = [
            v for v in self._validations.values()
            if v.get("statut") == ValidationState.EN_ATTENTE
        ]
        return pending

    def get_all(self) -> dict[str, dict[str, Any]]:
        """Retourne toutes les validations de la session."""
        return self._validations.copy()

    def get_status(self, finding_id: str) -> Optional[str]:
        """
        Retourne le statut d'un finding donné.

        Args:
            finding_id: Identifiant du finding.

        Returns:
            Statut du finding ou None si non trouvé.
        """
        validation = self._validations.get(finding_id)
        if validation:
            return validation.get("statut")
        return None

    def register_findings(self, finding_ids: list[str]) -> None:
        """
        Enregistre une liste de findings comme en attente de validation.

        Args:
            finding_ids: Liste des identifiants à enregistrer.
        """
        for fid in finding_ids:
            if fid not in self._validations:
                self._validations[fid] = {
                    "finding_id": fid,
                    "statut": ValidationState.EN_ATTENTE,
                    "date_enregistrement": datetime.datetime.now().isoformat(),
                    "action": "en_attente",
                }
        self._save_to_disk()

    # ── Résumé ──────────────────────────────────────────────────────────────

    def get_summary(self) -> dict[str, Any]:
        """
        Génère un résumé de l'état de validation.

        Returns:
            Dictionnaire contenant les compteurs et le taux de validation.
        """
        total = len(self._validations)
        if total == 0:
            return {
                "session_id": self._session_id,
                "total_findings": 0,
                "approuves": 0,
                "rejetes": 0
            }

        approuves = sum(
            1 for v in self._validations.values()
            if v.get("statut") == ValidationState.APPROUVE
        )
        rejetes = sum(
            1 for v in self._validations.values()
            if v.get("statut") == ValidationState.REJETE
        )
        modifies = sum(
            1 for v in self._validations.values()
            if v.get("statut") == ValidationState.MODIFIE
        )
        en_attente = total - approuves - rejetes - modifies

        return {
            "session_id": self._session_id,
            "total_findings": total,
            "approuves": approuves,
            "rejetes": rejetes,
            "modifies": modifies,
            "en_attente": en_attente,
            "taux_validation": round(approuves / total * 100, 1) if total > 0 else 0,
            "taux_rejet": round(rejetes / total * 100, 1) if total > 0 else 0,
        }

    # ── Persistance ─────────────────────────────────────────────────────────

    def _save_to_disk(self) -> None:
        """Sauvegarde l'état des validations sur disque."""
        if not self._storage_path:
            return
        if os.getenv("SAVE_REPORTS_TO_DISK", "0").strip().lower() not in ("1", "true", "yes", "on"):
            return

        storage_dir = Path(self._storage_path)
        storage_dir.mkdir(parents=True, exist_ok=True)

        filepath = storage_dir / f"validation_{self._session_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._validations, f, ensure_ascii=False, indent=2)

    def _load_from_disk(self) -> None:
        """Charge l'état des validations depuis le disque."""
        if not self._storage_path:
            return
        if os.getenv("SAVE_REPORTS_TO_DISK", "0").strip().lower() not in ("1", "true", "yes", "on"):
            return

        filepath = Path(self._storage_path) / f"validation_{self._session_id}.json"
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                self._validations = json.load(f)

    def export_results(self) -> dict[str, Any]:
        """
        Exporte les résultats de validation au format dictionnaire.

        Returns:
            Dictionnaire complet avec résumé et détails.
        """
        return {
            "session_id": self._session_id,
            "resume": self.get_summary(),
            "validations": self._validations,
        }
