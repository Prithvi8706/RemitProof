from datetime import date
from decimal import Decimal

import pytest

from app.models import CandidateBundle, InvestigationProposal
from app.services.proof_engine import verify_candidate


def synthetic_bundle(*, known_payers=None):
    return CandidateBundle.model_validate(
        {
            "payment": {
                "payment_id": "PAY_TEST",
                "date": date(2026, 1, 15),
                "amount": Decimal("100.00"),
                "currency": "USD",
                "payer_name": "Treasury Bank",
            },
            "candidate_customers": [
                {
                    "customer_id": "CUS_TEST",
                    "legal_name": "Acme Corp",
                    "known_payers": known_payers or [],
                }
            ],
            "candidate_invoices": [
                {
                    "invoice_id": "INV_TEST",
                    "customer_id": "CUS_TEST",
                    "amount": Decimal("100.00"),
                    "currency": "USD",
                    "issue_date": date(2025, 12, 1),
                    "due_date": date(2026, 1, 1),
                    "description": "Synthetic invoice",
                }
            ],
            "candidate_emails": [
                {
                    "email_id": "EMAIL_TEST",
                    "sender": "treasury@example.test",
                    "customer_id": "CUS_TEST",
                    "date": date(2026, 1, 15),
                    "subject": "Payment instruction",
                    "body": "Treasury Bank paid on behalf of Acme Corp.",
                }
            ],
        }
    )


def proposal(*, evidence_ids):
    return InvestigationProposal(
        payment_id="PAY_TEST",
        proposed_customer="CUS_TEST",
        invoice_ids=["INV_TEST"],
        evidence_ids=evidence_ids,
    )


@pytest.mark.parametrize(
    ("evidence_ids", "expected_entity_support"),
    [
        (["CUS_TEST", "INV_TEST"], False),
        (["CUS_TEST", "INV_TEST", "EMAIL_TEST"], True),
    ],
)
def test_entity_relationship_support_requires_a_cited_email(evidence_ids, expected_entity_support):
    proof = verify_candidate(synthetic_bundle(), proposal(evidence_ids=evidence_ids))

    assert proof.entity_support is expected_entity_support


def test_direct_customer_payer_mapping_does_not_require_email_citation():
    proof = verify_candidate(
        synthetic_bundle(known_payers=["Treasury Bank"]),
        proposal(evidence_ids=["CUS_TEST", "INV_TEST"]),
    )

    assert proof.entity_support is True
