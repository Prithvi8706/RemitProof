# Progress ledger

The owner maintains this file. An implementer never edits it (`IMPLEMENTER_RULES.md` R-03).

A row moves to Accepted only when the reviewer has run the contract's checks and the owner has committed the work. Record the commit hash and the observed suite totals. If observed totals differ from expected, the task is not accepted.

States: Not started, In progress, Stopped (with the stop condition number), In review, Accepted, Blocked.

## Owner gates

| Gate | Condition | Needed by | State | Date |
| --- | --- | --- | --- | --- |
| OG-0 | This specification is accepted. A working branch exists. Commit `80fc1d7` is tagged `v0-audit-baseline`. `spec/` is committed. | RP-001 | Met | 2026-11-15 |
| OG-1 | Phase 0 reviewed: all five tasks Accepted, `audit/v0/` committed. The 2026-11-12 revisions in `DESIGN_DECISIONS.md` accepted by the owner. | Phase 1, RP-201, RP-301 | Met | 2026-11-15 |
| OG-2 | OD-1 decided (Python 3.9 in CI). For RP-505 also OD-6 (how the lock handles numpy under Python 3.13). | RP-105, RP-505, RP-705 | Open | |
| OG-3 | OD-4 decided: at least three seed authors and one second labeller confirmed with dates | H-202 (sending the guide). RP-203 itself is not blocked. | Open | |
| OG-4 | OD-2 decided (data licence). Storage location for the sealed test chosen, outside the repository. | H-205 (the sealing). RP-206 itself is not blocked. | Open | |
| OG-5 | OD-3 decided (model, and whether a second family is available) | RP-305 | Open | |
| OG-6 | H-301 (pre-registration) and H-401 (policy choice) committed, both before any sealed run | RP-801 | Open | |

Tagging and branching commands for OG-0, to be run by the owner:

```
git tag -a v0-audit-baseline 80fc1d7b9f1a9bc0bfc7490aba7d84c2aac7d00e -m "State audited on 2026-11-10"
git switch -c research/v1
```

## Task ledger

