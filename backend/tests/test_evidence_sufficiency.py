from app.models import InvestigationProposal
from app.services.alternative_finder import find_valid_alternatives
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.proof_engine import verify_candidate


def evaluate(bundle, customer_id, invoice_ids, credit_ids=None, evidence_ids=None):
    proposal = InvestigationProposal(
        payment_id=bundle.payment.payment_id,
        proposed_customer=customer_id,
        invoice_ids=invoice_ids,
        credit_ids=credit_ids or [],
        evidence_ids=evidence_ids or [],
        semantic_claims=[],
        unresolved_questions=[],
    )
    proof = verify_candidate(bundle, proposal)
    alternatives = find_valid_alternatives(bundle)
    return evaluate_evidence_sufficiency(bundle, proposal, proof, alternatives)


def test_email_disambiguates_two_financial_allocations(bundle_factory):
    bundle = bundle_factory("SPIKE_05")

    result = evaluate(bundle, "CUS_S05", ["INV_S05A", "INV_S05B"], evidence_ids=["EMAIL_S05"])

    assert result.alternative_allocations_exist is True
    assert result.evidence_disambiguates_alternatives is True
    assert result.safe_to_resolve is True


def test_same_amount_without_remittance_abstains(bundle_factory):
    bundle = bundle_factory("SPIKE_06")

    result = evaluate(bundle, "CUS_S06", ["INV_S06A"])

    assert result.alternative_allocations_exist is True
    assert result.evidence_disambiguates_alternatives is False
    assert result.safe_to_resolve is False
    assert result.abstention_reason == "multiple_financially_valid_explanations"


def test_conflicting_evidence_abstains_even_when_arithmetic_passes(bundle_factory):
    bundle = bundle_factory("SPIKE_07")

    result = evaluate(
        bundle,
        "CUS_S07",
        ["INV_S07A"],
        ["CR_S07A"],
        ["EMAIL_S07", "CR_S07A"],
    )

    assert result.financial_validity is True
    assert result.contradictions_exist is True
    assert result.safe_to_resolve is False
    assert result.abstention_reason == "contradictory_evidence"


def test_complex_hero_case_resolves_only_with_disambiguating_evidence(bundle_factory):
    bundle = bundle_factory("SPIKE_10")

    result = evaluate(
        bundle,
        "CUS_S10",
        ["INV_S10A", "INV_S10B"],
        ["CR_S10A"],
        ["EMAIL_S10", "CR_S10A", "CUS_S10"],
    )

    assert result.alternative_allocations_exist is True
    assert result.evidence_disambiguates_alternatives is True
    assert result.safe_to_resolve is True
