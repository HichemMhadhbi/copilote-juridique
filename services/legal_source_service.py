"""Service de sources officielles (Légifrance / PISTE).

Objectif : relier chaque anomalie du rapport à une source officielle
sans jamais inventer de référence.

Comportement :
- `legifrance_search_url(reference)` : construit un lien de recherche
  réel vers Légifrance (garanti, fonctionne sans jeton).
- `fetch_article_text(reference)` : si les identifiants PISTE sont
  configurés dans `.env` (PISTE_CLIENT_ID / PISTE_CLIENT_SECRET), obtient
  un jeton OAuth2 (client_credentials) puis interroge l'API Légifrance
  pour récupérer le texte officiel de l'article. En cas d'absence
  d'identifiants ou d'erreur réseau, retourne None (repli local, aucune
  donnée inventée).
- `enrich_report_with_sources(report)` : enrichit chaque anomalie du
  rapport avec un lien Légifrance et une mention de vérification.

Note : l'API PISTE (piste.gouv.fr) nécessite un compte, une application
et l'abonnement à l'API "Légifrance". Deux environnements : prod
(api.piste.gouv.fr) et sandbox (sandbox-api.piste.gouv.fr), sélectionnés
via PISTE_ENV. Les URLs sont personnalisables via PISTE_BASE_URL et
PISTE_OAUTH_URL.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.parse
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

_LEGIFRANCE_SEARCH = "https://www.legifrance.gouv.fr/search/code?tab_selection=code&searchField=ALL&query={q}"

_PISTE_ENV = os.getenv("PISTE_ENV", "prod").strip().lower()
if _PISTE_ENV == "sandbox":
    _PISTE_BASE_URL = os.getenv(
        "PISTE_BASE_URL",
        "https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app",
    )
    _PISTE_OAUTH_URL = os.getenv(
        "PISTE_OAUTH_URL",
        "https://sandbox-oauth.piste.gouv.fr/api/oauth/token",
    )
else:
    _PISTE_BASE_URL = os.getenv(
        "PISTE_BASE_URL",
        "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app",
    )
    _PISTE_OAUTH_URL = os.getenv(
        "PISTE_OAUTH_URL",
        "https://oauth.piste.gouv.fr/api/oauth/token",
    )

_CLIENT_ID = (os.getenv("PISTE_CLIENT_ID", "") or "").strip()
_CLIENT_SECRET = (os.getenv("PISTE_CLIENT_SECRET", "") or "").strip()
_API_KEY = (os.getenv("PISTE_API_KEY", "") or "").strip()
_API_SECRET = (os.getenv("PISTE_API_SECRET", "") or "").strip()
_LEGACY_TOKEN = (os.getenv("LEGIFRANCE_API_TOKEN", "") or "").strip()

_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}

_REF_PATTERN = re.compile(
    r"(?:Art(?:icle)?\.?\s*)?((?:L|R|D)?\.?\s*\d{3,}(?:[-–]\d{1,3})?(?:-[a-zA-Z]+)?)",
    re.IGNORECASE,
)


def normalize_reference(reference: str) -> str:
    """Extrait une référence d'article lisible depuis une chaîne quelconque."""
    if not reference:
        return ""
    match = _REF_PATTERN.search(reference)
    if match:
        return match.group(1).strip().replace(" ", "")
    return reference.strip()


