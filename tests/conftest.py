"""Configuration pytest commune aux tests.

Les tests unitaires ne doivent pas dépendre du réseau ni des identifiants
PISTE : la vérification live des références Légifrance est désactivée ici.
"""

import os

import pytest

os.environ.setdefault("LEGIFRANCE_VERIFY_LIVE", "0")


@pytest.fixture(autouse=True)
def _sans_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force le repli local LLM dans toute la suite.

    Sans cette neutralisation globale, une clé API valide dans .env fait que
    analyse_documents (appelé par test_analysis_service, test_knowledge_base...)
    déclenche un véritable appel LLM : suite lente (retries/timeouts) et
    résultats non déterministes. Ici tous les tests restent hors ligne.
    """
    monkeypatch.setattr("services.llm_service.get_llm_config", lambda: None)
