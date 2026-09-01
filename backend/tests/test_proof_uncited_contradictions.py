from datetime import date

from app.models import CandidateBundle, InvestigationProposal
from app.services.alternative_finder import find_valid_alternatives
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.proof_engine import verify_candidate


def _bundle(email_body: str) -> CandidateBundle:
    return CandidateBundle.model_validate(
        {
            "payment": {
                "payment_id": "PAY_UC",
                "date": date(2026, 1, 15),
                "amount": "100.00",
                "currency": "USD",
                "payer_name": "Treasury Bank",
            },
            "candidate_customers": [
                {
                    "customer_id": "CUS_UC",
                    "legal_name": "Acme Corp",
                    "known_payers": ["Treasury Bank"],
                }
            ],
            "candidate_invoices": [
                {
                    "invoice_id": "INV_UC",
                    "customer_id": "CUS_UC",
                    "amount": "100.00",
                    "currency": "USD",
                    "issue_date": date(2025, 12, 1),
                    "due_date": date(2026, 1, 1),
                    "description": "Synthetic invoice",
                }
            ],
            "candidate_credits": [
                {
                    "credit_id": "CR_UC",
                    "customer_id": "CUS_UC",
                    "invoice_id": "INV_UC",
                    "amount": "10.00",
                    "currency": "USD",
                    "reason": "Synthetic credit",
                    "status": "valid",
                }
            ],
            "candidate_emails": [
                {
                    "email_id": "EMAIL_UC",
                    "sender": "treasury@example.test",
                    "customer_id": "CUS_UC",
                    "date": date(2026, 1, 15),
                    "subject": "Payment instruction",
                    "body": email_body,
                }
            ],
        }
    )


def _evaluate(bundle: CandidateBundle):
    proposal = InvestigationProposal(
        payment_id="PAY_UC",
        proposed_customer="CUS_UC",
        invoice_ids=["INV_UC"],
        credit_ids=[],
        evidence_ids=["CUS_UC", "INV_UC"],
    )
    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        find_valid_alternatives(bundle),
    )
    return proof, sufficiency


def test_uncited_credit_claim_blocks_gross_allocation():
    proof, sufficiency = _evaluate(
        _bundle("Apply INV_UC after deducting USD 10 credit CR_UC.")
    )

    assert proof.financial_validity is True
    assert proof.credit_support is False
    assert "missing_credit_note" in proof.reason_codes
    assert "CR_UC" in proof.missing_required_evidence
    assert sufficiency.safe_to_resolve is False


def test_uncited_email_without_credit_claim_preserves_no_credit_resolution():
    proof, sufficiency = _evaluate(_bundle("Apply INV_UC in full."))

    assert proof.financial_validity is True
    assert proof.credit_support is True
    assert sufficiency.safe_to_resolve is True
