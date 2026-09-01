from datetime import date
from decimal import Decimal

import pytest

from app.models import CandidateBundle, Credit, Customer, Invoice, Payment, RemittanceEmail
from app.services.baseline_matcher import baseline_match


def _invoice(invoice_id: str, amount: str = "100.00") -> Invoice:
    return Invoice(
        invoice_id=invoice_id,
        customer_id="CUS_CONFLICT",
        amount=Decimal(amount),
        currency="USD",
        issue_date=date(2026, 8, 1),
        due_date=date(2026, 8, 31),
        description=f"{invoice_id} invoice",
        status="open",
    )


def _credit(credit_id: str, amount: str = "10.00") -> Credit:
    return Credit(
        credit_id=credit_id,
        customer_id="CUS_CONFLICT",
        invoice_id="INV_GOOD",
        amount=Decimal(amount),
        currency="USD",
        reason="Service credit",
        status="valid",
    )


def _bundle(
    email_body: str,
    *,
    payer_name: str = "Acme Corp",
    known_payers=None,
    payment_amount: str = "100.00",
    remittance_reference: str = "INV_GOOD",
    candidate_invoices=None,
    candidate_credits=None,
    allocated_customer_id=None,
) -> CandidateBundle:
    return CandidateBundle(
        payment=Payment(
            payment_id="PAY_CONFLICT",
            date=date(2026, 8, 31),
            amount=Decimal(payment_amount),
            currency="USD",
            payer_name=payer_name,
            bank_reference="WIRE-CONFLICT",
            remittance_reference=remittance_reference,
            status="unmatched",
            allocated_customer_id=allocated_customer_id,
        ),
        candidate_customers=[
            Customer(
                customer_id="CUS_CONFLICT",
                legal_name="Acme Corp",
                known_payers=known_payers or [],
            ),
        ],
        candidate_invoices=candidate_invoices
        if candidate_invoices is not None
        else [_invoice("INV_GOOD"), _invoice("INV_BAD")],
        candidate_credits=candidate_credits or [],
        candidate_emails=[
            RemittanceEmail(
                email_id="EMAIL_CONFLICT",
                sender="ar@acme.example",
                customer_id="CUS_CONFLICT",
                date=date(2026, 8, 30),
                subject="Payment allocation",
                body=email_body,
            ),
        ],
    )


def test_baseline_abstains_when_email_contradicts_invoice_reference():
    result = baseline_match(
        _bundle(
            "Do not apply this payment to INV_GOOD. "
            "Please apply it to INV_BAD instead."
        )
    )

    assert result.status == "unresolved"
    assert result.reason == "conflicting_remittance_evidence"
    assert result.matched_invoices == []


def test_baseline_keeps_exact_reference_match_without_conflicting_email():
    result = baseline_match(_bundle("Please apply this payment to INV_GOOD."))

    assert result.status == "matched"
    assert result.matched_invoices == ["INV_GOOD"]


def test_baseline_rejects_referenced_credit_that_is_not_selected():
    result = baseline_match(
        _bundle(
            "Please apply this payment to INV_GOOD.",
            remittance_reference="CR_BAD",
            candidate_invoices=[_invoice("INV_GOOD")],
        )
    )

    assert result.status == "unresolved"
    assert result.reason == "conflicting_remittance_credit_reference"


def test_baseline_rejects_referenced_credit_when_a_different_credit_is_selected():
    result = baseline_match(
        _bundle(
            "Please apply this payment to INV_GOOD.",
            remittance_reference="CR_BAD",
            candidate_invoices=[_invoice("INV_GOOD", "110.00")],
            candidate_credits=[_credit("CR_GOOD")],
        )
    )

    assert result.status == "unresolved"
    assert result.reason == "conflicting_remittance_credit_reference"


def test_baseline_allows_exactly_referenced_credit():
    result = baseline_match(
        _bundle(
            "Please apply this payment to INV_GOOD.",
            remittance_reference="CR_GOOD",
            candidate_invoices=[_invoice("INV_GOOD", "110.00")],
            candidate_credits=[_credit("CR_GOOD")],
        )
    )

    assert result.status == "matched"
    assert result.matched_invoices == ["INV_GOOD"]
    assert result.matched_credits == ["CR_GOOD"]


def test_baseline_rejects_email_prohibition_of_referenced_credit():
    result = baseline_match(
        _bundle(
            "Do not use CR_GOOD.",
            payment_amount="90.00",
            remittance_reference="CR_GOOD",
            candidate_invoices=[_invoice("INV_GOOD", "100.00")],
            candidate_credits=[_credit("CR_GOOD")],
        )
    )

    assert result.status == "unresolved"
    assert result.reason == "conflicting_remittance_evidence"
    assert result.matched_credits == []


@pytest.mark.parametrize(
    "negative_status",
    ["unauthorized", "unapproved", "prohibited", "forbidden", "disallowed", "ineligible"],
)
def test_baseline_rejects_explicit_negative_payer_evidence_against_known_payer(negative_status):
    result = baseline_match(
        _bundle(
            f"Treasury Bank is a {negative_status} payer for Acme Corp.",
            payer_name="Treasury Bank",
            known_payers=["Treasury Bank"],
            candidate_invoices=[_invoice("INV_GOOD")],
        )
    )

    assert result.status == "unresolved"
    assert result.reason == "conflicting_payer_evidence"


def test_baseline_preserves_positive_known_payer_match():
    result = baseline_match(
        _bundle(
            "Treasury Bank is an authorized payer for Acme Corp.",
            payer_name="Treasury Bank",
            known_payers=["Treasury Bank"],
            candidate_invoices=[_invoice("INV_GOOD")],
        )
    )

    assert result.status == "matched"
    assert result.customer_id == "CUS_CONFLICT"
    assert result.matched_invoices == ["INV_GOOD"]


def test_baseline_rejects_email_prohibition_without_payment_invoice_reference():
    result = baseline_match(
        _bundle(
            "Do not use INV_GOOD.",
            remittance_reference="",
            candidate_invoices=[_invoice("INV_GOOD")],
        )
    )

    assert result.status == "unresolved"
    assert result.reason == "conflicting_remittance_evidence"


def test_baseline_keeps_positive_email_instruction_without_payment_invoice_reference():
    result = baseline_match(
        _bundle(
            "Please apply this payment to INV_GOOD.",
            remittance_reference="",
            candidate_invoices=[_invoice("INV_GOOD")],
        )
    )

    assert result.status == "matched"
    assert result.matched_invoices == ["INV_GOOD"]


def test_baseline_rejects_credit_deduction_against_gross_invoice():
    result = baseline_match(
        _bundle(
            "Please deduct a USD 10 credit from this payment.",
            remittance_reference="",
            candidate_invoices=[_invoice("INV_GOOD")],
        )
    )

    assert result.status == "unresolved"
    assert result.reason == "remittance_credit_instruction_requires_review"


def test_baseline_rejects_unmatched_payment_with_existing_allocation():
    result = baseline_match(
        _bundle(
            "Please apply this payment to INV_GOOD.",
            allocated_customer_id="CUS_CONFLICT",
        )
    )

    assert result.status == "unresolved"
    assert result.reason == "payment_already_allocated"
