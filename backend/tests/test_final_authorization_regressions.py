from datetime import date
from decimal import Decimal

import pytest

from app.models import (
    CandidateBundle,
    Credit,
    Customer,
    InvestigationProposal,
    Invoice,
    Payment,
    RemittanceEmail,
)
from app.services.alternative_finder import find_valid_alternatives
from app.services.baseline_matcher import baseline_match
from app.services.decision_artifacts import build_counterfactuals
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.evidence_sufficiency import _evidence_matrix
from app.services.pipeline import process_payment
from app.services.proof_engine import verify_candidate
from app.utils.loaders import Dataset


def _invoice(invoice_id: str, amount: str = "100.00") -> Invoice:
    return Invoice(
        invoice_id=invoice_id,
        customer_id="CUS_AUTH",
        amount=Decimal(amount),
        currency="USD",
        issue_date=date(2026, 8, 1),
        due_date=date(2026, 8, 31),
        description=f"Authorization regression {invoice_id}",
    )


def _credit(credit_id: str, invoice_id: str, amount: str) -> Credit:
    return Credit(
        credit_id=credit_id,
        customer_id="CUS_AUTH",
        invoice_id=invoice_id,
        amount=Decimal(amount),
        currency="USD",
        reason="Authorization regression credit",
    )


def _bundle(
    *,
    payer_name: str = "Treasury Bank",
    amount: str = "100.00",
    bank_reference: str = "WIRE-AUTH",
    remittance_reference: str = "",
    email_body: str = "",
    known_payers=None,
    invoices=None,
    credits=None,
) -> CandidateBundle:
    return CandidateBundle(
        payment=Payment(
            payment_id="PAY_AUTH",
            date=date(2026, 8, 31),
            amount=Decimal(amount),
            currency="USD",
            payer_name=payer_name,
            bank_reference=bank_reference,
            remittance_reference=remittance_reference,
        ),
        candidate_customers=[
            Customer(
                customer_id="CUS_AUTH",
                legal_name="Acme Corp",
                known_payers=list(known_payers or []),
            )
        ],
        candidate_invoices=list(invoices or [_invoice("INV_AUTH")]),
        candidate_credits=list(credits or []),
        candidate_emails=(
            [
                RemittanceEmail(
                    email_id="EMAIL_AUTH",
                    sender="ar@acme.example",
                    customer_id="CUS_AUTH",
                    date=date(2026, 8, 30),
                    subject="Payment PAY_AUTH",
                    body=email_body,
                )
            ]
            if email_body
            else []
        ),
    )


def _proposal(
    *,
    invoice_ids=None,
    credit_ids=None,
    cite_email: bool = True,
) -> InvestigationProposal:
    invoice_ids = list(invoice_ids or ["INV_AUTH"])
    credit_ids = list(credit_ids or [])
    evidence_ids = ["CUS_AUTH", *invoice_ids, *credit_ids]
    if cite_email:
        evidence_ids.append("EMAIL_AUTH")
    return InvestigationProposal(
        payment_id="PAY_AUTH",
        proposed_customer="CUS_AUTH",
        invoice_ids=invoice_ids,
        credit_ids=credit_ids,
        evidence_ids=evidence_ids,
    )


def _sufficiency(bundle: CandidateBundle, proposal: InvestigationProposal):
    proof = verify_candidate(bundle, proposal)
    result = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        find_valid_alternatives(bundle),
    )
    return proof, result


class _StaticInvestigator:
    def __init__(self, proposal: InvestigationProposal):
        self.proposal = proposal

    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        return self.proposal


def _dataset(bundle: CandidateBundle) -> Dataset:
    return Dataset(
        payments=[bundle.payment],
        invoices=bundle.candidate_invoices,
        customers=bundle.candidate_customers,
        credits=bundle.candidate_credits,
        emails=bundle.candidate_emails,
    )


