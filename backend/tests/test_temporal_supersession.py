from datetime import date

import pytest

from app.models import CandidateBundle, Customer, InvestigationProposal, Payment, RemittanceEmail
from app.services.alternative_finder import find_valid_alternatives
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.proof_engine import verify_candidate
from app.utils.remittance_semantics import (
    superseded_allocation_email_ids,
    trusted_remittance_sender_ids,
)


def _bundle(
    *,
    old_email_body: str,
    new_email_body: str,
    bank_reference: str = "",
    remittance_reference: str = "",
    old_sender: str = "treasury@acme.example",
    new_sender: str = "treasury@acme.example",
    candidate_invoices=None,
    candidate_credits=None,
    old_date=date(2026, 1, 5),
    new_date=date(2026, 1, 10),
) -> CandidateBundle:
    return CandidateBundle.model_validate(
        {
            "payment": {
                "payment_id": "PAY_TEST",
                "date": date(2026, 1, 15),
                "amount": "100.00",
                "currency": "USD",
                "payer_name": "Treasury Bank",
                "bank_reference": bank_reference,
                "remittance_reference": remittance_reference,
                "allocated_customer_id": None,
            },
            "candidate_customers": [
                {
                    "customer_id": "CUS_TEST",
                    "legal_name": "Acme Corp",
                    "known_payers": ["Treasury Bank"],
                }
            ],
            "candidate_invoices": candidate_invoices or [
                {
                    "invoice_id": "INV_201",
                    "customer_id": "CUS_TEST",
                    "amount": "100.00",
                    "currency": "USD",
                    "issue_date": date(2025, 12, 1),
                    "due_date": date(2026, 1, 1),
                    "description": "Synthetic invoice",
                },
                {
                    "invoice_id": "INV_202",
                    "customer_id": "CUS_TEST",
                    "amount": "100.00",
                    "currency": "USD",
                    "issue_date": date(2025, 12, 2),
                    "due_date": date(2026, 1, 2),
                    "description": "Synthetic invoice",
                },
            ],
            "candidate_credits": candidate_credits or [],
            "candidate_emails": [
                {
                    "email_id": "EMAIL_OLD",
                    "sender": old_sender,
                    "customer_id": "CUS_TEST",
                    "date": old_date,
                    "subject": "Payment instruction",
                    "body": old_email_body,
                },
                {
                    "email_id": "EMAIL_NEW",
                    "sender": new_sender,
                    "customer_id": "CUS_TEST",
                    "date": new_date,
                    "subject": "Payment instruction update",
                    "body": new_email_body,
                },
            ],
        }
    )


def _proposal(*, invoice_ids, evidence_ids, credit_ids=None) -> InvestigationProposal:
    return InvestigationProposal(
        payment_id="PAY_TEST",
        proposed_customer="CUS_TEST",
        invoice_ids=invoice_ids,
        credit_ids=credit_ids or [],
        evidence_ids=evidence_ids,
    )


def _decide(bundle: CandidateBundle, proposal: InvestigationProposal):
    proof = verify_candidate(bundle, proposal)
    alternatives = find_valid_alternatives(bundle)
    sufficiency = evaluate_evidence_sufficiency(bundle, proposal, proof, alternatives)
    return proof, alternatives, sufficiency


def _superseded(bundle: CandidateBundle, *, authoritative_payments=None):
    return superseded_allocation_email_ids(
        bundle.candidate_emails,
        payment=bundle.payment,
        trusted_sender_ids=trusted_remittance_sender_ids(
            bundle.candidate_emails,
            bundle.payment,
            bundle.candidate_customers,
            customer_id="CUS_TEST",
        ),
        authoritative_payments=authoritative_payments,
    )


