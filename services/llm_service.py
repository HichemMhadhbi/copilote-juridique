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

import logging
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
