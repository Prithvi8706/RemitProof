import json
from decimal import Decimal
from pathlib import Path
from typing import Dict

import pytest

from app.models import AlternativeAllocation, CandidateBundle, InvestigationProposal
from app.services import authorization, verifier_only
from app.services.authorization import (
    REASON_PROPOSAL_NOT_AUTHORIZABLE,
    authorizable_allocations,
    authorization_block_reason,
    names_allocation,
)
from app.services.pipeline import process_payment
from app.services.proof_set import build_proof_set
from app.services.search import search
from app.services.verifier_only import VerifierOnlyInvestigator, verifier_only_decision
from app.utils.loaders import Dataset, load_dataset
from tests.test_soundness_probes import FixedInvestigator, _proposal, f2_dataset, f4_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "backend" / "app"

READ_BODY = "Apply BNK-1 only to INV_A and INV_B."


class _Replay:
    def __init__(self, proposals: Dict[str, InvestigationProposal]) -> None:
        self.proposals = proposals

    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        return self.proposals[bundle.payment.payment_id]


def _cached_proposals() -> Dict[str, InvestigationProposal]:
    cache = json.loads((REPO_ROOT / "results" / "proposal_cache.json").read_text(encoding="utf-8"))
    proposals = {}
    for entry in cache["entries"].values():
        proposal = InvestigationProposal.model_validate(entry["proposal"])
        proposals[proposal.payment_id] = proposal
    return proposals


def _authorizable(dataset: Dataset, payment_id: str = "PAY_1"):
    proof_set = build_proof_set(dataset.payments_by_id[payment_id], dataset)
    return authorizable_allocations(proof_set.proof_bundle, search(proof_set).alternatives)


def _allocation(customer_id, invoice_ids, credit_ids=()):
    return AlternativeAllocation(
        allocation_id="ALT_X",
        customer_id=customer_id,
        invoice_ids=list(invoice_ids),
        credit_ids=list(credit_ids),
        calculated_total=Decimal("1.00"),
    )


def _assert_every_resolution_is_the_single_authorizable_allocation(dataset, investigator) -> int:
    resolved = 0
    for payment in dataset.payments:
        decision = process_payment(payment.payment_id, dataset, investigator).decision
        if decision.decision != "resolved":
            continue
        authorizable = _authorizable(dataset, payment.payment_id)
        assert len(authorizable) == 1
        allocation = authorizable[0][0]
        assert decision.customer_id == allocation.customer_id
        assert set(decision.invoice_ids) == set(allocation.invoice_ids)
        assert set(decision.credit_ids) == set(allocation.credit_ids)
        resolved += 1
    return resolved


def test_the_baseline_module_reuses_the_runtime_functions():
    assert verifier_only.canonical_proposal is authorization.canonical_proposal
    assert verifier_only.REASON_MULTIPLE_AUTHORIZABLE == "multiple_authorizable_allocations"
    assert REASON_PROPOSAL_NOT_AUTHORIZABLE == "proposal_not_authorizable"


def test_names_allocation_compares_customer_and_id_sets():
    allocation = _allocation("CUS_1", ["INV_A", "INV_B"], ["CR_1"])

    def proposal(customer_id, invoice_ids, credit_ids):
        return InvestigationProposal(
            payment_id="PAY_1",
            proposed_customer=customer_id,
            invoice_ids=invoice_ids,
            credit_ids=credit_ids,
        )

    assert names_allocation(proposal("CUS_1", ["INV_B", "INV_A"], ["CR_1"]), allocation) is True
    assert names_allocation(proposal("CUS_2", ["INV_B", "INV_A"], ["CR_1"]), allocation) is False
    assert names_allocation(proposal("CUS_1", ["INV_A"], ["CR_1"]), allocation) is False
    assert names_allocation(proposal("CUS_1", ["INV_B", "INV_A"], []), allocation) is False


def test_block_reason_for_zero_one_and_two_authorizable_allocations():
    allocation = _allocation("CUS_1", ["INV_A"])
    other = _allocation("CUS_2", ["INV_B"])
    proposal = InvestigationProposal(
        payment_id="PAY_1", proposed_customer="CUS_1", invoice_ids=["INV_A"]
    )
    assert authorization_block_reason(proposal, []) == "proposal_not_authorizable"
    assert authorization_block_reason(proposal, [(allocation, proposal)]) is None
    assert authorization_block_reason(proposal, [(other, proposal)]) == "proposal_not_authorizable"
    assert (
        authorization_block_reason(proposal, [(allocation, proposal), (other, proposal)])
        == "multiple_authorizable_allocations"
    )


def test_conflicting_customer_instructions_give_two_authorizable_allocations():
    assert [
        (allocation.customer_id, allocation.invoice_ids)
        for allocation, _ in _authorizable(f4_dataset())
    ] == [("CUS_A", ["INV_A1"]), ("CUS_B", ["INV_B1"])]


