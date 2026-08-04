"""
Endpoints API FastAPI pour TOP-JURIDIQUE.

Fournit les routes REST pour l'analyse de documents,
la consultation de rapports et la validation humaine.
"""

from __future__ import annotations

import datetime
import os
import uuid
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="TOP-JURIDIQUE API",
    description="API du copilote juridique IA — Analyse automatisée de documents juridiques",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
# Modèles Pydantic
# ══════════════════════════════════════════════════════════════════════════════

class AnalyzeRequest(BaseModel):
    """Requête d'analyse de documents."""
    mode: str = Field(
        default="complet",
        description="Mode d'analyse : 'rapide', 'complet', ou 'avance'"
    )
    provider: Optional[str] = Field(
        default=None,
        description="Fournisseur LLM à utiliser (groq, google_ai, openrouter)"
    )
    enable_rag: bool = Field(
        default=True,
        description="Activer la recherche RAG sur la base de connaissances"
    )


class AnalyzeResponse(BaseModel):
    """Réponse de l'analyse."""
    report_id: str
    statut: str
    message: str
    date_debut: str
    date_fin: str
    nombre_documents: int
    niveau_risque: str


class FindingValidationRequest(BaseModel):
    """Requête de validation d'un finding."""
    action: str = Field(
        description="Action : 'approuver', 'rejeter', 'modifier'"
    )
    comment: Optional[str] = Field(
        default=None,
        description="Commentaire du juriste"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Motif (requis si action = 'rejeter')"
    )
    new_content: Optional[dict[str, Any]] = Field(
        default=None,
        description="Nouveau contenu (requis si action = 'modifier')"
    )


class FindingValidationResponse(BaseModel):
    """Réponse de validation d'un finding."""
    finding_id: str
    statut: str
    date_validation: str


class ReportResponse(BaseModel):
    """Réponse contenant un rapport complet."""
    rapport_id: str
    date_analyse: str
    documents_analyses: list[dict[str, str]]
    informations_principales: dict[str, Any]
    incoherences: list[dict[str, str]]
    anomalies_juridiques: list[dict[str, Any]]
    clauses_a_risque: list[dict[str, str]]
    clauses_manquantes: list[dict[str, str]]
    ameliorations_proposees: list[dict[str, str]]
    niveau_risque_global: str
    recommandations_finales: list[dict[str, str]]
    points_validation_humaine: list[dict[str, str]]


class HealthResponse(BaseModel):
    """Réponse du health check."""
    statut: str
    version: str
    uptime: str
    fournisseurs_disponibles: list[str]


class ValidationErrorDetail(BaseModel):
    """Détail d'une erreur de validation."""
    detail: str


# ══════════════════════════════════════════════════════════════════════════════
# Stockage en mémoire (pour démo — à remplacer par une base de données)
# ══════════════════════════════════════════════════════════════════════════════

_reports_store: dict[str, dict[str, Any]] = {}
_validations_store: dict[str, dict[str, dict[str, Any]]] = {}
_start_time = datetime.datetime.now()


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health", response_model=HealthResponse, tags=["Système"])
async def health_check() -> HealthResponse:
    """
    Vérifie l'état de santé de l'API.

    Retourne le statut, la version, le temps de fonctionnement
    et la liste des fournisseurs LLM disponibles.
    """
    uptime = datetime.datetime.now() - _start_time
    heures = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)

    fournisseurs = []
    for key in ["groq", "google_ai", "openrouter"]:
        env_key = {
            "groq": "GROQ_API_KEY",
            "google_ai": "GOOGLE_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }.get(key)
        if env_key and os.getenv(env_key):
            fournisseurs.append(key)

    return HealthResponse(
        statut="operational",
        version="1.0.0",
        uptime=f"{heures}h {minutes}min",
        fournisseurs_disponibles=fournisseurs,
    )


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    tags=["Analyse"],
    responses={400: {"model": ValidationErrorDetail}},
)
async def analyze_documents(
    files: list[UploadFile] = File(
        default_factory=list, description="Fichiers PDF à analyser"
    ),
    mode: str = "complet",
    provider: Optional[str] = None,
    enable_rag: bool = True,
) -> AnalyzeResponse:
    """
    Analyse une liste de documents juridiques.

    Utilise la pile unifiee `services/` (extraction avec OCR, classification,
    regles de controle, sources officielles, rapport), identique a celle du
    CLI et de l'interface Streamlit. Accepte un ou plusieurs fichiers PDF.
    """
    from services.document_service import extract_text_from_pdf_with_status
    from services.analysis_service import analyze_documents as run_analysis
    from services import storage_service

    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni.")

    documents: dict[str, str] = {}
    statuses: dict[str, str] = {}
    documents_illisibles: list[str] = []

    for uploaded in files:
        filename = uploaded.filename or "document.pdf"
        content = await uploaded.read()
        text, status = extract_text_from_pdf_with_status(content, filename)
        if not text or len(text.strip()) < 50 or text.startswith("[OCR indisponible"):
            documents_illisibles.append(filename)
            continue
        documents[filename] = text
        statuses[filename] = status

    if not documents:
        raise HTTPException(
            status_code=400,
            detail=(
                "Aucun document exploitable. Illisibles ou trop courts : "
                f"{documents_illisibles or 'aucun'}."
            ),
        )

    report = run_analysis(documents, statuses)
    report_id = report.get("rapport_id") or str(uuid.uuid4())
    report["rapport_id"] = report_id

    try:
        storage_service.save_report(report)
    except Exception:
        pass

    _reports_store[report_id] = report
    _validations_store[report_id] = {}

    date_fin = datetime.datetime.now().isoformat()

    return AnalyzeResponse(
        report_id=report_id,
        statut="termine",
        message=f"Analyse de {len(documents)} document(s) terminée (lecture : {', '.join(sorted(set(statuses.values()))) or 'natif'}).",
        date_debut=datetime.datetime.now().isoformat(),
        date_fin=date_fin,
        nombre_documents=len(documents),
        niveau_risque=report.get("niveau_risque_global", "non_evalue"),
    )


