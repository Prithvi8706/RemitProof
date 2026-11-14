# Test strategy

A task is accepted on evidence a reviewer can reproduce, not on the implementer's report.

## 1. Principles

1. **Tests come from the contract.** Each contract names every test, its inputs and its expected result. The implementer writes the test to that description. A test the implementer invented does not count toward acceptance.
2. **Passing the old suite proves nothing new.** The 283 existing tests reached 91% coverage and missed four false-authorization paths. Each task adds tests that would fail without it.
3. **Counts are exact.** Every task states the suite totals before and after. A total that differs in either direction is a stop condition.
4. **Expected values were observed.** Every count, exit code, message and hash in a Phase 0 or Phase 1 contract was seen in a dry run that started at commit `80fc1d7` and applied the tasks in their execution order. Later contracts must meet the same bar before they are marked ready.
5. **The reviewer checks independently.** Each contract has a "Reviewer checks" section with commands the implementer did not design the task around.
6. **Safety first, usefulness second.** A change that raises coverage and adds one wrong automatic decision is rejected.

## 2. Layers

| Layer | What it shows | Where | From |
| --- | --- | --- | --- |
| Existing unit and contract tests | Nothing regressed | `backend/tests/test_*.py` | Now |
| Guard tests | Frozen files and module boundaries are intact | `test_frozen_inputs.py`, boundary tests | RP-001, RP-003 |
| Soundness probes | Each known false authorization, stated as the safe behaviour | `test_soundness_probes.py` | RP-002 |
| Fixture control tests | A probe can fail only for its documented reason | Same file | RP-002 |
| Characterization tests | Pinned outcomes on the legacy corpus | `test_verifier_only.py`, `test_audit_baseline.py` | RP-003, RP-004 |
| Cross-validation | New scoring agrees with numbers the old evaluator published | `test_audit_baseline.py` | RP-004 |
| Reproducibility | A committed report equals a fresh run byte for byte | `test_audit_baseline.py` | RP-004 |
| Property tests | An invariant holds over generated inputs | `backend/tests/test_search_properties.py` (RP-106); `backend/tests/properties/` (new, RP-601) | RP-106, RP-601 |
| Differential tests | Independent implementations agree | Solver against a brute force and the enumerator (`test_solver_search.py`, RP-502); solver, enumerator, brute force and CP-SAT together (`test_solver_differential.py`, RP-506); `search` against the enumerator as JSON (`test_search_solver.py`, RP-507); indexed against scan retrieval | RP-502, RP-506, RP-507, RP-701 |
| Adversarial families | A naive pruning bound is caught by a ledger built against it | `test_solver_differential.py`: equal amounts, one amount that is the sum of others, credits equal to invoice differences, amounts one minor unit apart | RP-506 |
| Known-answer tests for a tool | A third-party status means what the oracle assumes | `test_solver_differential.py`, tests 1 to 5 (CP-SAT) | RP-506 |
| Metamorphic tests | Decisions are stable across paraphrase and reordering | RemitBench dev | RP-602 |
| Mutation tests | The suite detects a changed operator in authorization code | Four modules | RP-603 |
| Hostile inputs | Malformed and oversized input fails closed | `backend/tests/adversarial/` (new) | RP-604 |

## 3. The probe protocol

A probe states the safe behaviour and is expected to fail today.

- Marker: `@pytest.mark.xfail(strict=True, raises=AssertionError, reason="<finding>: <cause>; closed by <task>")`.
- `strict=True`: the suite fails the day the probe passes, so the marker is removed on purpose.
- `raises=AssertionError`: a probe that errors for another reason (bad fixture, exception) is a real failure, not an expected one.
- Every probe has a control test that pins its fixture.
- Only the task named in the reason removes the marker (INV-P8). That task's contract lists the exact marker lines to delete.

Probe register after RP-002. After Phase 1 only the F2 residual row is still marked:

| Probe | Finding | Marker removed by |
| --- | --- | --- |
| `test_f2_unread_instruction_must_not_authorize_the_wrong_invoices[settles]`, `[clears]`, `[covers]` | F2 | RP-108 |
| `test_f2_residual_misread_sentence_must_not_authorize_the_wrong_invoices` | F2 residual | Not scheduled. Measured by the Phase 4 reader study. It may remain an expected failure and is then reported as a known limit. |
| `test_f3_truncated_search_must_not_match_in_the_rules_only_path` | F3 | RP-103 |
| `test_f3_truncated_search_must_not_resolve_a_proposal` | F3 | RP-104 |
| `test_f4_conflicting_customer_instructions_must_not_resolve[CUS_A-INV_A1-EMAIL_A]`, `[CUS_B-INV_B1-EMAIL_B]` | F4 | RP-110 |

