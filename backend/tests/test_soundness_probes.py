"""Soundness probes for known false-authorization paths (F2, F2 residual, F3, F4).

Each probe asserts the safe behaviour. Each fails today and is marked as a
strict expected failure, so a fix cannot land without removing its marker on
purpose and a regression cannot hide. The control tests pin every fixture, so
a probe can only fail for the reason it documents.
"""

from datetime import date
from decimal import Decimal
from typing import List

import pytest

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
from app.services.candidate_retriever import retrieve_candidates
from app.services.pipeline import process_payment
from app.utils.loaders import Dataset
from app.utils.remittance_semantics import trusted_remittance_sender_ids


class FixedInvestigator:
    def __init__(self, proposal: InvestigationProposal) -> None:
        self._proposal = proposal

    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        return self._proposal


class UnavailableInvestigator:
    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        raise InvestigatorError("probe: no model is consulted")


F2_BODIES = {
    "settles": (
        "This transfer settles INV_C in full. We will use a separate transfer "
        "for INV_A and INV_B next month."
    ),
    "clears": (
        "This transfer clears INV_C. INV_A and INV_B are booked for our next "
        "payment run."
    ),
    "covers": (
        "Today's wire covers INV_C only. Please post INV_A and INV_B to the "
        "vendor portal so we can approve them."
    ),
}
F2_RESIDUAL_BODY = "We will use a separate transfer for INV_A and INV_B next month."


def _payment(payer_name: str) -> Payment:
    return Payment(
        payment_id="PAY_1",
        date=date(2026, 8, 10),
        amount=Decimal("10000.00"),
        currency="USD",
        bank_reference="BNK-1",
        payer_name=payer_name,
    )


def _invoice(invoice_id: str, customer_id: str, amount: str) -> Invoice:
    return Invoice(
        invoice_id=invoice_id,
        customer_id=customer_id,
        amount=Decimal(amount),
        currency="USD",
        issue_date=date(2026, 6, 16),
        due_date=date(2026, 7, 16),
        description="Services",
    )


def _email(email_id: str, sender: str, customer_id: str, body: str) -> RemittanceEmail:
    return RemittanceEmail(
        email_id=email_id,
        sender=sender,
        customer_id=customer_id,
        date=date(2026, 8, 9),
        subject="Remittance BNK-1",
        body=body,
    )


def _proposal(
    customer_id: str, invoice_ids: List[str], evidence_ids: List[str]
) -> InvestigationProposal:
    return InvestigationProposal(
        payment_id="PAY_1",
        proposed_customer=customer_id,
        invoice_ids=invoice_ids,
        evidence_ids=evidence_ids,
    )


def f2_dataset(body: str) -> Dataset:
    return Dataset(
        payments=[_payment("Acme Trading Ltd")],
        invoices=[
            _invoice("INV_A", "CUS_1", "6000.00"),
            _invoice("INV_B", "CUS_1", "4000.00"),
            _invoice("INV_C", "CUS_1", "10000.00"),
        ],
        customers=[Customer(customer_id="CUS_1", legal_name="Acme Trading Ltd")],
        credits=[],
        emails=[_email("EMAIL_1", "ap@acmetrading.example", "CUS_1", body)],
    )


def f3_dataset() -> Dataset:
    amounts = [
        ("INV_010", "10000.00"),
        ("INV_020", "9600.00"),
        ("INV_021", "9700.00"),
        ("INV_022", "9800.00"),
        ("INV_023", "9900.00"),
        ("INV_024", "10100.00"),
        ("INV_025", "10200.00"),
        ("INV_026", "10300.00"),
        ("INV_090", "6000.00"),
        ("INV_091", "4000.00"),
    ]
    return Dataset(
        payments=[_payment("Acme Trading Ltd")],
        invoices=[_invoice(invoice_id, "CUS_1", amount) for invoice_id, amount in amounts],
        customers=[Customer(customer_id="CUS_1", legal_name="Acme Trading Ltd")],
        credits=[],
        emails=[],
    )


def f4_dataset() -> Dataset:
    return Dataset(
        payments=[_payment("Global Treasury Services")],
        invoices=[
            _invoice("INV_A1", "CUS_A", "10000.00"),
            _invoice("INV_B1", "CUS_B", "10000.00"),
        ],
        customers=[
            Customer(
                customer_id="CUS_A",
                legal_name="Acme Trading Ltd",
                known_payers=["Global Treasury Services"],
            ),
            Customer(
                customer_id="CUS_B",
                legal_name="Borealis Supply Ltd",
                known_payers=["Global Treasury Services"],
            ),
        ],
        credits=[],
        emails=[
            _email("EMAIL_A", "ap@acmetrading.example", "CUS_A", "Apply BNK-1 only to INV_A1."),
            _email(
                "EMAIL_B", "ap@borealissupply.example", "CUS_B", "Apply BNK-1 only to INV_B1."
            ),
        ],
    )


