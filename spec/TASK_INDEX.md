# Task index

64 tasks: 63 in 9 phases (Phase 0 to Phase 8) plus one optional task. Forty-three have validated contracts: all of Phase 0, Phase 1, Phase 2 and Phase 5, six of the seven Phase 3 tasks and five of the seven Phase 6 tasks. The other 21 rows are scope statements. They fix the task's identity, order and size. They are not instructions, and no agent should implement from them.

## Reading the table

| Column | Meaning |
| --- | --- |
| Depends on | Every listed task must be accepted and committed first. `OG-n` is an owner gate (see `PROGRESS_LEDGER.md`). |
| Hours | Estimate for a human developer, including learning and debugging. A coding agent is faster to write and no faster to review. |
| Risk | Low: additive, no behaviour change. Medium: new logic near authorization code, or a dependency change. High: changes what gets authorized, or protects the sealed test. |
| Changes AC code | Yes: edits an authorization-critical module (`IMPLEMENTER_RULES.md` R-04). Reads only: calls such code without editing it. |
| Review | Standard: any reviewer runs the contract's checks. Architect: the contract author reads every changed line against the invariants. Owner: needs a decision or an action only the owner can take. |
| Contract | READY: written, dry-run and safe to delegate. NOT WRITTEN: scope only. |

## Totals

| Group | Tasks | Implementation hours | Human hours | Total |
| --- | --- | --- | --- | --- |
| Phase 0. Freeze and measure | 5 | 16 | 0 | 16 |
| Phase 1. Close the soundness gaps | 11 | 41 | 0 | 41 |
| Phase 2. RemitBench v1 | 8 | 37 | 28 | 65 |
| Phase 3. Baselines and statistics | 7 | 30 | 6 | 36 |
| Phase 4. Reader study | 8 | 35 | 3 | 38 |
| Phase 5. Exact solver | 8 | 28 | 0 | 28 |
| Phase 6. Robustness | 7 | 37 | 2 | 39 |
| Phase 7. Engineering | 5 | 14 | 0 | 14 |
| Phase 8. Final run and write-up | 4 | 17 | 14 | 31 |
| Optional | 1 | 15 | 0 | 15 |
| **Core plan (Phases 0 to 8)** | **63** | **255** | **53** | **308** |

The audit estimated about 220 hours. The difference is explained in `AUDIT_VALIDATION.md`, C6: the F4 fix, smaller reviewable steps in Phase 1, lock regeneration tasks, and human benchmark work counted explicitly. The 51 human hours cannot be delegated.

Phase 6 moved from 26 to 37 implementation hours and from 5 to 7 tasks when its contracts were written. The hostile-input review found three unsafe behaviours of the rules-only matcher (F5 to F7), so that task grew from 3 to 5 hours and a new task of 3 hours closes F5 (RP-606). Mutation testing became a tool without a new dependency and a first report (5 hours where 6 were planned), and a new task of 8 hours for the older gate code, where the dry run found survivors (RP-607, not written). The review-reason task shrank from 6 to 5 hours because it no longer edits the pipeline. One human task was added: the owner triages surviving mutants (H-601, 2 hours).

Phase 5 moved from 25 to 28 implementation hours when its contracts were written. The differential tests grew by two hours (the CP-SAT oracle is a module of its own and its statuses are settled by known-answer tests), the switch of `search` by two (five existing tests pin the old limits, and the cap on the list of allocations was not in the scope statement) and the scaling table by one (it is reproducible and pinned). The dependency task shrank by one, and the old "credit options" task by one, because the option builder of RP-501 already covers credits.

Phase 3 moved from 25 to 30 implementation hours and from 3 to 6 human hours when its contracts were written: the results table grew by an hour, the investigator prompt fix became its own task (RP-307, not yet written), and the live model runs became an explicit human task (H-302).

Phase 2 moved from 31 to 37 implementation hours and from 26 to 28 human hours when its contracts were written: one task was added (RP-208, the second-labelling tools), the validator gained its own oracle, and the sealing act became an explicit human task (H-205).

