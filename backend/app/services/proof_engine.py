from decimal import Decimal, DecimalException
from typing import List, Optional, Set

from app.models import CandidateBundle, Customer, InvestigationProposal, ProofResult, RemittanceEmail
from app.models.payment import is_valid_monetary_amount
from app.utils.money import money_sum
from app.utils.normalization import extract_document_ids, normalize_name
from app.utils.remittance_semantics import (
    affirmatively_supports_payer_relationship,
    classify_document_semantics,
    explicitly_negates_payer_relationship,
    payer_identity_phrases,
    sender_is_trusted_for_relationship,
    superseded_allocation_email_ids,
    trusted_remittance_sender_ids,
)


def _explicitly_negates_payer_relationship(
    customer: Customer,
    payer_name: str,
    emails: List[RemittanceEmail],
) -> bool:
    for email in emails:
        if email.customer_id != customer.customer_id:
            continue
        if explicitly_negates_payer_relationship(
            f"{email.subject} {email.body}",
            payer_name,
        ):
            return True
    return False


def _safe_decimal(value: object) -> Decimal:
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (DecimalException, TypeError, ValueError):
        return Decimal("0.00")
    return amount if amount.is_finite() else Decimal("0.00")


def _explicit_entity_support(
    customer: Customer,
    payer_name: str,
    emails: List[RemittanceEmail],
    negative_emails: Optional[List[RemittanceEmail]] = None,
    payment_texts: Optional[List[str]] = None,
) -> bool:
    if any(
        explicitly_negates_payer_relationship(text, payer_name)
        for text in (payment_texts or [])
        if text
    ):
        return False
    if _explicitly_negates_payer_relationship(
        customer,
        payer_name,
        emails if negative_emails is None else negative_emails,
    ):
        return False

    supported_names = [
        customer.legal_name,
        *customer.aliases,
        *customer.parent_entities,
        *customer.subsidiaries,
        *customer.known_payers,
    ]
    supported_normalized = {normalize_name(value) for value in supported_names}
    if any(
        normalize_name(payer_phrase) in supported_normalized
        for payer_phrase in payer_identity_phrases(payer_name)
    ):
        return True

    for email in emails:
        if email.customer_id != customer.customer_id:
            continue
        if not sender_is_trusted_for_relationship(
            email.sender,
            payer_name,
            [
                customer.legal_name,
                *customer.aliases,
                *customer.parent_entities,
                *customer.subsidiaries,
            ],
        ):
            continue
        if affirmatively_supports_payer_relationship(
            f"{email.subject} {email.body}",
            payer_name,
            customer.legal_name,
        ):
            return True
    return False


