import http.client
import json
from pathlib import Path
from urllib import error

import pytest

from app.models import InvestigationProposal
from app.services.ai_investigator import InvestigatorError, OllamaInvestigator
from app.services.pipeline import process_payment
from app.utils.loaders import load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]


class FakeResponse:
    def __init__(self, body=b"", read_error=None):
        self.body = body
        self.read_error = read_error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        if self.read_error is not None:
            raise self.read_error
        return self.body


@pytest.mark.parametrize(
    ("urlopen_behavior", "expected_message"),
    [
        (ConnectionResetError("peer reset with secret-token"), "request transport failed"),
        (error.URLError("private-hostname.example"), "request transport failed"),
        (
            FakeResponse(read_error=ConnectionResetError("peer reset during read")),
            "response body read failed",
        ),
        (
            FakeResponse(read_error=http.client.IncompleteRead(b"partial")),
            "response body read failed",
        ),
        (FakeResponse(body=b"\xff\xfe\xfa"), "response body is not valid UTF-8"),
        (FakeResponse(body=b"not-json"), "response body is not valid JSON"),
        (FakeResponse(body=json.dumps([]).encode("utf-8")), "envelope must be a JSON object"),
        (FakeResponse(body="not-bytes"), "response body must be bytes"),
    ],
)
def test_investigator_normalizes_external_response_failures(
    monkeypatch, bundle_factory, urlopen_behavior, expected_message
):
    calls = []

    def fake_urlopen(call, timeout):
        calls.append((call, timeout))
        if isinstance(urlopen_behavior, BaseException):
            raise urlopen_behavior
        return urlopen_behavior

    monkeypatch.setattr("app.services.ai_investigator.request.urlopen", fake_urlopen)
    investigator = OllamaInvestigator(host="http://ollama.test", timeout_seconds=1)

    with pytest.raises(InvestigatorError, match=expected_message) as captured:
        investigator.investigate(bundle_factory("SPIKE_01"))

    assert len(calls) == 1
    assert "secret-token" not in str(captured.value)
    assert "private-hostname" not in str(captured.value)


@pytest.mark.parametrize(
    "failure",
    [
        ConnectionResetError("peer reset"),
        FakeResponse(body=b"\xff\xfe\xfa"),
    ],
)
def test_pipeline_fails_closed_for_transport_and_utf8_failures(monkeypatch, failure):
    def fake_urlopen(call, timeout):
        if isinstance(failure, BaseException):
            raise failure
        return failure

    monkeypatch.setattr("app.services.ai_investigator.request.urlopen", fake_urlopen)
    dataset = load_dataset(REPO_ROOT / "data")
    investigator = OllamaInvestigator(host="http://ollama.test", timeout_seconds=1)

    result = process_payment("PAY_051", dataset, investigator)

    assert result.decision.decision == "human_review"
    assert result.decision.reason == "Investigator unavailable; no autonomous action is allowed."
    assert result.investigator_error is not None
    assert result.proposal is None


def test_schema_validation_retry_remains_bounded_to_three_attempts(
    monkeypatch, bundle_factory
):
    calls = []
    envelope = {
        "message": {
            "content": json.dumps(
                {
                    "payment_id": "WRONG_PAYMENT",
                    "proposed_customer": None,
                    "invoice_ids": [],
                    "credit_ids": [],
                    "semantic_claims": [],
                    "evidence_ids": [],
                    "unresolved_questions": [],
                }
            )
        }
    }

    def fake_urlopen(call, timeout):
        calls.append((call, timeout))
        return FakeResponse(json.dumps(envelope).encode("utf-8"))

    monkeypatch.setattr("app.services.ai_investigator.request.urlopen", fake_urlopen)
    investigator = OllamaInvestigator(host="http://ollama.test", timeout_seconds=1)

    with pytest.raises(InvestigatorError, match="after three attempts"):
        investigator.investigate(bundle_factory("SPIKE_01"))

    assert len(calls) == 3


def test_programmer_error_after_valid_envelope_is_not_reclassified(
    monkeypatch, bundle_factory
):
    envelope = {"message": {"content": "{}"}}
    monkeypatch.setattr(
        "app.services.ai_investigator.request.urlopen",
        lambda call, timeout: FakeResponse(json.dumps(envelope).encode("utf-8")),
    )

    def fail_validation(cls, raw_content):
        raise RuntimeError("programmer defect")

    monkeypatch.setattr(
        InvestigationProposal,
        "model_validate_json",
        classmethod(fail_validation),
    )
    investigator = OllamaInvestigator(host="http://ollama.test", timeout_seconds=1)

    with pytest.raises(RuntimeError, match="programmer defect"):
        investigator.investigate(bundle_factory("SPIKE_01"))
