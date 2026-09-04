import copy
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_investigator import InvestigatorError
from app.services.evaluator import CachedInvestigator, evaluate_dataset
from app.utils import results
from app.utils.loaders import Dataset, load_dataset, load_ground_truth
from scripts.evaluate import _csv_bytes, _publish_results, main as evaluate_main


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"
client = TestClient(app)


def test_csv_serialization_is_platform_independent_lf_bytes():
    payload = _csv_bytes(
        [
            {"payment_id": "PAY_001", "reason": "plain"},
            {"payment_id": "PAY_002", "reason": "comma, quoted"},
        ]
    )

    assert payload == (
        b"payment_id,reason\n"
        b"PAY_001,plain\n"
        b'PAY_002,"comma, quoted"\n'
    )
    assert b"\r\n" not in payload


def _active_payloads():
    metrics = json.loads((RESULTS_DIR / "metrics.json").read_text(encoding="utf-8"))
    details = json.loads((RESULTS_DIR / "details.json").read_text(encoding="utf-8"))
    with (RESULTS_DIR / "results.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows, metrics, details


def _write_valid_snapshot(
    base: Path, metrics, details, *, generation_id=None, mixed_detail_generation=None
):
    generation = generation_id or metrics["evaluation_generation_id"]
    metrics = copy.deepcopy(metrics)
    details = copy.deepcopy(details)
    metrics["evaluation_generation_id"] = generation
    for detail in details:
        detail["evaluation_generation_id"] = generation
    if mixed_detail_generation is not None:
        details[0]["evaluation_generation_id"] = mixed_detail_generation

    source_pointer = json.loads(
        (RESULTS_DIR / results.POINTER_FILENAME).read_text(encoding="utf-8")
    )
    source_dir = RESULTS_DIR / "generations" / source_pointer["publication_id"]
    artifacts = {
        "results.csv": (source_dir / "results.csv").read_bytes(),
        "confusion_breakdown.csv": (source_dir / "confusion_breakdown.csv").read_bytes(),
        "metrics.json": (json.dumps(metrics, indent=2) + "\n").encode(),
        "details.json": (json.dumps(details, indent=2) + "\n").encode(),
    }
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in artifacts.items()}
    publication = results.publication_id(generation, hashes)
    manifest = {
        "manifest_format_version": results.MANIFEST_FORMAT_VERSION,
        "publication_id": publication,
        "evaluation_generation_id": generation,
        "evaluation_mode": metrics["evaluation_mode"],
        "artifacts": hashes,
    }
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
    generation_dir = base / "generations" / publication
    generation_dir.mkdir(parents=True)
    for name, content in artifacts.items():
        (generation_dir / name).write_bytes(content)
    (generation_dir / results.MANIFEST_FILENAME).write_bytes(manifest_bytes)
    pointer = {
        "pointer_format_version": results.MANIFEST_FORMAT_VERSION,
        "publication_id": publication,
        "evaluation_generation_id": generation,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    (base / results.POINTER_FILENAME).write_text(json.dumps(pointer), encoding="utf-8")
    return generation_dir


def test_mixed_generation_and_hash_tampering_fail_all_artifact_endpoints(
    monkeypatch, tmp_path
):
    _, metrics, details = _active_payloads()
    _write_valid_snapshot(
        tmp_path,
        metrics,
        details,
        mixed_detail_generation="old-generation",
    )
    monkeypatch.setattr(results, "RESULTS_DIR", tmp_path)

    for path in (
        "/ready",
        "/health",
        "/api/dashboard",
        "/api/benchmark",
        "/api/benchmark/cases",
        "/api/exceptions",
    ):
        response = client.get(path)
        assert response.status_code == 503
        assert "generation ID disagrees" in response.json()["detail"]


def test_hash_tampering_fails_readiness(monkeypatch, tmp_path):
    _, metrics, details = _active_payloads()
    generation_dir = _write_valid_snapshot(tmp_path, metrics, details)
    with (generation_dir / "details.json").open("ab") as handle:
        handle.write(b" ")
    monkeypatch.setattr(results, "RESULTS_DIR", tmp_path)

    response = client.get("/ready")
    assert response.status_code == 503
    assert "content hash" in response.json()["detail"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda metrics, details: details[50].pop("baseline"),
        lambda metrics, details: details[50]["decision"].update(decision="invented"),
        lambda metrics, details: metrics.pop("comparison"),
        lambda metrics, details: metrics["cache"].update(status=7),
    ],
)
def test_contract_invalid_artifacts_return_controlled_503(
    monkeypatch, tmp_path, mutation
):
    _, metrics, details = _active_payloads()
    mutation(metrics, details)
    _write_valid_snapshot(tmp_path, metrics, details)
    monkeypatch.setattr(results, "RESULTS_DIR", tmp_path)

    assert client.get("/ready").status_code == 503
    assert client.get("/health").status_code == 503
    assert client.get("/api/dashboard").status_code == 503
    assert client.get("/api/benchmark").status_code == 503
    assert client.get("/api/benchmark/cases").status_code == 503
    assert client.get("/api/exceptions/PAY_051").status_code == 503


