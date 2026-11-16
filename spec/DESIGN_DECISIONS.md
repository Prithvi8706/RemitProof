# Design decisions

Each decision is settled. An implementer who believes a decision is wrong stops and reports. Only the owner changes a decision, by adding a dated entry at the end of this file.

"Validated" means the decision was exercised in a dry run: Phase 0 for DD-02, DD-03, DD-10, DD-13 and DD-14, Phase 1 for DD-04 to DD-09 and DD-11, Phase 5 for DD-15, DD-16 and the revised DD-06, Phase 6 for DD-28 to DD-30. "Reasoned" means it follows from inspected code and was not yet exercised; the task that implements it must validate it when its contract is written.

## Index

| ID | Decision | Status |
| --- | --- | --- |
| DD-01 | The published result contract is frozen through Phase 7 | Reasoned |
| DD-02 | Phase 0 measurements live in separate audit reports | Validated |
| DD-03 | `CandidateBundle` is the prompt view and stays byte-stable | Validated |
| DD-04 | `ProofSet` is a superset of the prompt view | Validated. Revised 2026-11-12. |
| DD-05 | Search has four outcomes and one choke point | Validated. Revised 2026-11-12. |
| DD-06 | Enumeration limits are 16 invoices and 3 credits per customer until the solver lands. From RP-507: 64 invoices per customer, 8 credits per invoice, 2048 allocations, 2,000,000 nodes | Validated. Extended 2026-11-12. Revised 2026-11-14. |
| DD-07 | An unread instruction blocks authorization | Validated. Made stricter 2026-11-12. |
| DD-08 | Citations are derived; citation quality is a metric | Validated |
| DD-09 | Authorization is proposal-independent | Validated. Conservative form chosen 2026-11-12. |
| DD-10 | The verifier-only baseline is an `Investigator` adapter | Validated |
| DD-11 | Python 3.9 is the language floor | Validated: the Phase 1 result passes on 3.9.25 and 3.13.18 |
| DD-12 | No new runtime dependency through Phase 7 | Reasoned |
| DD-13 | The prompt file is frozen until RP-303 | Validated |
| DD-14 | Legacy data and published results are guarded fixtures | Validated |
| DD-15 | Decimal at boundaries, integer minor units inside the solver | Validated 2026-11-14 |
| DD-16 | Hand-written exact solver in production, CP-SAT as a development oracle | Validated. Revised 2026-11-14. |
| DD-17 | The model becomes a reader; the proposer stays as a baseline | Reasoned |
| DD-18 | A fixed set of reading policies; the default is chosen on dev data | Reasoned |
| DD-19 | Identifiers resolve against the ledger; ambiguity escalates | Reasoned |
| DD-20 | RemitBench is split by seed and its test split is sealed | Validated on the example seeds. Extended 2026-11-13. |
| DD-21 | Evaluation harness v2 is new code; the legacy evaluator is frozen | Reasoned |
| DD-22 | Reason codes are reserved | Reasoned. One reserved reason withdrawn 2026-11-14. |
| DD-23 | Implementers do not commit, tag or push | Owner preference |
| DD-24 | Sandbox limits are unchanged | Reasoned. Checked against the allocation cap 2026-11-14. |
| DD-25 | Scope exclusions | Owner direction |
| DD-26 | Benchmark tooling: location, label, oracle, what a variant may change | Validated on the example seeds |
| DD-27 | What the benchmark measures, and how a system is run | Validated on the example seeds. No real model run. |
| DD-28 | A rules-only match must survive its own proof | Validated 2026-11-16 |
| DD-29 | The review reason of a case is computed beside the decision path and published only by RP-803 | Validated 2026-11-16 |
| DD-30 | Mutation testing uses a standard-library runner; triage is the owner's | Validated on the dry-run code 2026-11-16 |

---

## DD-01. The published result contract is frozen through Phase 7

**Decision.** Until RP-803, no task changes `backend/app/utils/results.py`, anything under `results/`, the legacy evaluator's output shape, `backend/app/api/`, or `frontend/`. No field is added to, removed from or renamed in any model serialized into `ProcessingResult`. New information travels in `Decision.proof`, which is a free-form mapping (`backend/app/models/decision.py:115`), or in new models outside `ProcessingResult`.

**Why.** `results.py` validates the snapshot field by field (`:163-253`, `:907-939`). Tests such as `backend/tests/test_api.py` and `backend/tests/test_final_artifact_contract.py` read the committed snapshot. The frontend types mirror it. A result-model change ripples through all three.

**Rejected.** Extending `ProcessingResult` with search fields in Phase 1. It couples the soundness fixes to a frontend change.

**Consequence.** After Phase 1 the live pipeline and the published v0 snapshot differ in behaviour. That is intended. The snapshot is labelled v0 until RP-803 republishes.

## DD-02. Phase 0 measurements live in separate audit reports

**Decision.** The verifier-only baseline is reported by `backend/scripts/audit_baseline.py` (new) into `audit/v0/verifier_only_baseline.json` (new). The evaluator and `results/metrics.json` are not touched.

