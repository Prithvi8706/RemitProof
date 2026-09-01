from datetime import date
from pathlib import Path

import pytest

from app.models import CandidateBundle, Customer, Invoice, InvestigationProposal, Payment
from app.services.alternative_finder import find_valid_alternatives
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.pipeline import process_payment
from app.services.proof_engine import verify_candidate
from app.utils.loaders import Dataset, load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]


def _bundle(
    *,
    email_body: str,
    legal_name: str = "Acme Corp",
    known_payers=None,
    candidate_credits=None,
    payment_amount: str = "100.00",
    bank_reference: str = "",
    remittance_reference: str = "",
    allocated_customer_id=None,
) -> CandidateBundle:
    return CandidateBundle.model_validate(
        {
            "payment": {
                "payment_id": "PAY_TEST",
                "date": date(2026, 1, 15),
                "amount": payment_amount,
                "currency": "USD",
                "payer_name": "Treasury Bank",
                "bank_reference": bank_reference,
                "remittance_reference": remittance_reference,
                "allocated_customer_id": allocated_customer_id,
            },
            "candidate_customers": [
                {
                    "customer_id": "CUS_TEST",
                    "legal_name": legal_name,
                    "known_payers": known_payers if known_payers is not None else [],
                }
            ],
            "candidate_invoices": [
                {
                    "invoice_id": "INV_TEST",
                    "customer_id": "CUS_TEST",
                    "amount": "100.00",
                    "currency": "USD",
                    "issue_date": date(2025, 12, 1),
                    "due_date": date(2026, 1, 1),
                    "description": "Synthetic invoice",
                }
            ],
            "candidate_credits": candidate_credits if candidate_credits is not None else [],
            "candidate_emails": [
                {
                    "email_id": "EMAIL_TEST",
                    "sender": "treasury@example.test",
                    "customer_id": "CUS_TEST",
                    "date": date(2026, 1, 15),
                    "subject": "Payment instruction",
                    "body": email_body,
                }
            ],
        }
    )


def _proposal(
    *,
    payment_id: str = "PAY_TEST",
    credit_ids=None,
    evidence_ids=None,
) -> InvestigationProposal:
    return InvestigationProposal(
        payment_id=payment_id,
        proposed_customer="CUS_TEST",
        invoice_ids=["INV_TEST"],
        credit_ids=credit_ids if credit_ids is not None else [],
        evidence_ids=evidence_ids if evidence_ids is not None else ["CUS_TEST", "INV_TEST"],
    )


def test_proof_rejects_proposal_for_a_different_payment():
    proof = verify_candidate(
        _bundle(email_body="Treasury Bank paid on behalf of Acme Corp."),
        _proposal(payment_id="PAY_OTHER"),
    )

    assert proof.financial_validity is False
    assert "payment_id_mismatch" in proof.reason_codes
    assert "payment_identity" in proof.missing_required_evidence


class _MismatchedPaymentInvestigator:
    def investigate(self, bundle):
        return InvestigationProposal(
            payment_id="PAY_OTHER",
            proposed_customer="CUS_X051",
            invoice_ids=["INV_X051A", "INV_X051B"],
            evidence_ids=["EMAIL_X051", "CUS_X051"],
        )


def test_pipeline_downgrades_mismatched_payment_proposal_to_human_review():
    dataset = load_dataset(REPO_ROOT / "data")

    result = process_payment(
        "PAY_051",
        dataset,
        _MismatchedPaymentInvestigator(),
    )

    assert result.proposal["payment_id"] == "PAY_OTHER"
    assert result.decision.decision == "human_review"
    assert result.proof is not None
    assert "payment_id_mismatch" in result.proof.reason_codes
    assert result.sufficiency is not None
    assert result.sufficiency.safe_to_resolve is False


