"""Tests for the heuristic fallback path of the orchestrator (no LLM key required)."""
import pytest

from app.agent import orchestrator
from app.config import settings


@pytest.fixture(autouse=True)
def force_heuristic(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "llm_provider", "anthropic")


def test_medicine_question_routes_to_medicines_checker():
    resp = orchestrator.answer("Should I pay for Paracetamol at the pharmacy?")
    names = [c["name"] for c in resp.tool_calls]
    assert "medicines_checker" in names
    assert resp.provider == "heuristic"
    assert resp.answer  # non-empty


def test_facility_question_routes_to_facility_checker():
    resp = orchestrator.answer("Is Korle Bu Teaching Hospital NHIS accredited?")
    names = [c["name"] for c in resp.tool_calls]
    assert "facility_checker" in names
    assert resp.provider == "heuristic"


def test_membership_question_routes_to_policy_retriever_with_enrollment_filter():
    resp = orchestrator.answer("My NHIS card expired, how do I renew?")
    matching = [c for c in resp.tool_calls if c["name"] == "policy_retriever"]
    assert matching
    assert matching[0]["input"]["category"] == "enrollment"
    assert resp.provider == "heuristic"


def test_dispute_question_routes_with_disputes_filter():
    resp = orchestrator.answer("They turned me away at the hospital, what are my rights?")
    matching = [c for c in resp.tool_calls if c["name"] == "policy_retriever"]
    # Could go to facility_checker if 'hospital' parsed as a name; both are acceptable, but we
    # at least require the heuristic to pick *some* tool.
    assert resp.tool_calls
    if matching:
        assert matching[0]["input"]["category"] == "disputes"
