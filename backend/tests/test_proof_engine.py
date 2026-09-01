from app.models import InvestigationProposal
from app.services.proof_engine import verify_candidate


def proposal(payment_id, customer_id, invoice_ids, credit_ids=None, evidence_ids=None):
    return InvestigationProposal(
        payment_id=payment_id,
        proposed_customer=customer_id,
        invoice_ids=invoice_ids,
        credit_ids=credit_ids or [],
        evidence_ids=evidence_ids or [],
        semantic_claims=[],
        unresolved_questions=[],
    )


def test_proof_uses_decimal_safe_credit_arithmetic(bundle_factory):
    bundle = bundle_factory("SPIKE_10")
    candidate = proposal(
        "PAY_S10",
        "CUS_S10",
        ["INV_S10A", "INV_S10B"],
        ["CR_S10A"],
        ["EMAIL_S10", "CR_S10A", "CUS_S10"],
    )

    proof = verify_candidate(bundle, candidate)

    assert proof.financial_validity is True
    assert str(proof.invoice_total) == "20000.00"
    assert str(proof.credit_total) == "350.00"
    assert str(proof.calculated_total) == "19650.00"
    assert proof.currency_validity is True
    assert proof.entity_support is True


def test_proof_detects_conflicting_credit_amount(bundle_factory):
    bundle = bundle_factory("SPIKE_07")
    candidate = proposal(
        "PAY_S07",
        "CUS_S07",
        ["INV_S07A"],
        ["CR_S07A"],
        ["EMAIL_S07", "CR_S07A"],
    )

    proof = verify_candidate(bundle, candidate)

    assert proof.financial_validity is True
    assert proof.contradictions
    assert "500" in proof.contradictions[0]
    assert "350" in proof.contradictions[0]


def test_proof_rejects_missing_credit_note(bundle_factory):
    bundle = bundle_factory("SPIKE_08")
    candidate = proposal(
        "PAY_S08",
        "CUS_S08",
        ["INV_S08A"],
        ["CR_S08A"],
        ["EMAIL_S08"],
    )

    proof = verify_candidate(bundle, candidate)

    assert proof.financial_validity is False
    assert "missing_credit_note" in proof.reason_codes
    assert "CR_S08A" in proof.missing_required_evidence


def test_proof_rejects_unsupported_entity_relationship(bundle_factory):
    bundle = bundle_factory("SPIKE_09")
    candidate = proposal("PAY_S09", "CUS_S09", ["INV_S09A"])

    proof = verify_candidate(bundle, candidate)

    assert proof.financial_validity is True
    assert proof.entity_support is False
    assert "unsupported_entity_relationship" in proof.reason_codes


def test_proof_blocks_closed_invoice_and_duplicate_allocation(bundle_factory):
    bundle = bundle_factory("SPIKE_01")
    closed_invoice = bundle.candidate_invoices[0].model_copy(
        update={"status": "closed", "allocated_payment_id": "PAY_OLD"}
    )
    unsafe_bundle = bundle.model_copy(update={"candidate_invoices": [closed_invoice]})
    candidate = proposal("PAY_S01", "CUS_S01", ["INV_S01A"])

    proof = verify_candidate(unsafe_bundle, candidate)

    assert proof.state_validity is False
    assert proof.duplicate_risk is True
    assert "invoice_not_open" in proof.reason_codes
    assert "duplicate_allocation_risk" in proof.reason_codes


def test_proof_rejects_unsupported_currency_mismatch(bundle_factory):
    bundle = bundle_factory("SPIKE_01")
    wrong_currency_invoice = bundle.candidate_invoices[0].model_copy(update={"currency": "EUR"})
    unsafe_bundle = bundle.model_copy(update={"candidate_invoices": [wrong_currency_invoice]})
    candidate = proposal("PAY_S01", "CUS_S01", ["INV_S01A"])

    proof = verify_candidate(unsafe_bundle, candidate)

    assert proof.currency_validity is False
    assert "unsupported_currency_mismatch" in proof.reason_codes
