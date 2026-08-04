"""Service d'analyse juridique - pipeline complet."""

from __future__ import annotations

from typing import Any

from extraction.clause_extractor import ClauseExtractor
from extraction.entity_extractor import EntityExtractor
from comparison.document_comparator import DocumentComparator
from rules_engine.rule_checker import RuleChecker
from legal_kb.knowledge_base import LegalKnowledgeBase
from report_generator.report_builder import ReportBuilder
from services.document_service import assess_document_quality, detect_document_type

_TYPE_LABELS = {
    "pacte": "pacte d'associes",
    "statuts": "statuts de societe",
    "proces_verbal": "proces-verbal d'assemblee",
    "modification_statutaire": "modification statutaire",
    "autre": "non_classe",
}


def analyze_documents(
    documents: dict[str, str], statuses: dict[str, str] | None = None
) -> dict[str, Any]:
    """
    Execute le pipeline complet d'analyse juridique.

    Les regles de controle (RuleChecker) ne sont appliquees qu'aux documents
    detectes comme pacte d'associes, statuts, proces-verbal ou modification
    statutaire. Les autres documents (cours, manuels, contrats hors societe...)
    sont analyses mais ne produisent pas de fausses anomalies.

    Args:
        documents: {nom_fichier: texte_extrait}
        statuses: {nom_fichier: statut de lecture} optionnel (OCR).

    Returns:
        Rapport complet au format dictionnaire.
    """
    extraction_per_doc: dict[str, dict[str, Any]] = {}
    clauses_per_doc: dict[str, list] = {}
    types_per_doc: dict[str, str] = {}
    qualite_per_doc: dict[str, dict[str, Any]] = {}

    for name, text in documents.items():
        types_per_doc[name] = detect_document_type(text)
        qualite_per_doc[name] = assess_document_quality(text, (statuses or {}).get(name, "natif"))
        extractor = EntityExtractor(text)
        extraction_per_doc[name] = {"entites": extractor.extract_all()}
        clause_extractor = ClauseExtractor(text)
        clauses_per_doc[name] = clause_extractor.extract_all()

    doc_keys = list(documents.keys())
    if len(doc_keys) >= 2:
        comparator = DocumentComparator(
            extraction_per_doc[doc_keys[0]],
            extraction_per_doc[doc_keys[1]],
        )
        incoherences = comparator.compare_all()
    else:
        incoherences = []

    corporate_docs = [
        k for k, t in types_per_doc.items() if t in ("pacte", "statuts")
    ]
    pv_docs = [k for k, t in types_per_doc.items() if t == "proces_verbal"]
    modif_docs = [k for k, t in types_per_doc.items() if t == "modification_statutaire"]

    findings: list[dict[str, Any]] = []
    if corporate_docs:
        pacte_keys = [k for k, t in types_per_doc.items() if t == "pacte"]
        statuts_keys = [k for k, t in types_per_doc.items() if t == "statuts"]
        pacte_data = {
            "type_document": "pacte_associes",
            "clauses": clauses_per_doc.get(pacte_keys[0], []) if pacte_keys else []
        }
        statuts_data = {
            "type_document": "statuts",
            "texte": documents.get(statuts_keys[0], "") if statuts_keys else "",
            "clauses": clauses_per_doc.get(statuts_keys[0], []) if statuts_keys else []
        }
        rule_checker = RuleChecker(pacte_data, statuts_data)
        findings = [dict(f) for f in rule_checker.run_all()]

    if pv_docs:
        for k in pv_docs:
            pv_data = {
                "clauses": clauses_per_doc.get(k, []),
                "texte": documents.get(k, ""),
                "type_document": "proces_verbal",
            }
            findings.extend(
                dict(f) for f in RuleChecker({}, {}).run_pv_rules(pv_data)
            )

    if modif_docs:
        for k in modif_docs:
            modif_data = {
                "clauses": clauses_per_doc.get(k, []),
                "texte": documents.get(k, ""),
                "type_document": "modification_statutaire",
            }
            findings.extend(
                dict(f) for f in RuleChecker({}, {}).run_modification_rules(modif_data)
            )

    regles_appliquees = bool(corporate_docs or pv_docs or modif_docs)
    if not regles_appliquees:
        clauses_per_doc = {}

    kb = LegalKnowledgeBase()
    kb_entries = kb.get_all_entries()

    builder = ReportBuilder()
    builder.set_documents_analyses([
        {
            "nom": name,
            "type": _TYPE_LABELS.get(types_per_doc.get(name, "autre"), "non_classe"),
            "statut": "analyse",
        }
        for name in doc_keys
    ])
    builder.set_informations_principales({
        "nombre_documents": len(doc_keys),
        "types_documents": {
            k: _TYPE_LABELS.get(t, "non_classe") for k, t in types_per_doc.items()
        },
        "regles_controle_appliquees": regles_appliquees,
        "entites_extraites": {
            k: v.get("entites", {}) for k, v in extraction_per_doc.items()
        },
        "base_juridique": f"{len(kb_entries)} entrees",
        "statut_lecture": statuses or {},
        "qualite_documents": qualite_per_doc,
        "document_text": "\n\n".join(documents.values()),
    })
    builder.set_incoherences(incoherences)
    builder.set_niveau_risque_global(
        "eleve" if any(f.get("priorite") == "bloquant" for f in findings)
        else "modere" if any(f.get("priorite") == "important" for f in findings)
        else "faible"
    )

    filenames_by_type: dict[str, list[str]] = {}
    for name, t in types_per_doc.items():
        filenames_by_type.setdefault(t, []).append(name)

    _TYPE_KEY = {
        "pacte_associes": "pacte",
        "statuts": "statuts",
        "proces_verbal": "proces_verbal",
        "modification_statutaire": "modification_statutaire",
    }

    def _documents_verifier(concerne: str) -> list[str]:
        """Retourne les noms de fichiers concernés par une anomalie."""
        if concerne == "les deux":
            return filenames_by_type.get("pacte", []) + filenames_by_type.get("statuts", [])
        type_key = _TYPE_KEY.get(concerne)
        if type_key:
            return filenames_by_type.get(type_key, [])
        if concerne and concerne != "non spécifié":
            return [concerne]
        # Repli : toutes les societes analysees (si le type n'a pas pu etre rattache)
        return (
            filenames_by_type.get("pacte", [])
            + filenames_by_type.get("statuts", [])
            + filenames_by_type.get("proces_verbal", [])
            + filenames_by_type.get("modification_statutaire", [])
        )

    for f in findings:
        builder.add_anomalie({
            "explication": f.get("explication", ""),
            "nature_controle": f.get("type", ""),
            "priorite": f.get("priorite", ""),
            "consequence": f.get("explication", ""),
            "source_juridique": f.get("reference_juridique", ""),
            "correction_recommandee": f.get("correction_recommandee", ""),
            "documents_a_verifier": _documents_verifier(f.get("document_concerne", "")),
            "validation_requise": "oui" if f.get("validation_requise") == "juriste" else "non",
        })

    report = builder.build()
    from services import legal_source_service
    legal_source_service.enrich_report_with_sources(report)
    report["synthese_intelligente"] = _llm_synthese(report)
    return report


