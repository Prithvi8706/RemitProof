from typing import List, Set, Tuple

from app.models import (
    AlternativeAllocation,
    CandidateBundle,
    InvestigationProposal,
    ProofResult,
    SufficiencyResult,
)
from app.utils.remittance_semantics import classify_document_semantics


def _candidate_evidence_ids(bundle: CandidateBundle) -> Set[str]:
    return {
        *(customer.customer_id for customer in bundle.candidate_customers),
        *(invoice.invoice_id for invoice in bundle.candidate_invoices),
        *(credit.credit_id for credit in bundle.candidate_credits),
        *(email.email_id for email in bundle.candidate_emails),
    }


def _proposal_evidence_issues(
    bundle: CandidateBundle,
    proposal: InvestigationProposal,
) -> Tuple[Set[str], List[str]]:
    available_ids = _candidate_evidence_ids(bundle)
    cited_ids = set(proposal.evidence_ids)
    issues: List[str] = []

    if not proposal.evidence_ids:
        issues.append("proposal_evidence")
    for evidence_id in proposal.evidence_ids:
        if evidence_id not in available_ids:
            issues.append(evidence_id)

    for claim in proposal.semantic_claims:
        if not claim.evidence_ids:
            issues.append(claim.claim_id)
        for evidence_id in claim.evidence_ids:
            if evidence_id not in available_ids or evidence_id not in cited_ids:
                issues.append(evidence_id)

    # A credit is an accounting deduction, so the credit note itself must be
    # part of the proposal's cited evidence rather than inferred only from an
    # email or from the model's selected IDs.
    for credit_id in proposal.credit_ids:
        if credit_id not in cited_ids:
            issues.append(credit_id)

    return cited_ids, list(dict.fromkeys(issues))


def _proposal_matches(
    proposal: InvestigationProposal,
    allocation: AlternativeAllocation,
) -> bool:
    return (
        proposal.proposed_customer == allocation.customer_id
        and set(proposal.invoice_ids) == set(allocation.invoice_ids)
        and set(proposal.credit_ids) == set(allocation.credit_ids)
    )


def _evidence_disambiguates(
    bundle: CandidateBundle,
    proposal: InvestigationProposal,
    alternatives: List[AlternativeAllocation],
) -> bool:
    if len(alternatives) <= 1:
        return True

    # Customer, invoice, and credit records establish accounting facts, but
    # citing one of those records does not establish the payer's allocation
    # intent. Only explicit payment/remittance references or cited email text
    # can narrow competing allocations.
    payment_semantics = classify_document_semantics(
        f"{bundle.payment.bank_reference} {bundle.payment.remittance_reference}",
        bare_references_are_affirmative=True,
    )
    invoice_references = set(payment_semantics.affirmative_invoice_ids)
    credit_references = set(payment_semantics.affirmative_credit_ids)
    cited_ids = set(proposal.evidence_ids)
    for email in bundle.candidate_emails:
        if email.email_id not in cited_ids:
            continue
        semantics = classify_document_semantics(f"{email.subject} {email.body}")
        invoice_references.update(semantics.affirmative_invoice_ids)
        credit_references.update(semantics.affirmative_credit_ids)

    if not invoice_references:
        return False

    supported = []
    for allocation in alternatives:
        invoice_match = set(allocation.invoice_ids) == invoice_references
        credit_match = not credit_references or set(allocation.credit_ids) == credit_references
        if invoice_match and credit_match:
            supported.append(allocation)
    return len(supported) == 1 and _proposal_matches(proposal, supported[0])


def _abstention_reason(
    proof: ProofResult,
    ambiguous: bool,
    missing_required_evidence: List[str],
) -> str:
    priorities = (
        ("unsupported_currency_mismatch", "unsupported_currency_mismatch"),
        ("duplicate_allocation_risk", "duplicate_allocation_risk"),
        ("invoice_not_open", "invoice_not_open"),
        ("credit_not_valid", "invalid_credit_note"),
        ("missing_credit_note", "missing_credit_note"),
        ("unsupported_entity_relationship", "unsupported_entity_relationship"),
        ("financial_mismatch", "financial_mismatch"),
    )
    if proof.contradictions:
        return "contradictory_evidence"
    for code, reason in priorities:
        if code in proof.reason_codes:
            return reason
    if ambiguous:
        return "multiple_financially_valid_explanations"
    if missing_required_evidence:
        return "missing_required_evidence"
    return "evidence_not_sufficient"


def evaluate_evidence_sufficiency(
    bundle: CandidateBundle,
    proposal: InvestigationProposal,
    proof: ProofResult,
    alternatives: List[AlternativeAllocation],
) -> SufficiencyResult:
    proposal_alternatives = [allocation for allocation in alternatives if _proposal_matches(proposal, allocation)]
    competing_alternatives = [allocation for allocation in alternatives if not _proposal_matches(proposal, allocation)]
    _, evidence_issues = _proposal_evidence_issues(bundle, proposal)
    missing_required_evidence = list(
        dict.fromkeys([*proof.missing_required_evidence, *evidence_issues])
    )
    evidence_disambiguates = _evidence_disambiguates(bundle, proposal, alternatives)
    ambiguous = bool(competing_alternatives) and not evidence_disambiguates

    safe_to_resolve = all(
        (
            proof.financial_validity,
            proof.state_validity,
            proof.currency_validity,
            proof.entity_support,
            proof.credit_support,
            not proof.duplicate_risk,
            not proof.contradictions,
            not missing_required_evidence,
            bool(proposal_alternatives),
            not ambiguous,
        )
    )

    return SufficiencyResult(
        financial_validity=proof.financial_validity,
        entity_support=proof.entity_support,
        credit_support=proof.credit_support,
        alternative_allocations_exist=bool(competing_alternatives),
        evidence_disambiguates_alternatives=evidence_disambiguates,
        contradictions_exist=bool(proof.contradictions),
        missing_required_evidence=missing_required_evidence,
        duplicate_risk=proof.duplicate_risk,
        safe_to_resolve=safe_to_resolve,
        abstention_reason=None
        if safe_to_resolve
        else _abstention_reason(proof, ambiguous, missing_required_evidence),
    )
