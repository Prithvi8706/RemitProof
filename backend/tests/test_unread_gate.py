import dataclasses
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import List

from app.models import (
    CandidateBundle,
    Customer,
    InvestigationProposal,
    Invoice,
    Payment,
    RemittanceEmail,
)
from app.services.baseline_matcher import baseline_match
from app.services.pipeline import process_payment
from app.services.proof_set import build_proof_set
from app.services.search import STATUS_UNKNOWN, SearchOutcome
from app.services.unread_instructions import UnreadFinding, find_unread_instructions
from app.utils.loaders import Dataset, load_dataset


ROOT = Path(__file__).resolve().parents[2]

UNREAD_BODY = (
    "This transfer settles INV_C in full. We will use a separate transfer for INV_A and "
    "INV_B next month."
)
READ_BODY = "Apply BNK-1 only to INV_A and INV_B."


class CountingInvestigator:
    def __init__(self, proposal: InvestigationProposal) -> None:
        self.proposal = proposal
        self.calls = 0

    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        self.calls += 1
        return self.proposal


def _invoice(invoice_id: str, amount: str) -> Invoice:
    return Invoice(
        invoice_id=invoice_id,
        customer_id="CUS_1",
        amount=Decimal(amount),
        currency="USD",
        issue_date=date(2026, 6, 16),
        due_date=date(2026, 7, 16),
        description="Services",
    )


def _email(email_id: str, body: str, sender: str = "ap@acmetrading.example") -> RemittanceEmail:
    return RemittanceEmail(
        email_id=email_id,
        sender=sender,
        customer_id="CUS_1",
        date=date(2026, 8, 9),
        subject="Remittance BNK-1",
        body=body,
    )


def _dataset(invoices: List[Invoice], emails: List[RemittanceEmail]) -> Dataset:
    return Dataset(
        payments=[
            Payment(
                payment_id="PAY_1",
                date=date(2026, 8, 10),
                amount=Decimal("10000.00"),
                currency="USD",
                payer_name="Acme Trading Ltd",
                bank_reference="BNK-1",
            )
        ],
        invoices=list(invoices),
        customers=[Customer(customer_id="CUS_1", legal_name="Acme Trading Ltd")],
        credits=[],
        emails=list(emails),
    )


def _proposal(invoice_ids: List[str], evidence_ids: List[str]) -> InvestigationProposal:
    return InvestigationProposal(
        payment_id="PAY_1",
        proposed_customer="CUS_1",
        invoice_ids=invoice_ids,
        evidence_ids=evidence_ids,
    )


TWO_WAY = [
    _invoice("INV_A", "6000.00"),
    _invoice("INV_B", "4000.00"),
    _invoice("INV_C", "10000.00"),
]


def test_finding_lists_emails_in_bundle_order_and_ids_sorted():
    dataset = _dataset(
        TWO_WAY,
        [
            _email("EMAIL_2", "This transfer clears INV_C."),
            _email("EMAIL_1", "INV_B and INV_A are on the statement."),
            _email("EMAIL_3", READ_BODY),
        ],
    )
    bundle = build_proof_set(dataset.payments[0], dataset).proof_bundle
    assert [email.email_id for email in bundle.candidate_emails] == [
        "EMAIL_1",
        "EMAIL_2",
        "EMAIL_3",
    ]
    finding = find_unread_instructions(bundle)
    assert finding == UnreadFinding(
        email_ids=("EMAIL_1", "EMAIL_2"), document_ids=("INV_A", "INV_B", "INV_C")
    )
    assert finding.blocks is True


def test_finding_is_empty_when_every_email_is_classified():
    dataset = _dataset(TWO_WAY, [_email("EMAIL_1", READ_BODY)])
    finding = find_unread_instructions(build_proof_set(dataset.payments[0], dataset).proof_bundle)
    assert finding == UnreadFinding(email_ids=(), document_ids=())
    assert finding.blocks is False


def test_unread_instruction_blocks_a_proposal_without_calling_the_model():
    dataset = _dataset(TWO_WAY, [_email("EMAIL_1", UNREAD_BODY)])
    investigator = CountingInvestigator(_proposal(["INV_A", "INV_B"], ["EMAIL_1", "CUS_1"]))
    result = process_payment("PAY_1", dataset, investigator)
    decision = result.decision
    assert investigator.calls == 0
    assert (decision.decision, decision.reason) == ("human_review", "unread_instruction")
    assert decision.proof == {
        "unread_email_ids": ["EMAIL_1"],
        "unread_document_ids": ["INV_C"],
        "investigator_skipped": True,
    }
    assert (result.baseline.status, result.baseline.reason) == ("unresolved", "unread_instruction")
    assert decision.invoice_ids == []
    assert result.proposal is None
    assert result.proof is None
    assert result.sufficiency is None


