# RP-xxx. Title

Use this template for every new contract. A contract is marked READY in `TASK_INDEX.md` only after the readiness checklist at the end is complete.

| Field | Value |
| --- | --- |
| Phase | |
| Depends on | Task IDs and owner gates |
| Risk | Low, Medium or High, with one sentence of reason |
| Changes authorization-critical code | No, Reads only, or Yes with the file names |
| Estimated effort | Hours |
| Review | Standard, Architect or Owner |
| Contract status | NOT WRITTEN, DRAFT, or READY with the commit and Python version of the dry run |

## 1. Objective and rationale

What changes and why. One paragraph each. Name the finding, invariant or decision it serves.

## 2. Prerequisites and start-state checks

A table of commands and required results. Always include the clean-tree check, the suite totals expected at the start, and both `--check` commands.

## 3. Current behaviour and references

What the code does today, with `path:line` for every statement. State what the implementer must read and must not change.

## 4. Files

Exhaustive tables: create, modify (with the region), generate by running a command. State that no other file changes.

## 5. Interfaces

Exact names, signatures, constants and string values. Field order where it matters.

## 6. Input and output contracts

For each function: inputs, outputs, exact keys, ordering, error behaviour. For each command: arguments, printed lines, exit codes.

## 7. Implementation steps

Numbered, each independently checkable.

## 8. Algorithm

Pseudocode for anything that is not a direct transcription of section 6. State complexity and the assumptions the algorithm relies on.

## 9. Edge cases and error handling

A table of case and required behaviour. Say explicitly what is not caught.

## 10. Financial correctness invariants

Each invariant ID the task could affect, and the observable check that shows it still holds. For a task that changes what gets authorized: the predicted change in the audit report, case by case.

## 11. Must remain unchanged

Files and behaviours. For authorization-critical tasks, list the existing tests that pin the unchanged behaviour.

## 12. Tests

Every test by name, with arrange, act and assert. Mark each as unit, integration, regression, property, differential or adversarial. List every probe marker the task removes, by test name.

## 13. Verification commands and expected results

Numbered commands with exact expected output, including suite totals and any hash.

## 14. Reviewer checks

Commands and reading tasks the reviewer performs independently.

## 15. Definition of done

## 16. Stop conditions

Task-specific conditions in addition to the global ones.

## 17. Implementation report

Anything required beyond the standard format.

---

## Readiness checklist for the contract author

A contract is READY only when every item is true.

- [ ] Every `path:line` reference was printed from the repository at the commit the task will start from.
- [ ] The task was dry-run in a throwaway copy. Every expected count, message, exit code and hash in sections 12 and 13 was observed, not predicted.
- [ ] The dry run started from a tree where all dependencies were applied.
- [ ] The dry-run code was discarded. It is not in the repository and not in the contract.
- [ ] The files list is exhaustive: `git status --short` and `git diff --stat` in the dry run showed nothing else.
- [ ] Both `--check` commands passed after the dry run, or the contract defines the generation bump and its predicted diff.
- [ ] For an authorization-critical task: the audit report diff was inspected case by case and matches section 10.
- [ ] For a task that removes a probe marker: the probe passed in the dry run with the marker removed, and its control test still passed.
- [ ] No sentence asks the implementer to choose, judge, prefer or decide.
- [ ] The contract contradicts no entry in `DESIGN_DECISIONS.md` and weakens no entry in `INVARIANTS.md`.
- [ ] Suite totals before and after are recorded in `TEST_STRATEGY.md` section 4 and `PROGRESS_LEDGER.md`.
- [ ] No sealed test content, and no test gold label, appears in the contract.
