"""Tests du service de validation humaine (validation_service)."""

from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import validation_service  # noqa: E402


def _sample_report(n_anomalies: int = 2) -> dict:
    return {
        "rapport_id": "rid-1",
        "anomalies_juridiques": [
            {"explication": f"anomalie {i}", "priorite": "important"}
            for i in range(1, n_anomalies + 1)
        ],
    }


class TestValidationService:
    def test_build_finding_ids(self) -> None:
        assert validation_service.build_finding_ids(_sample_report(3)) == [
            "anomalie_1",
            "anomalie_2",
            "anomalie_3",
        ]

    def test_register_met_en_attente(self) -> None:
        state = validation_service.register_report_findings(_sample_report(2))
        assert len(state) == 2
        assert all(v["statut"] == "en_attente" for v in state.values())

    def test_apply_approuver(self) -> None:
        state = validation_service.apply_action(
            "rid", "anomalie_1", "approuver", comment="OK", current_state={}
        )
        assert state["anomalie_1"]["statut"] == "approuve"
        assert state["anomalie_1"]["commentaire_juriste"] == "OK"

    def test_apply_rejeter(self) -> None:
        state = validation_service.apply_action(
            "rid", "anomalie_1", "rejeter", reason="pas pertinent", current_state={}
        )
        assert state["anomalie_1"]["statut"] == "rejete"
        assert state["anomalie_1"]["motif_rejet"] == "pas pertinent"

    def test_apply_modifier(self) -> None:
        state = validation_service.apply_action(
            "rid", "anomalie_1", "modifier", new_content={"explication": "corrige"}, current_state={}
        )
        assert state["anomalie_1"]["statut"] == "modifie"
        assert state["anomalie_1"]["nouveau_contenu"] == {"explication": "corrige"}

    def test_apply_action_inconnue(self) -> None:
        with pytest.raises(ValueError):
            validation_service.apply_action("rid", "anomalie_1", "supprimer", current_state={})

    def test_conserve_etat_existant(self) -> None:
        etat = validation_service.register_report_findings(_sample_report(2))
        nouvel_etat = validation_service.apply_action(
            "rid", "anomalie_2", "rejeter", reason="doublon", current_state=etat
        )
        # l'état de l'anomalie_1 est conservé
        assert nouvel_etat["anomalie_1"]["statut"] == "en_attente"
        assert nouvel_etat["anomalie_2"]["statut"] == "rejete"

    def test_summary(self) -> None:
        etat = validation_service.register_report_findings(_sample_report(2))
        etat = validation_service.apply_action(
            "rid", "anomalie_1", "approuver", comment="OK", current_state=etat
        )
        resume = validation_service.summary("rid", etat)
        assert resume["total"] == 2
        assert resume["approuves"] == 1
        assert resume["en_attente"] == 1
        assert resume["taux_validation"] == 50.0

    def test_summary_vide(self) -> None:
        resume = validation_service.summary("rid", {})
        assert resume["total"] == 0
        assert resume["taux_validation"] == 0.0
