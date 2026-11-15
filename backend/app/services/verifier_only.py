"""Verifier-only evaluation baseline.

Decides a payment with the existing deterministic checks and no model: for
every financially valid allocation it asks the unchanged proof engine and
sufficiency gate whether that allocation would be authorized, and resolves
only when exactly one would. It is an evaluation baseline and is never
imported by the pipeline or the API.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.models import AlternativeAllocation, CandidateBundle, InvestigationProposal
from app.services.alternative_finder import find_valid_alternatives
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.proof_engine import verify_candidate


REASON_UNIQUE = "unique_authorizable_allocation"
REASON_NO_ALLOCATION = "no_financially_valid_allocation"
REASON_NONE_AUTHORIZABLE = "no_authorizable_allocation"
REASON_MULTIPLE_AUTHORIZABLE = "multiple_authorizable_allocations"


@dataclass(frozen=True)
class VerifierOnlyOutcome:
    payment_id: str
    decision: str
    reason: str
    alternatives_considered: int
    authorizable_allocation_ids: Tuple[str, ...]
    proposal: Optional[InvestigationProposal]


def canonical_proposal(
    bundle: CandidateBundle, alternative: AlternativeAllocation
) -> InvestigationProposal:
    email_ids = [
        email.email_id
        for email in bundle.candidate_emails
        if email.customer_id == alternative.customer_id
    ]
    evidence: List[str] = list(
        dict.fromkeys(
            [alternative.customer_id] + sorted(alternative.credit_ids) + email_ids
        )
    )
    return InvestigationProposal(
        payment_id=bundle.payment.payment_id,
        proposed_customer=alternative.customer_id,
        invoice_ids=list(alternative.invoice_ids),
        credit_ids=list(alternative.credit_ids),
        evidence_ids=evidence,
    )


def verifier_only_decision(bundle: CandidateBundle) -> VerifierOnlyOutcome:
    alternatives = find_valid_alternatives(bundle)
    authorizable: List[Tuple[AlternativeAllocation, InvestigationProposal]] = []
    for alternative in alternatives:
        proposal = canonical_proposal(bundle, alternative)
        proof = verify_candidate(bundle, proposal)
        sufficiency = evaluate_evidence_sufficiency(bundle, proposal, proof, alternatives)
        if sufficiency.safe_to_resolve:
            authorizable.append((alternative, proposal))

    selected: Optional[InvestigationProposal] = None
    if len(authorizable) == 1:
        decision, reason = "resolve", REASON_UNIQUE
        selected = authorizable[0][1]
    elif not alternatives:
        decision, reason = "abstain", REASON_NO_ALLOCATION
    elif not authorizable:
        decision, reason = "abstain", REASON_NONE_AUTHORIZABLE
    else:
        decision, reason = "abstain", REASON_MULTIPLE_AUTHORIZABLE

    return VerifierOnlyOutcome(
        payment_id=bundle.payment.payment_id,
        decision=decision,
        reason=reason,
        alternatives_considered=len(alternatives),
        authorizable_allocation_ids=tuple(
            alternative.allocation_id for alternative, _ in authorizable
        ),
        proposal=selected,
    )


class VerifierOnlyInvestigator:
    def __init__(self) -> None:
        self.outcomes: Dict[str, VerifierOnlyOutcome] = {}

    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        outcome = verifier_only_decision(bundle)
        self.outcomes[bundle.payment.payment_id] = outcome
        if outcome.proposal is not None:
            return outcome.proposal
        return InvestigationProposal(payment_id=bundle.payment.payment_id)
