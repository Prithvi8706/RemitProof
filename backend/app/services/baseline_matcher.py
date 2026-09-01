from typing import List, Set

from app.models import BaselineResult, CandidateBundle, Customer, RemittanceEmail
from app.services.alternative_finder import find_valid_alternatives
from app.utils.normalization import normalize_name
from app.utils.remittance_semantics import (
    classify_document_semantics,
    explicitly_negates_payer_relationship,
)


def _payer_matches(customer: Customer, payer_name: str) -> bool:
    payer = normalize_name(payer_name)
    supported_names = [
        customer.legal_name,
        *customer.aliases,
        *customer.parent_entities,
        *customer.subsidiaries,
        *customer.known_payers,
        customer.customer_id,
    ]
    return payer in {normalize_name(value) for value in supported_names}


def _has_negative_payer_relationship(payer_name: str, text: str) -> bool:
    return explicitly_negates_payer_relationship(text, payer_name)


def _candidate_remittance_texts(
    candidate_emails: List[RemittanceEmail],
    recognized_customers: Set[str],
) -> List[str]:
    return [
        f"{email.subject} {email.body}"
        for email in candidate_emails
        if email.customer_id in recognized_customers
    ]


def baseline_match(bundle: CandidateBundle) -> BaselineResult:
    payment = bundle.payment
    if payment.status != "unmatched":
        return BaselineResult(
            payment_id=payment.payment_id,
            status="unresolved",
            reason="payment_not_unmatched",
        )
    if payment.allocated_customer_id is not None:
        return BaselineResult(
            payment_id=payment.payment_id,
            status="unresolved",
            reason="payment_already_allocated",
        )

    recognized_customers: Set[str] = {
        customer.customer_id
        for customer in bundle.candidate_customers
        if _payer_matches(customer, payment.payer_name)
    }
    if not recognized_customers:
        return BaselineResult(
            payment_id=payment.payment_id,
            status="unresolved",
            reason="payer_not_deterministically_mapped",
        )

    payment_semantics = classify_document_semantics(
        " ".join([payment.bank_reference, payment.remittance_reference]),
        bare_references_are_affirmative=True,
    )
    alternatives = [
        alternative
        for alternative in find_valid_alternatives(bundle)
        if alternative.customer_id in recognized_customers
    ]

    explicit_invoice_ids = payment_semantics.affirmative_invoice_ids
    explicit_credit_ids = payment_semantics.affirmative_credit_ids
    remittance_texts = _candidate_remittance_texts(
        bundle.candidate_emails,
        recognized_customers,
    )
    email_semantics = [classify_document_semantics(text) for text in remittance_texts]
    affirmative_email_credit_ids: Set[str] = set()
    for item in email_semantics:
        affirmative_email_credit_ids.update(item.affirmative_credit_ids)
    has_credit_instruction = any(
        item.affirmative_credit_ids or item.affirmative_credit_amounts
        for item in email_semantics
    )
    prohibited_invoice_ids = set(payment_semantics.prohibited_invoice_ids)
    prohibited_invoice_ids.update(payment_semantics.noncurrent_invoice_ids)
    prohibited_credit_ids = set(payment_semantics.prohibited_credit_ids)
    for item in email_semantics:
        prohibited_invoice_ids.update(item.prohibited_invoice_ids)
        prohibited_invoice_ids.update(item.noncurrent_invoice_ids)
        prohibited_credit_ids.update(item.prohibited_credit_ids)
    has_negated_credit_amount = bool(payment_semantics.prohibited_credit_amounts) or any(
        item.prohibited_credit_amounts for item in email_semantics
    )
    if any(
        _has_negative_payer_relationship(payment.payer_name, text)
        for text in remittance_texts
    ):
        return BaselineResult(
            payment_id=payment.payment_id,
            status="unresolved",
            reason="conflicting_payer_evidence",
            candidate_count=len(alternatives),
        )
    if prohibited_invoice_ids or prohibited_credit_ids or has_negated_credit_amount:
        return BaselineResult(
            payment_id=payment.payment_id,
            status="unresolved",
            reason="conflicting_remittance_evidence",
            candidate_count=len(alternatives),
        )

    if explicit_invoice_ids:
        alternatives = [
            alternative
            for alternative in alternatives
            if set(alternative.invoice_ids) == explicit_invoice_ids
        ]

    # If more than one financial explanation exists, the conventional layer
    # cannot silently discard a credit-backed option and choose another. That
    # ambiguity is precisely where RemitProof must begin.
    if len(alternatives) != 1:
        reason = "multiple_financial_allocations" if len(alternatives) > 1 else "no_unique_safe_allocation"
        return BaselineResult(
            payment_id=payment.payment_id,
            status="unresolved",
            reason=reason,
            candidate_count=len(alternatives),
        )

    safe_alternatives = []
    for alternative in alternatives:
        if prohibited_invoice_ids.intersection(alternative.invoice_ids):
            continue
        if prohibited_credit_ids.intersection(alternative.credit_ids):
            continue
        # Applying a credit is safe in the conventional layer only when the
        # remittance fields explicitly identify every credit note.
        if explicit_credit_ids and set(alternative.credit_ids) != explicit_credit_ids:
            continue
        if (
            affirmative_email_credit_ids
            and set(alternative.credit_ids) != affirmative_email_credit_ids
        ):
            continue
        if alternative.credit_ids and set(alternative.credit_ids) != explicit_credit_ids:
            continue
        if not alternative.credit_ids and has_credit_instruction:
            continue
        safe_alternatives.append(alternative)

    if len(safe_alternatives) != 1:
        reason = (
            "conflicting_remittance_credit_reference"
            if explicit_credit_ids
            else "conflicting_remittance_evidence"
            if prohibited_invoice_ids or prohibited_credit_ids
            else "remittance_credit_instruction_requires_review"
            if has_credit_instruction and any(not alternative.credit_ids for alternative in alternatives)
            else "no_unique_safe_allocation"
        )
        return BaselineResult(
            payment_id=payment.payment_id,
            status="unresolved",
            reason=reason,
            candidate_count=len(alternatives),
        )

    match = safe_alternatives[0]
    return BaselineResult(
        payment_id=payment.payment_id,
        status="matched",
        matched_invoices=match.invoice_ids,
        matched_credits=match.credit_ids,
        customer_id=match.customer_id,
        reason="unique_deterministic_allocation",
        candidate_count=len(alternatives),
    )