**Why.** See C3 in `AUDIT_VALIDATION.md`. The dry run shows the separate report reproduces the evaluator's published baseline counts and its dataset hash, so nothing is lost.

**Rejected.** Adding a fourth system to `backend/app/services/evaluator.py`.

## DD-03. `CandidateBundle` is the prompt view and stays byte-stable

**Decision.** No task changes the fields, ordering, caps or serialization of `CandidateBundle` or the logic of `retrieve_candidates` that builds it.

**Why.** The bundle is the model's input (`backend/app/services/ai_investigator.py:109`) and part of every cache key (`backend/app/services/evaluator.py:91-96`). A change makes all 30 cached proposals unreachable.

**Consequence.** Completeness information is computed beside the bundle, never inside it. RP-002 pins the capped bundle with a control test.

## DD-04. `ProofSet` is a superset of the prompt view

**Decision (revised 2026-11-12, RP-101).** Retrieval ranks records and then cuts each list at a cap. `ProofSet` keeps the ranking and drops two of the four cuts.

- Prompt view: the capped `CandidateBundle`, byte-identical to v0.
- Proof bundle, invoices: every invoice retrieval ranked, before the cap of 8.
- Proof bundle, credits: every credit retrieval ranked, before the cap of 3, plus every dataset credit linked to a proof invoice that is not already included, sorted by credit ID.
- Proof bundle, customers and emails: those in the prompt view.
- `complete` is false, with a named reason, when retrieval cut an email (`email_cap`) or a customer with a strong signal (`customer_cap`). A strong signal is a payer-name match, an email of that customer, or a referenced invoice.

**Why.** See C2 in `AUDIT_VALIDATION.md`. The first version of this decision ("bundle plus all eligible invoices of the candidate customers") was compared with this one in the dry run. Neither changes a legacy alternative or decision. This one needs no second eligibility rule: it reuses the ranking retrieval already computes.

**Rejected.** "All invoices of the candidate customers" as written in the audit. "Bundle plus eligible invoices of candidate customers" as first written here.

**Validated.** One hash over all 80 legacy prompt bundles is unchanged. All 80 legacy proof sets are complete. The invoice cap is hit on 39 of 80 legacy payments, and the largest proof bundle has 25 invoices. Enumerating over the proof bundle gives the same alternatives as over the prompt view for all 80. A property test (RP-106) checks on generated ledgers that the proof view never lacks an allocation the prompt view has.

**Consequence.** Enumerating over a `ProofSet` can only add alternatives relative to v0. It can never remove one. Adding an alternative can turn a match into a review (finding F3) and, where the cap hid the only valid allocation, a review into a match. The second case is new automation and is pinned by a test in RP-103.

## DD-05. Search has four outcomes and one choke point

**Decision (revised 2026-11-12, RP-102 to RP-104).** `search(proof_set)` returns `SearchOutcome` with `status` in `unique`, `ambiguous`, `none`, `unknown`, plus `complete`, `alternatives`, `detail` and `incomplete_reasons`. `process_payment` calls `search` once, directly after the replay gate. On `unknown` it returns human review with reason `search_incomplete` before the rules-only matcher and before the investigator. Every later stage receives the alternatives from that one call. After RP-104 `pipeline.py` no longer imports `find_valid_alternatives`.

**Changed from the first version.** There is no runtime assertion. The early return is the enforcement, and a test replaces `search` with a function that returns `unknown` to prove nothing downstream runs. Search details are written to `Decision.proof` only in that early return. The proof mapping of every other path is unchanged, because existing tests compare it.

**Why.** Completeness must travel with the result. A comment cannot enforce it.

**Consequence.** `unknown` maps to human review with `search_incomplete`. It never maps to `unique`.

## DD-06. Enumeration limits are 16 invoices and 3 credits per customer until the solver lands

**Decision (extended 2026-11-12, RP-102).** Until RP-507, `search` returns `unknown` when any customer in the proof bundle has more than 16 eligible invoices or more than 3 eligible credits. RP-507 raises the invoice limit to 64 with a node budget.

**Why.** Invoices: measured cost of the existing enumerator is 597 ms at 16 invoices and 10.4 s at 20. Credits: the enumerator only tries credit subsets of size up to 3 (`backend/app/services/alternative_finder.py:66`), so with four or more eligible credits it silently skips combinations. Reporting that as `unknown` is the honest answer.

**Validated.** On the legacy corpus the largest customer has 4 eligible invoices and 2 eligible credits. No legacy payment reaches either limit.

**Trade-off.** Coverage drops for large ledgers between RP-104 and RP-507. Accepted: a refusal is safe, a truncated answer is not.

**Revised 2026-11-14 (RP-507).** From RP-507 on, `search` calls the solver and returns `unknown` in four cases:

| Limit | Value | Detail string |
| --- | --- | --- |
| Eligible invoices for one customer | more than 64 | `invoice_limit` |
| Eligible credits linked to one eligible invoice | more than 8 | `credit_limit` |
| Search nodes in one call | 2,000,000 visited without finishing | `node_budget` |
| Exact allocations | more than 2048 | `alternative_limit` |

The limit of 3 credits per customer is removed.

