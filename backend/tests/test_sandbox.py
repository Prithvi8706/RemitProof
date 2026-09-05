import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.sandbox import examples
from app.services.ai_investigator import InvestigatorError


client = TestClient(app)


@pytest.fixture
def scenario():
    return copy.deepcopy(examples()[1]["scenario"])


def test_editable_examples_exercise_actual_pipeline():
    expected = ["matched_normally", "resolved", "human_review"]
    for example, decision in zip(examples(), expected):
        response = client.post("/api/sandbox/investigate", json=example["scenario"])
        assert response.status_code == 200, response.text
        report = response.json()
        assert report["detail"]["decision"]["decision"] == decision
        assert report["stored"] is False
        assert report["simulation_only"] is True
        assert response.headers["cache-control"] == "no-store"


def test_removing_decisive_evidence_changes_resolution_to_review(scenario):
    first = client.post("/api/sandbox/investigate", json=scenario).json()
    scenario["emails"] = []
    second = client.post("/api/sandbox/investigate", json=scenario).json()
    assert first["detail"]["decision"]["decision"] == "resolved"
    assert second["detail"]["decision"]["decision"] == "human_review"
    assert first["input_sha256"] != second["input_sha256"]


def test_untrusted_proposal_cannot_override_money(scenario):
    scenario["payment"]["amount"] = "0.01"
    report = client.post("/api/sandbox/investigate", json=scenario).json()
    assert report["detail"]["decision"]["decision"] == "human_review"
    assert report["detail"]["proof"]["financial_validity"] is False


def test_replayed_bank_payment_is_blocked(scenario):
    scenario["related_payments"] = [{**scenario["payment"], "payment_id": "PAY_REPLAY"}]
    report = client.post("/api/sandbox/investigate", json=scenario).json()
    assert report["detail"]["decision"]["proof"]["duplicate_risk"] is True
    assert report["detail"]["decision"]["decision"] == "human_review"
    assert report["detail"]["proposal"] is None


@pytest.mark.parametrize("mutation", [
    lambda s: s["invoices"].append(s["invoices"][0]),
    lambda s: s["invoices"][0].update(customer_id="UNKNOWN"),
    lambda s: s["proposal"].update(payment_id="OTHER"),
    lambda s: s.update(ground_truth={"should_resolve": True}),
    lambda s: s.update(host="http://internal-service"),
    lambda s: s.update(invoices=s["invoices"] * 9),
])
def test_invalid_records_and_untrusted_controls_are_rejected(scenario, mutation):
    mutation(scenario)
    response = client.post("/api/sandbox/investigate", json=scenario)
    assert response.status_code == 422
    assert all("input" not in error for error in response.json()["detail"])


def test_body_size_and_content_type_boundaries():
    assert client.post("/api/sandbox/investigate", content="x" * 65537, headers={"Content-Type": "application/json"}).status_code == 413
    assert client.post("/api/sandbox/investigate", content="{}").status_code == 415
    assert client.post("/api/sandbox/investigate", content="{", headers={"Content-Type": "application/json"}).status_code == 422


def test_live_disabled_never_silently_replays_a_proposal(scenario, monkeypatch):
    monkeypatch.delenv("SANDBOX_LIVE_AI_ENABLED", raising=False)
    scenario.update(mode="live_ai", proposal=None)
    assert client.post("/api/sandbox/investigate", json=scenario).status_code == 503


def test_live_failure_abstains_and_hides_transport_details(scenario, monkeypatch):
    monkeypatch.setenv("SANDBOX_LIVE_AI_ENABLED", "true")
    def failed(*args, **kwargs):
        raise InvestigatorError("private transport details")
    monkeypatch.setattr("app.api.sandbox.OllamaInvestigator.investigate", failed)
    scenario.update(mode="live_ai", proposal=None)
    response = client.post("/api/sandbox/investigate", json=scenario)
    assert response.status_code == 200
    assert response.json()["detail"]["decision"]["decision"] == "human_review"
    assert response.json()["proposal_source"] == "unavailable"
    assert "private transport details" not in response.text


def test_live_model_proposal_uses_same_verifier(scenario, monkeypatch):
    from app.models import InvestigationProposal
    proposal = InvestigationProposal.model_validate(scenario["proposal"])
    seen = []
    def generated(self, bundle):
        seen.append(bundle.payment.payment_id)
        return proposal
    monkeypatch.setenv("SANDBOX_LIVE_AI_ENABLED", "true")
    monkeypatch.setattr("app.api.sandbox.OllamaInvestigator.investigate", generated)
    scenario.update(mode="live_ai", proposal=None)
    report = client.post("/api/sandbox/investigate", json=scenario).json()
    assert seen == [scenario["payment"]["payment_id"]]
    assert report["proposal_source"] == "live_ai"
    assert report["detail"]["decision"]["decision"] == "resolved"


def test_repeat_runs_do_not_publish_or_mutate_benchmark(scenario):
    root = Path(__file__).resolve().parents[2] / "results"
    assert (root / "current_generation.json").is_file()
    before = {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    first = client.post("/api/sandbox/investigate", json=scenario).json()
    second = client.post("/api/sandbox/investigate", json=scenario).json()
    assert first["input_sha256"] == second["input_sha256"]
    assert first["run_id"] != second["run_id"]
    assert before == {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_busy_process_rejects_then_accepts_after_slots_are_released(scenario):
    from app.api.sandbox import _RUN_SLOTS
    assert _RUN_SLOTS.acquire(blocking=False)
    assert _RUN_SLOTS.acquire(blocking=False)
    try:
        response = client.post("/api/sandbox/investigate", json=scenario)
        assert response.status_code == 429
        assert response.headers["retry-after"] == "5"
    finally:
        _RUN_SLOTS.release()
        _RUN_SLOTS.release()
    assert client.post("/api/sandbox/investigate", json=scenario).status_code == 200
