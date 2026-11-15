# RemitProof implementation specification

This folder turns the "RemitProof: Audit and Technical Plan" into task contracts that a coding agent can execute without making architectural decisions.

Place the folder at the repository root as `spec/`.

## Status

| Item | State |
| --- | --- |
| Repository commit validated | `80fc1d7b9f1a9bc0bfc7490aba7d84c2aac7d00e` (2026-10-24), 15 commits, branch `main`, no tags |
| Audit re-validated | Yes. See `AUDIT_VALIDATION.md`. Eight corrections, one new finding (F4), eleven observations from the Phase 1 dry run (section 7), ten from Phase 2 (section 8), eleven from Phase 3 (section 9) and fourteen from Phase 5 (section 10). |
| Architecture | Frozen. See `ARCHITECTURE.md` and `DESIGN_DECISIONS.md`. |
| Task inventory | 62 tasks in 10 groups. See `TASK_INDEX.md`. |
| Phases | 9 (Phase 0 to Phase 8), plus one optional task |
| Contracts ready to implement | 38 of 62: `tasks/RP-001.md` to `tasks/RP-005.md` (Phase 0), `tasks/RP-101.md` to `tasks/RP-111.md` (Phase 1), `tasks/RP-201.md` to `tasks/RP-208.md` (Phase 2), `tasks/RP-301.md` to `tasks/RP-306.md` (Phase 3) and `tasks/RP-501.md` to `tasks/RP-508.md` (Phase 5) |
| Contracts not written | 24 (RP-307, Phases 4, 6, 7 and 8, and the optional task). Their rows in `TASK_INDEX.md` are scope statements only. They are not implementation-ready. |

## Reading order

1. `AUDIT_VALIDATION.md`: what was re-checked, what the audit got wrong, what is new.
2. `ARCHITECTURE.md`: current system and target system.
3. `DESIGN_DECISIONS.md`: every decision an implementer must not re-open.
4. `INVARIANTS.md`: the properties no task may weaken.
5. `IMPLEMENTER_RULES.md`: standing rules for the coding agent. Give this file to the agent with every task.
6. `TEST_STRATEGY.md`: how results are verified.
7. `TASK_INDEX.md` and `DEPENDENCY_GRAPH.md`: what exists and in what order.
8. `PROGRESS_LEDGER.md`: the coordination record. The owner updates it.
9. `tasks/RP-0xx.md` to `tasks/RP-3xx.md` and `tasks/RP-5xx.md`: one contract per task.

## How to run one task

1. Check the task's prerequisites in `PROGRESS_LEDGER.md`.
2. Give the agent exactly three files: `IMPLEMENTER_RULES.md`, `INVARIANTS.md`, and the task contract. Give it the repository. Do not give it sealed evaluation data.
3. The agent implements, runs the verification commands, and returns the report defined in the contract.
4. A reviewer runs the "Reviewer checks" section of the contract independently. The reviewer does not rely on the agent's report.
5. The owner commits, then updates `PROGRESS_LEDGER.md`.

## How the Phase 0 contracts were validated

Each Phase 0 contract was dry-run in a throwaway copy of the repository on Python 3.13.18 with the pinned dependencies. Every expected count, exit code and hash in those contracts was observed in that dry run. The dry-run code is not part of this package and was not added to the repository. Python 3.9 was not available for the dry run, so 3.9 compatibility was checked by parsing with the 3.9 grammar only. CI is the authority for 3.9.

## How the Phase 1 contracts were validated

The eleven Phase 1 tasks were applied one after another, in their execution order, on top of the Phase 0 dry run in the same throwaway copy. After each task the full suite, the frozen-input check and the audit report check were run, and the totals in the contract are the ones seen. Python 3.9.25 was available this time: the final tree passes on 3.9.25 and 3.13.18 from hash-locked environments (430 passed, 1 expected failure on both).

Phase 1 must run in this order: RP-101, RP-102, RP-103, RP-104, RP-107, RP-108, RP-109, RP-110, RP-105, RP-106, RP-111. See `TASK_INDEX.md`.

Three things in Phase 1 need the owner, not an agent:

1. Accept the revised design decisions (DD-04, DD-05, DD-06, DD-07, DD-09) in `DESIGN_DECISIONS.md`. They changed while the contracts were written.
2. RP-109: sign off that `PAY_057`, `PAY_063` and `PAY_068` may move from review to resolved.
3. RP-105: decide OD-1 and regenerate the development lock under Python 3.9.

