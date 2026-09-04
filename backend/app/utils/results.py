import csv
import hashlib
import hmac
import io
import json
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from pydantic import ValidationError

from app.models import CandidateBundle, InvestigationProposal, Payment


REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "results"
POINTER_FILENAME = "current_generation.json"
MANIFEST_FILENAME = "generation_manifest.json"
MANIFEST_FORMAT_VERSION = 1
REQUIRED_ARTIFACTS = {
    "results.csv",
    "confusion_breakdown.csv",
    "metrics.json",
    "details.json",
}
DECISIONS = {"matched_normally", "resolved", "human_review"}
EVALUATION_MODES = {
    "cache_only_legacy_identity_unverified_proposal_replay",
    "cache_only_proposal_verifier_replay",
    "live_or_mixed_proposal_evaluation",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ResultsUnavailableError(RuntimeError):
    """Raised when generated result artifacts cannot be served safely."""


def _artifact_error(filename: str, reason: str) -> ResultsUnavailableError:
    return ResultsUnavailableError(
        f"Generated artifact {filename} is unavailable: {reason}. "
        "Run backend/scripts/evaluate.py to publish a complete result set."
    )


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise _artifact_error(label, "file is missing") from exc
    except OSError as exc:
        raise _artifact_error(label, "file is unreadable") from exc


def _decode_json(content: bytes, label: str) -> object:
    try:
        return json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise _artifact_error(label, "file is unreadable or malformed") from exc


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256(encoded)


def publication_id(generation_id: str, artifacts: Dict[str, str]) -> str:
    encoded = json.dumps(
        {"evaluation_generation_id": generation_id, "artifacts": artifacts},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(encoded)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_nullable_string(value: object) -> bool:
    return value is None or _is_string(value)


def _is_amount(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        amount = Decimal(value)
    except InvalidOperation:
        return False
    return amount.is_finite() and amount >= 0 and amount.as_tuple().exponent >= -2


def _is_positive_amount(value: object) -> bool:
    return _is_amount(value) and Decimal(str(value)) > 0


def _is_iso_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _is_currency(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Z]{3}", value))


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _require_mapping(value: object, filename: str, location: str) -> Dict[str, object]:
    if not isinstance(value, dict):
        raise _artifact_error(filename, f"{location} must be an object")
    return value


def _require_list(value: object, filename: str, location: str) -> List[object]:
    if not isinstance(value, list):
        raise _artifact_error(filename, f"{location} must be an array")
    return value


def _require_fields(
    value: Dict[str, object],
    filename: str,
    location: str,
    fields: Dict[str, Callable[[object], bool]],
) -> None:
    for field, validator in fields.items():
        if field not in value:
            raise _artifact_error(filename, f"{location}.{field} is missing")
        if not validator(value[field]):
            raise _artifact_error(filename, f"{location}.{field} has an invalid type or value")


def _validate_nonnegative_int(value: object) -> bool:
    return _is_int(value) and int(value) >= 0


def _validate_rate(value: object) -> bool:
    return _is_number(value) and 0 <= float(value) <= 1


def _validate_comparison(value: object, location: str) -> None:
    comparison = _require_mapping(value, "metrics.json", location)
    for name in ("baseline", "llm_only", "remitproof"):
        item = _require_mapping(
            comparison.get(name), "metrics.json", f"{location}.{name}"
        )
        _require_fields(
            item,
            "metrics.json",
            f"{location}.{name}",
            {
                "resolved": _validate_nonnegative_int,
                "correct_resolutions": _validate_nonnegative_int,
                "wrong_auto_resolutions": _validate_nonnegative_int,
                "correct_abstentions": _validate_nonnegative_int,
                "false_escalations": _validate_nonnegative_int,
            },
        )
    llm_only = comparison["llm_only"]
    _require_fields(
        llm_only,
        "metrics.json",
        f"{location}.llm_only",
        {
            "mode": _is_string,
            "label": _is_string,
            "standalone_llm_system": lambda item: isinstance(item, bool),
            "allows_independent_abstention": lambda item: isinstance(item, bool),
        },
    )


def _validate_metric_set(metrics: Dict[str, object], location: str) -> None:
    _require_fields(
        metrics,
        "metrics.json",
        location,
        {
            "total_receipts": _validate_nonnegative_int,
            "matched_normally": _validate_nonnegative_int,
            "exceptions": _validate_nonnegative_int,
            "resolved_by_remitproof": _validate_nonnegative_int,
            "human_review": _validate_nonnegative_int,
            "baseline_match_rate": _validate_rate,
            "exception_resolution_rate": _validate_rate,
            "resolution_accuracy": _validate_rate,
            "incorrect_auto_resolution_rate": _validate_rate,
            "correct_abstention_rate": _validate_rate,
            "false_escalation_rate": _validate_rate,
            "entity_resolution_accuracy": _validate_rate,
            "evidence_precision": _validate_rate,
            "arithmetic_correctness": _validate_rate,
            "retrieval_accuracy": _validate_rate,
            "alternative_detection_accuracy": _validate_rate,
            "ambiguity_detection_accuracy": _validate_rate,
            "contradiction_detection_accuracy": _validate_rate,
            "decision_critical_evidence_accuracy": _validate_rate,
            "throughput_per_minute": lambda item: _is_number(item) and float(item) >= 0,
            "mean_latency_ms": lambda item: _is_number(item) and float(item) >= 0,
            "comparison_scope": _is_string,
            "comparison_record_count": _validate_nonnegative_int,
            "timing_scope": _is_string,
            "comparison": lambda item: isinstance(item, dict),
        },
    )
    _validate_comparison(metrics["comparison"], f"{location}.comparison")
    if metrics["total_receipts"] != (
        metrics["matched_normally"]
        + metrics["resolved_by_remitproof"]
        + metrics["human_review"]
    ):
        raise _artifact_error("metrics.json", f"{location} decision counts disagree")
    if metrics["exceptions"] != (
        metrics["resolved_by_remitproof"] + metrics["human_review"]
    ):
        raise _artifact_error("metrics.json", f"{location} exception counts disagree")
    if metrics["comparison_record_count"] > metrics["exceptions"]:
        raise _artifact_error("metrics.json", f"{location} comparison count exceeds exception count")
    for name, item in metrics["comparison"].items():
        if item["resolved"] != (
            item["correct_resolutions"] + item["wrong_auto_resolutions"]
        ):
            raise _artifact_error(
                "metrics.json", f"{location}.comparison.{name} resolution counts disagree"
            )
        if metrics["comparison_record_count"] != (
            item["resolved"] + item["correct_abstentions"] + item["false_escalations"]
        ):
            raise _artifact_error(
                "metrics.json", f"{location}.comparison.{name} outcome counts disagree"
            )


def _validate_metrics(raw: object) -> Dict[str, object]:
    metrics = dict(_require_mapping(raw, "metrics.json", "root"))
    _require_fields(
        metrics,
        "metrics.json",
        "root",
        {
            "generated_from": _is_string,
            "evaluation_generation_id": _is_string,
            "evaluation_mode": lambda item: item in EVALUATION_MODES,
            "result_status": lambda item: item in {
                "model_backed_benchmark", "offline_verifier_regression_only"
            },
            "benchmark_claim_eligible": lambda item: isinstance(item, bool),
            "partition_label": _is_string,
            "independent_held_out": lambda item: isinstance(item, bool),
            "model": _is_string,
            "elapsed_seconds": lambda item: _is_number(item) and float(item) >= 0,
            "cache_hits": _validate_nonnegative_int,
            "cache_misses": _validate_nonnegative_int,
            "cache": lambda item: isinstance(item, dict),
            "safety_gate": lambda item: isinstance(item, dict),
            "verifier_regression_gate": lambda item: isinstance(item, dict),
            "provenance": lambda item: isinstance(item, dict),
            "synthetic_benchmark_regression": lambda item: isinstance(item, dict),
            "held_out": lambda item: isinstance(item, dict),
        },
    )
    _validate_metric_set(metrics, "root")

    cache = _require_mapping(metrics["cache"], "metrics.json", "root.cache")
    _require_fields(
        cache,
        "metrics.json",
        "root.cache",
        {
            "status": lambda item: item in {"cache_only", "live_or_mixed"},
            "hits": _validate_nonnegative_int,
            "misses": _validate_nonnegative_int,
            "model_inference_included": lambda item: isinstance(item, bool),
            "model_inference_attempted": lambda item: isinstance(item, bool),
            "proposal_source_identity_verified": lambda item: isinstance(item, bool),
        },
    )
    if cache["model_inference_included"] != cache["model_inference_attempted"]:
        raise _artifact_error("metrics.json", "cache inference timing flags disagree")
    expected_cache_status = (
        "cache_only" if metrics["evaluation_mode"].startswith("cache_only") else "live_or_mixed"
    )
    if cache["status"] != expected_cache_status:
        raise _artifact_error("metrics.json", "cache status disagrees with evaluation mode")

    safety_gate = _require_mapping(
        metrics["safety_gate"], "metrics.json", "root.safety_gate"
    )
    _require_fields(
        safety_gate,
        "metrics.json",
        "root.safety_gate",
        {
            "eligible": lambda item: isinstance(item, bool),
            "passed": lambda item: isinstance(item, bool),
            "reason": _is_string,
        },
    )
    if bool(metrics["benchmark_claim_eligible"]) != bool(safety_gate["eligible"]):
        raise _artifact_error("metrics.json", "benchmark eligibility flags disagree")
    if safety_gate["passed"] and not safety_gate["eligible"]:
        raise _artifact_error("metrics.json", "an ineligible benchmark cannot pass the safety gate")
    if metrics["result_status"] == "model_backed_benchmark" and not safety_gate["eligible"]:
        raise _artifact_error("metrics.json", "model-backed status requires an eligible safety gate")
    if metrics["result_status"] == "offline_verifier_regression_only" and safety_gate["eligible"]:
        raise _artifact_error("metrics.json", "offline verifier status cannot claim benchmark eligibility")

    verifier_gate = _require_mapping(
        metrics["verifier_regression_gate"], "metrics.json", "root.verifier_regression_gate"
    )
    _require_fields(
        verifier_gate,
        "metrics.json",
        "root.verifier_regression_gate",
        {
            "eligible": lambda item: item is True,
            "passed": lambda item: isinstance(item, bool),
            "reason": _is_string,
        },
    )

    provenance = _require_mapping(
        metrics["provenance"], "metrics.json", "root.provenance"
    )
    _require_fields(
        provenance,
        "metrics.json",
        "root.provenance",
        {
            "evaluator_version": _is_string,
            "evaluation_mode": _is_string,
            "dataset_sha256": lambda item: isinstance(item, str) and bool(SHA256_PATTERN.fullmatch(item)),
            "proposal_cache_sha256": lambda item: isinstance(item, str) and bool(SHA256_PATTERN.fullmatch(item)),
            "investigator": lambda item: isinstance(item, dict),
            "proposal_source_identity_verified": lambda item: isinstance(item, bool),
            "cache_hits": _validate_nonnegative_int,
            "cache_misses": _validate_nonnegative_int,
            "live_model_calls": _validate_nonnegative_int,
            "successful_live_model_calls": _validate_nonnegative_int,
            "failed_live_model_calls": _validate_nonnegative_int,
            "investigator_failures": _validate_nonnegative_int,
            "legacy_cache_promotions": _validate_nonnegative_int,
            "unverified_legacy_cache_hits": _validate_nonnegative_int,
            "cache_entries": _validate_nonnegative_int,
            "unverified_legacy_entries": _validate_nonnegative_int,
        },
    )
    if provenance["evaluation_mode"] != metrics["evaluation_mode"]:
        raise _artifact_error("metrics.json", "provenance evaluation mode disagrees")
    if provenance["live_model_calls"] != (
        provenance["successful_live_model_calls"] + provenance["failed_live_model_calls"]
    ):
        raise _artifact_error("metrics.json", "live model call counts disagree")
    if bool(cache["model_inference_attempted"]) != bool(provenance["live_model_calls"]):
        raise _artifact_error("metrics.json", "model inference attempt metadata disagrees")
    if cache["hits"] != metrics["cache_hits"] or cache["hits"] != provenance["cache_hits"]:
        raise _artifact_error("metrics.json", "cache hit counts disagree")
    if cache["misses"] != metrics["cache_misses"] or cache["misses"] != provenance["cache_misses"]:
        raise _artifact_error("metrics.json", "cache miss counts disagree")
    if cache["proposal_source_identity_verified"] != provenance["proposal_source_identity_verified"]:
        raise _artifact_error("metrics.json", "proposal source identity flags disagree")
    expected_verified = provenance["unverified_legacy_cache_hits"] == 0
    if provenance["proposal_source_identity_verified"] != expected_verified:
        raise _artifact_error("metrics.json", "proposal source identity is inconsistent")
    expected_eligible = bool(
        expected_verified
        and provenance["failed_live_model_calls"] == 0
        and provenance["investigator_failures"] == 0
    )
    if metrics["benchmark_claim_eligible"] != expected_eligible:
        raise _artifact_error("metrics.json", "benchmark eligibility is inconsistent")
    expected_gate_pass = bool(
        expected_eligible
        and metrics["incorrect_auto_resolution_rate"] == 0
        and metrics["arithmetic_correctness"] == 1
        and metrics["retrieval_accuracy"] == 1
    )
    if safety_gate["passed"] != expected_gate_pass:
        raise _artifact_error("metrics.json", "benchmark safety gate result is inconsistent")
    expected_regression_pass = bool(
        metrics["incorrect_auto_resolution_rate"] == 0
        and metrics["arithmetic_correctness"] == 1
        and metrics["retrieval_accuracy"] == 1
    )
    if verifier_gate["passed"] != expected_regression_pass:
        raise _artifact_error("metrics.json", "verifier regression gate result is inconsistent")

    investigator = _require_mapping(
        provenance["investigator"], "metrics.json", "root.provenance.investigator"
    )
    _require_fields(
        investigator,
        "metrics.json",
        "root.provenance.investigator",
        {
            "investigator_version": _is_string,
            "model": _is_string,
            "model_digest": _is_nullable_string,
            "timeout_seconds": lambda item: _is_number(item) and float(item) > 0,
            "generation_options": lambda item: isinstance(item, dict),
            "prompt_sha256": lambda item: isinstance(item, str) and bool(SHA256_PATTERN.fullmatch(item)),
            "proposal_schema_sha256": lambda item: isinstance(item, str) and bool(SHA256_PATTERN.fullmatch(item)),
            "host_sha256": lambda item: isinstance(item, str) and bool(SHA256_PATTERN.fullmatch(item)),
            "identity_sha256": lambda item: isinstance(item, str) and bool(SHA256_PATTERN.fullmatch(item)),
        },
    )
    options = _require_mapping(
        investigator["generation_options"],
        "metrics.json",
        "root.provenance.investigator.generation_options",
    )
    _require_fields(
        options,
        "metrics.json",
        "root.provenance.investigator.generation_options",
        {
            "temperature": _is_number,
            "seed": _is_int,
        },
    )
    if investigator["model"] != metrics["model"]:
        raise _artifact_error("metrics.json", "investigator model disagrees")
    if _sha256_json(provenance) != metrics["evaluation_generation_id"]:
        raise _artifact_error("metrics.json", "evaluation generation ID is not derived from provenance")

    for field in ("synthetic_benchmark_regression", "held_out"):
        nested = _require_mapping(metrics[field], "metrics.json", f"root.{field}")
        _require_fields(
            nested,
            "metrics.json",
            f"root.{field}",
            {
                "partition_label": _is_string,
                "independent_held_out": lambda item: isinstance(item, bool),
            },
        )
        _validate_metric_set(nested, f"root.{field}")
    if metrics["held_out"].get("legacy_key") is not True:
        raise _artifact_error("metrics.json", "held_out.legacy_key must be true")
    held_out_without_marker = dict(metrics["held_out"])
    del held_out_without_marker["legacy_key"]
    if held_out_without_marker != metrics["synthetic_benchmark_regression"]:
        raise _artifact_error("metrics.json", "held_out compatibility metrics disagree")
    return metrics


def _validate_payment(value: object, location: str) -> Dict[str, object]:
    payment = _require_mapping(value, "details.json", location)
    _require_fields(
        payment,
        "details.json",
        location,
        {
            "payment_id": _is_string,
            "date": _is_iso_date,
            "payer_name": _is_string,
            "amount": _is_positive_amount,
            "currency": _is_currency,
            "status": lambda item: item in {"unmatched", "matched", "reconciled"},
            "bank_reference": lambda item: isinstance(item, str),
            "remittance_reference": lambda item: isinstance(item, str),
            "allocated_customer_id": _is_nullable_string,
        },
    )
    try:
        Payment.model_validate(payment)
    except ValidationError as exc:
        raise _artifact_error("details.json", f"{location} is invalid") from exc
    return payment


def _validate_baseline(value: object, location: str) -> None:
    baseline = _require_mapping(value, "details.json", location)
    _require_fields(
        baseline,
        "details.json",
        location,
        {
            "payment_id": _is_string,
            "status": lambda item: item in {"matched", "unresolved"},
            "matched_invoices": _is_string_list,
            "matched_credits": _is_string_list,
            "customer_id": _is_nullable_string,
            "reason": _is_string,
            "candidate_count": _validate_nonnegative_int,
        },
    )
    if baseline["candidate_count"] < len(baseline["matched_invoices"]):
        raise _artifact_error("details.json", f"{location}.candidate_count is inconsistent")


def _validate_decision(value: object, location: str) -> Dict[str, object]:
    decision = _require_mapping(value, "details.json", location)
    _require_fields(
        decision,
        "details.json",
        location,
        {
            "payment_id": _is_string,
            "decision": lambda item: item in DECISIONS,
            "customer_id": _is_nullable_string,
            "invoice_ids": _is_string_list,
            "credit_ids": _is_string_list,
            "proof": lambda item: isinstance(item, dict),
            "evidence": _is_string_list,
            "reason": _is_string,
            "latency_ms": lambda item: _is_number(item) and float(item) >= 0,
        },
    )
    return decision


def _validate_proposal(value: object, location: str) -> None:
    if value is None:
        return
    proposal = _require_mapping(value, "details.json", location)
    _require_fields(
        proposal,
        "details.json",
        location,
        {
            "payment_id": _is_string,
            "proposed_customer": _is_nullable_string,
            "invoice_ids": _is_string_list,
            "credit_ids": _is_string_list,
            "semantic_claims": lambda item: isinstance(item, list),
            "evidence_ids": _is_string_list,
            "unresolved_questions": _is_string_list,
        },
    )
    try:
        InvestigationProposal.model_validate(proposal)
    except ValidationError as exc:
        raise _artifact_error("details.json", f"{location} is invalid") from exc


def _validate_evidence(value: object, location: str) -> None:
    rows = _require_list(value, "details.json", location)
    for index, raw in enumerate(rows):
        row_location = f"{location}[{index}]"
        row = _require_mapping(raw, "details.json", row_location)
        _require_fields(
            row,
            "details.json",
            row_location,
            {
                "evidence_id": _is_string,
                "evidence_type": lambda item: item in {
                    "customer_record", "invoice_record", "remittance_email", "credit_note"
                },
                "title": _is_string,
                "content": lambda item: isinstance(item, (str, dict)),
            },
        )
        if "evidence_role" in row and row["evidence_role"] not in {
            "model_citation", "audit_context"
        }:
            raise _artifact_error("details.json", f"{row_location}.evidence_role is invalid")
        allowed = {
            "evidence_id", "evidence_type", "title", "content",
            "sender", "date", "evidence_role",
        }
        if set(row) - allowed:
            raise _artifact_error("details.json", f"{row_location} has unsupported fields")
        if "sender" in row and not _is_string(row["sender"]):
            raise _artifact_error("details.json", f"{row_location}.sender is invalid")
        if "date" in row and not _is_iso_date(row["date"]):
            raise _artifact_error("details.json", f"{row_location}.date is invalid")


def _validate_proof(value: object, location: str) -> None:
    if value is None:
        return
    proof = _require_mapping(value, "details.json", location)
    _require_fields(
        proof,
        "details.json",
        location,
        {
            "financial_validity": lambda item: isinstance(item, bool),
            "state_validity": lambda item: isinstance(item, bool),
            "currency_validity": lambda item: isinstance(item, bool),
            "entity_support": lambda item: isinstance(item, bool),
            "credit_support": lambda item: isinstance(item, bool),
            "duplicate_risk": lambda item: isinstance(item, bool),
            "contradictions": _is_string_list,
            "missing_required_evidence": _is_string_list,
            "reason_codes": _is_string_list,
            "invoice_total": _is_amount,
            "credit_total": _is_amount,
            "calculated_total": _is_amount,
            "payment_total": _is_amount,
        },
    )


def _validate_sufficiency(value: object, location: str) -> None:
    if value is None:
        return
    item = _require_mapping(value, "details.json", location)
    bool_fields = {
        field: (lambda candidate: isinstance(candidate, bool))
        for field in (
            "financial_validity", "entity_support", "credit_support",
            "alternative_allocations_exist", "evidence_disambiguates_alternatives",
            "contradictions_exist", "duplicate_risk", "safe_to_resolve",
            "chosen_proposal_supported", "alternatives_eliminated",
        )
    }
    _require_fields(
        item,
        "details.json",
        location,
        {
            **bool_fields,
            "missing_required_evidence": _is_string_list,
            "uniquely_distinguishing_evidence": _is_string_list,
            "evidence_alternative_matrix": lambda candidate: isinstance(candidate, list)
            and all(isinstance(row, dict) for row in candidate),
            "abstention_reason": _is_nullable_string,
        },
    )


def _validate_detail(raw: object, index: int) -> Dict[str, object]:
    location = f"root[{index}]"
    detail = _require_mapping(raw, "details.json", location)
    _require_fields(
        detail,
        "details.json",
        location,
        {
            "evaluation_generation_id": _is_string,
            "operational_exception_class": _is_string,
            "operational_is_exception": lambda item: isinstance(item, bool),
            "exception_class": _is_string,
            "is_exception": lambda item: isinstance(item, bool),
            "split": lambda item: item in {"dev", "benchmark"},
            "expected_should_resolve": lambda item: isinstance(item, bool),
            "payment": lambda item: isinstance(item, dict),
            "baseline": lambda item: isinstance(item, dict),
            "decision": lambda item: isinstance(item, dict),
            "proposal": lambda item: item is None or isinstance(item, dict),
            "candidates": lambda item: isinstance(item, dict),
            "proposed_allocation": lambda item: isinstance(item, list),
            "evidence": lambda item: isinstance(item, list),
            "proof": lambda item: item is None or isinstance(item, dict),
            "alternatives": lambda item: isinstance(item, list),
            "conflict": lambda item: item is None or isinstance(item, dict),
            "sufficiency": lambda item: item is None or isinstance(item, dict),
            "counterfactuals": lambda item: isinstance(item, list),
            "resolution_proof": lambda item: item is None or isinstance(item, dict),
            "blocked_decision": lambda item: item is None or isinstance(item, dict),
            "investigator_error": _is_nullable_string,
        },
    )
    payment = _validate_payment(detail["payment"], f"{location}.payment")
    _validate_baseline(detail["baseline"], f"{location}.baseline")
    decision = _validate_decision(detail["decision"], f"{location}.decision")
    if decision["payment_id"] != payment["payment_id"]:
        raise _artifact_error("details.json", f"{location} payment identifiers disagree")
    if detail["baseline"]["payment_id"] != payment["payment_id"]:
        raise _artifact_error("details.json", f"{location} baseline payment identifier disagrees")
    expected_operational_exception = detail["baseline"]["status"] != "matched"
    if detail["operational_is_exception"] != expected_operational_exception:
        raise _artifact_error("details.json", f"{location} operational exception flag disagrees")
    if not expected_operational_exception and detail["operational_exception_class"] != "matched_normally":
        raise _artifact_error("details.json", f"{location} operational class disagrees")
    _validate_proposal(detail["proposal"], f"{location}.proposal")
    candidates = detail["candidates"]
    for field in ("customers", "invoices", "credits", "emails"):
        if field not in candidates or not isinstance(candidates[field], list):
            raise _artifact_error("details.json", f"{location}.candidates.{field} must be an array")
    for allocation_index, raw_allocation in enumerate(detail["proposed_allocation"]):
        allocation_location = f"{location}.proposed_allocation[{allocation_index}]"
        allocation = _require_mapping(raw_allocation, "details.json", allocation_location)
        _require_fields(
            allocation,
            "details.json",
            allocation_location,
            {
                "record_type": lambda item: item in {"invoice", "credit"},
                "record_id": _is_string,
                "description": lambda item: isinstance(item, str),
                "amount": _is_positive_amount,
                "currency": _is_currency,
                "operator": lambda item: item in {"+", "-"},
            },
        )
        if set(allocation) != {
            "record_type", "record_id", "description", "amount", "currency", "operator"
        }:
            raise _artifact_error("details.json", f"{allocation_location} has unsupported fields")
        expected_operator = "+" if allocation["record_type"] == "invoice" else "-"
        if allocation["operator"] != expected_operator:
            raise _artifact_error("details.json", f"{allocation_location}.operator is inconsistent")
    _validate_evidence(detail["evidence"], f"{location}.evidence")
    _validate_proof(detail["proof"], f"{location}.proof")
    for alternative_index, raw_alternative in enumerate(detail["alternatives"]):
        alternative_location = f"{location}.alternatives[{alternative_index}]"
        alternative = _require_mapping(raw_alternative, "details.json", alternative_location)
        _require_fields(
            alternative,
            "details.json",
            alternative_location,
            {
                "customer_id": _is_string,
                "allocation_id": _is_string,
                "invoice_ids": _is_string_list,
                "credit_ids": _is_string_list,
                "calculated_total": _is_positive_amount,
                "financially_valid": lambda item: isinstance(item, bool),
            },
        )
    _validate_sufficiency(detail["sufficiency"], f"{location}.sufficiency")
    if not all(isinstance(item, dict) for item in detail["counterfactuals"]):
        raise _artifact_error("details.json", f"{location}.counterfactuals must contain objects")
    try:
        CandidateBundle.model_validate(
            {
                "payment": detail["payment"],
                "candidate_customers": candidates["customers"],
                "candidate_invoices": candidates["invoices"],
                "candidate_credits": candidates["credits"],
                "candidate_emails": candidates["emails"],
            }
        )
    except ValidationError as exc:
        raise _artifact_error("details.json", f"{location}.candidates are invalid") from exc
    return detail


def _validate_details(raw: object) -> List[Dict[str, object]]:
    rows = _require_list(raw, "details.json", "root")
    return [_validate_detail(row, index) for index, row in enumerate(rows)]


def _validate_manifest(
    raw: object,
    base_dir: Path,
    *,
    label: str,
    expected_publication_id: Optional[str] = None,
    expected_generation_id: Optional[str] = None,
) -> Tuple[Dict[str, bytes], Dict[str, object]]:
    manifest = _require_mapping(raw, label, "root")
    generation_id = manifest.get("evaluation_generation_id")
    evaluation_mode = manifest.get("evaluation_mode")
    artifacts = manifest.get("artifacts")
    if not _is_string(generation_id) or not _is_string(evaluation_mode):
        raise _artifact_error(label, "generation metadata is invalid")
    artifact_hashes = _require_mapping(artifacts, label, "root.artifacts")
    if set(artifact_hashes) != REQUIRED_ARTIFACTS:
        raise _artifact_error(label, "artifact hash set is incomplete or unsupported")
    for name, digest in artifact_hashes.items():
        if not isinstance(name, str) or Path(name).name != name:
            raise _artifact_error(label, "artifact names must be plain filenames")
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            raise _artifact_error(label, f"artifact hash for {name} is invalid")
    if manifest.get("manifest_format_version") != MANIFEST_FORMAT_VERSION:
        raise _artifact_error(label, "manifest format version is unsupported")
    manifest_publication = manifest.get("publication_id")
    if not isinstance(manifest_publication, str) or not SHA256_PATTERN.fullmatch(
        manifest_publication
    ):
        raise _artifact_error(label, "publication ID is invalid")
    calculated = publication_id(str(generation_id), artifact_hashes)
    if not hmac.compare_digest(calculated, manifest_publication):
        raise _artifact_error(label, "publication ID does not match artifact hashes")
    if expected_generation_id is not None and generation_id != expected_generation_id:
        raise _artifact_error(label, "evaluation generation ID disagrees with pointer")
    if expected_publication_id is not None:
        if manifest_publication != expected_publication_id:
            raise _artifact_error(label, "publication ID disagrees with pointer")

    contents: Dict[str, bytes] = {}
    for name, expected_hash in artifact_hashes.items():
        content = _read_bytes(base_dir / name, name)
        if not hmac.compare_digest(_sha256(content), str(expected_hash)):
            raise _artifact_error(name, "content hash does not match the published manifest")
        contents[name] = content
    return contents, manifest


def _load_snapshot() -> Tuple[object, object, Dict[str, object], Dict[str, bytes]]:
    pointer_path = RESULTS_DIR / POINTER_FILENAME
    if pointer_path.exists():
        pointer_bytes = _read_bytes(pointer_path, POINTER_FILENAME)
        pointer = _require_mapping(
            _decode_json(pointer_bytes, POINTER_FILENAME), POINTER_FILENAME, "root"
        )
        _require_fields(
            pointer,
            POINTER_FILENAME,
            "root",
            {
                "pointer_format_version": lambda item: item == MANIFEST_FORMAT_VERSION,
                "publication_id": lambda item: isinstance(item, str) and bool(SHA256_PATTERN.fullmatch(item)),
                "evaluation_generation_id": _is_string,
                "manifest_sha256": lambda item: isinstance(item, str) and bool(SHA256_PATTERN.fullmatch(item)),
            },
        )
        publication_id = str(pointer["publication_id"])
        generation_dir = RESULTS_DIR / "generations" / publication_id
        manifest_path = generation_dir / MANIFEST_FILENAME
        manifest_bytes = _read_bytes(manifest_path, MANIFEST_FILENAME)
        if not hmac.compare_digest(_sha256(manifest_bytes), str(pointer["manifest_sha256"])):
            raise _artifact_error(MANIFEST_FILENAME, "manifest hash disagrees with pointer")
        contents, manifest = _validate_manifest(
            _decode_json(manifest_bytes, MANIFEST_FILENAME),
            generation_dir,
            label=MANIFEST_FILENAME,
            expected_publication_id=publication_id,
            expected_generation_id=str(pointer["evaluation_generation_id"]),
        )
    else:
        # Root files are compatibility exports, never an API-readable snapshot.
        # Parse malformed primary JSON first so migration failures remain diagnosable,
        # then require the atomic generation pointer even when the exports are valid.
        metric_bytes = _read_bytes(RESULTS_DIR / "metrics.json", "metrics.json")
        detail_bytes = _read_bytes(RESULTS_DIR / "details.json", "details.json")
        _decode_json(metric_bytes, "metrics.json")
        _decode_json(detail_bytes, "details.json")
        raise _artifact_error(POINTER_FILENAME, "atomic generation pointer is missing")

    metrics_raw = _decode_json(contents["metrics.json"], "metrics.json")
    details_raw = _decode_json(contents["details.json"], "details.json")
    return metrics_raw, details_raw, manifest, contents


def _validate_snapshot(
    metrics_raw: object,
    details_raw: object,
    manifest: Dict[str, object],
) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    """Validate the metrics/details pair selected by one immutable snapshot."""

    metrics = _validate_metrics(metrics_raw)
    details = _validate_details(details_raw)
    generation_id = str(metrics["evaluation_generation_id"])
    if generation_id != manifest["evaluation_generation_id"]:
        raise _artifact_error("metrics.json", "generation ID disagrees with manifest")
    if metrics["evaluation_mode"] != manifest["evaluation_mode"]:
        raise _artifact_error("metrics.json", "evaluation mode disagrees with manifest")

    payment_ids = set()
    decision_counts = {decision: 0 for decision in DECISIONS}
    operational_exception_count = 0
    for index, detail in enumerate(details):
        if detail["evaluation_generation_id"] != generation_id:
            raise _artifact_error(
                "details.json", f"root[{index}] generation ID disagrees"
            )
        payment_id = str(detail["payment"]["payment_id"])
        if payment_id in payment_ids:
            raise _artifact_error("details.json", f"duplicate payment ID {payment_id}")
        payment_ids.add(payment_id)
        decision_counts[str(detail["decision"]["decision"])] += 1
        operational_exception_count += int(bool(detail["operational_is_exception"]))

    if int(metrics["total_receipts"]) != len(details):
        raise _artifact_error("metrics.json/details.json", "total receipt counts disagree")
    if int(metrics["exceptions"]) != operational_exception_count:
        raise _artifact_error("metrics.json/details.json", "exception counts disagree")
    expected_counts = {
        "matched_normally": decision_counts["matched_normally"],
        "resolved_by_remitproof": decision_counts["resolved"],
        "human_review": decision_counts["human_review"],
    }
    for metric, expected in expected_counts.items():
        if int(metrics[metric]) != expected:
            raise _artifact_error(
                "metrics.json/details.json", f"{metric} counts disagree"
            )
    return metrics, details


def load_results() -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    """Load and validate exactly one content-addressed result publication."""

    metrics_raw, details_raw, manifest, _ = _load_snapshot()
    return _validate_snapshot(metrics_raw, details_raw, manifest)


_CASE_CSV_COLUMNS = {
    "payment_id",
    "split",
    "is_exception",
    "exception_class",
    "payer",
    "amount",
    "currency",
    "baseline_decision",
    "llm_only_decision",
    "llm_only_correct_resolution",
    "comparator_mode",
    "decision",
    "final_correct_resolution",
    "expected_should_resolve",
    "correct_abstention",
    "false_escalation",
    "wrong_auto_resolution",
    "reason",
}
_CLASS_CSV_COLUMNS = {
    "exception_class",
    "records",
    "resolved",
    "correct_resolutions",
    "human_review",
    "wrong_auto_resolutions",
    "false_escalations",
}


def _csv_bool(row: Dict[str, str], column: str, filename: str) -> bool:
    value = row.get(column)
    if value not in {"True", "False"}:
        raise _artifact_error(filename, f"column {column} has a non-boolean value")
    return value == "True"


def _csv_rows(content: bytes, filename: str, required_columns: set) -> List[Dict[str, str]]:
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    except UnicodeError as exc:
        raise _artifact_error(filename, "file is unreadable or malformed") from exc
    if reader.fieldnames is None or not required_columns.issubset(set(reader.fieldnames)):
        raise _artifact_error(filename, "required columns are missing")
    return list(reader)


_CASE_BOOLEAN_COLUMNS = {
    "is_exception",
    "llm_only_correct_resolution",
    "final_correct_resolution",
    "expected_should_resolve",
    "correct_abstention",
    "false_escalation",
    "wrong_auto_resolution",
}
_CLASS_AGGREGATE_COLUMNS = (
    "records",
    "resolved",
    "correct_resolutions",
    "human_review",
    "wrong_auto_resolutions",
    "false_escalations",
)


def _csv_nonnegative_int(row: Dict[str, str], column: str, filename: str) -> int:
    value = row.get(column)
    try:
        parsed = int(value) if value is not None else -1
    except (TypeError, ValueError) as exc:
        raise _artifact_error(filename, f"column {column} has a non-integer value") from exc
    if parsed < 0:
        raise _artifact_error(filename, f"column {column} must be non-negative")
    return parsed


def load_case_comparisons() -> Dict[str, object]:
    """Serve per-case baseline/ablation/RemitProof outcomes from the published CSVs.

    The CSV bytes are already hash-verified against the generation manifest.
    Derived aggregates are additionally cross-checked against the validated
    metrics comparison so an inconsistent publication fails closed instead of
    serving numbers the committed metrics do not support.
    """

    metrics_raw, details_raw, manifest, contents = _load_snapshot()
    metrics, details = _validate_snapshot(metrics_raw, details_raw, manifest)
    generation_id = str(metrics["evaluation_generation_id"])

    rows = _csv_rows(contents["results.csv"], "results.csv", _CASE_CSV_COLUMNS)
    detail_payment_ids = {
        str(detail["payment"]["payment_id"])
        for detail in details
    }
    result_payment_ids = []
    for row in rows:
        payment_id = row.get("payment_id", "")
        if not isinstance(payment_id, str) or not payment_id.strip():
            raise _artifact_error("results.csv", "payment_id is missing or blank")
        result_payment_ids.append(payment_id)
        for column in _CASE_BOOLEAN_COLUMNS:
            _csv_bool(row, column, "results.csv")
    if len(result_payment_ids) != len(set(result_payment_ids)):
        raise _artifact_error("results.csv", "payment IDs must be unique")
    if set(result_payment_ids) != detail_payment_ids:
        raise _artifact_error(
            "results.csv",
            "payment IDs disagree with the validated details publication",
        )

    cases: List[Dict[str, object]] = []
    for row in rows:
        if row["baseline_decision"] not in {"resolve", "abstain"}:
            raise _artifact_error("results.csv", "baseline_decision has an unsupported value")
        if row["llm_only_decision"] not in {"resolve", "abstain"}:
            raise _artifact_error("results.csv", "llm_only_decision has an unsupported value")
        if row["decision"] not in DECISIONS:
            raise _artifact_error("results.csv", "decision has an unsupported value")
        is_exception = _csv_bool(row, "is_exception", "results.csv")
        if not is_exception or row["baseline_decision"] != "abstain":
            continue
        llm_only_resolved = row["llm_only_decision"] == "resolve"
        llm_only_correct = _csv_bool(row, "llm_only_correct_resolution", "results.csv")
        final_correct = _csv_bool(row, "final_correct_resolution", "results.csv")
        cases.append(
            {
                "payment_id": row["payment_id"],
                "split": row["split"],
                "exception_class": row["exception_class"],
                "payer": row["payer"],
                "amount": row["amount"],
                "currency": row["currency"],
                "expected_should_resolve": _csv_bool(row, "expected_should_resolve", "results.csv"),
                "baseline_decision": "human_review",
                "llm_only_decision": row["llm_only_decision"],
                "llm_only_wrong_resolution": llm_only_resolved and not llm_only_correct,
                "remitproof_decision": row["decision"],
                "remitproof_correct_resolution": row["decision"] == "resolved" and final_correct,
                "correct_abstention": _csv_bool(row, "correct_abstention", "results.csv"),
                "false_escalation": _csv_bool(row, "false_escalation", "results.csv"),
                "wrong_auto_resolution": _csv_bool(row, "wrong_auto_resolution", "results.csv"),
                "recovered_from_baseline": row["decision"] == "resolved" and final_correct,
                "reason": row["reason"],
            }
        )

    comparison = metrics["comparison"]
    summary = {
        "comparison_record_count": len(cases),
        "llm_only_wrong_resolutions": sum(1 for case in cases if case["llm_only_wrong_resolution"]),
        "remitproof_wrong_auto_resolutions": sum(1 for case in cases if case["wrong_auto_resolution"]),
        "recovered_from_baseline": sum(1 for case in cases if case["recovered_from_baseline"]),
        "correct_abstentions": sum(1 for case in cases if case["correct_abstention"]),
        "false_escalations": sum(1 for case in cases if case["false_escalation"]),
    }
    consistency = (
        summary["comparison_record_count"] == metrics["comparison_record_count"],
        summary["llm_only_wrong_resolutions"] == comparison["llm_only"]["wrong_auto_resolutions"],
        summary["remitproof_wrong_auto_resolutions"] == comparison["remitproof"]["wrong_auto_resolutions"],
        summary["recovered_from_baseline"] == comparison["remitproof"]["correct_resolutions"],
        summary["correct_abstentions"] == comparison["remitproof"]["correct_abstentions"],
        summary["false_escalations"] == comparison["remitproof"]["false_escalations"],
    )
    if not all(consistency):
        raise _artifact_error(
            "results.csv", "per-case outcomes disagree with the published metrics comparison"
        )

    class_rows = _csv_rows(
        contents["confusion_breakdown.csv"], "confusion_breakdown.csv", _CLASS_CSV_COLUMNS
    )
    expected_by_class: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {column: 0 for column in _CLASS_AGGREGATE_COLUMNS}
    )
    for row in rows:
        exception_class = row["exception_class"].strip()
        if not exception_class:
            raise _artifact_error("results.csv", "exception_class is missing or blank")
        aggregate = expected_by_class[exception_class]
        aggregate["records"] += 1
        aggregate["resolved"] += row["decision"] in {"matched_normally", "resolved"}
        aggregate["correct_resolutions"] += _csv_bool(
            row, "final_correct_resolution", "results.csv"
        )
        aggregate["human_review"] += row["decision"] == "human_review"
        aggregate["wrong_auto_resolutions"] += _csv_bool(
            row, "wrong_auto_resolution", "results.csv"
        )
        aggregate["false_escalations"] += _csv_bool(
            row, "false_escalation", "results.csv"
        )

    by_class: List[Dict[str, object]] = []
    seen_classes = set()
    for row in class_rows:
        try:
            exception_class = row["exception_class"].strip()
            if not exception_class:
                raise ValueError("blank exception class")
            if exception_class in seen_classes:
                raise ValueError("duplicate exception class")
            seen_classes.add(exception_class)
            by_class.append(
                {
                    "exception_class": exception_class,
                    **{
                        column: _csv_nonnegative_int(row, column, "confusion_breakdown.csv")
                        for column in _CLASS_AGGREGATE_COLUMNS
                    },
                }
            )
        except (KeyError, ValueError) as exc:
            raise _artifact_error(
                "confusion_breakdown.csv", "class breakdown row is malformed"
            ) from exc
    provided_by_class = {
        str(item["exception_class"]): {
            column: int(item[column])
            for column in _CLASS_AGGREGATE_COLUMNS
        }
        for item in by_class
    }
    if provided_by_class != dict(expected_by_class):
        raise _artifact_error(
            "confusion_breakdown.csv",
            "class aggregates disagree with results.csv",
        )
    if sum(item["records"] for item in by_class) != metrics["total_receipts"]:
        raise _artifact_error(
            "confusion_breakdown.csv", "class record counts disagree with total receipts"
        )

    return {
        "evaluation_generation_id": generation_id,
        "result_status": metrics["result_status"],
        "evaluation_mode": metrics["evaluation_mode"],
        "comparison_scope": metrics["comparison_scope"],
        "comparator_mode": comparison["llm_only"]["mode"],
        "comparator_label": comparison["llm_only"]["label"],
        "summary": summary,
        "cases": cases,
        "by_class": by_class,
    }


def load_metrics() -> Dict[str, object]:
    return load_results()[0]


def load_details() -> List[Dict[str, object]]:
    return load_results()[1]