def test_abbreviated_synthetic_sender_domain_fails_closed_when_other_brand_owner_is_not_retrieved():
    payment = Payment(
        payment_id="PAY_COLLISION",
        date=date(2026, 1, 15),
        amount="100.00",
        currency="USD",
        payer_name="Treasury Bank",
    )
    customers = [Customer(customer_id="CUS_TECH", legal_name="Acme Technologies Inc")]
    emails = [
        RemittanceEmail(
            email_id="EMAIL_COLLISION",
            sender="finance@acme.example",
            customer_id="CUS_TECH",
            date=date(2026, 1, 10),
            subject="Allocation",
            body="Apply PAY_COLLISION to INV_1.",
        )
    ]

    assert trusted_remittance_sender_ids(
        emails, payment, customers, customer_id="CUS_TECH"
    ) == set()


def test_abbreviated_synthetic_sender_domain_is_rejected_even_when_brand_looks_unique():
    payment = Payment(
        payment_id="PAY_UNIQUE",
        date=date(2026, 1, 15),
        amount="100.00",
        currency="USD",
        payer_name="Treasury Bank",
    )
    customer = Customer(
        customer_id="CUS_ACME", legal_name="Acme Technologies Inc"
    )
    email = RemittanceEmail(
        email_id="EMAIL_UNIQUE",
        sender="finance@acme.example",
        customer_id="CUS_ACME",
        date=date(2026, 1, 10),
        subject="Allocation",
        body="Apply PAY_UNIQUE to INV_1.",
    )

    assert trusted_remittance_sender_ids(
        [email], payment, [customer], customer_id="CUS_ACME"
    ) == set()


def test_complete_synthetic_sender_domain_remains_trusted_during_brand_collision():
    payment = Payment(
        payment_id="PAY_EXACT",
        date=date(2026, 1, 15),
        amount="100.00",
        currency="USD",
        payer_name="Treasury Bank",
    )
    customers = [
        Customer(customer_id="CUS_TECH", legal_name="Acme Technologies Inc"),
        Customer(customer_id="CUS_LOGISTICS", legal_name="Acme Logistics LLC"),
    ]
    email = RemittanceEmail(
        email_id="EMAIL_EXACT",
        sender="finance@acmetechnologies.example",
        customer_id="CUS_TECH",
        date=date(2026, 1, 10),
        subject="Allocation",
        body="Apply PAY_EXACT to INV_1.",
    )

    assert trusted_remittance_sender_ids(
        [email], payment, customers, customer_id="CUS_TECH"
    ) == {"finance@acmetechnologies.example"}


def test_newer_instruction_can_supersede_old_instruction():
    bundle = _bundle(
        old_email_body="For PAY_TEST, please apply the payment to INV_201.",
        new_email_body="Correction for PAY_TEST: please apply the payment to INV_202.",
    )
    proposal = _proposal(
        invoice_ids=["INV_202"],
        evidence_ids=["CUS_TEST", "INV_202", "EMAIL_NEW"],
    )

    proof, alternatives, sufficiency = _decide(bundle, proposal)

    assert _superseded(bundle) == {"EMAIL_OLD"}
    assert proof.contradictions == []
    assert len(alternatives) == 2
    assert sufficiency.evidence_disambiguates_alternatives is True
    assert sufficiency.safe_to_resolve is True


def test_unique_secondary_reference_requires_authoritative_payment_context():
    bundle = _bundle(
        old_email_body="For WIRE_TEST_77, please apply the payment to INV_201.",
        new_email_body="Correction for PAY_TEST: please apply the payment to INV_202.",
        bank_reference="WIRE_TEST_77",
    )
    proposal = _proposal(
        invoice_ids=["INV_202"],
        evidence_ids=["CUS_TEST", "INV_202", "EMAIL_NEW"],
    )

    proof, _, sufficiency = _decide(bundle, proposal)

    assert _superseded(
        bundle, authoritative_payments=[bundle.payment]
    ) == {"EMAIL_OLD"}
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False


