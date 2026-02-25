"""
Regression tests for retry budget behavior.

These tests guard against reintroducing nested retry explosions where both
graph/verification layers and provider client retry the same request.
"""
import pytest
import importlib

from app.services import doctor_graph, patient_graph, verification_service
llm_client_module = importlib.import_module("app.services.llm_client")


def test_openai_token_candidates_single_when_fallback_matches_primary(monkeypatch):
    monkeypatch.setattr(
        llm_client_module.settings,
        "openai_compatible_fallback_max_tokens",
        700,
        raising=False,
    )
    assert llm_client_module.LLMClient._openai_compatible_token_candidates(700) == [700]


def test_doctor_graph_retry_config_forces_single_attempt_with_openai_provider(monkeypatch):
    monkeypatch.setattr(doctor_graph.settings, "llm_provider", "openai_compatible", raising=False)
    monkeypatch.setattr(doctor_graph.settings, "llm_retry_max_attempts", 5, raising=False)
    assert doctor_graph._llm_retry_config().max_attempts == 1


def test_doctor_graph_retry_config_honors_setting_for_non_openai_provider(monkeypatch):
    monkeypatch.setattr(doctor_graph.settings, "llm_provider", "vertex", raising=False)
    monkeypatch.setattr(doctor_graph.settings, "llm_retry_max_attempts", 4, raising=False)
    assert doctor_graph._llm_retry_config().max_attempts == 4


def test_patient_graph_retry_config_forces_single_attempt_with_openai_provider(monkeypatch):
    monkeypatch.setattr(patient_graph.settings, "llm_provider", "featherless", raising=False)
    monkeypatch.setattr(patient_graph.settings, "llm_retry_max_attempts", 6, raising=False)
    assert patient_graph._llm_retry_config().max_attempts == 1


def test_verification_retry_config_forces_single_attempt_with_openai_provider(monkeypatch):
    monkeypatch.setattr(verification_service.settings, "llm_provider", "openai", raising=False)
    assert verification_service._verification_retry_config().max_attempts == 1


@pytest.mark.asyncio
async def test_medical_reasoning_node_uses_single_graph_retry_with_openai_provider(monkeypatch):
    captured = {}

    async def _mock_generate(**_kwargs):
        return "Patient appears stable."

    async def _mock_with_circuit_breaker(_breaker, _retry_func, call, **kwargs):
        captured["max_attempts"] = kwargs["config"].max_attempts
        return await call()

    monkeypatch.setattr(doctor_graph.settings, "llm_provider", "openai_compatible", raising=False)
    monkeypatch.setattr(doctor_graph.settings, "llm_retry_max_attempts", 3, raising=False)
    monkeypatch.setattr(doctor_graph.llm_client, "generate", _mock_generate)
    monkeypatch.setattr(doctor_graph, "with_circuit_breaker", _mock_with_circuit_breaker)

    state = {
        "patient_context": "Latest vitals are stable.",
        "query_en": "What's the patient's current status?",
        "image_base64": None,
        "patient_record_images_base64": [],
    }
    await doctor_graph.medical_reasoning_node(state)
    assert captured["max_attempts"] == 1