## 4. Suite totals

Observed in the dry run. Recorded again in `PROGRESS_LEDGER.md` as each task lands.

| After | Passed | Expected failures | Change |
| --- | --- | --- | --- |
| Commit `80fc1d7` | 283 | 0 | Baseline |
| RP-001 | 289 | 0 | +6 |
| RP-002 | 295 | 8 | +6 passed, +8 expected failures |
| RP-003 | 307 | 8 | +12 |
| RP-004 | 318 | 8 | +11 |
| RP-005 | 318 | 8 | No test change |
| RP-101 | 331 | 8 | +13 |
| RP-102 | 345 | 8 | +14 |
| RP-103 | 354 | 7 | +8 new, +1 probe now passing |
| RP-104 | 361 | 6 | +6 new, +1 probe now passing |
| RP-107 | 378 | 6 | +17 |
| RP-108 | 392 | 3 | +11 new, +3 probes now passing |
| RP-109 | 402 | 3 | +10 new. Three existing tests revised by name, count unchanged. |
| RP-110 | 417 | 1 | +13 new, +2 probes now passing |
| RP-105 | 417 | 1 | No test change |
| RP-106 | 423 | 1 | +6 |
| RP-111 | 430 | 1 | +7 |
| RP-201 | 463 | 1 | +33 |
| RP-204 | 474 | 1 | +11 |
| RP-202 | 512 | 1 | +38: 18 oracle, 20 validator |
| RP-208 | 523 | 1 | +11 |
| RP-203 | 526 | 1 | +3 |
| RP-205 | 547 | 1 | +21 |
| RP-206 | 558 | 1 | +11 |
| RP-207 | 565 | 1 | +7 |
| RP-301 | 604 | 1 | +39 |
| RP-302 | 624 | 1 | +20: 12 systems, 8 scoring |
| RP-306 | 631 | 1 | +7 |
| RP-304 | 641 | 1 | +10 |
| RP-303 | 652 | 1 | +11 |
| RP-305 | 657 | 1 | +5 |
| RP-501 | 696 | 1 | +39 |
| RP-502 | 716 | 1 | +20 |
| RP-503 | 726 | 1 | +10 |
| RP-504 | 746 | 1 | +20 |
| RP-505 | 746 | 1 | No test change |
| RP-506 | 760 | 1 | +14 |
| RP-507 | 781 | 1 | +21 new. Five existing tests revised by name, count unchanged. |
| RP-508 | 793 | 1 | +12 |

Rows are in execution order. After Phase 1 the expected-failure count is 1 (the F2 residual), and every removed marker corresponds to a probe that passes. Phase 2 adds 135 tests and the written part of Phase 3 adds 92. Neither changes runtime code. Phase 5 adds 136 tests and changes one runtime file. No test contacts a model: the two model-facing modules are tested through a stand-in transport.

The final Phase 1 tree was also run from hash-locked environments on Python 3.9.25 and 3.13.18: 430 passed and 1 expected failure on both. The Phase 5 trees were run the same way after every task. From RP-505 on the environments were built from the regenerated lock, which on Python 3.13 means numpy compiled from source (OD-6).

Values pinned by Phase 1 tests:

| Value | Meaning | Pinned by |
| --- | --- | --- |
| `e69d95861c5eae99b45979e3a1e8b59f10d94fc93154bc34d3b630db7e855f19` | One hash over the 80 legacy prompt bundles | RP-101 |
| `4a4473d8a7a6f659f1e205b7d0aa5a26b47d58e63d1b1b9ba0b4c4f0211775fc` | The seven v0 reader fields over 24 legacy emails and 80 payment references, both reader modes | RP-107 |
| `fd96d3cab59a45e86d10c1baae88f537dbc66ed3317677e412f4633a029bbb3d` | The v0 audit report, kept | RP-111 |
| `291bfce9372a899dea8fb14b83f02e3221cf0935a667c51c8478172f802ed8e2` | The v1 audit report | RP-111, generation register |
| `unique` 54, `ambiguous` 20, `none` 6 | Search status over the 80 legacy payments | RP-102 |
| 50 matched, 12 resolved, 18 review | Replay of the 30 stored proposals after RP-109 | RP-109, RP-111 |