def test_shared_secondary_reference_cannot_authorize_temporal_supersession():
    bundle = _bundle(
        old_email_body="For WIRE2026, please apply the payment to INV_201.",
        new_email_body=(
            "Correction for WIRE2026: please apply the payment to INV_202."
        ),
        bank_reference="WIRE2026",
    )
    other_payment = bundle.payment.model_copy(
        update={"payment_id": "PAY_OTHER", "bank_reference": "wire-2026"}
    )

    assert _superseded(
        bundle,
        authoritative_payments=[bundle.payment, other_payment],
    ) == set()


def test_credit_amount_correction_supersedes_older_amount_claim():
    bundle = _bundle(
        old_email_body=(
            "For PAY_TEST, apply the payment to INV_201 after deducting USD 10.00 credit."
        ),
        new_email_body=(
            "Correction for PAY_TEST: apply the payment to INV_201 after deducting USD 20.00 credit."
        ),
    )

    assert _superseded(bundle) == {"EMAIL_OLD"}


def test_credit_only_correction_can_disambiguate_credit_alternatives():
    bundle = _bundle(
        old_email_body="For PAY_TEST, apply credit CR_OLD to the payment.",
        new_email_body="Correction for PAY_TEST: apply credit CR_NEW to the payment.",
        candidate_invoices=[
            {
                "invoice_id": "INV_201",
                "customer_id": "CUS_TEST",
                "amount": "120.00",
                "currency": "USD",
                "issue_date": date(2025, 12, 1),
                "due_date": date(2026, 1, 1),
                "description": "Synthetic invoice",
            }
        ],
        candidate_credits=[
            {
                "credit_id": "CR_OLD",
                "customer_id": "CUS_TEST",
                "invoice_id": "INV_201",
                "amount": "20.00",
                "currency": "USD",
                "reason": "Synthetic credit",
            },
            {
                "credit_id": "CR_NEW",
                "customer_id": "CUS_TEST",
                "invoice_id": "INV_201",
                "amount": "20.00",
                "currency": "USD",
                "reason": "Synthetic correction credit",
            },
        ],
    )
    proposal = _proposal(
        invoice_ids=["INV_201"],
        credit_ids=["CR_NEW"],
        evidence_ids=["CUS_TEST", "INV_201", "CR_NEW", "EMAIL_NEW"],
    )

    proof, alternatives, sufficiency = _decide(bundle, proposal)

    assert _superseded(bundle) == {"EMAIL_OLD"}
    assert len(alternatives) == 2
    assert proof.financial_validity is True
    assert proof.contradictions == []
    assert sufficiency.evidence_disambiguates_alternatives is True
    assert any(
        row.evidence_id == "EMAIL_NEW"
        and row.relationship == "supports"
        and set(alternative.credit_ids) == {"CR_NEW"}
        for alternative in alternatives
        for row in sufficiency.evidence_alternative_matrix
        if row.allocation_id == alternative.allocation_id
    )
    assert sufficiency.safe_to_resolve is True


def test_unrelated_later_correction_cannot_supersede_current_instruction():
    bundle = _bundle(
        old_email_body="For PAY_TEST, please apply the payment to INV_201.",
        new_email_body="Correction for PAY_OTHER: please apply the payment to INV_202.",
    )
    proposal = _proposal(
        invoice_ids=["INV_202"],
        evidence_ids=["CUS_TEST", "INV_202", "EMAIL_NEW"],
    )

    proof, _, sufficiency = _decide(bundle, proposal)

    assert _superseded(bundle) == set()
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False
    assert sufficiency.abstention_reason == "contradictory_evidence"


def test_untrusted_later_correction_cannot_supersede_current_instruction():
    bundle = _bundle(
        old_email_body="For PAY_TEST, please apply the payment to INV_201.",
        new_email_body="Correction for PAY_TEST: please apply the payment to INV_202.",
        new_sender="attacker@evil.example",
    )
    proposal = _proposal(
        invoice_ids=["INV_202"],
        evidence_ids=["CUS_TEST", "INV_202", "EMAIL_NEW"],
    )

    proof, _, sufficiency = _decide(bundle, proposal)

    assert _superseded(bundle) == set()
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False
    assert sufficiency.abstention_reason == "contradictory_evidence"


