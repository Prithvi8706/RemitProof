from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List, Optional

from app.models import CandidateBundle, Credit, Customer, Invoice, Payment
from app.services.alternative_finder import (
    eligible_credits,
    eligible_invoices,
    find_valid_alternatives,
)
from app.services.candidate_retriever import retrieve_candidates
from app.services.proof_set import ProofSet, build_proof_set
from app.services.search import (
    CREDIT_SEARCH_LIMIT,
    INVOICE_SEARCH_LIMIT,
    SearchOutcome,
    search,
)
from app.utils.loaders import Dataset, load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]

ACME = Customer(customer_id="CUS_1", legal_name="Acme Trading Ltd")
BOREALIS = Customer(customer_id="CUS_2", legal_name="Borealis Supply Ltd")
NEAR_AMOUNTS = ["9600.00", "9700.00", "9800.00", "9900.00", "10100.00", "10200.00", "10300.00"]


def _invoice(invoice_id: str, amount: str, customer_id: str = "CUS_1", **overrides: object) -> Invoice:
    fields = {
        "invoice_id": invoice_id,
        "customer_id": customer_id,
        "amount": Decimal(amount),
        "currency": "USD",
        "issue_date": date(2026, 6, 16),
        "due_date": date(2026, 7, 16),
        "description": "Services",
    }
    fields.update(overrides)
    return Invoice(**fields)


def _credit(
    credit_id: str,
    invoice_id: str,
    amount: str,
    customer_id: str = "CUS_1",
    **overrides: object,
) -> Credit:
    fields = {
        "credit_id": credit_id,
        "customer_id": customer_id,
        "invoice_id": invoice_id,
        "amount": Decimal(amount),
        "currency": "USD",
        "reason": "x",
    }
    fields.update(overrides)
    return Credit(**fields)


def _payment(amount: str = "10000.00") -> Payment:
    return Payment(
        payment_id="PAY_1",
        date=date(2026, 8, 10),
        amount=Decimal(amount),
        currency="USD",
        payer_name="Acme Trading Ltd",
        bank_reference="BNK-1",
    )


def _proof_set(
    invoices: Iterable[Invoice],
    credits: Iterable[Credit] = (),
    customers: Iterable[Customer] = (ACME,),
    complete: bool = True,
    reasons: Iterable[str] = (),
    payment: Optional[Payment] = None,
) -> ProofSet:
    bundle = CandidateBundle(
        payment=_payment() if payment is None else payment,
        candidate_customers=list(customers),
        candidate_invoices=list(invoices),
        candidate_credits=list(credits),
    )
    return ProofSet(
        prompt_bundle=bundle,
        proof_bundle=bundle,
        complete=complete,
        incomplete_reasons=tuple(reasons),
    )


def _keys(outcome: SearchOutcome) -> list:
    return [(a.customer_id, a.invoice_ids, a.credit_ids) for a in outcome.alternatives]


def _filler(count: int, customer_id: str = "CUS_1", prefix: str = "INV_F") -> List[Invoice]:
    return [_invoice(f"{prefix}{index:02d}", "7.00", customer_id) for index in range(count)]


def _assert_well_formed(outcome: SearchOutcome) -> None:
    unknown = outcome.status == "unknown"
    assert unknown == (not outcome.complete) == (outcome.detail is not None)
    if unknown:
        assert outcome.alternatives == ()
    if outcome.detail != "retrieval_incomplete":
        assert outcome.incomplete_reasons == ()
    if not unknown:
        if len(outcome.alternatives) == 0:
            assert outcome.status == "none"
        elif len(outcome.alternatives) == 1:
            assert outcome.status == "unique"
        else:
            assert outcome.status == "ambiguous"


def test_limits_keep_their_values():
    assert (INVOICE_SEARCH_LIMIT, CREDIT_SEARCH_LIMIT) == (16, 3)


def test_one_valid_allocation_is_unique():
    outcome = search(_proof_set([_invoice("INV_A", "10000.00"), _invoice("INV_B", "7000.00")]))
    _assert_well_formed(outcome)
    assert (outcome.status, outcome.complete, outcome.detail) == ("unique", True, None)
    assert _keys(outcome) == [("CUS_1", ["INV_A"], [])]
    assert outcome.alternatives[0].allocation_id == "ALT_001"


def test_no_valid_allocation_is_none():
    outcome = search(_proof_set([_invoice("INV_A", "9999.99")]))
    _assert_well_formed(outcome)
    assert (outcome.status, outcome.complete, outcome.alternatives) == ("none", True, ())


def test_two_valid_allocations_are_ambiguous():
    outcome = search(
        _proof_set(
            [
                _invoice("INV_A", "6000.00"),
                _invoice("INV_B", "4000.00"),
                _invoice("INV_C", "10000.00"),
            ]
        )
    )
    _assert_well_formed(outcome)
    assert (outcome.status, outcome.complete) == ("ambiguous", True)
    assert _keys(outcome) == [
        ("CUS_1", ["INV_A", "INV_B"], []),
        ("CUS_1", ["INV_C"], []),
    ]


def test_incomplete_proof_set_is_unknown_and_is_never_enumerated(monkeypatch):
    def _enumerate(bundle):
        raise AssertionError("find_valid_alternatives must not be called")

    monkeypatch.setattr("app.services.search.find_valid_alternatives", _enumerate)
    outcome = search(
        _proof_set(
            [_invoice("INV_A", "10000.00")],
            complete=False,
            reasons=("email_cap", "customer_cap"),
        )
    )
    _assert_well_formed(outcome)
    assert (outcome.status, outcome.complete, outcome.detail) == (
        "unknown",
        False,
        "retrieval_incomplete",
    )
    assert outcome.incomplete_reasons == ("email_cap", "customer_cap")


