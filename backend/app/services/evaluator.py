import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from app.models import CandidateBundle, InvestigationProposal, ProcessingResult
from app.services.ai_investigator import InvestigatorError, OllamaInvestigator
from app.services.pipeline import process_payment
from app.utils.atomic import atomic_write_json
from app.utils.loaders import Dataset


CACHE_FORMAT_VERSION = 2
EVALUATOR_VERSION = "remitproof-evaluator-v6"
PROPOSAL_ABLATION_MODE = "proposal_only_forced_proposal_verifier_ablation"
SYNTHETIC_BENCHMARK_LABEL = (
    "synthetic benchmark/regression partition; not an independent held-out set"
)

ALTERNATIVE_SEARCH_CLASSES = {
    "detached_remittance_email",
    "same_amount_ambiguity",
    "credit_deduction",
    "multiple_allocations_email",
    "parent_entity_multi_invoice",
    "known_payer_disambiguated",
    "multi_invoice_remittance",
    "semantic_credit_reason",
    "treasury_bank_on_behalf",
    "alternative_allocation_email",
}
CONTRADICTION_CLASSES = {"conflicting_evidence"}


def _sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


class CachedInvestigator:
    """Cache proposals under a complete investigator and input identity."""

    def __init__(
        self,
        delegate: OllamaInvestigator,
        cache_path: Path,
        *,
        cache_only: bool = False,
        allow_unverified_legacy: bool = False,
    ) -> None:
        self.delegate = delegate
        self.cache_path = cache_path
        self.cache_only = cache_only
        self.allow_unverified_legacy = allow_unverified_legacy
        self.hits = 0
        self.misses = 0
        self.live_calls = 0
        self.successful_live_calls = 0
        self.legacy_promotions = 0
        self.unverified_legacy_hits = 0
        self._cache_needs_versioned_write = False
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("proposal cache must be a JSON object")
            if payload.get("cache_format_version") == CACHE_FORMAT_VERSION:
                entries = payload.get("entries")
                if not isinstance(entries, dict):
                    raise ValueError("versioned proposal cache is missing entries")
                self.cache = entries
                legacy_entries = payload.get("legacy_entries", {})
                if not isinstance(legacy_entries, dict):
                    raise ValueError("proposal cache legacy_entries must be an object")
                self.legacy_cache = legacy_entries
            else:
                # Read the original flat cache only to migrate matching entries under
                # the stronger identity. It is never treated as identity-complete.
                self.cache = {}
                self.legacy_cache = payload
                self._cache_needs_versioned_write = True
        else:
            self.cache = {}
            self.legacy_cache = {}

    def _key(self, bundle: CandidateBundle) -> str:
        payload = {
            "investigator": self.delegate.cache_identity(),
            "bundle": bundle.model_dump(mode="json"),
        }
        return _sha256_json(payload)

    def _legacy_key(self, bundle: CandidateBundle) -> str:
        return _sha256_json(
            {
                "model": self.delegate.model,
                "prompt": self.delegate.system_prompt,
                "bundle": bundle.model_dump(mode="json"),
            }
        )

    def _entry(
        self,
        proposal: InvestigationProposal,
        bundle: CandidateBundle,
        *,
        source_identity_verified: bool,
    ) -> Dict[str, object]:
        return {
            "proposal": proposal.model_dump(mode="json"),
            "investigator_identity_sha256": _sha256_json(
                self.delegate.cache_identity()
            ),
            "bundle_sha256": _sha256_json(bundle.model_dump(mode="json")),
            "source_identity_verified": source_identity_verified,
        }

    def _document(self) -> Dict[str, object]:
        document: Dict[str, object] = {
            "cache_format_version": CACHE_FORMAT_VERSION,
            "entries": self.cache,
        }
        if self.legacy_cache:
            document["legacy_entries"] = self.legacy_cache
        return document

    def _save(self) -> None:
        atomic_write_json(self.cache_path, self._document())

    def cache_sha256(self) -> str:
        return _sha256_json(self._document())

    def statistics(self) -> Dict[str, int]:
        return {
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "live_model_calls": self.live_calls,
            "successful_live_model_calls": self.successful_live_calls,
            "failed_live_model_calls": self.live_calls - self.successful_live_calls,
            "legacy_cache_promotions": self.legacy_promotions,
            "unverified_legacy_cache_hits": self.unverified_legacy_hits,
            "cache_entries": len(self.cache),
            "unverified_legacy_entries": len(self.legacy_cache),
        }

    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        key = self._key(bundle)
        cached = self.cache.get(key)
        if cached is not None:
            if not isinstance(cached, dict) or "proposal" not in cached:
                raise ValueError(f"malformed proposal cache entry: {key}")
            self.hits += 1
            if not bool(cached.get("source_identity_verified", False)):
                self.unverified_legacy_hits += 1
                if "source_identity_verified" not in cached:
                    cached["source_identity_verified"] = False
                    self._save()
            return InvestigationProposal.model_validate(cached["proposal"])

        legacy_key = self._legacy_key(bundle)
        legacy = self.legacy_cache.get(legacy_key)
        if legacy is not None:
            proposal = InvestigationProposal.model_validate(legacy)
            self.hits += 1
            self.legacy_promotions += 1
            self.unverified_legacy_hits += 1
            self.cache[key] = self._entry(
                proposal,
                bundle,
                source_identity_verified=False,
            )
            del self.legacy_cache[legacy_key]
            self._save()
            return proposal

        if self.allow_unverified_legacy:
            legacy_matches = []
            for legacy_entry in self.legacy_cache.values():
                if not isinstance(legacy_entry, dict):
                    continue
                if legacy_entry.get("payment_id") == bundle.payment.payment_id:
                    legacy_matches.append(legacy_entry)
            if len(legacy_matches) == 1:
                proposal = InvestigationProposal.model_validate(legacy_matches[0])
                self.hits += 1
                self.unverified_legacy_hits += 1
                if self._cache_needs_versioned_write:
                    self._save()
                    self._cache_needs_versioned_write = False
                return proposal
            if len(legacy_matches) > 1:
                raise ValueError(
                    "multiple unverified legacy proposals exist for payment "
                    f"{bundle.payment.payment_id}"
                )

        self.misses += 1
        if self.cache_only:
            raise InvestigatorError(
                "cache-only evaluation refused an Ollama call for "
                f"payment {bundle.payment.payment_id}"
            )
        self.live_calls += 1
        proposal = self.delegate.investigate(bundle)
        self.successful_live_calls += 1
        self.cache[key] = self._entry(
            proposal,
            bundle,
            source_identity_verified=True,
        )
        self._save()
        return proposal


