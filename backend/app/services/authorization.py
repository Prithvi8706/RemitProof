from typing import List, Optional, Sequence, Tuple

from app.models import AlternativeAllocation, CandidateBundle, InvestigationProposal
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.proof_engine import verify_candidate


REASON_MULTIPLE_AUTHORIZABLE = "multiple_authorizable_allocations"
REASON_PROPOSAL_NOT_AUTHORIZABLE = "proposal_not_authorizable"

Authorizable = Tuple[AlternativeAllocation, InvestigationProposal]


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


def authorizable_allocations(
    bundle: CandidateBundle, alternatives: Sequence[AlternativeAllocation]
) -> List[Authorizable]:
    authorizable: List[Authorizable] = []
    for alternative in alternatives:
        proposal = canonical_proposal(bundle, alternative)
        proof = verify_candidate(bundle, proposal)
        sufficiency = evaluate_evidence_sufficiency(bundle, proposal, proof, list(alternatives))
        if sufficiency.safe_to_resolve:
            authorizable.append((alternative, proposal))
    return authorizable


def names_allocation(proposal: InvestigationProposal, alternative: AlternativeAllocation) -> bool:
    return (
        proposal.proposed_customer == alternative.customer_id
        and set(proposal.invoice_ids) == set(alternative.invoice_ids)
        and set(proposal.credit_ids) == set(alternative.credit_ids)
    )


def authorization_block_reason(
    proposal: InvestigationProposal, authorizable: Sequence[Authorizable]
) -> Optional[str]:
    if len(authorizable) >= 2:
        return REASON_MULTIPLE_AUTHORIZABLE
    if len(authorizable) == 1 and names_allocation(proposal, authorizable[0][0]):
        return None
    return REASON_PROPOSAL_NOT_AUTHORIZABLE