| Task | Contract | State | Commit | Suite passed / expected failures (expected) | Observed | Reviewer | Date | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RP-001 | READY | Accepted | `b16c071` | 289 / 0 | 289 / 0 | Owner | 2026-11-15 | Start tree had one unrelated untracked file (`PROJECT_DOSSIER_LOCAL.md`). |
| RP-002 | READY | Accepted | `123ca6c` | 295 / 8 | 295 / 8 | Owner | 2026-11-15 | Command 2 as written (`-q` twice) prints a per-file count, 14; the IDs list with one `-q`. |
| RP-003 | READY | Accepted | `d7bf59e` | 307 / 8 | 307 / 8 | Owner (architect checks run) | 2026-11-15 | Legacy outcomes match the reference lists: 18 resolve, 6 no_authorizable_allocation, 6 no_financially_valid_allocation. |
| RP-004 | READY | Accepted | `8df3526` | 318 / 8 | 318 / 8 | Owner | 2026-11-15 | Report hash and all reference counts match. |
| RP-005 | READY | Accepted | `ee41803` | 318 / 8 | 318 / 8 | Owner | 2026-11-15 | All nine checks match. Owner signed off the wording of the four findings. |
| RP-101 | READY | Accepted | `6631de0` | 331 / 8 | 331 / 8 | Owner (architect checks run) | 2026-11-15 | Order 1 of 11. Diff size differs from the dry run as the contract allows; open choices and two documented residuals (weak-signal cap drop, duplicate credit_id ValidationError) accepted. |
| RP-102 | READY | Accepted | `7314e9a` | 345 / 8 | 345 / 8 | Owner (architect checks run) | 2026-11-15 | Order 2. Open test-helper details settled without changing contract values; two documented residuals (conservative per-customer credit limit, exponential worst-case cost at the limits) accepted. |
| RP-103 | READY | Accepted | `51454e1` | 354 / 7 | 354 / 7 | Owner (architect checks run) | 2026-11-15 | Order 3. Removes 1 marker. Review notes: probe P4 now fails as 'resolved' via the prompt-bundle proposal path (until RP-104), the matcher can still match on ambiguous search via existing filters, and duplicate IDs among cap-dropped records now raise ValidationError (fail closed). |
| RP-104 | READY | Accepted | `cea9db8` | 361 / 6 | 361 / 6 | Owner (architect checks run) | 2026-11-15 | Order 4. Removes 1 marker. Review notes: proposals naming proof-bundle-only invoices, credits or evidence beyond the prompt cap can now resolve when the complete search finds that allocation unique (contract section 9, rows 1-2), and result.candidates now reports the proof bundle, so later retrieval-recall metrics in evaluator.py would count records the model never saw (accepted by the contract; authorization unaffected). |
| RP-105 | READY | Not started | | 417 / 1 | | | | Order 9. Owner regenerates the lock. Needs OG-2. |
| RP-106 | READY | Not started | | 423 / 1 | | | | Order 10 |
| RP-107 | READY | Accepted | `3c8c0df` | 378 / 6 | 378 / 6 | Owner (architect checks run) | 2026-11-15 | Order 5. Review notes: two style-only deviations (a parenthesized condition, an extra assertion message), and a clause the reader misclassifies still hides its ID, the contract's stated F2 residual limit. |
| RP-108 | READY | Not started | | 392 / 3 | | | | Order 6. Removes 3 markers. |
| RP-109 | READY | Not started | | 402 / 3 | | | | Order 7. Owner signs off three changed decisions. |
| RP-110 | READY | Not started | | 417 / 1 | | | | Order 8. Removes 2 markers. |
| RP-111 | READY | Not started | | 430 / 1 | | | | Order 11. Owner signs off the record. |
| RP-201 | READY | Not started | | 463 / 1 | | | | Order 1 of 8 |
| RP-202 | READY | Not started | | 512 / 1 | | | | Order 3 |
| RP-203 | READY | Not started | | 526 / 1 | | | | Order 5. Owner accepts the guide text. |
| RP-204 | READY | Not started | | 474 / 1 | | | | Order 2 |
| RP-205 | READY | Not started | | 547 / 1 | | | | Order 6 |
| RP-206 | READY | Not started | | 558 / 1 | | | | Order 7. Tooling only. The sealing itself is H-205. |
| RP-207 | READY | Not started | | 565 / 1 | | | | Order 8 |
| RP-208 | READY | Not started | | 523 / 1 | | | | Order 4. Added 2026-11-13. |
| RP-301 | READY | Not started | | 604 / 1 | | | | Order 1 of 6 |
| RP-302 | READY | Not started | | 624 / 1 | | | | Order 2 |
| RP-303 | READY | Not started | | 652 / 1 | | | | Order 5. Owner accepts the prompt. Code only: no real model in the dry run. |
| RP-304 | READY | Not started | | 641 / 1 | | | | Order 4 |
| RP-305 | READY | Not started | | 657 / 1 | | | | Order 6. Code only: no real model in the dry run. |
| RP-306 | READY | Not started | | 631 / 1 | | | | Order 3 |
| RP-307 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | Added 2026-11-13. Needs a live model to write and to run. |
| RP-401 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-402 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-403 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-404 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-405 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-406 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-407 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-408 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-501 | READY | Not started | | 696 / 1 | | | | Order 1 of 8. No consumer yet. |
| RP-502 | READY | Not started | | 716 / 1 | | | | Order 2. Owner derives both bounds from section 8 before accepting. |
| RP-503 | READY | Not started | | 726 / 1 | | | | Order 3. Was "credit options" in the plan. Now the solution limit. |
| RP-504 | READY | Not started | | 746 / 1 | | | | Order 4 |
| RP-505 | READY | Not started | | 746 / 1 | | | | Order 5. Owner regenerates the lock under Python 3.9. Needs OG-2 and OD-6. |
| RP-506 | READY | Not started | | 760 / 1 | | | | Order 6. Needs OR-Tools installed. |
| RP-507 | READY | Not started | | 781 / 1 | | | | Order 7. Owner accepts the revised DD-06 and one new refusal. |
| RP-508 | READY | Not started | | 793 / 1 | | | | Order 8. Owner reads the table. |
| RP-601 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-602 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-603 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-604 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-605 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-701 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-702 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-703 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-704 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-705 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-801 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-802 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-803 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-804 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |
| RP-901 | NOT WRITTEN | Blocked: no contract | | set by contract | | | | |

