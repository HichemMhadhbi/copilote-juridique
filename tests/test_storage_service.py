"""Tests du service de persistance des rapports (storage_service).

La persistance est désactivée par défaut (SAVE_REPORTS_TO_DISK absent).
Les tests activent la variable via monkeypatch et redirigent le dossier
de sortie vers un répertoire temporaire pour rester autonomes.
"""

from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import storage_service  # noqa: E402


def _sample_report(rid: str = "abc123") -> dict:
    return {
        "rapport_id": rid,
        "niveau_risque_global": "eleve",
        "documents_analyses": [{"nom": "pacte.pdf", "type": "pacte_associes", "statut": "lu"}],
        "informations_principales": {"statut_lecture": {"pacte.pdf": "natif"}},
        "anomalies_juridiques": [{"explication": "test"}],
        "incoherences": [],
    }


def _enable_persistence(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("SAVE_REPORTS_TO_DISK", "1")
    monkeypatch.setattr(storage_service, "REPORTS_DIR", tmp_path)


class TestPersistenceDesactivee:
    """Comportement par défaut : aucune écriture sur disque."""

    def test_reports_enabled_false(self) -> None:
        assert storage_service.reports_enabled() is False

    def test_save_retourne_rien(self) -> None:
        assert storage_service.save_report(_sample_report()) == ""

    def test_list_vide(self) -> None:
        assert storage_service.list_reports() == []


class TestPersistenceActivee:
    """Cycle de vie complet : sauvegarde, liste, chargement, suppression."""

    def test_save_puis_list(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        _enable_persistence(monkeypatch, tmp_path)
        path = storage_service.save_report(_sample_report("r1"))
        assert path and os.path.basename(path) == "report_r1.json"

        reports = storage_service.list_reports()
        assert len(reports) == 1
        assert reports[0]["rapport_id"] == "r1"
        assert reports[0]["niveau_risque"] == "eleve"
        assert reports[0]["nombre_documents"] == 1
        assert reports[0]["nombre_anomalies"] == 1

    def test_regression_list_reports_pas_de_nameerror(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Le bug : `reports` n'était jamais initialisé dans list_reports()."""
        _enable_persistence(monkeypatch, tmp_path)
        storage_service.save_report(_sample_report("r1"))
        storage_service.save_report(_sample_report("r2"))
        reports = storage_service.list_reports()
        assert {r["rapport_id"] for r in reports} == {"r1", "r2"}

    def test_load(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        _enable_persistence(monkeypatch, tmp_path)
        storage_service.save_report(_sample_report("r1"))
        loaded = storage_service.load_report("r1")
        assert loaded is not None
        assert loaded["rapport_id"] == "r1"

    def test_load_introuvable(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        _enable_persistence(monkeypatch, tmp_path)
        assert storage_service.load_report("inconnu") is None

    def test_delete(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        _enable_persistence(monkeypatch, tmp_path)
        storage_service.save_report(_sample_report("r1"))
        assert storage_service.delete_report("r1") is True
        assert storage_service.list_reports() == []
        assert storage_service.delete_report("r1") is False