F2_WRONG_PROPOSAL = _proposal("CUS_1", ["INV_A", "INV_B"], ["EMAIL_1", "CUS_1"])
F3_PROPOSAL = _proposal("CUS_1", ["INV_010"], ["CUS_1"])


def _decision(dataset: Dataset, investigator) -> str:
    return process_payment("PAY_1", dataset, investigator).decision.decision


def _allocations(bundle: CandidateBundle) -> list:
    return [(item.customer_id, item.invoice_ids) for item in find_valid_alternatives(bundle)]


@pytest.mark.parametrize("body", [*F2_BODIES.values(), F2_RESIDUAL_BODY])
def test_f2_fixture_is_well_formed(body):
    dataset = f2_dataset(body)
    bundle = retrieve_candidates(dataset.payments[0], dataset)
    assert [email.email_id for email in bundle.candidate_emails] == ["EMAIL_1"]
    assert trusted_remittance_sender_ids(
        bundle.candidate_emails,
        bundle.payment,
        bundle.candidate_customers,
        customer_id="CUS_1",
    ) == {"ap@acmetrading.example"}
    assert _allocations(bundle) == [("CUS_1", ["INV_A", "INV_B"]), ("CUS_1", ["INV_C"])]


def test_f3_fixture_prompt_bundle_is_capped_and_hides_a_competing_allocation():
    dataset = f3_dataset()
    bundle = retrieve_candidates(dataset.payments[0], dataset)
    kept = {invoice.invoice_id for invoice in bundle.candidate_invoices}
    assert len(dataset.invoices) == 10
    assert len(kept) == 8
    assert {invoice.invoice_id for invoice in dataset.invoices} - kept == {
        "INV_090",
        "INV_091",
    }
    assert _allocations(bundle) == [("CUS_1", ["INV_010"])]
    full = bundle.model_copy(update={"candidate_invoices": dataset.invoices})
    assert _allocations(full) == [("CUS_1", ["INV_010"]), ("CUS_1", ["INV_090", "INV_091"])]


def test_f4_fixture_is_well_formed():
    dataset = f4_dataset()
    bundle = retrieve_candidates(dataset.payments[0], dataset)
    assert [customer.customer_id for customer in bundle.candidate_customers] == [
        "CUS_A",
        "CUS_B",
    ]
    assert [email.email_id for email in bundle.candidate_emails] == ["EMAIL_A", "EMAIL_B"]
    assert _allocations(bundle) == [("CUS_A", ["INV_A1"]), ("CUS_B", ["INV_B1"])]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="F2: unread instruction is ignored; closed by RP-108")
@pytest.mark.parametrize("name", sorted(F2_BODIES))
def test_f2_unread_instruction_must_not_authorize_the_wrong_invoices(name):
    dataset = f2_dataset(F2_BODIES[name])
    assert _decision(dataset, FixedInvestigator(F2_WRONG_PROPOSAL)) == "human_review"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="F2 residual: a fully classified sentence is misread; measured by the Phase 4 reader study")
def test_f2_residual_misread_sentence_must_not_authorize_the_wrong_invoices():
    dataset = f2_dataset(F2_RESIDUAL_BODY)
    assert _decision(dataset, FixedInvestigator(F2_WRONG_PROPOSAL)) == "human_review"


def test_f3_truncated_search_must_not_match_in_the_rules_only_path():
    assert _decision(f3_dataset(), UnavailableInvestigator()) == "human_review"


def test_f3_truncated_search_must_not_resolve_a_proposal():
    assert _decision(f3_dataset(), FixedInvestigator(F3_PROPOSAL)) == "human_review"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="F4: authorization depends on the proposed customer; closed by RP-110")
@pytest.mark.parametrize(
    "customer_id,invoice_id,email_id",
    [("CUS_A", "INV_A1", "EMAIL_A"), ("CUS_B", "INV_B1", "EMAIL_B")],
)
def test_f4_conflicting_customer_instructions_must_not_resolve(
    customer_id, invoice_id, email_id
):
    proposal = _proposal(customer_id, [invoice_id], [email_id, customer_id])
    assert _decision(f4_dataset(), FixedInvestigator(proposal)) == "human_review"
