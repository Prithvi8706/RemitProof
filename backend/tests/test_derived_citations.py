import json
from collections import Counter
from pathlib import Path
from typing import Dict

from app.models import CandidateBundle, InvestigationProposal
from app.services.alternative_finder import find_valid_alternatives
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.pipeline import process_payment
from app.services.proof_engine import verify_candidate
from app.utils.loaders import load_dataset, load_ground_truth


REPO_ROOT = Path(__file__).resolve().parents[2]

NEWLY_RESOLVED = ["PAY_057", "PAY_063", "PAY_068"]
SUFFICIENCY_ONLY = [
    "PAY_052", "PAY_053", "PAY_056", "PAY_058", "PAY_060", "PAY_067", "PAY_069",
    "PAY_071", "PAY_072", "PAY_073", "PAY_075", "PAY_077", "PAY_078",
]


class Replay:
    def __init__(self, proposals: Dict[str, InvestigationProposal]) -> None:
        self.proposals = proposals

    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        return self.proposals[bundle.payment.payment_id]


def _evaluate(bundle, customer_id, invoice_ids, credit_ids, evidence_ids):
    proposal = InvestigationProposal(
        payment_id=bundle.payment.payment_id,
        proposed_customer=customer_id,
        invoice_ids=invoice_ids,
        credit_ids=credit_ids,
        evidence_ids=evidence_ids,
        semantic_claims=[],
        unresolved_questions=[],
    )
    proof = verify_candidate(bundle, proposal)
    return evaluate_evidence_sufficiency(bundle, proposal, proof, find_valid_alternatives(bundle))


def _replay():
    dataset = load_dataset(REPO_ROOT / "data")
    cache = json.loads((REPO_ROOT / "results" / "proposal_cache.json").read_text(encoding="utf-8"))
    proposals = {}
    for entry in cache["entries"].values():
        proposal = InvestigationProposal.model_validate(entry["proposal"])
        proposals[proposal.payment_id] = proposal
    details = json.loads((REPO_ROOT / "results" / "details.json").read_text(encoding="utf-8"))
    published = {item["payment"]["payment_id"]: item for item in details}
    truth = {row["payment_id"]: row for row in load_ground_truth(REPO_ROOT / "data")}
    live = {
        payment.payment_id: process_payment(
            payment.payment_id, dataset, Replay(proposals)
        ).model_dump(mode="json")
        for payment in dataset.payments
    }
    return live, published, truth, proposals


def test_without_any_email_records_alone_do_not_disambiguate(bundle_factory):
    bundle = bundle_factory("SPIKE_05").model_copy(update={"candidate_emails": []})

    result = _evaluate(bundle, "CUS_S05", ["INV_S05A", "INV_S05B"], [], ["CUS_S05"])

    assert result.evidence_disambiguates_alternatives is False
    assert result.safe_to_resolve is False
    assert result.abstention_reason == "multiple_financially_valid_explanations"


def test_uncited_email_from_an_untrusted_sender_does_not_disambiguate(bundle_factory):
    bundle = bundle_factory("SPIKE_05")
    email = bundle.candidate_emails[0].model_copy(update={"sender": "someone@unrelated.example"})
    bundle = bundle.model_copy(update={"candidate_emails": [email]})

    result = _evaluate(bundle, "CUS_S05", ["INV_S05A", "INV_S05B"], [], ["CUS_S05"])

    assert result.evidence_disambiguates_alternatives is False
    assert result.safe_to_resolve is False


def test_uncited_email_of_another_customer_does_not_disambiguate(bundle_factory):
    bundle = bundle_factory("SPIKE_05")
    email = bundle.candidate_emails[0].model_copy(update={"customer_id": "CUS_OTHER"})
    bundle = bundle.model_copy(update={"candidate_emails": [email]})

    result = _evaluate(bundle, "CUS_S05", ["INV_S05A", "INV_S05B"], [], ["CUS_S05"])

    assert result.evidence_disambiguates_alternatives is False
    assert result.safe_to_resolve is False


