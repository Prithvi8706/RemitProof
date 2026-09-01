import re
from collections import defaultdict
from decimal import Decimal
from typing import Dict, Iterable, List, Set, Tuple

from app.models import CandidateBundle, Customer, Invoice, Payment, RemittanceEmail
from app.utils.loaders import Dataset
from app.utils.normalization import extract_document_ids, normalize_name
from app.utils.remittance_semantics import (
    classify_document_semantics,
    explicitly_negates_payer_relationship,
)


def _tokens(value: str) -> Set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) >= 4 and token not in {"limited", "services", "international"}
    }


def _customer_names(customer: Customer) -> Iterable[str]:
    return (
        customer.legal_name,
        *customer.aliases,
        *customer.parent_entities,
        *customer.subsidiaries,
        *customer.known_payers,
        customer.customer_id,
    )


def _customer_identity_names(customer: Customer) -> Iterable[str]:
    return (
        customer.legal_name,
        *customer.aliases,
        *customer.parent_entities,
        *customer.subsidiaries,
        customer.customer_id,
    )


def _contains_normalized_phrase(text: str, value: str) -> bool:
    text_tokens = re.findall(r"[a-z0-9]+", text.casefold())
    value_tokens = re.findall(r"[a-z0-9]+", value.casefold())
    if not value_tokens or len(value_tokens) > len(text_tokens):
        return False
    width = len(value_tokens)
    return any(
        text_tokens[index : index + width] == value_tokens
        for index in range(len(text_tokens) - width + 1)
    )


def _mentions_exact_amount(text: str, amount: Decimal) -> bool:
    amount_text = format(amount, "f")
    compact_text = text.replace(",", "")
    return re.search(rf"(?<![\d.]){re.escape(amount_text)}(?![\d.])", compact_text) is not None


def _email_score(
    payment: Payment,
    email: RemittanceEmail,
    customers_by_id: Dict[str, Customer],
    invoices_by_id: Dict[str, Invoice],
) -> int:
    text = f"{email.subject} {email.body}"
    score = 0
    direct_references = [
        payment.payment_id,
        payment.bank_reference,
        payment.remittance_reference,
    ]
    for reference in direct_references:
        if reference and _contains_normalized_phrase(text, reference):
            score += 120
    has_exact_amount = (
        _contains_normalized_phrase(text, payment.currency)
        and _mentions_exact_amount(text, payment.amount)
    )
    if has_exact_amount:
        score += 30
    days_apart = abs((payment.date - email.date).days)
    if days_apart <= 7:
        score += 15
    elif days_apart <= 45:
        score += 5
    has_exact_payer = _contains_normalized_phrase(text, payment.payer_name)

    customer = customers_by_id.get(email.customer_id)
    referenced_invoice_ids = {
        record_id
        for record_id in extract_document_ids(text)
        if record_id.startswith("INV_")
    }
    aligned_invoices = [
        invoices_by_id[invoice_id]
        for invoice_id in referenced_invoice_ids
        if invoice_id in invoices_by_id
        and invoices_by_id[invoice_id].customer_id == email.customer_id
    ]
    has_exact_customer = customer is not None and any(
        _contains_normalized_phrase(text, name)
        for name in _customer_identity_names(customer)
        if normalize_name(name)
    )
    # A detached remittance may lack the bank/payment ID, but it must then
    # align on every independent business signal. Additive partial matches are
    # deliberately insufficient because common amounts, dates and bank words
    # otherwise pull unrelated correspondence into the candidate set.
    if (
        aligned_invoices
        and has_exact_customer
        and has_exact_payer
        and has_exact_amount
        and days_apart <= 7
    ):
        score += 100
    return score


def _contains_safety_contradiction(payment: Payment, email: RemittanceEmail) -> bool:
    """Return whether relevant correspondence contains fail-closed evidence."""

    text = f"{email.subject} {email.body}"
    if explicitly_negates_payer_relationship(text, payment.payer_name):
        return True
    semantics = classify_document_semantics(text)
    return bool(
        semantics.prohibited_invoice_ids
        or semantics.prohibited_credit_ids
        or semantics.noncurrent_invoice_ids
        or semantics.prohibited_credit_amounts
    )


def _amount_is_close(invoice_amount: Decimal, payment_amount: Decimal) -> bool:
    if invoice_amount == payment_amount:
        return True
    difference = abs(invoice_amount - payment_amount)
    return difference <= max(Decimal("500.00"), payment_amount * Decimal("0.08"))