## Human work

| Item | Work | State | Date | Notes |
| --- | --- | --- | --- | --- |
| H-201 | Owner writes 12 dev seeds | Not started | | |
| H-202 | Collect at least 48 seeds from at least 3 other authors | Not started | | |
| H-203 | Second labelling and adjudication; report kappa. Uses the two commands of RP-208. | Not started | | |
| H-204 | Human paraphrases, two per seed, by a different author | Not started | | |
| H-205 | Owner expands, splits and seals the real seeds with the commands of RP-205 and RP-206, then commits `bench/TEST_COMMITMENT.json`, `bench/TEST_FINGERPRINTS.json`, the split record and the dev seeds. Records the generator seed and the split salt here. | Not started | | |
| H-301 | Pre-registration document. Cites the test commitment hash, the metric definitions of RP-302 and the planned comparisons. Committed before RP-801. | Not started | | |
| H-302 | Owner runs `proposal_pipeline`, `basic_validation` and `llm_abstain` on the dev split with `remitbench_record.py`, two runs each, model identified by digest. Five runs if they differ. Keeps the manifests. | Not started | | |
| H-401 | Dev runs and policy choice, written down before unsealing | Not started | | |
| H-801 | Technical report | Not started | | |
| H-802 | Five-minute demo and clean-clone reproduction by another person | Not started | | |

## Probe register

Update when a marker is removed.

| Probe | Finding | Marker state | Removed by | Commit |
| --- | --- | --- | --- | --- |
| `test_f2_unread_instruction_must_not_authorize_the_wrong_invoices[settles]` | F2 | Marked, strict (added in `123ca6c`) | RP-108 | |
| `test_f2_unread_instruction_must_not_authorize_the_wrong_invoices[clears]` | F2 | Marked, strict (added in `123ca6c`) | RP-108 | |
| `test_f2_unread_instruction_must_not_authorize_the_wrong_invoices[covers]` | F2 | Marked, strict (added in `123ca6c`) | RP-108 | |
| `test_f2_residual_misread_sentence_must_not_authorize_the_wrong_invoices` | F2 residual | Marked, strict (added in `123ca6c`) | Not scheduled | |
| `test_f3_truncated_search_must_not_match_in_the_rules_only_path` | F3 | Removed | RP-103 | `51454e1` |
| `test_f3_truncated_search_must_not_resolve_a_proposal` | F3 | Removed | RP-104 | `cea9db8` |
| `test_f4_conflicting_customer_instructions_must_not_resolve[CUS_A-INV_A1-EMAIL_A]` | F4 | Marked, strict (added in `123ca6c`) | RP-110 | |
| `test_f4_conflicting_customer_instructions_must_not_resolve[CUS_B-INV_B1-EMAIL_B]` | F4 | Marked, strict (added in `123ca6c`) | RP-110 | |

## Generation register

| Kind | Generation | Created by | Files | SHA-256 (LF-normalized) | Commit |
| --- | --- | --- | --- | --- | --- |
| Frozen inputs | v0 | RP-001 | `audit/v0/frozen_inputs.json` | `eb1ee75661b40b2c6c2e1248d90f938baffdb2f1da6c31605107bf47c4572ed0` (observed) | `b16c071` |
| Audit report | v0 | RP-004 | `audit/v0/verifier_only_baseline.json` | `fd96d3cab59a45e86d10c1baae88f537dbc66ed3317677e412f4633a029bbb3d` (observed) | `8df3526` |
| Audit report | v1 | RP-111 | `audit/v1/verifier_only_baseline.json` | `291bfce9372a899dea8fb14b83f02e3221cf0935a667c51c8478172f802ed8e2` (expected) | |
| Frozen inputs | next | RP-303 | Generation directory named by the RP-303 contract. `audit/v1/` already holds the v1 audit report, and the two generation counters are independent. | | |
| Published results | v0 | Commit `f510cfd` | `results/` | See `results/current_generation.json` | `f510cfd` |

