from datetime import date

from app.models import CandidateBundle, InvestigationProposal
from app.services.alternative_finder import find_valid_alternatives
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.proof_engine import verify_candidate
from app.utils.remittance_semantics import superseded_allocation_email_ids


def _bundle(
    *,
    old_email_body: str,
    new_email_body: str,
    bank_reference: str = "",
    remittance_reference: str = "",
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
            "candidate_invoices": [
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
            "candidate_credits": [],
            "candidate_emails": [
                {
                    "email_id": "EMAIL_OLD",
                    "sender": "treasury@acmecorp.example",
                    "customer_id": "CUS_TEST",
                    "date": old_date,
                    "subject": "Payment instruction",
                    "body": old_email_body,
                },
                {
                    "email_id": "EMAIL_NEW",
                    "sender": "treasury@acmecorp.example",
                    "customer_id": "CUS_TEST",
                    "date": new_date,
                    "subject": "Payment instruction update",
                    "body": new_email_body,
                },
            ],
        }
    )


def _proposal(*, invoice_ids, evidence_ids) -> InvestigationProposal:
    return InvestigationProposal(
        payment_id="PAY_TEST",
        proposed_customer="CUS_TEST",
        invoice_ids=invoice_ids,
        credit_ids=[],
        evidence_ids=evidence_ids,
    )


def _decide(bundle: CandidateBundle, proposal: InvestigationProposal):
    proof = verify_candidate(bundle, proposal)
    alternatives = find_valid_alternatives(bundle)
    sufficiency = evaluate_evidence_sufficiency(bundle, proposal, proof, alternatives)
    return proof, alternatives, sufficiency


def _superseded(bundle: CandidateBundle):
    return superseded_allocation_email_ids(
        bundle.candidate_emails,
        payment=bundle.payment,
    )


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


def test_correction_can_switch_between_current_payment_reference_fields():
    bundle = _bundle(
        old_email_body="For WIRE_TEST, please apply the payment to INV_201.",
        new_email_body="Correction for PAY_TEST: please apply the payment to INV_202.",
        bank_reference="WIRE_TEST",
    )
    proposal = _proposal(
        invoice_ids=["INV_202"],
        evidence_ids=["CUS_TEST", "INV_202", "EMAIL_NEW"],
    )

    proof, _, sufficiency = _decide(bundle, proposal)

    assert _superseded(bundle) == {"EMAIL_OLD"}
    assert proof.contradictions == []
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