def verify_candidate(
    bundle: CandidateBundle,
    proposal: InvestigationProposal,
) -> ProofResult:
    payment = bundle.payment
    invoices_by_id = {invoice.invoice_id: invoice for invoice in bundle.candidate_invoices}
    credits_by_id = {credit.credit_id: credit for credit in bundle.candidate_credits}
    customers_by_id = {customer.customer_id: customer for customer in bundle.candidate_customers}

    selected_invoices = [invoices_by_id[invoice_id] for invoice_id in proposal.invoice_ids if invoice_id in invoices_by_id]
    selected_credits = [credits_by_id[credit_id] for credit_id in proposal.credit_ids if credit_id in credits_by_id]
    reason_codes = []
    missing_evidence = []
    contradictions = []

    payment_identity_valid = proposal.payment_id == payment.payment_id
    if not payment_identity_valid:
        reason_codes.append("payment_id_mismatch")
        missing_evidence.append("payment_identity")

    payment_text = f"{payment.bank_reference} {payment.remittance_reference}"
    payment_relationship_contradiction = explicitly_negates_payer_relationship(
        payment_text,
        payment.payer_name,
    )
    if payment_relationship_contradiction:
        reason_codes.append("conflicting_payer_evidence")
        missing_evidence.append("entity_relationship")
        contradictions.append("payment fields explicitly deny the payer relationship")
    payment_semantics = classify_document_semantics(
        payment_text,
        bare_references_are_affirmative=True,
    )
    payment_invoice_references = payment_semantics.affirmative_invoice_ids
    payment_credit_references = payment_semantics.affirmative_credit_ids
    proposal_invoice_ids = set(proposal.invoice_ids)
    proposal_credit_ids = set(proposal.credit_ids)
    payment_invoice_reference_consistent = (
        not payment_invoice_references
        or proposal_invoice_ids == payment_invoice_references
    )
    payment_credit_reference_consistent = (
        not payment_credit_references
        or proposal_credit_ids == payment_credit_references
    )
    payment_references_consistent = (
        payment_invoice_reference_consistent and payment_credit_reference_consistent
    )
    negated_payment_references = (
        payment_semantics.prohibited_invoice_ids
        | payment_semantics.prohibited_credit_ids
        | payment_semantics.noncurrent_invoice_ids
    )
    negated_payment_credit_amounts = payment_semantics.prohibited_credit_amounts
    if negated_payment_references or negated_payment_credit_amounts:
        payment_references_consistent = False
        reason_codes.append("negated_payment_reference")
        missing_evidence.append("affirmative_payment_reference")
        detail = sorted(negated_payment_references)
        amount_detail = sorted(str(value) for value in negated_payment_credit_amounts)
        contradictions.append(
            "payment remittance prohibits or negates "
            f"records {detail} and credit amounts {amount_detail}"
        )
    if not payment_invoice_reference_consistent:
        reason_codes.append("payment_invoice_reference_mismatch")
        missing_evidence.append("payment_invoice_reference")
        contradictions.append(
            f"payment references invoices {sorted(payment_invoice_references)} "
            f"but proposal uses {sorted(proposal_invoice_ids)}"
        )
    if not payment_credit_reference_consistent:
        reason_codes.append("payment_credit_reference_mismatch")
        missing_evidence.append("payment_credit_reference")
        contradictions.append(
            f"payment references credits {sorted(payment_credit_references)} "
            f"but proposal uses {sorted(proposal_credit_ids)}"
        )

    unknown_invoices = sorted(set(proposal.invoice_ids) - set(invoices_by_id))
    unknown_credits = sorted(set(proposal.credit_ids) - set(credits_by_id))
    if unknown_invoices:
        reason_codes.append("unknown_invoice")
        missing_evidence.extend(unknown_invoices)
    if unknown_credits:
        reason_codes.append("missing_credit_note")
        missing_evidence.extend(unknown_credits)

    payment_amount_valid = is_valid_monetary_amount(payment.amount)
    invalid_invoice_ids = sorted(
        invoice.invoice_id
        for invoice in selected_invoices
        if not is_valid_monetary_amount(invoice.amount)
    )
    invalid_credit_ids = sorted(
        credit.credit_id
        for credit in selected_credits
        if not is_valid_monetary_amount(credit.amount)
    )
    if not payment_amount_valid:
        reason_codes.append("invalid_payment_amount")
    if invalid_invoice_ids:
        reason_codes.append("invalid_invoice_amount")
        missing_evidence.extend(invalid_invoice_ids)
    if invalid_credit_ids:
        reason_codes.append("invalid_credit_amount")
        missing_evidence.extend(invalid_credit_ids)

    selected_invoice_amounts = {
        invoice.invoice_id: invoice.amount
        for invoice in selected_invoices
        if is_valid_monetary_amount(invoice.amount)
    }
    overapplied_invoice_ids = sorted(
        invoice_id
        for invoice_id, invoice_amount in selected_invoice_amounts.items()
        if money_sum(
            credit.amount
            for credit in selected_credits
            if credit.invoice_id == invoice_id and is_valid_monetary_amount(credit.amount)
        )
        > invoice_amount
    )
    credits_within_invoice_balance = not overapplied_invoice_ids
    if overapplied_invoice_ids:
        reason_codes.append("credit_exceeds_invoice_balance")
        missing_evidence.append("valid_credit_application")
        contradictions.append(
            "selected credits exceed the linked invoice amount for "
            f"{overapplied_invoice_ids}"
        )

    invoice_total = money_sum(
        invoice.amount for invoice in selected_invoices if is_valid_monetary_amount(invoice.amount)
    )
    credit_total = money_sum(
        credit.amount
        for credit in selected_credits
        if credit.status == "valid" and is_valid_monetary_amount(credit.amount)
    )
    calculated_total = invoice_total - credit_total
    financial_validity = (
        payment_identity_valid
        and payment_references_consistent
        and payment_amount_valid
        and bool(selected_invoices)
        and not unknown_invoices
        and not unknown_credits
        and not invalid_invoice_ids
        and not invalid_credit_ids
        and credits_within_invoice_balance
        and calculated_total == payment.amount
    )
    if not financial_validity:
        reason_codes.append("financial_mismatch")

    invoice_states_valid = all(invoice.status == "open" for invoice in selected_invoices)
    credit_states_valid = all(credit.status == "valid" for credit in selected_credits)
    payment_already_allocated = payment.allocated_customer_id is not None
    payment_state_valid = payment.status == "unmatched" and not payment_already_allocated
    state_validity = invoice_states_valid and credit_states_valid and payment_state_valid
    if not invoice_states_valid:
        reason_codes.append("invoice_not_open")
    if not credit_states_valid:
        reason_codes.append("credit_not_valid")
    if payment.status != "unmatched":
        reason_codes.append("payment_not_unmatched")
    if payment_already_allocated:
        reason_codes.append("payment_already_allocated")

    all_currencies = [invoice.currency for invoice in selected_invoices]
    all_currencies.extend(credit.currency for credit in selected_credits)
    currency_validity = all(currency == payment.currency for currency in all_currencies)
    if not currency_validity:
        reason_codes.append("unsupported_currency_mismatch")

    duplicate_risk = (
        payment_already_allocated
        or payment.status != "unmatched"
        or any(invoice.allocated_payment_id is not None for invoice in selected_invoices)
        or any(credit.consumed_by_payment_id is not None for credit in selected_credits)
    )
    if duplicate_risk:
        reason_codes.append("duplicate_allocation_risk")

    proposed_customer: Optional[Customer] = customers_by_id.get(proposal.proposed_customer or "")
    invoice_customers = {invoice.customer_id for invoice in selected_invoices}
    customer_consistent = (
        proposed_customer is not None
        and invoice_customers == {proposed_customer.customer_id}
        and all(credit.customer_id == proposed_customer.customer_id for credit in selected_credits)
        and all(credit.invoice_id in set(proposal.invoice_ids) for credit in selected_credits)
    )
    contradictory_relationship_emails = [
        email.email_id
        for email in bundle.candidate_emails
        if proposed_customer
        and email.customer_id == proposed_customer.customer_id
        and explicitly_negates_payer_relationship(
            f"{email.subject} {email.body}",
            payment.payer_name,
        )
    ]
    if contradictory_relationship_emails:
        reason_codes.append("conflicting_payer_evidence")
        missing_evidence.append("entity_relationship")
        contradictions.append(
            "candidate emails explicitly deny the payer relationship: "
            f"{sorted(contradictory_relationship_emails)}"
        )
    cited_evidence_ids = set(proposal.evidence_ids)
    cited_emails = [
        email for email in bundle.candidate_emails if email.email_id in cited_evidence_ids
    ]
    entity_support = bool(
        customer_consistent
        and proposed_customer
        and _explicit_entity_support(
            proposed_customer,
            payment.payer_name,
            cited_emails,
            negative_emails=bundle.candidate_emails,
            payment_texts=[payment.bank_reference, payment.remittance_reference],
        )
    )
    if not entity_support:
        reason_codes.append("unsupported_entity_relationship")
        missing_evidence.append("entity_relationship")

    valid_credit_ids = {credit.credit_id for credit in selected_credits if credit.status == "valid"}
    credit_support = payment_credit_reference_consistent and credits_within_invoice_balance and (
        not proposal.credit_ids
        or (
            len(valid_credit_ids) == len(proposal.credit_ids)
            and all(credit.invoice_id in proposal.invoice_ids for credit in selected_credits)
        )
    )
    if not credit_support:
        reason_codes.append("unsupported_credit")

    selected_credit_amounts = {credit.amount for credit in selected_credits}
    affirmative_credit_references = set()
    affirmative_credit_amounts = set()
    superseded_email_ids = superseded_allocation_email_ids(
        bundle.candidate_emails,
        payment=bundle.payment,
        trusted_sender_ids=trusted_remittance_sender_ids(
            bundle.candidate_emails,
            bundle.payment,
            bundle.candidate_customers,
            customer_id=proposed_customer.customer_id if proposed_customer else None,
        ),
    )
    for email in bundle.candidate_emails:
        if proposed_customer and email.customer_id != proposed_customer.customer_id:
            continue
        email_text = f"{email.subject} {email.body}"
        semantics = classify_document_semantics(email_text)
        # A dated, explicit, payment-linked correction from a trusted source
        # supersedes an older affirmative instruction. Its prohibitions remain
        # active safety input; only its positive allocation claim loses authority.
        superseded = email.email_id in superseded_email_ids
        mentioned_invoice_ids = set() if superseded else semantics.affirmative_invoice_ids
        mentioned_credit_ids = set() if superseded else semantics.affirmative_credit_ids
        mentioned_amounts = set() if superseded else semantics.affirmative_credit_amounts
        affirmative_credit_references.update(mentioned_credit_ids)
        affirmative_credit_amounts.update(mentioned_amounts)
        prohibited_invoice_ids = (
            semantics.prohibited_invoice_ids | semantics.noncurrent_invoice_ids
        ).intersection(proposal_invoice_ids)
        prohibited_credit_ids = semantics.prohibited_credit_ids.intersection(proposal_credit_ids)
        if prohibited_invoice_ids:
            reason_codes.append("prohibited_invoice_reference")
            missing_evidence.append("prohibited_invoice_reference")
            contradictions.append(
                f"{email.email_id} prohibits invoices {sorted(prohibited_invoice_ids)} "
                f"but proposal uses them"
            )
        if prohibited_credit_ids:
            reason_codes.append("prohibited_credit_reference")
            missing_evidence.append("prohibited_credit_reference")
            contradictions.append(
                f"{email.email_id} prohibits credits {sorted(prohibited_credit_ids)} "
                f"but proposal uses them"
            )
        if semantics.prohibited_credit_amounts.intersection(selected_credit_amounts):
            credit_support = False
            reason_codes.append("prohibited_credit_amount")
            missing_evidence.append("affirmative_credit_instruction")
            contradictions.append(
                f"{email.email_id} prohibits selected credit amount"
            )
        if mentioned_invoice_ids and mentioned_invoice_ids != proposal_invoice_ids:
            reason_codes.append("email_invoice_reference_mismatch")
            missing_evidence.append("invoice_reference")
            contradictions.append(
                f"{email.email_id} names invoices {sorted(mentioned_invoice_ids)} "
                f"but proposal uses {sorted(proposal_invoice_ids)}"
            )
        if mentioned_credit_ids and proposal_credit_ids != mentioned_credit_ids:
            credit_support = False
            reason_codes.append("email_credit_reference_mismatch")
            missing_evidence.append("credit_reference")
            contradictions.append(
                f"{email.email_id} names {sorted(mentioned_credit_ids)} but proposal uses {sorted(proposal.credit_ids)}"
            )
        if mentioned_amounts and selected_credit_amounts and mentioned_amounts.isdisjoint(selected_credit_amounts):
            contradictions.append(
                f"{email.email_id} states credit amount {sorted(str(value) for value in mentioned_amounts)} "
                f"but credit note amount is {sorted(str(value) for value in selected_credit_amounts)}"
            )

    # Every explicitly instructed credit must be selected. Comparing the
    # aggregate set prevents a proposal from satisfying one instruction while
    # silently omitting a second credit named in the same or another candidate
    # remittance.
    if affirmative_credit_references and proposal_credit_ids != affirmative_credit_references:
        credit_support = False
        if "email_credit_reference_mismatch" not in reason_codes:
            reason_codes.append("email_credit_reference_mismatch")
        missing_evidence.append("credit_reference")
        contradictions.append(
            f"remittance names credits {sorted(affirmative_credit_references)} "
            f"but proposal uses {sorted(proposal_credit_ids)}"
        )

    # An available remittance that explicitly claims a credit or deduction is
    # authoritative contradiction evidence even when the model omitted it
    # from evidence_ids. Do not authorize the gross allocation while ignoring
    # a candidate instruction that changes the accounting meaning of the
    # payment. Entity support remains intentionally limited to cited emails.
    email_claims_credit = bool(affirmative_credit_references or affirmative_credit_amounts)
    if email_claims_credit and not proposal.credit_ids:
        credit_support = False
        if "missing_credit_note" not in reason_codes:
            reason_codes.append("missing_credit_note")
        missing_evidence.extend(sorted(affirmative_credit_references) or ["valid_credit_note"])

    return ProofResult(
        financial_validity=financial_validity,
        state_validity=state_validity,
        currency_validity=currency_validity,
        entity_support=entity_support,
        credit_support=credit_support,
        duplicate_risk=duplicate_risk,
        contradictions=contradictions,
        missing_required_evidence=sorted(set(missing_evidence)),
        reason_codes=list(dict.fromkeys(reason_codes)),
        invoice_total=invoice_total,
        credit_total=credit_total,
        calculated_total=calculated_total,
        payment_total=_safe_decimal(payment.amount),
    )
