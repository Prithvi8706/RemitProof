import csv
import json
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import (
    CandidateBundle,
    Credit,
    Customer,
    InvestigationProposal,
    Invoice,
    Payment,
    RemittanceEmail,
    SemanticClaim,
)
from app.services.alternative_finder import find_valid_alternatives
from app.services.baseline_matcher import baseline_match
from app.services.candidate_retriever import retrieve_candidates
from app.utils.loaders import Dataset, load_dataset


def _payment(**updates):
    values = {
        "payment_id": "PAY_CURRENT",
        "date": date(2026, 8, 31),
        "amount": Decimal("100.00"),
        "currency": "USD",
        "payer_name": "Trusted Treasury Bank",
        "bank_reference": "BANK-CURRENT",
        "remittance_reference": "",
        "status": "unmatched",
    }
    values.update(updates)
    return Payment(**values)


def _customer(**updates):
    values = {
        "customer_id": "CUS_ACME",
        "legal_name": "Acme Corporation",
        "aliases": ["Acme Corp"],
        "known_payers": ["Trusted Treasury Bank"],
    }
    values.update(updates)
    return Customer(**values)


def _invoice(**updates):
    values = {
        "invoice_id": "INV_CURRENT",
        "customer_id": "CUS_ACME",
        "amount": Decimal("100.00"),
        "currency": "USD",
        "issue_date": date(2026, 8, 1),
        "due_date": date(2026, 8, 31),
        "description": "Consulting",
        "status": "open",
    }
    values.update(updates)
    return Invoice(**values)


def _email(**updates):
    values = {
        "email_id": "EMAIL_CURRENT",
        "sender": "ap@acme.example",
        "customer_id": "CUS_ACME",
        "date": date(2026, 8, 30),
        "subject": "Remittance advice",
        "body": "Acme Corporation: Trusted Treasury Bank paid USD 100.00 for INV_CURRENT.",
    }
    values.update(updates)
    return RemittanceEmail(**values)


def _dataset(**updates):
    values = {
        "payments": [_payment()],
        "customers": [_customer()],
        "invoices": [_invoice()],
        "credits": [],
        "emails": [],
    }
    values.update(updates)
    return Dataset(**values)