@pytest.mark.parametrize(
    "customer_id,invoice_id,email_id",
    [("CUS_A", "INV_A1", "EMAIL_A"), ("CUS_B", "INV_B1", "EMAIL_B")],
)
def test_conflicting_customer_instructions_are_reported_with_the_named_reason(
    customer_id, invoice_id, email_id
):
    proposal = _proposal(customer_id, [invoice_id], [email_id, customer_id])
    result = process_payment("PAY_1", f4_dataset(), FixedInvestigator(proposal))
    assert result.decision.decision == "human_review"
    assert result.decision.reason == "multiple_authorizable_allocations"
    assert result.sufficiency.safe_to_resolve is False
    assert result.sufficiency.abstention_reason == "multiple_authorizable_allocations"
    assert result.resolution_proof is None
    assert result.blocked_decision is not None


def test_the_outcome_does_not_depend_on_customer_order():
    dataset = f4_dataset()
    reordered = Dataset(
        payments=dataset.payments,
        invoices=list(reversed(dataset.invoices)),
        customers=list(reversed(dataset.customers)),
        credits=dataset.credits,
        emails=list(reversed(dataset.emails)),
    )
    proposal = _proposal("CUS_A", ["INV_A1"], ["EMAIL_A", "CUS_A"])
    result = process_payment("PAY_1", reordered, FixedInvestigator(proposal))
    assert result.decision.reason == "multiple_authorizable_allocations"


def test_a_single_authorizable_allocation_still_resolves():
    dataset = f2_dataset(READ_BODY)
    assert [
        (allocation.customer_id, allocation.invoice_ids)
        for allocation, _ in _authorizable(dataset)
    ] == [("CUS_1", ["INV_A", "INV_B"])]
    proposal = _proposal("CUS_1", ["INV_A", "INV_B"], ["EMAIL_1", "CUS_1"])
    result = process_payment("PAY_1", dataset, FixedInvestigator(proposal))
    assert result.decision.decision == "resolved"
    assert result.sufficiency.safe_to_resolve is True
    assert result.resolution_proof is not None


def test_a_passing_proposal_is_blocked_when_nothing_is_authorizable(monkeypatch):
    monkeypatch.setattr(
        "app.services.pipeline.authorizable_allocations",
        lambda bundle, alternatives: [],
    )
    proposal = _proposal("CUS_1", ["INV_A", "INV_B"], ["EMAIL_1", "CUS_1"])
    result = process_payment("PAY_1", f2_dataset(READ_BODY), FixedInvestigator(proposal))
    assert result.decision.decision == "human_review"
    assert result.decision.reason == "proposal_not_authorizable"
    assert result.sufficiency.safe_to_resolve is False


def test_authorization_is_not_computed_for_a_proposal_that_already_fails(monkeypatch):
    def must_not_be_called(bundle, alternatives):
        raise AssertionError("authorization must not be computed")

    monkeypatch.setattr("app.services.pipeline.authorizable_allocations", must_not_be_called)
    proposal = _proposal("CUS_1", ["INV_C"], ["EMAIL_1", "CUS_1"])
    result = process_payment("PAY_1", f2_dataset(READ_BODY), FixedInvestigator(proposal))
    assert result.decision.decision == "human_review"
    assert result.decision.reason == "contradictory_evidence"


def test_invariant_every_resolution_is_the_single_authorizable_allocation():
    dataset = load_dataset(REPO_ROOT / "data")
    assert (
        _assert_every_resolution_is_the_single_authorizable_allocation(
            dataset, _Replay(_cached_proposals())
        )
        == 12
    )
    assert (
        _assert_every_resolution_is_the_single_authorizable_allocation(
            dataset, VerifierOnlyInvestigator()
        )
        == 18
    )
    _assert_every_resolution_is_the_single_authorizable_allocation(
        f2_dataset(READ_BODY),
        FixedInvestigator(_proposal("CUS_1", ["INV_A", "INV_B"], ["EMAIL_1", "CUS_1"])),
    )
    for customer_id, invoice_id, email_id in [
        ("CUS_A", "INV_A1", "EMAIL_A"),
        ("CUS_B", "INV_B1", "EMAIL_B"),
    ]:
        _assert_every_resolution_is_the_single_authorizable_allocation(
            f4_dataset(),
            FixedInvestigator(_proposal(customer_id, [invoice_id], [email_id, customer_id])),
        )


def test_on_the_legacy_corpus_the_baseline_and_the_runtime_agree():
    dataset = load_dataset(REPO_ROOT / "data")
    for payment in dataset.payments:
        proof_set = build_proof_set(payment, dataset)
        assert verifier_only_decision(proof_set.prompt_bundle).authorizable_allocation_ids == tuple(
            alternative.allocation_id
            for alternative, _ in _authorizable(dataset, payment.payment_id)
        )


def test_authorization_module_boundaries():
    text = (APP_ROOT / "services" / "authorization.py").read_text(encoding="utf-8")
    assert "ground_truth" not in text
    assert "verifier_only" not in text
    assert "ai_investigator" not in text