@pytest.mark.parametrize(
    "email_body",
    [
        "Treasury Bank did not pay on behalf of Acme Corp.",
        "Do not treat Treasury Bank as an authorized payer for Acme Corp.",
        "Treasury Bank is an unauthorized payer for Acme Corp.",
        "Treasury Bank is an unapproved payer for Acme Corp.",
        "Treasury Bank is a prohibited payer for Acme Corp.",
        "Treasury Bank is a forbidden payer for Acme Corp.",
        "Treasury Bank is a disallowed payer for Acme Corp.",
        "Treasury Bank is an unauthorised payer for Acme Corp.",
        "Treasury Bank is an ineligible payer for Acme Corp.",
    ],
)
def test_negated_relationship_email_cannot_support_entity(email_body):
    bundle = _bundle(email_body=email_body)
    proposal = _proposal(evidence_ids=["CUS_TEST", "INV_TEST", "EMAIL_TEST"])

    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        find_valid_alternatives(bundle),
    )

    assert proof.entity_support is False
    assert "unsupported_entity_relationship" in proof.reason_codes
    assert sufficiency.safe_to_resolve is False


def test_positive_cited_relationship_email_supports_entity():
    proof = verify_candidate(
        _bundle(email_body="Treasury Bank paid on behalf of Acme Corp."),
        _proposal(evidence_ids=["CUS_TEST", "INV_TEST", "EMAIL_TEST"]),
    )

    assert proof.entity_support is True


@pytest.mark.parametrize(
    ("legal_name", "email_body"),
    [
        ("Acme Corp", "Treasury Bank paid on behalf of Acme Corporate."),
        ("A B", "Treasury Bank paid on behalf of ABC."),
    ],
)
def test_email_relationship_requires_legal_name_token_boundaries(legal_name, email_body):
    bundle = _bundle(email_body=email_body, legal_name=legal_name)
    proposal = _proposal(evidence_ids=["CUS_TEST", "INV_TEST", "EMAIL_TEST"])

    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        find_valid_alternatives(bundle),
    )

    assert proof.entity_support is False
    assert "unsupported_entity_relationship" in proof.reason_codes
    assert sufficiency.safe_to_resolve is False


def test_direct_customer_payer_mapping_remains_valid_without_negative_evidence():
    proof = verify_candidate(
        _bundle(
            email_body="Payment instructions for Acme Corp.",
            known_payers=["Treasury Bank"],
        ),
        _proposal(),
    )

    assert proof.entity_support is True


@pytest.mark.parametrize(
    "email_body",
    [
        "Treasury Bank did not pay on behalf of Acme Corp.",
        "Treasury Bank is an unauthorized payer for Acme Corp.",
        "Treasury Bank is a prohibited payer for Acme Corp.",
    ],
)
def test_explicit_negative_payer_evidence_overrides_direct_mapping(email_body):
    bundle = _bundle(
        email_body=email_body,
        known_payers=["Treasury Bank"],
    )
    proposal = _proposal()

    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        find_valid_alternatives(bundle),
    )

    assert proof.entity_support is False
    assert "unsupported_entity_relationship" in proof.reason_codes
    assert sufficiency.safe_to_resolve is False


def test_unmatched_payment_with_allocated_customer_is_not_authorizable():
    bundle = _bundle(
        email_body="Treasury Bank paid on behalf of Acme Corp.",
        known_payers=["Treasury Bank"],
        allocated_customer_id="CUS_TEST",
    )
    proposal = _proposal()

    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        find_valid_alternatives(bundle),
    )

    assert proof.state_validity is False
    assert proof.duplicate_risk is True
    assert "payment_already_allocated" in proof.reason_codes
    assert sufficiency.safe_to_resolve is False


