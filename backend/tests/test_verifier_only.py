import ast
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.models import (
    AlternativeAllocation,
    CandidateBundle,
    Credit,
    Customer,
    InvestigationProposal,
    Invoice,
    Payment,
    RemittanceEmail,
)
from app.services.pipeline import process_payment
from app.services.verifier_only import (
    REASON_MULTIPLE_AUTHORIZABLE,
    REASON_NO_ALLOCATION,
    REASON_NONE_AUTHORIZABLE,
    REASON_UNIQUE,
    VerifierOnlyInvestigator,
    canonical_proposal,
    verifier_only_decision,
)
from app.utils.loaders import Dataset, load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "backend" / "app"


def _invoice(invoice_id, amount, customer_id="CUS_1"):
    return Invoice(
        invoice_id=invoice_id,
        customer_id=customer_id,
        amount=Decimal(amount),
        currency="USD",
        issue_date=date(2026, 6, 16),
        due_date=date(2026, 7, 16),
        description="Services",
    )


def _payment(payer_name="Acme Trading Ltd", amount="10000.00"):
    return Payment(
        payment_id="PAY_1",
        date=date(2026, 8, 10),
        amount=Decimal(amount),
        currency="USD",
        bank_reference="BNK-1",
        payer_name=payer_name,
    )


def _email(email_id, sender, customer_id, body):
    return RemittanceEmail(
        email_id=email_id,
        sender=sender,
        customer_id=customer_id,
        date=date(2026, 8, 9),
        subject="Remittance BNK-1",
        body=body,
    )


ACME = Customer(customer_id="CUS_1", legal_name="Acme Trading Ltd")


def _bundle(invoices, emails=(), credits=(), customers=(ACME,), payment=None):
    return CandidateBundle(
        payment=payment if payment is not None else _payment(),
        candidate_customers=list(customers),
        candidate_invoices=list(invoices),
        candidate_credits=list(credits),
        candidate_emails=list(emails),
    )


