import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models import CandidateBundle, InvestigationProposal  # noqa: E402
from app.services.ai_investigator import InvestigatorError, OllamaInvestigator  # noqa: E402
from app.services.alternative_finder import find_valid_alternatives  # noqa: E402
from app.services.baseline_matcher import baseline_match  # noqa: E402
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency  # noqa: E402
from app.services.proof_engine import verify_candidate  # noqa: E402


SPIKE_CASES_PATH = REPO_ROOT / "data" / "dev" / "spike_cases.json"
RESULTS_DIR = REPO_ROOT / "results"


def _is_correct_resolution(
    customer_id: Optional[str],
    invoice_ids: List[str],
    credit_ids: List[str],
    truth: Dict[str, object],
) -> bool:
    return bool(
        truth["should_resolve"]
        and customer_id == truth["correct_customer"]
        and set(invoice_ids) == set(truth["correct_invoices"])
        and set(credit_ids) == set(truth["correct_credits"])
    )


def _system_metrics(rows: List[Dict[str, object]], prefix: str) -> Dict[str, int]:
    resolved = sum(row[f"{prefix}_decision"] == "resolve" for row in rows)
    correct_resolutions = sum(bool(row[f"{prefix}_correct_resolution"]) for row in rows)
    wrong_auto_resolutions = resolved - correct_resolutions
    correct_abstentions = sum(
        row[f"{prefix}_decision"] == "abstain" and not row["expected_should_resolve"]
        for row in rows
    )
    false_escalations = sum(
        row[f"{prefix}_decision"] == "abstain" and row["expected_should_resolve"]
        for row in rows
    )
    return {
        "resolved": resolved,
        "correct_resolutions": correct_resolutions,
        "wrong_auto_resolutions": wrong_auto_resolutions,
        "correct_abstentions": correct_abstentions,
        "false_escalations": false_escalations,
    }


def run_spike(model: str) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    cases = json.loads(SPIKE_CASES_PATH.read_text(encoding="utf-8"))
    investigator = OllamaInvestigator(model=model)
    rows = []
    detailed_results = []
    started = time.perf_counter()

    for case in cases:
        bundle = CandidateBundle.model_validate(case["input"])
        truth = case["ground_truth"]
        baseline = baseline_match(bundle)
        baseline_decision = "resolve" if baseline.status == "matched" else "abstain"
        baseline_correct = _is_correct_resolution(
            baseline.customer_id,
            baseline.matched_invoices,
            baseline.matched_credits,
            truth,
        )

        proposal = None
        investigator_error = None
        model_started = time.perf_counter()
        try:
            proposal = investigator.investigate(bundle)
        except InvestigatorError as exc:
            investigator_error = str(exc)
        model_latency_ms = round((time.perf_counter() - model_started) * 1000)

        if proposal is None:
            llm_decision = "abstain"
            llm_correct = False
            proof = None
            alternatives = find_valid_alternatives(bundle)
            sufficiency = None
            remitproof_decision = baseline_decision
            remitproof_correct = baseline_correct
            abstention_reason = "investigator_error" if baseline.status != "matched" else None
        else:
            # Comparator B intentionally represents the unsafe model-only policy:
            # any syntactically complete proposal is authorized without verification.
            llm_decision = (
                "resolve"
                if proposal.proposed_customer is not None and bool(proposal.invoice_ids)
                else "abstain"
            )
            llm_correct = _is_correct_resolution(
                proposal.proposed_customer,
                proposal.invoice_ids,
                proposal.credit_ids,
                truth,
            )

            proof = verify_candidate(bundle, proposal)
            alternatives = find_valid_alternatives(bundle)
            sufficiency = evaluate_evidence_sufficiency(bundle, proposal, proof, alternatives)
            if baseline.status == "matched":
                remitproof_decision = "resolve"
                remitproof_correct = baseline_correct
                abstention_reason = None
            else:
                remitproof_decision = "resolve" if sufficiency.safe_to_resolve else "abstain"
                remitproof_correct = bool(
                    sufficiency.safe_to_resolve
                    and _is_correct_resolution(
                        proposal.proposed_customer,
                        proposal.invoice_ids,
                        proposal.credit_ids,
                        truth,
                    )
                )
                abstention_reason = sufficiency.abstention_reason

        row = {
            "case_id": case["case_id"],
            "exception": case["exception"],
            "expected_should_resolve": bool(truth["should_resolve"]),
            "baseline_decision": baseline_decision,
            "baseline_correct_resolution": baseline_correct,
            "llm_only_decision": llm_decision,
            "llm_only_correct_resolution": llm_correct,
            "remitproof_decision": remitproof_decision,
            "remitproof_correct_resolution": remitproof_correct,
            "abstention_reason": abstention_reason or "",
            "model_latency_ms": model_latency_ms,
            "investigator_error": investigator_error or "",
        }
        rows.append(row)
        detailed_results.append(
            {
                **row,
                "baseline": baseline.model_dump(mode="json"),
                "proposal": proposal.model_dump(mode="json") if proposal else None,
                "proof": proof.model_dump(mode="json") if proof else None,
                "alternatives": [item.model_dump(mode="json") for item in alternatives],
                "sufficiency": sufficiency.model_dump(mode="json") if sufficiency else None,
            }
        )
        print(
            f"{case['case_id']}: baseline={baseline_decision:<7} "
            f"llm_only={llm_decision:<7} remitproof={remitproof_decision:<7} "
            f"expected={'resolve' if truth['should_resolve'] else 'abstain'}"
        )

    elapsed_seconds = time.perf_counter() - started
    comparison = {
        "baseline": _system_metrics(rows, "baseline"),
        "llm_only": _system_metrics(rows, "llm_only"),
        "remitproof": _system_metrics(rows, "remitproof"),
    }
    semantic_wins = sum(
        row["baseline_decision"] == "abstain"
        and row["expected_should_resolve"]
        and row["remitproof_correct_resolution"]
        for row in rows
    )
    safety_blocks = sum(
        not row["expected_should_resolve"]
        and row["llm_only_decision"] == "resolve"
        and row["remitproof_decision"] == "abstain"
        for row in rows
    )
    go = bool(
        semantic_wins >= 2
        and safety_blocks >= 1
        and comparison["remitproof"]["wrong_auto_resolutions"] == 0
    )
    metrics = {
        "spike_case_count": len(rows),
        "model": model,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "mean_model_latency_ms": round(
            sum(int(row["model_latency_ms"]) for row in rows) / len(rows), 1
        ),
        "comparison": comparison,
        "semantic_wins_over_baseline": semantic_wins,
        "unsafe_llm_resolutions_blocked": safety_blocks,
        "gate": "GO" if go else "MODIFY",
        "gate_requirements": {
            "two_or_more_semantic_wins": semantic_wins >= 2,
            "at_least_one_unsafe_llm_resolution_blocked": safety_blocks >= 1,
            "zero_incorrect_remitproof_auto_resolutions": (
                comparison["remitproof"]["wrong_auto_resolutions"] == 0
            ),
        },
        "results": detailed_results,
    }
    return rows, metrics


def write_results(rows: List[Dict[str, object]], metrics: Dict[str, object]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "spike_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    with (RESULTS_DIR / "spike_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the 10-case RemitProof kill spike.")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "llama3.2"))
    arguments = parser.parse_args()
    rows, metrics = run_spike(arguments.model)
    write_results(rows, metrics)
    print(json.dumps({key: value for key, value in metrics.items() if key != "results"}, indent=2))
    return 0 if metrics["gate"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
