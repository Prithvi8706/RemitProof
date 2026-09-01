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
)
from app.services.alternative_finder import find_valid_alternatives
from app.services.baseline_matcher import baseline_match
from app.services.candidate_retriever import retrieve_candidates
from app.services.pipeline import process_payment
from app.services.proof_engine import verify_candidate
from app.utils.loaders import Dataset


TODAY = date(2026, 8, 31)


def _customer(*, known_payers=None) -> Customer:
    return Customer(
        customer_id="CUS_HARD",
        legal_name="Acme Corp",
        aliases=["Acme Corporation"],
        known_payers=known_payers if known_payers is not None else ["Treasury Bank"],
    )


def _payment(payment_id="PAY_HARD", **updates) -> Payment:
    values = {
        "payment_id": payment_id,
        "date": TODAY,
        "amount": "100.00",
        "currency": "USD",
        "payer_name": "Treasury Bank",
        "bank_reference": f"BANK-{payment_id}",
        "remittance_reference": "",
        "status": "unmatched",
    }
    values.update(updates)
    return Payment(**values)


def _invoice(invoice_id, amount="100.00", **updates) -> Invoice:
    values = {
        "invoice_id": invoice_id,
        "customer_id": "CUS_HARD",
        "amount": amount,
        "currency": "USD",
        "issue_date": date(2026, 8, 1),
        "due_date": TODAY,
        "description": f"Invoice {invoice_id}",
        "status": "open",
    }
    values.update(updates)
    return Invoice(**values)


def _email(email_id="EMAIL_HARD", **updates) -> RemittanceEmail:
    values = {
        "email_id": email_id,
        "sender": "ar@acme.example",
        "customer_id": "CUS_HARD",
        "date": TODAY,
        "subject": "Remittance advice",
        "body": "PAY_HARD: Treasury Bank paid on behalf of Acme Corp. Apply INV_100.",
    }
    values.update(updates)
    return RemittanceEmail(**values)


def _dataset(*, payments, invoices, customers=None, credits=None, emails=None) -> Dataset:
    return Dataset(
        payments=payments,
        invoices=invoices,
        customers=customers if customers is not None else [_customer()],
        credits=credits if credits is not None else [],
        emails=emails if emails is not None else [],
    )


class _StaticInvestigator:
    def __init__(self, proposal):
        self.proposal = proposal
        self.calls = 0

    def investigate(self, bundle):
        self.calls += 1
        return self.proposal


def _proposal(*, invoice_ids, credit_ids=None, evidence_ids=None) -> InvestigationProposal:
    return InvestigationProposal(
        payment_id="PAY_HARD",
        proposed_customer="CUS_HARD",
        invoice_ids=invoice_ids,
        credit_ids=credit_ids or [],
        evidence_ids=evidence_ids or ["CUS_HARD", *invoice_ids, *(credit_ids or [])],
    )


def test_five_invoice_alternative_prevents_false_uniqueness():
    payment = _payment()
    invoices = [_invoice("INV_100")] + [
        _invoice(f"INV_20_{index}", "20.00") for index in range(1, 6)
    ]
    bundle = CandidateBundle(
        payment=payment,
        candidate_customers=[_customer()],
        candidate_invoices=invoices,
    )

    alternatives = find_valid_alternatives(bundle)

    assert {tuple(item.invoice_ids) for item in alternatives} == {
        ("INV_100",),
        tuple(f"INV_20_{index}" for index in range(1, 6)),
    }
    assert baseline_match(bundle).reason == "multiple_financial_allocations"

    investigator = _StaticInvestigator(_proposal(invoice_ids=["INV_100"]))
    result = process_payment(
        "PAY_HARD",
        _dataset(payments=[payment], invoices=invoices),
        investigator,
    )

    assert result.decision.decision == "human_review"
    assert result.sufficiency is not None
    assert result.sufficiency.abstention_reason == "multiple_financially_valid_explanations"


