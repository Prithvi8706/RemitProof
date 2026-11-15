import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List, Optional

from app.models import Credit, Customer, Invoice, Payment, RemittanceEmail
from app.services.candidate_retriever import (
    CREDIT_LIMIT,
    CUSTOMER_LIMIT,
    EMAIL_LIMIT,
    INVOICE_LIMIT,
    retrieve_candidates,
    retrieve_with_trace,
)
from app.services.proof_set import build_proof_set
from app.utils.loaders import Dataset, load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]

LEGACY_BUNDLES_SHA256 = "e69d95861c5eae99b45979e3a1e8b59f10d94fc93154bc34d3b630db7e855f19"
PAYER = "Acme Trading Ltd"
ACME = Customer(customer_id="CUS_1", legal_name=PAYER)
NEAR_AMOUNTS = ["9600.00", "9700.00", "9800.00", "9900.00", "10100.00", "10200.00", "10300.00"]
KNOWN_PAYER_CUSTOMERS = tuple(
    Customer(
        customer_id=customer_id,
        legal_name=legal_name,
        known_payers=["Global Treasury Services"],
    )
    for customer_id, legal_name in (
        ("CUS_A", "Acme Trading Ltd"),
        ("CUS_B", "Borealis Supply Ltd"),
        ("CUS_C", "Cedar Works Ltd"),
        ("CUS_D", "Delta Marine Ltd"),
    )
)


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


def _payment(payer_name: str = PAYER) -> Payment:
    return Payment(
        payment_id="PAY_1",
        date=date(2026, 8, 10),
        amount=Decimal("10000.00"),
        currency="USD",
        payer_name=payer_name,
        bank_reference="BNK-1",
    )


def _email(email_id: str, customer_id: str = "CUS_1") -> RemittanceEmail:
    return RemittanceEmail(
        email_id=email_id,
        sender="ap@acmetrading.example",
        customer_id=customer_id,
        date=date(2026, 8, 9),
        subject="Remittance BNK-1",
        body="Payment advice attached.",
    )


def _ten_invoices() -> List[Invoice]:
    return (
        [_invoice("INV_010", "10000.00")]
        + [_invoice(f"INV_02{index}", amount) for index, amount in enumerate(NEAR_AMOUNTS)]
        + [_invoice("INV_090", "6000.00"), _invoice("INV_091", "4000.00")]
    )


def _dataset(
    invoices: Iterable[Invoice],
    customers: Iterable[Customer] = (ACME,),
    credits: Iterable[Credit] = (),
    emails: Iterable[RemittanceEmail] = (),
    payment: Optional[Payment] = None,
) -> Dataset:
    return Dataset(
        payments=[_payment() if payment is None else payment],
        invoices=list(invoices),
        customers=list(customers),
        credits=list(credits),
        emails=list(emails),
    )


def _legacy() -> Dataset:
    return load_dataset(REPO_ROOT / "data")