def _matches_truth(
    customer_id: Optional[str],
    invoice_ids: Iterable[str],
    credit_ids: Iterable[str],
    truth: Dict[str, object],
) -> bool:
    return bool(
        truth["should_resolve"]
        and customer_id == truth["correct_customer"]
        and set(invoice_ids) == set(truth["correct_invoices"])
        and set(credit_ids) == set(truth["correct_credits"])
    )


def _row_from_result(
    result: ProcessingResult,
    truth: Dict[str, object],
) -> Dict[str, object]:
    proposal = result.proposal or {}
    baseline_resolved = result.baseline.status == "matched"
    baseline_correct = _matches_truth(
        result.baseline.customer_id,
        result.baseline.matched_invoices,
        result.baseline.matched_credits,
        truth,
    )
    llm_complete = bool(proposal.get("proposed_customer") and proposal.get("invoice_ids"))
    llm_decision = "resolve" if llm_complete else "abstain"
    llm_correct = bool(
        llm_complete
        and _matches_truth(
            proposal.get("proposed_customer"),
            proposal.get("invoice_ids", []),
            proposal.get("credit_ids", []),
            truth,
        )
    )
    final_auto = result.decision.decision in {"matched_normally", "resolved"}
    final_correct = bool(
        final_auto
        and _matches_truth(
            result.decision.customer_id,
            result.decision.invoice_ids,
            result.decision.credit_ids,
            truth,
        )
    )

    candidate_ids = {
        *(item["customer_id"] for item in result.candidates.get("customers", [])),
        *(item["invoice_id"] for item in result.candidates.get("invoices", [])),
        *(item["credit_id"] for item in result.candidates.get("credits", [])),
        *(item["email_id"] for item in result.candidates.get("emails", [])),
    }
    required_retrieval_ids = set(truth["required_retrieval_ids"])
    relevant_evidence_ids = {
        truth["correct_customer"],
        *truth["correct_invoices"],
        *truth["correct_credits"],
        *truth["required_evidence"],
    }.intersection(candidate_ids)
    cited_ids = set(proposal.get("evidence_ids", []))
    proof = result.proof
    arithmetic_correct = bool(
        (result.decision.decision == "matched_normally")
        or (result.decision.decision == "resolved" and proof and proof.financial_validity)
        or result.decision.decision == "human_review"
    )
    alternatives_expected = truth["exception_class"] in ALTERNATIVE_SEARCH_CLASSES
    alternatives_detected = len(result.alternatives) > 1
    ambiguity_expected = truth["exception_class"] == "same_amount_ambiguity"
    ambiguity_detected = bool(
        alternatives_detected
        and result.sufficiency
        and not result.sufficiency.evidence_disambiguates_alternatives
    )
    contradiction_expected = truth["exception_class"] in CONTRADICTION_CLASSES
    contradiction_detected = bool(result.proof and result.proof.contradictions)
    critical_expected = bool(truth["should_resolve"] and alternatives_expected)
    critical_detected = any(item.decision_critical for item in result.counterfactuals)

    return {
        "payment_id": result.decision.payment_id,
        "split": truth["split"],
        "is_exception": bool(truth["is_exception"]),
        "exception_class": truth["exception_class"],
        "payer": result.payment["payer_name"],
        "amount": result.payment["amount"],
        "currency": result.payment["currency"],
        "baseline_decision": "resolve" if baseline_resolved else "abstain",
        "baseline_correct_resolution": baseline_correct,
        "llm_only_decision": llm_decision,
        "llm_only_correct_resolution": llm_correct,
        "comparator_mode": PROPOSAL_ABLATION_MODE,
        "decision": result.decision.decision,
        "final_correct_resolution": final_correct,
        "expected_should_resolve": bool(truth["should_resolve"]),
        "correct_abstention": (
            result.decision.decision == "human_review" and not truth["should_resolve"]
        ),
        "false_escalation": (
            result.decision.decision == "human_review" and truth["should_resolve"]
        ),
        "wrong_auto_resolution": final_auto and not final_correct,
        "entity_correct": (
            proposal.get("proposed_customer") == truth["correct_customer"]
            if truth["is_exception"]
            else True
        ),
        "evidence_cited_count": len(cited_ids),
        "evidence_relevant_count": len(cited_ids.intersection(relevant_evidence_ids)),
        "arithmetic_correct": arithmetic_correct,
        "retrieval_correct": required_retrieval_ids.issubset(candidate_ids),
        "alternative_detection_correct": alternatives_detected == alternatives_expected,
        "ambiguity_detection_correct": ambiguity_detected == ambiguity_expected,
        "contradiction_detection_correct": contradiction_detected == contradiction_expected,
        "decision_critical_evidence_correct": critical_detected == critical_expected,
        "reason": result.decision.reason,
        "latency_ms": result.decision.latency_ms,
        "investigator_error": result.investigator_error or "",
    }


