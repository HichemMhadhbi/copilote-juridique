"""Lanceur de l'API FastAPI TOP-JURIDIQUE.

Usage :
    python run_api.py

Variables d'environnement (optionnelles) :
    API_HOST   (défaut : 0.0.0.0)
    API_PORT   (défaut : 8000)
"""

from __future__ import annotations

import os

import uvicorn

HOST = os.getenv("API_HOST", "0.0.0.0")
PORT = int(os.getenv("API_PORT", "8000"))


def main() -> None:
    uvicorn.run("api.endpoints:app", host=HOST, port=PORT)


if __name__ == "__main__":
    main()