_CODE_HINTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"proc(?:\.|\b)\s*(?:\.)?\s*civ", re.IGNORECASE), "Code de procédure civile"),
    (re.compile(r"c\.?\s*proc", re.IGNORECASE), "Code de procédure civile"),
    (re.compile(r"code\s+de\s+procedure\s+civile", re.IGNORECASE), "Code de procédure civile"),
    (re.compile(r"c\.?\s*civ", re.IGNORECASE), "Code civil"),
    (re.compile(r"code\s+civil", re.IGNORECASE), "Code civil"),
    (re.compile(r"c\.?\s*comm(?:\.|erce)?", re.IGNORECASE), "Code de commerce"),
    (re.compile(r"code\s+de\s+commerce", re.IGNORECASE), "Code de commerce"),
    (re.compile(r"c\.?\s*trav", re.IGNORECASE), "Code du travail"),
    (re.compile(r"code\s+du\s+travail", re.IGNORECASE), "Code du travail"),
    (re.compile(r"c\.?\s*rur", re.IGNORECASE), "Code rural et de la pêche maritime"),
    (re.compile(r"code\s+rural", re.IGNORECASE), "Code rural et de la pêche maritime"),
    (re.compile(r"c\.?\s*conso", re.IGNORECASE), "Code de la consommation"),
    (re.compile(r"code\s+de\s+la\s+consommation", re.IGNORECASE), "Code de la consommation"),
]


def _infer_code(source: str) -> Optional[str]:
    """Déduit le nom officiel d'un code depuis la source de la référence.

    Exemples : "Art. 1103 C. civ" -> "Code civil",
    "Art. 1530 C. proc. civ" -> "Code de procédure civile".
    """
    if not source:
        return None
    for pattern, name in _CODE_HINTS:
        if pattern.search(source):
            return name
    return None


def _default_code(ref: str) -> str:
    """Code par défaut quand la source ne précise pas le code.

    Pour les références de type L/R/D (articles de code), on suppose le
    Code de commerce (documents de sociétés) ; pour les références
    numériques seules, le Code civil.
    """
    if ref and ref[0].upper() in ("L", "R", "D"):
        return "Code de commerce"
    return "Code civil"


def legifrance_search_url(reference: str) -> str:
    """Retourne un lien de recherche Légifrance pour une référence donnée."""
    ref = normalize_reference(reference)
    if not ref:
        return ""
    return _LEGIFRANCE_SEARCH.format(q=urllib.parse.quote(ref))


def piste_configured() -> bool:
    """True si des identifiants PISTE sont configurés dans l'environnement."""
    return bool((_CLIENT_ID and _CLIENT_SECRET) or _LEGACY_TOKEN or _API_KEY)


def piste_mode() -> str:
    """Retourne le mode PISTE : 'oauth', 'api_key', 'token' ou ''."""
    if _CLIENT_ID and _CLIENT_SECRET:
        return "oauth"
    if _LEGACY_TOKEN:
        return "token"
    if _API_KEY:
        return "api_key"
    return ""


def _get_access_token(timeout: int = 15) -> Optional[str]:
    """
    Obtient un jeton OAuth2 (client_credentials) auprès de PISTE.

    Le jeton est mis en cache jusqu'à son expiration. Si un ancien
    jeton simple (LEGIFRANCE_API_TOKEN) ou une API Key est fourni, il
    est utilisé directement.
    """
    now = time.time()
    cached = _token_cache.get("token")
    if cached and _token_cache.get("expires_at", 0) > now + 60:
        return cached

    mode = piste_mode()
    if mode == "token":
        _token_cache.update({"token": _LEGACY_TOKEN, "expires_at": now + 3600})
        return _LEGACY_TOKEN
    if mode == "api_key":
        _token_cache.update({"token": _API_KEY, "expires_at": now + 3600})
        return _API_KEY
    if mode != "oauth":
        return None

    try:
        resp = requests.post(
            _PISTE_OAUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": _CLIENT_ID,
                "client_secret": _CLIENT_SECRET,
                "scope": "openid",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            timeout=timeout,
        )
    except requests.RequestException:
        logger.exception("Echec réseau obtention token PISTE")
        return None

    if resp.status_code != 200:
        logger.warning("Echec obtention token PISTE (HTTP %s)", resp.status_code)
        return None

    try:
        data = resp.json()
        token = data.get("access_token")
    except (ValueError, KeyError):
        logger.warning("Réponse token PISTE illisible")
        return None

    if not token:
        return None
    expires_in = int(data.get("expires_in", 3600))
    _token_cache.update({"token": token, "expires_at": now + expires_in})
    return token