def _operational_exception_class(result: ProcessingResult) -> str:
    """Classify a case using runtime output only, never evaluation truth."""

    if result.baseline.status == "matched":
        return "matched_normally"
    if result.investigator_error:
        return "investigator_error"
    if result.decision.decision == "resolved":
        return "resolved_after_investigation"
    if result.proof and result.proof.reason_codes:
        return str(result.proof.reason_codes[0]).lower()
    if result.sufficiency and result.sufficiency.abstention_reason:
        return "evidence_review_required"
    return "unresolved_payment"


def _comparison(rows: List[Dict[str, object]], prefix: str) -> Dict[str, object]:
    if prefix == "remitproof":
        resolved = [row for row in rows if row["decision"] in {"matched_normally", "resolved"}]
        correct_key = "final_correct_resolution"
        abstained = [row for row in rows if row["decision"] == "human_review"]
    else:
        resolved = [row for row in rows if row[f"{prefix}_decision"] == "resolve"]
        correct_key = f"{prefix}_correct_resolution"
        abstained = [row for row in rows if row[f"{prefix}_decision"] == "abstain"]
    correct_resolutions = sum(bool(row[correct_key]) for row in resolved)
    comparison: Dict[str, object] = {
        "resolved": len(resolved),
        "correct_resolutions": correct_resolutions,
        "wrong_auto_resolutions": len(resolved) - correct_resolutions,
        "correct_abstentions": sum(not row["expected_should_resolve"] for row in abstained),
        "false_escalations": sum(row["expected_should_resolve"] for row in abstained),
    }
    if prefix == "llm_only":
        comparison.update(
            {
                "mode": PROPOSAL_ABLATION_MODE,
                "label": "Forced-proposal verifier ablation (proposal only)",
                "standalone_llm_system": False,
                "allows_independent_abstention": False,
            }
        )
    return comparison