def _has_illisible(report: dict[str, Any]) -> bool:
    """Vrai si au moins un document est jugé illisible."""
    qualites = report.get("informations_principales", {}).get("qualite_documents", {})
    return any(q.get("illisible") for q in qualites.values())


def _llm_synthese(report: dict[str, Any]) -> str | None:
    """Synthese intelligente optionnelle (None si pas de cle valide / echec LLM)."""
    if _has_illisible(report):
        # Un document illisible ne doit pas produire de synthèse rassurante
        # ("aucune anomalie, document sécurisé") : ce serait trompeur.
        return None
    try:
        from services import llm_service

        if llm_service.get_llm_config() is None:
            return None
        document_text = report.get("informations_principales", {}).get("document_text", "")
        return llm_service.generate_analysis_synthesis(report, document_text)
    except Exception:
        return None


def format_report_markdown(report: dict[str, Any]) -> str:
    """Formate un rapport en Markdown lisible."""
    lines = []
    lines.append("# Rapport d'Analyse Juridique\n")

    lines.append("## Documents Analysees\n")
    for doc in report.get("documents_analyses", []):
        type_doc = doc.get('type', '')
        suffixe = f" ({type_doc})" if type_doc and type_doc != "non_classe" else ""
        lines.append(f"- **{doc.get('nom', 'N/A')}**{suffixe} ({doc.get('statut', '')})")

    risque = report.get("niveau_risque_global", "non_evalue")
    emoji_risque = {"eleve": "eleve", "modere": "modere", "faible": "faible"}.get(risque, risque)
    lines.append(f"\n**Niveau de risque : {emoji_risque.upper()}**\n")

    infos = report.get("informations_principales", {})
    if infos.get("regles_controle_appliquees") is False:
        lines.append(
            "> **Note :** aucun document de type pacte d'associes, statuts, "
            "proces-verbal ou modification statutaire n'a ete detecte. Les regles "
            "de controle specifiques aux societes ne sont donc pas appliquees, et "
            "aucune anomalie de pacte/statuts n'est rapportee.\n"
        )

    statuts_lecture = infos.get("statut_lecture", {})
    if statuts_lecture:
        labels = {
            "natif": "texte natif",
            "ocr": "OCR applique",
            "ocr_indisponible": "OCR indisponible (scan probable)",
            "erreur": "erreur de lecture",
        }
        lignes_statuts = ", ".join(
            f"{nom} ({labels.get(st, st)})" for nom, st in statuts_lecture.items()
        )
        if lignes_statuts:
            lines.append(f"\n**Lecture des documents :** {lignes_statuts}\n")

    qualites = infos.get("qualite_documents", {})
    problemes = {
        nom: q.get("detail", "") for nom, q in qualites.items() if q.get("detail") != "lecture correcte"
    }
    if problemes:
        lignes_qualite = "; ".join(f"{nom}: {detail}" for nom, detail in problemes.items())
        lines.append(f"\n**Qualite des documents :** {lignes_qualite}\n")

    sources = infos.get("sources_officielles", {})
    if sources:
        lines.append(
            f"\n**Sources officielles :** {sources.get('anomalies_liees_a_legifrance', 0)} "
            f"anomalie(s) liee(s) a Légifrance | "
            f"PISTE: {'configure' if sources.get('piste_token_configured') else 'non configure'} "
            f"| {sources.get('anomalies_reference_fictive', 0)} reference(s) fictive(s) "
            f"(a verifier).\n"
        )

    synthese = report.get("synthese_intelligente")
    if synthese:
        lines.append("## Synthese Intelligente (IA)\n")
        lines.append(synthese + "\n")

    anomalies = report.get("anomalies_juridiques", [])
    if anomalies:
        lines.append("## Anomalies Juridiques\n")
        for i, a in enumerate(anomalies, 1):
            priorite = a.get("priorite", "").upper()
            lines.append(f"### Anomalie {i} [{priorite}]\n")
            lines.append(f"**Explication :** {a.get('explication', '')}\n")
            lines.append(f"- **Nature :** {a.get('nature_controle', '')}")
            lines.append(f"- **Source :** {a.get('source_juridique', '')}")
            lines.append(f"- **Correction :** {a.get('correction_recommandee', '')}")
            lines.append("")

    incoherences = report.get("incoherences", [])
    if incoherences:
        lines.append("## Incoherences Entre Documents\n")
        for inc in incoherences:
            lines.append(f"- **{inc.get('type', '')}** ({inc.get('severite', '')}) : {inc.get('description', '')}")

    infos = report.get("informations_principales", {})
    entites = infos.get("entites_extraites", {})
    if entites:
        lines.append("\n## Entites Extraites\n")
        for doc_name, doc_entites in entites.items():
            lines.append(f"### {doc_name}\n")
            dates = doc_entites.get("dates", [])
            if dates:
                dates_unique = list({d["valeur"] for d in dates})
                lines.append(f"- **Dates :** {', '.join(dates_unique)}")
            parties = doc_entites.get("parties", [])
            if parties:
                noms = [p.get("nom", "") for p in parties]
                lines.append(f"- **Organisations :** {', '.join(noms)}")
            montants = doc_entites.get("montants", [])
            if montants:
                vals = [m.get("valeur", "") for m in montants]
                lines.append(f"- **Montants :** {', '.join(vals)}")
            lines.append("")

    return "\n".join(lines)