Values pinned by Phase 5 tests:

| Value | Meaning | Pinned by |
| --- | --- | --- |
| 648 groups, 799 items, 944 options; at most 4 items in a group and 4 options on an item | The solver problems of the 80 legacy payments | RP-501 |
| 1,943 nodes; at most 62 for one payment | Complete search of the 80 legacy payments | RP-502, RP-504 |
| 389 of 600 with at least one allocation, at most 637, 84,948 nodes | The drawn problems compared with a brute force | RP-502 |
| 38 unique, 22 ambiguous, 0 unknown, 52 compared in full | 60 ledgers of 17 to 20 invoices per customer, solver against CP-SAT | RP-506 |
| 18, 14, 14 and 28 cases with 1475, 19, 145 and 74 allocations | The four adversarial families | RP-506 |
| `(64, 8, 2048, 2000000)` | The four limits of `search` | RP-507 |
| `95ab417aba4d3f6362fda2b03f59629acb498c7aef7b74d5aa5c5576e9997c88` | `docs/solver_scaling.json` | RP-508 |
| `97d15b897c47a62f168636cc7eaf54374a496a16091cc112291261a3220ddb52` | `docs/solver_scaling.md` | RP-508 |

## 5. Generation scheme for pinned outputs

Two kinds of committed output are compared with a fresh run:

- `audit/<generation>/frozen_inputs.json`: hashes of `data/`, `results/`, `backend/app/prompts/`.
- `audit/<generation>/verifier_only_baseline.json`: the audit report.

A task that legitimately changes either one writes a new generation directory, bumps the constant (`CURRENT_FREEZE_GENERATION` or `CURRENT_AUDIT_GENERATION`), keeps the old directory, and records the before and after figures in its report. A reviewer reads that diff. A changed figure with no explanation is a rejection.

A third kind was added by RP-508: `docs/solver_scaling.json` and `docs/solver_scaling.md`, compared with a fresh run by `python backend/scripts/solver_scaling.py --check`. They have no generation directory. A task that changes a limit of `search` regenerates them with `--write --force` and reports the difference.

## 6. What counts as evidence

| Claim | Minimum evidence |
| --- | --- |
| "Finding closed" | The probe passes with its marker removed, its control test still passes, and a new property or regression test covers the class of input |
| "No behaviour change" | Full suite totals unchanged except for added tests, both `--check` commands exit 0, and the audit report is byte-identical |
| "Behaviour change is the intended one" | A new audit generation whose diff is limited to the cases the contract predicts |
| "Safe on new language" | A measured false authorization rate with an exact one-sided bound on sealed RemitBench test, never the legacy corpus |
| "Solver is correct" | Zero disagreements with two independent oracles over a stated number of generated instances, plus named adversarial families |

## 7. Test data rules

- Fixtures are built in the test file or loaded from `data/`. No test writes under `data/`, `results/` or `audit/`. Tests that write use `tmp_path`.
- Tests may read `data/ground_truth.json` (legacy regression fixture). Runtime code may not (R-11).
- No test reads RemitBench test data. The benchmark tooling tests read only the three example files under `bench/examples/`, which are not benchmark seeds. Dev seeds are read only by evaluation code from Phase 3 on.
- The leak guard (RP-207) runs in every suite run. It compares one-way sentence fingerprints and needs no test data.
- Synthetic identifiers in new fixtures use the existing shapes (`INV_...`, `CR_...`, `EMAIL_...`, `CUS_...`) until RP-402 changes identifier resolution.
- Sender addresses that must be trusted use the customer's full legal-name slug under `.example` (`backend/app/utils/remittance_semantics.py:171-201`). `Acme Trading Ltd` maps to `ap@acmetrading.example`.

## 8. Reviewer routine for every task

1. Confirm the diff touches only the listed files: `git status --short`, `git diff --stat`.
2. Run the full suite and compare totals with the contract.
3. Run both `--check` commands (once they exist).
4. Run the contract's "Reviewer checks".
5. For any authorization-critical file in the diff, read every changed line against the contract's invariants section.
6. Reject on any unexplained difference. Do not fix it in review.