Phase 1 moved from 39 to 41 hours when its contracts were written: the property tests (RP-106) and the Phase 1 record (RP-111) turned out larger than the scope statements assumed, and RP-101 and RP-104 smaller.

Cut order if time is short, unchanged from the audit: the second model family (`P-2llm`), RP-508, RP-603, RP-704. Never cut Phases 0 to 3.

## Inventory

### Phase 0. Freeze and measure

| ID | Title | Depends on | Hours | Risk | Changes AC code | Review | Contract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [RP-001](tasks/RP-001.md) | Frozen-input manifest and guard test | OG-0 | 3 | Low | No | Standard | READY |
| [RP-002](tasks/RP-002.md) | Soundness probes as strict expected failures | RP-001 | 3 | Low | No | Standard | READY |
| [RP-003](tasks/RP-003.md) | Verifier-only baseline module | RP-002 | 4 | Medium | Reads only | Architect | READY |
| [RP-004](tasks/RP-004.md) | Audit baseline script and committed report | RP-003 | 4 | Low | No | Standard | READY |
| [RP-005](tasks/RP-005.md) | Documentation correction and baseline record | RP-004 | 2 | Low | No | Owner | READY |

### Phase 1. Close the soundness gaps

| ID | Title | Depends on | Hours | Risk | Changes AC code | Review | Contract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [RP-101](tasks/RP-101.md) | Retrieval trace and ProofSet, no consumers | RP-005, OG-1 | 4 | Medium | Yes | Architect | READY |
| [RP-102](tasks/RP-102.md) | SearchOutcome and search with a completeness status, no consumers | RP-101 | 4 | Medium | Yes | Architect | READY |
| [RP-103](tasks/RP-103.md) | Rules-only path decides on the complete search (closes the F3 rules-only probe) | RP-102 | 4 | High | Yes | Architect | READY |
| [RP-104](tasks/RP-104.md) | Proposal path decides on the complete search (closes the F3 proposal probe) | RP-103 | 3 | High | Yes | Architect | READY |
| [RP-105](tasks/RP-105.md) | Hypothesis as a development dependency; lock regeneration | RP-110, OG-2 | 2 | Medium | No | Owner | READY |
| [RP-106](tasks/RP-106.md) | Property tests: the search agrees with an independent brute force | RP-105, RP-102 | 5 | Low | No | Architect | READY |
| [RP-107](tasks/RP-107.md) | Reader reports the IDs it did not classify, no consumers | RP-104 | 3 | Medium | Yes | Architect | READY |
| [RP-108](tasks/RP-108.md) | An unread instruction sends the payment to review (closes three F2 probes) | RP-107 | 4 | High | Yes | Architect | READY |
| [RP-109](tasks/RP-109.md) | The gate stops depending on two citation habits (three legacy payments resolve) | RP-108 | 4 | High | Yes | Architect, then Owner | READY |
| [RP-110](tasks/RP-110.md) | Authorization does not depend on what was proposed (closes two F4 probes) | RP-109 | 5 | High | Yes | Architect | READY |
| [RP-111](tasks/RP-111.md) | Audit generation v1 and the Phase 1 record | RP-110, RP-106 | 3 | Low | No | Owner | READY |

Execution order. It is fixed, and it is not the numeric order:

RP-101, RP-102, RP-103, RP-104, RP-107, RP-108, RP-109, RP-110, RP-105, RP-106, RP-111.

Each contract states the suite totals it expects at its start, and those totals were observed in exactly this order. RP-107 and RP-105 have no code dependency on the task before them. Their dependency is on the totals only. Running Phase 1 in another order needs re-derived contracts.

### Phase 2. RemitBench v1

