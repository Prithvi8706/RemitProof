import json

from fastapi.testclient import TestClient

from app.main import app
from app.utils import results


client = TestClient(app)


def test_liveness_and_readiness_contracts():
    live = client.get("/live")
    ready = client.get("/ready")
    health = client.get("/health")

    assert live.status_code == 200
    assert live.json() == {"status": "alive"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "ready": True}


def test_dashboard_uses_generated_benchmark_values():
    response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_receipts"] == 80
    assert payload["matched_normally"] == 50
    assert payload["exceptions"] == 30
    assert payload["incorrect_auto_resolution_rate"] == 0
    assert payload["evaluation_mode"] == (
        "cache_only_legacy_identity_unverified_proposal_replay"
    )
    assert payload["cache"]["status"] == "cache_only"
    assert payload["cache"]["hits"] == 30
    assert payload["cache"]["misses"] == 0
    assert payload["cache"]["model_inference_included"] is False
    assert payload["cache"]["proposal_source_identity_verified"] is False
    assert len(payload["recent_exceptions"]) <= 8


def test_exception_list_and_detail():
    listing = client.get("/api/exceptions")

    assert listing.status_code == 200
    assert len(listing.json()) == 30
    payment_id = listing.json()[0]["payment_id"]

    detail = client.get(f"/api/exceptions/{payment_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["payment"]["payment_id"] == payment_id
    assert "proof" in payload
    assert "evidence" in payload
    assert "alternatives" in payload


def test_unknown_exception_returns_404():
    response = client.get("/api/exceptions/PAY_DOES_NOT_EXIST")

    assert response.status_code == 404


def test_exception_detail_separates_model_citations_from_audit_context():
    response = client.get("/api/exceptions/PAY_057")

    assert response.status_code == 200
    payload = response.json()
    cited_ids = {record["evidence_id"] for record in payload["model_cited_evidence"]}
    audit_ids = {record["evidence_id"] for record in payload["audit_records"]}

    assert cited_ids == {"EMAIL_X057", "CUS_X057"}
    assert {"INV_X057A", "INV_X057B", "CR_X057A"}.issubset(audit_ids)
    assert "CR_X057A" in payload["sufficiency"]["missing_required_evidence"]
    assert "CR_X057A" not in cited_ids


def test_benchmark_exposes_held_out_metrics():
    response = client.get("/api/benchmark")

    assert response.status_code == 200
    payload = response.json()
    assert payload["held_out"]["total_receipts"] == 60
    assert payload["arithmetic_correctness"] == 1
    assert payload["retrieval_accuracy"] == 1


def test_missing_artifacts_keep_liveness_up_but_fail_readiness(monkeypatch, tmp_path):
    monkeypatch.setattr(results, "RESULTS_DIR", tmp_path)

    assert client.get("/live").status_code == 200
    assert client.get("/ready").status_code == 503
    assert client.get("/health").status_code == 503
    assert client.get("/api/dashboard").status_code == 503
    assert client.get("/api/benchmark").status_code == 503
    assert client.get("/api/exceptions").status_code == 503


def test_malformed_artifacts_return_controlled_503(monkeypatch, tmp_path):
    (tmp_path / "metrics.json").write_text("{not-json", encoding="utf-8")
    (tmp_path / "details.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(results, "RESULTS_DIR", tmp_path)

    response = client.get("/ready")

    assert response.status_code == 503
    assert "unreadable or malformed" in response.json()["detail"]
    assert client.get("/health").status_code == 503
    assert client.get("/api/benchmark").status_code == 503


def test_invalid_schema_and_cross_artifact_counts_fail_readiness(monkeypatch, tmp_path):
    metrics = results.load_metrics()
    metrics["total_receipts"] = 1
    metrics["exceptions"] = 1
    (tmp_path / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    (tmp_path / "details.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(results, "RESULTS_DIR", tmp_path)

    assert client.get("/ready").status_code == 503
    assert client.get("/health").status_code == 503

    (tmp_path / "metrics.json").write_text("{}", encoding="utf-8")
    assert client.get("/api/benchmark").status_code == 503
