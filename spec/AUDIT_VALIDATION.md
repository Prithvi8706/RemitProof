# Audit validation

Independent re-check of "RemitProof: Audit and Technical Plan" (2026-11-10) against the repository and its commit history. Performed 2026-11-11.

Result: the three audit findings reproduce exactly. Eight statements in the audit need correction. One additional false-authorization path (F4) was found. Two audit recommendations are replaced because they conflict with code the audit had only skimmed.

## 1. Repository state

| Check | Result |
| --- | --- |
| `HEAD` of `origin/main` | `80fc1d7b9f1a9bc0bfc7490aba7d84c2aac7d00e`, same commit the audit used |
| Commits | 15, from 2026-08-31 to 2026-10-24 |
| Branches and tags | Five branches, no tags. Corrected 2026-11-14: the first version of this table said one branch. `main` is at `80fc1d7`. `dev` (`c55cf2e`) is an ancestor of `main`. `review/sol-final-hardening`, `docs/engineering-review-retrospective` and `refinement/proposal-proof-conflict` are the source branches of pull requests #1, #2 and #3. Each tip has the same tree as its merge commit on `main` (`5276a63`, `05e8f9e`, `f510cfd`). No work exists outside `main`. |
| Last change to `backend/app/services`, `backend/app/utils`, `data`, `results` | `f510cfd`, 2026-09-05 |
| Last change to `backend/tests`, `docs` | `9bb51e5`, 2026-09-05 |
| Last change to `backend/app/prompts`, `backend/scripts` | `5276a63`, 2026-09-01 |
| Content of `80fc1d7` | Adds `LICENSE` only |
| Working tree after every validation run | Clean |

Because no code changed after the audit, every existing path and line number the audit cites still resolves. No stale path was found. Paths the audit marked as new remain proposals; two of them are superseded (C3, C5).

## 2. Claims reproduced

Environment: Python 3.13.18, pytest 8.3.5, pydantic 2.11.5, installed from `backend/requirements-dev.txt`.

| Audit claim | Method | Observed | Status |
| --- | --- | --- | --- |
| 283 backend tests pass | `python -m pytest -q backend/tests` | 283 passed | Reproduced |
| 91% line and branch coverage; core modules 93% to 99% | `--cov=backend/app --cov-branch` | Total 91%. `evidence_sufficiency.py` 99%, `candidate_retriever.py` 98%, `pipeline.py` 97%, `baseline_matcher.py` 96%, `alternative_finder.py` 95%, `proof_engine.py` 94%, `remittance_semantics.py` 93% | Reproduced |
| F1: verifier-only enumeration gets 18 correct, 0 wrong, 12 correct abstentions, 0 false escalations | Scratch enumerator, then the RP-003 and RP-004 dry run | 18, 0, 12, 0 overall. Dev 5, 0, 5, 0. Benchmark 13, 0, 7, 0. | Reproduced twice, by two implementations |
| Published pipeline: 9 correct, 0 wrong, 12 correct abstentions, 9 false escalations | `results/metrics.json` | Same | Reproduced |
| Cached model allocation exactly right in 12 of 18 resolvable cases | Compared `results/proposal_cache.json` with `data/ground_truth.json` | 12 of 18 | Reproduced |
| F2: three emails make the verifier resolve the wrong invoices and reject the right ones | `process_payment` with fixed proposals | 3 of 3: wrong proposal `resolved`, right proposal `human_review` with `contradictory_evidence` | Reproduced |
| F3: customer with 10 open invoices gets `matched_normally` on a truncated search | `process_payment` | Retrieval kept 8, dropped `INV_090` and `INV_091`, decision `matched_normally` | Reproduced |
| 24 emails reduce to 7 templates; all 18 resolvable cases share one instruction sentence | Masking IDs, names, amounts | 7 templates. The sentence "Apply the ... receipt only to ..." appears in all 18. | Reproduced |
| No two payments share a customer | Ground truth | 0 shared | Reproduced |
| Exhaustive enumeration cost doubles per invoice | Timed `find_valid_alternatives` | 8: 1.3 ms. 12: 28 ms. 16: 597 ms. 20: 10.4 s. Audit recorded 1.5 ms, 31 ms, 632 ms, 11.4 s on another run. | Reproduced (same growth) |
| Per-payment latency grows with ledger size | Replicated easy cases | 0.7 ms at 50 payments, 5.6 ms at 500, 22.2 ms at 2,000 | Reproduced |
| Published run is `offline_verifier_regression_only` with unverified legacy proposals | `results/metrics.json`, `results/proposal_cache.json` | Status as stated. 0 of 30 cache entries are identity-verified. | Reproduced |
| 0 wrong in 9 gives a 95% upper bound of 28.3%; 9 of 18 gives a Wilson interval of 29.0% to 71.0% | Recomputed | Same | Reproduced |