**Why the credit limit changed shape.** It existed because the enumerator never combines more than three credits. The solver has no such restriction. What grows with credits is the number of options of one invoice, which doubles with each credit linked to it: measured 256 options in 0.2 ms for 8 credits and 16,384 in 18 ms for 14. So the limit is per invoice.

**Why there is a cap on allocations.** Every later stage needs the whole list: the rules-only matcher filters it before counting, the gate checks the evidence against each entry, authorization tests each entry, and the result publishes all of them. A list that stops at the second allocation would let a later stage read "exactly one" out of two that hide a third. So the list is complete or it is refused. It also has to be bounded, because authorization costs the square of its length (measured 1.3 s at 210 alternatives, 6.7 s at 495). 2048 is the smallest power of two above the most a ledger accepted by the sandbox can produce (255 invoice sets times 8 credit sets, 2040), so DD-24 holds: no sandbox request is refused for this reason.

**Why 2,000,000 nodes.** A search that runs out stops after about a third of a second on Python 3.13 and about half a second on Python 3.9 on the dry-run machine. The budget counts nodes, not time, so the outcome for a ledger is the same on every machine. Inside the old limits the budget cannot be reached: the largest possible tree for 16 invoices and 3 credits has 589,816 nodes.

**Trade-offs, both accepted by the owner with RP-507.**

1. One new refusal. A ledger inside the old limits with more than 2048 exact allocations (for example 16 equal invoices and a payment for 8 of them, 12,870 allocations) was searched before and is `unknown` now.
2. The limit of 64 is real for payments that cover one or two invoices and mostly nominal beyond that. On 360 synthetic ledgers of 64 invoices the search answers 119 and refuses 241 (RP-508). A refusal is safe. The number must not be described as "solved up to 64".

## DD-07. An unread instruction blocks authorization

**Decision (made stricter 2026-11-12, RP-107 and RP-108).** `classify_document_semantics` records, per document, the invoice and credit IDs that appear in a clause that is neither negated, non-current nor affirmative (`unread_ids`). The rule is per clause: an ID that is classified in one clause and unclassified in another is still unread. Called with `bare_references_are_affirmative=True` (payment reference fields), the set is empty by construction.

If any candidate email has a non-empty unread set, `process_payment` returns human review with reason `unread_instruction`, after the search and before the rules-only matcher and the investigator.

**Changed from the first version.** The first version blocked only when the unread ID appeared in a financially valid allocation and the email belonged to a candidate customer. Both conditions were dropped.

- An email saying the transfer clears an invoice that is in no allocation (wrong amount, or not in the ledger) is exactly the case where the visible allocation is likely wrong.
- An unreadable message about this payment is a reason for a person to look, whoever sent it.

**Why.** Finding F2. "Cannot support" alone still resolves when another source selects an allocation and the unread email contradicts it.

**Trade-off.** Any sentence that names a document with wording the reader does not know sends the payment to review. A third party who can get an email into the candidate set can force a review. Both fail safe. The cost in lost automation is not known and is measured in Phase 4.

**Limit, stated on purpose.** A sentence that is fully classified and classified wrongly is not caught. RP-002 records that case as the F2 residual probe. It stays an expected failure after Phase 1.

**Validated.** The three F2 probes pass. None of the 24 legacy emails has an unread ID, and no legacy decision changes.

## DD-08. Citations are derived; citation quality is a metric

**Decision.** RP-109 removes the requirement that a selected credit be repeated in `evidence_ids` (`backend/app/services/evidence_sufficiency.py:48-53`) and lets every candidate email from a trusted sender count for disambiguation whether or not the proposal cited it (`:102`). Citation precision and recall stay as reported metrics.

**What stays a gate.** An empty citation list, a cited ID that is not in the bundle, and the semantic-claim citation checks.

**Why.** Three of the nine published false escalations (PAY_057, PAY_063, PAY_068) had the exact correct allocation and failed only the re-citation rule.

**Validated.** Replaying the 30 stored proposals: PAY_057, PAY_063 and PAY_068 resolve, each equal to its truth label. Thirteen other payments keep their decision, reason and proof and differ in one reported field. The other 64 are identical. Totals move from 50 matched, 9 resolved, 21 review to 50, 12, 18, with 0 wrong. Three existing tests asserted the old rule and are revised by name in the RP-109 contract.

**Trade-off.** "The model must show its work" stops being a gate. The protection was never the citation. It is the sender trust rule and the reader, which apply to uncited emails too.

## DD-09. Authorization is proposal-independent

**Decision (conservative form chosen 2026-11-12, RP-110).** Let A be the set of financially valid allocations that pass the proof and sufficiency checks when each is evaluated with its canonical citations (DD-10). A payment resolves only if both hold:

1. The proposal passes the proof and sufficiency checks with its own citations, as at v0.
2. A has exactly one element and the proposal names it.

If A has more than one element the reason is `multiple_authorizable_allocations`. If condition 1 holds and the proposal is not the single element of A, the reason is `proposal_not_authorizable`. A is computed only when condition 1 holds.