| ID | Title | Depends on | Hours | Risk | Changes AC code | Review | Contract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [RP-201](tasks/RP-201.md) | Benchmark case format | RP-111 | 4 | Low | No | Standard | READY |
| [RP-202](tasks/RP-202.md) | Case validator and the benchmark's own oracle | RP-204 | 6 | Medium | No | Architect | READY |
| [RP-203](tasks/RP-203.md) | Authoring guide and seed template | RP-208 | 4 | Low | No | Owner | READY |
| [RP-204](tasks/RP-204.md) | Case-to-Dataset adapter | RP-201 | 2 | Low | No | Standard | READY |
| [RP-205](tasks/RP-205.md) | Deterministic variants: renamed IDs, reordered and padded ledgers, one generated twin | RP-203 | 10 | Medium | No | Architect | READY |
| [RP-206](tasks/RP-206.md) | Seed-level split, commitment to the sealed test split, access log | RP-205 | 5 | Medium | No | Owner | READY |
| [RP-207](tasks/RP-207.md) | Leak guard: no sentence of the sealed test split in the repository | RP-206 | 3 | Low | No | Standard | READY |
| [RP-208](tasks/RP-208.md) | Blind copies for the second labeller and the agreement report | RP-202 | 3 | Low | No | Standard | READY |

Human work in this phase, not delegable:

| ID | Work | Depends on | Hours |
| --- | --- | --- | --- |
| H-201 | Owner writes 12 dev seeds | RP-203 | 6 |
| H-202 | Collect at least 48 seeds from at least 3 other authors | RP-203, OG-3 | 10 |
| H-203 | Second labelling and adjudication; report kappa | H-202, RP-208 | 6 |
| H-204 | Human paraphrases, two per seed, by a different author | H-202 | 4 |
| H-205 | Owner expands, splits and seals the real seeds; commits the commitment, the fingerprints, the split record and the dev seeds | H-201, H-203, H-204, RP-207, OG-4 | 2 |

Execution order. It is fixed, and it is not the numeric order:

RP-201, RP-204, RP-202, RP-208, RP-203, RP-205, RP-206, RP-207.

Phase 2 starts from the tree Phase 1 ends on (430 passed, 1 expected failure) and ends at 565 passed, 1 expected failure. No Phase 2 task changes runtime code.

The human work can start before any Phase 2 code exists. The guide, the seed template and the two worked examples are printed in full in the contracts RP-203 and RP-201. Once OG-3 is met the owner may send them to authors as they are.

### Phase 3. Baselines and statistics

| ID | Title | Depends on | Hours | Risk | Changes AC code | Review | Contract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [RP-301](tasks/RP-301.md) | Statistics module | RP-207 | 6 | Medium | No | Architect | READY |
| [RP-302](tasks/RP-302.md) | Evaluation harness: named systems, decisions files, outcomes and metrics | RP-301 | 7 | Medium | No | Architect | READY |
| [RP-303](tasks/RP-303.md) | Abstaining-model baseline | RP-304 | 4 | Medium | No | Architect, then Owner | READY |
| [RP-304](tasks/RP-304.md) | Basic-validation baseline | RP-306 | 2 | Low | No | Standard | READY |
| [RP-305](tasks/RP-305.md) | Run recorder: repeated runs, determinism check, run manifest | RP-303 | 3 | Medium | No | Standard | READY |
| [RP-306](tasks/RP-306.md) | Results table: scopes, strata, paired comparisons | RP-302 | 4 | Low | No | Standard | READY |
| RP-307 | Investigator prompt example fix; stored proposals regenerated with a live model; freeze generation bump | RP-305, OG-5 | 4 | High | No | Owner | NOT WRITTEN |

Human work in this phase, not delegable:

| ID | Work | Depends on | Hours |
| --- | --- | --- | --- |
| H-301 | Pre-registration document, citing the test commitment hash | RP-306, H-205 | 3 |
| H-302 | Owner runs the model systems on the dev split with the recorder, two runs each, and keeps the manifests | RP-305, OG-5, H-205 | 3 |

Execution order of the written contracts. It is fixed, and it is not the numeric order:

RP-301, RP-302, RP-306, RP-304, RP-303, RP-305.

