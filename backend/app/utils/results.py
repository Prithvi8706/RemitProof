import json
from pathlib import Path
from typing import Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "results"


class ResultsUnavailableError(RuntimeError):
    """Raised when generated result artifacts cannot be served safely."""


def _artifact_error(filename: str, reason: str) -> ResultsUnavailableError:
    return ResultsUnavailableError(
        f"Generated artifact {filename} is unavailable: {reason}. "
        "Run backend/scripts/evaluate.py to publish a complete result set."
    )


def _load_json(filename: str):
    path = RESULTS_DIR / filename
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise _artifact_error(filename, "file is missing") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _artifact_error(filename, "file is unreadable or malformed") from exc


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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
    fields: Dict[str, object],
) -> None:
    for field, expected in fields.items():
        if field not in value:
            raise _artifact_error(filename, f"{location}.{field} is missing")
        field_value = value[field]
        valid = (
            isinstance(field_value, expected)
            if isinstance(expected, type)
            else bool(expected(field_value))
        )
        if not valid:
            raise _artifact_error(filename, f"{location}.{field} has an invalid type")


def _normalise_timing_metadata(metrics: Dict[str, object]) -> None:
    evaluation_mode = metrics.get("evaluation_mode", "unknown")
    if not isinstance(evaluation_mode, str):
        raise _artifact_error("metrics.json", "evaluation_mode must be a string")

    cache = metrics.get("cache", {})
    if cache is None:
        cache = {}
    if not isinstance(cache, dict):
        raise _artifact_error("metrics.json", "cache must be an object")

    normalised_cache = dict(cache)
    normalised_cache.setdefault("status", "unknown")
    normalised_cache.setdefault("model_inference_included", None)
    metrics["evaluation_mode"] = evaluation_mode
    metrics["cache"] = normalised_cache


def _validate_metrics(raw: object) -> Dict[str, object]:
    metrics = dict(_require_mapping(raw, "metrics.json", "root"))
    _require_fields(
        metrics,
        "metrics.json",
        "root",
        {
            "total_receipts": lambda value: isinstance(value, int) and not isinstance(value, bool),
            "matched_normally": lambda value: isinstance(value, int) and not isinstance(value, bool),
            "exceptions": lambda value: isinstance(value, int) and not isinstance(value, bool),
            "resolved_by_remitproof": lambda value: isinstance(value, int) and not isinstance(value, bool),
            "human_review": lambda value: isinstance(value, int) and not isinstance(value, bool),
            "incorrect_auto_resolution_rate": _is_number,
            "throughput_per_minute": _is_number,
            "mean_latency_ms": _is_number,
            "held_out": dict,
        },
    )
    for field in (
        "total_receipts",
        "matched_normally",
        "exceptions",
        "resolved_by_remitproof",
        "human_review",
    ):
        if int(metrics[field]) < 0:
            raise _artifact_error("metrics.json", f"{field} cannot be negative")
    _normalise_timing_metadata(metrics)
    return metrics


def _validate_detail(raw: object, index: int) -> Dict[str, object]:
    location = f"root[{index}]"
    detail = _require_mapping(raw, "details.json", location)
    _require_fields(
        detail,
        "details.json",
        location,
        {
            "is_exception": bool,
            "exception_class": str,
            "payment": dict,
            "decision": dict,
            "proposal": lambda value: value is None or isinstance(value, dict),
            "evidence": list,
            "proof": lambda value: value is None or isinstance(value, dict),
            "alternatives": list,
            "sufficiency": lambda value: value is None or isinstance(value, dict),
        },
    )
    payment = _require_mapping(detail["payment"], "details.json", f"{location}.payment")
    _require_fields(
        payment,
        "details.json",
        f"{location}.payment",
        {
            "payment_id": str,
            "date": str,
            "payer_name": str,
            "amount": lambda value: isinstance(value, (str, int, float)) and not isinstance(value, bool),
            "currency": str,
            "status": str,
        },
    )
    decision = _require_mapping(detail["decision"], "details.json", f"{location}.decision")
    _require_fields(
        decision,
        "details.json",
        f"{location}.decision",
        {
            "decision": str,
            "reason": str,
            "latency_ms": _is_number,
        },
    )
    return detail


def _validate_details(raw: object) -> List[Dict[str, object]]:
    rows = _require_list(raw, "details.json", "root")
    return [_validate_detail(row, index) for index, row in enumerate(rows)]


def load_metrics() -> Dict[str, object]:
    return _validate_metrics(_load_json("metrics.json"))


def load_details() -> List[Dict[str, object]]:
    return _validate_details(_load_json("details.json"))


def load_results() -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    """Load one internally consistent generation for readiness checks."""
    metrics = load_metrics()
    details = load_details()
    exception_count = sum(bool(detail["is_exception"]) for detail in details)
    if int(metrics["total_receipts"]) != len(details):
        raise _artifact_error("metrics.json/details.json", "total receipt counts disagree")
    if int(metrics["exceptions"]) != exception_count:
        raise _artifact_error("metrics.json/details.json", "exception counts disagree")
    return metrics, details