def test_cited_credit_deduction_without_selected_credit_cannot_resolve():
    bundle = _bundle(
        email_body="Apply INV_TEST after deducting USD 10 credit CR_TEST.",
        known_payers=["Treasury Bank"],
        candidate_credits=[
            {
                "credit_id": "CR_TEST",
                "customer_id": "CUS_TEST",
                "invoice_id": "INV_TEST",
                "amount": "10.00",
                "currency": "USD",
                "reason": "Synthetic credit",
                "status": "valid",
            }
        ],
    )
    proposal = _proposal(evidence_ids=["CUS_TEST", "INV_TEST", "EMAIL_TEST"])

    proof = verify_candidate(bundle, proposal)
    alternatives = find_valid_alternatives(bundle)
    sufficiency = evaluate_evidence_sufficiency(bundle, proposal, proof, alternatives)

    assert proof.financial_validity is True
    assert proof.credit_support is False
    assert "missing_credit_note" in proof.reason_codes
    assert "CR_TEST" in proof.missing_required_evidence
    assert len(alternatives) == 1
    assert sufficiency.safe_to_resolve is False


def test_no_credit_claim_preserves_valid_no_credit_authorization():
    bundle = _bundle(
        email_body="Apply INV_TEST in full.",
        known_payers=["Treasury Bank"],
        candidate_credits=[
            {
                "credit_id": "CR_TEST",
                "customer_id": "CUS_TEST",
                "invoice_id": "INV_TEST",
                "amount": "10.00",
                "currency": "USD",
                "reason": "Unused credit",
                "status": "valid",
            }
        ],
    )
    proposal = _proposal(evidence_ids=["CUS_TEST", "INV_TEST", "EMAIL_TEST"])

    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        find_valid_alternatives(bundle),
    )

    assert proof.financial_validity is True
    assert proof.credit_support is True
    assert sufficiency.safe_to_resolve is True


def test_candidate_email_invoice_reference_conflict_blocks_unique_allocation():
    bundle = _bundle(
        email_body="Apply INV_BAD.",
        known_payers=["Treasury Bank"],
    )
    proposal = _proposal(evidence_ids=["CUS_TEST", "INV_TEST", "EMAIL_TEST"])

    proof = verify_candidate(bundle, proposal)
    alternatives = find_valid_alternatives(bundle)
    sufficiency = evaluate_evidence_sufficiency(bundle, proposal, proof, alternatives)

    assert len(alternatives) == 1
    assert proof.financial_validity is True
    assert "email_invoice_reference_mismatch" in proof.reason_codes
    assert proof.contradictions
    assert sufficiency.evidence_disambiguates_alternatives is True
    assert sufficiency.safe_to_resolve is False


def _reference_dataset() -> Dataset:
    return Dataset(
        payments=[
            Payment(
                payment_id="PAY_REF",
                date=date(2026, 1, 15),
                amount="100.00",
                currency="USD",
                payer_name="Acme Corp",
                remittance_reference="INV_BAD",
            )
        ],
        invoices=[
            Invoice(
                invoice_id="INV_GOOD",
                customer_id="CUS_REF",
                amount="100.00",
                currency="USD",
                issue_date=date(2025, 12, 1),
                due_date=date(2026, 1, 1),
                description="Synthetic invoice",
            )
        ],
        customers=[Customer(customer_id="CUS_REF", legal_name="Acme Corp")],
        credits=[],
        emails=[],
    )


class _ReferenceInvestigator:
    def investigate(self, bundle):
        return InvestigationProposal(
            payment_id=bundle.payment.payment_id,
            proposed_customer="CUS_REF",
            invoice_ids=["INV_GOOD"],
            evidence_ids=["CUS_REF"],
        )


def test_payment_invoice_reference_conflict_keeps_pipeline_in_human_review():
    result = process_payment("PAY_REF", _reference_dataset(), _ReferenceInvestigator())

    assert result.baseline.status == "unresolved"
    assert result.decision.decision == "human_review"
    assert result.proof is not None
    assert result.proof.financial_validity is False
    assert "payment_invoice_reference_mismatch" in result.proof.reason_codes
    assert result.sufficiency is not None
    assert result.sufficiency.safe_to_resolve is False


