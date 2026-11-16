# Implementer rules

You are implementing one task contract from `spec/tasks/`. You execute decisions. You do not make them.

Read this file, `spec/INVARIANTS.md` and your task contract before touching anything.

## Order of authority

1. Your task contract.
2. This file.
3. `spec/INVARIANTS.md`, `spec/DESIGN_DECISIONS.md`, `spec/ARCHITECTURE.md`.
4. The repository's own documents.

If two of these disagree, or the contract disagrees with the code you find, stop and report. Do not pick one.

## Rules

**R-01. Scope.** Create or modify only the files your contract lists. The lists are exhaustive. If the task seems to need another file, stop.

**R-02. No design.** Do not rename, reorder, refactor, reformat or "improve" anything. Do not add parameters, options, helper modules, logging, comments on untouched lines or extra tests beyond the contract. Use the exact names, signatures, strings and constants given.

**R-03. Never touch.** Unless your contract names the file:

- `data/**`, `results/**`, `backend/app/prompts/**`
- `frontend/**`, `api/**`, `backend/api/**`, `backend/vercel.json`, `.github/**`
- `backend/app/utils/results.py`, `backend/app/services/evaluator.py`, `backend/scripts/evaluate.py`
- `backend/app/api/**`, `backend/app/main.py`
- every `requirements*` file and every `.lock` file
- every existing file under `backend/tests/`
- `LICENSE`, `README.md`, `.gitignore`, `.gitattributes`
- `spec/**`

**R-04. Authorization-critical modules.** These decide whether money is allocated. Change one only when your contract names it, and only as written:

`backend/app/services/pipeline.py`, `candidate_retriever.py`, `baseline_matcher.py`, `alternative_finder.py`, `proof_engine.py`, `evidence_sufficiency.py`, `backend/app/utils/remittance_semantics.py`, `normalization.py`, `money.py`, and everything under `backend/app/models/`.

Once Phase 1 has created them, also: `backend/app/services/proof_set.py`, `search.py`, `unread_instructions.py` and `authorization.py`.

**R-05. Language.** Python 3.9 compatible. Use `typing.Optional`, `List`, `Dict`, `Tuple`, `Set`. No `X | Y` in annotations, no `match`, no `zip(strict=...)`, no `itertools.pairwise`, no parenthesized multi-item `with`. Follow the style of the neighbouring file.

**R-06. Existing tests.** Never delete, skip, rename, loosen or re-baseline an existing test. Never change an expected value to match what the code produced. If an existing test fails after your change, stop. One exception: your contract names the test and gives the exact new text. Then make exactly that edit and no other. If a test your contract does not name fails, stop.

**R-07. Expected-failure markers.** Do not add `xfail` or `skip` unless your contract gives the exact marker. Do not remove one unless your contract names the test.

**R-08. Dependencies.** Standard library and the packages already pinned in `backend/requirements-dev.txt` only. No installs. No network access. No new dependency unless the contract is a dependency task.

**R-09. Determinism.** No wall-clock time, random values, environment-dependent ordering, hostnames or absolute paths in any output file. Sort before you serialize. Write JSON with `indent=2`, `sort_keys=True`, UTF-8, one trailing newline, LF line endings.

**R-10. Money.** `Decimal` only. Never `float`. Never compare amounts with a tolerance.

**R-11. Ground truth and sealed data.** Code under `backend/app/` never reads `ground_truth.json` and never calls `load_ground_truth`. Only scripts under `backend/scripts/` and tests may. Never open, request or reconstruct RemitBench test data or its labels. The benchmark tooling in `backend/remitbench/` holds gold labels: code under `backend/app/` never imports it. Never run a benchmark command with an output directory inside the repository unless your contract says so.

**R-12. Dangerous commands.** Never run these with default arguments, because they rewrite frozen files:

- `backend/scripts/evaluate.py` (writes `results/` and mutates `results/proposal_cache.json`)
- `backend/scripts/generate_dataset.py` (writes `data/`)
- `backend/scripts/run_spike.py` (writes `results/spike_metrics.json` and `results/spike_results.csv`)

Run them only if your contract gives the full command line.

**R-13. Git.** Do not commit, amend, tag, push, pull, rebase, stash, reset, clean or switch branches. Leave your work in the working tree. Do not create files outside the repository.

**R-14. Evidence over belief.** A passing suite is not proof of correctness. Run every verification command in your contract and paste the real output. Never write an expected result into your report that you did not observe.

**R-15. No silent adjustment.** If a number, count, hash or message differs from the contract, stop and report the difference. Do not edit the contract's expectation, the test or the code until it matches.

**R-16. Line numbers into files that earlier tasks wrote.** A contract gives `path:line` for every statement. For a file that exists at commit `80fc1d7` and that no earlier task changed, the line is exact. For a file that an earlier task created or changed, the line is its position in the architect's dry-run tree, and in your repository it may be a few lines off. Find the place by the quoted text, the function name or the test name the contract gives next to the line number. If that text or name does not exist, or exists more than once, stop and report. Never guess from the line number alone. The same holds for a start-state check whose expected output shows a line number: the text after the number must match, the number may differ, and you report the number you saw.

## Standard commands

Run from the repository root.

| Purpose | Command |
| --- | --- |
| Confirm the starting state | `git status --short` and `git rev-parse HEAD` |
| Full backend suite | `python -m pytest -q backend/tests` |
| One file | `python -m pytest -q backend/tests/<file>.py` |
| Frozen inputs (after RP-001) | `python backend/scripts/freeze_manifest.py --check` |
| Audit report (after RP-004) | `python backend/scripts/audit_baseline.py --check` |
| Python 3.9 grammar check for a file | `python -c "import ast,sys; ast.parse(open(sys.argv[1]).read(), feature_version=(3,9))" <file>` |

The suite prints one known warning about `asyncio_default_fixture_loop_scope`. Ignore it. Any other warning is new: report it.

## Global stop conditions

Stop immediately, change nothing further, and report when any of these is true:

1. A prerequisite in your contract is not met.
2. `git status --short` is not empty before you start, or a start-state check in your contract fails.
3. Code at a referenced line does not match the contract's description of it.
4. The task needs a file that is not listed.
5. An existing test fails.
6. A verification result differs from the expected result.
7. `python backend/scripts/freeze_manifest.py --check` reports drift.
8. Completing the task would require weakening an invariant, changing a design decision, or resolving an ambiguity yourself.
9. You notice a defect that is outside your task. Report it. Do not fix it.
10. You have attempted the same failing step twice.

A stop is a correct outcome. A guess is not.

## Implementation report

Return exactly this structure. Leave no section out. Write "none" where nothing applies.

```
TASK: RP-xxx <title>
STATUS: COMPLETE | STOPPED
START COMMIT: <git rev-parse HEAD>

FILES CREATED:
- <path> (<line count>)
FILES MODIFIED:
- <path>: <one line per changed region>
FILES DELETED: none

COMMANDS RUN AND OUTPUT:
$ <command>
<verbatim output, last 20 lines at most>

EXPECTED VERSUS OBSERVED:
| Check | Expected | Observed | Match |

DEVIATIONS FROM THE CONTRACT: <list, or none>
STOP CONDITION HIT: <number and description, or none>
OUT-OF-SCOPE OBSERVATIONS: <defects or risks noticed, or none>
OPEN QUESTIONS FOR THE ARCHITECT: <list, or none>
```
