import hashlib
import json

import pytest

from app.services.ai_investigator import InvestigatorError, OllamaInvestigator
from app.services.evaluator import CACHE_FORMAT_VERSION, CachedInvestigator
from app.utils.atomic import atomic_write_text
from scripts.evaluate import _publish_results


def _empty_proposal(bundle):
    return {
        "payment_id": bundle.payment.payment_id,
        "proposed_customer": None,
        "invoice_ids": [],
        "credit_ids": [],
        "semantic_claims": [],
        "evidence_ids": [],
        "unresolved_questions": ["Human review required."],
    }


def test_cache_identity_changes_with_host_and_generation_options(tmp_path, bundle_factory):
    bundle = bundle_factory("SPIKE_01")
    first = CachedInvestigator(
        OllamaInvestigator(
            host="http://ollama-a.test",
            generation_options={"temperature": 0, "seed": 42},
        ),
        tmp_path / "first.json",
    )
    other_host = CachedInvestigator(
        OllamaInvestigator(
            host="http://ollama-b.test",
            generation_options={"temperature": 0, "seed": 42},
        ),
        tmp_path / "second.json",
    )
    other_options = CachedInvestigator(
        OllamaInvestigator(
            host="http://ollama-a.test",
            generation_options={"temperature": 0, "seed": 7},
        ),
        tmp_path / "third.json",
    )

    assert first._key(bundle) != other_host._key(bundle)
    assert first._key(bundle) != other_options._key(bundle)
    provenance = first.delegate.public_provenance()
    assert "host" not in provenance
    assert provenance["host_sha256"] == hashlib.sha256(
        b"http://ollama-a.test"
    ).hexdigest()
    assert provenance["prompt_sha256"]
    assert provenance["proposal_schema_sha256"]
    assert provenance["investigator_version"]


def test_cache_only_mode_fails_closed_without_calling_ollama(
    tmp_path, monkeypatch, bundle_factory
):
    investigator = OllamaInvestigator(host="http://must-not-be-called.test")
    monkeypatch.setattr(
        investigator,
        "investigate",
        lambda bundle: pytest.fail("cache-only mode attempted a model call"),
    )
    cached = CachedInvestigator(
        investigator,
        tmp_path / "cache.json",
        cache_only=True,
    )

    with pytest.raises(InvestigatorError, match="cache-only evaluation refused"):
        cached.investigate(bundle_factory("SPIKE_01"))

    assert cached.statistics()["cache_misses"] == 1
    assert cached.statistics()["live_model_calls"] == 0


def test_legacy_cache_entry_is_validated_and_promoted_atomically(
    tmp_path, bundle_factory
):
    bundle = bundle_factory("SPIKE_01")
    delegate = OllamaInvestigator(host="http://offline.test")
    cache_path = tmp_path / "cache.json"
    probe = CachedInvestigator(delegate, cache_path, cache_only=True)
    cache_path.write_text(
        json.dumps({probe._legacy_key(bundle): _empty_proposal(bundle)}),
        encoding="utf-8",
    )

    cached = CachedInvestigator(delegate, cache_path, cache_only=True)
    proposal = cached.investigate(bundle)
    payload = json.loads(cache_path.read_text(encoding="utf-8"))

    assert proposal.payment_id == bundle.payment.payment_id
    assert payload["cache_format_version"] == CACHE_FORMAT_VERSION
    assert len(payload["entries"]) == 1
    assert next(iter(payload["entries"].values()))["source_identity_verified"] is False
    assert "legacy_entries" not in payload
    assert cached.statistics()["legacy_cache_promotions"] == 1
    assert cached.statistics()["unverified_legacy_cache_hits"] == 1
    assert cached.statistics()["cache_misses"] == 0


def test_unverified_legacy_fallback_requires_opt_in_and_is_not_promoted(
    tmp_path, bundle_factory
):
    bundle = bundle_factory("SPIKE_01")
    delegate = OllamaInvestigator(host="http://offline.test")
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(
        json.dumps({"old-unknown-key": _empty_proposal(bundle)}),
        encoding="utf-8",
    )

    strict = CachedInvestigator(delegate, cache_path, cache_only=True)
    with pytest.raises(InvestigatorError, match="cache-only evaluation refused"):
        strict.investigate(bundle)

    fallback = CachedInvestigator(
        delegate,
        cache_path,
        cache_only=True,
        allow_unverified_legacy=True,
    )
    proposal = fallback.investigate(bundle)
    payload = json.loads(cache_path.read_text(encoding="utf-8"))

    assert proposal.payment_id == bundle.payment.payment_id
    assert fallback.statistics()["unverified_legacy_cache_hits"] == 1
    assert fallback.statistics()["legacy_cache_promotions"] == 0
    assert payload["cache_format_version"] == CACHE_FORMAT_VERSION
    assert payload["entries"] == {}
    assert "old-unknown-key" in payload["legacy_entries"]


def test_atomic_replace_failure_preserves_previous_valid_file(
    tmp_path, monkeypatch
):
    target = tmp_path / "artifact.json"
    target.write_text('{"generation":"old"}\n', encoding="utf-8")

    def fail_replace(source, destination):
        raise OSError("simulated interrupted publication")

    monkeypatch.setattr("app.utils.atomic.os.replace", fail_replace)

    with pytest.raises(OSError, match="interrupted publication"):
        atomic_write_text(target, '{"generation":"new"}\n')

    assert target.read_text(encoding="utf-8") == '{"generation":"old"}\n'
    assert list(tmp_path.glob("*.tmp")) == []


def test_result_publication_writes_verifiable_generation_manifest(tmp_path):
    generation_id = "generation-test"
    rows = [
        {
            "payment_id": "PAY_TEST",
            "exception_class": "test",
            "decision": "human_review",
            "final_correct_resolution": False,
            "wrong_auto_resolution": False,
            "false_escalation": False,
            "evaluation_generation_id": generation_id,
        }
    ]
    details = [{"evaluation_generation_id": generation_id}]
    metrics = {
        "evaluation_generation_id": generation_id,
        "evaluation_mode": "cache_only_proposal_verifier_replay",
    }

    _publish_results(tmp_path, rows, metrics, details)

    manifest = json.loads(
        (tmp_path / "generation_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["evaluation_generation_id"] == generation_id
    for name, expected_hash in manifest["artifacts"].items():
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == expected_hash
