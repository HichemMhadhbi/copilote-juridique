"""Service d'analyse juridique - pipeline complet."""

from __future__ import annotations

import re
from typing import Any

from extraction.clause_extractor import ClauseExtractor
from extraction.entity_extractor import EntityExtractor
from comparison.document_comparator import DocumentComparator, _tokens_significatifs
from rules_engine.rule_checker import RuleChecker
from legal_kb.knowledge_base import LegalKnowledgeBase
from report_generator.report_builder import ReportBuilder
from report_generator.report_export import (
    TYPE_LABELS_HUMAIN,
    INCOH_TYPE_HUMAIN,
    SEVERITE_HUMAIN,
    NATURE_CONTROLE_HUMAIN,
    CONTROLE_FONDEMENT,
    points_cles_document,
)
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

# Où chercher la société concernée par un document : dénomination (statuts),
# en-tête « MAJ STATUTS », titre du pacte, préambule « la société X (la
# « Société ») ». Le préfixe est insensible à la casse (?i:...) mais la capture
# est volontairement sensible : seules les séquences EN MAJUSCULES sont
# retenues, ce qui arrête la lecture avant le corps du texte
# (« Avertissement... », etc.) et évite d'attraper des mots courants.
_PATTERNS_DENOMINATION = (
    # « la dénomination de la SARL est X » / « dénomination sociale : X »
    re.compile(
        r"(?i:d[ée]nomination(?:\s+sociale)?"
        r"(?:\s+de\s+(?:la\s+)?(?:soci[ée]t[ée]|sarl|sas|sa|sci))?"
        r"\s*(?:est|sera)?\s*[:\-]?\s*)"
        r"([A-ZÀ-ÖØ-Ý]{2,}(?:[\s-][A-ZÀ-ÖØ-Ý]{2,}){0,6})",
    ),
    # en-tête « MAJ STATUTS » : le nom de la société précède « MAJ STATUTS »
    re.compile(
        r"([A-ZÀ-ÖØ-Ý]{2,}(?:[\s-][A-ZÀ-ÖØ-Ý]{2,}){0,6})\s+(?i:MAJ\s+STATUTS)"
    ),
    # titre du pacte : « PACTE D'ASSOCIÉS X » / « PACTE D'ACTIONNAIRES X »
    # (apostrophe ASCII ou typographique)
    re.compile(
        r"(?i:PACTE\s+D['’]?(?:ASSOCI[ÉE]S|ASSOCIES|ACTIONNAIRES)\s+)"
        r"([A-ZÀ-ÖØ-Ý0-9]{2,}(?:[\s-][A-ZÀ-ÖØ-Ý0-9]{2,}){0,6})",
    ),
    # préambule : « la société X (la « Société ») »
    re.compile(
        r"(?i:la\s+soci[ée]t[ée]\s+)"
        r"([A-ZÀ-ÖØ-Ý]{2,}(?:[\s-][A-ZÀ-ÖØ-Ý]{2,}){0,6})\s*\(la\s*[«\"']?\s*(?i:Soci[ée]t[ée])"
    ),
)


def _noms_societes_candidats(text: str) -> list[str]:
    """Noms de société repérés dans un document (titre, dénomination, préambule)."""
    candidats: list[str] = []
    for pattern in _PATTERNS_DENOMINATION:
        for m in pattern.finditer(text):
            nom = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(".,;:")
            if nom and nom not in candidats:
                candidats.append(nom)
    return candidats


def _societes_comparables(noms_a: list[str], noms_b: list[str]) -> bool:
    """Vrai si les deux documents concernent probablement la même société.

    On compare les mots significatifs des noms de société repérés. Si les
    deux listes sont vides, on ne peut pas conclure : on compare (défaut
    historique). Sinon, il faut au moins un mot significatif commun.
    """
    tokens_a: set[str] = set()
    for nom in noms_a:
        tokens_a |= _tokens_significatifs(nom)
    tokens_b: set[str] = set()
    for nom in noms_b:
        tokens_b |= _tokens_significatifs(nom)
    if not tokens_a or not tokens_b:
        return True
    return bool(tokens_a & tokens_b)


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


def _enrichir_incoherence_fichiers(
    incoherence: dict[str, Any], fichier_a: str, fichier_b: str
) -> None:
    """Rattache chaque incohérence au(x) fichier(s) réel(s) concerné(s).

    Une incohérence de montant est toujours inter-documents : les deux fichiers
    comparés sont impliqués. Les autres incohérences (règle 24 mois, titres de
    capital...) concernent le document de référence indiqué par le comparateur
    (document_reference = "pacte_associes" ou "statuts").
    """
    reference = incoherence.get("document_reference", "")
    if incoherence.get("type") == "montant":
        fichiers = [fichier_a, fichier_b]
    elif reference == "pacte_associes":
        fichiers = [fichier_a]
    elif reference == "statuts":
        fichiers = [fichier_b]
    elif reference == "pacte":
        fichiers = [fichier_a]
    else:
        fichiers = [fichier_a, fichier_b]
    fichiers = list(dict.fromkeys(fichiers))
    incoherence["documents"] = fichiers
    incoherence["document_1"] = fichiers[0]
    incoherence["document_2"] = fichiers[-1] if len(fichiers) > 1 else fichiers[0]