def test_relationship_email_must_name_actual_payer_and_customer():
    bundle = _bundle(
        payer_name="Attacker Bank",
        email_body="Trusted Treasury Bank paid on behalf of Acme Corp for INV_AUTH.",
    )
    proposal = _proposal()

    proof, sufficiency = _sufficiency(bundle, proposal)
    result = process_payment("PAY_AUTH", _dataset(bundle), _StaticInvestigator(proposal))

    assert proof.entity_support is False
    assert "unsupported_entity_relationship" in proof.reason_codes
    assert sufficiency.safe_to_resolve is False
    assert result.decision.decision == "human_review"


def test_structured_obo_payer_requires_bank_component_and_customer():
    bundle = _bundle(
        payer_name="Citibank N.A. OBO Acme Corp",
        email_body=(
            "Payment PAY_AUTH was sent by Citibank N.A. on behalf of Acme Corp "
            "for INV_AUTH."
        ),
    )

    proof, sufficiency = _sufficiency(bundle, _proposal())

    assert proof.entity_support is True
    assert sufficiency.safe_to_resolve is True


def test_structured_obo_payer_rejects_different_bank_component():
    bundle = _bundle(
        payer_name="Attacker Bank OBO Acme Corp",
        email_body=(
            "Payment PAY_AUTH was sent by Citibank N.A. on behalf of Acme Corp "
            "for INV_AUTH."
        ),
    )

    proof, sufficiency = _sufficiency(bundle, _proposal())

    assert proof.entity_support is False
    assert sufficiency.safe_to_resolve is False


def test_unrelated_negation_does_not_cancel_positive_relationship_clause():
    bundle = _bundle(
        email_body=(
            "Treasury Bank paid on behalf of Acme Corp for INV_AUTH. "
            "Please do not delay processing."
        )
    )

    proof, sufficiency = _sufficiency(bundle, _proposal())

    assert proof.entity_support is True
    assert "unsupported_entity_relationship" not in proof.reason_codes
    assert sufficiency.safe_to_resolve is True


def test_direct_master_mapping_is_valid_only_without_relationship_contradiction():
    positive = _bundle(
        known_payers=["Treasury Bank"],
        email_body="Please apply PAY_AUTH to INV_AUTH. Do not delay processing.",
    )
    negative = _bundle(
        known_payers=["Treasury Bank"],
        email_body="Treasury Bank is not an authorized payer.",
    )

    positive_proof, _ = _sufficiency(positive, _proposal())
    negative_proof, negative_sufficiency = _sufficiency(negative, _proposal())

    assert positive_proof.entity_support is True
    assert negative_proof.entity_support is False
    assert negative_sufficiency.safe_to_resolve is False


def test_partial_multi_credit_instruction_cannot_resolve_full_pipeline():
    bundle = _bundle(
        amount="100.00",
        known_payers=["Treasury Bank"],
        email_body="Apply INV_MULTI after deducting CR_A and CR_B for PAY_AUTH.",
        invoices=[_invoice("INV_MULTI", "110.00")],
        credits=[
            _credit("CR_A", "INV_MULTI", "10.00"),
            _credit("CR_B", "INV_MULTI", "5.00"),
        ],
    )
    proposal = _proposal(invoice_ids=["INV_MULTI"], credit_ids=["CR_A"])

    proof, sufficiency = _sufficiency(bundle, proposal)
    baseline = baseline_match(bundle)
    result = process_payment("PAY_AUTH", _dataset(bundle), _StaticInvestigator(proposal))

    assert baseline.status == "unresolved"
    assert proof.financial_validity is True
    assert proof.credit_support is False
    assert "email_credit_reference_mismatch" in proof.reason_codes
    assert sufficiency.safe_to_resolve is False
    assert result.decision.decision == "human_review"