**Changed from the first version.** The first version replaced condition 1 with condition 2. Keeping both means this task can only turn a resolution into a review, never the reverse.

**Why.** Finding F4. At v0 two different proposals for the same input can both resolve.

**Validated.** On the legacy corpus A has at most one element for every payment. The 12 replay resolutions and the 18 verifier-only resolutions are each the single element of A. No legacy decision changes. Both F4 probes pass, in both directions and under reordered records.

**Consequence.** For any input, pipeline resolutions are a subset of the allocations that are singly authorizable. That relation is a permanent test (RP-110, RP-111).

## DD-10. The verifier-only baseline is an `Investigator` adapter

**Decision.** `backend/app/services/verifier_only.py` (new) exposes `canonical_proposal`, `verifier_only_decision` and `VerifierOnlyInvestigator`. The adapter returns the single authorizable proposal, or an empty proposal when there is none or more than one. Evaluation calls the unchanged `process_payment` with the adapter.

Canonical citations for an alternative, in order and without duplicates: the alternative's customer ID, its credit IDs sorted ascending, then the IDs of candidate emails whose `customer_id` equals the alternative's customer, in bundle order.

**Why.** The pipeline applies three gates before it consults an investigator (`backend/app/services/pipeline.py:51-126`). Reusing the pipeline removes any chance of the baseline drifting from those gates.

**Boundary.** No runtime module imports `verifier_only`, in Phase 0 and after. RP-110 moves `canonical_proposal` and the authorizable-set loop into `backend/app/services/authorization.py` (new). The pipeline imports `authorization`. `verifier_only` imports it too. The import-boundary test stays as written.

**Limit.** The adapter receives the prompt view and enumerates over it. See `ARCHITECTURE.md` section 1a, limit 4.

## DD-11. Python 3.9 is the language floor

**Decision.** All new code parses and runs on Python 3.9: `typing.Optional`, `List`, `Dict`, `Tuple`, `Set`; no `X | Y` annotations; no `match`; no parenthesized context managers; no `zip(strict=...)`; no `itertools.pairwise`.

**Why.** CI runs 3.9 and 3.13 (`.github/workflows/ci.yml`), and the existing code uses this style.

**Amended 2026-11-15.** GitHub's `ubuntu-latest` runner moved to Ubuntu 26.04, and `actions/setup-python` has no Python 3.9 build for it (builds exist for 22.04 and 24.04). The backend job failed at "Set up Python" before any test ran. The backend job is now pinned to `runs-on: ubuntu-24.04` (`.github/workflows/ci.yml:17`). The frontend job stays on `ubuntu-latest`. The change rewrites one line in place, so no line reference into `ci.yml` moves.

**Trade-off.** The pin keeps Python 3.9 in CI only as long as GitHub offers Ubuntu 24.04 runners. When they are withdrawn, the backend job fails the same way and OD-1 has to be decided. Moving to 22.04 would only buy less time.

**Open.** OD-1.

## DD-12. No new runtime dependency through Phase 7

**Decision.** `backend/requirements.in`, `backend/requirements.lock`, `backend/requirements.txt` and the root `requirements.txt` do not change. Development dependencies (Hypothesis, OR-Tools, a mutation tool, Ruff, mypy) are added only by RP-105, RP-505, RP-603 and RP-705. RP-105 pins `hypothesis==6.141.1`, the newest release that supports Python 3.9. In the dry run the regenerated lock added three packages (`hypothesis`, `attrs`, `sortedcontainers`) and changed the version or hashes of none. RP-505 pins `ortools==9.15.6755`, the newest release, which supports Python 3.9. Its lock adds ten packages (`ortools`, `absl-py`, `immutabledict`, `numpy`, `pandas`, `protobuf`, `python-dateutil`, `pytz`, `six`, `tzdata`) and changes none. numpy is pinned at 2.0.2, which has no wheel for Python 3.13 (OD-6). An implementer edits the `.in` file only. The owner regenerates the hash locks under Python 3.9 with the command in the lock header.

**Why.** CI installs with `--require-hashes`. The solver is hand-written and logging uses the standard library, so production needs nothing new.

## DD-13. The prompt file is frozen until RP-303

**Decision.** `backend/app/prompts/investigator.txt` is not edited before RP-307, including the leaking example IDs at `:42-45`. (First recorded as RP-303. The prompt fix was split out on 2026-11-13.)

**Why.** The prompt is part of the cache identity. An edit strands the cached proposals. RP-307 needs a live model to regenerate them and fixes the examples then.

## DD-14. Legacy data and published results are guarded fixtures

**Decision.** `data/`, `results/` and `backend/app/prompts/` are covered by `audit/v0/frozen_inputs.json` (new). A test fails on any difference. A task that must change a covered file names the files, writes a new generation directory (`audit/v1/`, ...), and bumps `CURRENT_FREEZE_GENERATION`. The same generation scheme applies to audit reports through `CURRENT_AUDIT_GENERATION`.

**Why.** `backend/scripts/evaluate.py` with default arguments rewrites `results/` and mutates `results/proposal_cache.json`. `generate_dataset.py` rewrites `data/`. `run_spike.py` rewrites two files in `results/`. Nothing detects a consistent republish today.

