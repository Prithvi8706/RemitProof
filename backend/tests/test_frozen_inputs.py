import json
from pathlib import Path

from scripts.freeze_manifest import (
    EXIT_DRIFT,
    EXIT_OK,
    EXIT_USAGE,
    build_manifest,
    default_manifest_path,
    diff_manifests,
    main,
    normalized_sha256,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _fake_repo(tmp_path: Path) -> Path:
    (tmp_path / "backend" / "app" / "prompts").mkdir(parents=True)
    (tmp_path / "data").mkdir()
    (tmp_path / "results").mkdir()
    (tmp_path / "backend" / "app" / "prompts" / "p.txt").write_bytes(b"prompt\n")
    (tmp_path / "data" / "a.csv").write_bytes(b"x,y\n1,2\n")
    (tmp_path / "results" / "m.json").write_bytes(b"{}\n")
    return tmp_path


def test_frozen_inputs_match_committed_manifest():
    expected = json.loads(
        default_manifest_path(REPO_ROOT).read_text(encoding="utf-8")
    )
    actual = build_manifest(REPO_ROOT)
    assert diff_manifests(expected, actual) == {
        "added": [],
        "removed": [],
        "changed": [],
    }
    assert actual == expected


def test_normalized_hash_ignores_line_ending_style(tmp_path):
    (tmp_path / "lf.txt").write_bytes(b"a\nb\n")
    (tmp_path / "crlf.txt").write_bytes(b"a\r\nb\r\n")
    (tmp_path / "other.txt").write_bytes(b"a\nc\n")
    lf_hash = normalized_sha256(tmp_path / "lf.txt")
    assert lf_hash == normalized_sha256(tmp_path / "crlf.txt")
    assert lf_hash != normalized_sha256(tmp_path / "other.txt")


def test_diff_reports_added_removed_and_changed():
    expected = {"files": {"data/a": "1", "data/b": "2", "data/c": "3"}}
    actual = {"files": {"data/a": "1", "data/b": "9", "data/d": "4"}}
    assert diff_manifests(expected, actual) == {
        "added": ["data/d"],
        "removed": ["data/c"],
        "changed": ["data/b"],
    }


def test_check_detects_drift_and_write_requires_force(tmp_path):
    repo = _fake_repo(tmp_path)
    base = ["--repo-root", str(repo)]
    assert main(["--check"] + base) == EXIT_USAGE
    assert main(["--write"] + base) == EXIT_OK
    assert main(["--check"] + base) == EXIT_OK
    assert main(["--write"] + base) == EXIT_USAGE
    (repo / "data" / "a.csv").write_bytes(b"x,y\n1,3\n")
    assert main(["--check"] + base) == EXIT_DRIFT
    assert main(["--write", "--force"] + base) == EXIT_OK
    assert main(["--check"] + base) == EXIT_OK


def test_hidden_and_cache_paths_are_ignored(tmp_path):
    repo = _fake_repo(tmp_path)
    before = build_manifest(repo)
    (repo / "results" / ".publishing-x").mkdir()
    (repo / "results" / ".publishing-x" / "metrics.json").write_bytes(b"{}\n")
    (repo / "data" / "__pycache__").mkdir()
    (repo / "data" / "__pycache__" / "x.pyc").write_bytes(b"\x00")
    (repo / "data" / ".DS_Store").write_bytes(b"\x00")
    assert build_manifest(repo) == before


def test_manifest_lists_every_frozen_root_and_is_sorted():
    manifest = build_manifest(REPO_ROOT)
    names = list(manifest["files"])
    assert names == sorted(names)
    assert manifest["file_count"] == len(names)
    for prefix in ("backend/app/prompts/", "data/", "results/"):
        assert any(name.startswith(prefix) for name in names)