def test_exact_multi_credit_instruction_remains_authorizable():
    bundle = _bundle(
        amount="100.00",
        known_payers=["Treasury Bank"],
        email_body="Apply INV_MULTI after deducting CR_A and CR_B for PAY_AUTH.",
        invoices=[_invoice("INV_MULTI", "120.00")],
        credits=[
            _credit("CR_A", "INV_MULTI", "10.00"),
            _credit("CR_B", "INV_MULTI", "10.00"),
        ],
    )
    proposal = _proposal(
        invoice_ids=["INV_MULTI"],
        credit_ids=["CR_A", "CR_B"],
    )

    proof, sufficiency = _sufficiency(bundle, proposal)

    assert proof.financial_validity is True
    assert proof.credit_support is True
    assert proof.contradictions == []
    assert sufficiency.safe_to_resolve is True


@pytest.mark.parametrize(
    "payment_field",
    [
        "DO NOT APPLY INV_AUTH",
        "INV_AUTH is prohibited",
        "INV_AUTH is forbidden from use",
    ],
)
def test_negated_payment_invoice_reference_forces_review(payment_field):
    bundle = _bundle(
        known_payers=["Treasury Bank"],
        remittance_reference=payment_field,
    )
    proposal = _proposal(cite_email=False)

    proof, sufficiency = _sufficiency(bundle, proposal)
    baseline = baseline_match(bundle)
    result = process_payment("PAY_AUTH", _dataset(bundle), _StaticInvestigator(proposal))

    assert baseline.status == "unresolved"
    assert proof.financial_validity is False
    assert "negated_payment_reference" in proof.reason_codes
    assert sufficiency.safe_to_resolve is False
    assert result.decision.decision == "human_review"


def test_negated_payment_credit_reference_forces_review():
    bundle = _bundle(
        amount="90.00",
        known_payers=["Treasury Bank"],
        remittance_reference="DO NOT USE CR_AUTH",
        invoices=[_invoice("INV_AUTH", "100.00")],
        credits=[_credit("CR_AUTH", "INV_AUTH", "10.00")],
    )
    proposal = _proposal(credit_ids=["CR_AUTH"], cite_email=False)

    proof, sufficiency = _sufficiency(bundle, proposal)
    baseline = baseline_match(bundle)

    assert baseline.status == "unresolved"
    assert proof.financial_validity is False
    assert "negated_payment_reference" in proof.reason_codes
    assert sufficiency.safe_to_resolve is False


def test_negated_amount_only_credit_is_not_a_positive_instruction():
    bundle = _bundle(
        amount="90.00",
        known_payers=["Treasury Bank"],
        remittance_reference="INV_AUTH CR_AUTH",
        email_body="Do not deduct the USD 10 credit for PAY_AUTH.",
        invoices=[_invoice("INV_AUTH", "100.00")],
        credits=[_credit("CR_AUTH", "INV_AUTH", "10.00")],
    )
    proposal = _proposal(credit_ids=["CR_AUTH"])

    proof, sufficiency = _sufficiency(bundle, proposal)
    baseline = baseline_match(bundle)

    assert baseline.status == "unresolved"
    assert proof.credit_support is False
    assert "prohibited_credit_amount" in proof.reason_codes
    assert sufficiency.safe_to_resolve is False


def test_positive_amount_credit_instruction_remains_supported():
    bundle = _bundle(
        amount="90.00",
        known_payers=["Treasury Bank"],
        remittance_reference="INV_AUTH CR_AUTH",
        email_body="Deduct the USD 10 credit CR_AUTH from INV_AUTH for PAY_AUTH.",
        invoices=[_invoice("INV_AUTH", "100.00")],
        credits=[_credit("CR_AUTH", "INV_AUTH", "10.00")],
    )

    proof, sufficiency = _sufficiency(bundle, _proposal(credit_ids=["CR_AUTH"]))

    assert proof.credit_support is True
    assert proof.contradictions == []
    assert sufficiency.safe_to_resolve is True


