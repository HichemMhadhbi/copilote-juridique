"""
Constructeur de rapports structurés pour TOP-JURIDIQUE.

Assemble les résultats de toutes les analyses (entités, incohérences,
règles juridiques, comparaisons) en un rapport JSON complet et standardisé.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, Optional

from config import Priorite


class ReportBuilder:
    """
    Construit un rapport d'analyse structuré au format dictionnaire.

    Le rapport suit le schéma défini par la spécification TOP-JURIDIQUE
    et inclut toutes les sections : entités, incohérences, anomalies,
    recommandations et validation humaine.
    """

    def __init__(self) -> None:
        """Initialise le builder avec un rapport vide."""
        self._report: dict[str, Any] = {
            "rapport_id": str(uuid.uuid4()),
            "date_analyse": datetime.datetime.now().isoformat(),
            "documents_analyses": [],
            "documents_manquants": [],
            "documents_illisibles": [],
            "informations_principales": {},
            "incoherences": [],
            "anomalies_juridiques": [],
            "clauses_a_risque": [],
            "clauses_manquantes": [],
            "ameliorations_proposees": [],
            "niveau_risque_global": "non_evalue",
            "recommandations_finales": [],
            "points_validation_humaine": [],
        }

    # ── Documents ───────────────────────────────────────────────────────────

    def set_documents_analyses(self, documents: list[dict[str, str]]) -> ReportBuilder:
        """
        Définit la liste des documents analysés.

        Args:
            documents: Liste de dicts avec au minimum {nom, type, statut}.
        """
        self._report["documents_analyses"] = documents
        return self

    def set_documents_manquants(self, documents: list[str]) -> ReportBuilder:
        """Définit la liste des documents manquants."""
        self._report["documents_manquants"] = documents
        return self

    def set_documents_illisibles(self, documents: list[str]) -> ReportBuilder:
        """Définit la liste des documents illisibles."""
        self._report["documents_illisibles"] = documents
        return self

    # ── Informations principales ────────────────────────────────────────────

    def set_informations_principales(self, infos: dict[str, Any]) -> ReportBuilder:
        """
        Définit les informations principales extraites.

        Args:
            infos: Dict avec les champs extraits (parties, dates, montants, etc.).
        """
        self._report["informations_principales"] = infos
        return self

    # ── Incohérences ───────────────────────────────────────────────────────

    def add_incoherence(self, incoherence: dict[str, str]) -> ReportBuilder:
        """
        Ajoute une incohérence détectée entre documents.

        Args:
            incoherence: Dict avec {description, document_1, document_2, champ}.
        """
        self._report["incoherences"].append(incoherence)
        return self

    def set_incoherences(self, incoherences: list[dict[str, str]]) -> ReportBuilder:
        """Définit la liste complète des incohérences."""
        self._report["incoherences"] = incoherences
        return self

    # ── Anomalies juridiques ────────────────────────────────────────────────

    def add_anomalie(self, anomalie: dict[str, Any]) -> ReportBuilder:
        """
        Ajoute une anomalie juridique détaillée.

        L'anomalie doit contenir les champs obligatoires :
        explication, nature_controle, priorite, consequence,
        source_juridique, correction_recommandee,
        documents_a_verifier, validation_requise.
        """
        anomalie_complete = self._normalize_anomalie(anomalie)
        self._report["anomalies_juridiques"].append(anomalie_complete)
        return self

    def set_anomalies(self, anomalies: list[dict[str, Any]]) -> ReportBuilder:
        """Définit la liste complète des anomalies."""
        self._report["anomalies_juridiques"] = [
            self._normalize_anomalie(a) for a in anomalies
        ]
        return self

    # ── Clauses à risque ────────────────────────────────────────────────────

    def add_clause_a_risque(self, clause: dict[str, str]) -> ReportBuilder:
        """Ajoute une clause identifiée comme à risque."""
        self._report["clauses_a_risque"].append(clause)
        return self

    def set_clauses_a_risque(self, clauses: list[dict[str, str]]) -> ReportBuilder:
        """Définit la liste complète des clauses à risque."""
        self._report["clauses_a_risque"] = clauses
        return self

    # ── Clauses manquantes ──────────────────────────────────────────────────

    def add_clause_manquante(self, clause: dict[str, str]) -> ReportBuilder:
        """Ajoute une clause absente du document analysé."""
        self._report["clauses_manquantes"].append(clause)
        return self

    def set_clauses_manquantes(self, clauses: list[dict[str, str]]) -> ReportBuilder:
        """Définit la liste complète des clauses manquantes."""
        self._report["clauses_manquantes"] = clauses
        return self

    # ── Améliorations ───────────────────────────────────────────────────────

    def add_amelioration(self, amelioration: dict[str, str]) -> ReportBuilder:
        """Ajoute une amélioration proposée."""
        self._report["ameliorations_proposees"].append(amelioration)
        return self

    def set_ameliorations(self, ameliorations: list[dict[str, str]]) -> ReportBuilder:
        """Définit la liste complète des améliorations."""
        self._report["ameliorations_proposees"] = ameliorations
        return self

    # ── Niveau de risque global ─────────────────────────────────────────────

    def set_niveau_risque_global(self, niveau: str) -> ReportBuilder:
        """
        Définit le niveau de risque global.

        Valeurs attendues: "faible", "modere", "eleve", "critique".
        """
        self._report["niveau_risque_global"] = niveau
        return self

    def compute_niveau_risque_global(self) -> ReportBuilder:
        """
        Calcule automatiquement le niveau de risque global
        en fonction des anomalies présentes.
        """
        anomalies = self._report["anomalies_juridiques"]

        if not anomalies:
            self._report["niveau_risque_global"] = "faible"
            return self

        has_bloquant = any(
            a.get("priorite") == Priorite.BLOQUANT.value for a in anomalies
        )
        has_important = any(
            a.get("priorite") == Priorite.IMPORTANT.value for a in anomalies
        )

        if has_bloquant:
            self._report["niveau_risque_global"] = "critique"
        elif has_important:
            self._report["niveau_risque_global"] = "eleve"
        elif len(anomalies) > 3:
            self._report["niveau_risque_global"] = "modere"
        else:
            self._report["niveau_risque_global"] = "faible"

        return self

    # ── Recommandations finales ─────────────────────────────────────────────

    def add_recommandation(self, recommandation: dict[str, str]) -> ReportBuilder:
        """Ajoute une recommandation finale."""
        self._report["recommandations_finales"].append(recommandation)
        return self

    def set_recommandations(self, recommandations: list[dict[str, str]]) -> ReportBuilder:
        """Définit la liste complète des recommandations."""
        self._report["recommandations_finales"] = recommandations
        return self

    # ── Validation humaine ──────────────────────────────────────────────────

    def add_point_validation(self, point: dict[str, str]) -> ReportBuilder:
        """Ajoute un point nécessitant une validation humaine."""
        self._report["points_validation_humaine"].append(point)
        return self

    def set_points_validation(self, points: list[dict[str, str]]) -> ReportBuilder:
        """Définit la liste complète des points de validation."""
        self._report["points_validation_humaine"] = points
        return self

    # ── Construction finale ─────────────────────────────────────────────────

    def build(self) -> dict[str, Any]:
        """
        Retourne le rapport construit.

        Effectue un calcul automatique du risque global si non défini.
        """
        if self._report["niveau_risque_global"] == "non_evalue":
            self.compute_niveau_risque_global()
        return self._report

    def reset(self) -> ReportBuilder:
        """Réinitialise le builder pour construire un nouveau rapport."""
        self.__init__()
        return self

    # ── Méthodes privées ────────────────────────────────────────────────────

    @staticmethod
    def _normalize_anomalie(anomalie: dict[str, Any]) -> dict[str, Any]:
        """
        Normalise un dictionnaire d'anomalie en s'assurant
        que tous les champs obligatoires sont présents.
        """
        champs_defaut = {
            "explication": "",
            "nature_controle": "",
            "priorite": Priorite.ALERTE.value,
            "consequence": "",
            "source_juridique": "",
            "correction_recommandee": "",
            "documents_a_verifier": [],
            "validation_requise": "oui",
        }
        anomalie_normalisee = champs_defaut.copy()
        anomalie_normalisee.update(anomalie)
        return anomalie_normalisee