_FIN_PHRASE = re.compile(r"[.!?](?:\s|\n|$)")


def _fin_de_phrase(texte: str, pos: int, max_extra: int = 160) -> int:
    """Prolonge `pos` jusqu'à la fin de la phrase en cours, sans dépasser `max_extra`."""
    reste = texte[pos : min(len(texte), pos + max_extra)]
    for match in _FIN_PHRASE.finditer(reste):
        return pos + match.end()
    return pos


def _extrait_autour(texte: str, mot: str, rayon: int = 180) -> str:
    """Retourne un extrait du texte autour de la première occurrence de `mot`."""
    if not texte or not mot:
        return ""
    idx = texte.lower().find(mot.lower())
    if idx == -1:
        return ""
    debut = max(0, idx - rayon)
    fin = min(len(texte), idx + len(mot) + rayon)
    extrait = texte[debut:fin].strip()
    if debut > 0:
        extrait = "…" + extrait
    if fin < len(texte):
        fin_propre = _fin_de_phrase(texte, fin)
        extrait = extrait + (texte[fin:fin_propre] if fin_propre > fin else "…")
    return extrait


_DEBUT_CONTENU = re.compile(r"[a-zà-ÿ][.!?:…;]?\s+(?=[A-ZÀ-Ý])")


def _abreger_titre(titre: str, max_chars: int = 60) -> str:
    """Raccourcit un intitulé de clause pour un affichage compact.

    Les PDF collent souvent titre et contenu sur la même ligne
    ("Forme juridique La société est une SARL...") : on coupe au début du
    segment capitalisé qui marque le passage au contenu.
    """
    t = titre.strip()
    m = _DEBUT_CONTENU.search(t)
    if m:
        t = t[: m.end()].rstrip(" .-–—")
    if len(t) <= max_chars:
        return t
    coupure = t.rfind(" ", 0, max_chars)
    if coupure <= 0:
        coupure = max_chars
    return t[:coupure].rstrip(" .-–—") + "…"


