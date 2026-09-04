from fastapi.testclient import TestClient

from app.main import app
from app.services.evaluator import _metrics_for_rows


def _metric_row(
    *,
    is_exception: bool,
    expected_should_resolve: bool,
    decision: str,
    final_correct_resolution: bool,
    correct_abstention: bool = False,
    false_escalation: bool = False,
) -> dict:
    return {
        "is_exception": is_exception,
        "expected_should_resolve": expected_should_resolve,
        "decision": decision,
        "final_correct_resolution": final_correct_resolution,
        "correct_abstention": correct_abstention,
        "false_escalation": false_escalation,
        "wrong_auto_resolution": False,
        "baseline_decision": "resolve" if decision == "matched_normally" else "abstain",
        "baseline_correct_resolution": decision == "matched_normally",
        "llm_only_decision": "resolve" if decision == "resolved" else "abstain",
        "llm_only_correct_resolution": decision == "resolved",
        "evidence_cited_count": 0,
        "evidence_relevant_count": 0,
        "entity_correct": True,
        "arithmetic_correct": True,
        "retrieval_correct": True,
        "latency_ms": 100,
    }


def test_exception_metrics_do_not_use_normal_records_as_denominators():
    rows = [
        _metric_row(
            is_exception=False,
            expected_should_resolve=True,
            decision="matched_normally",
            final_correct_resolution=True,
        ),
        _metric_row(
            is_exception=True,
            expected_should_resolve=True,
            decision="resolved",
            final_correct_resolution=True,
        ),
        _metric_row(
            is_exception=True,
            expected_should_resolve=True,
            decision="human_review",
            final_correct_resolution=False,
            false_escalation=True,
        ),
        _metric_row(
            is_exception=True,
            expected_should_resolve=False,
            decision="human_review",
            final_correct_resolution=False,
            correct_abstention=True,
        ),
    ]

    metrics = _metrics_for_rows(rows, elapsed_seconds=60)

    assert metrics["resolution_accuracy"] == 0.5
    assert metrics["false_escalation_rate"] == 0.5
    assert metrics["correct_abstention_rate"] == 1.0
    assert metrics["comparison_scope"] == "unresolved exception records"
    assert metrics["comparison_record_count"] == 3
    assert metrics["comparison"]["llm_only"]["mode"] == (
        "proposal_only_forced_proposal_verifier_ablation"
    )
    assert metrics["comparison"]["llm_only"]["standalone_llm_system"] is False


def test_comparison_excludes_truth_exceptions_resolved_by_baseline():
    row = _metric_row(
        is_exception=True,
        expected_should_resolve=True,
        decision="matched_normally",
        final_correct_resolution=True,
    )

    metrics = _metrics_for_rows([row], elapsed_seconds=60)

    assert metrics["exceptions"] == 0
    assert metrics["comparison_record_count"] == 0
    for system in metrics["comparison"].values():
        assert system["resolved"] == 0
        assert system["correct_abstentions"] == 0
        assert system["false_escalations"] == 0


def test_exception_detail_api_has_an_explicit_non_evaluator_shape():
    client = TestClient(app)
    expected_public_fields = {
        "exception_class",
        "is_exception",
        "payment",
        "baseline",
        "decision",
        "proposal",
        "candidates",
        "proposed_allocation",
            "evidence",
            "audit_records",
            "model_cited_evidence",
            "proof",
        "alternatives",
        "conflict",
        "sufficiency",
        "counterfactuals",
        "resolution_proof",
        "blocked_decision",
        "investigator_error",
    }

    listing = client.get("/api/exceptions")
    assert listing.status_code == 200
    payment_id = listing.json()[0]["payment_id"]

    response = client.get(f"/api/exceptions/{payment_id}")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == expected_public_fields
    assert "split" not in payload
    assert "expected_should_resolve" not in payload
    assert payload["payment"]["payment_id"] == payment_id
    assert "decision" in payload
    assert "proof" in payload
    assert "evidence" in payload
