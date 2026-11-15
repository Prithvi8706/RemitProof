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
from app.services.audit_builder import build_allocation, build_evidence
from app.services.authorization import authorizable_allocations, authorization_block_reason
from app.services.baseline_matcher import baseline_match
from app.services.decision_artifacts import (
    build_conflict,
    build_counterfactuals,
    build_decision_artifact,
)
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.proof_engine import verify_candidate
from app.services.proof_set import build_proof_set
from app.services.search import STATUS_UNKNOWN, search
from app.services.unread_instructions import REASON_UNREAD_INSTRUCTION, find_unread_instructions
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

    proof_set = build_proof_set(payment, dataset)
    candidates = proof_set.prompt_bundle
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

    outcome = search(proof_set)
    if outcome.status == STATUS_UNKNOWN:
        baseline = BaselineResult(
            payment_id=payment.payment_id,
            status="unresolved",
            reason="search_incomplete",
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        decision = Decision(
            payment_id=payment.payment_id,
            decision="human_review",
            proof={
                "search_status": outcome.status,
                "search_detail": outcome.detail,
                "incomplete_reasons": list(outcome.incomplete_reasons),
                "investigator_skipped": True,
            },
            reason="search_incomplete",
            latency_ms=latency_ms,
        )
        return ProcessingResult(
            payment=payment.model_dump(mode="json"),
            baseline=baseline,
            decision=decision,
            candidates=_candidate_dump(candidates),
        )

    proof_bundle = proof_set.proof_bundle
    unread = find_unread_instructions(proof_bundle)
    if unread.blocks:
        baseline = BaselineResult(
            payment_id=payment.payment_id,
            status="unresolved",
            reason=REASON_UNREAD_INSTRUCTION,
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        decision = Decision(
            payment_id=payment.payment_id,
            decision="human_review",
            proof={
                "unread_email_ids": list(unread.email_ids),
                "unread_document_ids": list(unread.document_ids),
                "investigator_skipped": True,
            },
            reason=REASON_UNREAD_INSTRUCTION,
            latency_ms=latency_ms,
        )
        return ProcessingResult(
            payment=payment.model_dump(mode="json"),
            baseline=baseline,
            decision=decision,
            candidates=_candidate_dump(proof_bundle),
        )

    baseline = baseline_match(proof_bundle, alternatives=list(outcome.alternatives))
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
            candidates=_candidate_dump(proof_bundle),
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
            candidates=_candidate_dump(proof_bundle),
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
            candidates=_candidate_dump(proof_bundle),
            investigator_error=str(exc),
        )

    proof = verify_candidate(proof_bundle, proposal)
    alternatives = list(outcome.alternatives)
    sufficiency = evaluate_evidence_sufficiency(
        proof_bundle,
        proposal,
        proof,
        alternatives,
    )
    if sufficiency.safe_to_resolve:
        block_reason = authorization_block_reason(
            proposal,
            authorizable_allocations(proof_bundle, alternatives),
        )
        if block_reason is not None:
            sufficiency = sufficiency.model_copy(
                update={"safe_to_resolve": False, "abstention_reason": block_reason}
            )
    conflict = build_conflict(payment.payment_id, proof, alternatives, sufficiency)
    counterfactuals = build_counterfactuals(proof_bundle, proposal, alternatives, sufficiency)
    decision_artifact = build_decision_artifact(
        payment.payment_id, proposal, proof, alternatives, sufficiency, counterfactuals
    )
    latency_ms = round((time.perf_counter() - started) * 1000)
    if sufficiency.safe_to_resolve:
        decision_state = "resolved"
        reason = "Evidence uniquely supports the proposed allocation and every deterministic proof passed."
    else:
        decision_state = "human_review"
        reason = sufficiency.abstention_reason or "evidence_not_sufficient"
    audit_evidence = build_evidence(proof_bundle, proposal)
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
        candidates=_candidate_dump(proof_bundle),
        proposed_allocation=build_allocation(proof_bundle, proposal),
        evidence=audit_evidence,
        proof=proof,
        alternatives=alternatives,
        conflict=conflict,
        sufficiency=sufficiency,
        counterfactuals=counterfactuals,
        resolution_proof=decision_artifact if sufficiency.safe_to_resolve else None,
        blocked_decision=decision_artifact if not sufficiency.safe_to_resolve else None,
    )