def _search_article(
    ref: str, token: str, code: Optional[str] = None, timeout: int = 15
) -> Optional[str]:
    """
    Recherche un article de code dans Légifrance et retourne son
    identifiant LEGIARTI (ou None si introuvable).
    """
    url = f"{_PISTE_BASE_URL}/search"
    filtres = []
    if code:
        filtres.append({"facette": "NOM_CODE", "valeurs": [code]})
    body = {
        "fond": "CODE_DATE",
        "recherche": {
            "champs": [
                {
                    "typeChamp": "NUM_ARTICLE",
                    "operateur": "ET",
                    "criteres": [
                        {
                            "typeRecherche": "EXACTE",
                            "valeur": ref,
                            "operateur": "ET",
                        }
                    ],
                }
            ],
            "filtres": filtres,
            "pageNumber": 1,
            "pageSize": 10,
            "operateur": "ET",
            "sort": "PERTINENCE",
            "typePagination": "ARTICLE",
        },
    }
    try:
        resp = requests.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=timeout,
        )
    except requests.RequestException:
        logger.exception("Echec réseau recherche Légifrance %s", ref)
        return None
    if resp.status_code != 200:
        logger.warning("Recherche Légifrance %s : HTTP %s", ref, resp.status_code)
        return None

    try:
        data = resp.json()
    except ValueError:
        return None

    results = data.get("results") or []
    if isinstance(results, dict):
        results = results.get("results") or []
    candidates: list[tuple[str, str]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        for section in item.get("sections") or []:
            for extract in section.get("extracts") or []:
                if not isinstance(extract, dict):
                    continue
                numero = str(extract.get("num") or extract.get("title") or "")
                if numero.replace(" ", "").upper() == ref.upper():
                    identifiant = extract.get("id") or ""
                    if identifiant:
                        status = str(extract.get("legalStatus") or item.get("etat") or "")
                        candidates.append((identifiant, status))
    if not candidates:
        return None
    for identifiant, status in candidates:
        if "VIGUEUR" in status.upper():
            return identifiant
    return candidates[0][0]


def _get_article_text(identifiant: str, token: str, timeout: int = 15) -> Optional[str]:
    """Récupère le texte d'un article Légifrance depuis son identifiant."""
    url = f"{_PISTE_BASE_URL}/consult/getArticle"
    body = {"id": identifiant}
    try:
        resp = requests.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=timeout,
        )
    except requests.RequestException:
        logger.exception("Echec réseau consultation article %s", identifiant)
        return None
    if resp.status_code != 200:
        logger.warning("Consultation article %s : HTTP %s", identifiant, resp.status_code)
        return None

    try:
        data = resp.json()
        article = data.get("article") or {}
        texte = article.get("texte") or data.get("texte") or ""
    except ValueError:
        return None
    return texte or None


def fetch_article_text(reference: str, timeout: int = 15) -> Optional[str]:
    """
    Tente de récupérer le texte officiel d'un article via l'API
    Légifrance/PISTE (flux OAuth2).

    Le code (ex. "Code de commerce") est déduit de la source de la
    référence ("Art. 1103 C. civ") ; en l'absence d'indication, un code
    par défaut est utilisé pour éviter de retomber sur un article du
    mauvais code.

    Args:
        reference: Référence d'article (ex. "L223-18" ou "Art. 1103 C. civ").
        timeout: Délai maximum de l'appel en secondes.

    Returns:
        Texte de l'article, ou None si indisponible/erreur (repli local).
    """
    ref = normalize_reference(reference)
    if not ref or not piste_configured():
        return None

    token = _get_access_token(timeout=timeout)
    if not token:
        return None

    code = _infer_code(reference) or _default_code(ref)
    identifiant = _search_article(ref, token, code=code, timeout=timeout)
    if not identifiant:
        logger.info("Article %s introuvable via Légifrance", ref)
        return None

    return _get_article_text(identifiant, token, timeout=timeout)