def retrieve_candidates(payment: Payment, dataset: Dataset) -> CandidateBundle:
    """Deterministically narrow records without embeddings or ground truth."""

    customers_by_id = {customer.customer_id: customer for customer in dataset.customers}
    invoices_by_id = {invoice.invoice_id: invoice for invoice in dataset.invoices}

    scored_emails: List[Tuple[int, RemittanceEmail]] = [
        (
            _email_score(payment, email, customers_by_id, invoices_by_id),
            email,
        )
        for email in dataset.emails
    ]
    # Keep the established bounded payload, but rank fail-closed evidence ahead
    # of supportive correspondence. A fifth equally relevant denial must never
    # disappear merely because four positive messages sort first.
    candidate_emails = [
        email
        for score, email in sorted(
            scored_emails,
            key=lambda item: (
                -int(_contains_safety_contradiction(payment, item[1])),
                -item[0],
                item[1].email_id,
            ),
        )
        if score >= 80
    ][:4]

    evidence_text = " ".join(
        [payment.bank_reference, payment.remittance_reference]
        + [f"{email.subject} {email.body}" for email in candidate_emails]
    )
    evidence_ids = extract_document_ids(evidence_text)
    referenced_invoices = {item for item in evidence_ids if item.startswith("INV_")}

    invoices_by_customer: Dict[str, list] = defaultdict(list)
    for invoice in dataset.invoices:
        invoices_by_customer[invoice.customer_id].append(invoice)

    email_customer_ids = {email.customer_id for email in candidate_emails}
    customer_scores = []
    payer_normalized = normalize_name(payment.payer_name)
    payer_tokens = _tokens(payment.payer_name)
    for customer in dataset.customers:
        score = 0
        supported_names = {normalize_name(value) for value in _customer_names(customer)}
        if payer_normalized in supported_names:
            score += 150
        if customer.customer_id in email_customer_ids:
            score += 130
        customer_invoice_ids = {invoice.invoice_id for invoice in invoices_by_customer[customer.customer_id]}
        if referenced_invoices.intersection(customer_invoice_ids):
            score += 140
        customer_tokens = set().union(*(_tokens(name) for name in _customer_names(customer)))
        score += 12 * len(payer_tokens.intersection(customer_tokens))
        if any(
            invoice.currency == payment.currency
            and invoice.amount == payment.amount
            and abs((payment.date - invoice.due_date).days) <= 180
            for invoice in invoices_by_customer[customer.customer_id]
        ):
            score += 100
        if any(
            invoice.currency == payment.currency
            and _amount_is_close(invoice.amount, payment.amount)
            and abs((payment.date - invoice.due_date).days) <= 180
            for invoice in invoices_by_customer[customer.customer_id]
        ):
            score += 20
        if score:
            customer_scores.append((score, customer))

    candidate_customers = [
        customer
        for _, customer in sorted(
            customer_scores,
            key=lambda item: (-item[0], item[1].customer_id),
        )[:3]
    ]
    candidate_customer_ids = {customer.customer_id for customer in candidate_customers}

    invoice_scores = []
    for invoice in dataset.invoices:
        score = 0
        explicitly_referenced = invoice.invoice_id in referenced_invoices
        if explicitly_referenced:
            score += 300
        if invoice.customer_id in candidate_customer_ids:
            score += 120
        if invoice.currency == payment.currency:
            score += 45
        elif not explicitly_referenced:
            score -= 180
        if invoice.issue_date <= payment.date and abs((payment.date - invoice.due_date).days) <= 180:
            score += 25
        if invoice.amount == payment.amount:
            score += 50
        elif _amount_is_close(invoice.amount, payment.amount):
            score += 20
        if invoice.status == "open":
            score += 10
        if score >= 100:
            invoice_scores.append((score, invoice))

    candidate_invoices = [
        invoice
        for _, invoice in sorted(
            invoice_scores,
            key=lambda item: (-item[0], item[1].invoice_id),
        )[:8]
    ]
    candidate_invoice_ids = {invoice.invoice_id for invoice in candidate_invoices}

    credit_scores = []
    for credit in dataset.credits:
        score = 0
        if credit.credit_id in evidence_ids:
            score += 200
        if credit.invoice_id in candidate_invoice_ids:
            score += 100
        if credit.customer_id in candidate_customer_ids:
            score += 50
        if credit.currency == payment.currency:
            score += 20
        if score >= 100:
            credit_scores.append((score, credit))
    candidate_credits = [
        credit
        for _, credit in sorted(
            credit_scores,
            key=lambda item: (-item[0], item[1].credit_id),
        )[:3]
    ]

    return CandidateBundle(
        payment=payment,
        candidate_customers=candidate_customers,
        candidate_invoices=candidate_invoices,
        candidate_credits=candidate_credits,
        candidate_emails=candidate_emails,
    )