## How the Phase 2 contracts were validated

The eight Phase 2 tasks were applied in their execution order on top of the Phase 1 result in the same throwaway copy: RP-201, RP-204, RP-202, RP-208, RP-203, RP-205, RP-206, RP-207. The full suite was run after each on Python 3.13.18 and 3.9.25. Phase 2 ends at 565 passed and 1 expected failure, and changes no runtime code.

Everything in Phase 2 was tested on three example seeds written by the specification author. They are tooling fixtures. No benchmark seed exists yet, and no Phase 2 number says anything about the system.

Four things in Phase 2 need the owner, not an agent:

1. Read and accept the authoring guide (printed in full in `tasks/RP-203.md`). It defines the labelling rule. It can be sent to authors before any Phase 2 code exists.
2. Recruit at least three authors and one second labeller (OG-3), and choose where the sealed test split is stored (OG-4).
3. Decide what happens if kappa is below 0.8: the plan says revise the guide and relabel before sealing.
4. H-205: run the expansion, the split and the commitment on the real seeds, and record the generator seed and the split salt in `PROGRESS_LEDGER.md`. An agent must never hold the test seeds.

## How the Phase 3 contracts were validated

Six Phase 3 tasks were applied in their execution order on top of the Phase 2 result: RP-301, RP-302, RP-306, RP-304, RP-303, RP-305. The full suite was run after each on Python 3.13.18 and 3.9.25. The line ends at 657 passed and 1 expected failure, with no change to runtime code or to any frozen file.

No real model was available. The two tasks that talk to a model (RP-303, RP-305) are ready as code and were tested through a stand-in. The first real model run is the owner's step H-302, and it needs OG-5.

Four things in Phase 3 need the owner, not an agent:

1. Read and accept the abstaining-baseline prompt (printed in full in `tasks/RP-303.md`). A baseline with an unfair prompt makes every comparison against it worthless.
2. Choose the model and record its digest (OG-5, OD-3), then run the three model systems on the dev split (H-302).
3. Write the pre-registration (H-301) before the sealed run. It must cite the test commitment hash, the metric definitions in DD-27 and the list of paired comparisons.
4. Decide when RP-307 is written. It needs a model and it changes a frozen input.

## How the Phase 5 contracts were validated

The eight Phase 5 tasks were applied in numeric order on top of the tree after RP-305: RP-501 to RP-508. Phase 4 is not written and Phase 5 does not depend on it. After each task the full suite and both `--check` commands were run on Python 3.13.18 and 3.9.25, from hash-locked environments. The line ends at 793 passed and 1 expected failure.

One runtime file changes in the whole phase: `backend/app/services/search.py`, in RP-507. On the legacy corpus nothing moves: the same alternatives to the character, the same 50 matched, 12 resolved and 18 review, the same audit report.

The solver was compared with three independent references (the existing enumerator, the brute force of RP-106 and OR-Tools CP-SAT) and no comparison disagreed. Forty-one deliberate defects were injected across the phase, one at a time, and each was caught by a test the contracts name.

Read `docs/solver_scaling.md` (written by RP-508) before describing the solver to anyone. The search accepts 64 invoices per customer. On synthetic ledgers of that size it answers about one in three and sends the rest to review.

Five things in Phase 5 need the owner, not an agent:

1. Derive both pruning bounds yourself from section 8 of `tasks/RP-502.md` before you accept RP-502 to RP-504. The audit asked for this and the contract is written for it.
2. Decide OD-6 and regenerate the development lock under Python 3.9 (RP-505). OR-Tools supports Python 3.9, but under Python 3.13 the lock then builds numpy from source.
3. Accept the revised DD-06 and DD-16 in `DESIGN_DECISIONS.md`: four limits where the plan had one, a credit limit per invoice where there was one per customer, and a list of allocations that is complete or refused.
4. Accept one new refusal (RP-507, section 10): a small ledger with more than 2048 exact allocations used to be searched and now goes to review.
5. Decide whether a third pruning bound is worth a task. A side experiment suggests it removes most budget stops (`AUDIT_VALIDATION.md`, section 10, item X13). It is not designed, not specified and not in the inventory.
