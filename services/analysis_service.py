"""Service d'analyse juridique - pipeline complet."""

from __future__ import annotations

import re
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

# Correspondance document_concerne d'une anomalie -> type attendu par la
# base de connaissance (legal_kb). Les valeurs None indiquent qu'aucun type
# ne correspond : la recherche se fait alors sur le domaine juridique seul.
_CONCERNE_TO_KB_TYPE = {
    "pacte": "pacte_associes",
    "statuts": "statuts",
    "les deux": None,
    "proces_verbal": None,
    "modification_statutaire": None,
}

_STOPWORDS = frozenset({
    "dans", "pour", "avec", "aucune", "aucun", "aucune", "trouve", "trouvee",
    "detecte", "mention", "doit", "sont", "dans", "une", "des", "les", "est",
    "que", "qui", "pas", "sur", "par", "au", "aux", "ce", "cette", "ces",
})

_KB_DOMAIN_DEFINI = "droit des sociétés"


def _tokens(texte: str) -> list[str]:
    """Découpe un texte en jetons alphanumériques minuscules, sans stopwords."""
    mots = re.findall(r"[a-z0-9àâäéèêëîïôöùûüç'-]+", texte.lower())
    return [m for m in mots if m not in _STOPWORDS and len(m) > 2]


def _termes_pour_finding(finding: dict[str, Any]) -> list[str]:
    """Construit les termes de recherche RAG-lite à partir d'une anomalie."""
    texte = " ".join([
        str(finding.get("type", "")),
        str(finding.get("explication", "")),
        str(finding.get("reference_juridique", "")),
    ])
    return _tokens(texte)[:12]


def _detecter_documents_manquants(types_per_doc: dict[str, str]) -> list[str]:
    """Détecte les documents juridiques attendus mais absents du dossier.

    Règle : dès qu'un dossier contient un document de société (pacte,
    statuts, procès-verbal ou modification statutaire), les statuts sont le
    document de référence obligatoire : leur absence est signalée. Le pacte
    d'associés reste optionnel en droit, il n'est donc pas exigé. Sans aucun
    document de société, on ne peut rien conclure sur la complétude.
    """
    types_presents = set(types_per_doc.values())
    corporates = types_presents & {
        "pacte", "statuts", "proces_verbal", "modification_statutaire",
    }
    if not corporates:
        return []
    if "statuts" in types_presents:
        return []
    return ["Statuts de société (document de référence obligatoire)"]


