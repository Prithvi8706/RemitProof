from typing import List, Set, Tuple

from app.models import (
    AlternativeAllocation,
    CandidateBundle,
    EvidenceAlternativeAssessment,
    InvestigationProposal,
    ProofResult,
    SufficiencyResult,
)
from app.utils.remittance_semantics import (
    classify_document_semantics,
    superseded_allocation_email_ids,
    trusted_remittance_sender_ids,
)


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
    credit_amount_references = set(payment_semantics.affirmative_credit_amounts)
    cited_ids = set(proposal.evidence_ids)
    trusted_sender_ids = trusted_remittance_sender_ids(
        bundle.candidate_emails,
        bundle.payment,
        bundle.candidate_customers,
        customer_id=proposal.proposed_customer,
    )
    superseded_ids = superseded_allocation_email_ids(
        bundle.candidate_emails,
        payment=bundle.payment,
        trusted_sender_ids=trusted_sender_ids,
    )
    for email in bundle.candidate_emails:
        if (
            email.email_id not in cited_ids
            or email.email_id in superseded_ids
            or email.customer_id != proposal.proposed_customer
            or email.sender.casefold() not in trusted_sender_ids
        ):
            continue
        semantics = classify_document_semantics(f"{email.subject} {email.body}")
        invoice_references.update(semantics.affirmative_invoice_ids)
        credit_references.update(semantics.affirmative_credit_ids)
        credit_amount_references.update(semantics.affirmative_credit_amounts)

    if not invoice_references and not credit_references and not credit_amount_references:
        return False

    supported = []
    for allocation in alternatives:
        invoice_match = not invoice_references or set(allocation.invoice_ids) == invoice_references
        credit_match = not credit_references or set(allocation.credit_ids) == credit_references
        allocation_credit_amounts = {
            credit.amount
            for credit in bundle.candidate_credits
            if credit.credit_id in allocation.credit_ids
        }
        amount_match = (
            not credit_amount_references
            or (
                allocation_credit_amounts == credit_amount_references
                and (
                    credit_references
                    or len(allocation.credit_ids) == len(credit_amount_references)
                )
            )
        )
        if invoice_match and credit_match and amount_match:
            supported.append(allocation)
    return len(supported) == 1 and _proposal_matches(proposal, supported[0])