def test_retrieval_output_is_byte_stable_on_the_legacy_corpus():
    dataset = _legacy()
    digest = hashlib.sha256()
    for payment in dataset.payments:
        digest.update(
            json.dumps(
                retrieve_candidates(payment, dataset).model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
    assert digest.hexdigest() == LEGACY_BUNDLES_SHA256


def test_caps_keep_their_values():
    assert (EMAIL_LIMIT, CUSTOMER_LIMIT, INVOICE_LIMIT, CREDIT_LIMIT) == (4, 3, 8, 3)


def test_bundle_is_the_prefix_of_the_ranked_records():
    dataset = _legacy()
    for payment in dataset.payments:
        bundle, trace = retrieve_with_trace(payment, dataset)
        assert bundle == retrieve_candidates(payment, dataset)
        assert bundle.candidate_invoices == list(trace.ranked_invoices[:8])
        assert bundle.candidate_credits == list(trace.ranked_credits[:3])


def test_legacy_corpus_is_complete_and_the_invoice_cap_is_hit_often():
    dataset = _legacy()
    proof_sets = [build_proof_set(payment, dataset) for payment in dataset.payments]
    assert len(proof_sets) == 80
    for payment, proof_set in zip(dataset.payments, proof_sets):
        assert proof_set.complete is True
        assert proof_set.incomplete_reasons == ()
        assert proof_set.prompt_bundle == retrieve_candidates(payment, dataset)
    extended = [
        proof_set
        for proof_set in proof_sets
        if len(proof_set.proof_bundle.candidate_invoices)
        > len(proof_set.prompt_bundle.candidate_invoices)
    ]
    assert len(extended) == 39
    assert max(len(proof_set.proof_bundle.candidate_invoices) for proof_set in proof_sets) == 25


def test_proof_bundle_extends_the_prompt_bundle_and_keeps_its_customers_and_emails():
    dataset = _legacy()
    for payment in dataset.payments:
        proof_set = build_proof_set(payment, dataset)
        prompt = proof_set.prompt_bundle
        proof = proof_set.proof_bundle
        assert proof.payment == prompt.payment
        assert proof.candidate_customers == prompt.candidate_customers
        assert proof.candidate_emails == prompt.candidate_emails
        assert proof.candidate_invoices[: len(prompt.candidate_invoices)] == prompt.candidate_invoices
        assert proof.candidate_credits[: len(prompt.candidate_credits)] == prompt.candidate_credits


def test_cap_dropped_invoices_are_in_the_proof_bundle():
    dataset = _dataset(_ten_invoices())
    proof_set = build_proof_set(dataset.payments[0], dataset)
    assert len(proof_set.prompt_bundle.candidate_invoices) == 8
    assert [invoice.invoice_id for invoice in proof_set.proof_bundle.candidate_invoices] == [
        "INV_010",
        "INV_020",
        "INV_021",
        "INV_022",
        "INV_023",
        "INV_024",
        "INV_025",
        "INV_026",
        "INV_090",
        "INV_091",
    ]
    assert proof_set.complete is True


def test_credits_of_cap_dropped_invoices_are_in_the_proof_bundle():
    credits = [
        Credit(
            credit_id="CR_9",
            customer_id="CUS_1",
            invoice_id="INV_091",
            amount=Decimal("50.00"),
            currency="USD",
            reason="Adjustment",
        ),
        Credit(
            credit_id="CR_8",
            customer_id="CUS_1",
            invoice_id="INV_090",
            amount=Decimal("100.00"),
            currency="USD",
            reason="Adjustment",
        ),
    ]
    dataset = _dataset(_ten_invoices(), credits=credits)
    proof_set = build_proof_set(dataset.payments[0], dataset)
    assert proof_set.prompt_bundle.candidate_credits == []
    assert [credit.credit_id for credit in proof_set.proof_bundle.candidate_credits] == [
        "CR_8",
        "CR_9",
    ]


def test_every_eligible_invoice_of_a_candidate_customer_is_in_the_proof_bundle():
    for dataset in (_legacy(), _dataset(_ten_invoices())):
        for payment in dataset.payments:
            proof_bundle = build_proof_set(payment, dataset).proof_bundle
            customer_ids = {customer.customer_id for customer in proof_bundle.candidate_customers}
            proof_invoice_ids = {invoice.invoice_id for invoice in proof_bundle.candidate_invoices}
            for invoice in dataset.invoices:
                if (
                    invoice.customer_id in customer_ids
                    and invoice.status == "open"
                    and invoice.allocated_payment_id is None
                    and invoice.currency == payment.currency
                    and invoice.issue_date <= payment.date
                ):
                    assert invoice.invoice_id in proof_invoice_ids


def test_email_dropped_by_the_cap_marks_the_proof_set_incomplete():
    emails = [_email(f"EMAIL_{index}") for index in range(1, 6)]
    dataset = _dataset([_invoice("INV_010", "10000.00")], emails=emails)
    proof_set = build_proof_set(dataset.payments[0], dataset)
    assert [email.email_id for email in proof_set.prompt_bundle.candidate_emails] == [
        "EMAIL_1",
        "EMAIL_2",
        "EMAIL_3",
        "EMAIL_4",
    ]
    assert proof_set.proof_bundle.candidate_emails == proof_set.prompt_bundle.candidate_emails
    assert (proof_set.complete, proof_set.incomplete_reasons) == (False, ("email_cap",))


def test_four_emails_do_not_mark_the_proof_set_incomplete():
    emails = [_email(f"EMAIL_{index}") for index in range(1, 5)]
    dataset = _dataset([_invoice("INV_010", "10000.00")], emails=emails)
    proof_set = build_proof_set(dataset.payments[0], dataset)
    assert (proof_set.complete, proof_set.incomplete_reasons) == (True, ())


def test_strong_customer_dropped_by_the_cap_marks_the_proof_set_incomplete():
    dataset = _dataset(
        [_invoice("INV_A1", "10000.00", "CUS_A")],
        customers=KNOWN_PAYER_CUSTOMERS,
        payment=_payment("Global Treasury Services"),
    )
    proof_set = build_proof_set(dataset.payments[0], dataset)
    assert [customer.customer_id for customer in proof_set.prompt_bundle.candidate_customers] == [
        "CUS_A",
        "CUS_B",
        "CUS_C",
    ]
    assert (proof_set.complete, proof_set.incomplete_reasons) == (False, ("customer_cap",))


def test_weak_customer_dropped_by_the_cap_keeps_the_proof_set_complete():
    zenith = Customer(customer_id="CUS_Z", legal_name="Zenith Foods Ltd")
    dataset = _dataset(
        [_invoice("INV_A1", "10000.00", "CUS_A"), _invoice("INV_Z1", "9900.00", "CUS_Z")],
        customers=KNOWN_PAYER_CUSTOMERS[:3] + (zenith,),
        payment=_payment("Global Treasury Services"),
    )
    payment = dataset.payments[0]
    _, trace = retrieve_with_trace(payment, dataset)
    proof_set = build_proof_set(payment, dataset)
    assert "CUS_Z" not in [
        customer.customer_id for customer in proof_set.prompt_bundle.candidate_customers
    ]
    assert trace.dropped_strong_customer_ids == ()
    assert (proof_set.complete, proof_set.incomplete_reasons) == (True, ())
    assert "INV_Z1" in [invoice.invoice_id for invoice in proof_set.proof_bundle.candidate_invoices]


def test_both_caps_are_reported_in_a_fixed_order():
    emails = [_email(f"EMAIL_{index}", "CUS_A") for index in range(1, 6)]
    dataset = _dataset(
        [_invoice("INV_A1", "10000.00", "CUS_A")],
        customers=KNOWN_PAYER_CUSTOMERS,
        emails=emails,
        payment=_payment("Global Treasury Services"),
    )
    proof_set = build_proof_set(dataset.payments[0], dataset)
    assert proof_set.incomplete_reasons == ("email_cap", "customer_cap")