## Reference figures at v0

Recorded once so later rows can be compared. Source: `AUDIT_VALIDATION.md`.

| Figure | Value |
| --- | --- |
| Backend tests | 283 passed |
| Published pipeline on 30 exceptions | 9 correct, 0 wrong, 12 correct abstentions, 9 false escalations |
| Verifier-only on 30 exceptions | 18 correct, 0 wrong, 12 correct abstentions, 0 false escalations |
| Rules-only on 30 exceptions | 0 resolved, 12 correct abstentions, 18 false escalations |
| Legacy dataset hash | `fd59237a5dddab0ee712c7a34bab735544c0acc1726026dfda7bdf0cfb7671ae` |
| Frozen files | 60 (1 prompt, 19 data, 40 results) |

## Reference figures expected after Phase 1

Observed in the dry run. Source: the Phase 1 contracts and `AUDIT_VALIDATION.md` section 7. Compare with the real result when RP-111 is accepted.

| Figure | Value |
| --- | --- |
| Backend tests | 430 passed, 1 expected failure (the F2 residual) |
| Stored proposals replayed on 30 exceptions | 12 correct, 0 wrong, 12 correct abstentions, 6 false escalations |
| Verifier-only on 30 exceptions | 18 correct, 0 wrong, 12 correct abstentions, 0 false escalations (unchanged) |
| Rules-only on 30 exceptions | 0 resolved, 12 correct abstentions, 18 false escalations (unchanged) |
| All 80 receipts, replay | 50 matched, 12 resolved, 18 review |
| Legacy decisions that differ from the published snapshot | 3: `PAY_057`, `PAY_063`, `PAY_068`, review to resolved, each equal to its truth label |
| Frozen files | 60, unchanged. `results/` is not regenerated. |
| Probes still marked | 1 |

## Reference figures expected after Phase 2

Observed in the dry run on the three example seeds. They are tooling checks, not benchmark results.

| Figure | Value |
| --- | --- |
| Backend tests | 565 passed, 1 expected failure |
| Example files | `EX01` `8c78a34a...474aeb`, `EX02` `c8cdce34...670ea0`, `EX03` `3bb43d90...6a062` (full hashes in RP-201) |
| Expansion of the three examples, generator seed 20261113 | 20 cases; tree hash `9d7991a7baf7cc20d5f491eccf3922baa30213e0716999d2de0d73c458f0dbc9`, identical on Python 3.9.25 and 3.13.18 |
| Commitment over those 20 cases | `237b895f5edaaa7ecf99c6e48871f0bab7274bf08085180bcba7fddd4488fa75` |
| Runtime code changed by Phase 2 | None. `git diff --stat -- backend/app` is empty across the phase. |

## Reference figures expected after the written part of Phase 3

Observed in the dry run on the three example seeds. They are tooling checks, not benchmark results.

| Figure | Value |
| --- | --- |
| Backend tests | 657 passed, 1 expected failure |
| Decisions of `rules_only` on the 20 expanded example cases | 0 allocations. File hash `9666a007...8a066` (full hash in RP-302). |
| Decisions of `verifier_only` on the same cases | 6 allocations, all correct, all from one seed. File hash `cbad84ff...ca9cb`. |
| Results table for those two systems | JSON `01eeac1c...31b96`, Markdown `3fac89b1...5b605` (full hashes in RP-306), identical on Python 3.9.25 and 3.13.18 |
| Abstaining-baseline prompt | `794f62a6...4c7f` (full hash in RP-303) |
| Real model contacted | Never. RP-303 and RP-305 were tested with a stand-in. |

## Reference figures expected after Phase 5

Observed in the dry run. Compare with the real result when RP-508 is accepted.