## 3. Corrections to the audit

**C1. The invoice cap is global, not per customer.** The audit says truncation affects "any customer with more than 8 scored invoices". The cap of 8 applies to all scored invoices across every candidate customer (`backend/app/services/candidate_retriever.py:250-255`). Truncation can therefore occur when no single customer has more than 8 invoices.

**C2. Retrieved invoices are not limited to candidate customers.** An open invoice with the payment's currency, a due date within 180 days and the exact payment amount scores 45 + 25 + 50 + 10 = 130 and is retrieved even when its customer is not a candidate (`candidate_retriever.py:235-247`). `find_valid_alternatives` then enumerates per customer over all retrieved invoices (`backend/app/services/alternative_finder.py:61-63`), and those allocations count as competing alternatives in the gate (`backend/app/services/evidence_sufficiency.py:348`). The audit defined the proof set as "all invoices of the candidate customers". That definition would remove competing alternatives and could turn an ambiguous case into a unique one. Replaced by the superset rule in DD-04.

**C3. Audit Task 4 is unsafe as written.** It says to add a fourth system to `_row_from_result` and the comparison dictionary in `backend/app/services/evaluator.py`. The audit had only skimmed `backend/app/utils/results.py`. That module validates the published snapshot strictly (`_validate_comparison` at `results.py:163-192`, `_validate_metric_set` at `:195-253`, required CSV columns at `:907-939`), many API tests read the committed snapshot, and the frontend renders the three named systems. Changing the evaluator output forces a republish, a results-contract change and a frontend change, for no measurement benefit. Replaced by DD-02: Phase 0 writes a separate audit report and leaves the evaluator untouched. The dry run confirms the separate report reproduces the evaluator's own baseline counts and dataset hash.

**C4. Placeholder identifiers leak into 6 cached proposals, not 2.** The audit names PAY_052 and PAY_067. `EMAIL_EXAMPLE` or `CUS_EXAMPLE` from `backend/app/prompts/investigator.txt:42-45` appears in the cached proposals for PAY_052, PAY_058, PAY_062, PAY_067, PAY_073 and PAY_077. All six are should-abstain cases, so the leak did not cause any of the nine false escalations.

**C5. Four probes become eight.** The audit specifies three F2 probes and one F3 probe. The validated set has three F2 probes, one F2 residual probe, two F3 probes (one per code path) and two F4 probes. See `tasks/RP-002.md`.

**C6. Phase 0 and Phase 1 estimates were low.** Phase 0 rises from 10 to 16 hours (guard manifest, F4 probes, separate report). Phase 1 rises from 22 to 39 hours (F4 fix, lock regeneration, smaller reviewable steps). The plan total moves from about 220 to 274 hours: 228 implementation hours that can be delegated and 46 hours of human work that cannot (seed authoring, labelling, pre-registration, the report). At 18 hours a week that is about 15 weeks, not 12. The audit's cut order still applies.

**C7. Adding Hypothesis is not a one-line change.** The audit says to add it to `backend/requirements-dev.in`. CI installs with `--require-hashes` from `backend/requirements-dev.lock`, and that lock was compiled with Python 3.9 (see its header). Any new dependency needs a lock regeneration under Python 3.9 and must itself support 3.9. This is owner decision OD-1 and task RP-105.

