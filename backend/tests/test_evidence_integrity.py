from pathlib import Path

from app.models import InvestigationProposal, SemanticClaim
from app.services.alternative_finder import find_valid_alternatives
from app.services.audit_builder import build_evidence
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.pipeline import process_payment
from app.services.proof_engine import verify_candidate
from app.utils.loaders import load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]


def evaluate(bundle, customer_id, invoice_ids, credit_ids=None, evidence_ids=None, semantic_claims=None):
    proposal = InvestigationProposal(
        payment_id=bundle.payment.payment_id,
        proposed_customer=customer_id,
        invoice_ids=invoice_ids,
        credit_ids=credit_ids or [],
        evidence_ids=evidence_ids or [],
        semantic_claims=semantic_claims or [],
        unresolved_questions=[],
    )
    proof = verify_candidate(bundle, proposal)
    alternatives = find_valid_alternatives(bundle)
    sufficiency = evaluate_evidence_sufficiency(bundle, proposal, proof, alternatives)
    return proposal, sufficiency


def test_empty_proposal_evidence_cannot_resolve(bundle_factory):
    bundle = bundle_factory("SPIKE_05")

    _, result = evaluate(
        bundle,
        "CUS_S05",
        ["INV_S05A", "INV_S05B"],
        evidence_ids=[],
    )

    assert result.safe_to_resolve is False
    assert "proposal_evidence" in result.missing_required_evidence


def test_invalid_proposal_evidence_id_cannot_resolve(bundle_factory):
    bundle = bundle_factory("SPIKE_05")

    _, result = evaluate(
        bundle,
        "CUS_S05",
        ["INV_S05A", "INV_S05B"],
        evidence_ids=["EMAIL_S05", "EMAIL_DOES_NOT_EXIST"],
    )

    assert result.safe_to_resolve is False
    assert "EMAIL_DOES_NOT_EXIST" in result.missing_required_evidence


def test_uncited_email_cannot_disambiguate_alternatives(bundle_factory):
    bundle = bundle_factory("SPIKE_05")

    _, result = evaluate(
        bundle,
        "CUS_S05",
        ["INV_S05A", "INV_S05B"],
        evidence_ids=["CUS_S05"],
    )

    assert result.alternative_allocations_exist is True
    assert result.evidence_disambiguates_alternatives is False
    assert result.safe_to_resolve is False


def test_selected_invoice_record_cannot_disambiguate_same_amount_invoices(bundle_factory):
    bundle = bundle_factory("SPIKE_06")

    _, result = evaluate(
        bundle,
        "CUS_S06",
        ["INV_S06A"],
        evidence_ids=["CUS_S06", "INV_S06A"],
    )

    assert result.alternative_allocations_exist is True
    assert result.evidence_disambiguates_alternatives is False
    assert result.safe_to_resolve is False


def test_selected_credit_record_cannot_disambiguate_competing_credits(bundle_factory):
    bundle = bundle_factory("SPIKE_04")

    _, result = evaluate(
        bundle,
        "CUS_S04",
        ["INV_S04A"],
        credit_ids=["CR_S04A"],
        evidence_ids=["CUS_S04", "INV_S04A", "CR_S04A"],
    )

    assert result.alternative_allocations_exist is True
    assert result.evidence_disambiguates_alternatives is False
    assert result.safe_to_resolve is False


def test_selected_credit_must_be_cited(bundle_factory):
    bundle = bundle_factory("SPIKE_10")

    _, result = evaluate(
        bundle,
        "CUS_S10",
        ["INV_S10A", "INV_S10B"],
        credit_ids=["CR_S10A"],
        evidence_ids=["EMAIL_S10", "CUS_S10"],
    )

    assert result.financial_validity is True
    assert result.safe_to_resolve is False
    assert "CR_S10A" in result.missing_required_evidence


def test_semantic_claim_evidence_must_be_valid_and_top_level_cited(bundle_factory):
    bundle = bundle_factory("SPIKE_05")
    claim = SemanticClaim(
        claim_id="CLAIM_UNCITED",
        claim="The remittance names the selected invoices.",
        evidence_ids=["EMAIL_S05"],
    )

    _, result = evaluate(
        bundle,
        "CUS_S05",
        ["INV_S05A", "INV_S05B"],
        evidence_ids=["CUS_S05"],
        semantic_claims=[claim],
    )

    assert result.safe_to_resolve is False
    assert "EMAIL_S05" in result.missing_required_evidence


def test_audit_contains_every_cited_and_required_record(bundle_factory):
    bundle = bundle_factory("SPIKE_10")
    proposal = InvestigationProposal(
        payment_id=bundle.payment.payment_id,
        proposed_customer="CUS_S10",
        invoice_ids=["INV_S10A", "INV_S10B"],
        credit_ids=["CR_S10A"],
        semantic_claims=[],
        evidence_ids=["EMAIL_S10", "CR_S10A", "CUS_S10"],
        unresolved_questions=[],
    )

    evidence = build_evidence(bundle, proposal)
    evidence_by_id = {record["evidence_id"]: record for record in evidence}

    assert set(evidence_by_id) == {
        "EMAIL_S10",
        "CR_S10A",
        "CUS_S10",
        "INV_S10A",
        "INV_S10B",
    }
    assert evidence_by_id["EMAIL_S10"]["evidence_type"] == "remittance_email"
    assert evidence_by_id["CR_S10A"]["evidence_type"] == "credit_note"
    assert evidence_by_id["CUS_S10"]["evidence_type"] == "customer_record"
    assert evidence_by_id["INV_S10A"]["evidence_type"] == "invoice_record"
    assert evidence_by_id["INV_S10B"]["evidence_type"] == "invoice_record"
    assert evidence_by_id["EMAIL_S10"]["evidence_role"] == "model_citation"
    assert evidence_by_id["CR_S10A"]["evidence_role"] == "model_citation"
    assert evidence_by_id["INV_S10A"]["evidence_role"] == "audit_context"
    assert evidence_by_id["INV_S10B"]["evidence_role"] == "audit_context"
    assert all(record["evidence_id"] in evidence_by_id for record in evidence)


class StubInvestigator:
    def __init__(self, proposal):
        self.proposal = proposal

    def investigate(self, bundle):
        return self.proposal


def test_pipeline_decision_ids_match_returned_audit_records():
    dataset = load_dataset(REPO_ROOT / "data")
    proposal = InvestigationProposal(
        payment_id="PAY_051",
        proposed_customer="CUS_X051",
        invoice_ids=["INV_X051A", "INV_X051B"],
        credit_ids=[],
        semantic_claims=[],
        evidence_ids=["EMAIL_X051", "CUS_X051"],
        unresolved_questions=[],
    )

    result = process_payment("PAY_051", dataset, StubInvestigator(proposal))
    audit_ids = [record["evidence_id"] for record in result.evidence]

    assert result.decision.decision == "resolved"
    assert result.decision.evidence == audit_ids
    assert set(audit_ids) == {
        "EMAIL_X051",
        "CUS_X051",
        "INV_X051A",
        "INV_X051B",
    }