Phase 3 starts from the tree Phase 2 ends on (565 passed, 1 expected failure) and reaches 657 passed, 1 expected failure after RP-305. No written Phase 3 task changes runtime code or a frozen file.

RP-303 and RP-305 are ready as code and were tested with a stand-in for the model. No real model was available in the dry run. The live runs are H-302.

### Phase 4. Reader study

| ID | Title | Depends on | Hours | Risk | Changes AC code | Review | Contract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RP-401 | Assertion and ReadingResult types | RP-111 | 3 | Low | No | Standard | NOT WRITTEN |
| RP-402 | Identifier resolution against the ledger | RP-401 | 4 | High | Yes | Architect | NOT WRITTEN |
| RP-403 | Lexical reader adapter with offsets, decision-equivalent on the legacy corpus | RP-401, RP-108 | 4 | Medium | Yes | Architect | NOT WRITTEN |
| RP-404 | Span check | RP-402 | 5 | High | Yes | Architect | NOT WRITTEN |
| RP-405 | LLM reader and prompt | RP-404, RP-305 | 8 | Medium | No | Architect | NOT WRITTEN |
| RP-406 | Reading policies | RP-403, RP-404 | 3 | High | Yes | Architect | NOT WRITTEN |
| RP-407 | Constraint mapping from accepted assertions into search | RP-406, RP-110 | 3 | High | Yes | Architect | NOT WRITTEN |
| RP-408 | Policy runner on dev and frontier table | RP-407, RP-405, RP-306, RP-206 | 5 | Low | No | Standard | NOT WRITTEN |

Human work in this phase, not delegable:

| ID | Work | Depends on | Hours |
| --- | --- | --- | --- |
| H-401 | Dev runs and policy choice, written down before unsealing | RP-408 | 3 |

### Phase 5. Exact solver

| ID | Title | Depends on | Hours | Risk | Changes AC code | Review | Contract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [RP-501](tasks/RP-501.md) | Minor units and the solver problem | RP-305, RP-102 | 4 | Medium | Yes | Architect | READY |
| [RP-502](tasks/RP-502.md) | Branch and bound: every exact allocation, with two pruning bounds | RP-501 | 5 | High | Yes | Architect, then Owner | READY |
| [RP-503](tasks/RP-503.md) | Solution limit: the search can stop at the k-th allocation | RP-502 | 2 | High | Yes | Architect | READY |
| [RP-504](tasks/RP-504.md) | Node budget: a search that cannot finish says so | RP-503 | 2 | High | Yes | Architect | READY |
| [RP-505](tasks/RP-505.md) | OR-Tools as a development dependency; lock regeneration | RP-504, RP-501, OG-2 | 3 | Medium | No | Owner | READY |
| [RP-506](tasks/RP-506.md) | The solver against three independent references, and adversarial families | RP-505, RP-504, RP-106 | 5 | Medium | Reads only | Architect | READY |
| [RP-507](tasks/RP-507.md) | The search delegates to the solver; limits of 64 invoices, 8 credits per invoice, 2048 allocations, 2,000,000 nodes | RP-506, RP-110 | 4 | High | Yes | Architect, then Owner | READY |
| [RP-508](tasks/RP-508.md) | Scaling experiment and table | RP-507 | 3 | Low | No | Standard, then Owner | READY |

Execution order. It is fixed, and here it is the numeric order:

RP-501, RP-502, RP-503, RP-504, RP-505, RP-506, RP-507, RP-508.

Phase 5 starts from the tree the written part of Phase 3 ends on (657 passed, 1 expected failure) and ends at 793 passed, 1 expected failure. It does not depend on Phase 4. RP-501 to RP-504 build the solver with no consumer. RP-507 is the one task that changes what the runtime does, and on the legacy corpus it changes nothing.

Three titles differ from the plan. RP-502 covers credits as well, because the option builder of RP-501 turns an invoice and its credits into options before the search starts. RP-503 was "credit options" and is now the solution limit. RP-507 sets four limits, not one.

