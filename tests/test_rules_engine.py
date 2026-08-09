"""
Tests pytest pour le moteur de règles juridiques.

Vérifie la détection des clauses obligatoires, des anomalies
et le fonctionnement global du rule_checker.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rules_engine.rules import (
    check_clause_agrement,
    check_clause_sortie,
    check_clause_confidentialite,
    check_clause_deces_incapacite,
    check_clause_impaye,
    check_clause_resiliation,
    check_desequilibre_pouvoirs,
    check_droit_veto,
    check_majorite_decisions,
    check_clause_non_concurrence,
    check_conflict_pacte_statuts,
    check_clause_blocage,
    check_responsabilite_gerant,
    check_clause_deces_incapacite,
    check_clause_impaye,
    check_valorisation_sortie,
    _forme_sociale,
    _article_agrement,
    _article_decisions,
)
from rules_engine.rule_checker import RuleChecker


def _make_data(clauses=None, type_doc="pacte_associes"):
    """Helper pour créer des données extraites."""
    return {
        "type_document": type_doc,
        "clauses": [{"titre": c, "contenu": c, "position": 0} for c in (clauses or [])],
        "entites": {"articles": [], "dates": [], "montants": [], "parties": [], "personnes": []},
    }


class TestCheckClauseAgrementPresent:
    """Teste la détection d'une clause d'agrément présente."""

    def test_clause_agrement_found(self) -> None:
        """Vérifie qu'aucune anomalie n'est levée si la clause existe."""
        data = _make_data(clauses=["Clause d'agrément — Toute cession doit être approuvée"])
        result = check_clause_agrement(data)
        assert len(result) == 0, "La clause d'agrément est présente, aucune anomalie attendue."

    def test_clause_agrement_with_synonym(self) -> None:
        """Vérifie que les synonymes de clause d'agrément sont reconnus."""
        data = _make_data(clauses=["Le droit d'agrément est exercé par les associés majoritaires"])
        result = check_clause_agrement(data)
        assert len(result) == 0


class TestCheckClauseAgrementAbsent:
    """Teste la détection d'une clause d'agrément absente."""

    def test_no_agrement_clause(self) -> None:
        """Vérifie qu'une anomalie est levée si la clause est absente."""
        data = _make_data(clauses=["Article 1 — Objet", "Article 2 — Capital"])
        result = check_clause_agrement(data)
        assert len(result) > 0, "La clause d'agrément est absente, une anomalie attendue."
        assert result[0]["priorite"] == "bloquant"
        assert "agrément" in result[0]["explication"].lower() or "agr" in result[0]["explication"].lower()

    def test_empty_clauses(self) -> None:
        """Vérifie qu'un document sans clauses déclenche l'anomalie."""
        data = _make_data(clauses=[])
        result = check_clause_agrement(data)
        assert len(result) > 0


class TestCheckClauseSortie:
    """Teste la détection des clauses de sortie."""

    def test_tag_along_present(self) -> None:
        """Vérifie qu'aucune anomalie n'est levée si tag-along est présent."""
        data = _make_data(clauses=["Clause de sortie — tag-along pour les associés minoritaires"])
        result = check_clause_sortie(data)
        assert len(result) == 0

    def test_drag_along_present(self) -> None:
        """Vérifie la détection du drag-along via la clause de sortie."""
        data = _make_data(clauses=["Clause de sortie — drag-along en cas de vente majoritaire"])
        result = check_clause_sortie(data)
        assert len(result) == 0

    def test_no_sortie_clause(self) -> None:
        """Vérifie l'anomalie en l'absence de clause de sortie."""
        data = _make_data(clauses=["Article 1 — Objet"])
        result = check_clause_sortie(data)
        assert len(result) > 0
        assert result[0]["priorite"] == "important"