def _contexte_pour_finding(
    finding: dict[str, Any],
    doc_keys: list[str],
    documents: dict[str, str],
    clauses: dict[str, list],
) -> str:
    """Extrait un passage du document source utile à l'avocat.

    - Pour une clause manquante : liste (courte) des clauses présentes dans le
      document, le périmètre de recherche de la règle.
    - Pour les autres anomalies : cite le passage contenant le mot-clé du
      problème (ex. la clause de veto, la clause de non-concurrence).
    """
    mots = [
        m for m in dict.fromkeys(_tokens(str(finding.get("explication", ""))))
        if len(m) >= 5
    ]
    if finding.get("type") != "clause_manquante":
        for k in doc_keys:
            texte = documents.get(k, "")
            for mot in mots:
                extrait = _extrait_autour(texte, mot)
                if extrait:
                    return f"{k} — {extrait}"

    titres: list[str] = []
    vus: set[str] = set()
    for k in doc_keys:
        for clause in clauses.get(k, []):
            titre = _abreger_titre(str(clause.get("titre", "")))
            if titre and titre not in vus:
                vus.add(titre)
                titres.append(titre)
    if titres:
        if len(titres) > 6:
            titres = titres[:6] + ["…"]
        return "Clauses identifiées dans le document : " + " · ".join(titres)
    return ""


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
    incoherences = []
    compare_pair = None
    comparaison_ecartee: str | None = None
    if len(doc_keys) >= 2:
        pacte_keys = [k for k in doc_keys if types_per_doc.get(k) == "pacte"]
        statuts_keys = [
            k for k in doc_keys
            if types_per_doc.get(k) in ("statuts", "modification_statutaire")
        ]
        if pacte_keys and statuts_keys:
            compare_pair = (pacte_keys[0], statuts_keys[0])
        else:
            compare_pair = (doc_keys[0], doc_keys[1])
        # Garde-fou : on ne compare que des documents qui concernent la même
        # société. Comparer un pacte de la société A avec les statuts de la
        # société B produirait des incohérences sans objet (faux positifs).
        candidats_a = _noms_societes_candidats(documents[compare_pair[0]])
        candidats_b = _noms_societes_candidats(documents[compare_pair[1]])
        if _societes_comparables(candidats_a, candidats_b):
            comparator = DocumentComparator(
                extraction_per_doc[compare_pair[0]],
                extraction_per_doc[compare_pair[1]],
            )
            incoherences = comparator.compare_all()
            for inc in incoherences:
                _enrichir_incoherence_fichiers(inc, compare_pair[0], compare_pair[1])
        else:
            incoherences = []
            comparaison_ecartee = (
                f"Documents de sociétés différentes : « {candidats_a[0]} » "
                f"vs « {candidats_b[0]} ». La comparaison automatique a été "
                f"écartée pour éviter de faux positifs."
            )
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
        # Les règles comparatives (pacte vs statuts) ne s'appliquent qu'à des
        # documents de la même société : croiser deux sociétés différentes
        # produirait de faux positifs (« capital différent », « gérant absent »...).
        comparer_documents = True
        if pacte_keys and statuts_keys:
            candidats_pacte = _noms_societes_candidats(documents[pacte_keys[0]])
            candidats_statuts = _noms_societes_candidats(documents[statuts_keys[0]])
            comparer_documents = _societes_comparables(candidats_pacte, candidats_statuts)
            if not comparer_documents:
                comparaison_ecartee = (
                    f"Documents de sociétés différentes : « {candidats_pacte[0]} » "
                    f"vs « {candidats_statuts[0]} ». Les règles comparatives du "
                    f"moteur de contrôle ont été écartées (les règles propres à "
                    f"chaque document restent appliquées)."
                )
        rule_checker = RuleChecker(pacte_data, statuts_data, comparer_documents=comparer_documents)
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
        concerne = f.get("document_concerne", "")
        contexte_keys = _documents_verifier(concerne)
        builder.add_anomalie({
            "explication": f.get("explication", ""),
            "nature_controle": f.get("type", ""),
            "priorite": f.get("priorite", ""),
            "consequence": f.get("explication", ""),
            "source_juridique": f.get("reference_juridique", ""),
            "correction_recommandee": f.get("correction_recommandee", ""),
            "documents_a_verifier": _documents_verifier(concerne),
            "validation_requise": "oui" if f.get("validation_requise") == "juriste" else "non",
            "base_juridique": kb_refs_par_finding[idx] if idx < len(kb_refs_par_finding) else [],
            "contexte": _contexte_pour_finding(f, contexte_keys, documents, clauses_per_doc),
        })

    report = builder.build()
    if comparaison_ecartee:
        report["comparaison_ecartee"] = comparaison_ecartee
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

    docs_by_name = {
        d.get("nom", ""): d.get("type", "") for d in report.get("documents_analyses", [])
    }

    lines.append("## Documents Analysees\n")
    for doc in report.get("documents_analyses", []):
        type_doc = doc.get('type', '')
        label = TYPE_LABELS_HUMAIN.get(type_doc, type_doc or "Non reconnu")
        lines.append(f"- **{doc.get('nom', 'N/A')}** — {label}")

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
            "> **Note :** aucun document de type pacte d'associés, statuts, "
            "procès-verbal ou modification statutaire n'a été détecté. Les vérifications "
            "propres à ces documents ne sont donc pas effectuées, et aucune anomalie "
            "de pacte/statuts n'est rapportée.\n"
        )

    statuts_lecture = infos.get("statut_lecture", {})
    if statuts_lecture:
        labels = {
            "natif": "texte lisible",
            "ocr": "scan numérisé (texte reconstitué)",
            "ocr_indisponible": "scan sans texte (à vérifier)",
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
        nb_liees = sources.get("anomalies_liees_a_legifrance", 0)
        nb_fictives = sources.get("anomalies_reference_fictive", 0)
        ligne_source = f"{nb_liees} anomalie(s) liée(s) à Légifrance"
        if nb_fictives:
            ligne_source += f" | {nb_fictives} référence(s) introuvable(s) (à vérifier)"
        lines.append(f"\n**Sources officielles :** {ligne_source}\n")

    synthese = report.get("synthese_intelligente")
    if synthese:
        lines.append("## Synthèse de l'analyse\n")
        lines.append(synthese + "\n")

    anomalies = report.get("anomalies_juridiques", [])
    if anomalies:
        lines.append("## Anomalies Juridiques\n")
        for i, a in enumerate(anomalies, 1):
            priorite = a.get("priorite", "").upper()
            nature_label = NATURE_CONTROLE_HUMAIN.get(
                a.get("nature_controle", ""), a.get("nature_controle", "Anomalie")
            )
            lines.append(f"### Anomalie {i} — {nature_label} [{priorite}]\n")
            lines.append(f"**Explication :** {a.get('explication', '')}\n")
            if a.get("statut_validation") == "modifie":
                lines.append("*✏️ Texte corrigé par le juriste (voir section Validation humaine).*")
            fondement = CONTROLE_FONDEMENT.get(a.get("nature_controle", ""))
            if fondement:
                lines.append(f"- **Contrôle :** {fondement}")
            if a.get("contexte"):
                lines.append(f"- **Contexte dans le document :** {a['contexte']}")
            if a.get("source_juridique"):
                lines.append(f"- **Source :** {a.get('source_juridique', '')}")
            if a.get("source_statut") == "verifiee":
                lines.append(f"- **Vérification :** texte retrouvé dans Légifrance")
                if a.get("texte_officiel"):
                    t = a["texte_officiel"]
                    tc = a.get("texte_officiel_complet", "")
                    tronque = bool(tc) and len(tc) > len(t)
                    libelle = "Texte officiel (extrait)" if tronque else "Texte officiel (article complet)"
                    lines.append(f"- **{libelle} :** «{t}{'…' if tronque else ''}»")
                texte_complet = a.get("texte_officiel_complet", "")
                if texte_complet and len(texte_complet) > len(a.get("texte_officiel", "") or ""):
                    lines.append(f"- **Texte officiel complet :** {texte_complet}")
            docs_verif = a.get("documents_a_verifier", [])
            if docs_verif:
                libelles = []
                for dv in docs_verif:
                    type_doc = TYPE_LABELS_HUMAIN.get(docs_by_name.get(dv, ""), docs_by_name.get(dv, ""))
                    libelles.append(f"{type_doc} ({dv})" if type_doc else dv)
                pluriel = "Document concerné" if len(libelles) == 1 else "Documents concernés"
                lines.append(f"- **{pluriel} :** {', '.join(libelles)}")
            lines.append(f"- **Correction :** {a.get('correction_recommandee', '')}")
            lines.append("")

    validations = report.get("validations_appliquees", [])
    if validations:
        lines.append("## Validation Humaine\n")
        statut_labels = {
            "approuve": "Approuvée",
            "rejete": "Rejetée",
            "modifie": "Modifiée",
        }
        for v in validations:
            label = statut_labels.get(v.get("statut"), v.get("statut", ""))
            lignes_val = [
                f"### Anomalie {v.get('numero', '')} — {v.get('nature', 'Anomalie')} [{label}]",
                f"- **Statut :** {label}",
            ]
            if v.get("commentaire_juriste"):
                lignes_val.append(f"- **Commentaire du juriste :** {v['commentaire_juriste']}")
            if v.get("motif_rejet"):
                lignes_val.append(f"- **Motif du rejet :** {v['motif_rejet']}")
            nc = v.get("nouveau_contenu") or {}
            if nc.get("explication"):
                lignes_val.append(f"- **Texte corrigé :** {nc['explication']}")
            if nc.get("correction_recommandee"):
                lignes_val.append(f"- **Correction recommandée (modifiée) :** {nc['correction_recommandee']}")
            lines.extend(lignes_val)
            lines.append("")

    incoherences = report.get("incoherences", [])
    if incoherences:
        lines.append("## Incoherences Entre Documents\n")
        for inc in incoherences:
            type_label = INCOH_TYPE_HUMAIN.get(inc.get("type", ""), inc.get("type", ""))
            sev = inc.get("severite", "")
            sev_label = SEVERITE_HUMAIN.get(sev, sev)
            documents = inc.get("documents") or []
            if len(documents) == 1:
                loc = f" — Fichier concerné : **{documents[0]}**"
            elif len(documents) >= 2:
                loc = f" — Concerne les 2 fichiers : **{documents[0]}** et **{documents[1]}**"
            else:
                loc = ""
            valeurs = ""
            if inc.get("valeur_pacte") or inc.get("valeur_statuts"):
                valeurs = f" (pacte : {inc.get('valeur_pacte', 'N/A')} / statuts : {inc.get('valeur_statuts', 'N/A')})"
            ligne = f"- **{type_label}** ({sev_label}) : {inc.get('description', '')}{valeurs}{loc}"
            lines.append(ligne)

    analyses = report.get("analyses_clauses", [])
    if analyses:
        a_risque = [a for a in analyses if a.get("niveau_risque") != "faible"]
        lines.append("## Analyse des Clauses\n")
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
        lines.append("\n## Points Cles des Documents\n")
        for doc_name, doc_entites in entites.items():
            lines.append(f"### {doc_name}\n")
            for label, valeurs in points_cles_document(doc_entites):
                if valeurs:
                    lines.append(f"- **{label} :** {', '.join(valeurs)}")
            lines.append("")

    return "\n".join(lines)
