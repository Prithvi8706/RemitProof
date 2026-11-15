from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List, Optional

from app.models import (
    CandidateBundle,
    Customer,
    InvestigationProposal,
    Invoice,
    Payment,
    RemittanceEmail,
)
from app.services.ai_investigator import InvestigatorError
from app.services.alternative_finder import find_valid_alternatives
from app.services.baseline_matcher import baseline_match
from app.services.candidate_retriever import retrieve_candidates
from app.services.pipeline import process_payment
from app.utils.loaders import Dataset, load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]

ACME = Customer(customer_id="CUS_1", legal_name="Acme Trading Ltd")
NEAR_AMOUNTS = ["9600.00", "9700.00", "9800.00", "9900.00", "10100.00", "10200.00", "10300.00"]


class MustNotBeCalled:
    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        raise AssertionError("the investigator must not be consulted")


class Unavailable:
    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        raise InvestigatorError("no model")


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


def _payment(payment_id: str = "PAY_1") -> Payment:
    return Payment(
        payment_id=payment_id,
        date=date(2026, 8, 10),
        amount=Decimal("10000.00"),
        currency="USD",
        payer_name="Acme Trading Ltd",
        bank_reference="BNK-1",
    )


def _email(email_id: str) -> RemittanceEmail:
    return RemittanceEmail(
        email_id=email_id,
        sender="ap@acmetrading.example",
        customer_id="CUS_1",
        date=date(2026, 8, 9),
        subject="Remittance BNK-1",
        body="Payment advice attached.",
    )


def _dataset(
    invoices: Iterable[Invoice],
    emails: Iterable[RemittanceEmail] = (),
    payments: Optional[List[Payment]] = None,
) -> Dataset:
    return Dataset(
        payments=[_payment()] if payments is None else list(payments),
        invoices=list(invoices),
        customers=[ACME],
        credits=[],
        emails=list(emails),
    )


def _seventeen() -> List[Invoice]:
    return [_invoice("INV_A", "10000.00")] + [
        _invoice(f"INV_F{index:02d}", "7.00") for index in range(16)
    ]


def test_ledger_over_the_search_limit_goes_to_review_without_a_model_call():
    result = process_payment("PAY_1", _dataset(_seventeen()), MustNotBeCalled())
    decision = result.decision
    assert (decision.decision, decision.reason) == ("human_review", "search_incomplete")
    assert decision.proof == {
        "search_status": "unknown",
        "search_detail": "invoice_limit",
        "incomplete_reasons": [],
        "investigator_skipped": True,
    }
    assert (result.baseline.status, result.baseline.reason) == ("unresolved", "search_incomplete")
    assert decision.invoice_ids == []
    assert decision.customer_id is None
    assert len(result.candidates["invoices"]) == 8
    assert result.proposal is None
    assert result.proof is None
    assert result.sufficiency is None


def test_retrieval_cap_on_emails_goes_to_review_without_a_model_call():
    emails = [_email(f"EMAIL_{index}") for index in range(1, 6)]
    dataset = _dataset([_invoice("INV_A", "10000.00")], emails=emails)
    result = process_payment("PAY_1", dataset, MustNotBeCalled())
    decision = result.decision
    assert (decision.decision, decision.reason) == ("human_review", "search_incomplete")
    assert decision.proof["search_detail"] == "retrieval_incomplete"
    assert decision.proof["incomplete_reasons"] == ["email_cap"]


def test_sixteen_invoices_are_still_matched_by_the_rules_only_path():
    result = process_payment("PAY_1", _dataset(_seventeen()[:16]), MustNotBeCalled())
    assert result.decision.decision == "matched_normally"
    assert result.decision.invoice_ids == ["INV_A"]
    assert len(result.candidates["invoices"]) == 16


def test_competing_allocation_hidden_by_the_cap_blocks_the_rules_only_match():
    invoices = (
        [_invoice("INV_010", "10000.00")]
        + [_invoice(f"INV_02{index}", amount) for index, amount in enumerate(NEAR_AMOUNTS)]
        + [_invoice("INV_090", "6000.00"), _invoice("INV_091", "4000.00")]
    )
    result = process_payment("PAY_1", _dataset(invoices), Unavailable())
    assert result.decision.decision == "human_review"
    baseline = result.baseline
    assert (baseline.status, baseline.reason, baseline.candidate_count) == (
        "unresolved",
        "multiple_financial_allocations",
        2,
    )


def test_unique_allocation_hidden_by_the_cap_is_matched_and_reported():
    invoices = [
        _invoice(f"INV_02{index}", amount)
        for index, amount in enumerate(NEAR_AMOUNTS + ["9500.00"])
    ] + [_invoice("INV_090", "6000.00"), _invoice("INV_091", "4000.00")]
    dataset = _dataset(invoices)
    assert find_valid_alternatives(retrieve_candidates(dataset.payments[0], dataset)) == []
    result = process_payment("PAY_1", dataset, MustNotBeCalled())
    assert result.decision.decision == "matched_normally"
    assert result.decision.invoice_ids == ["INV_090", "INV_091"]
    reported = [invoice["invoice_id"] for invoice in result.candidates["invoices"]]
    assert len(reported) == 10
    assert "INV_090" in reported
    assert "INV_091" in reported


def test_replay_gate_still_runs_before_the_search():
    dataset = _dataset(_seventeen(), payments=[_payment("PAY_1"), _payment("PAY_2")])
    result = process_payment("PAY_1", dataset, MustNotBeCalled())
    assert result.decision.decision == "human_review"
    assert result.baseline.reason == "duplicate_bank_transaction"
    assert result.decision.proof["reason_code"] == "duplicate_bank_transaction"


def test_baseline_alternatives_argument_is_equivalent_to_enumerating():
    dataset = load_dataset(REPO_ROOT / "data")
    for payment in dataset.payments:
        bundle = retrieve_candidates(payment, dataset)
        assert baseline_match(bundle, alternatives=find_valid_alternatives(bundle)) == baseline_match(
            bundle
        )


def test_legacy_rules_only_results_are_unchanged():
    dataset = load_dataset(REPO_ROOT / "data")
    replayed = dataset.replayed_payment_ids
    matched = 0
    for payment in dataset.payments:
        result = process_payment(payment.payment_id, dataset, Unavailable())
        if payment.payment_id not in replayed:
            assert result.baseline == baseline_match(retrieve_candidates(payment, dataset))
        if result.decision.decision == "matched_normally":
            matched += 1
    assert matched == 50