def _evidence_matrix(
    bundle: CandidateBundle,
    proposal: InvestigationProposal,
    alternatives: List[AlternativeAllocation],
) -> List[EvidenceAlternativeAssessment]:
    """Explain how authoritative evidence bears on every financially valid allocation."""

    emails = {email.email_id: email for email in bundle.candidate_emails}
    customers = {customer.customer_id for customer in bundle.candidate_customers}
    invoices = {invoice.invoice_id for invoice in bundle.candidate_invoices}
    credits = {credit.credit_id for credit in bundle.candidate_credits}
    credit_amounts = {credit.credit_id: credit.amount for credit in bundle.candidate_credits}
    trusted_sender_ids = trusted_remittance_sender_ids(
        bundle.candidate_emails,
        bundle.payment,
        bundle.candidate_customers,
        customer_id=proposal.proposed_customer,
    )
    superseded_ids = superseded_allocation_email_ids(
        bundle.candidate_emails,
        payment=bundle.payment,
        trusted_sender_ids=trusted_sender_ids,
    )
    rows: List[EvidenceAlternativeAssessment] = []

    payment_semantics = classify_document_semantics(
        f"{bundle.payment.bank_reference} {bundle.payment.remittance_reference}",
        bare_references_are_affirmative=True,
    )
    payment_has_allocation_evidence = bool(
        payment_semantics.affirmative_invoice_ids
        or payment_semantics.affirmative_credit_ids
        or payment_semantics.affirmative_credit_amounts
        or payment_semantics.prohibited_invoice_ids
        or payment_semantics.noncurrent_invoice_ids
        or payment_semantics.prohibited_credit_ids
        or payment_semantics.prohibited_credit_amounts
    )
    if payment_has_allocation_evidence:
        for allocation in alternatives:
            allocation_invoices = set(allocation.invoice_ids)
            allocation_credits = set(allocation.credit_ids)
            selected_credit_amounts = {
                credit_amounts[credit_id]
                for credit_id in allocation_credits
                if credit_id in credit_amounts
            }
            prohibited = bool(
                allocation_invoices.intersection(payment_semantics.prohibited_invoice_ids)
                or allocation_invoices.intersection(payment_semantics.noncurrent_invoice_ids)
                or allocation_credits.intersection(payment_semantics.prohibited_credit_ids)
                or selected_credit_amounts.intersection(
                    payment_semantics.prohibited_credit_amounts
                )
            )
            has_affirmative_allocation = bool(
                payment_semantics.affirmative_invoice_ids
                or payment_semantics.affirmative_credit_ids
                or payment_semantics.affirmative_credit_amounts
            )
            invoice_support = not payment_semantics.affirmative_invoice_ids or (
                allocation_invoices == set(payment_semantics.affirmative_invoice_ids)
            )
            credit_id_support = not payment_semantics.affirmative_credit_ids or (
                allocation_credits == set(payment_semantics.affirmative_credit_ids)
            )
            credit_amount_support = not payment_semantics.affirmative_credit_amounts or (
                selected_credit_amounts
                == set(payment_semantics.affirmative_credit_amounts)
                and (
                    payment_semantics.affirmative_credit_ids
                    or len(allocation_credits)
                    == len(payment_semantics.affirmative_credit_amounts)
                )
            )
            relationship = "irrelevant"
            reason = "The payment remittance does not distinguish this allocation."
            if prohibited:
                relationship = "contradicts"
                reason = "The payment remittance explicitly prohibits a selected record."
            elif (
                has_affirmative_allocation
                and invoice_support
                and credit_id_support
                and credit_amount_support
            ):
                relationship = "supports"
                reason = "The payment remittance explicitly identifies this allocation."
            rows.append(
                EvidenceAlternativeAssessment(
                    evidence_id=bundle.payment.payment_id,
                    allocation_id=allocation.allocation_id,
                    relationship=relationship,
                    reason=reason,
                )
            )

    for evidence_id in proposal.evidence_ids:
        for allocation in alternatives:
            relationship = "irrelevant"
            reason = "The record does not distinguish this allocation."
            if evidence_id in emails:
                email = emails[evidence_id]
                semantics = classify_document_semantics(f"{email.subject} {email.body}")
                allocation_invoices = set(allocation.invoice_ids)
                allocation_credits = set(allocation.credit_ids)
                selected_credit_amounts = {
                    credit_amounts[credit_id]
                    for credit_id in allocation_credits
                    if credit_id in credit_amounts
                }
                prohibited = bool(
                    allocation_invoices.intersection(semantics.prohibited_invoice_ids)
                    or allocation_invoices.intersection(semantics.noncurrent_invoice_ids)
                    or allocation_credits.intersection(semantics.prohibited_credit_ids)
                    or selected_credit_amounts.intersection(semantics.prohibited_credit_amounts)
                )
                has_affirmative_allocation = bool(
                    semantics.affirmative_invoice_ids
                    or semantics.affirmative_credit_ids
                    or semantics.affirmative_credit_amounts
                )
                invoice_support = not semantics.affirmative_invoice_ids or (
                    allocation_invoices == set(semantics.affirmative_invoice_ids)
                )
                credit_id_support = not semantics.affirmative_credit_ids or (
                    allocation_credits == set(semantics.affirmative_credit_ids)
                )
                credit_amount_support = not semantics.affirmative_credit_amounts or (
                    selected_credit_amounts == set(semantics.affirmative_credit_amounts)
                    and (
                        semantics.affirmative_credit_ids
                        or len(allocation_credits)
                        == len(semantics.affirmative_credit_amounts)
                    )
                )
                if prohibited:
                    relationship = "contradicts"
                    reason = "The remittance explicitly prohibits a selected record."
                elif evidence_id in superseded_ids:
                    relationship = "superseded"
                    reason = (
                        "A later payment-linked correction from a trusted source "
                        "replaces this instruction."
                    )
                elif (
                    email.customer_id == allocation.customer_id
                    and email.sender.casefold() in trusted_sender_ids
                    and has_affirmative_allocation
                    and invoice_support
                    and credit_id_support
                    and credit_amount_support
                ):
                    relationship = "supports"
                    reason = "The remittance explicitly identifies this allocation."
            elif evidence_id in customers and evidence_id == allocation.customer_id:
                relationship = "shared_fact"
                reason = "The customer record supports entity validity, not payer intent."
            elif evidence_id in invoices and evidence_id in allocation.invoice_ids:
                relationship = "shared_fact"
                reason = "The invoice supports financial validity, not payer intent."
            elif evidence_id in credits and evidence_id in allocation.credit_ids:
                relationship = "shared_fact"
                reason = "The credit note supports deduction validity, not payer intent."
            rows.append(
                EvidenceAlternativeAssessment(
                    evidence_id=evidence_id,
                    allocation_id=allocation.allocation_id,
                    relationship=relationship,
                    reason=reason,
                )
            )
    return rows


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
    evidence_matrix = _evidence_matrix(bundle, proposal, alternatives)
    proposal_ids = {
        allocation.allocation_id
        for allocation in proposal_alternatives
    }
    distinguishing_evidence = sorted(
        {
            row.evidence_id
            for row in evidence_matrix
            if row.allocation_id in proposal_ids
            and row.relationship == "supports"
            and not any(
                other.evidence_id == row.evidence_id
                and other.allocation_id not in proposal_ids
                and other.relationship == "supports"
                for other in evidence_matrix
            )
        }
    )
    chosen_semantically_supported = bool(proposal_alternatives) and (
        not competing_alternatives
        or any(
            row.allocation_id in proposal_ids and row.relationship == "supports"
            for row in evidence_matrix
        )
    )
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
        chosen_proposal_supported=chosen_semantically_supported and not evidence_issues,
        alternatives_eliminated=not competing_alternatives or evidence_disambiguates,
        uniquely_distinguishing_evidence=distinguishing_evidence,
        evidence_alternative_matrix=evidence_matrix,
        contradictions_exist=bool(proof.contradictions),
        missing_required_evidence=missing_required_evidence,
        duplicate_risk=proof.duplicate_risk,
        safe_to_resolve=safe_to_resolve,
        abstention_reason=None
        if safe_to_resolve
        else _abstention_reason(proof, ambiguous, missing_required_evidence),
    )
