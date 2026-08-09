"""Configuration globale de l'application TOP-JURIDIQUE."""

import os

from dotenv import load_dotenv

# Charge les cles API depuis le fichier .env (aucune cle dans le code).
load_dotenv()

# Formats supportes
SUPPORTED_FORMATS = {
    "pdf": "PDF",
    "docx": "Word",
    "doc": "Word (.doc)",
    "png": "Image",
    "jpg": "Image",
    "jpeg": "Image",
    "txt": "Texte",
}

# Modeles LLM supportes
SUPPORTED_MODELS = ("Groq", "Google AI", "OpenRouter")

# Parametres RAG
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FAISS_INDEX_PATH = "faiss_index"
QA_SEARCH_K = 10

# Modeles par provider
LLM_MODELS = {
    "Groq": "llama-3.3-70b-versatile",
    "Google AI": "gemini-2.0-flash",
    "OpenRouter": "meta-llama/llama-3.3-70b-instruct",
}

# Parametres des appels LLM (enrichissement optionnel)
LLM_TIMEOUT = 30
LLM_MAX_TOKENS = 1100

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Cles API depuis .env
ENV_API_KEYS = {
    "Groq": os.getenv("GROQ_API_KEY", ""),
    "Google AI": os.getenv("GOOGLE_API_KEY", ""),
    "OpenRouter": os.getenv("OPENROUTER_API_KEY", ""),
}

API_LINKS = {
    "Groq": "https://console.groq.com/keys",
    "Google AI": "https://ai.google.dev/",
    "OpenRouter": "https://openrouter.ai/workspaces/default/keys",
}

# Questions typiques pour l'analyse juridique
TYPICAL_QUESTIONS = {
    "Resume du document": "Resume ce document en 5 points cles.",
    "Parties concernees": "Quelles sont les parties ou personnes mentionnees dans ce document ?",
    "Dates importantes": "Quelles sont les dates importantes citees dans le document ?",
    "Sujets principaux": "Quels sont les grands sujets ou themes abordes dans ce document ?",
    "Definitions et concepts": "Quels sont les termes juridiques ou concepts importants definis dans ce document ?",
    "Obligations et droits": "Quelles sont les obligations ou droits mentionnes dans ce document ?",
    "References legales": "Quelles references a des textes de loi ou articles sont citees ?",
    "Points importants": "Quels sont les points les plus importants a retenir de ce document ?",
    "Organisation judiciaire": "Quelle est l'organisation judiciaire ou les juridictions mentionnees ?",
    "Risques et recommandations": "Quels sont les risques ou recommandations identifies ?",
}
