import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.pipeline import process_payment  # noqa: E402
from app.services.verifier_only import VerifierOnlyInvestigator  # noqa: E402
from app.utils.atomic import atomic_write_bytes  # noqa: E402
from app.utils.loaders import Dataset, load_dataset, load_ground_truth  # noqa: E402


REPORT_FORMAT_VERSION = 1
CURRENT_AUDIT_GENERATION = "v0"
REPORT_FILENAME = "verifier_only_baseline.json"
SYSTEMS = ("rules_only_baseline", "verifier_only")
SCOPE = "truth-labelled exceptions that the rules-only baseline did not resolve"
EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_USAGE = 2


def default_report_path(repo_root: Path) -> Path:
    return repo_root / "audit" / CURRENT_AUDIT_GENERATION / REPORT_FILENAME


def _sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def dataset_sha256(dataset: Dataset, ground_truth: List[Dict[str, object]]) -> str:
    return _sha256_json(
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


def matches_truth(
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


def run_cases(
    dataset: Dataset, ground_truth: List[Dict[str, object]]
) -> List[Dict[str, object]]:
    truth_by_id = {str(row["payment_id"]): row for row in ground_truth}
    investigator = VerifierOnlyInvestigator()
    rows: List[Dict[str, object]] = []
    for payment in dataset.payments:
        result = process_payment(payment.payment_id, dataset, investigator)
        truth = truth_by_id[payment.payment_id]
        outcome = investigator.outcomes.get(payment.payment_id)
        baseline_resolved = result.baseline.status == "matched"
        final_auto = result.decision.decision in {"matched_normally", "resolved"}
        rows.append(
            {
                "payment_id": payment.payment_id,
                "split": truth["split"],
                "is_exception": bool(truth["is_exception"]),
                "exception_class": truth["exception_class"],
                "expected_should_resolve": bool(truth["should_resolve"]),
                "rules_only_baseline_decision": "resolve" if baseline_resolved else "abstain",
                "rules_only_baseline_correct_resolution": baseline_resolved
                and matches_truth(
                    result.baseline.customer_id,
                    result.baseline.matched_invoices,
                    result.baseline.matched_credits,
                    truth,
                ),
                "verifier_only_decision": "resolve" if final_auto else "abstain",
                "verifier_only_correct_resolution": final_auto
                and matches_truth(
                    result.decision.customer_id,
                    result.decision.invoice_ids,
                    result.decision.credit_ids,
                    truth,
                ),
                "verifier_only_reason": outcome.reason if outcome is not None else "not_consulted",
                "alternatives_considered": (
                    outcome.alternatives_considered if outcome is not None else None
                ),
                "authorizable_allocations": (
                    len(outcome.authorizable_allocation_ids) if outcome is not None else None
                ),
                "selected_customer": result.decision.customer_id if final_auto else None,
                "selected_invoices": sorted(result.decision.invoice_ids) if final_auto else [],
                "selected_credits": sorted(result.decision.credit_ids) if final_auto else [],
            }
        )
    return rows


def comparison_rows(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return [
        row
        for row in rows
        if row["is_exception"] and row["rules_only_baseline_decision"] == "abstain"
    ]


def summarize(rows: List[Dict[str, object]], system: str) -> Dict[str, int]:
    if system not in SYSTEMS:
        raise ValueError(f"unknown system: {system}")
    resolved = [row for row in rows if row[system + "_decision"] == "resolve"]
    abstained = [row for row in rows if row[system + "_decision"] == "abstain"]
    correct = sum(1 for row in resolved if row[system + "_correct_resolution"])
    return {
        "resolved": len(resolved),
        "correct_resolutions": correct,
        "wrong_auto_resolutions": len(resolved) - correct,
        "correct_abstentions": sum(1 for row in abstained if not row["expected_should_resolve"]),
        "false_escalations": sum(1 for row in abstained if row["expected_should_resolve"]),
    }


def _section(rows: List[Dict[str, object]]) -> Dict[str, object]:
    scoped = comparison_rows(rows)
    return {
        "total_receipts": len(rows),
        "comparison_record_count": len(scoped),
        "systems": {system: summarize(scoped, system) for system in SYSTEMS},
    }


def build_report(
    dataset: Dataset, ground_truth: List[Dict[str, object]]
) -> Dict[str, object]:
    rows = run_cases(dataset, ground_truth)
    splits = sorted({str(row["split"]) for row in rows})
    return {
        "report_format_version": REPORT_FORMAT_VERSION,
        "audit_generation": CURRENT_AUDIT_GENERATION,
        "dataset_sha256": dataset_sha256(dataset, ground_truth),
        "scope": SCOPE,
        "systems": {
            "rules_only_baseline": "baseline_match on the retrieved candidate bundle; no model",
            "verifier_only": (
                "resolve only when exactly one financially valid allocation passes the "
                "existing proof and sufficiency checks; no model"
            ),
        },
        "overall": _section(rows),
        "by_split": {
            split: _section([row for row in rows if row["split"] == split]) for split in splits
        },
        "cases": sorted(comparison_rows(rows), key=lambda row: str(row["payment_id"])),
    }


def report_bytes(report: Dict[str, object]) -> bytes:
    return (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write or check the verifier-only audit baseline report."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--data", default=str(REPO_ROOT / "data"))
    parser.add_argument("--output", default=str(default_report_path(REPO_ROOT)))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    data_dir = Path(args.data).resolve()
    output = Path(args.output)
    content = report_bytes(build_report(load_dataset(data_dir), load_ground_truth(data_dir)))

    if args.write:
        if output.exists() and not args.force:
            print(f"refusing to overwrite {output}; pass --force after review")
            return EXIT_USAGE
        atomic_write_bytes(output, content)
        print(f"wrote {output}")
        return EXIT_OK

    if not output.exists():
        print(f"report is missing: {output}")
        return EXIT_USAGE
    if output.read_bytes().replace(b"\r\n", b"\n") != content:
        print(f"report differs from a fresh run: {output}")
        return EXIT_DRIFT
    print(f"report matches a fresh run: {output}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