def test_authoritative_payment_credit_reference_cannot_be_omitted():
    bundle = _bundle(
        email_body="Apply INV_TEST in full.",
        known_payers=["Treasury Bank"],
        remittance_reference="CR_TEST",
        candidate_credits=[
            {
                "credit_id": "CR_TEST",
                "customer_id": "CUS_TEST",
                "invoice_id": "INV_TEST",
                "amount": "10.00",
                "currency": "USD",
                "reason": "Synthetic credit",
                "status": "valid",
            }
        ],
    )
    proposal = _proposal(evidence_ids=["CUS_TEST", "INV_TEST", "EMAIL_TEST"])

    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        find_valid_alternatives(bundle),
    )

    assert proof.credit_support is False
    assert "payment_credit_reference_mismatch" in proof.reason_codes
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False


def test_authoritative_payment_credit_reference_cannot_be_substituted():
    bundle = _bundle(
        email_body="Apply INV_TEST after the selected credit.",
        known_payers=["Treasury Bank"],
        payment_amount="90.00",
        remittance_reference="CR_TEST",
        candidate_credits=[
            {
                "credit_id": "CR_TEST",
                "customer_id": "CUS_TEST",
                "invoice_id": "INV_TEST",
                "amount": "10.00",
                "currency": "USD",
                "reason": "Authoritative credit",
                "status": "valid",
            },
            {
                "credit_id": "CR_OTHER",
                "customer_id": "CUS_TEST",
                "invoice_id": "INV_TEST",
                "amount": "10.00",
                "currency": "USD",
                "reason": "Substitute credit",
                "status": "valid",
            },
        ],
    )
    proposal = _proposal(
        credit_ids=["CR_OTHER"],
        evidence_ids=["CUS_TEST", "INV_TEST", "CR_OTHER", "EMAIL_TEST"],
    )

    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        find_valid_alternatives(bundle),
    )

    assert proof.financial_validity is False
    assert "payment_credit_reference_mismatch" in proof.reason_codes
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False


def test_email_prohibition_blocks_selected_sole_invoice():
    bundle = _bundle(
        email_body="Do not apply INV_TEST.",
        known_payers=["Treasury Bank"],
    )
    proposal = _proposal(evidence_ids=["CUS_TEST", "INV_TEST", "EMAIL_TEST"])

    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        find_valid_alternatives(bundle),
    )

    assert proof.financial_validity is True
    assert "prohibited_invoice_reference" in proof.reason_codes
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False


def test_email_prohibition_blocks_selected_sole_credit():
    bundle = _bundle(
        email_body="Do not use CR_TEST.",
        known_payers=["Treasury Bank"],
        payment_amount="90.00",
        candidate_credits=[
            {
                "credit_id": "CR_TEST",
                "customer_id": "CUS_TEST",
                "invoice_id": "INV_TEST",
                "amount": "10.00",
                "currency": "USD",
                "reason": "Synthetic credit",
                "status": "valid",
            }
        ],
    )
    proposal = _proposal(
        credit_ids=["CR_TEST"],
        evidence_ids=["CUS_TEST", "INV_TEST", "CR_TEST", "EMAIL_TEST"],
    )

    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        find_valid_alternatives(bundle),
    )

    assert proof.financial_validity is True
    assert "prohibited_credit_reference" in proof.reason_codes
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False


@pytest.mark.parametrize(
    "email_body",
    [
        "INV_TEST is prohibited.",
        "INV_TEST is forbidden from use.",
    ],
)
def test_unambiguous_invoice_prohibition_blocks_selected_invoice(email_body):
    bundle = _bundle(
        email_body=email_body,
        known_payers=["Treasury Bank"],
    )
    proposal = _proposal(evidence_ids=["CUS_TEST", "INV_TEST", "EMAIL_TEST"])

    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        find_valid_alternatives(bundle),
    )

    assert proof.financial_validity is True
    assert "prohibited_invoice_reference" in proof.reason_codes
    assert proof.contradictions
    assert sufficiency.safe_to_resolve is False