def test_the_same_ledger_resolves_when_the_email_is_fully_classified():
    dataset = _dataset(TWO_WAY, [_email("EMAIL_1", READ_BODY)])
    investigator = CountingInvestigator(_proposal(["INV_A", "INV_B"], ["EMAIL_1", "CUS_1"]))
    result = process_payment("PAY_1", dataset, investigator)
    assert investigator.calls == 1
    assert result.decision.decision == "resolved"
    assert result.decision.invoice_ids == ["INV_A", "INV_B"]


def test_unread_instruction_blocks_the_rules_only_match():
    dataset = _dataset(
        [_invoice("INV_A", "10000.00"), _invoice("INV_C", "7000.00")],
        [_email("EMAIL_1", "This transfer clears INV_C and the balance is a prepayment.")],
    )
    baseline = baseline_match(build_proof_set(dataset.payments[0], dataset).proof_bundle)
    assert baseline.status == "matched"
    assert baseline.matched_invoices == ["INV_A"]
    investigator = CountingInvestigator(_proposal(["INV_A"], ["CUS_1"]))
    result = process_payment("PAY_1", dataset, investigator)
    assert investigator.calls == 0
    assert (result.decision.decision, result.decision.reason) == (
        "human_review",
        "unread_instruction",
    )
    assert result.decision.proof["unread_document_ids"] == ["INV_C"]


def test_an_unread_id_that_is_in_no_allocation_still_blocks():
    dataset = _dataset(
        [_invoice("INV_A", "10000.00")],
        [_email("EMAIL_1", "This transfer clears INV_Z.")],
    )
    result = process_payment("PAY_1", dataset, CountingInvestigator(_proposal(["INV_A"], ["CUS_1"])))
    assert result.decision.decision == "human_review"
    assert result.decision.proof["unread_document_ids"] == ["INV_Z"]


def test_an_unread_email_from_an_untrusted_sender_still_blocks():
    dataset = _dataset(
        [_invoice("INV_A", "10000.00")],
        [_email("EMAIL_1", "BNK-1 clears INV_A.", sender="someone@unrelated.example")],
    )
    result = process_payment("PAY_1", dataset, CountingInvestigator(_proposal(["INV_A"], ["CUS_1"])))
    assert (result.decision.decision, result.decision.reason) == (
        "human_review",
        "unread_instruction",
    )


def test_without_emails_the_rules_only_match_is_unchanged():
    dataset = _dataset([_invoice("INV_A", "10000.00")], [])
    result = process_payment("PAY_1", dataset, CountingInvestigator(_proposal(["INV_A"], ["CUS_1"])))
    assert result.decision.decision == "matched_normally"


def test_replay_gate_is_reported_before_the_unread_gate():
    dataset = _dataset(TWO_WAY, [_email("EMAIL_1", UNREAD_BODY)])
    payment = dataset.payments[0]
    dataset = dataclasses.replace(
        dataset, payments=[payment, payment.model_copy(update={"payment_id": "PAY_2"})]
    )
    investigator = CountingInvestigator(_proposal(["INV_A", "INV_B"], ["EMAIL_1", "CUS_1"]))
    result = process_payment("PAY_1", dataset, investigator)
    assert result.baseline.reason == "duplicate_bank_transaction"


def test_incomplete_search_is_reported_before_the_unread_gate(monkeypatch):
    monkeypatch.setattr(
        "app.services.pipeline.search",
        lambda proof_set: SearchOutcome(
            status=STATUS_UNKNOWN,
            complete=False,
            alternatives=(),
            detail="invoice_limit",
            incomplete_reasons=(),
        ),
    )
    dataset = _dataset(TWO_WAY, [_email("EMAIL_1", UNREAD_BODY)])
    investigator = CountingInvestigator(_proposal(["INV_A", "INV_B"], ["EMAIL_1", "CUS_1"]))
    result = process_payment("PAY_1", dataset, investigator)
    assert result.decision.reason == "search_incomplete"


def test_no_legacy_payment_is_blocked_by_the_unread_gate():
    dataset = load_dataset(ROOT / "data")
    assert len(dataset.payments) == 80
    blocked = [
        payment.payment_id
        for payment in dataset.payments
        if find_unread_instructions(build_proof_set(payment, dataset).proof_bundle).blocks
    ]
    assert blocked == []