**C8. The stale documentation line is longer than quoted.** `docs/failure_analysis.md:42` reads "up to eight invoices, three credits, four invoices per allocation, no FX, and no partial-payment schedule". Only "four invoices per allocation" is stale. The eight and three are real and are global caps. RP-005 carries the exact replacement text.

## 4. New finding

**F4. Authorization depends on which customer is proposed.**

Setup: one payment of 10,000.00 USD from a payer that two customers both list under `known_payers`. Each customer has one open invoice of 10,000.00. Each customer's own trusted mailbox sends "Apply BNK-1 only to" its own invoice.

Observed at `80fc1d7`: a proposal for customer A resolves. A proposal for customer B also resolves. Both carry the reason "Evidence uniquely supports the proposed allocation". The result is the same when the proposal cites both emails.

Cause: the gate evaluates evidence relative to the proposed customer only. `_evidence_disambiguates` skips emails of other customers (`evidence_sufficiency.py:104`), and the proof engine's contradiction loop does the same (`backend/app/services/proof_engine.py:353-355`). Conflicting instructions from another customer are never seen.

Consequence: for the same input, two different allocations are each authorizable. Which one is posted depends on the model's guess. This breaks the rule that the model cannot decide. It is recorded as invariant INV-07, probed in RP-002, detected by the verifier-only baseline as `multiple_authorizable_allocations` (RP-003), and closed by RP-110 under DD-09.

The verifier-only baseline finds at most one authorizable allocation for every legacy case, so F4 does not affect any published number.

## 5. Unsupported assumptions and unresolved decisions

| Item in the audit | Problem | Settled by |
| --- | --- | --- |
| "Keep `CandidateBundle` unchanged" | Correct, and stricter than stated: the bundle is hashed into every cache key (`evaluator.py:91-96`) and sent to the model (`backend/app/services/ai_investigator.py:109`). Any field or ordering change invalidates all 30 cached proposals. | DD-03 |
| Proof set definition | See C2 | DD-04 |
| Closed-world rule: an unread document "cannot support an allocation" | Not fail-closed enough. If the payment reference selects an allocation and an unread email says otherwise, "cannot support" still resolves. | DD-07: an unread instruction blocks authorization |
| "Let every trusted email for the proposed customer count" | Still relative to the proposed customer. Does not address F4. | DD-08 with DD-09 |
| Where the verifier-only baseline applies the pipeline's pre-investigator gates | Unspecified. Re-implementing the three gates invites drift. | DD-10: the baseline is an `Investigator` adapter, so the unchanged pipeline applies its own gates |
| Evaluator generalization in Phase 3 | Same contract problem as C3 | DD-21: a new harness; the legacy evaluator stays frozen |
| Whether result models may gain fields | Every result model uses `extra="forbid"` and is serialized into `details.json` | DD-01 |
| Who commits and tags | Unspecified | DD-23, owner gates in `PROGRESS_LEDGER.md` |
| Python version floor | Unspecified. CI runs 3.9 and 3.13. | DD-11, OD-1 |
| Running `backend/scripts/evaluate.py` during development | With default arguments it rewrites `results/` and mutates `results/proposal_cache.json` (`backend/scripts/evaluate.py:135`, `:165`, `:114-116`) | Rule R-12 in `IMPLEMENTER_RULES.md`, guard in RP-001 |

## 6. Not validated

- Frontend code (about 4,000 lines of TypeScript). Not reviewed.
- Live model behaviour. No Ollama model was available. Statements about the model rest on the 30 cached proposals.
- The deployed demo.
- Python 3.9 execution of the Phase 0 tasks one by one. Each Phase 0 task was run on 3.13 only. The complete Phase 1 result, which contains all of Phase 0, passes on 3.9.25 (section 7).
- `RemitProof_Codex_Implementation_Spec.md`. Not read.
- Every Phase 2 to Phase 8 design decision is recorded and reasoned in `DESIGN_DECISIONS.md`, but only the Phase 0 and Phase 1 contracts were dry-run. Later contracts must be validated when they are written.

