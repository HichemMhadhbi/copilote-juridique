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

    def test_bulk_approuver_tout(self) -> None:
        etat = validation_service.register_report_findings(_sample_report(3))
        nouvel_etat = validation_service.apply_bulk_action(
            "rid", "approuver", comment="Validé par le cabinet", current_state=etat
        )
        assert all(v["statut"] == "approuve" for v in nouvel_etat.values())
        assert nouvel_etat["anomalie_2"]["commentaire_juriste"] == "Validé par le cabinet"

    def test_bulk_rejeter_tout(self) -> None:
        etat = validation_service.register_report_findings(_sample_report(2))
        nouvel_etat = validation_service.apply_bulk_action(
            "rid", "rejeter", comment="hors périmètre", current_state=etat
        )
        assert all(v["statut"] == "rejete" for v in nouvel_etat.values())

    def test_bulk_ne_touche_pas_les_validees(self) -> None:
        etat = validation_service.register_report_findings(_sample_report(3))
        etat = validation_service.apply_action(
            "rid", "anomalie_1", "approuver", comment="OK", current_state=etat
        )
        nouvel_etat = validation_service.apply_bulk_action(
            "rid", "approuver", comment="reste", current_state=etat
        )
        assert nouvel_etat["anomalie_1"]["statut"] == "approuve"
        assert nouvel_etat["anomalie_1"]["commentaire_juriste"] == "OK"
        assert nouvel_etat["anomalie_2"]["statut"] == "approuve"
        assert nouvel_etat["anomalie_2"]["commentaire_juriste"] == "reste"

    def test_bulk_action_inconnue(self) -> None:
        etat = validation_service.register_report_findings(_sample_report(2))
        with pytest.raises(ValueError):
            validation_service.apply_bulk_action("rid", "modifier", current_state=etat)

    def test_merge_charge_les_validations_persistees(self) -> None:
        rid = "rid-test-persist"
        validation_service.reset_saved_state(rid)
        etat = validation_service.register_report_findings(_sample_report(2))
        validation_service.apply_action(
            rid, "anomalie_1", "approuver", comment="OK", current_state=etat
        )
        # simule un rechargement : on repart de findings "en attente"
        refait = validation_service.register_report_findings(_sample_report(2))
        fusion = validation_service.merge_with_saved(rid, refait)
        assert fusion["anomalie_1"]["statut"] == "approuve"
        assert fusion["anomalie_1"]["commentaire_juriste"] == "OK"
        assert fusion["anomalie_2"]["statut"] == "en_attente"
        validation_service.reset_saved_state(rid)

    def test_reset_saved_state_efface(self) -> None:
        rid = "rid-test-reset"
        validation_service.reset_saved_state(rid)
        etat = validation_service.register_report_findings(_sample_report(1))
        validation_service.apply_action(
            rid, "anomalie_1", "approuver", comment="OK", current_state=etat
        )
        validation_service.reset_saved_state(rid)
        assert validation_service.merge_with_saved(rid, {}) == {}