def test_unknown_sender_cannot_establish_payer_customer_authorization():
    payment = _payment(payer_name="Attacker Bank")
    invoice = _invoice("INV_100")
    email = _email(
        sender="attacker@evil.example",
        body=(
            "PAY_HARD: Attacker Bank paid on behalf of Acme Corp. "
            "Apply INV_100."
        ),
    )
    dataset = _dataset(
        payments=[payment],
        invoices=[invoice],
        customers=[_customer(known_payers=[])],
        emails=[email],
    )
    proposal = _proposal(
        invoice_ids=["INV_100"],
        evidence_ids=["CUS_HARD", "INV_100", "EMAIL_HARD"],
    )
    bundle = retrieve_candidates(payment, dataset)

    proof = verify_candidate(bundle, proposal)
    result = process_payment("PAY_HARD", dataset, _StaticInvestigator(proposal))

    assert [item.email_id for item in bundle.candidate_emails] == ["EMAIL_HARD"]
    assert proof.entity_support is False
    assert "unsupported_entity_relationship" in proof.reason_codes
    assert result.decision.decision == "human_review"


@pytest.mark.parametrize(
    "sender",
    [
        "attacker@acme.evil.example",
        "attacker@acme-example.evil",
        "attacker@corp.example",
        "not-an-address",
    ],
)
def test_lookalike_sender_domains_cannot_establish_authorization(sender):
    payment = _payment(payer_name="Attacker Bank")
    invoice = _invoice("INV_100")
    email = _email(
        sender=sender,
        body="PAY_HARD: Attacker Bank paid on behalf of Acme Corp. Apply INV_100.",
    )
    bundle = CandidateBundle(
        payment=payment,
        candidate_customers=[_customer(known_payers=[])],
        candidate_invoices=[invoice],
        candidate_emails=[email],
    )

    proof = verify_candidate(
        bundle,
        _proposal(
            invoice_ids=["INV_100"],
            evidence_ids=["CUS_HARD", "INV_100", "EMAIL_HARD"],
        ),
    )

    assert proof.entity_support is False
    assert "unsupported_entity_relationship" in proof.reason_codes


def test_replayed_bank_transaction_ids_are_both_blocked_before_investigation():
    first = _payment("PAY_HARD", bank_reference="BANK-REPLAY")
    second = _payment("PAY_COPY", bank_reference="bank replay")
    dataset = _dataset(payments=[first, second], invoices=[_invoice("INV_100")])
    investigator = _StaticInvestigator(_proposal(invoice_ids=["INV_100"]))

    first_result = process_payment("PAY_HARD", dataset, investigator)
    second_result = process_payment("PAY_COPY", dataset, investigator)

    assert dataset.replayed_payment_ids == {"PAY_HARD", "PAY_COPY"}
    assert first_result.decision.decision == "human_review"
    assert second_result.decision.decision == "human_review"
    assert second_result.baseline.reason == "duplicate_bank_transaction"
    assert second_result.decision.proof["duplicate_risk"] is True
    assert investigator.calls == 0


def test_reused_reference_with_different_transaction_facts_is_not_a_replay():
    first = _payment("PAY_HARD", bank_reference="BANK-SHARED")
    second = _payment(
        "PAY_DISTINCT",
        bank_reference="BANK-SHARED",
        amount="125.00",
    )
    dataset = _dataset(payments=[first, second], invoices=[_invoice("INV_100")])

    assert dataset.replayed_payment_ids == set()


@pytest.mark.parametrize(
    ("location", "negative_text"),
    [
        ("bank_reference", "Treasury Bank is not an authorized payer"),
        ("remittance_reference", "Treasury Bank is not an authorized payer"),
        ("subject", "PAY_HARD: Treasury Bank is not an authorized payer"),
        ("body", "PAY_HARD: Treasury Bank is not an authorized payer for Acme Corp."),
    ],
)
def test_payer_contradictions_in_every_authoritative_text_field_force_review(
    location,
    negative_text,
):
    payment_updates = {location: negative_text} if location in {
        "bank_reference",
        "remittance_reference",
    } else {}
    email_updates = {location: negative_text} if location in {"subject", "body"} else {}
    payment = _payment(**payment_updates)
    invoice = _invoice("INV_100")
    email = _email(**email_updates)
    dataset = _dataset(payments=[payment], invoices=[invoice], emails=[email])
    proposal = _proposal(invoice_ids=["INV_100"])
    bundle = retrieve_candidates(payment, dataset)

    assert baseline_match(bundle).reason == "conflicting_payer_evidence"
    proof = verify_candidate(bundle, proposal)
    assert proof.entity_support is False
    assert "conflicting_payer_evidence" in proof.reason_codes or proof.contradictions
    assert process_payment(
        "PAY_HARD",
        dataset,
        _StaticInvestigator(proposal),
    ).decision.decision == "human_review"


