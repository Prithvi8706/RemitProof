import json
from pathlib import Path

import pytest

from app.utils.loaders import load_dataset, load_ground_truth
from scripts.audit_baseline import (
    EXIT_DRIFT,
    EXIT_OK,
    EXIT_USAGE,
    build_report,
    comparison_rows,
    default_report_path,
    main,
    matches_truth,
    report_bytes,
    summarize,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def report():
    return build_report(load_dataset(REPO_ROOT / "data"), load_ground_truth(REPO_ROOT / "data"))


@pytest.fixture(scope="module")
def published_metrics():
    return json.loads((REPO_ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))


def _row(decision, correct, should_resolve, *, baseline="abstain", is_exception=True):
    return {
        "is_exception": is_exception,
        "expected_should_resolve": should_resolve,
        "rules_only_baseline_decision": baseline,
        "rules_only_baseline_correct_resolution": False,
        "verifier_only_decision": decision,
        "verifier_only_correct_resolution": correct,
    }


def _counts(a, b, c, d, e):
    return {
        "resolved": a,
        "correct_resolutions": b,
        "wrong_auto_resolutions": c,
        "correct_abstentions": d,
        "false_escalations": e,
    }


def test_verifier_only_counts_on_the_legacy_corpus(report):
    assert report["overall"]["comparison_record_count"] == 30
    assert report["overall"]["systems"]["verifier_only"] == _counts(18, 18, 0, 12, 0)
    assert report["by_split"]["dev"]["systems"]["verifier_only"] == _counts(5, 5, 0, 5, 0)
    assert report["by_split"]["benchmark"]["systems"]["verifier_only"] == _counts(
        13, 13, 0, 7, 0
    )


def test_rules_only_scoring_agrees_with_the_published_evaluator(report, published_metrics):
    assert report["overall"]["total_receipts"] == published_metrics["total_receipts"]
    assert (
        report["overall"]["comparison_record_count"]
        == published_metrics["comparison_record_count"]
    )
    assert (
        report["overall"]["systems"]["rules_only_baseline"]
        == published_metrics["comparison"]["baseline"]
    )
    benchmark = published_metrics["synthetic_benchmark_regression"]
    section = report["by_split"]["benchmark"]
    assert section["comparison_record_count"] == benchmark["comparison_record_count"]
    assert section["systems"]["rules_only_baseline"] == benchmark["comparison"]["baseline"]


def test_report_is_bound_to_the_published_dataset_hash(report, published_metrics):
    assert report["dataset_sha256"] == published_metrics["provenance"]["dataset_sha256"]


def test_verifier_only_resolves_a_superset_of_the_published_pipeline(report):
    details = json.loads((REPO_ROOT / "results" / "details.json").read_text(encoding="utf-8"))
    published_resolved = {
        item["payment"]["payment_id"]
        for item in details
        if item["decision"]["decision"] == "resolved"
    }
    verifier_resolved = {
        case["payment_id"]
        for case in report["cases"]
        if case["verifier_only_decision"] == "resolve"
    }
    assert len(published_resolved) == 9
    assert published_resolved <= verifier_resolved


def test_committed_report_is_reproducible(report):
    committed = default_report_path(REPO_ROOT).read_bytes().replace(b"\r\n", b"\n")
    assert committed == report_bytes(report)
    assert main(["--check"]) == EXIT_OK


def test_report_has_no_volatile_fields(report):
    again = build_report(load_dataset(REPO_ROOT / "data"), load_ground_truth(REPO_ROOT / "data"))
    assert report_bytes(again) == report_bytes(report)
    text = report_bytes(report).decode("utf-8")
    for word in ("latency", "elapsed", "timestamp", "generated_at"):
        assert word not in text


def test_cases_are_the_comparison_scope_in_payment_order(report):
    cases = report["cases"]
    ids = [case["payment_id"] for case in cases]
    assert ids == sorted(ids)
    for case in cases:
        assert case["is_exception"] is True
        assert case["rules_only_baseline_decision"] == "abstain"
    assert len(cases) == report["overall"]["comparison_record_count"]


def test_summarize_counts_each_outcome_once():
    rows = [
        _row("resolve", True, True),
        _row("resolve", False, True),
        _row("resolve", False, False),
        _row("abstain", False, True),
        _row("abstain", False, False),
    ]
    assert summarize(rows, "verifier_only") == _counts(3, 1, 2, 1, 1)
    with pytest.raises(ValueError):
        summarize(rows, "llm_only")


def test_comparison_scope_excludes_normal_and_baseline_resolved_records():
    rows = [
        _row("resolve", True, True),
        _row("resolve", True, True, baseline="resolve"),
        _row("resolve", True, True, is_exception=False),
    ]
    assert comparison_rows(rows) == rows[:1]


def test_matches_truth_requires_every_component():
    truth = {
        "should_resolve": True,
        "correct_customer": "C",
        "correct_invoices": ["I1", "I2"],
        "correct_credits": ["K"],
    }
    assert matches_truth("C", ["I2", "I1"], ["K"], truth) is True
    assert matches_truth("D", ["I2", "I1"], ["K"], truth) is False
    assert matches_truth("C", ["I1"], ["K"], truth) is False
    assert matches_truth("C", ["I2", "I1"], [], truth) is False
    assert matches_truth("C", ["I2", "I1"], ["K"], {**truth, "should_resolve": False}) is False


def test_cli_write_check_and_overwrite_guard(tmp_path):
    output = tmp_path / "out" / "report.json"
    base = ["--output", str(output)]
    assert main(["--check"] + base) == EXIT_USAGE
    assert main(["--write"] + base) == EXIT_OK
    assert main(["--check"] + base) == EXIT_OK
    assert main(["--write"] + base) == EXIT_USAGE
    output.write_bytes(output.read_bytes().replace(b'"resolved": 18', b'"resolved": 17'))
    assert main(["--check"] + base) == EXIT_DRIFT
    assert main(["--write", "--force"] + base) == EXIT_OK
    assert main(["--check"] + base) == EXIT_OK