def test_operational_apis_do_not_expose_evaluation_truth_labels():
    truth = {row["payment_id"]: row for row in load_ground_truth(REPO_ROOT / "data")}

    detail = client.get("/api/exceptions/PAY_051").json()
    summary = next(
        row for row in client.get("/api/exceptions").json()
        if row["payment_id"] == "PAY_051"
    )
    dashboard = client.get("/api/dashboard").json()
    operational_classes = {
        row["payment"]["payment_id"]: row["operational_exception_class"]
        for row in results.load_details()
    }

    assert truth["PAY_051"]["exception_class"] == "detached_remittance_email"
    assert detail["exception_class"] == "resolved_after_investigation"
    assert summary["exception_class"] == "resolved_after_investigation"
    assert all(
        row["exception_class"] == operational_classes[row["payment_id"]]
        for row in dashboard["recent_exceptions"]
    )
    assert detail["is_exception"] is True
    assert "expected_should_resolve" not in detail


class _FailingInvestigator:
    model = "offline-test-model"
    system_prompt = "offline test prompt"

    def cache_identity(self):
        return {"model": self.model, "identity": "offline-test"}

    def public_provenance(self):
        return {"model": self.model, "identity": "offline-test"}

    def investigate(self, bundle):
        raise InvestigatorError("simulated offline inference failure")


def test_failed_live_inference_is_counted_and_timing_is_not_verifier_only(tmp_path):
    full = load_dataset(REPO_ROOT / "data")
    payment = next(item for item in full.payments if item.payment_id == "PAY_051")
    dataset = Dataset(
        payments=[payment],
        invoices=full.invoices,
        customers=full.customers,
        credits=full.credits,
        emails=full.emails,
    )
    truth = [
        row for row in load_ground_truth(REPO_ROOT / "data")
        if row["payment_id"] == payment.payment_id
    ]
    investigator = CachedInvestigator(
        _FailingInvestigator(), tmp_path / "proposal_cache.json"
    )

    _, metrics, details = evaluate_dataset(dataset, truth, investigator)

    assert details[0]["decision"]["decision"] == "human_review"
    assert metrics["provenance"]["live_model_calls"] == 1
    assert metrics["provenance"]["successful_live_model_calls"] == 0
    assert metrics["provenance"]["failed_live_model_calls"] == 1
    assert metrics["cache"]["model_inference_attempted"] is True
    assert metrics["cache"]["model_inference_included"] is True
    assert "including attempted model inference" in metrics["timing_scope"]
    assert metrics["benchmark_claim_eligible"] is False
    assert metrics["safety_gate"]["passed"] is False


def test_unverified_replay_is_only_an_offline_verifier_regression():
    metrics = client.get("/api/benchmark").json()

    assert metrics["result_status"] == "offline_verifier_regression_only"
    assert metrics["benchmark_claim_eligible"] is False
    assert metrics["safety_gate"] == {
        "eligible": False,
        "passed": False,
        "reason": "identity-unverified cached proposals are verifier regression inputs only",
    }
    assert metrics["verifier_regression_gate"]["eligible"] is True
    assert metrics["verifier_regression_gate"]["passed"] is True


def test_cache_only_cli_fails_when_required_proposals_are_absent(
    monkeypatch, tmp_path
):
    output_dir = tmp_path / "empty-output"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate.py",
            "--cache-only",
            "--allow-unverified-legacy-cache",
            "--output",
            str(output_dir),
        ],
    )

    exit_code = evaluate_main()
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))

    assert exit_code != 0
    assert metrics["cache_hits"] == 0
    assert metrics["cache_misses"] == 30
    assert metrics["provenance"]["investigator_failures"] == 30
    assert metrics["verifier_regression_gate"] == {
        "eligible": False,
        "passed": False,
        "reason": "required proposal coverage was incomplete",
    }


def test_cache_only_cli_accepts_complete_identity_unverified_legacy_replay(
    monkeypatch, tmp_path
):
    output_dir = tmp_path / "complete-legacy-output"
    output_dir.mkdir()
    shutil.copy2(RESULTS_DIR / "proposal_cache.json", output_dir)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate.py",
            "--cache-only",
            "--allow-unverified-legacy-cache",
            "--output",
            str(output_dir),
        ],
    )

    exit_code = evaluate_main()
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert metrics["cache_hits"] == 30
    assert metrics["cache_misses"] == 0
    assert metrics["provenance"]["investigator_failures"] == 0
    assert metrics["benchmark_claim_eligible"] is False
    assert metrics["safety_gate"]["passed"] is False
    assert metrics["verifier_regression_gate"]["eligible"] is True
    assert metrics["verifier_regression_gate"]["passed"] is True


def test_interrupted_pointer_publication_keeps_previous_generation(
    monkeypatch, tmp_path
):
    rows, metrics, details = _active_payloads()
    _publish_results(tmp_path, rows, metrics, details)
    monkeypatch.setattr(results, "RESULTS_DIR", tmp_path)
    previous_elapsed = results.load_metrics()["elapsed_seconds"]
    previous_pointer = (tmp_path / results.POINTER_FILENAME).read_bytes()

    updated = copy.deepcopy(metrics)
    updated["elapsed_seconds"] = float(previous_elapsed) + 1
    original_write_json = __import__(
        "scripts.evaluate", fromlist=["atomic_write_json"]
    ).atomic_write_json

    def interrupt_pointer(path, payload):
        if Path(path).name == results.POINTER_FILENAME:
            raise OSError("simulated pointer interruption")
        return original_write_json(path, payload)

    monkeypatch.setattr("scripts.evaluate.atomic_write_json", interrupt_pointer)
    with pytest.raises(OSError, match="pointer interruption"):
        _publish_results(tmp_path, rows, updated, details)

    assert (tmp_path / results.POINTER_FILENAME).read_bytes() == previous_pointer
    assert results.load_metrics()["elapsed_seconds"] == previous_elapsed
