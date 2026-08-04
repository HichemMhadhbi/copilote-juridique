"""
Vérificateur de règles automatiques TOP-JURIDIQUE.

La classe RuleChecker orchestre l'exécution de toutes les règles de
contrôle sur les données extraites des documents, déduplique les
résultats et produit un résumé statistique.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from rules_engine.rules import (
    _Finding,
    check_clause_agrement,
    check_clause_blocage,
    check_clause_non_concurrence,
    check_clause_sortie,
    check_conflict_pacte_statuts,
    check_droit_veto,
    check_majorite_decisions,
    check_modification_statutaire,
    check_pv_quorum,
    check_pv_resolutions,
    check_responsabilite_gerant,
)


class RuleChecker:
    """
    Exécute l'ensemble des règles de contrôle et agrège les résultats.
    """

    def __init__(self, pacte_data: Dict[str, Any], statuts_data: Dict[str, Any]) -> None:
        """
        Args:
            pacte_data: Données extraites du pacte d'associés.
            statuts_data: Données extraites des statuts.
        """
        self._pacte = pacte_data
        self._statuts = statuts_data

    @staticmethod
    def _est_vide(data: Dict[str, Any]) -> bool:
        """Un document est 'vide' si aucune clause ni aucun texte n'a été extrait."""
        if not data:
            return True
        return not data.get("clauses") and not data.get("texte")

    def run_all(self) -> List[_Finding]:
        """
        Lance toutes les règles applicables et retourne la liste dédupliquée
        des findings.

        Les règles propres aux statuts ne sont exécutées que si un document
        de type statuts est présent, et celles propres au pacte que si un
        pacte est présent. Cela évite les faux positifs lorsqu'un seul des
        deux documents est analysé (ex. un pacte seul ne doit pas déclencher
        les règles sur les statuts).
        """
        findings: List[_Finding] = []
        statuts_present = not self._est_vide(self._statuts)
        pacte_present = not self._est_vide(self._pacte)

        # Règles applicables aux statuts (uniquement si des statuts sont fournis)
        if statuts_present:
            findings.extend(check_clause_agrement(self._statuts))
            findings.extend(check_clause_sortie(self._statuts))
            findings.extend(check_droit_veto(self._statuts))
            findings.extend(check_majorite_decisions(self._statuts))
            findings.extend(check_clause_blocage(self._statuts))
            findings.extend(check_responsabilite_gerant(self._statuts))

        # Règles applicables au pacte (uniquement si un pacte est fourni)
        if pacte_present:
            findings.extend(check_clause_agrement(self._pacte))
            findings.extend(check_clause_sortie(self._pacte))
            findings.extend(check_droit_veto(self._pacte))
            findings.extend(check_majorite_decisions(self._pacte))
            findings.extend(check_clause_non_concurrence(self._pacte))
            findings.extend(check_clause_blocage(self._pacte))

        # Règles comparatives (uniquement si les deux documents sont présents)
        if statuts_present and pacte_present:
            findings.extend(check_conflict_pacte_statuts(self._pacte, self._statuts))

        return self._deduplicate(findings)

    def run_pv_rules(self, pv_data: Dict[str, Any]) -> List[_Finding]:
        """
        Lance les règles applicables à un procès-verbal d'assemblée.

        Args:
            pv_data: Données extraites du procès-verbal.

        Returns:
            Liste dédupliquée des findings (quorum/majorité, résolutions, feuille de présence).
        """
        findings: List[_Finding] = []
        findings.extend(check_pv_quorum(pv_data))
        findings.extend(check_pv_resolutions(pv_data))
        return self._deduplicate(findings)

    def run_modification_rules(self, modif_data: Dict[str, Any]) -> List[_Finding]:
        """
        Lance les règles applicables à une modification statutaire.

        Args:
            modif_data: Données extraites de l'acte de modification des statuts.

        Returns:
            Liste dédupliquée des findings (décision extraordinaire, formalités).
        """
        return self._deduplicate(check_modification_statutaire(modif_data))

    def run_all_with_stats(self) -> Dict[str, Any]:
        """
        Exécute toutes les règles et retourne un rapport structuré contenant
        la liste des findings et des statistiques récapitulatives.

        Returns:
            Dict avec les clés suivantes :
            - findings (list) : tous les résultats
            - total (int)
            - par_priorite (Dict[str, int])
            - par_type (Dict[str, int])
            - par_document (Dict[str, int])
        """
        findings = self.run_all()
        total = len(findings)

        par_priorite: Dict[str, int] = {}
        par_type: Dict[str, int] = {}
        par_document: Dict[str, int] = {}

        for f in findings:
            p = f.get("priorite", "inconnue")
            par_priorite[p] = par_priorite.get(p, 0) + 1

            t = f.get("type", "inconnu")
            par_type[t] = par_type.get(t, 0) + 1

            d = f.get("document_concerne", "non spécifié")
            par_document[d] = par_document.get(d, 0) + 1

        return {
            "findings": findings,
            "total": total,
            "par_priorite": par_priorite,
            "par_type": par_type,
            "par_document": par_document,
        }

    @staticmethod
    def _deduplicate(findings: List[_Finding]) -> List[_Finding]:
        """
        Supprime les findings en double (même type, même priorité, même explication).
        L'ordre de la première occurrence est conservé.
        """
        vus: set[Tuple[str, str, str]] = set()
        uniques: List[_Finding] = []
        for f in findings:
            cle = (f.get("type", ""), f.get("priorite", ""), f.get("explication", ""))
            if cle not in vus:
                vus.add(cle)
                uniques.append(f)
        return uniques
