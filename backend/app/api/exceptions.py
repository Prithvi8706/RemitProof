from typing import Dict

from fastapi import APIRouter, HTTPException

from app.api.dashboard import _exception_summary
from app.utils.results import ResultsUnavailableError, load_details


router = APIRouter(prefix="/api/exceptions", tags=["exceptions"])


_PUBLIC_EXCEPTION_DETAIL_FIELDS = (
    "payment",
    "baseline",
    "decision",
    "proposal",
    "candidates",
    "proposed_allocation",
    "evidence",
    "proof",
    "alternatives",
    "sufficiency",
    "counterfactuals",
    "investigator_error",
)


def _public_exception_detail(detail: Dict[str, object]) -> Dict[str, object]:
    """Return the operational exception contract without evaluator labels."""
    payload = {
        field: detail[field]
        for field in _PUBLIC_EXCEPTION_DETAIL_FIELDS
    }
    payload["exception_class"] = detail["operational_exception_class"]
    payload["is_exception"] = detail["operational_is_exception"]
    proposal = detail.get("proposal") or {}
    cited_ids = set(proposal.get("evidence_ids", [])) if isinstance(proposal, dict) else set()
    evidence = detail.get("evidence", [])
    payload["model_cited_evidence"] = [
        record for record in evidence
        if isinstance(record, dict) and record.get("evidence_id") in cited_ids
    ]
    payload["audit_records"] = [
        record for record in evidence
        if isinstance(record, dict) and record.get("evidence_id") not in cited_ids
    ]
    return payload


@router.get("")
def list_exceptions():
    try:
        details = load_details()
    except ResultsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    rows = [
        _exception_summary(detail)
        for detail in details
        if detail["operational_is_exception"]
    ]
    return sorted(rows, key=lambda row: row["payment_id"])


@router.get("/{payment_id}")
def exception_detail(payment_id: str):
    try:
        details = load_details()
    except ResultsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    for detail in details:
        if (
            detail["operational_is_exception"]
            and detail["payment"]["payment_id"] == payment_id
        ):
            return _public_exception_detail(detail)
    raise HTTPException(status_code=404, detail=f"Exception {payment_id} was not found.")
