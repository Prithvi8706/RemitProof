from decimal import Decimal

from app.models import (
    AlternativeAllocation,
    InvestigationProposal,
    ProofResult,
    SufficiencyResult,
)
from app.services.decision_artifacts import (
    _counterfactual_reason,
    build_decision_artifact,
)


def test_single_alternative_counterfactual_explains_missing_evidence():
    assert _counterfactual_reason(True, 1) == (
        "Without this record, the proposed allocation lacks required evidence."
    )


def test_blocked_single_alternative_preserves_financial_proof_status():
    proof = ProofResult(
        financial_validity=True,
        state_validity=True,
        currency_validity=True,
        entity_support=False,
        credit_support=True,
        duplicate_risk=False,
    )
    sufficiency = SufficiencyResult(
        financial_validity=True,
        entity_support=False,
        credit_support=True,
        alternative_allocations_exist=False,
        evidence_disambiguates_alternatives=True,
        contradictions_exist=False,
        missing_required_evidence=["entity_relationship"],
        duplicate_risk=False,
        safe_to_resolve=False,
        abstention_reason="missing_required_evidence",
    )
    alternative = AlternativeAllocation(
        allocation_id="ALLOC_001",
        customer_id="CUS_001",
        invoice_ids=["INV_001"],
        credit_ids=[],
        calculated_total=Decimal("100.00"),
    )

    artifact = build_decision_artifact(
        "PAY_001",
        proposal=InvestigationProposal(
            payment_id="PAY_001",
            proposed_customer="CUS_001",
            invoice_ids=["INV_001"],
            evidence_ids=["CUS_001", "INV_001"],
        ),
        proof=proof,
        alternatives=[alternative],
        sufficiency=sufficiency,
        counterfactuals=[],
    )

    assert artifact["proof_status"]["financial_constraints"] == "pass"


def test_blocked_single_alternative_reports_pass_when_proposal_itself_is_invalid():
    proof = ProofResult(
        financial_validity=False,
        state_validity=True,
        currency_validity=True,
        entity_support=True,
        credit_support=True,
        duplicate_risk=False,
    )
    sufficiency = SufficiencyResult(
        financial_validity=False,
        entity_support=True,
        credit_support=True,
        alternative_allocations_exist=False,
        evidence_disambiguates_alternatives=False,
        contradictions_exist=False,
        missing_required_evidence=[],
        duplicate_risk=False,
        safe_to_resolve=False,
        abstention_reason="financial_mismatch",
    )
    alternative = AlternativeAllocation(
        allocation_id="ALT_001",
        customer_id="CUS_001",
        invoice_ids=["INV_002"],
        credit_ids=[],
        calculated_total=Decimal("100.00"),
    )

    artifact = build_decision_artifact(
        "PAY_001",
        proposal=InvestigationProposal(
            payment_id="PAY_001",
            proposed_customer="CUS_001",
            invoice_ids=["INV_001"],
            evidence_ids=["CUS_001", "INV_001"],
        ),
        proof=proof,
        alternatives=[alternative],
        sufficiency=sufficiency,
        counterfactuals=[],
    )

    assert artifact["proof_status"]["financial_constraints"] == "pass"