@app.get(
    "/report/{report_id}",
    response_model=ReportResponse,
    tags=["Rapport"],
    responses={404: {"model": ValidationErrorDetail}},
)
async def get_report(report_id: str) -> ReportResponse:
    """
    Récupère un rapport d'analyse par son identifiant.

    Args:
        report_id: Identifiant UUID du rapport.
    """
    from services import storage_service

    report = _reports_store.get(report_id)
    if not report:
        report = storage_service.load_report(report_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Rapport non trouvé : {report_id}",
        )

    return ReportResponse(
        rapport_id=report.get("rapport_id", report_id),
        date_analyse=report.get("date_analyse", ""),
        documents_analyses=report.get("documents_analyses", []),
        informations_principales=report.get("informations_principales", {}),
        incoherences=report.get("incoherences", []),
        anomalies_juridiques=report.get("anomalies_juridiques", []),
        clauses_a_risque=report.get("clauses_a_risque", []),
        clauses_manquantes=report.get("clauses_manquantes", []),
        ameliorations_proposees=report.get("ameliorations_proposees", []),
        niveau_risque_global=report.get("niveau_risque_global", "non_evalue"),
        recommandations_finales=report.get("recommandations_finales", []),
        points_validation_humaine=report.get("points_validation_humaine", []),
    )


@app.post(
    "/validate/{report_id}/{finding_id}",
    response_model=FindingValidationResponse,
    tags=["Validation"],
    responses={404: {"model": ValidationErrorDetail}},
)
async def validate_finding(
    report_id: str,
    finding_id: str,
    request: FindingValidationRequest,
) -> FindingValidationResponse:
    """
    Valide un finding spécifique dans un rapport.

    Actions possibles : approuver, rejeter, modifier.
    """
    from services import storage_service

    if report_id not in _reports_store and not storage_service.load_report(report_id):
        raise HTTPException(
            status_code=404,
            detail=f"Rapport non trouvé : {report_id}",
        )

    # Vérification de l'action
    actions_valides = {"approuver", "rejeter", "modifier"}
    if request.action not in actions_valides:
        raise HTTPException(
            status_code=400,
            detail=f"Action invalide. Actions possibles : {actions_valides}",
        )

    if request.action == "rejeter" and not request.reason:
        raise HTTPException(
            status_code=400,
            detail="Le motif (reason) est requis pour un rejet.",
        )

    if request.action == "modifier" and not request.new_content:
        raise HTTPException(
            status_code=400,
            detail="Le nouveau contenu (new_content) est requis pour une modification.",
        )

    # Construction de la validation
    validation = {
        "finding_id": finding_id,
        "statut": request.action,
        "date_validation": datetime.datetime.now().isoformat(),
    }

    if request.comment:
        validation["commentaire_juriste"] = request.comment
    if request.reason:
        validation["motif_rejet"] = request.reason
    if request.new_content:
        validation["nouveau_contenu"] = request.new_content

    # Stockage
    if report_id not in _validations_store:
        _validations_store[report_id] = {}
    _validations_store[report_id][finding_id] = validation

    return FindingValidationResponse(
        finding_id=finding_id,
        statut=request.action,
        date_validation=validation["date_validation"],
    )
