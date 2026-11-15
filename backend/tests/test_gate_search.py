import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

from app.models import (
    CandidateBundle,
    Customer,
    InvestigationProposal,
    Invoice,
    Payment,
)
from app.services.ai_investigator import InvestigatorError
from app.services.pipeline import process_payment
from app.services.proof_set import build_proof_set
from app.services.search import SearchOutcome, search
from app.utils.loaders import Dataset, load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]

ACME = Customer(customer_id="CUS_1", legal_name="Acme Trading Ltd")
NEAR_AMOUNTS = ["9600.00", "9700.00", "9800.00", "9900.00", "10100.00", "10200.00", "10300.00"]

# Payments whose live replay is expected to differ from results/details.json.
# Empty until a task changes what the gate authorizes. Only a contract may add an entry.
PAYMENTS_THAT_DIFFER_FROM_THE_PUBLISHED_SNAPSHOT = [
    "PAY_052", "PAY_053", "PAY_056", "PAY_057", "PAY_058", "PAY_060", "PAY_063", "PAY_067",
    "PAY_068", "PAY_069", "PAY_071", "PAY_072", "PAY_073", "PAY_075", "PAY_077", "PAY_078",
]  # RP-109: see test_derived_citations.py for what differs in each


class Fixed:
    def __init__(self, proposal: InvestigationProposal) -> None:
        self.proposal = proposal
        self.seen: List[CandidateBundle] = []

    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        self.seen.append(bundle)
        return self.proposal


class MustNotBeCalled:
    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        raise AssertionError("the investigator must not be consulted")


class Unavailable:
    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        raise InvestigatorError("no model")


class Replay:
    def __init__(self, proposals: Dict[str, InvestigationProposal]) -> None:
        self.proposals = proposals

    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        return self.proposals[bundle.payment.payment_id]


def _invoice(invoice_id: str, amount: str, customer_id: str = "CUS_1") -> Invoice:
    return Invoice(
        invoice_id=invoice_id,
        customer_id=customer_id,
        amount=Decimal(amount),
        currency="USD",
        issue_date=date(2026, 6, 16),
        due_date=date(2026, 7, 16),
        description="Services",
    )


def _payment(payer_name: str = "Acme Trading Ltd") -> Payment:
    return Payment(
        payment_id="PAY_1",
        date=date(2026, 8, 10),
        amount=Decimal("10000.00"),
        currency="USD",
        payer_name=payer_name,
        bank_reference="BNK-1",
    )


def _ten_invoice_dataset() -> Dataset:
    invoices = (
        [_invoice("INV_010", "10000.00")]
        + [_invoice(f"INV_02{index}", amount) for index, amount in enumerate(NEAR_AMOUNTS)]
        + [_invoice("INV_090", "6000.00"), _invoice("INV_091", "4000.00")]
    )
    return Dataset(
        payments=[_payment()],
        invoices=invoices,
        customers=[ACME],
        credits=[],
        emails=[],
    )


def _proposal(invoice_ids: List[str]) -> InvestigationProposal:
    return InvestigationProposal(
        payment_id="PAY_1",
        proposed_customer="CUS_1",
        invoice_ids=invoice_ids,
        evidence_ids=["CUS_1"],
    )


def test_proposal_is_judged_against_alternatives_hidden_by_the_cap():
    result = process_payment("PAY_1", _ten_invoice_dataset(), Fixed(_proposal(["INV_010"])))
    assert result.decision.decision == "human_review"
    assert result.decision.reason == "multiple_financially_valid_explanations"
    assert [a.invoice_ids for a in result.alternatives] == [["INV_010"], ["INV_090", "INV_091"]]
    assert result.sufficiency.alternative_allocations_exist is True
    assert len(result.candidates["invoices"]) == 10


def test_the_model_still_receives_the_capped_prompt_bundle():
    investigator = Fixed(_proposal(["INV_010"]))
    process_payment("PAY_1", _ten_invoice_dataset(), investigator)
    assert len(investigator.seen) == 1
    assert len(investigator.seen[0].candidate_invoices) == 8


def test_result_alternatives_are_the_search_alternatives():
    dataset = _ten_invoice_dataset()
    result = process_payment("PAY_1", dataset, Fixed(_proposal(["INV_010"])))
    assert result.alternatives == list(search(build_proof_set(dataset.payments[0], dataset)).alternatives)


def test_unknown_search_can_never_reach_an_automatic_decision(monkeypatch):
    dataset = Dataset(
        payments=[_payment()],
        invoices=[_invoice("INV_010", "10000.00")],
        customers=[ACME],
        credits=[],
        emails=[],
    )
    assert process_payment("PAY_1", dataset, MustNotBeCalled()).decision.decision == "matched_normally"
    monkeypatch.setattr(
        "app.services.pipeline.search",
        lambda proof_set: SearchOutcome(
            status="unknown",
            complete=False,
            alternatives=(),
            detail="invoice_limit",
            incomplete_reasons=(),
        ),
    )
    decision = process_payment("PAY_1", dataset, MustNotBeCalled()).decision
    assert (decision.decision, decision.reason) == ("human_review", "search_incomplete")


def test_investigator_failure_after_the_search_reports_the_proof_bundle():
    result = process_payment("PAY_1", _ten_invoice_dataset(), Unavailable())
    assert result.decision.decision == "human_review"
    assert result.investigator_error == "no model"
    assert len(result.candidates["invoices"]) == 10


def test_legacy_replay_of_cached_proposals_reproduces_every_published_decision():
    dataset = load_dataset(REPO_ROOT / "data")
    cache = json.loads((REPO_ROOT / "results" / "proposal_cache.json").read_text(encoding="utf-8"))
    proposals = {}
    for entry in cache["entries"].values():
        proposal = InvestigationProposal.model_validate(entry["proposal"])
        proposals[proposal.payment_id] = proposal
    details = json.loads((REPO_ROOT / "results" / "details.json").read_text(encoding="utf-8"))
    published = {item["payment"]["payment_id"]: item for item in details}
    assert len(proposals) == 30
    assert len(published) == 80
    differ = []
    for payment in dataset.payments:
        result = process_payment(payment.payment_id, dataset, Replay(proposals)).model_dump(mode="json")
        expected = published[payment.payment_id]
        same = all(
            result["decision"][field] == expected["decision"][field]
            for field in ("decision", "customer_id", "invoice_ids", "credit_ids", "reason", "evidence", "proof")
        )
        same = same and result["baseline"] == expected["baseline"]
        same = same and result["alternatives"] == expected["alternatives"]
        same = same and result["sufficiency"] == expected["sufficiency"]
        if not same:
            differ.append(payment.payment_id)
    assert differ == sorted(PAYMENTS_THAT_DIFFER_FROM_THE_PUBLISHED_SNAPSHOT)