## 7. Phase 1 addendum (2026-11-12)

Found while dry-running the Phase 1 contracts in a throwaway copy. Each item was observed, and each changed a contract or a design decision.

| # | Observation | Effect |
| --- | --- | --- |
| P1 | The invoice cap of 8 is hit on 39 of the 80 legacy payments. The largest set of ranked invoices is 25. Enumerating over all ranked invoices gives the same alternatives as the capped view on all 80. | The legacy corpus cannot show finding F3 at all. DD-04 was simplified to "keep the ranking, drop the invoice and credit cuts". |
| P2 | A complete search does not only remove matches. Where the cap hid the only valid allocation, the rules-only path now matches a payment it used to send to review. | Stated as new automation in RP-103 and pinned by a test. Without this note a reviewer would read it as a regression. |
| P3 | The enumerator only tries credit subsets of size up to 3 (`backend/app/services/alternative_finder.py:66`). With four or more eligible credits for one customer it silently skips combinations. No legacy customer has more than 2. | DD-06 extended: more than 3 eligible credits gives `unknown`. |
| P4 | The first wording of DD-07 blocked only when the unread ID was part of a valid allocation. An email saying the transfer clears an invoice that is in no allocation would have passed, and the visible allocation would have been authorized. | DD-07 made strict: any unread ID in any candidate email blocks. |
| P5 | Removing the two citation rules changes exactly three legacy decisions (`PAY_057`, `PAY_063`, `PAY_068`, review to resolved, each equal to its label). Thirteen more payments keep their decision and reason and differ in one reported field. | Predicted case by case in RP-109. The owner signs off the three. |
| P6 | After Phase 1 the stored proposals give 12 correct resolutions, 0 wrong, 6 false escalations. In all six, the stored proposal names a customer, invoice set or credit set that differs from the label. The verifier-only system resolves all six. | Finding F1 stands unchanged: on this corpus the model's proposal is the only thing between 12 and 18. |
| P7 | `backend/scripts/run_spike.py` calls the matcher and the gate directly, not through `process_payment`. It gets none of the Phase 1 gates. | Recorded as a stated limit in `ARCHITECTURE.md` section 1a. Not an authorization path. Left untouched. |
| P8 | The verifier-only adapter enumerates over the prompt view. The runtime authorizes over the proof bundle. They agree on all 80 legacy payments. | Recorded as a stated limit. The baseline is conservative where they differ. |
| P9 | Hypothesis 6.141.1 is the newest release that supports Python 3.9. Regenerating the development lock under 3.9.25 adds three packages and changes none. The full suite passes from the hash-locked environment on 3.9.25 and 3.13.18. | RP-105 pins the version. OD-1 still belongs to the owner. |
| P10 | The property tests of RP-106 run four properties on 300 generated ledgers each. Four deliberate defects were injected one at a time, and each was caught. | Evidence that the properties can fail. |
| P11 | The three sandbox examples in `backend/app/sandbox_examples.json` give the same decision, reason and allocation before and after Phase 1. | The demo flows are unaffected. |

Not validated in Phase 1:

- The cost of the strict unread rule on real remittance text. The legacy corpus has no email with an unread ID, so it says nothing.
- Windows. Hashes are taken on LF bytes. Contracts say what to do on a CRLF checkout, and that path was not exercised.
- The lock regeneration on the owner's machine. It was done on Linux with pip 26.0.1 and pip-tools 7.6.2.
- The frontend, at run time. Phase 1 changes no result field, but four new reason strings (`search_incomplete`, `unread_instruction`, `multiple_authorizable_allocations`, `proposal_not_authorizable`) can reach the sandbox response. By reading the code only: an unknown reason is shown in title case, for example "Unread Instruction" (`frontend/lib/format.ts:131-133`). Nothing breaks, and the text is not explanatory. Proper wording belongs to RP-605 and RP-803.