RP-505 needs OG-2 and a new owner decision, OD-6 (`DESIGN_DECISIONS.md`): OR-Tools supports Python 3.9, but one of its dependencies has no wheel for Python 3.13 at the version Python 3.9 needs.

### Phase 6. Robustness

| ID | Title | Depends on | Hours | Risk | Changes AC code | Review | Contract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [RP-601](tasks/RP-601.md) | Property suite for the authorization invariants | RP-508, RP-106, RP-110, RP-105 | 8 | Medium | Reads only | Architect | READY |
| RP-602 | Metamorphic stability report on dev | RP-408, H-205 | 3 | Low | No | Standard | NOT WRITTEN |
| [RP-603](tasks/RP-603.md) | Mutation testing of the solver, the search and authorization | RP-605, RP-601, RP-507 | 5 | Medium | Reads only | Standard, then Owner | READY |
| [RP-604](tasks/RP-604.md) | Hostile-input tests, and three findings recorded as probes | RP-601, RP-110 | 5 | Medium | Reads only | Architect, then Owner | READY |
| [RP-605](tasks/RP-605.md) | Why a case needs review, computed from the case | RP-606, RP-601, RP-110 | 5 | Medium | Reads only | Architect, then Owner | READY |
| [RP-606](tasks/RP-606.md) | A rules-only match is refused when its own proof shows a contradiction | RP-604, RP-110 | 3 | High | Yes | Architect, then Owner | READY |
| RP-607 | Mutation testing of the matcher, the proof engine, the gate and the pipeline; triage and the tests it calls for | RP-603 | 8 | Medium | No | Architect, then Owner | NOT WRITTEN |

Human work in this phase, not delegable:

| ID | Work | Depends on | Hours |
| --- | --- | --- | --- |
| H-601 | Owner triages the surviving mutants; repeated after the last change to a target file and before the sealed run | RP-603 | 2 |

Execution order of the written tasks. It is fixed, and it is not the numeric order:

RP-601, RP-604, RP-606, RP-605, RP-603.

Phase 6 starts from the tree Phase 5 ends on (793 passed, 1 expected failure) and its written part ends at 914 passed, 10 expected failures. Nine of the ten are the probes for findings F6 and F7, which stay until a Phase 4 contract names them. The tenth is the F2 residual probe.

RP-606 is the one task in the phase that changes a decision path. It only removes automatic decisions, and on the legacy corpus and the benchmark examples it changes nothing.

Two tasks are not written. RP-602 needs the policy runner of RP-408 and real dev seeds (H-205), so it moves behind Phase 4. RP-607 needs the owner's decision on how much of the older gate code to cover: see its scope note below.

### Phase 7. Engineering

| ID | Title | Depends on | Hours | Risk | Changes AC code | Review | Contract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RP-701 | Ledger index with a differential test against scan retrieval | RP-101 | 5 | Medium | Yes | Architect | NOT WRITTEN |
| RP-702 | Cached dataset lookups | RP-701 | 1 | Low | Yes | Standard | NOT WRITTEN |
| RP-703 | Decision log and replay test | RP-110 | 4 | Medium | No | Standard | NOT WRITTEN |
| RP-704 | Latency harness | RP-701 | 2 | Low | No | Standard | NOT WRITTEN |
| RP-705 | Ruff and mypy in CI; lock regeneration | OG-2 | 2 | Low | No | Owner | NOT WRITTEN |

### Phase 8. Final run and write-up

| ID | Title | Depends on | Hours | Risk | Changes AC code | Review | Contract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RP-801 | Sealed-run script with hash check and access logging | RP-408, RP-507, RP-206, H-601, OG-6 | 4 | High | No | Owner | NOT WRITTEN |
| RP-802 | Final tables generator | RP-801 | 3 | Low | No | Standard | NOT WRITTEN |
| RP-803 | Republish the legacy snapshot as a new generation; API and frontend compatibility | RP-507, RP-605 | 5 | High | No | Architect | NOT WRITTEN |
| RP-804 | README rewrite and report skeleton | RP-802, RP-803 | 5 | Low | No | Owner | NOT WRITTEN |

