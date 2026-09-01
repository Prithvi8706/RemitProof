import json

import pytest

from app.services.ai_investigator import InvestigatorError, OllamaInvestigator


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.payload


@pytest.mark.parametrize(
    "response_payload",
    [
        [],
        "not-an-envelope",
        {"status": "success"},
        {"message": {"content": ["not a string"]}},
        {"message": {"content": None}},
    ],
)
def test_malformed_ollama_envelopes_fail_through_investigator_error(
    monkeypatch, bundle_factory, response_payload
):
    calls = []

    def fake_urlopen(call, timeout):
        calls.append((call, timeout))
        return FakeResponse(response_payload)

    monkeypatch.setattr("app.services.ai_investigator.request.urlopen", fake_urlopen)
    investigator = OllamaInvestigator(host="http://ollama.test", timeout_seconds=1)

    with pytest.raises(InvestigatorError):
        investigator.investigate(bundle_factory("SPIKE_01"))

    assert len(calls) == 1


def test_valid_ollama_envelope_still_returns_proposal(monkeypatch, bundle_factory):
    response_payload = {
        "message": {
            "content": json.dumps(
                {
                    "payment_id": "PAY_S01",
                    "proposed_customer": "CUS_S01",
                    "invoice_ids": ["INV_S01A"],
                    "credit_ids": [],
                    "semantic_claims": [],
                    "evidence_ids": ["CUS_S01"],
                    "unresolved_questions": [],
                }
            )
        }
    }

    monkeypatch.setattr(
        "app.services.ai_investigator.request.urlopen",
        lambda call, timeout: FakeResponse(response_payload),
    )
    investigator = OllamaInvestigator(host="http://ollama.test", timeout_seconds=1)

    proposal = investigator.investigate(bundle_factory("SPIKE_01"))

    assert proposal.payment_id == "PAY_S01"
    assert proposal.invoice_ids == ["INV_S01A"]