## 8. Phase 2 addendum (2026-11-13)

Found while designing and dry-running the Phase 2 contracts. Each item changed a contract, a design decision or the inventory.

| # | Observation | Effect |
| --- | --- | --- |
| Q1 | The suite runs with `backend` on the import path (`backend/pytest.ini`). A Python package in `bench/` at the repository root, as the audit proposed, would not be importable by the tests without changing how every test is collected. | Code is `backend/remitbench/`. `bench/` holds documents and data only. |
| Q2 | The runtime recognizes only identifiers of the form `INV_`, `CR_` or `EMAIL_` followed by letters and digits (`backend/app/utils/normalization.py:6`). Seeds written by other people will use their own numbering, for example `HF/26-27/0412`. | Expected and wanted: this is hypothesis H1. On such seeds the v1 system will mostly send payments to review until RP-402 lands. On the three example seeds the verifier-only system reviews two and resolves one. Those three are tooling fixtures and prove nothing. |
| Q3 | The audit planned resampled amounts and entity names. An author's email can state an amount or a company name in free text, in any format. Changing the record without changing the text creates a contradiction the author did not write, and no rule finds every mention. | The generator renames record IDs only, and only when no message shortens an ID. Amounts, names and dates are never changed by code. |
| Q4 | The audit planned two generated hard-negative twins per seed. Most of the listed edits (a lexical trap, text aimed at the model, removing "the deciding email") need judgement about what the label becomes. | One generated twin, for `allocate` seeds only, with a label that follows from the guide's rules and is confirmed by the oracle: every customer message removed, at least two exact allocations. The other twins are written by people. |
| Q5 | H-203 (second labelling, kappa) had no tooling in the inventory: nothing to produce a copy without the first label, and nothing to compute agreement. | RP-208 added, 3 hours. |
| Q6 | "Seal the test set" was folded into RP-206, which an agent implements. An agent must never hold the test seeds. | RP-206 is tooling only, tested on the examples. The sealing is a new human task, H-205. OG-3 and OG-4 now gate human steps, not code. |
| Q7 | The first scope note for RP-207 said "no test-seed identifier in the repository". A seed ID is a counter. | The guard compares one-way fingerprints of test sentences with every sentence in the repository's text files. |
| Q8 | A reorder that happens to produce the original order is a wasted variant. It happened on the first example with the first generator seed tried. | The reorder operator rotates by one in that case. Found only because the dry run asserted the order. |
| Q9 | A human would accept "oldest invoice first" as a reason to post. If the benchmark allowed that, the generated twin's label would be wrong. | The guide states three rules of the benchmark's world, and RP-205's correctness is tied to them in its contract. The owner must not relax them without revisiting RP-205. |
| Q10 | Generated output is byte-identical on Python 3.9.25 and 3.13.18. | The generator uses SHA-256 draws, not the `random` module. One tree hash is pinned. |

Not validated in Phase 2:

- Anything about real seeds. No seed from another author exists yet. Every Phase 2 figure comes from three examples written by the specification author.
- Whether authors without a technical background can fill in a JSON template. If they cannot, the owner transcribes their seeds, and that transcription is a place where the owner's wording can leak in. Watch for it.
- The guide's labelling rule against real disagreement. Kappa will show it.
- Model paraphrases. They are files made outside this repository by a model family that is never used as a reader. The validator checks that only text changed. It cannot check that the meaning is kept.

## 9. Phase 3 addendum (2026-11-13)

Found while designing and dry-running the Phase 3 contracts.