Human work in this phase, not delegable:

| ID | Work | Depends on | Hours |
| --- | --- | --- | --- |
| H-801 | Technical report | RP-802 | 10 |
| H-802 | Five-minute demo and clean-clone reproduction by another person | RP-804 | 4 |

### Optional

| ID | Title | Depends on | Hours | Risk | Changes AC code | Review | Contract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RP-901 | Deduction model: tax withheld and bank fee as explained residuals | RP-507 | 15 | High | Yes | Architect | NOT WRITTEN |

## Scope notes for unwritten contracts

These record what each contract must settle. They exist so the contract author does not rediscover constraints.

### Phase 1

All eleven contracts are written and dry-run. The scope notes that stood here are superseded by the contracts. Where a contract differs from its old scope note, the contract is right and the reason is in `DESIGN_DECISIONS.md` (change log, 2026-11-12) and `AUDIT_VALIDATION.md` (Phase 1 addendum).

### Phase 2

All eight contracts are written and dry-run. The scope note that stood here is superseded. Differences from it, with reasons, are in `AUDIT_VALIDATION.md` section 8 and `DESIGN_DECISIONS.md` DD-26.

### Phase 3

Six contracts are written and dry-run. Their old scope notes are superseded. Differences, with reasons, are in `AUDIT_VALIDATION.md` section 9 and `DESIGN_DECISIONS.md` DD-21 and DD-27.

- **RP-307.** Not written. Replaces the worked example in `backend/app/prompts/investigator.txt` (which leaks placeholder identifiers into proposals), regenerates the stored proposals with an identified live model, and bumps the freeze generation. It is the only task before RP-803 allowed to edit that prompt. It was split out of RP-303 because it cannot be dry-run without a model, and because it changes a frozen input that the published snapshot depends on. Its contract must be written with a model available, and must list every test that pins the old prompt hash.

### Phase 4

- **RP-403.** Must reproduce every legacy decision exactly before any policy work starts.
- **RP-404.** Tested against at least 50 fabricated assertions before RP-405 exists.
- **RP-407.** `apply(S)` means the allocation's invoices equal S, the meaning already used at `backend/app/services/proof_engine.py:392`.

### Phase 5

All eight contracts are written and dry-run. The scope notes that stood here are superseded. Differences from the plan, with reasons, are in `AUDIT_VALIDATION.md` section 10 and `DESIGN_DECISIONS.md` (DD-06, DD-16, OD-6, change log 2026-11-14).

The audit's note stands: the owner should be able to derive both pruning bounds before accepting RP-502 to RP-504. The derivation, in plain words and with a worked example, is section 8 of `tasks/RP-502.md`.

### Phase 6

Five contracts are written and dry-run. Differences from the plan, with reasons, are in `AUDIT_VALIDATION.md` section 12 and `DESIGN_DECISIONS.md` (change log 2026-11-16).

- **RP-602.** Not written. It reruns the reader policies on metamorphic variants of the dev seeds. It needs RP-408 and H-205.
- **RP-607.** Not written. Point the tool of RP-603 at `baseline_matcher.py`, `proof_engine.py`, `evidence_sufficiency.py` and `pipeline.py`, triage every survivor, and add the tests the triage calls for. What the dry run saw: 252 mutants, 83 survive the 16 gate and proof test files. The full suite was run against 13 of the 83 before the run was stopped for time: it killed 7 and 6 survived. The full-suite stage needs about three minutes per mutant on two cores, so the contract must either name a faster kill suite or accept a run of several hours. Phase 4 changes the gate, so this task is best written after Phase 4.

### Phases 7 and 8

- **RP-703.** Moves `latency_ms` out of the hashed decision content first.
- **RP-801.** Refuses to run unless the archive hash equals the commitment and the pre-registration commit is an ancestor of `HEAD`.
- **RP-803.** The only task allowed to change `results/`, `results.py`, the API result shape or the frontend. Bumps the freeze generation.
