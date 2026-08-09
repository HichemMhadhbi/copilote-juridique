"""Service LLM optionnel : enrichit les reponses et l'analyse juridique.

Les cles API sont lues uniquement depuis l'environnement (.env) via
config_app — aucune cle n'est stockee dans le code.

Design : tout est optionnel.
- Sans cle valide : get_llm_config() retourne None et l'application
  fonctionne exactement comme avant (regles + recherche locale).
- Avec une cle : Groq est utilise en priorite, OpenRouter en secours.
- Si l'appel echoue, expire (timeout) ou renvoie un contenu inutilisable :
  call_llm() retourne None et l'application retombe sur le comportement local.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Any

from config_app import (
    ENV_API_KEYS,
    LLM_MAX_TOKENS,
    LLM_MODELS,
    LLM_TIMEOUT,
    OPENROUTER_BASE_URL,
)

logger = logging.getLogger(__name__)

_SYSTEM_CHAT = (
    "Tu es « Copilote juridique », un assistant juridique francophone specialise "
    "dans l'analyse de documents. Tu reponds UNIQUEMENT a partir des extraits et "
    "informations fournis. Si l'information demandee n'y figure pas, dis-le "
    "honnetement plutot que d'inventer.\n"
    "Respecte strictement ce format de reponse Markdown leger :\n"
    "- Titres en **gras** suivis de « : » (ex. **Synthèse :**)\n"
    "- Listes a puces avec « - »\n"
    "- Citations des extraits dans un bloc precede de « > » (une ligne par extrait)\n"
    "- Termine par « --- » puis une note de quelques mots sur la source.\n"
    "Interdit : tableaux, titres « # », blocs de code, tout Markdown complexe."
)

_SYSTEM_CLAUSE = (
    "Tu es un expert juridique senior specialise en droit des societes.\n"
    "Analyse la clause fournie (titre + contenu) et reponds UNIQUEMENT en JSON, "
    "sans texte autour, avec exactement ces 4 champs :\n"
    "{\"niveau_risque\": \"faible\" ou \"modere\" ou \"eleve\", "
    "\"analyse\": \"<1-2 phrases sur le risque juridique concret>\", "
    "\"amelioration_argmentee\": \"<1-2 phrases proposant une amelioration concrete et argumentee>\", "
    "\"fondement\": \"<article de loi pertinent, vide si aucun>\"}\n"
    "Si la clause est conforme et sans risque particulier, mets niveau_risque a \"faible\". "
    "N'invente aucune information absente de la clause."
)

# Analyse locale (repli deterministe, sans LLM) : motif normalise -> (niveau,
# analyse, amelioration, fondement). L'analyse IA enrichit ce socle lorsque
# une cle valide est configuree ; sinon ce socle garantit un rendu utile.
_LOCAL_RISKS: list[tuple[str, str, str, str, str]] = [
    (
        "veto",
        "eleve",
        "Droit de veto : risque de paralysie des decisions si son perimetre n'est pas borne.",
        "Limiter le veto aux decisions strategiques listees dans les statuts (cession, fusion, dissolution) et prevoir un mecanisme de leve de blocage.",
        "Art. L223-27 / Art. L227-9",
    ),
    (
        "non-concurrence",
        "modere",
        "Clause de non-concurrence : risque de nullite si la clause n'est pas limitee dans le temps et dans l'espace.",
        "Limiter la duree a 2 ans maximum, definir un perimetre geographique et prevoir une contrepartie pour rester proportionnee.",
        "Art. 1103 C. civ + jurisprudence",
    ),
    (
        "agrement",
        "modere",
        "Clause d'agrement : risque d'ambiguite si la majorite requise ou les delais de reponse ne sont pas precises.",
        "Preciser la majorite d'agrement, les delais de reponse et de rachat, et l'organe competent (conformite L.223-14 ou L.228-23).",
        "Art. L223-14 / Art. L228-23",
    ),
    (
        "cession",
        "modere",
        "Cession de parts ou d'actions : verifier la conformite de la procedure (offre, agrement, preemption).",
        "Detailer la procedure de cession et les droits de preference ou de preemption associes.",
        "Art. L223-14 / Art. L228-23",
    ),
    (
        "sortie",
        "modere",
        "Clause de sortie (drag/tag-along) : risque d'asymetrie de prix ou de conditions entre les associes.",
        "Garantir un prix et des conditions identiques entre majoritaire et minoritaire et definir le seuil de declenchement.",
        "Art. 1103 C. civ",
    ),
    (
        "valorisation",
        "eleve",
        "Valorisation des titres en cas de sortie : risque d'insecurite juridique si la methode d'evaluation n'est pas definie.",
        "Definir la methode de valorisation (reference a l'Art. 1843-4 C. civ ou expert independant) et la procedure en cas de desaccord.",
        "Art. 1843-4 C. civ",
    ),
    (
        "impaye",
        "modere",
        "Clause en cas de non-paiement : verifier la mise en œuvre d'une clause resolutoire (sommation prealable).",
        "Prevoir une mise en demeure et un delai avant toute resolution, conformement a l'Art. 1225 C. civ.",
        "Art. 1225 C. civ",
    ),
    (
        "resolutoire",
        "modere",
        "Clause resolutoire : risque si la resolution opere sans mise en demeure prealable.",
        "Ajouter une mise en demeure restee sans effet dans un delai determine avant toute resolution.",
        "Art. 1225 C. civ",
    ),
    (
        "deces",
        "modere",
        "Deces d'un associe : risque si le sort des parts (agrement des heritiers ou rachat) n'est pas organise.",
        "Prevoir le sort des parts en cas de deces (agrement des heritiers ou rachat), conforme a la forme sociale.",
        "Art. L223-13 / Art. L227-9",
    ),
    (
        "incapacite",
        "modere",
        "Incapacite d'un associe : risque si la continuite de la societe n'est pas assuree.",
        "Organiser la representation ou le rachat des parts de l'associe frappe d'incapacite.",
        "Art. L223-13 / Art. L227-9",
    ),
    (
        "penalite",
        "modere",
        "Penalites ou sanctions prevues : risque d'exces ou de clause abusive.",
        "Verifier la proportionnalite des penalites au regard du prejudice subi.",
        "Art. 1231-5 C. civ",
    ),
]


def _normaliser(texte: str) -> str:
    """Normalise en minuscules sans accents et sans tirets.

    Robustesse aux extractions PDF : « non-concurrence » et « non concurrence »
    doivent etre considérés identiques.
    """
    if not texte:
        return ""
    texte = texte.replace("-", " ")
    return "".join(
        c for c in unicodedata.normalize("NFD", texte.lower())
        if unicodedata.category(c) != "Mn"
    )


def analyser_clause(titre: str, contenu: str) -> dict[str, Any]:
    """Analyse une clause : niveau de risque + analyse + amelioration argumentee.

    Essaye d'abord le LLM (reponse JSON stricte) ; en l'absence de cle valide,
    d'echec ou de JSON inexploitable, retombe sur une analyse locale
    deterministe (toujours disponible, sans reseau). Le resultat est un dict :
    {titre, niveau_risque, analyse, amelioration_argmentee, fondement}.
    """
    texte = f"{titre}\n{contenu}"
    if get_llm_config() is not None:
        try:
            brut = call_llm(_SYSTEM_CLAUSE, f"Clause : {titre}\nContenu : {contenu}\n")
            data = _parse_clause_json(brut)
            if data:
                data["titre"] = data["titre"] or titre
                return data
        except Exception:
            pass
    return _analyse_clause_locale(titre, contenu)


def _parse_clause_json(brut: str | None) -> dict[str, Any] | None:
    """Parse la reponse JSON du LLM (tolere les blocs de code markdown)."""
    if not brut:
        return None
    texte = brut.strip()
    if texte.startswith("```"):
        texte = re.sub(r"^```[a-zA-Z]*\s*", "", texte)
        texte = re.sub(r"\s*```$", "", texte)
    try:
        data = json.loads(texte)
    except (ValueError, TypeError):
        m = re.search(r"\{.*\}", texte, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except ValueError:
            return None
    if not isinstance(data, dict):
        return None
    niveau = str(data.get("niveau_risque", "")).strip().lower()
    if niveau not in ("faible", "modere", "eleve"):
        return None
    return {
        "titre": str(data.get("titre") or ""),
        "niveau_risque": niveau,
        "analyse": str(data.get("analyse") or "").strip(),
        "amelioration_argmentee": str(data.get("amelioration_argmentee") or "").strip(),
        "fondement": str(data.get("fondement") or "").strip(),
    }


def _analyse_clause_locale(titre: str, contenu: str) -> dict[str, Any]:
    """Analyse deterministe d'une clause a partir de motifs normalises.

    Le risque le plus grave l'emporte (eleve > modere > faible) afin de
    remonter en priorite le danger le plus structurant pour la societe.
    """
    texte = _normaliser(f"{titre} {contenu}")
    risques = [
        r for r in _LOCAL_RISKS
        if _normaliser(r[0]) in texte
    ]
    if risques:
        def _poids(niveau: str) -> int:
            return {"eleve": 3, "modere": 2, "faible": 1}.get(niveau, 0)

        meilleur = max(risques, key=lambda r: _poids(r[1]))
        _, niveau, analyse, amelioration, fondement = meilleur
        return {
            "titre": titre,
            "niveau_risque": niveau,
            "analyse": analyse,
            "amelioration_argmentee": amelioration,
            "fondement": fondement,
        }
    return {
        "titre": titre,
        "niveau_risque": "faible",
        "analyse": "Clause conforme au regard des motifs de controle usuels ; aucune anomalie evidente relevee.",
        "amelioration_argmentee": "Aucune amelioration requise ; une relecture juridique reste recommandee.",
        "fondement": "",
    }


_SYSTEM_ANALYSE = (
    "Tu es un expert juridique senior. A partir du rapport d'analyse automatique "
    "(regles + entites) et du debut du texte du document, redige une « Synthese "
    "intelligente » en francais, professionnelle et neutre, structuree ainsi :\n"
    "**Synthèse exécutive :** 2-3 phrases.\n"
    "**Points clés :**\n"
    "- ... (3 a 6 puces)\n"
    "**Recommandations :**\n"
    "- ... (2 a 4 puces, uniquement si des points d'attention existent, sinon une "
    "phrase indiquant qu'aucune anomalie n'est a corriger)\n"
    "Respecte strictement ce format Markdown leger (pas de tableaux, pas de « # »). "
    "Ne fabrique AUCUNE information absente du rapport."
)


def get_llm_config() -> dict[str, str] | None:
    """Retourne la config du fournisseur disponible (Groq prioritaire) ou None.

    Les cles dont le format est manifestement invalide sont ignorees afin
    d'eviter tout appel reseau et de retomber immediatement sur le mode local.
    """
    groq_key = (ENV_API_KEYS.get("Groq") or "").strip()
    if groq_key.startswith("gsk_"):
        return {"provider": "groq", "api_key": groq_key, "model": LLM_MODELS["Groq"]}
    openrouter_key = (ENV_API_KEYS.get("OpenRouter") or "").strip()
    if openrouter_key.startswith("sk-or-v1-"):
        return {
            "provider": "openrouter",
            "api_key": openrouter_key,
            "model": LLM_MODELS["OpenRouter"],
        }
    return None


def call_llm(system_prompt: str, user_prompt: str) -> str | None:
    """Appelle le fournisseur disponible. Retourne None en cas d'erreur/d'absence de cle."""
    cfg = get_llm_config()
    if cfg is None:
        return None
    try:
        if cfg["provider"] == "groq":
            content = _call_groq(cfg, system_prompt, user_prompt)
        else:
            content = _call_openrouter(cfg, system_prompt, user_prompt)
    except Exception as exc:
        logger.warning("Appel LLM (%s) echoue (%s) -> repli local", cfg["provider"], type(exc).__name__)
        return None
    if content and content.strip():
        return content.strip()
    return None


def _call_groq(cfg: dict[str, str], system: str, user: str) -> str | None:
    from groq import Groq

    client = Groq(api_key=cfg["api_key"], timeout=LLM_TIMEOUT)
    resp = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=LLM_MAX_TOKENS,
    )
    return getattr(resp.choices[0].message, "content", None)


def _call_openrouter(cfg: dict[str, str], system: str, user: str) -> str | None:
    from openai import OpenAI

    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=cfg["api_key"],
        timeout=LLM_TIMEOUT,
    )
    resp = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=LLM_MAX_TOKENS,
    )
    return getattr(resp.choices[0].message, "content", None)


def _collect_entities(entites: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    dates: list[str] = []
    parties: list[str] = []
    montants: list[str] = []
    for doc_entites in entites.values():
        for d in doc_entites.get("dates", []):
            dates.append(d.get("valeur", ""))
        for p in doc_entites.get("parties", []):
            parties.append(p.get("nom", ""))
        for m in doc_entites.get("montants", []):
            montants.append(m.get("valeur", ""))
    uniq = lambda items: list(dict.fromkeys(x for x in items if x))
    return uniq(dates), uniq(parties), uniq(montants)


def _build_report_context(report: dict[str, Any]) -> str:
    infos = report.get("informations_principales", {})
    entites = infos.get("entites_extraites", {})
    dates, parties, montants = _collect_entities(entites)
    anomalies = report.get("anomalies_juridiques", [])
    incoherences = report.get("incoherences", [])
    docs = report.get("documents_analyses", [])
    risque = report.get("niveau_risque_global", "non_evalue")

    context = []
    context.append(f"- Niveau de risque global : {risque}")
    context.append(f"- Documents : {', '.join(d.get('nom', '') for d in docs) or 'aucun'}")
    if dates:
        context.append(f"- Dates : {', '.join(dates)}")
    if parties:
        context.append(f"- Parties/Organisations : {', '.join(parties)}")
    if montants:
        context.append(f"- Montants : {', '.join(montants)}")
    context.append(f"- Anomalies detectees : {len(anomalies)}")
    for a in anomalies[:5]:
        context.append(
            f"  - [{a.get('priorite', '')}] {a.get('nature_controle', '')} : "
            f"{a.get('explication', '')[:200]}"
        )
    if incoherences:
        context.append("- Incoherences :")
        for inc in incoherences[:5]:
            context.append(
                f"  - {inc.get('type', '')} ({inc.get('severite', '')}) : "
                f"{inc.get('description', '')[:200]}"
            )
    return "\n".join(context)


def build_chat_prompt(
    question: str, report: dict[str, Any], excerpts: list[str]
) -> tuple[str, str]:
    """Construit (system, user) pour une reponse de chat enrichie par l'IA."""
    context = _build_report_context(report)
    extraits = "\n".join(f"> {ex}" for ex in excerpts) if excerpts else "Aucun extrait pertinent."

    user = (
        f"Question : {question}\n\n"
        f"Contexte du rapport :\n{context}\n\n"
        f"Extraits pertinents du document :\n{extraits}\n\n"
        "Reponds en francais, de maniere structuree et concise."
    )
    return _SYSTEM_CHAT, user


def generate_analysis_synthesis(report: dict[str, Any], document_text: str) -> str | None:
    """Genere une synthese intelligente du rapport. None si indisponible/echoue."""
    if get_llm_config() is None:
        return None
    context = _build_report_context(report)
    debut = (document_text or "")[:6000].replace("\n", " ").strip()
    user = (
        f"Rapport d'analyse :\n{context}\n\n"
        f"Debut du document :\n> {debut}\n\n"
        "Redige la synthese intelligente demandee."
    )
    return call_llm(_SYSTEM_ANALYSE, user)