| # | Observation | Effect |
| --- | --- | --- |
| S1 | The plan put the evaluation harness in `backend/app/eval/`. It reads gold labels, and the boundary test of RP-201 forbids any import of the benchmark tooling from `backend/app/`. | All evaluation code is in `backend/remitbench/`. DD-21 revised. |
| S2 | The audit's fix for the comparison was to edit `_comparison` in the legacy evaluator. DD-21 already froze that file. A system-agnostic decisions file does the same job with no edit to published code. | Systems write decisions files. Scoring reads only those. DD-27. |
| S3 | "Exception" was defined in the legacy numbers as "not matched by the rules-only baseline". Under that rule a payment the baseline matches wrongly disappears from every other system's denominator. | An easy case is one the baseline allocates correctly. A wrong baseline allocation stays among the exceptions. |
| S4 | When no model is present the pipeline's review reason is a sentence about the missing investigator, not about the payment. | The `rules_only` system reports the baseline's own reason. |
| S5 | The Wilson formula returns 2.8e-17 and 0.9999999999999999 at the two ends. | The ends are set exactly. Found only because the dry run printed the raw values. |
| S6 | With three seeds, the seed-level bootstrap interval for coverage is 0% to 100%. | Correct, and useful: it is a built-in demonstration that the example seeds say nothing. Kept as a pinned test value. |
| S7 | RP-303 as first scoped did three things: a new baseline, an edit to the frozen investigator prompt, and a freeze generation bump. The second and third strand the 30 stored proposals and cannot be dry-run without a model. | Split. RP-303 is the baseline only and changes no frozen file. The prompt fix is RP-307, not yet written. |
| S8 | The product's prompt contains a worked JSON example with placeholder identifiers, and six stored proposals repeat them (C4). | The new baseline's prompt has no example object and no identifier. A test enforces it. |
| S9 | A model that is down for a whole run produces identical runs of all-review decisions. The manifest then says "deterministic". | Stated in the RP-305 contract as a limit. The owner reads the decisions before using a run. |
| S10 | Six systems were planned. Two of them are the v0 code run on the new benchmark. That needs the old commit to execute on new case files. | Not built. DD-27 records that the decisions-file design allows it and that no task exists for it. |
| S11 | Statistics, decision files and the results table are byte-identical on Python 3.9.25 and 3.13.18. | Hashes pinned in RP-302 and RP-306. |

Not validated in Phase 3:

- Any run with a real model. `llm_abstain`, `basic_validation` and `proposal_pipeline` were exercised only through stand-ins. The Ollama request format in RP-303 follows the existing investigator's and was not sent to a server.
- Whether the abstaining prompt is fair. It was written by the specification author and read by nobody else.
- The pre-registration. It is a document the owner writes (H-301). The metric definitions it must cite are fixed in DD-27.
- Statistical power. With 48 or more test seeds the intervals will be wide. Nobody has computed how wide. That calculation belongs in the pre-registration.

## 10. Phase 5 addendum (2026-11-14)

Found while designing and dry-running the Phase 5 contracts on top of the tree after RP-305. Each item was observed, and each changed a contract, a design decision or the inventory.