class TestCheckConflictPacteStatuts:
    """Teste la détection d'incohérences entre pacte et statuts."""

    def test_no_conflict(self) -> None:
        """Vérifie qu'aucune anomalie n'est levée en l'absence de conflit."""
        data_pacte = _make_data(clauses=["Clause d'agrément — majorité simple"])
        data_statuts = _make_data(clauses=["Clause d'agrément — majorité simple"], type_doc="statuts")
        result = check_conflict_pacte_statuts(data_pacte, data_statuts)
        # Pas de conflit si les clauses sont identiques
        contradictions = [f for f in result if f["type"] == "contradiction"]
        assert len(contradictions) == 0

    def test_conflict_detected(self) -> None:
        """Vérifie la détection d'un conflit entre pacte et statuts."""
        data_pacte = _make_data(clauses=["Clause d'agrément — unanimité requise"])
        data_statuts = _make_data(clauses=["Clause d'agrément — majorité simple"], type_doc="statuts")
        result = check_conflict_pacte_statuts(data_pacte, data_statuts)
        contradictions = [f for f in result if f["type"] == "contradiction"]
        assert len(contradictions) > 0
        assert contradictions[0]["priorite"] == "bloquant"


class TestRuleCheckerFullRun:
    """Teste l'exécution complète du moteur de règles."""

    def test_run_all_finds_issues(self) -> None:
        """Vérifie le fonctionnement complet sur un pacte avec anomalies."""
        pacte_data = _make_data(
            clauses=["Article 1 — Objet", "Article 2 — Capital"],
            type_doc="pacte_associes",
        )
        statuts_data = _make_data(
            clauses=["Article 1 — Objet", "Article 2 — Capital"],
            type_doc="statuts",
        )
        checker = RuleChecker(pacte_data, statuts_data)
        result = checker.run_all_with_stats()

        assert "findings" in result
        assert "total" in result
        assert result["total"] > 0

    def test_run_all_compliant(self) -> None:
        """Vérifie qu'un document conforme génère moins d'anomalies."""
        pacte_data = _make_data(
            clauses=[
                "Clause d'agrément — cession contrôlée",
                "Clause de sortie — tag-along",
                "Clause de médiation — résolution des conflits",
                "Clause de non-concurrence — durée 2 ans",
                "Pouvoirs du gérant — limités aux actes courants",
            ],
            type_doc="pacte_associes",
        )
        statuts_data = _make_data(
            clauses=[
                "Clause d'agrément — cession contrôlée",
                "Pouvoirs du gérant — définis",
            ],
            type_doc="statuts",
        )
        checker = RuleChecker(pacte_data, statuts_data)
        result = checker.run_all_with_stats()

        # Un document bien rédigé devrait avoir moins de findings bloquants
        bloquants = [f for f in result["findings"] if f.get("priorite") == "bloquant"]
        assert len(bloquants) == 0, "Aucune anomalie bloquante attendue sur un document conforme."

    def test_insensible_aux_accents(self) -> None:
        """Vérifie que les règles restent robustes aux extractions PDF sans accents."""
        pacte_data = _make_data(
            clauses=[
                "Agrement des cessions de parts",
                "Clause de sortie - tag-along",
                "Mediation en cas de conflit",
            ],
            type_doc="pacte_associes",
        )
        statuts_data = _make_data(
            clauses=[
                "Agrement des cessions de parts",
                "Gerance et pouvoirs du gerant - limites aux actes courants",
            ],
            type_doc="statuts",
        )
        checker = RuleChecker(pacte_data, statuts_data)
        result = checker.run_all_with_stats()

        agrements = [
            f for f in result["findings"] if "agrement" in f.get("explication", "").lower()
        ]
        assert len(agrements) == 0, "La clause 'Agrement' sans accent doit etre detectee."
        pouvoirs = [
            f for f in result["findings"] if "pouvoirs" in f.get("explication", "").lower()
        ]
        assert len(pouvoirs) == 0, "Les pouvoirs du gerant (sans accent) doivent etre reconnus."

    def test_deduplication(self) -> None:
        """Vérifie que les findings en double sont supprimés."""
        pacte_data = _make_data(clauses=[], type_doc="pacte_associes")
        statuts_data = _make_data(clauses=[], type_doc="statuts")
        checker = RuleChecker(pacte_data, statuts_data)
        result = checker.run_all_with_stats()
        # Vérifier que le dédupliquage fonctionne
        assert result["total"] == len(result["findings"])

    def test_pacte_seul_sans_faux_positifs(self) -> None:
        """Un pacte analysé seul ne doit pas déclencher les règles des statuts."""
        pacte_data = _make_data(
            clauses=[
                "Agrément des cessions de parts",
                "Médiation en cas de conflit",
                "Clause de non-concurrence — durée 2 ans",
            ],
            type_doc="pacte_associes",
        )
        statuts_data = {}
        checker = RuleChecker(pacte_data, statuts_data)
        result = checker.run_all_with_stats()

        textes = [f.get("explication", "").lower() for f in result["findings"]]
        # Aucun faux positif lié aux règles des statuts (agrément, blocage, gérant)
        assert not any("agrement" in t for t in textes), "L'agrément présent dans le pacte est ignoré."
        assert not any("blocage" in t for t in textes), "La médiation présente dans le pacte est ignorée."
        assert not any("pouvoirs du gerant" in t for t in textes), "La règle gérant est propre aux statuts."
        # L'absence de clause de sortie doit être signalée (règle du pacte)
        sorties = [t for t in textes if "aucune clause de sortie" in t]
        assert len(sorties) == 1, "L'absence de clause de sortie doit être signalée une fois."

    def test_statuts_seuls_sans_faux_positifs(self) -> None:
        """Des statuts analysés seuls ne doivent pas déclencher les règles du pacte."""
        statuts_data = _make_data(
            clauses=[
                "Gérance et pouvoirs du gérant — limites aux actes courants",
            ],
            type_doc="statuts",
        )
        pacte_data = {}
        checker = RuleChecker(pacte_data, statuts_data)
        result = checker.run_all_with_stats()

        textes = [f.get("explication", "").lower() for f in result["findings"]]
        # Pas de faux positif sur les règles du pacte (non-concurrence notamment)
        assert not any("non-concurrence" in t for t in textes)
        # La règle gérant s'applique aux statuts : pouvoirs trouvés avec limite -> aucune anomalie
        assert not any("pouvoirs" in t for t in textes)


