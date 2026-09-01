from fastapi import APIRouter, HTTPException

from app.utils.results import ResultsUnavailableError, load_results


router = APIRouter(prefix="/api", tags=["dashboard"])


def _exception_summary(detail):
    payment = detail["payment"]
    decision = detail["decision"]
    return {
        "payment_id": payment["payment_id"],
        "date": payment["date"],
        "payer": payment["payer_name"],
        "amount": payment["amount"],
        "currency": payment["currency"],
        "status": payment["status"],
        "exception_class": detail["operational_exception_class"],
        "decision": decision["decision"],
        "reason": decision["reason"],
        "latency_ms": decision["latency_ms"],
    }


@router.get("/dashboard")
def dashboard():
    try:
        metrics, details = load_results()
        exception_details = [
            detail for detail in details if detail["operational_is_exception"]
        ]
    except ResultsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    recent = sorted(
        (_exception_summary(detail) for detail in exception_details),
        key=lambda item: (item["date"], item["payment_id"]),
        reverse=True,
    )[:8]
    return {
        "total_receipts": metrics["total_receipts"],
        "matched_normally": metrics["matched_normally"],
        "exceptions": metrics["exceptions"],
        "resolved_by_remitproof": metrics["resolved_by_remitproof"],
        "human_review": metrics["human_review"],
        "incorrect_auto_resolution_rate": metrics["incorrect_auto_resolution_rate"],
        "throughput_per_minute": metrics["throughput_per_minute"],
        "mean_latency_ms": metrics["mean_latency_ms"],
        "evaluation_mode": metrics["evaluation_mode"],
        "cache": metrics["cache"],
        "recent_exceptions": recent,
    }