| # | Observation | Effect |
| --- | --- | --- |
| X1 | The start tree reproduces. A fresh copy of `80fc1d7` with the Phase 0 to 3 dry-run patch gives 657 passed and 1 expected failure on Python 3.13.18 and 3.9.25, from two new hash-locked environments, and both `--check` commands exit 0. | Phase 5 joins the end of the written line. |
| X2 | Every consumer of `SearchOutcome.alternatives` needs the whole list, not a count. The rules-only matcher filters the list by customer and by referenced invoice IDs before it counts. The gate checks the evidence against every entry. Authorization tests every entry. The result publishes all of them. | "Stops at the second solution" (DD-16) became a parameter. `search` asks for the full list up to a cap and refuses beyond it. A limit of 2 is used only where a bare count is asked. |
| X3 | Once an invoice and its credits are turned into options before the search starts, the search itself has no credit logic at all. A "branch and bound without credits" followed by a "credit options" task would have meant writing the search twice. | RP-501 builds options with credits. RP-502 is the complete search. The ID RP-503 is reused for the solution limit. |
| X4 | The solver returns exactly the allocations of every reference where both are complete. No disagreement over 600 drawn problems against a brute force, 300 generated ledgers checked by four searches at once (solver, enumerator, the RP-106 brute force, CP-SAT), 60 ledgers of 17 to 20 invoices per customer against CP-SAT, 74 adversarial cases, and the 80 legacy payments. | DD-16 validated. The evidence is in RP-502, RP-506 and RP-507. |
| X5 | The generator of RP-106 only draws amounts that are multiples of 50.00. A solver whose two bounds are each wrong by one minor unit passes all 300 of its ledgers. Three of the four families and the large ledgers catch it. | The four adversarial families are not decoration. RP-506 section 10 records which injected defect each family caught and which it missed. No single family caught all seven. |
| X6 | CP-SAT's statuses, by known answer: `INFEASIBLE` is a proof. `OPTIMAL` is a found solution, or a finished enumeration. `FEASIBLE` is an enumeration cut off after at least one solution. `UNKNOWN` is a cut-off with nothing proven, and it was observed on an instance that has a solution. | The oracle reports `unique` only when the second solve is `INFEASIBLE`. A cut-off is never read as "no solution". Limits use CP-SAT's deterministic time, not the clock. |
| X7 | CP-SAT is not fast on this problem either. On ledgers of 18 to 40 invoices per customer it needed up to five seconds per ledger and was cut off in 17 of 120 at a deterministic limit of 2.0. | The large ledgers in the suite stay at 17 to 20 invoices, where no limit is needed. The cross-check does not reach 64 invoices. Stated as a limit below. |
| X8 | OR-Tools 9.15.6755 is the newest release and supports Python 3.9, so keeping 3.9 costs no OR-Tools version. It costs elsewhere: OR-Tools needs numpy 2.0.2 or newer, the newest numpy for Python 3.9 is 2.0.2, and that version has no wheel for Python 3.13. A lock compiled under 3.9 makes Python 3.13 build numpy from source: 365 seconds without a cache, against 9 seconds for the whole install under 3.9. The lock gains ten packages and changes none. | New owner decision OD-6. RP-505 is written for the option that was dry-run and stops if the owner chooses another. |
| X9 | The limit of 3 credits per customer had one reason: the enumerator never combines more than three. The solver does not have that restriction. What grows is the number of options of a single invoice: 256 for 8 credits (0.2 ms), 16,384 for 14 (18 ms). | The credit limit is per invoice and is 8. DD-06 revised. A ledger with four credits on one invoice, refused before, is now searched and its allocation found. |
| X10 | Authorization costs the square of the number of alternatives: 1.3 s at 210 and 6.7 s at 495. A sandbox-sized ledger (8 invoices, 3 credits) can have at most 2040 allocations. The largest the dry run found has 266. | `ALTERNATIVE_LIMIT = 2048`. One new refusal follows: a ledger inside the old limits with more than 2048 allocations was searched before and is `unknown` now. Stated in RP-507 for the owner to accept. |
| X11 | On the legacy corpus RP-507 changes nothing. For all 80 payments the alternatives equal the enumerator's as JSON. 54 unique, 20 ambiguous, 6 none. 50 matched, 12 resolved, 18 review. The v1 audit report, the 60 frozen files, the prompt-bundle hash and the benchmark decision and table hashes are unchanged after every Phase 5 task. The whole corpus needs 1,943 search nodes, at most 62 for one payment. | Predicted case by case in RP-507 and confirmed by tests that were not edited. |
| X12 | A budget of 2,000,000 nodes stops a search after 0.32 to 0.34 s on Python 3.13.18 and 0.46 to 0.49 s on 3.9.25. Inside the old limits it cannot be reached (the largest tree has 589,816 nodes). On synthetic ledgers it is never reached at 8 or 16 invoices, in 66 of 360 at 32 and in 137 of 360 at 64. Another 55 and 104 stop at the allocation cap. At 64 invoices the search answers 119 of 360. At 16 invoices it is about 750 times faster than the enumerator on the same ledgers (0.36 s against 266 s for 360 ledgers). | The limit of 64 is real for payments that cover one or two invoices and nominal beyond. RP-507 and RP-508 say so in their first section, and the table is committed so that the claim can be checked. |
| X13 | A side experiment, not part of any contract: a third bound that keeps, per position, the set of sums still reachable. It returned the same allocation lists as the contract solver on 854 problems (720 scaling ledgers of 8 and 16 invoices, the 60 large ledgers, the 74 family cases) with 178,518 nodes against 3,744,061. On 1,260 synthetic ledgers of 16 to 64 invoices with a solution limit of 257, the two-bound solver hit a budget of 1,000,000 nodes on 286 and the variant hit a budget of 2,000,000 on 5. The two runs used different budgets, so read the pair as a direction and not as a ratio. | Not adopted. DD-16 names two bounds, the owner is to derive the bounds himself, and a table whose size grows with the payment amount is a design decision with a memory cost. It is the obvious next step if 64 invoices is meant seriously. It needs its own task, its own derivation and the same differential tests. |
| X14 | `ARCHITECTURE.md` had reserved a reason `solver_timeout` for RP-504. A budget stop is one more incomplete search, and DD-05 already sends every incomplete search to review as `search_incomplete`. | The reserved reason is withdrawn (DD-22). Two new detail strings, `node_budget` and `alternative_limit`, travel in `Decision.proof["search_detail"]`. No result model changes. |

