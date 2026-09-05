from fastapi.testclient import TestClient

from app.main import app
from app.utils.results import load_metrics


client = TestClient(app)


def test_benchmark_cases_match_published_comparison():
    metrics = load_metrics()
    response = client.get("/api/benchmark/cases")
    assert response.status_code == 200
    payload = response.json()

    assert payload["evaluation_generation_id"] == metrics["evaluation_generation_id"]
    assert payload["result_status"] == metrics["result_status"]
    assert payload["comparator_mode"] == metrics["comparison"]["llm_only"]["mode"]

    summary = payload["summary"]
    comparison = metrics["comparison"]
    assert summary["comparison_record_count"] == metrics["comparison_record_count"]
    assert summary["llm_only_wrong_resolutions"] == comparison["llm_only"]["wrong_auto_resolutions"]
    assert summary["remitproof_wrong_auto_resolutions"] == comparison["remitproof"]["wrong_auto_resolutions"]
    assert summary["recovered_from_baseline"] == comparison["remitproof"]["correct_resolutions"]
    assert summary["correct_abstentions"] == comparison["remitproof"]["correct_abstentions"]
    assert summary["false_escalations"] == comparison["remitproof"]["false_escalations"]

    assert len(payload["cases"]) == metrics["comparison_record_count"]
    for case in payload["cases"]:
        assert case["baseline_decision"] == "human_review"
        assert case["remitproof_decision"] in {"resolved", "human_review"}
        # The verifier regression invariant: nothing wrongly auto-resolved.
        assert case["wrong_auto_resolution"] is False
        if case["llm_only_wrong_resolution"]:
            assert case["remitproof_decision"] == "human_review"

    class_records = sum(item["records"] for item in payload["by_class"])
    assert class_records == metrics["total_receipts"]


def test_benchmark_cases_do_not_expose_truth_labels_beyond_evaluation_fields():
    payload = client.get("/api/benchmark/cases").json()
    allowed = {
        "payment_id", "split", "exception_class", "payer", "amount", "currency",
        "expected_should_resolve", "baseline_decision", "llm_only_decision",
        "llm_only_wrong_resolution", "remitproof_decision",
        "remitproof_correct_resolution", "correct_abstention", "false_escalation",
        "wrong_auto_resolution", "recovered_from_baseline", "reason",
    }
    for case in payload["cases"]:
        assert set(case) == allowed
