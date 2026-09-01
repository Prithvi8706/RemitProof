import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, List


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ai_investigator import OllamaInvestigator  # noqa: E402
from app.services.evaluator import (  # noqa: E402
    CachedInvestigator,
    confusion_breakdown,
    evaluate_dataset,
)
from app.utils.atomic import atomic_write_bytes, atomic_write_json  # noqa: E402
from app.utils.loaders import load_dataset, load_ground_truth  # noqa: E402
from app.utils.results import (  # noqa: E402
    MANIFEST_FILENAME,
    MANIFEST_FORMAT_VERSION,
    POINTER_FILENAME,
    publication_id,
)


def _csv_bytes(rows: List[Dict[str, object]]) -> bytes:
    if not rows:
        return b""
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode("utf-8")


def _publish_results(
    output_dir: Path,
    rows: List[Dict[str, object]],
    metrics: Dict[str, object],
    details: List[Dict[str, object]],
) -> None:
    generation_id = str(metrics["evaluation_generation_id"])
    artifacts = {
        "results.csv": _csv_bytes(rows),
        "confusion_breakdown.csv": _csv_bytes(confusion_breakdown(rows)),
        "metrics.json": (json.dumps(metrics, indent=2) + "\n").encode("utf-8"),
        "details.json": (json.dumps(details, indent=2) + "\n").encode("utf-8"),
    }
    artifact_hashes = {
        name: hashlib.sha256(content).hexdigest()
        for name, content in artifacts.items()
    }
    publication = publication_id(generation_id, artifact_hashes)
    manifest = {
        "manifest_format_version": MANIFEST_FORMAT_VERSION,
        "publication_id": publication,
        "evaluation_generation_id": generation_id,
        "evaluation_mode": metrics["evaluation_mode"],
        "artifacts": artifact_hashes,
    }
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")

    generations_dir = output_dir / "generations"
    generations_dir.mkdir(parents=True, exist_ok=True)
    generation_dir = generations_dir / publication
    expected_generation_files = {**artifacts, MANIFEST_FILENAME: manifest_bytes}

    def generation_matches() -> bool:
        return generation_dir.is_dir() and all(
            (generation_dir / name).is_file()
            and (generation_dir / name).read_bytes() == content
            for name, content in expected_generation_files.items()
        )

    if generation_dir.exists():
        if not generation_matches():
            raise RuntimeError(
                f"immutable result publication {publication} already exists with different content"
            )
    else:
        staging_dir = Path(
            tempfile.mkdtemp(prefix=".publishing-", dir=str(generations_dir))
        )
        try:
            for name, content in artifacts.items():
                atomic_write_bytes(staging_dir / name, content)
            atomic_write_bytes(staging_dir / MANIFEST_FILENAME, manifest_bytes)
            try:
                os.replace(staging_dir, generation_dir)
            except OSError:
                # A concurrent publisher may have installed the identical immutable
                # generation first. Accept only an exact byte-for-byte match.
                if not generation_matches():
                    raise
        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir)

    # Root exports are compatibility copies only. API readers use the immutable
    # generation selected by the pointer below and never combine these files.
    for name, content in artifacts.items():
        atomic_write_bytes(output_dir / name, content)
    atomic_write_bytes(output_dir / MANIFEST_FILENAME, manifest_bytes)

    pointer = {
        "pointer_format_version": MANIFEST_FORMAT_VERSION,
        "publication_id": publication,
        "evaluation_generation_id": generation_id,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    atomic_write_json(output_dir / POINTER_FILENAME, pointer)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate baseline, forced-proposal verifier ablation, and RemitProof "
            "on the synthetic regression corpus."
        )
    )
    parser.add_argument("--data", default=str(REPO_ROOT / "data"))
    parser.add_argument("--output", default=str(REPO_ROOT / "results"))
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "llama3.2"))
    parser.add_argument("--model-digest", default=os.getenv("OLLAMA_MODEL_DIGEST"))
    parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Refuse every network/model call and fail if any proposal is absent from cache.",
    )
    parser.add_argument(
        "--allow-unverified-legacy-cache",
        action="store_true",
        help=(
            "Allow cache-only replay of legacy proposals matched by payment ID when "
            "their original prompt/configuration identity cannot be proven. Results "
            "are explicitly labeled identity-unverified."
        ),
    )
    arguments = parser.parse_args()

    data_dir = Path(arguments.data).resolve()
    output_dir = Path(arguments.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = load_dataset(data_dir)
    ground_truth = load_ground_truth(data_dir)
    delegate = OllamaInvestigator(
        model=arguments.model,
        model_digest=arguments.model_digest,
    )
    investigator = CachedInvestigator(
        delegate,
        output_dir / "proposal_cache.json",
        cache_only=arguments.cache_only,
        allow_unverified_legacy=arguments.allow_unverified_legacy_cache,
    )

    rows, metrics, details = evaluate_dataset(dataset, ground_truth, investigator)
    _publish_results(output_dir, rows, metrics, details)
    print(json.dumps(metrics, indent=2))

    gate_name = (
        "safety_gate"
        if metrics["benchmark_claim_eligible"]
        else "verifier_regression_gate"
    )
    if arguments.cache_only and (
        metrics["cache_misses"] > 0
        or metrics["provenance"]["investigator_failures"] > 0
    ):
        return 2
    return 0 if metrics[gate_name]["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
