from pathlib import Path

from app.services.baseline_matcher import baseline_match
from app.services.candidate_retriever import retrieve_candidates
from app.utils.loaders import load_dataset, load_ground_truth


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_generated_dataset_has_frozen_composition():
    dataset = load_dataset(REPO_ROOT / "data")
    truth = load_ground_truth(REPO_ROOT / "data")

    assert len(dataset.payments) == 80
    assert len(truth) == 80
    assert sum(not row["is_exception"] for row in truth) == 50
    assert sum(row["is_exception"] for row in truth) == 30
    assert sum(row["split"] == "dev" for row in truth) == 20
    assert sum(row["split"] == "benchmark" for row in truth) == 60
    assert all(row["independent_held_out"] is False for row in truth)
    assert all(
        row["partition_label"] == "synthetic benchmark/regression partition"
        for row in truth
        if row["split"] == "benchmark"
    )


def test_candidate_retrieval_keeps_correct_records_without_ground_truth_access():
    dataset = load_dataset(REPO_ROOT / "data")
    truth_by_payment = {
        row["payment_id"]: row for row in load_ground_truth(REPO_ROOT / "data")
    }

    for payment in dataset.payments:
        truth = truth_by_payment[payment.payment_id]
        candidates = retrieve_candidates(payment, dataset)
        candidate_ids = {
            *(customer.customer_id for customer in candidates.candidate_customers),
            *(invoice.invoice_id for invoice in candidates.candidate_invoices),
            *(credit.credit_id for credit in candidates.candidate_credits),
            *(email.email_id for email in candidates.candidate_emails),
        }
        expected_ids = set(truth["required_retrieval_ids"])

        assert expected_ids.issubset(candidate_ids), (
            payment.payment_id,
            sorted(expected_ids - candidate_ids),
        )
        assert len(candidates.candidate_customers) <= 3
        assert len(candidates.candidate_invoices) <= 8
        assert len(candidates.candidate_credits) <= 3
        assert len(candidates.candidate_emails) <= 4


def test_abstention_retrieval_truth_includes_conflicting_financial_records():
    truth_by_payment = {
        row["payment_id"]: row for row in load_ground_truth(REPO_ROOT / "data")
    }

    truth = truth_by_payment["PAY_069"]

    assert set(truth["required_retrieval_ids"]) == {
        "CUS_X069",
        "INV_X069A",
        "CR_X069A",
        "EMAIL_X069",
    }


def test_conventional_layer_resolves_exactly_the_easy_fifty():
    dataset = load_dataset(REPO_ROOT / "data")
    truth_by_payment = {
        row["payment_id"]: row for row in load_ground_truth(REPO_ROOT / "data")
    }
    matched = []

    for payment in dataset.payments:
        candidates = retrieve_candidates(payment, dataset)
        result = baseline_match(candidates)
        if result.status == "matched":
            matched.append(payment.payment_id)
            assert truth_by_payment[payment.payment_id]["is_exception"] is False

    assert len(matched) == 50
