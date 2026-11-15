import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.utils.atomic import atomic_write_bytes  # noqa: E402


MANIFEST_FORMAT_VERSION = 1
CURRENT_FREEZE_GENERATION = "v0"
FROZEN_ROOTS = ("backend/app/prompts", "data", "results")
HASH_DESCRIPTION = "sha256 of file bytes after replacing CRLF with LF"
EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_USAGE = 2


def default_manifest_path(repo_root: Path) -> Path:
    return repo_root / "audit" / CURRENT_FREEZE_GENERATION / "frozen_inputs.json"


def normalized_sha256(path: Path) -> str:
    content = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def _is_ignored(relative: Path) -> bool:
    return any(
        part.startswith(".") or part == "__pycache__" for part in relative.parts
    )


def build_manifest(repo_root: Path) -> Dict[str, object]:
    files: Dict[str, str] = {}
    for root in FROZEN_ROOTS:
        root_path = repo_root / root
        if not root_path.is_dir():
            raise FileNotFoundError("frozen root is missing: " + root)
        for path in sorted(root_path.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(repo_root)
            if _is_ignored(relative):
                continue
            files[relative.as_posix()] = normalized_sha256(path)
    sorted_files = {name: files[name] for name in sorted(files)}
    return {
        "manifest_format_version": MANIFEST_FORMAT_VERSION,
        "freeze_generation": CURRENT_FREEZE_GENERATION,
        "hash": HASH_DESCRIPTION,
        "roots": list(FROZEN_ROOTS),
        "file_count": len(sorted_files),
        "files": sorted_files,
    }


def diff_manifests(
    expected: Dict[str, object], actual: Dict[str, object]
) -> Dict[str, List[str]]:
    expected_files = expected.get("files", {})
    actual_files = actual.get("files", {})
    return {
        "added": sorted(set(actual_files) - set(expected_files)),
        "removed": sorted(set(expected_files) - set(actual_files)),
        "changed": sorted(
            name
            for name in set(expected_files) & set(actual_files)
            if expected_files[name] != actual_files[name]
        ),
    }


def manifest_bytes(manifest: Dict[str, object]) -> bytes:
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Record or check hashes of the frozen input files."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if args.manifest is None:
        manifest_path = default_manifest_path(repo_root)
    else:
        manifest_path = Path(args.manifest)

    if args.write:
        if manifest_path.exists() and not args.force:
            print(f"refusing to overwrite {manifest_path}; pass --force after review")
            return EXIT_USAGE
        actual = build_manifest(repo_root)
        atomic_write_bytes(manifest_path, manifest_bytes(actual))
        print(f"wrote {manifest_path} ({actual['file_count']} files)")
        return EXIT_OK

    if not manifest_path.exists():
        print(f"manifest is missing: {manifest_path}")
        return EXIT_USAGE
    expected = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = build_manifest(repo_root)
    diff = diff_manifests(expected, actual)
    if any(diff.values()):
        print(json.dumps(diff, indent=2, sort_keys=True))
        return EXIT_DRIFT
    print(f"frozen inputs match {manifest_path} ({actual['file_count']} files)")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