Changes from the plan, in one place:

| Plan | Written | Why |
| --- | --- | --- |
| RP-502 "branch and bound without credits" | The complete search, credits included | X3 |
| RP-503 "credit options", 3 hours | The solution limit, 2 hours | X2, X3 |
| RP-505 depends on RP-501 only, 4 hours | Placed after RP-504 in the line, 3 hours | The line needs one order. No code dependency on RP-502 to RP-504. |
| RP-506, 3 hours | 5 hours | The oracle is a module of its own, and the known-answer tests (X6) |
| RP-507 "limit raised to 64", 2 hours | Four limits, five existing tests revised by name, 4 hours | X9, X10, X12 |
| RP-508, 2 hours | 3 hours | The table is reproducible and pinned by hash |
| Reason `solver_timeout` | Not introduced | X14 |

Found in the package itself while updating it. The first two were corrected. The third was left for the owner.

- `README.md` said "60 tasks in 10 groups". The inventory has 62.
- The totals row of `TASK_INDEX.md` carried six stale cells from earlier revisions.
- `TASK_INDEX.md` lists RP-206 as a dependency of RP-408 and RP-801. `DEPENDENCY_GRAPH.md` and the generator's task list say H-205. H-205 is probably meant, since the dev split and the commitment exist only after the owner seals. Not changed.

Not validated in Phase 5:

- The lock regeneration on the owner's machine, and the numpy source build in GitHub Actions. Both were done on Linux in the dry run. That a Windows machine with Python 3.13 and no compiler cannot install the lock is an inference, not an observation.
- Options (b), (c) and (d) of OD-6. Only (a) was run.
- CP-SAT on another platform or another OR-Tools release. Three known-answer tests rely on a cut-off at a deterministic limit of 0.001 or 0.01. They gave the same result on Python 3.9.25 and 3.13.18, on one Linux x86-64 machine.
- The solver against CP-SAT above 20 invoices per customer (X7). Above that size the only checks are the solver's own statuses and the scaling table.
- More than 8 credits on one invoice, and large ledgers with credits or several customers. The scaling table has one customer and no credits.
- Any real ledger of 32 or 64 open invoices. None exists in the project. How often a real customer's payment covers one or two invoices, where the search does answer, is unknown.
- Wall-clock times on another machine. All times are from one core of a 2.3 GHz Xeon.
- The frontend. Two new values of `search_detail` can reach a sandbox response only through `Decision.proof`, and by DD-24 no sandbox ledger can produce them. Not checked in the browser.
- The third bound of X13. It was compared with the solver and nothing else. It was not reviewed, not derived on paper and not tested against CP-SAT.
- Windows line endings, as in every earlier phase.