**Detail.** Hashes are taken after replacing CRLF with LF, so a Windows checkout with automatic line-ending conversion passes.

## DD-15. Decimal at boundaries, integer minor units inside the solver

**Decision.** Records keep `Decimal` with the existing two-decimal validators. The solver converts each amount to an integer number of minor units once, asserts the conversion is exact, and works in integers. No float appears in any financial path.

**Validated 2026-11-14 (RP-501).** `backend/app/solver/minor_units.py` converts through the decimal's own digits and exponent, raises on a fraction of a minor unit, and does not depend on the decimal context. All 230 distinct amounts of the legacy corpus convert and return unchanged. On the way out, `calculated_total` is rebuilt with exactly two places, so a published alternative is the same to the character as the enumerator's (RP-507).

## DD-16. Hand-written exact solver in production, CP-SAT as a development oracle

**Decision.** `backend/app/solver/branch_and_bound.py` (new) is the production search: multiple-choice branch and bound, stops at the second solution, node budget, `unknown` on budget exhaustion. OR-Tools CP-SAT is a development-only dependency used as an independent oracle with a two-solve uniqueness check. Only a proven infeasible second solve counts as proof of uniqueness.

**Why.** Two unrelated implementations agreeing is stronger evidence than either alone, and the production path stays dependency-free and explainable.

**Revised 2026-11-14 (RP-501 to RP-507).** What was built, and where it differs from the sentence above:

1. The package is `backend/app/solver/`: `minor_units.py`, `problem.py` and `branch_and_bound.py`. `problem.py` turns each eligible invoice into an item whose options are the subsets of its credits that fit the invoice. Credits are therefore part of the first two tasks, and no separate "credit options" task exists.
2. `solve(problem, solution_limit=None, node_budget=None)` returns a status (`complete`, `solution_limit` or `node_budget`), the allocations found and the number of nodes visited. Two bounds cut a branch: the running net is above the target, or the running net plus everything still undecided is below it. Both are derived in `tasks/RP-502.md`, section 8.
3. "Stops at the second solution" is a parameter and not the behaviour. `search` needs the whole list (DD-06), so it asks for up to 2049 allocations and treats 2049 as `unknown`. A limit of 2 is used where only "zero, one or more than one" is asked: the comparison with CP-SAT.
4. A stopped search never reports `complete`, and `search` returns no allocation from a stopped search, even though the solver found some.
5. The CP-SAT oracle is `backend/tests/cpsat_oracle.py`, a test helper. Nothing under `backend/app/` imports OR-Tools, and a test enforces it. The oracle builds its model from the records and shares no code with the solver or the enumerator.
6. What CP-SAT's statuses mean was settled by known-answer tests, not from documentation (RP-506): `INFEASIBLE` is a proof, `OPTIMAL` is a found solution or a finished enumeration, `FEASIBLE` is an enumeration cut off after at least one solution, `UNKNOWN` is a cut-off with nothing proven and was observed on an instance that has a solution. The oracle reports `unique` only when the second solve is `INFEASIBLE`.
7. Limits on CP-SAT use its deterministic time, never wall-clock time, so that a test does not depend on how busy the machine is.

**Validated.** No disagreement between the solver and any of three references (the enumerator, the brute force of RP-106, CP-SAT) over 600 drawn problems, 300 generated ledgers, 60 ledgers of 17 to 20 invoices per customer, 74 adversarial cases and the 80 legacy payments.

**Not built, and a known weakness.** The two bounds are weak on large ledgers with many amounts of similar size. See DD-06, trade-off 2, and `AUDIT_VALIDATION.md` section 10, item X13.

## DD-17. The model becomes a reader; the proposer stays as a baseline

**Decision.** From Phase 4 the default configuration uses the model to produce typed assertions with quoted spans. The proposal-based configuration is kept runnable for comparison.

**Why.** Finding F1: enumeration already finds every allocation, so a proposer adds nothing. The open question is who reads the remittance.

## DD-18. A fixed set of reading policies; the default is chosen on dev data

**Decision.** Five policies: `P-lex-v0`, `P-lex-cw`, `P-llm`, `P-and`, `P-2llm`. The default is chosen on RemitBench dev and written down before the sealed test is opened.

## DD-19. Identifiers resolve against the ledger; ambiguity escalates

**Decision.** RP-402 replaces the prefix pattern at `backend/app/utils/normalization.py:6` for the reading path. A mention is a token sequence equal, after normalization, to an identifier of a `ProofSet` record. Zero or several matches produce `unresolved_identifier`. Nothing is guessed.

## DD-20. RemitBench is split by seed and its test split is sealed

**Decision (extended 2026-11-13, RP-206 and RP-207).** Splitting is by seed, never by case. The owner's own seeds are always development seeds. The other seeds are ranked by a salted hash, so the split is reproducible and nobody picks it by hand. The test split is stored outside the repository, and the split command refuses to write it inside. Its commitment (case count, label counts, one SHA-256 over every case) is committed before any system runs on it, and is never overwritten. One script runs on it and appends to an access log. No implementer receives test cases or test gold labels. Dev gold labels are read only by evaluation code and tests.

