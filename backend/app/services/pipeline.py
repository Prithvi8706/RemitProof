import time
from typing import Protocol

from app.models import (
    BaselineResult,
    CandidateBundle,
    Decision,
    InvestigationProposal,
    ProcessingResult,
)
from app.services.ai_investigator import InvestigatorError
from app.services.alternative_finder import find_valid_alternatives
from app.services.audit_builder import build_allocation, build_evidence
from app.services.baseline_matcher import baseline_match
from app.services.candidate_retriever import retrieve_candidates
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.proof_engine import verify_candidate
from app.utils.loaders import Dataset


class Investigator(Protocol):
    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        ...


def _candidate_dump(bundle: CandidateBundle):
    return {
        "customers": [item.model_dump(mode="json") for item in bundle.candidate_customers],
        "invoices": [item.model_dump(mode="json") for item in bundle.candidate_invoices],
        "credits": [item.model_dump(mode="json") for item in bundle.candidate_credits],
        "emails": [item.model_dump(mode="json") for item in bundle.candidate_emails],
    }


def process_payment(
    payment_id: str,
    dataset: Dataset,
    investigator: Investigator,
) -> ProcessingResult:
    started = time.perf_counter()
    payment = dataset.payments_by_id.get(payment_id)
    if payment is None:
        raise KeyError(f"Unknown payment: {payment_id}")

    candidates = retrieve_candidates(payment, dataset)
    if payment.payment_id in dataset.replayed_payment_ids:
        baseline = BaselineResult(
            payment_id=payment.payment_id,
            status="unresolved",
            reason="duplicate_bank_transaction",
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        decision = Decision(
            payment_id=payment.payment_id,
            decision="human_review",
            proof={
                "duplicate_risk": True,
                "reason_code": "duplicate_bank_transaction",
                "investigator_skipped": True,
            },
            reason=(
                "Another payment record has the same normalized bank reference and "
                "transaction facts; autonomous allocation is blocked."
            ),
            latency_ms=latency_ms,
        )
        return ProcessingResult(
            payment=payment.model_dump(mode="json"),
            baseline=baseline,
            decision=decision,
            candidates=_candidate_dump(candidates),
        )

    baseline = baseline_match(candidates)
    if baseline.status == "matched":
        latency_ms = round((time.perf_counter() - started) * 1000)
        decision = Decision(
            payment_id=payment.payment_id,
            decision="matched_normally",
            customer_id=baseline.customer_id,
            invoice_ids=baseline.matched_invoices,
            credit_ids=baseline.matched_credits,
            proof={"baseline_reason": baseline.reason, "candidate_count": baseline.candidate_count},
            evidence=[
                *(baseline.matched_invoices),
                *(baseline.matched_credits),
                *([baseline.customer_id] if baseline.customer_id else []),
            ],
            reason="Unique deterministic allocation; no AI investigation required.",
            latency_ms=latency_ms,
        )
        return ProcessingResult(
            payment=payment.model_dump(mode="json"),
            baseline=baseline,
            decision=decision,
            candidates=_candidate_dump(candidates),
        )

    if payment.status != "unmatched":
        latency_ms = round((time.perf_counter() - started) * 1000)
        decision = Decision(
            payment_id=payment.payment_id,
            decision="human_review",
            proof={
                "payment_status": payment.status,
                "baseline_reason": baseline.reason,
                "candidate_count": baseline.candidate_count,
                "investigator_skipped": True,
            },
            reason=(
                f"Payment status is '{payment.status}'; AI investigation is only allowed "
                "for unmatched payments."
            ),
            latency_ms=latency_ms,
        )
        return ProcessingResult(
            payment=payment.model_dump(mode="json"),
            baseline=baseline,
            decision=decision,
            candidates=_candidate_dump(candidates),
        )

    try:
        proposal = investigator.investigate(candidates)
    except InvestigatorError as exc:
        latency_ms = round((time.perf_counter() - started) * 1000)
        decision = Decision(
            payment_id=payment.payment_id,
            decision="human_review",
            reason="Investigator unavailable; no autonomous action is allowed.",
            latency_ms=latency_ms,
        )
        return ProcessingResult(
            payment=payment.model_dump(mode="json"),
            baseline=baseline,
            decision=decision,
            candidates=_candidate_dump(candidates),
            investigator_error=str(exc),
        )

    proof = verify_candidate(candidates, proposal)
    alternatives = find_valid_alternatives(candidates)
    sufficiency = evaluate_evidence_sufficiency(
        candidates,
        proposal,
        proof,
        alternatives,
    )
    latency_ms = round((time.perf_counter() - started) * 1000)
    if sufficiency.safe_to_resolve:
        decision_state = "resolved"
        reason = "Evidence uniquely supports the proposed allocation and every deterministic proof passed."
    else:
        decision_state = "human_review"
        reason = sufficiency.abstention_reason or "evidence_not_sufficient"
    audit_evidence = build_evidence(candidates, proposal)
    decision = Decision(
        payment_id=payment.payment_id,
        decision=decision_state,
        customer_id=proposal.proposed_customer,
        invoice_ids=proposal.invoice_ids,
        credit_ids=proposal.credit_ids,
        proof=proof.model_dump(mode="json"),
        evidence=[str(item["evidence_id"]) for item in audit_evidence],
        reason=reason,
        latency_ms=latency_ms,
    )
    return ProcessingResult(
        payment=payment.model_dump(mode="json"),
        baseline=baseline,
        decision=decision,
        proposal=proposal.model_dump(mode="json"),
        candidates=_candidate_dump(candidates),
        proposed_allocation=build_allocation(candidates, proposal),
        evidence=audit_evidence,
        proof=proof,
        alternatives=alternatives,
        sufficiency=sufficiency,
    )