class TestRisquesFuturs:
    """Tests des regles de risques futurs (valorisation, deces, impaye)."""

    def test_valorisation_manquante_si_cession(self) -> None:
        """Une clause de cession sans methode de valorisation est signalee."""
        data = _make_data(
            clauses=["Clause de cession — cession libre des parts entre associes"],
            type_doc="pacte_associes",
        )
        result = check_valorisation_sortie(data)
        assert len(result) == 1
        assert result[0]["type"] == "risque_futur"
        assert result[0]["reference_juridique"] == "Art. 1843-4 C. civ"

    def test_valorisation_presente(self) -> None:
        """Une clause avec reference a l'expert ne declenche rien."""
        data = _make_data(
            clauses=[
                "Clause de sortie — le prix sera fixe par un expert independant "
                "conformement a l'article 1843-4 du Code civil"
            ],
            type_doc="pacte_associes",
        )
        assert check_valorisation_sortie(data) == []

    def test_valorisation_sans_sortie(self) -> None:
        """Un document sans mecanisme de sortie/cession ne declenche rien."""
        data = _make_data(clauses=["Article 1 — Objet"], type_doc="pacte_associes")
        assert check_valorisation_sortie(data) == []

    def test_deces_non_couvert_dans_pacte(self) -> None:
        """Un pacte silencieux sur le deces/incapacite est alerte."""
        data = _make_data(clauses=["Article 1 — Objet"], type_doc="pacte_associes")
        result = check_clause_deces_incapacite(data)
        assert len(result) == 1
        assert result[0]["priorite"] == "alerte"
        assert result[0]["reference_juridique"] == "Art. L223-13"

    def test_deces_couvert(self) -> None:
        """Un pacte organisant le sort des heritiers ne declenche rien."""
        data = _make_data(
            clauses=[
                "Sort des parts en cas de deces — les heritiers doivent etre agrees"
            ],
            type_doc="pacte_associes",
        )
        assert check_clause_deces_incapacite(data) == []

    def test_deces_ignore_dans_statuts(self) -> None:
        """La regle deces/incapacite est propre au pacte (pas de faux positif)."""
        data = _make_data(clauses=["Article 1 — Objet"], type_doc="statuts")
        assert check_clause_deces_incapacite(data) == []

    def test_impaye_alerte_si_paiement_sans_sanction(self) -> None:
        """Un paiement sans sanction de defaillance est signale."""
        data = _make_data(
            clauses=[
                "Appel de fonds — chaque associe verse sa contribution sous 30 jours"
            ],
            type_doc="pacte_associes",
        )
        result = check_clause_impaye(data)
        assert len(result) == 1
        assert result[0]["reference_juridique"] == "Art. 1225 C. civ"

    def test_impaye_couvert_par_clause_resolutoire(self) -> None:
        """Une clause resolutoire couvre le risque de non-paiement."""
        data = _make_data(
            clauses=[
                "En cas de non-paiement, mise en demeure puis clause resolutoire"
            ],
            type_doc="pacte_associes",
        )
        assert check_clause_impaye(data) == []

    def test_impaye_sans_paiement(self) -> None:
        """Un document sans obligation de paiement ne declenche rien."""
        data = _make_data(clauses=["Article 1 — Objet"], type_doc="pacte_associes")
        assert check_clause_impaye(data) == []


