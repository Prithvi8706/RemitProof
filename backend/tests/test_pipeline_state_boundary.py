from dataclasses import replace
from pathlib import Path

import pytest

from app.models import InvestigationProposal
from app.services.pipeline import process_payment
from app.utils.loaders import load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]


class NeverCalledInvestigator:
    def investigate(self, bundle):
        raise AssertionError("non-unmatched payments must not reach the investigator")


class RecordingInvestigator:
    def __init__(self):
        self.calls = []

    def investigate(self, bundle):
        self.calls.append(bundle.payment.payment_id)
        return InvestigationProposal(
            payment_id=bundle.payment.payment_id,
            proposed_customer="CUS_X051",
            invoice_ids=["INV_X051A", "INV_X051B"],
            credit_ids=[],
            evidence_ids=["EMAIL_X051", "CUS_X051"],
            unresolved_questions=[],
        )


def _dataset_with_payment_status(status: str):
    dataset = load_dataset(REPO_ROOT / "data")
    payments = [
        payment.model_copy(update={"status": status})
        if payment.payment_id == "PAY_001"
        else payment
        for payment in dataset.payments
    ]
    return replace(dataset, payments=payments)


@pytest.mark.parametrize("status", ["matched", "reconciled"])
def test_non_unmatched_payment_status_stays_in_human_review(status):
    result = process_payment(
        "PAY_001",
        _dataset_with_payment_status(status),
        NeverCalledInvestigator(),
    )

    assert result.baseline.status == "unresolved"
    assert result.baseline.reason == "payment_not_unmatched"
    assert result.decision.decision == "human_review"
    assert result.decision.reason == (
        f"Payment status is '{status}'; AI investigation is only allowed for unmatched payments."
    )
    assert result.decision.proof == {
        "payment_status": status,
        "baseline_reason": "payment_not_unmatched",
        "candidate_count": 0,
        "investigator_skipped": True,
    }
    assert result.proposal is None


def test_unmatched_payment_keeps_normal_deterministic_match_path():
    investigator = NeverCalledInvestigator()

    result = process_payment("PAY_001", load_dataset(REPO_ROOT / "data"), investigator)

    assert result.baseline.status == "matched"
    assert result.decision.decision == "matched_normally"


def test_unmatched_unresolved_payment_still_reaches_investigator():
    investigator = RecordingInvestigator()

    result = process_payment("PAY_051", load_dataset(REPO_ROOT / "data"), investigator)

    assert result.baseline.status == "unresolved"
    assert investigator.calls == ["PAY_051"]