def _compacter_entree_kb(entry: dict[str, Any]) -> dict[str, Any]:
    """Réduit une entrée de la base de connaissance aux champs utiles au rapport."""
    return {
        "id": entry.get("id", ""),
        "article": entry.get("numero_article", ""),
        "titre": entry.get("titre_texte", ""),
        "source": entry.get("source", ""),
        "domaine": entry.get("domaine", ""),
        "regles_controle": entry.get("regles_controle", []),
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
        pacte_keys = [k for k in doc_keys if types_per_doc.get(k) == "pacte"]
        statuts_keys = [
            k for k in doc_keys
            if types_per_doc.get(k) in ("statuts", "modification_statutaire")
        ]
        if pacte_keys and statuts_keys:
            comparator = DocumentComparator(
                extraction_per_doc[pacte_keys[0]],
                extraction_per_doc[statuts_keys[0]],
            )
        else:
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
            "texte": documents.get(pacte_keys[0], "") if pacte_keys else "",
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

    # RAG-lite : pour chaque anomalie, on interroge la base de connaissance
    # (type de document + termes + domaine) et on rattache les entrées
    # pertinentes (articles, règles de contrôle) à l'anomalie.
    kb_ids_utilisees: list[str] = []
    kb_refs_par_finding: list[list[dict[str, Any]]] = []
    for f in findings:
        compacts = [
            _compacter_entree_kb(e)
            for e in kb.search_relevant(
                _termes_pour_finding(f),
                doc_type=_CONCERNE_TO_KB_TYPE.get(f.get("document_concerne", "")),
                domain=_KB_DOMAIN_DEFINI,
                top_k=3,
            )
        ]
        for e in compacts:
            if e["id"] and e["id"] not in kb_ids_utilisees:
                kb_ids_utilisees.append(e["id"])
        kb_refs_par_finding.append(compacts)

    builder = ReportBuilder()
    builder.set_documents_analyses([
        {
            "nom": name,
            "type": _TYPE_LABELS.get(types_per_doc.get(name, "autre"), "non_classe"),
            "statut": "analyse",
        }
        for name in doc_keys
    ])
    builder.set_documents_manquants(_detecter_documents_manquants(types_per_doc))
    builder.set_informations_principales({
        "nombre_documents": len(doc_keys),
        "types_documents": {
            k: _TYPE_LABELS.get(t, "non_classe") for k, t in types_per_doc.items()
        },
        "regles_controle_appliquees": regles_appliquees,
        "entites_extraites": {
            k: v.get("entites", {}) for k, v in extraction_per_doc.items()
        },
        "base_juridique": (
            f"{len(kb_entries)} entrees"
            f" ({len(kb_ids_utilisees)} mobilisees par RAG-lite)"
        ),
        "base_juridique_utilisee": kb_ids_utilisees,
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

    for idx, f in enumerate(findings):
        builder.add_anomalie({
            "explication": f.get("explication", ""),
            "nature_controle": f.get("type", ""),
            "priorite": f.get("priorite", ""),
            "consequence": f.get("explication", ""),
            "source_juridique": f.get("reference_juridique", ""),
            "correction_recommandee": f.get("correction_recommandee", ""),
            "documents_a_verifier": _documents_verifier(f.get("document_concerne", "")),
            "validation_requise": "oui" if f.get("validation_requise") == "juriste" else "non",
            "base_juridique": kb_refs_par_finding[idx] if idx < len(kb_refs_par_finding) else [],
        })

    report = builder.build()
    report["analyses_clauses"] = _analyser_clauses(types_per_doc, clauses_per_doc)
    report["clauses_a_risque"] = [
        {
            "clause": a.get("titre", ""),
            "risque": a.get("niveau_risque", ""),
            "document": a.get("document", ""),
            "amelioration": a.get("amelioration_argmentee", ""),
        }
        for a in report["analyses_clauses"]
        if a.get("niveau_risque") != "faible"
    ]
    from services import legal_source_service
    legal_source_service.enrich_report_with_sources(report)
    report["synthese_intelligente"] = _llm_synthese(report)
    return report


def _analyser_clauses(
    types_per_doc: dict[str, str],
    clauses_per_doc: dict[str, list],
) -> list[dict[str, Any]]:
    """Analyse chaque clause (IA si clé valide, sinon repli local déterministe).

    Seules les clauses des documents de sociétés sont analysées ; on borne le
    volume (20 clauses max par document) pour limiter le coût des appels LLM.
    """
    from services import llm_service

    analyses: list[dict[str, Any]] = []
    if not clauses_per_doc:
        return analyses
    for name, clauses in clauses_per_doc.items():
        if types_per_doc.get(name) not in ("pacte", "statuts"):
            continue
        for clause in clauses[:20]:
            titre = clause.get("titre", "")
            contenu = clause.get("contenu", "")
            if not titre and not contenu:
                continue
            try:
                resultat = llm_service.analyser_clause(titre, contenu)
            except Exception:
                continue
            if resultat:
                resultat["document"] = name
                analyses.append(resultat)
    return analyses


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

    docs_manquants = report.get("documents_manquants", [])
    if docs_manquants:
        lignes_manquants = "; ".join(f"**{d}**" for d in docs_manquants)
        lines.append(
            f"\n> **⚠️ Documents manquants :** {lignes_manquants}. "
            f"L'analyse comparative (pacte vs statuts) ne peut etre complete sans ce document.\n"
        )

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

    analyses = report.get("analyses_clauses", [])
    if analyses:
        a_risque = [a for a in analyses if a.get("niveau_risque") != "faible"]
        lines.append("## Analyse des Clauses (IA)\n")
        if not a_risque:
            lines.append("Aucune clause ne presente de risque particulier au regard "
                         "de l'analyse automatique.\n")
        for a in analyses:
            niveau = a.get("niveau_risque", "faible")
            label = {"eleve": "ELEVE", "modere": "MODERE", "faible": "FAIBLE"}.get(niveau, niveau.upper())
            ligne = f"- **{a.get('titre', '')}** [{label}]"
            if a.get("document"):
                ligne += f" ({a.get('document', '')})"
            lines.append(ligne)
            if a.get("fondement"):
                lines.append(f"  - Fondement : {a.get('fondement', '')}")
            if a.get("analyse"):
                lines.append(f"  - Analyse : {a.get('analyse', '')}")
            if a.get("amelioration_argmentee"):
                lines.append(f"  - Amélioration : {a.get('amelioration_argmentee', '')}")
            lines.append("")

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