class TestRisqueConfidentialite:
    """Regle 17 : clause de confidentialite."""

    def test_confidentialite_alerte_sans_clause(self) -> None:
        """Des informations sensibles sans clause de confidentialite sont signalees."""
        data = _make_data(
            clauses=[
                "Le pacte contient les donnees financieres et la strategie de la societe"
            ],
            type_doc="pacte_associes",
        )
        result = check_clause_confidentialite(data)
        assert len(result) == 1
        assert result[0]["type"] == "risque_futur"
        assert result[0]["reference_juridique"] == "Art. L151-1 C. com"

    def test_confidentialite_couverte(self) -> None:
        """Une clause de confidentialite couvre le risque."""
        data = _make_data(
            clauses=[
                "Chaque associe s'engage a la confidentialite sur le savoir-faire de la societe"
            ],
            type_doc="pacte_associes",
        )
        assert check_clause_confidentialite(data) == []

    def test_confidentialite_sans_informations(self) -> None:
        """Un pacte sans informations sensibles ne declenche rien."""
        data = _make_data(clauses=["Article 1 — Objet"], type_doc="pacte_associes")
        assert check_clause_confidentialite(data) == []

    def test_confidentialite_propre_au_pacte(self) -> None:
        """La regle ne s'applique pas aux statuts (pas de faux positif)."""
        data = _make_data(clauses=["Article 1 — Objet"], type_doc="statuts")
        assert check_clause_confidentialite(data) == []


class TestRisqueResiliation:
    """Regle 18 : duree/engagement irrevocable sans issue."""

    def test_resiliation_alerte_si_duree_sans_issue(self) -> None:
        """Un pacte conclu pour une duree sans clause de resiliation est signale."""
        data = _make_data(
            clauses=["Le present pacte est conclu pour une duree de dix ans"],
            type_doc="pacte_associes",
        )
        result = check_clause_resiliation(data)
        assert len(result) == 1
        assert result[0]["type"] == "risque_futur"
        assert result[0]["reference_juridique"] == "Art. 1210 C. civ"

    def test_resiliation_couverte(self) -> None:
        """Une clause de resiliation avec preavis couvre le risque."""
        data = _make_data(
            clauses=[
                "Le present pacte est conclu pour une duree de dix ans, "
                "resiliable avec un preavis de six mois"
            ],
            type_doc="pacte_associes",
        )
        assert check_clause_resiliation(data) == []

    def test_resiliation_sans_engagement(self) -> None:
        """Un pacte sans duree ni engagement irrevocable ne declenche rien."""
        data = _make_data(clauses=["Article 1 — Objet"], type_doc="pacte_associes")
        assert check_clause_resiliation(data) == []