def test_uncited_email_still_contradicts_a_proposal_it_does_not_name(bundle_factory):
    bundle = bundle_factory("SPIKE_05")

    result = _evaluate(bundle, "CUS_S05", ["INV_S05C", "INV_S05D"], [], ["CUS_S05"])

    assert result.safe_to_resolve is False
    assert result.abstention_reason == "contradictory_evidence"


def test_uncited_email_still_contradicts_the_wrong_credit(bundle_factory):
    bundle = bundle_factory("SPIKE_04")

    result = _evaluate(bundle, "CUS_S04", ["INV_S04A"], ["CR_S04B"], ["CUS_S04"])

    assert result.safe_to_resolve is False
    assert result.abstention_reason == "contradictory_evidence"


def test_a_cited_id_that_is_not_in_the_bundle_still_blocks(bundle_factory):
    bundle = bundle_factory("SPIKE_05")

    result = _evaluate(bundle, "CUS_S05", ["INV_S05A", "INV_S05B"], [], ["CUS_S05", "EMAIL_FAKE"])

    assert result.safe_to_resolve is False
    assert result.missing_required_evidence == ["EMAIL_FAKE"]


def test_an_empty_citation_list_still_blocks(bundle_factory):
    bundle = bundle_factory("SPIKE_05")

    result = _evaluate(bundle, "CUS_S05", ["INV_S05A", "INV_S05B"], [], [])

    assert result.safe_to_resolve is False
    assert result.missing_required_evidence == ["proposal_evidence"]


def test_legacy_replay_changes_exactly_three_decisions_and_each_equals_the_label():
    live, published, truth, _ = _replay()

    changed = sorted(
        payment_id
        for payment_id in live
        if live[payment_id]["decision"]["decision"] != published[payment_id]["decision"]["decision"]
    )

    assert changed == NEWLY_RESOLVED
    for payment_id in changed:
        before = published[payment_id]["decision"]
        after = live[payment_id]["decision"]
        assert (before["decision"], before["reason"]) == ("human_review", "missing_required_evidence")
        assert after["decision"] == "resolved"
        label = truth[payment_id]
        assert label["should_resolve"] is True
        assert after["customer_id"] == label["correct_customer"]
        assert sorted(after["invoice_ids"]) == sorted(label["correct_invoices"])
        assert sorted(after["credit_ids"]) == sorted(label["correct_credits"])


def test_legacy_replay_counts_and_no_resolution_disagrees_with_its_label():
    live, _, truth, _ = _replay()

    counts = Counter(result["decision"]["decision"] for result in live.values())

    assert dict(counts) == {"matched_normally": 50, "resolved": 12, "human_review": 18}
    for payment_id, result in live.items():
        decision = result["decision"]
        if decision["decision"] == "resolved":
            label = truth[payment_id]
            assert label["should_resolve"] is True
            assert decision["customer_id"] == label["correct_customer"]
            assert sorted(decision["invoice_ids"]) == sorted(label["correct_invoices"])
            assert sorted(decision["credit_ids"]) == sorted(label["correct_credits"])


def test_the_other_thirteen_differ_only_by_the_dropped_credit_citation_entry():
    live, published, _, proposals = _replay()

    for payment_id in SUFFICIENCY_ONLY:
        after = live[payment_id]
        before = published[payment_id]
        assert after["decision"]["decision"] == "human_review"
        assert before["decision"]["decision"] == "human_review"
        assert after["decision"]["reason"] == before["decision"]["reason"]
        assert after["decision"]["proof"] == before["decision"]["proof"]
        differing = sorted(
            key
            for key in set(after["sufficiency"]) | set(before["sufficiency"])
            if after["sufficiency"].get(key) != before["sufficiency"].get(key)
        )
        assert differing == ["missing_required_evidence"]
        proposal = proposals[payment_id]
        uncited_credits = [
            credit_id for credit_id in proposal.credit_ids if credit_id not in proposal.evidence_ids
        ]
        assert uncited_credits
        assert after["sufficiency"]["missing_required_evidence"] == [
            evidence_id
            for evidence_id in before["sufficiency"]["missing_required_evidence"]
            if evidence_id not in uncited_credits
        ]
