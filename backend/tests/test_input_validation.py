from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import Credit, InvestigationProposal, Invoice, Payment
from app.services.alternative_finder import find_valid_alternatives
from app.services.proof_engine import verify_candidate
from app.utils.normalization import extract_credit_amounts


VALID_PAYMENT = {
    "payment_id": "PAY_TEST",
    "date": date(2026, 8, 31),
    "amount": "100.00",
    "currency": "USD",
    "payer_name": "Test Customer",
}
VALID_INVOICE = {
    "invoice_id": "INV_TEST",
    "customer_id": "CUS_TEST",
    "amount": "100.00",
    "currency": "USD",
    "issue_date": date(2026, 7, 1),
    "due_date": date(2026, 8, 1),
    "description": "Test invoice",
}
VALID_CREDIT = {
    "credit_id": "CR_TEST",
    "customer_id": "CUS_TEST",
    "invoice_id": "INV_TEST",
    "amount": "10.00",
    "currency": "USD",
    "reason": "Test credit",
}


@pytest.mark.parametrize("model_cls,payload", [(Payment, VALID_PAYMENT), (Invoice, VALID_INVOICE), (Credit, VALID_CREDIT)])
@pytest.mark.parametrize(
    "bad_amount",
    [0, -1, "NaN", "Infinity", "1.001", "1e999999", "not-a-money-value"],
)
def test_models_reject_non_positive_or_malformed_amounts(model_cls, payload, bad_amount):
    with pytest.raises(ValidationError):
        model_cls.model_validate({**payload, "amount": bad_amount})


def test_proof_and_alternatives_reject_invalid_credit_amount(bundle_factory):
    bundle = bundle_factory("SPIKE_10")
    invalid_credit = bundle.candidate_credits[0].model_copy(update={"amount": Decimal("-350.00")})
    payment = bundle.payment.model_copy(update={"amount": Decimal("20350.00")})
    unsafe_bundle = bundle.model_copy(
        update={"payment": payment, "candidate_credits": [invalid_credit]}
    )
    proposal = InvestigationProposal(
        payment_id=payment.payment_id,
        proposed_customer="CUS_S10",
        invoice_ids=["INV_S10A", "INV_S10B"],
        credit_ids=["CR_S10A"],
        evidence_ids=["EMAIL_S10", "CR_S10A", "CUS_S10"],
        semantic_claims=[],
        unresolved_questions=[],
    )

    proof = verify_candidate(unsafe_bundle, proposal)

    assert proof.financial_validity is False
    assert "invalid_credit_amount" in proof.reason_codes
    assert find_valid_alternatives(unsafe_bundle) == []


def test_credit_document_id_digits_are_not_parsed_as_amounts():
    assert extract_credit_amounts("Please apply credit CR_S10A to the remittance.") == []


def test_explicit_credit_amounts_remain_detectable():
    assert extract_credit_amounts("Apply credit CR_S10A for USD 350.00.") == [Decimal("350.00")]
    assert extract_credit_amounts("Credit CR_S10A amount USD 500.00.") == [Decimal("500.00")]
