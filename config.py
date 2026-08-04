"""
Configuration centrale du copilote IA TOP-JURIDIQUE.

Définit les modèles LLM, paramètres d'embedding, chemins des bases
de connaissances, et énumérations de priorité / types documentaires.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

# ── Cartographie des modèles LLM ──────────────────────────────────────────

LLM_MODEL_MAP: Final[dict[str, dict[str, str]]] = {
    "groq": {
        "provider": "Groq",
        "model": "llama-3.3-70b-versatile",
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key_env": "GROQ_API_KEY",
    },
    "google_ai": {
        "provider": "Google AI",
        "model": "gemini-2.0-flash",
        "api_url": "https://generativelanguage.googleapis.com/v1beta/models/",
        "api_key_env": "GOOGLE_API_KEY",
    },
    "openrouter": {
        "provider": "OpenRouter",
        "model": "anthropic/claude-sonnet-20241022",
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key_env": "OPENROUTER_API_KEY",
    },
}

# ── Paramètres de chunking / embedding ────────────────────────────────────

CHUNK_SIZE: Final[int] = 1024
CHUNK_OVERLAP: Final[int] = 128
EMBEDDING_MODEL: Final[str] = "sentence-transformers/all-MiniLM-L6-v2"

# ── Chemins des bases de connaissance ─────────────────────────────────────

LEGAL_KB_PATH: Final[str] = "legal_kb/data"
FAISS_INDEX_PATH: Final[str] = "rag/faiss_index"

# ── Énumérations ──────────────────────────────────────────────────────────


class Priorite(str, Enum):
    """Niveaux de priorité des anomalies / alertes."""
    BLOQUANT = "bloquant"
    IMPORTANT = "important"
    ALERTE = "alerte"


class TypeDocument(str, Enum):
    """Types de documents juridiques reconnus par l'outil."""
    PACTE_ASSOCIES = "pacte_associes"
    STATUTS = "statuts"
    CONTRAT_COMMERCIAL = "contrat_commercial"
    CONTRAT_TRAVAIL = "contrat_travail"
    BAIL = "bail"
    REGLEMENT_INTERIEUR = "reglement_interieur"
    PROCES_VERBAL = "proces_verbal"
    MODIFICATION_STATUTAIRE = "modification_statutaire"
    CONVENTION = "convention"
    AUTRE = "autre"