def _mark_fictif(reference: str) -> bool:
    """True si la référence est marquée fictive (ex. 'Art. L223-18-fictif')."""
    return "fictif" in (reference or "").lower()


_verification_cache: dict[str, Optional[tuple[str, str]]] = {}


def _verifier_reference(
    source: str, timeout: int = 15
) -> tuple[str, Optional[str], Optional[str]]:
    """Vérifie une référence auprès de Légifrance.

    Retourne (statut, identifiant LEGIARTI, texte officiel).
    Statuts possibles : "verifiee", "introuvable", "erreur", "non_configure",
    "vide".
    """
    ref = normalize_reference(source)
    if not ref:
        return ("vide", None, None)

    if ref in _verification_cache:
        cached = _verification_cache[ref]
        if cached is None:
            return ("introuvable", None, None)
        return ("verifiee", *cached)

    if not piste_configured():
        return ("non_configure", None, None)

    token = _get_access_token(timeout=timeout)
    if not token:
        return ("erreur", None, None)

    code = _infer_code(source) or _default_code(ref)
    identifiant = _search_article(ref, token, code=code, timeout=timeout)
    if not identifiant:
        _verification_cache[ref] = None
        return ("introuvable", None, None)

    texte = _get_article_text(identifiant, token, timeout=timeout)
    if not texte:
        return ("erreur", None, None)

    _verification_cache[ref] = (identifiant, texte)
    return ("verifiee", identifiant, texte)


def enrich_report_with_sources(
    report: dict[str, Any], verify_live: Optional[bool] = None
) -> dict[str, Any]:
    """
    Enrichit le rapport avec les liens Légifrance et la vérification des
    sources.

    - Ajoute `legifrance_url` à chaque anomalie dont la source est vérifiable.
    - Si `verify_live` est activé (défaut : variable LEGIFRANCE_VERIFY_LIVE,
      active sauf si elle vaut "0"), interroge l'API PISTE/Légifrance pour
      chaque référence et renseigne `source_verifiee`, `source_statut`,
      `legifrance_id` et `texte_officiel`.
    - Ajoute `informations_principales.sources_officielles` avec l'état
      de la configuration PISTE et le nombre de références liées.

    Args:
        report: Rapport d'analyse (dictionnaire).
        verify_live: Active la vérification live (None = selon l'environnement).

    Returns:
        Le même rapport, enrichi en place.
    """
    if verify_live is None:
        verify_live = os.getenv("LEGIFRANCE_VERIFY_LIVE", "1") != "0"

    liens = 0
    fictives = 0
    verifiees = 0
    for anom in report.get("anomalies_juridiques", []):
        source = anom.get("source_juridique", "")
        if not source:
            continue
        if _mark_fictif(source):
            fictives += 1
            anom["source_verifiee"] = False
            anom["source_statut"] = "fictive"
            continue
        url = legifrance_search_url(source)
        if url:
            anom["legifrance_url"] = url
            liens += 1
        if verify_live:
            statut, identifiant, texte = _verifier_reference(source)
            anom["source_verifiee"] = statut == "verifiee"
            anom["source_statut"] = statut
            if identifiant:
                anom["legifrance_id"] = identifiant
            if texte:
                anom["texte_officiel"] = texte[:400]
            if statut == "verifiee":
                verifiees += 1
        else:
            anom["source_verifiee"] = not _mark_fictif(source)
            anom["source_statut"] = "liee" if url else ""

    infos = report.setdefault("informations_principales", {})
    mode = piste_mode()
    infos["sources_officielles"] = {
        "mode": "piste" if mode else "liens_legifrance",
        "piste_mode": mode or "",
        "piste_token_configured": piste_configured(),
        "anomalies_liees_a_legifrance": liens,
        "anomalies_reference_fictive": fictives,
        "references_verifiees_piste": verifiees,
        "verification_active": bool(verify_live and piste_configured()),
        "avertissement": (
            "Les références marquées 'fictif' doivent être remplacées par de "
            "vraies références vérifiées via Légifrance/PISTE avant production."
        ),
    }
    return report