def test_single_credit_amount_cannot_authorize_multiple_equal_credits():
    bundle = _bundle(
        amount="100.00",
        known_payers=["Treasury Bank"],
        email_body="Deduct the USD 10 credit for PAY_AUTH.",
        invoices=[_invoice("INV_AUTH", "120.00")],
        credits=[
            _credit("CR_A", "INV_AUTH", "10.00"),
            _credit("CR_B", "INV_AUTH", "10.00"),
            _credit("CR_C", "INV_AUTH", "20.00"),
        ],
    )
    proposal = _proposal(credit_ids=["CR_A", "CR_B"])

    alternatives = find_valid_alternatives(bundle)
    proposal_allocation = next(
        allocation
        for allocation in alternatives
        if set(allocation.credit_ids) == {"CR_A", "CR_B"}
    )
    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        alternatives,
    )
    proposal_row = next(
        row
        for row in sufficiency.evidence_alternative_matrix
        if row.evidence_id == "EMAIL_AUTH"
        and row.allocation_id == proposal_allocation.allocation_id
    )

    assert proof.financial_validity is True
    assert proof.contradictions == []
    assert proposal_row.relationship != "supports"
    assert sufficiency.evidence_disambiguates_alternatives is False
    assert sufficiency.safe_to_resolve is False


def test_payment_remittance_support_is_visible_in_evidence_matrix():
    bundle = _bundle(
        known_payers=["Treasury Bank"],
        remittance_reference="INV_A",
        invoices=[_invoice("INV_A"), _invoice("INV_B")],
    )
    proposal = _proposal(invoice_ids=["INV_A"], cite_email=False)

    proof, sufficiency = _sufficiency(bundle, proposal)
    payment_rows = {
        row.allocation_id: row.relationship
        for row in sufficiency.evidence_alternative_matrix
        if row.evidence_id == "PAY_AUTH"
    }

    assert proof.financial_validity is True
    assert sufficiency.evidence_disambiguates_alternatives is True
    assert sufficiency.chosen_proposal_supported is True
    assert payment_rows == {"ALT_001": "supports", "ALT_002": "irrelevant"}
    assert "PAY_AUTH" in sufficiency.uniquely_distinguishing_evidence
    assert sufficiency.safe_to_resolve is True

    counterfactuals = build_counterfactuals(
        bundle,
        proposal,
        find_valid_alternatives(bundle),
        sufficiency,
    )
    payment_counterfactual = next(
        row for row in counterfactuals if row.evidence_id == "PAY_AUTH"
    )
    assert payment_counterfactual.decision_critical is True
    assert payment_counterfactual.decision_without_evidence == "human_review"


def test_evidence_matrix_marks_prohibited_credit_amount_as_contradiction():
    bundle = _bundle(
        amount="90.00",
        remittance_reference="INV_AUTH CR_AUTH",
        email_body="Do not deduct the USD 10 credit for PAY_AUTH.",
        invoices=[_invoice("INV_AUTH", "100.00")],
        credits=[_credit("CR_AUTH", "INV_AUTH", "10.00")],
    )
    proposal = _proposal(credit_ids=["CR_AUTH"])
    rows = _evidence_matrix(bundle, proposal, find_valid_alternatives(bundle))
    email_rows = [row for row in rows if row.evidence_id == "EMAIL_AUTH"]
    assert email_rows and all(row.relationship == "contradicts" for row in email_rows)