| Figure | Value |
| --- | --- |
| Backend tests | 793 passed, 1 expected failure, on Python 3.9.25 and 3.13.18 |
| Search limits | 64 eligible invoices per customer, 8 eligible credits per invoice, 2048 allocations, 2,000,000 nodes |
| Legacy corpus through the solver | 54 unique, 20 ambiguous, 6 none, as before. Alternatives identical as JSON to the enumerator's for all 80 payments. At most 3 alternatives and 62 nodes per payment, 1,943 nodes for all 80. |
| All 80 receipts, replay | 50 matched, 12 resolved, 18 review (unchanged) |
| Audit report v1, frozen files, benchmark decision and table hashes | Unchanged. Both `--check` commands exit 0 after every Phase 5 task. |
| Disagreements between the solver and any reference | 0, over 600 drawn problems, 300 generated ledgers checked by four searches, 60 ledgers of 17 to 20 invoices per customer, 74 adversarial cases and the 80 legacy payments |
| OR-Tools | `9.15.6755`, development only. Ten new packages in the development lock. |
| Scaling table | `docs/solver_scaling.json` `95ab417a...997c88`, `docs/solver_scaling.md` `97d15b89...0ddb52` (full hashes in RP-508) |
| Synthetic ledgers answered | 360 of 360 at 8 invoices, 360 of 360 at 16, 239 of 360 at 32, 119 of 360 at 64 |
| Runtime files changed by Phase 5 | `backend/app/services/search.py` modified. `backend/app/solver/` new. Nothing else under `backend/app/`. |

## Stops and deviations

Record every stop, even one resolved in minutes.

| Date | Task | Stop condition | What was found | Resolution | Spec change needed |
| --- | --- | --- | --- | --- | --- |

## Change log for this specification

| Date | Change |
| --- | --- |
| 2026-11-11 | Package created. Phase 0 contracts validated by dry run. |
| 2026-11-15 | OG-1 met: RP-001 to RP-005 accepted, `audit/v0/` committed, and the owner accepted the 2026-11-12 revisions of DD-04, DD-05, DD-06, DD-07 and DD-09. The 2026-11-14 revision of DD-06 is accepted separately with RP-507. |
| 2026-11-15 | OG-0 met: specification accepted, `80fc1d7` tagged `v0-audit-baseline`, working branch `research/v1` started from `main` at `72aefa5`. |
| 2026-11-15 | `spec/` merged into `main` (PR #4, `2b1edd0`). Backend CI job pinned to `ubuntu-24.04` (DD-11). The written line was re-run on top of both: 793 passed, 1 expected failure on Python 3.13.18 and 3.9.25. |
| 2026-11-14 | Phase 5 contracts RP-501 to RP-508 written and validated by dry run, on Python 3.13.18 and 3.9.25. They start after RP-305 and join the end of the written line. DD-06 and DD-16 revised, DD-15 validated, OD-6 added, the reserved reason `solver_timeout` withdrawn (see `DESIGN_DECISIONS.md`). Phase 5 estimate 25 to 28 implementation hours. |
| 2026-11-13 | Phase 3 contracts RP-301 to RP-306 written and validated by dry run, on Python 3.13.18 and 3.9.25. RP-307 and H-302 added. Evaluation code moved from the planned `backend/app/eval/` to `backend/remitbench/` (DD-21). DD-27 added. Phase 3 estimate 25 to 30 implementation hours. |
| 2026-11-13 | Phase 2 contracts RP-201 to RP-208 written and validated by dry run, on Python 3.13.18 and 3.9.25. RP-208 and H-205 added. OG-3 and OG-4 now gate the human steps, not the code. DD-20 extended, DD-26 added. Phase 2 estimate 31 to 37 implementation hours. |
| 2026-11-12 | Phase 1 contracts RP-101 to RP-111 written and validated by dry run, on Python 3.13.18 and 3.9.25. Execution order fixed. DD-04, DD-05, DD-06, DD-07 and DD-09 revised (see `DESIGN_DECISIONS.md`). Phase 1 estimate 39 to 41 hours. |