def _write_dataset(tmp_path, *, payments=None, invoices=None, customers=None, credits=None, emails=None):
    payment_rows = payments or [
        {
            "payment_id": "PAY_CURRENT",
            "date": "2026-08-31",
            "amount": "100.00",
            "currency": "USD",
            "payer_name": "Trusted Treasury Bank",
            "bank_reference": "BANK-CURRENT",
            "remittance_reference": "",
            "status": "unmatched",
            "allocated_customer_id": "",
        }
    ]
    invoice_rows = invoices or [
        {
            "invoice_id": "INV_CURRENT",
            "customer_id": "CUS_ACME",
            "amount": "100.00",
            "currency": "USD",
            "issue_date": "2026-08-01",
            "due_date": "2026-08-31",
            "description": "Consulting",
            "status": "open",
            "allocated_payment_id": "",
        }
    ]
    customer_rows = customers or [
        {
            "customer_id": "CUS_ACME",
            "legal_name": "Acme Corporation",
            "aliases": ["Acme Corp"],
            "parent_entities": [],
            "subsidiaries": [],
            "known_payers": ["Trusted Treasury Bank"],
        }
    ]
    credit_rows = credits or []
    email_rows = emails or []

    for filename, rows in (("payments.csv", payment_rows), ("invoices.csv", invoice_rows)):
        with (tmp_path / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    credit_fields = [
        "credit_id",
        "customer_id",
        "invoice_id",
        "amount",
        "currency",
        "reason",
        "status",
        "consumed_by_payment_id",
    ]
    with (tmp_path / "credits.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=credit_fields)
        writer.writeheader()
        writer.writerows(credit_rows)

    (tmp_path / "customers.json").write_text(json.dumps(customer_rows), encoding="utf-8")
    (tmp_path / "emails.jsonl").write_text(
        "".join(f"{json.dumps(row)}\n" for row in email_rows),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("record_type", "override", "message"),
    [
        ("payments", [{"payment_id": "PAY_CURRENT"}], "duplicate payment"),
        ("invoices", [{"invoice_id": "INV_CURRENT"}], "duplicate invoice"),
        ("customers", [{"customer_id": "CUS_ACME"}], "duplicate customer"),
        ("credits", [{"credit_id": "CR_CURRENT"}], "duplicate credit"),
        ("emails", [{"email_id": "EMAIL_CURRENT"}], "duplicate email"),
    ],
)
def test_loader_rejects_duplicate_source_identifiers(tmp_path, record_type, override, message):
    payment = {
        "payment_id": "PAY_CURRENT", "date": "2026-08-31", "amount": "100.00",
        "currency": "USD", "payer_name": "Trusted Treasury Bank", "bank_reference": "BANK",
        "remittance_reference": "", "status": "unmatched", "allocated_customer_id": "",
    }
    invoice = {
        "invoice_id": "INV_CURRENT", "customer_id": "CUS_ACME", "amount": "100.00",
        "currency": "USD", "issue_date": "2026-08-01", "due_date": "2026-08-31",
        "description": "Consulting", "status": "open", "allocated_payment_id": "",
    }
    customer = {
        "customer_id": "CUS_ACME", "legal_name": "Acme Corporation", "aliases": [],
        "parent_entities": [], "subsidiaries": [], "known_payers": [],
    }
    credit = {
        "credit_id": "CR_CURRENT", "customer_id": "CUS_ACME", "invoice_id": "INV_CURRENT",
        "amount": "10.00", "currency": "USD", "reason": "Adjustment", "status": "valid",
        "consumed_by_payment_id": "",
    }
    email = {
        "email_id": "EMAIL_CURRENT", "sender": "ap@acme.example", "customer_id": "CUS_ACME",
        "date": "2026-08-30", "subject": "Advice", "body": "Apply INV_CURRENT",
    }
    rows = {
        "payments": [payment], "invoices": [invoice], "customers": [customer],
        "credits": [credit], "emails": [email],
    }
    rows[record_type] = rows[record_type] + [{**rows[record_type][0], **override[0]}]
    _write_dataset(tmp_path, **rows)

    with pytest.raises(ValueError, match=message):
        load_dataset(tmp_path)


def test_loader_accepts_historical_allocation_ids_outside_extract(tmp_path):
    invoices = [{
        "invoice_id": "INV_CURRENT", "customer_id": "CUS_ACME", "amount": "100.00",
        "currency": "USD", "issue_date": "2026-08-01", "due_date": "2026-08-31",
        "description": "Consulting", "status": "paid", "allocated_payment_id": "PAY_PREVIOUS",
    }]
    credits = [{
        "credit_id": "CR_CURRENT", "customer_id": "CUS_ACME", "invoice_id": "INV_CURRENT",
        "amount": "10.00", "currency": "USD", "reason": "Adjustment", "status": "consumed",
        "consumed_by_payment_id": "PAY_PREVIOUS",
    }]
    _write_dataset(tmp_path, invoices=invoices, credits=credits)

    dataset = load_dataset(tmp_path)

    assert dataset.invoices[0].allocated_payment_id == "PAY_PREVIOUS"
    assert dataset.credits[0].consumed_by_payment_id == "PAY_PREVIOUS"


@pytest.mark.parametrize(
    ("invoices", "credits", "message"),
    [
        ([_invoice(customer_id="CUS_UNKNOWN")], [], "invoice INV_CURRENT references unknown customer"),
        ([_invoice()], [Credit(credit_id="CR_CURRENT", customer_id="CUS_UNKNOWN", invoice_id="INV_CURRENT", amount="10.00", currency="USD", reason="Adjustment")], "credit CR_CURRENT references unknown customer"),
        ([_invoice()], [Credit(credit_id="CR_CURRENT", customer_id="CUS_ACME", invoice_id="INV_UNKNOWN", amount="10.00", currency="USD", reason="Adjustment")], "credit CR_CURRENT references unknown invoice"),
        ([_invoice()], [Credit(credit_id="CR_CURRENT", customer_id="CUS_OTHER", invoice_id="INV_CURRENT", amount="10.00", currency="USD", reason="Adjustment")], "credit CR_CURRENT customer CUS_OTHER does not match"),
    ],
)
def test_relationship_validation_rejects_broken_invoice_and_credit_links(invoices, credits, message):
    customers = [_customer(), _customer(customer_id="CUS_OTHER", legal_name="Other Corp")]
    dataset = _dataset(invoices=invoices, credits=credits, customers=customers)

    from app.utils.loaders import _validate_relationships

    with pytest.raises(ValueError, match=message):
        _validate_relationships(dataset)


def test_candidate_bundle_rejects_duplicate_candidate_ids():
    with pytest.raises(ValidationError, match="candidate invoice identifiers must be unique"):
        CandidateBundle(
            payment=_payment(),
            candidate_customers=[_customer()],
            candidate_invoices=[_invoice(), _invoice(amount="200.00")],
        )


@pytest.mark.parametrize(
    "proposal",
    [
        {"invoice_ids": ["INV_CURRENT", "INV_CURRENT"]},
        {"credit_ids": ["CR_CURRENT", "CR_CURRENT"]},
        {"evidence_ids": ["EMAIL_CURRENT", "EMAIL_CURRENT"]},
        {"semantic_claims": [
            SemanticClaim(claim_id="CLAIM_1", claim="One", evidence_ids=[]),
            SemanticClaim(claim_id="CLAIM_1", claim="Two", evidence_ids=[]),
        ]},
    ],
)
def test_proposal_rejects_duplicate_identifiers(proposal):
    with pytest.raises(ValidationError, match="unique"):
        InvestigationProposal(payment_id="PAY_CURRENT", **proposal)


def test_semantic_claim_rejects_duplicate_evidence_ids():
    with pytest.raises(ValidationError, match="evidence identifiers must be unique"):
        SemanticClaim(
            claim_id="CLAIM_1",
            claim="Supported claim",
            evidence_ids=["EMAIL_CURRENT", "EMAIL_CURRENT"],
        )


def test_future_issued_invoice_is_not_an_alternative_or_auto_match():
    payment = _payment(remittance_reference="INV_FUTURE")
    future_invoice = _invoice(
        invoice_id="INV_FUTURE",
        issue_date=date(2026, 9, 1),
        due_date=date(2026, 9, 30),
    )
    bundle = CandidateBundle(
        payment=payment,
        candidate_customers=[_customer()],
        candidate_invoices=[future_invoice],
    )

    assert find_valid_alternatives(bundle) == []
    result = baseline_match(bundle)
    assert result.status == "unresolved"
    assert result.matched_invoices == []


def test_same_day_invoice_remains_eligible_for_auto_match():
    payment = _payment(remittance_reference="INV_CURRENT")
    invoice = _invoice(issue_date=payment.date)
    bundle = CandidateBundle(
        payment=payment,
        candidate_customers=[_customer()],
        candidate_invoices=[invoice],
    )

    assert [item.invoice_ids for item in find_valid_alternatives(bundle)] == [["INV_CURRENT"]]
    assert baseline_match(bundle).status == "matched"


def test_strong_detached_remittance_email_is_retrieved_without_direct_reference():
    payment = _payment()
    email = _email()
    assert payment.payment_id not in email.body
    assert payment.bank_reference not in email.body

    bundle = retrieve_candidates(payment, _dataset(emails=[email]))

    assert [item.email_id for item in bundle.candidate_emails] == ["EMAIL_CURRENT"]


def test_detached_email_requires_customer_identity_separate_from_payer():
    email = _email(
        body="Trusted Treasury Bank paid USD 100.00 for INV_CURRENT.",
    )

    bundle = retrieve_candidates(_payment(), _dataset(emails=[email]))

    assert bundle.candidate_emails == []


def test_weak_amount_and_date_only_email_is_not_retrieved():
    weak_email = _email(
        email_id="EMAIL_WEAK",
        customer_id="CUS_OTHER",
        subject="Transfer received",
        body="USD 100.00 received.",
    )
    dataset = _dataset(
        customers=[_customer(), _customer(customer_id="CUS_OTHER", legal_name="Other Corp", aliases=[], known_payers=[])],
        emails=[weak_email],
    )

    bundle = retrieve_candidates(_payment(), dataset)

    assert bundle.candidate_emails == []