**Leak guard.** The repository holds one-way fingerprints of the test messages' sentences (five words or more), and a test fails when any text file in the repository contains a matching sentence. The first scope note said "no test-seed identifier in the repository". A seed ID is a counter and proves nothing either way. A copied sentence is what a leak looks like.

**Limit.** The guard catches copies, not paraphrases, and not sentences shorter than five words.

## DD-21. Evaluation harness v2 is new code; the legacy evaluator is frozen

**Decision (location revised 2026-11-13, RP-301 to RP-306).** `backend/app/services/evaluator.py`, `backend/scripts/evaluate.py` and `EVALUATOR_VERSION` do not change before RP-803. Named systems, decisions files, exception-only denominators, intervals and the results table are built in `backend/remitbench/`.

**Changed from the first version.** The first version put the new code in `backend/app/eval/`. Evaluation code reads gold labels, and nothing under `backend/app/` may (R-11). The boundary test of RP-201 would have failed on the first import.

## DD-22. Reason codes are reserved

**Decision.** The reason strings in `ARCHITECTURE.md` section 5 are the only new reasons. A task introduces a reason only if its contract names it. Existing reason strings keep their spelling.

**Withdrawn 2026-11-14.** The reserved reason `solver_timeout` is not introduced. A search that runs out of its node budget is one more way for the search to be incomplete, and DD-05 already maps every such case to `search_incomplete`. The cause travels in `Decision.proof["search_detail"]` as `node_budget` (RP-507). A second reason for the same decision would have needed a second early return in `process_payment` for no gain. It is also not a timeout: the budget counts nodes.

## DD-23. Implementers do not commit, tag or push

**Decision.** An implementer leaves its work in the working tree and returns a report. The owner reviews, commits and tags.

## DD-24. Sandbox limits are unchanged

**Decision.** `backend/app/api/sandbox.py:24-25` and `:39-43` do not change. The sandbox keeps accepting at most 8 invoices, so its searches are always complete.

**Checked 2026-11-14 (RP-507).** "Always complete" now also depends on the allocation cap. A sandbox ledger has at most 8 invoices and 3 credits, so at most 2040 allocations, and the cap is 2048. A test pins the inequality. The largest count found on such a ledger in the dry run is 266. The 16 existing sandbox tests pass unedited.

## DD-25. Scope exclusions

**Decision.** Not built in this plan: write operations, payment execution, ERP integration, currency conversion, authentication, databases, queues, microservices, fine-tuning, embeddings, vector stores, additional LLM agents, LLM repair loops that feed verifier errors back to the model, LLM self-reported confidence as an authorization input, quantum solvers, and visual redesign.

---

## DD-26. Benchmark tooling: where it lives, what a variant may change, how labels are checked

Recorded 2026-11-13 while writing the Phase 2 contracts. Validated on three example seeds.

**Where.** Code is the package `backend/remitbench/`. Data and documents are in `bench/` at the repository root. The suite runs with `backend` on the import path, so a package at the root would need a change to how every test is collected. Nothing under `backend/app/` may import `remitbench`, and a test enforces it.

**Label.** `allocate` with an exact allocation, or `review` with one of eight families. Whether an automatic decision was "easy" is not part of the label. It is computed in Phase 3 from what the rules-only baseline does.

**Rules of the benchmark's world.** Exact amounts only, one customer per allocation, no default such as oldest-first. They are stated in the authoring guide, and the generated variants are only correct under them.

**Independent oracle.** The validator has its own exhaustive search and imports nothing from `app.services`. The benchmark judges the system, so it must not ask the system whether a label is arithmetically possible. The oracle agrees with the pipeline's search on the examples and with a third, naive enumeration on 60 generated ledgers.

**What a generated variant may change.** Only things that provably keep or provably flip the label: record IDs (renaming), list order, eight added invoices too large to take part, and one twin that removes every customer message and, if needed, adds a competing exact allocation. Amounts, names, dates and wording are not changed by code. Text variation comes from human and model paraphrases, which are files checked by the validator (records and label must be identical to the parent).

**Changed from the audit.** The audit described twelve variants per seed, including resampled amounts and names and two generated hard-negative twins. Changing amounts or names can contradict text the author wrote, and most hard-negative edits need judgement. The generator therefore produces up to six variants, and the more valuable twins (lexical traps, text aimed at the model) are written by people and saved with index 1 or higher.

**Determinism.** No use of the `random` module in the generator. Every draw is a SHA-256 of a key string. Output bytes are identical on Python 3.9.25 and 3.13.18.

**Second labelling.** Blind copies contain the records and an empty form. Agreement reports Cohen's kappa on allocate against review, exact-allocation agreement, and family agreement. The tool does not judge the value. The owner does.

**Stated limits.** Renaming is skipped when a message shortens an ID, and a shortened ID of fewer than three characters is not detected. The validator checks the arithmetic of a label, not the judgement behind it. The second labeller does that.

## DD-27. What the benchmark measures, and how a system is run