def _comparison_rows(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Return truth exceptions the baseline could not resolve.

    The three-system comparison is intentionally scoped to hard exceptions. A
    truth exception that the deterministic baseline already resolves is still
    included in the overall evaluation, but it is not a comparison case.
    """

    return [
        row
        for row in rows
        if row["is_exception"] and row["baseline_decision"] == "abstain"
    ]


def _metrics_for_rows(
    rows: List[Dict[str, object]],
    elapsed_seconds: float,
    timing_scope: str = "pipeline/verifier timing; model-inference inclusion is declared by run metadata",
) -> Dict[str, object]:
    # Operational exception metrics must agree with the baseline boundary used
    # by details.json and the dashboard. A truth-labelled exception that the
    # deterministic baseline already resolves is still part of the complete
    # evaluation, but it is not an unresolved exception for the AI comparison.
    operational_exceptions = [
        row for row in rows if row["baseline_decision"] == "abstain"
    ]
    comparison_rows = _comparison_rows(rows)
    resolvable_exceptions = [
        row for row in comparison_rows if row["expected_should_resolve"]
    ]
    ambiguous_exceptions = [
        row for row in comparison_rows if not row["expected_should_resolve"]
    ]
    auto_resolved = [row for row in rows if row["decision"] in {"matched_normally", "resolved"}]
    remitproof_resolved = [row for row in rows if row["decision"] == "resolved"]
    comparison_resolved = [
        row for row in comparison_rows if row["decision"] == "resolved"
    ]
    correct_exception_resolutions = sum(
        bool(row["final_correct_resolution"]) for row in resolvable_exceptions
    )
    wrong_resolutions = sum(bool(row["wrong_auto_resolution"]) for row in rows)
    correct_abstentions = sum(
        bool(row["correct_abstention"]) for row in ambiguous_exceptions
    )
    false_escalations = sum(
        bool(row["false_escalation"]) for row in resolvable_exceptions
    )
    evidence_cited = sum(int(row["evidence_cited_count"]) for row in comparison_rows)
    evidence_relevant = sum(int(row["evidence_relevant_count"]) for row in comparison_rows)

    return {
        "total_receipts": len(rows),
        "matched_normally": sum(row["decision"] == "matched_normally" for row in rows),
        "exceptions": len(operational_exceptions),
        "resolved_by_remitproof": len(remitproof_resolved),
        "human_review": sum(row["decision"] == "human_review" for row in rows),
        "baseline_match_rate": _ratio(
            sum(row["baseline_decision"] == "resolve" for row in rows), len(rows)
        ),
        "exception_resolution_rate": _ratio(
            len(comparison_resolved), len(comparison_rows)
        ),
        # These metrics intentionally use only safely resolvable exception records.
        "resolution_accuracy": _ratio(
            correct_exception_resolutions, len(resolvable_exceptions)
        ),
        "incorrect_auto_resolution_rate": _ratio(wrong_resolutions, len(auto_resolved)),
        "correct_abstention_rate": _ratio(
            correct_abstentions, len(ambiguous_exceptions)
        ),
        "false_escalation_rate": _ratio(
            false_escalations, len(resolvable_exceptions)
        ),
        "entity_resolution_accuracy": _ratio(
            sum(bool(row["entity_correct"]) for row in comparison_rows), len(comparison_rows)
        ),
        "evidence_precision": _ratio(evidence_relevant, evidence_cited),
        "arithmetic_correctness": _ratio(
            sum(bool(row["arithmetic_correct"]) for row in rows), len(rows)
        ),
        "retrieval_accuracy": _ratio(
            sum(bool(row["retrieval_correct"]) for row in rows), len(rows)
        ),
        "alternative_detection_accuracy": _ratio(
            sum(bool(row.get("alternative_detection_correct", True)) for row in comparison_rows),
            len(comparison_rows),
        ),
        "ambiguity_detection_accuracy": _ratio(
            sum(bool(row.get("ambiguity_detection_correct", True)) for row in comparison_rows),
            len(comparison_rows),
        ),
        "contradiction_detection_accuracy": _ratio(
            sum(bool(row.get("contradiction_detection_correct", True)) for row in comparison_rows),
            len(comparison_rows),
        ),
        "decision_critical_evidence_accuracy": _ratio(
            sum(bool(row.get("decision_critical_evidence_correct", True)) for row in comparison_rows),
            len(comparison_rows),
        ),
        "throughput_per_minute": round(
            len(rows) / (elapsed_seconds / 60), 2
        ) if elapsed_seconds else 0.0,
        "mean_latency_ms": round(
            sum(int(row["latency_ms"]) for row in rows) / len(rows), 1
        ) if rows else 0.0,
        "comparison_scope": "unresolved exception records",
        "comparison_record_count": len(comparison_rows),
        "timing_scope": timing_scope,
        "comparison": {
            "baseline": _comparison(comparison_rows, "baseline"),
            "llm_only": _comparison(comparison_rows, "llm_only"),
            "remitproof": _comparison(comparison_rows, "remitproof"),
        },
    }


def evaluate_dataset(
    dataset: Dataset,
    ground_truth: List[Dict[str, object]],
    investigator: CachedInvestigator,
) -> Tuple[List[Dict[str, object]], Dict[str, object], List[Dict[str, object]]]:
    truth_by_payment = {row["payment_id"]: row for row in ground_truth}
    rows = []
    details = []
    started = time.perf_counter()

    for index, payment in enumerate(dataset.payments, start=1):
        result = process_payment(payment.payment_id, dataset, investigator)
        truth = truth_by_payment[payment.payment_id]
        row = _row_from_result(result, truth)
        rows.append(row)
        details.append(
            {
                "operational_exception_class": _operational_exception_class(result),
                "operational_is_exception": result.baseline.status != "matched",
                "exception_class": truth["exception_class"],
                "is_exception": truth["is_exception"],
                "split": truth["split"],
                "expected_should_resolve": truth["should_resolve"],
                **result.model_dump(mode="json"),
            }
        )
        print(
            f"[{index:02d}/{len(dataset.payments)}] {payment.payment_id} "
            f"{result.decision.decision:<16} {result.decision.reason}"
        )

    elapsed_seconds = time.perf_counter() - started
    benchmark_rows = [row for row in rows if row["split"] == "benchmark"]
    cache_statistics = investigator.statistics()
    investigator_failures = sum(bool(row["investigator_error"]) for row in rows)
    model_inference_attempted = cache_statistics["live_model_calls"] > 0
    timing_scope = (
        "end-to-end pipeline timing including attempted model inference"
        if model_inference_attempted
        else "pipeline/verifier replay timing; model inference was not attempted"
    )
    dataset_sha256 = _sha256_json(
        {
            "dataset": {
                "payments": [item.model_dump(mode="json") for item in dataset.payments],
                "invoices": [item.model_dump(mode="json") for item in dataset.invoices],
                "customers": [item.model_dump(mode="json") for item in dataset.customers],
                "credits": [item.model_dump(mode="json") for item in dataset.credits],
                "emails": [item.model_dump(mode="json") for item in dataset.emails],
            },
            "ground_truth": ground_truth,
        }
    )
    if cache_statistics["unverified_legacy_cache_hits"]:
        evaluation_mode = "cache_only_legacy_identity_unverified_proposal_replay"
    elif investigator.cache_only and cache_statistics["live_model_calls"] == 0:
        evaluation_mode = "cache_only_proposal_verifier_replay"
    else:
        evaluation_mode = "live_or_mixed_proposal_evaluation"
    provenance = {
        "evaluator_version": EVALUATOR_VERSION,
        "evaluation_mode": evaluation_mode,
        "dataset_sha256": dataset_sha256,
        "proposal_cache_sha256": investigator.cache_sha256(),
        "investigator": investigator.delegate.public_provenance(),
        "proposal_source_identity_verified": (
            cache_statistics["unverified_legacy_cache_hits"] == 0
        ),
        "investigator_failures": investigator_failures,
        **cache_statistics,
    }
    proposal_source_identity_verified = (
        cache_statistics["unverified_legacy_cache_hits"] == 0
    )
    benchmark_claim_eligible = bool(
        proposal_source_identity_verified
        and cache_statistics["failed_live_model_calls"] == 0
        and investigator_failures == 0
    )
    cache_only_proposal_coverage_complete = bool(
        investigator.cache_only
        and cache_statistics["cache_hits"] > 0
        and cache_statistics["cache_misses"] == 0
        and cache_statistics["live_model_calls"] == 0
        and investigator_failures == 0
    )
    verifier_regression_eligible = bool(
        benchmark_claim_eligible or cache_only_proposal_coverage_complete
    )
    generation_id = _sha256_json(provenance)
    for row in rows:
        row["evaluation_generation_id"] = generation_id
    for detail in details:
        detail["evaluation_generation_id"] = generation_id

    benchmark_metrics = {
        "partition_label": SYNTHETIC_BENCHMARK_LABEL,
        "independent_held_out": False,
        **_metrics_for_rows(
            benchmark_rows,
            sum(int(row["latency_ms"]) for row in benchmark_rows) / 1000,
            timing_scope,
        ),
    }
    metrics = {
        "generated_from": "deterministic synthetic benchmark/regression evaluation",
        "evaluation_generation_id": generation_id,
        "evaluation_mode": evaluation_mode,
        "result_status": (
            "model_backed_benchmark"
            if benchmark_claim_eligible
            else "offline_verifier_regression_only"
        ),
        "benchmark_claim_eligible": benchmark_claim_eligible,
        "partition_label": f"{len(rows)}-record synthetic regression corpus",
        "independent_held_out": False,
        "model": investigator.delegate.model,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "cache_hits": cache_statistics["cache_hits"],
        "cache_misses": cache_statistics["cache_misses"],
        "cache": {
            "status": (
                "cache_only"
                if evaluation_mode.startswith("cache_only")
                else "live_or_mixed"
            ),
            "hits": cache_statistics["cache_hits"],
            "misses": cache_statistics["cache_misses"],
            "model_inference_included": model_inference_attempted,
            "model_inference_attempted": model_inference_attempted,
            "proposal_source_identity_verified": proposal_source_identity_verified,
        },
        "safety_gate": {
            "eligible": benchmark_claim_eligible,
            "passed": False,
            "reason": (
                "eligible identity-verified proposal sources"
                if benchmark_claim_eligible
                else "identity-unverified cached proposals are verifier regression inputs only"
            ),
        },
        "verifier_regression_gate": {
            "eligible": verifier_regression_eligible,
            "passed": False,
            "reason": (
                "identity-verified proposal evaluation also satisfies verifier regression checks"
                if benchmark_claim_eligible
                else (
                    "all required cached proposals were replayed; offline verifier regression checks only"
                    if cache_only_proposal_coverage_complete
                    else "required proposal coverage was incomplete"
                )
            ),
        },
        "provenance": provenance,
        **_metrics_for_rows(rows, elapsed_seconds, timing_scope),
        "synthetic_benchmark_regression": benchmark_metrics,
        # Legacy API key retained for compatibility; its metadata explicitly states
        # that this is not an independently held-out evaluation.
        "held_out": {"legacy_key": True, **benchmark_metrics},
    }
    metrics["safety_gate"]["passed"] = bool(
        benchmark_claim_eligible
        and metrics["incorrect_auto_resolution_rate"] == 0
        and metrics["arithmetic_correctness"] == 1
        and metrics["retrieval_accuracy"] == 1
    )
    metrics["verifier_regression_gate"]["passed"] = bool(
        verifier_regression_eligible
        and metrics["incorrect_auto_resolution_rate"] == 0
        and metrics["arithmetic_correctness"] == 1
        and metrics["retrieval_accuracy"] == 1
    )
    return rows, metrics, details


def confusion_breakdown(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    groups: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row["exception_class"])].append(row)
    return [
        {
            "exception_class": exception_class,
            "records": len(group),
            "resolved": sum(row["decision"] in {"matched_normally", "resolved"} for row in group),
            "correct_resolutions": sum(bool(row["final_correct_resolution"]) for row in group),
            "human_review": sum(row["decision"] == "human_review" for row in group),
            "wrong_auto_resolutions": sum(bool(row["wrong_auto_resolution"]) for row in group),
            "false_escalations": sum(bool(row["false_escalation"]) for row in group),
        }
        for exception_class, group in sorted(groups.items())
    ]
