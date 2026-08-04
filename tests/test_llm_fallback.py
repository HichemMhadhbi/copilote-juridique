"""Tests du repli automatique quand l'IA est indisponible ou echoue.

Les cles sont lues depuis .env ; ces tests forcant l'absence/echec du LLM
pour verifier que le comportement local reste identique.
"""

from services import llm_service
from services.chat_service import answer_question_from_report

REPORT = {
    "niveau_risque_global": "faible",
    "anomalies_juridiques": [],
    "incoherences": [],
    "documents_analyses": [{"nom": "doc.pdf", "type": "autre", "statut": "analyse"}],
    "informations_principales": {
        "document_text": (
            "Contrat de vente. .Montant de 10 000 euros. .Date de signature : "
            "01/02/2024. .La societe SARL Alpha cede ses parts."
        ),
        "entites_extraites": {
            "doc.pdf": {
                "dates": [{"valeur": "01/02/2024"}],
                "parties": [{"nom": "SARL Alpha"}],
                "montants": [{"valeur": "10 000 euros"}],
            }
        },
    },
}


def _fake_config(monkeypatch, enabled: bool):
    if enabled:
        monkeypatch.setattr(
            llm_service, "get_llm_config", lambda: {"provider": "groq", "api_key": "x", "model": "m"}
        )
    else:
        monkeypatch.setattr(llm_service, "get_llm_config", lambda: None)


def test_provider_none_without_keys(monkeypatch):
    _fake_config(monkeypatch, enabled=False)
    assert llm_service.get_llm_config() is None
    assert llm_service.call_llm("system", "user") is None


def test_synthesis_none_without_keys(monkeypatch):
    _fake_config(monkeypatch, enabled=False)
    assert llm_service.generate_analysis_synthesis(REPORT, "texte") is None


def test_answer_falls_back_to_local(monkeypatch):
    _fake_config(monkeypatch, enabled=False)
    answer = answer_question_from_report("Quels sont les montants ?", REPORT)
    assert "Montants identifies" in answer
    assert "10 000 euros" in answer


def test_answer_uses_llm_when_available(monkeypatch):
    _fake_config(monkeypatch, enabled=True)
    monkeypatch.setattr(
        llm_service, "call_llm", lambda system, user: "**Reponse IA** structuree"
    )
    answer = answer_question_from_report("Question test", REPORT)
    assert answer == "**Reponse IA** structuree"


def test_answer_falls_back_when_llm_fails(monkeypatch):
    _fake_config(monkeypatch, enabled=True)
    monkeypatch.setattr(llm_service, "call_llm", lambda system, user: None)
    answer = answer_question_from_report("Quels sont les montants ?", REPORT)
    assert "Montants identifies" in answer