Recorded 2026-11-13 while writing the Phase 3 contracts. Validated on the expanded example seeds.

**A system is a function from a case to a decision.** A decision is `allocate` with a customer, invoices and credits, or `review` with a reason code. A run of a system is a decisions file: identifiers and reason codes, no label, no message text. Scoring only ever reads decisions files, so a system that needs a model, another machine or an old commit is scored exactly like one that does not.

**Four outcomes.** Correct allocation, wrong allocation, correct review, false escalation. An allocation is wrong when the label is `review`, or when the customer, the invoice set or the credit set differs. There is no partial credit.

**Denominators.**

| Metric | Numerator | Denominator | Interval |
| --- | --- | --- | --- |
| False authorization rate | Wrong allocations | All cases in scope | Exact, plus a one-sided 95% upper bound |
| Automation error | Wrong allocations | Automatic decisions in scope | Exact |
| Coverage | Correct allocations | Cases labelled `allocate` in scope | Wilson |
| Correct review | Correct reviews | Cases labelled `review` in scope | Wilson |

Each is also given with a bootstrap interval that resamples seeds, because the cases of one seed are not independent. Where the two intervals disagree, the seed-level one leads.

**Easy cases.** A case is easy when the rules-only system allocates it correctly. Everything else is an exception, and headline figures are on exceptions. A case the rules-only system allocates wrongly is an exception, so that the mistake is counted and not hidden in the "easy" row.

**Paired comparisons.** Exact McNemar on the exceptions, for "correct decision" and for "wrong allocation", Holm-adjusted across the comparisons named in the pre-registration. Discordant counts are always printed with the p-value.

**Baselines.** `rules_only`, `verifier_only`, `proposal_pipeline` (the product with a model proposal), `basic_validation` (a proposal accepted on arithmetic and record state alone) and `llm_abstain` (a model alone, allowed to abstain, unchecked). The two baselines exist to be beaten fairly: the abstaining model gets every record and the same rules the labellers had, with no worked example in its prompt.

**Not in this phase.** The published v0 system (model proposal plus the old verifier) as a row on RemitBench. It needs the old code to run on the new cases, which means a checkout of the v0 tag writing a decisions file. The decisions-file design allows it. No task builds it yet. Also not built: scoring whether a system's review reason matches the label's family.

**Determinism.** Statistics use no `random` module. Bootstrap indices come from SHA-256. A run is recorded at least twice, and the manifest says whether the runs agreed.

## DD-28. A rules-only match must survive its own proof

**Finding (F5).** The matcher reads affirmative invoice IDs only from the payment's own reference fields. A fully read email from the same customer that names other invoices did not stop a match. The proof engine holds exactly that against a proposal, so the two automatic paths disagreed.

**Decision.** A rules-only match is made only if the proof of the matched allocation, computed for its canonical proposal, shows no contradiction. Otherwise the pipeline replaces the matcher's result by "unresolved" with the existing reason `conflicting_remittance_evidence`, and the payment continues as an unmatched payment (RP-606).

**Why in the pipeline and not in the matcher.** The matcher is also the `rules_only` system of the benchmark, and its decisions there are pinned. Keeping it plain keeps that baseline what it was and lets the benchmark show the difference.

**Rejected.** "A match must be the one authorizable allocation" (the predicate of RP-110). It refuses a plain payer-name match whenever an unrelated customer has an open invoice of the same amount, because the gate counts that invoice as a second explanation. On a large ledger that sends many ordinary payments to review. A control test of RP-601 caught it in the dry run.

**Trade-off.** The rule only removes automatic decisions: 4 of 679 generated cases moved from matched to review, and no legacy or benchmark decision moved. It closes F5 only. A match is still as blind as the reader: F6 and F7 stay open.

## DD-29. The review reason of a case is computed beside the decision path

**Decision.** `assess_case(payment_id, dataset)` answers from the case alone whether a payment can be decided automatically, on which allocation, and if not, why not. It lives in `backend/app/services/review_reason.py`. Nothing on the decision path imports it, and no result carries it. RP-803 is the task that may publish it (RP-605).

**Why.** The published reason describes the proposal that was judged. On the legacy corpus it is the case's own reason for 5 of 18 review decisions, and 6 of the 18 are payments with exactly one authorizable allocation that a wrong proposal sent to review. A reviewer needs the case's reason. But `Decision.reason` is part of the frozen legacy snapshot, and a module that cannot change a decision can be checked against the pipeline by a property test.

**Trade-off.** The order of the checks is now written twice, in `process_payment` and in `assess_case`. They are kept in step by a property test over 300 generated cases and by the legacy corpus, not by shared code. Sharing the code would mean restructuring `process_payment`, which is a larger change to authorization-critical code than the benefit justifies before RP-803.

## DD-30. Mutation testing uses a standard-library runner; triage is the owner's

**Decision.** `backend/scripts/mutation_run.py` generates mutants with six operators from the syntax tree, runs each against the tests named for its file and, if it survives, against the whole suite. It writes `docs/mutation_report.json`. Every survivor needs an entry in `docs/mutation_triage.json` with a class and a reason. An implementer leaves every survivor `open`. The owner triages (H-601).

