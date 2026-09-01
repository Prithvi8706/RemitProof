from pathlib import Path

from app.models import InvestigationProposal, SemanticClaim
from app.services.pipeline import process_payment
from app.utils.loaders import load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]


class StubInvestigator:
    def __init__(self, proposals):
        self.proposals = proposals
        self.calls = []

    def investigate(self, bundle):
        self.calls.append(bundle.payment.payment_id)
        return self.proposals[bundle.payment.payment_id]


def test_pipeline_never_sends_normal_match_to_investigator():
    dataset = load_dataset(REPO_ROOT / "data")
    investigator = StubInvestigator({})

    result = process_payment("PAY_001", dataset, investigator)

    assert result.decision.decision == "matched_normally"
    assert investigator.calls == []


def test_pipeline_resolves_disambiguated_semantic_exception():
    dataset = load_dataset(REPO_ROOT / "data")
    proposal = InvestigationProposal(
        payment_id="PAY_051",
        proposed_customer="CUS_X051",
        invoice_ids=["INV_X051A", "INV_X051B"],
        credit_ids=[],
        semantic_claims=[
            SemanticClaim(
                claim_id="CLAIM_001",
                claim="The remittance names both selected invoices.",
                evidence_ids=["EMAIL_X051"],
            )
        ],
        evidence_ids=["EMAIL_X051", "CUS_X051"],
        unresolved_questions=[],
    )
    investigator = StubInvestigator({"PAY_051": proposal})

    result = process_payment("PAY_051", dataset, investigator)

    assert result.baseline.status == "unresolved"
    assert result.decision.decision == "resolved"
    assert result.sufficiency is not None
    assert result.sufficiency.evidence_disambiguates_alternatives is True


def test_pipeline_abstains_on_same_amount_ambiguity():
    dataset = load_dataset(REPO_ROOT / "data")
    proposal = InvestigationProposal(
        payment_id="PAY_052",
        proposed_customer="CUS_X052",
        invoice_ids=["INV_X052A"],
        credit_ids=[],
        semantic_claims=[],
        evidence_ids=["CUS_X052"],
        unresolved_questions=["Two equal-value invoices are open."],
    )
    investigator = StubInvestigator({"PAY_052": proposal})

    result = process_payment("PAY_052", dataset, investigator)

    assert result.decision.decision == "human_review"
    assert result.sufficiency is not None
    assert result.sufficiency.abstention_reason == "multiple_financially_valid_explanations"
