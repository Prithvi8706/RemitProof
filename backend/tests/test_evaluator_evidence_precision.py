from app.models import BaselineResult, Decision, ProcessingResult
from app.services.evaluator import _row_from_result


def _result_with_evidence(*evidence_ids: str) -> ProcessingResult:
    return ProcessingResult(
        payment={
            "payer_name": "Example Payer",
            "amount": "100.00",
            "currency": "USD",
        },
        baseline=BaselineResult(
            payment_id="PAY_S08",
            status="unresolved",
            reason="No deterministic match",
        ),
        decision=Decision(
            payment_id="PAY_S08",
            decision="human_review",
            reason="Evidence is insufficient",
        ),
        proposal={
            "proposed_customer": "CUS_S08",
            "invoice_ids": ["INV_S08A"],
            "credit_ids": [],
            "evidence_ids": list(evidence_ids),
        },
        candidates={
            "customers": [{"customer_id": "CUS_S08"}],
            "invoices": [{"invoice_id": "INV_S08A"}],
            "credits": [],
            "emails": [{"email_id": "EMAIL_S08"}],
        },
    )


TRUTH = {
    "split": "benchmark",
    "is_exception": True,
    "exception_class": "missing_evidence",
    "should_resolve": False,
    "correct_customer": "CUS_S08",
    "correct_invoices": ["INV_S08A"],
    "correct_credits": [],
    "required_evidence": ["CR_S08A_missing", "EMAIL_S08"],
    "required_retrieval_ids": ["CUS_S08", "INV_S08A", "EMAIL_S08"],
}


def test_evidence_precision_excludes_missing_ground_truth_markers():
    missing_only = _row_from_result(
        _result_with_evidence("CR_S08A_missing"),
        TRUTH,
    )
    missing_and_supplied = _row_from_result(
        _result_with_evidence("CR_S08A_missing", "EMAIL_S08"),
        TRUTH,
    )

    assert missing_only["evidence_cited_count"] == 1
    assert missing_only["evidence_relevant_count"] == 0
    assert missing_and_supplied["evidence_cited_count"] == 2
    assert missing_and_supplied["evidence_relevant_count"] == 1


def test_retrieval_falsification_detects_missing_safety_critical_invoice():
    result = _result_with_evidence("EMAIL_S08")
    result.candidates["invoices"] = []

    row = _row_from_result(result, TRUTH)

    assert row["retrieval_correct"] is False


def test_proposal_comparator_is_explicitly_labeled_as_an_ablation():
    row = _row_from_result(_result_with_evidence("EMAIL_S08"), TRUTH)

    assert row["comparator_mode"] == "proposal_only_forced_proposal_verifier_ablation"