class TestRisqueDesequilibre:
    """Regle 19 : pouvoirs unilateraux sans protection minoritaire."""

    def test_desequilibre_alerte_si_veto_sans_protection(self) -> None:
        """Un veto unilateral sans protection du minoritaire est signale."""
        data = _make_data(
            clauses=["L'associe majoritaire dispose d'un droit de veto sur toute decision"],
            type_doc="pacte_associes",
        )
        result = check_desequilibre_pouvoirs(data)
        assert len(result) == 1
        assert result[0]["type"] == "risque_futur"
        assert result[0]["priorite"] == "important"
        assert result[0]["reference_juridique"] == "Art. 1104 C. civ"

    def test_desequilibre_couvert_par_tag_along(self) -> None:
        """Une protection du minoritaire (tag-along) equilibre le veto."""
        data = _make_data(
            clauses=[
                "Droit de veto de l'associe majoritaire ; tag-along au profit "
                "des associes minoritaires en cas de cession"
            ],
            type_doc="pacte_associes",
        )
        assert check_desequilibre_pouvoirs(data) == []

    def test_desequilibre_sans_veto(self) -> None:
        """Un pacte sans pouvoir unilateral ne declenche rien."""
        data = _make_data(clauses=["Article 1 — Objet"], type_doc="pacte_associes")
        assert check_desequilibre_pouvoirs(data) == []

    def test_desequilibre_propre_au_pacte(self) -> None:
        """La regle ne s'applique pas aux statuts (pas de faux positif)."""
        data = _make_data(clauses=["Article 1 — Objet"], type_doc="statuts")
        assert check_desequilibre_pouvoirs(data) == []


class TestReferenceParFormeSociale:
    """Vérifie que les références juridiques sont adaptées à la forme sociale.

    Suite à la demande de correction : L.228-23 ne s'applique pas à une SARL.
    """

    def _make_sarl(self):
        return {
            "type_document": "statuts",
            "texte": "La société est une SARL au capital de 10 000 euros.",
            "clauses": [{"titre": "Article 1 — Objet", "contenu": "Objet social", "position": 0}],
            "entites": {"articles": [], "dates": [], "montants": [], "parties": [], "personnes": []},
        }

    def _make_sa(self):
        return {
            "type_document": "statuts",
            "texte": "La société est une société anonyme (SA) au capital de 100 000 euros.",
            "clauses": [{"titre": "Article 1 — Objet", "contenu": "Objet social", "position": 0}],
            "entites": {"articles": [], "dates": [], "montants": [], "parties": [], "personnes": []},
        }

    def test_detection_sarl(self) -> None:
        """La forme sociale 'SARL' est bien détectée dans le texte."""
        assert _forme_sociale(self._make_sarl()) == "SARL"

    def test_detection_sa(self) -> None:
        """La forme sociale 'SA' est bien détectée dans le texte."""
        assert _forme_sociale(self._make_sa()) == "SA"

    def test_agrement_sarl_utilise_l223_14(self) -> None:
        """Pour une SARL, l'agrément doit référencer L.223-14 (et non L.228-23)."""
        result = check_clause_agrement(self._make_sarl())
        assert len(result) == 1
        assert result[0]["reference_juridique"] == "Art. L223-14"

    def test_agrement_sa_utilise_l228_23(self) -> None:
        """Pour une SA, l'agrément peut référencer L.228-23 (sociétés par actions)."""
        result = check_clause_agrement(self._make_sa())
        assert len(result) == 1
        assert result[0]["reference_juridique"] == "Art. L228-23"

    def test_article_agrement_table(self) -> None:
        """Table de correspondance agrément / forme sociale."""
        assert _article_agrement("SARL") == "Art. L223-14"
        assert _article_agrement("EURL") == "Art. L223-14"
        assert _article_agrement("SA") == "Art. L228-23"
        assert _article_agrement("SAS") == "Art. L228-23"

    def test_article_decisions_table(self) -> None:
        """Table de correspondance majorités / forme sociale."""
        assert _article_decisions("SARL") == "Art. L223-29"
        assert _article_decisions("EURL") == "Art. L223-29"
        assert _article_decisions("SAS") == "Art. L227-9"
        assert _article_decisions("SA") == "Art. L225-96"
