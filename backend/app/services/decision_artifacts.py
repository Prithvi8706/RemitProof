from typing import List, Optional, Tuple

from app.models import (
    AlternativeAllocation,
    CandidateBundle,
    Conflict,
    CounterfactualEvidence,
    InvestigationProposal,
    ProofResult,
    SufficiencyResult,
)
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.proof_engine import verify_candidate


def build_conflict(
    payment_id: str,
    proof: ProofResult,
    alternatives: List[AlternativeAllocation],
    sufficiency: SufficiencyResult,
) -> Optional[Conflict]:
    if proof.contradictions:
        return Conflict(
            conflict_id=f"CONF_{payment_id.removeprefix('PAY_')}",
            payment_id=payment_id,
            type="contradictory_remittance",
            allocation_ids=[item.allocation_id for item in alternatives],
            reason="Authoritative evidence contradicts the proposed allocation.",
            required_disambiguation=list(sufficiency.missing_required_evidence),
            status="unresolved",
        )
    if len(alternatives) > 1:
        return Conflict(
            conflict_id=f"CONF_{payment_id.removeprefix('PAY_')}",
            payment_id=payment_id,
            type="multiple_valid_allocations",
            allocation_ids=[item.allocation_id for item in alternatives],
            reason=f"{len(alternatives)} allocations satisfy the financial constraints.",
            required_disambiguation=[
                "explicit remittance instruction",
                "invoice reference",
                "trusted customer communication",
            ],
            status="cleared" if sufficiency.evidence_disambiguates_alternatives else "unresolved",
        )
    if proof.duplicate_risk:
        conflict_type = "duplicate_allocation_conflict"
        reason = "A selected record is already consumed or allocated."
    elif not proof.currency_validity:
        conflict_type = "currency_conflict"
        reason = "The payment and selected records do not share a supported currency."
    elif not proof.state_validity:
        conflict_type = "state_conflict"
        reason = "A selected financial record is not eligible for allocation."
    elif not proof.entity_support:
        conflict_type = "entity_identity_conflict"
        reason = "The payer-to-customer relationship is not supported."
    elif not proof.credit_support:
        conflict_type = "credit_application_conflict"
        reason = "The proposed credit application is not supported."
    elif sufficiency.missing_required_evidence:
        conflict_type = "missing_required_evidence"
        reason = "Required authorization evidence is missing."
    else:
        return None
    return Conflict(
        conflict_id=f"CONF_{payment_id.removeprefix('PAY_')}",
        payment_id=payment_id,
        type=conflict_type,
        allocation_ids=[item.allocation_id for item in alternatives],
        reason=reason,
        required_disambiguation=list(sufficiency.missing_required_evidence),
        status="unresolved",
    )


def _without_evidence(
    bundle: CandidateBundle,
    proposal: InvestigationProposal,
    evidence_id: str,
) -> Tuple[CandidateBundle, InvestigationProposal]:
    payment = bundle.payment
    if evidence_id == payment.payment_id:
        payment = payment.model_copy(
            update={"bank_reference": "", "remittance_reference": ""}
        )
    reduced_bundle = bundle.model_copy(
        update={
            "payment": payment,
            "candidate_customers": [item for item in bundle.candidate_customers if item.customer_id != evidence_id],
            "candidate_invoices": [item for item in bundle.candidate_invoices if item.invoice_id != evidence_id],
            "candidate_credits": [item for item in bundle.candidate_credits if item.credit_id != evidence_id],
            "candidate_emails": [item for item in bundle.candidate_emails if item.email_id != evidence_id],
        }
    )
    reduced_claims = [
        claim.model_copy(update={"evidence_ids": [item for item in claim.evidence_ids if item != evidence_id]})
        for claim in proposal.semantic_claims
    ]
    reduced_proposal = proposal.model_copy(
        update={
            "evidence_ids": [item for item in proposal.evidence_ids if item != evidence_id],
            "semantic_claims": reduced_claims,
        }
    )
    return reduced_bundle, reduced_proposal


def build_counterfactuals(
    bundle: CandidateBundle,
    proposal: InvestigationProposal,
    alternatives: List[AlternativeAllocation],
    sufficiency: SufficiencyResult,
) -> List[CounterfactualEvidence]:
    rows = []
    for evidence_id in sufficiency.uniquely_distinguishing_evidence:
        reduced_bundle, reduced_proposal = _without_evidence(bundle, proposal, evidence_id)
        reduced_proof = verify_candidate(reduced_bundle, reduced_proposal)
        reduced_sufficiency = evaluate_evidence_sufficiency(
            reduced_bundle, reduced_proposal, reduced_proof, alternatives
        )
        changed = sufficiency.safe_to_resolve and not reduced_sufficiency.safe_to_resolve
        rows.append(
            CounterfactualEvidence(
                evidence_id=evidence_id,
                decision_with_evidence="resolved" if sufficiency.safe_to_resolve else "human_review",
                decision_without_evidence="resolved" if reduced_sufficiency.safe_to_resolve else "human_review",
                decision_critical=changed,
                reason=_counterfactual_reason(changed, len(alternatives)),
            )
        )
    return rows


def _counterfactual_reason(
    changed: bool,
    alternative_count: int,
) -> str:
    if not changed:
        return "Removing this record does not change the authorization decision."
    if alternative_count > 1:
        return "Without this record, competing financially valid allocations remain."
    return "Without this record, the proposed allocation lacks required evidence."


def build_decision_artifact(
    payment_id: str,
    proposal: InvestigationProposal,
    proof: ProofResult,
    alternatives: List[AlternativeAllocation],
    sufficiency: SufficiencyResult,
    counterfactuals: List[CounterfactualEvidence],
) -> dict:
    allocation = {
        "customer": proposal.proposed_customer,
        "invoices": proposal.invoice_ids,
        "credits": proposal.credit_ids,
    }
    critical = [item.evidence_id for item in counterfactuals if item.decision_critical]
    if sufficiency.safe_to_resolve:
        return {
            "artifact_type": "resolution_proof",
            "payment_id": payment_id,
            "decision": "resolved",
            "proposal": allocation,
            "proof": proof.model_dump(mode="json"),
            "alternatives": {"count": len(alternatives), "detected": len(alternatives) > 1},
            "evidence_sufficiency": {
                "chosen_proposal_supported": sufficiency.chosen_proposal_supported,
                "alternatives_eliminated": sufficiency.alternatives_eliminated,
                "contradictions": proof.contradictions,
                "decision_critical_evidence": critical,
            },
            "authorization": "safe_to_resolve",
        }
    return {
        "artifact_type": "blocked_decision",
        "payment_id": payment_id,
        "decision": "human_review",
        "reason": sufficiency.abstention_reason,
        "surviving_alternatives": [item.model_dump(mode="json") for item in alternatives],
        "missing_disambiguation": sufficiency.missing_required_evidence,
        "proof_status": {
            "financial_constraints": (
                "pass_for_multiple_options"
                if len(alternatives) > 1
                else "pass"
                if alternatives
                else "failed"
            ),
            "entity_support": "pass" if proof.entity_support else "fail",
            "contradictions": proof.contradictions,
            "uniqueness": "fail" if len(alternatives) > 1 else "not_established",
        },
    }