**Why no tool.** `mutmut` for Python 3.9 stops at 3.3.1 and `cosmic-ray` adds dependencies. Either needs another lock regeneration on top of OD-6. The runner is about 250 lines with no dependency and gives an identical report on Python 3.9 and 3.13.

**Why nothing is pinned.** The mutants depend on the exact text of files that implementers write. The contract pins the tool's behaviour on fixed examples and the agreement of report and triage record.

**Why staleness does not fail the suite.** A later task that edits a target file would otherwise have to rerun the tool and triage, and triage is a judgement. `--check` reports a stale report. The owner reruns before the sealed run.

**Trade-off.** Six operators. A surviving mutant is a finding. A killed one proves little. On the dry-run code 99 of 102 mutants were killed and the other 3 were equivalent, which says the Phase 1 and Phase 5 code is tightly tested and says nothing about the older gate code, where a first look found survivors (RP-607).

## Open decisions for the owner

An implementer never resolves these.

| ID | Question | Needed before | Default if unanswered |
| --- | --- | --- | --- |
| OD-1 | Keep Python 3.9 in the CI matrix? It reached end of life in October 2025, and each new development dependency must still support it. Since 2026-11-15 it also needs the backend CI job pinned to `ubuntu-24.04` (DD-11). | RP-105 | Keep 3.9 and pin versions that support it |
| OD-2 | Licence for RemitBench data. The repository is all-rights-reserved today, which prevents reuse. | RP-206 | Do not release |
| OD-3 | Which local model, and a second model family for `P-2llm`? | RP-305 | One model; `P-2llm` is skipped and reported as not run |
| OD-4 | Who are the seed authors and the second labeller? | RP-203 | Blocked. No substitute. |
| OD-5 | May an agent commit on a task branch? | Any time | No (DD-23) |
| OD-6 | OR-Tools needs numpy 2.0.2 or newer. The newest numpy for Python 3.9 is 2.0.2, and it has no wheel for Python 3.13. How should the development lock handle that? (a) One lock compiled under Python 3.9; under Python 3.13 pip builds numpy from source, which took 365 seconds in the dry run and needs a C compiler. CI on Linux can do it, and the pip cache keeps the built wheel. A Windows machine with Python 3.13 and no compiler cannot install the lock. (b) Drop Python 3.9 (OD-1). Then one ordinary lock has wheels everywhere. (c) A separate lock for the oracle, installed under one Python version only, with the CP-SAT tests in their own directory and their own CI job. (d) Two numpy pins with environment markers in one lock, merged by hand after every compile. Only (a) was dry-run. | RP-505 | (a). RP-505 is written for it and stops if the owner chose otherwise. |

## Change log

| Date | Change | By |
| --- | --- | --- |
| 2026-11-11 | DD-01 to DD-25 and OD-1 to OD-5 recorded | Specification author |
| 2026-11-16 | DD-28 (a match must survive its own proof), DD-29 (case assessment beside the decision path) and DD-30 (standard-library mutation runner, owner triage) recorded while writing and dry-running the Phase 6 contracts. DD-28 changes a decision path and only removes automatic decisions. Findings F5 to F7 recorded in `AUDIT_VALIDATION.md` section 12. Needs owner acceptance with the Phase 6 contracts. | Specification author |
| 2026-11-15 | DD-11 amended: the backend CI job is pinned to `ubuntu-24.04`, because `ubuntu-latest` (Ubuntu 26.04) has no Python 3.9. OD-1 notes the new cost. No decision about what may be authorized changes. | Specification author |
| 2026-11-14 | DD-06 revised (four limits from RP-507, credit limit per invoice, allocation cap), DD-16 revised (solver interface, the oracle as a test helper, CP-SAT statuses by known answer), DD-15 validated, DD-12 extended (OR-Tools pin), DD-22: reserved reason `solver_timeout` withdrawn, DD-24 checked against the allocation cap, OD-6 added. All while writing and dry-running the Phase 5 contracts. The allocation cap is stricter than before: a ledger with more than 2048 exact allocations is now refused. The raised invoice and credit limits allow new automation and are stated as such in RP-507. Needs owner acceptance with the Phase 5 contracts. | Specification author |
| 2026-11-13 | DD-21 location revised (evaluation code in `backend/remitbench/`, not `backend/app/eval/`). DD-27 added. DD-13 stands, but the task that may edit the prompt is now RP-307, not RP-303. While writing and dry-running the Phase 3 contracts. Needs owner acceptance with them. | Specification author |
| 2026-11-13 | DD-20 extended (salted split, commitment never overwritten, sentence-fingerprint leak guard). DD-26 added. Both while writing and dry-running the Phase 2 contracts. Needs owner acceptance with them. | Specification author |
| 2026-11-12 | DD-04, DD-05, DD-07 and DD-09 revised, DD-06 extended, DD-08 and DD-11 validated, while writing and dry-running the Phase 1 contracts. Each revision makes the rule simpler or stricter. None loosens what may be authorized. Needs owner acceptance with the Phase 1 contracts. | Specification author |