def test_credit_cannot_overapply_its_linked_invoice():
    payment = _payment(amount="90.00")
    invoices = [_invoice("INV_SMALL", "10.00"), _invoice("INV_LARGE", "100.00")]
    credit = Credit(
        credit_id="CR_TOO_LARGE",
        customer_id="CUS_HARD",
        invoice_id="INV_SMALL",
        amount="20.00",
        currency="USD",
        reason="Oversized adjustment",
    )
    bundle = CandidateBundle(
        payment=payment,
        candidate_customers=[_customer()],
        candidate_invoices=invoices,
        candidate_credits=[credit],
    )
    proposal = _proposal(
        invoice_ids=["INV_SMALL", "INV_LARGE"],
        credit_ids=["CR_TOO_LARGE"],
    )

    proof = verify_candidate(bundle, proposal)

    assert find_valid_alternatives(bundle) == []
    assert proof.financial_validity is False
    assert proof.credit_support is False
    assert "credit_exceeds_invoice_balance" in proof.reason_codes


def test_credits_cannot_cumulatively_overapply_their_linked_invoice():
    payment = _payment(amount="98.00")
    invoices = [_invoice("INV_SMALL", "10.00"), _invoice("INV_LARGE", "100.00")]
    credits = [
        Credit(
            credit_id=f"CR_{index}",
            customer_id="CUS_HARD",
            invoice_id="INV_SMALL",
            amount="6.00",
            currency="USD",
            reason="Cumulative adjustment",
        )
        for index in (1, 2)
    ]
    bundle = CandidateBundle(
        payment=payment,
        candidate_customers=[_customer()],
        candidate_invoices=invoices,
        candidate_credits=credits,
    )
    proposal = _proposal(
        invoice_ids=["INV_SMALL", "INV_LARGE"],
        credit_ids=["CR_1", "CR_2"],
    )

    proof = verify_candidate(bundle, proposal)

    assert all(
        set(alternative.credit_ids) != {"CR_1", "CR_2"}
        for alternative in find_valid_alternatives(bundle)
    )
    assert proof.financial_validity is False
    assert proof.credit_support is False
    assert "credit_exceeds_invoice_balance" in proof.reason_codes


def test_fifth_relevant_email_contradiction_is_not_truncated():
    payment = _payment()
    invoice = _invoice("INV_100")
    supportive = [
        _email(
            f"EMAIL_0{index}",
            body=f"PAY_HARD: Apply INV_100 for Acme Corp. Message {index}.",
        )
        for index in range(1, 5)
    ]
    contradiction = _email(
        "EMAIL_05",
        body="PAY_HARD: Treasury Bank is not an authorized payer for Acme Corp.",
    )
    dataset = _dataset(
        payments=[payment],
        invoices=[invoice],
        emails=[*supportive, contradiction],
    )

    bundle = retrieve_candidates(payment, dataset)

    assert len(bundle.candidate_emails) == 4
    assert "EMAIL_05" in {email.email_id for email in bundle.candidate_emails}
    assert baseline_match(bundle).reason == "conflicting_payer_evidence"
    assert process_payment(
        "PAY_HARD",
        dataset,
        _StaticInvestigator(_proposal(invoice_ids=["INV_100"])),
    ).decision.decision == "human_review"


@pytest.mark.parametrize("currency", ["", "US", "US1", "US D", "€UR"])
@pytest.mark.parametrize("model", [Payment, Invoice])
def test_payment_and_invoice_reject_malformed_currency(model, currency):
    values = (
        _payment().model_dump()
        if model is Payment
        else _invoice("INV_100").model_dump()
    )
    values["currency"] = currency

    with pytest.raises(ValidationError, match="three-letter ISO-style code"):
        model(**values)


def test_payment_and_invoice_normalize_supported_currency_case():
    assert _payment(currency="usd").currency == "USD"
    assert _invoice("INV_100", currency="eur").currency == "EUR"