@pytest.mark.parametrize("generic_reference", ["WIRE", "ACH", "SEPA", "SWIFT", "NEFT", "RTGS"])
def test_generic_bank_reference_cannot_authorize_temporal_supersession(generic_reference):
    bundle = _bundle(
        old_email_body=f"For {generic_reference}, please apply the payment to INV_201.",
        new_email_body=(
            f"Correction for {generic_reference}: please apply the payment to INV_202."
        ),
        bank_reference=generic_reference,
    )
    proposal = _proposal(
        invoice_ids=["INV_202"],
        evidence_ids=["CUS_TEST", "INV_202", "EMAIL_NEW"],
    )

    proof, _, sufficiency = _decide(bundle, proposal)

    assert _superseded(bundle) == set()
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False
    assert sufficiency.abstention_reason == "contradictory_evidence"


def test_conflicting_instructions_without_correction_language_force_review():
    bundle = _bundle(
        old_email_body="For PAY_TEST, please apply the payment to INV_201.",
        new_email_body="For PAY_TEST, please apply the payment to INV_202.",
    )
    proposal = _proposal(
        invoice_ids=["INV_202"],
        evidence_ids=["CUS_TEST", "INV_202", "EMAIL_NEW"],
    )

    proof, _, sufficiency = _decide(bundle, proposal)

    assert _superseded(bundle) == set()
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False
    assert sufficiency.abstention_reason == "contradictory_evidence"


def test_older_correction_cannot_supersede_newer_instruction():
    bundle = _bundle(
        old_email_body="Correction for PAY_TEST: please apply the payment to INV_202.",
        new_email_body="For PAY_TEST, please apply the payment to INV_201.",
    )
    proposal = _proposal(
        invoice_ids=["INV_202"],
        evidence_ids=["CUS_TEST", "INV_202", "EMAIL_OLD"],
    )

    proof, _, sufficiency = _decide(bundle, proposal)

    assert _superseded(bundle) == set()
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False


def test_same_day_correction_does_not_supersede():
    bundle = _bundle(
        old_email_body="For PAY_TEST, please apply the payment to INV_201.",
        new_email_body="Correction for PAY_TEST: please apply the payment to INV_202.",
        old_date=date(2026, 1, 10),
        new_date=date(2026, 1, 10),
    )
    proposal = _proposal(
        invoice_ids=["INV_202"],
        evidence_ids=["CUS_TEST", "INV_202", "EMAIL_NEW"],
    )

    proof, _, sufficiency = _decide(bundle, proposal)

    assert _superseded(bundle) == set()
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False


def test_superseded_email_prohibition_remains_active():
    bundle = _bundle(
        old_email_body="For PAY_TEST, please apply the payment to INV_201. Do not apply INV_202.",
        new_email_body="Correction for PAY_TEST: please apply the payment to INV_202.",
    )
    proposal = _proposal(
        invoice_ids=["INV_202"],
        evidence_ids=["CUS_TEST", "INV_202", "EMAIL_NEW"],
    )

    proof, _, sufficiency = _decide(bundle, proposal)

    assert _superseded(bundle) == {"EMAIL_OLD"}
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False


def test_superseded_cited_email_is_labeled_in_evidence_matrix():
    bundle = _bundle(
        old_email_body="For PAY_TEST, please apply the payment to INV_201.",
        new_email_body="Correction for PAY_TEST: please apply the payment to INV_202.",
    )
    proposal = _proposal(
        invoice_ids=["INV_202"],
        evidence_ids=["CUS_TEST", "INV_202", "EMAIL_NEW", "EMAIL_OLD"],
    )

    proof, alternatives, sufficiency = _decide(bundle, proposal)

    old_rows = [
        row
        for row in sufficiency.evidence_alternative_matrix
        if row.evidence_id == "EMAIL_OLD"
    ]
    assert old_rows
    assert all(row.relationship == "superseded" for row in old_rows)
    assert proof.contradictions == []
    assert sufficiency.safe_to_resolve is True