def test_cross_customer_email_cannot_support_allocation():
    bundle = CandidateBundle(
        payment=Payment(
            payment_id="PAY_AUTH",
            date=date(2026, 8, 31),
            amount=Decimal("100.00"),
            currency="USD",
            payer_name="Treasury Bank",
            bank_reference="WIRE-AUTH",
            remittance_reference="",
        ),
        candidate_customers=[
            Customer(customer_id="CUS_A", legal_name="Alpha Corp"),
            Customer(
                customer_id="CUS_B",
                legal_name="Beta Corp",
                known_payers=["Treasury Bank"],
            ),
        ],
        candidate_invoices=[
            _invoice("INV_A").model_copy(update={"customer_id": "CUS_A"}),
            _invoice("INV_B").model_copy(update={"customer_id": "CUS_B"}),
        ],
        candidate_emails=[
            RemittanceEmail(
                email_id="EMAIL_A",
                sender="ar@alpha.example",
                customer_id="CUS_A",
                date=date(2026, 8, 30),
                subject="Payment PAY_AUTH",
                body="Apply PAY_AUTH to INV_B.",
            )
        ],
    )
    proposal = InvestigationProposal(
        payment_id="PAY_AUTH",
        proposed_customer="CUS_B",
        invoice_ids=["INV_B"],
        evidence_ids=["CUS_B", "INV_B", "EMAIL_A"],
    )
    alternatives = find_valid_alternatives(bundle)
    proof = verify_candidate(bundle, proposal)
    sufficiency = evaluate_evidence_sufficiency(
        bundle,
        proposal,
        proof,
        alternatives,
    )
    email_row = next(
        row
        for row in sufficiency.evidence_alternative_matrix
        if row.evidence_id == "EMAIL_A" and row.allocation_id == "ALT_002"
    )

    assert proof.financial_validity is True
    assert proof.entity_support is True
    assert email_row.relationship != "supports"
    assert sufficiency.evidence_disambiguates_alternatives is False
    assert sufficiency.safe_to_resolve is False


def test_untrusted_email_cannot_disambiguate_financial_alternatives():
    bundle = _bundle(
        known_payers=["Treasury Bank"],
        email_body="Apply PAY_AUTH to INV_A.",
        invoices=[_invoice("INV_A"), _invoice("INV_B")],
    )
    bundle.candidate_emails[0].sender = "attacker@evil.example"
    proposal = _proposal(invoice_ids=["INV_A"])

    proof, sufficiency = _sufficiency(bundle, proposal)
    email_rows = [
        row
        for row in sufficiency.evidence_alternative_matrix
        if row.evidence_id == "EMAIL_AUTH"
    ]

    assert proof.financial_validity is True
    assert proof.entity_support is True
    assert email_rows and all(row.relationship != "supports" for row in email_rows)
    assert sufficiency.evidence_disambiguates_alternatives is False
    assert sufficiency.safe_to_resolve is False


@pytest.mark.parametrize(
    "state_phrase",
    [
        "already paid",
        "settled",
        "closed",
        "cancelled",
        "disputed",
        "previously allocated",
    ],
)
def test_noncurrent_invoice_never_disambiguates_or_authorizes(state_phrase):
    bundle = _bundle(
        known_payers=["Treasury Bank"],
        email_body=f"INV_A was {state_phrase} for PAY_AUTH.",
        invoices=[_invoice("INV_A"), _invoice("INV_B")],
    )
    proposal = _proposal(invoice_ids=["INV_A"])

    proof, sufficiency = _sufficiency(bundle, proposal)

    assert "prohibited_invoice_reference" in proof.reason_codes
    assert proof.contradictions
    assert sufficiency.evidence_disambiguates_alternatives is False
    assert sufficiency.safe_to_resolve is False


def test_noncurrent_invoice_selected_by_investigator_stays_human_review():
    bundle = _bundle(
        known_payers=["Treasury Bank"],
        email_body="INV_A was already paid for PAY_AUTH. Apply this receipt to INV_B.",
        invoices=[_invoice("INV_A"), _invoice("INV_B")],
    )
    proposal = _proposal(invoice_ids=["INV_A"])

    result = process_payment("PAY_AUTH", _dataset(bundle), _StaticInvestigator(proposal))

    assert result.baseline.status == "unresolved"
    assert result.decision.decision == "human_review"
    assert result.sufficiency is not None
    assert result.sufficiency.safe_to_resolve is False