def _conflicting_customers_bundle():
    return _bundle(
        invoices=[
            _invoice("INV_A1", "10000.00", customer_id="CUS_A"),
            _invoice("INV_B1", "10000.00", customer_id="CUS_B"),
        ],
        emails=[
            _email("EMAIL_A", "ap@acmetrading.example", "CUS_A", "Apply BNK-1 only to INV_A1."),
            _email(
                "EMAIL_B", "ap@borealissupply.example", "CUS_B", "Apply BNK-1 only to INV_B1."
            ),
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
        payment=_payment(payer_name="Global Treasury Services"),
    )


def _three_invoices():
    return [
        _invoice("INV_A", "6000.00"),
        _invoice("INV_B", "4000.00"),
        _invoice("INV_C", "10000.00"),
    ]


def _instruction_email():
    return _email(
        "EMAIL_1", "ap@acmetrading.example", "CUS_1", "Apply BNK-1 only to INV_A and INV_B."
    )


def _credit(credit_id, amount):
    return Credit(
        credit_id=credit_id,
        customer_id="CUS_1",
        invoice_id="INV_A",
        amount=Decimal(amount),
        currency="USD",
        reason="x",
    )


def test_canonical_proposal_cites_customer_then_credits_then_customer_emails():
    bundle = _bundle(
        invoices=[_invoice("INV_A", "10150.00")],
        credits=[_credit("CR_2", "100.00"), _credit("CR_1", "50.00")],
        emails=[
            _email("EMAIL_2", "ap@acmetrading.example", "CUS_1", "x"),
            _email("EMAIL_9", "ap@other.example", "CUS_9", "x"),
            _email("EMAIL_1", "ap@acmetrading.example", "CUS_1", "x"),
        ],
    )
    alternative = AlternativeAllocation(
        allocation_id="ALT_001",
        customer_id="CUS_1",
        invoice_ids=["INV_A"],
        credit_ids=["CR_2", "CR_1"],
        calculated_total=Decimal("10000.00"),
    )
    proposal = canonical_proposal(bundle, alternative)
    assert proposal == InvestigationProposal(
        payment_id="PAY_1",
        proposed_customer="CUS_1",
        invoice_ids=["INV_A"],
        credit_ids=["CR_2", "CR_1"],
        evidence_ids=["CUS_1", "CR_1", "CR_2", "EMAIL_2", "EMAIL_1"],
    )
    assert proposal.semantic_claims == []
    assert proposal.unresolved_questions == []


def test_single_valid_allocation_with_supported_payer_resolves():
    outcome = verifier_only_decision(
        _bundle([_invoice("INV_A", "10000.00"), _invoice("INV_B", "7000.00")])
    )
    assert (outcome.decision, outcome.reason) == ("resolve", REASON_UNIQUE)
    assert outcome.alternatives_considered == 1
    assert outcome.authorizable_allocation_ids == ("ALT_001",)
    assert outcome.proposal.invoice_ids == ["INV_A"]
    assert outcome.proposal.evidence_ids == ["CUS_1"]


def test_no_financially_valid_allocation_abstains():
    outcome = verifier_only_decision(_bundle([_invoice("INV_A", "9999.99")]))
    assert (outcome.decision, outcome.reason) == ("abstain", REASON_NO_ALLOCATION)
    assert outcome.alternatives_considered == 0
    assert outcome.authorizable_allocation_ids == ()
    assert outcome.proposal is None


def test_two_valid_allocations_without_evidence_abstain():
    outcome = verifier_only_decision(_bundle(_three_invoices()))
    assert (outcome.decision, outcome.reason) == ("abstain", REASON_NONE_AUTHORIZABLE)
    assert outcome.alternatives_considered == 2
    assert outcome.proposal is None


def test_trusted_instruction_selects_one_of_two_allocations():
    outcome = verifier_only_decision(
        _bundle(_three_invoices(), emails=[_instruction_email()])
    )
    assert (outcome.decision, outcome.reason) == ("resolve", REASON_UNIQUE)
    assert outcome.alternatives_considered == 2
    assert outcome.proposal.invoice_ids == ["INV_A", "INV_B"]
    assert outcome.proposal.evidence_ids == ["CUS_1", "EMAIL_1"]


def test_two_authorizable_allocations_abstain():
    outcome = verifier_only_decision(_conflicting_customers_bundle())
    assert (outcome.decision, outcome.reason) == ("abstain", REASON_MULTIPLE_AUTHORIZABLE)
    assert outcome.authorizable_allocation_ids == ("ALT_001", "ALT_002")
    assert outcome.proposal is None


def test_decision_does_not_depend_on_candidate_order():
    bundle = _conflicting_customers_bundle()
    reordered = bundle.model_copy(
        update={
            "candidate_customers": list(reversed(bundle.candidate_customers)),
            "candidate_invoices": list(reversed(bundle.candidate_invoices)),
            "candidate_emails": list(reversed(bundle.candidate_emails)),
        }
    )
    assert verifier_only_decision(reordered) == verifier_only_decision(bundle)


def test_investigator_adapter_returns_empty_proposal_on_abstention():
    dataset = Dataset(
        payments=[_payment()],
        invoices=_three_invoices(),
        customers=[ACME],
        credits=[],
        emails=[],
    )
    investigator = VerifierOnlyInvestigator()
    result = process_payment("PAY_1", dataset, investigator)
    assert investigator.outcomes["PAY_1"].decision == "abstain"
    assert result.decision.decision == "human_review"
    assert result.proposal == InvestigationProposal(payment_id="PAY_1").model_dump(mode="json")


def test_investigator_adapter_resolution_passes_the_unchanged_pipeline():
    dataset = Dataset(
        payments=[_payment()],
        invoices=_three_invoices(),
        customers=[ACME],
        credits=[],
        emails=[_instruction_email()],
    )
    investigator = VerifierOnlyInvestigator()
    result = process_payment("PAY_1", dataset, investigator)
    assert investigator.outcomes["PAY_1"].decision == "resolve"
    assert result.decision.decision == "resolved"
    assert result.decision.invoice_ids == ["INV_A", "INV_B"]


def test_legacy_corpus_outcome_counts_are_pinned():
    dataset = load_dataset(REPO_ROOT / "data")
    investigator = VerifierOnlyInvestigator()
    decisions = {
        payment.payment_id: process_payment(
            payment.payment_id, dataset, investigator
        ).decision.decision
        for payment in dataset.payments
    }
    assert Counter(decisions.values()) == {
        "matched_normally": 50,
        "resolved": 18,
        "human_review": 12,
    }
    assert len(investigator.outcomes) == 30
    assert Counter(outcome.reason for outcome in investigator.outcomes.values()) == {
        REASON_UNIQUE: 18,
        REASON_NONE_AUTHORIZABLE: 6,
        REASON_NO_ALLOCATION: 6,
    }
    for payment_id, outcome in investigator.outcomes.items():
        assert (decisions[payment_id] == "resolved") == (outcome.decision == "resolve")
        assert len(outcome.authorizable_allocation_ids) <= 1


def test_runtime_modules_do_not_import_the_baseline():
    offending = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if path.name == "verifier_only.py":
            continue
        names = []
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
                names.extend(alias.name for alias in node.names)
        if any("verifier_only" in name for name in names):
            offending.append(path.relative_to(APP_ROOT).as_posix())
    assert offending == []


def test_baseline_module_never_reads_ground_truth():
    text = (APP_ROOT / "services" / "verifier_only.py").read_text(encoding="utf-8")
    assert "ground_truth" not in text
    assert "load_ground_truth" not in text