def test_seventeen_eligible_invoices_for_one_customer_are_unknown_and_never_enumerated(monkeypatch):
    def _enumerate(bundle):
        raise AssertionError("find_valid_alternatives must not be called")

    monkeypatch.setattr("app.services.search.find_valid_alternatives", _enumerate)
    outcome = search(_proof_set([_invoice("INV_A", "10000.00")] + _filler(16)))
    _assert_well_formed(outcome)
    assert (outcome.status, outcome.detail) == ("unknown", "invoice_limit")


def test_sixteen_eligible_invoices_are_searched_completely():
    outcome = search(_proof_set([_invoice("INV_A", "10000.00")] + _filler(15)))
    _assert_well_formed(outcome)
    assert (outcome.status, outcome.complete) == ("unique", True)
    assert _keys(outcome) == [("CUS_1", ["INV_A"], [])]


def test_ineligible_invoices_do_not_count_toward_the_limit():
    invoices = (
        [_invoice("INV_A", "10000.00")]
        + _filler(15)
        + [_invoice("INV_PAID", "7.00", status="paid")]
    )
    outcome = search(_proof_set(invoices))
    _assert_well_formed(outcome)
    assert (outcome.status, outcome.complete) == ("unique", True)


def test_invoice_limit_is_per_customer():
    invoices = [_invoice("INV_A", "10000.00")] + _filler(8) + _filler(9, "CUS_2", "INV_G")
    outcome = search(_proof_set(invoices, customers=(ACME, BOREALIS)))
    _assert_well_formed(outcome)
    assert (outcome.status, outcome.complete) == ("unique", True)


def test_four_eligible_credits_for_one_customer_are_unknown():
    credits = [_credit(f"CR_{index}", "INV_A", "100.00") for index in range(1, 5)]
    proof_set = _proof_set([_invoice("INV_A", "10400.00")], credits=credits)
    assert find_valid_alternatives(proof_set.proof_bundle) == []
    outcome = search(proof_set)
    _assert_well_formed(outcome)
    assert (outcome.status, outcome.detail) == ("unknown", "credit_limit")


def test_three_eligible_credits_are_searched_completely():
    credits = [_credit(f"CR_{index}", "INV_A", "100.00") for index in range(1, 4)] + [
        _credit("CR_INVALID", "INV_A", "100.00", status="invalid")
    ]
    outcome = search(_proof_set([_invoice("INV_A", "10300.00")], credits=credits))
    _assert_well_formed(outcome)
    assert (outcome.status, outcome.complete) == ("unique", True)
    assert _keys(outcome) == [("CUS_1", ["INV_A"], ["CR_1", "CR_2", "CR_3"])]


def test_cap_hidden_allocation_is_found_through_the_proof_set():
    invoices = (
        [_invoice("INV_010", "10000.00")]
        + [_invoice(f"INV_02{index}", amount) for index, amount in enumerate(NEAR_AMOUNTS)]
        + [_invoice("INV_090", "6000.00"), _invoice("INV_091", "4000.00")]
    )
    dataset = Dataset(
        payments=[_payment()],
        invoices=invoices,
        customers=[ACME],
        credits=[],
        emails=[],
    )
    outcome = search(build_proof_set(dataset.payments[0], dataset))
    _assert_well_formed(outcome)
    assert (outcome.status, outcome.complete) == ("ambiguous", True)
    assert _keys(outcome) == [
        ("CUS_1", ["INV_010"], []),
        ("CUS_1", ["INV_090", "INV_091"], []),
    ]


def test_eligibility_filters_match_the_enumerator():
    invoices = [
        _invoice("INV_OK", "10000.00"),
        _invoice("INV_PAID", "10000.00", status="paid"),
        _invoice("INV_ALLOCATED", "10000.00", allocated_payment_id="PAY_0"),
        _invoice("INV_EUR", "10000.00", currency="EUR"),
        _invoice("INV_FUTURE", "10000.00", issue_date=date(2026, 8, 11)),
    ]
    credits = [
        _credit("CR_OK", "INV_OK", "10.00"),
        _credit("CR_INVALID", "INV_OK", "10.00", status="invalid"),
        _credit("CR_USED", "INV_OK", "10.00", consumed_by_payment_id="PAY_0"),
        _credit("CR_EUR", "INV_OK", "10.00", currency="EUR"),
    ]
    bundle = _proof_set(invoices, credits=credits).proof_bundle
    assert [invoice.invoice_id for invoice in eligible_invoices(bundle)] == ["INV_OK"]
    assert [credit.credit_id for credit in eligible_credits(bundle)] == ["CR_OK"]


def test_legacy_corpus_search_is_complete_and_equals_the_prompt_bundle_enumeration():
    dataset = load_dataset(REPO_ROOT / "data")
    statuses = Counter()
    for payment in dataset.payments:
        outcome = search(build_proof_set(payment, dataset))
        _assert_well_formed(outcome)
        assert outcome.complete is True
        assert list(outcome.alternatives) == find_valid_alternatives(
            retrieve_candidates(payment, dataset)
        )
        statuses[outcome.status] += 1
    assert statuses == {"unique": 54, "ambiguous": 20, "none": 6}
