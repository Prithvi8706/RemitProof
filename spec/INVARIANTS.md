# Invariants

No task may weaken an invariant. A task that touches an authorization-critical module lists the invariants it must preserve and the test that shows each one still holds.

"Status at v0" is the state at commit `80fc1d7`. "Fails" means a concrete counterexample exists and is recorded as a probe in `backend/tests/test_soundness_probes.py` (RP-002).

## Authorization invariants

| ID | Invariant | Status at v0 | Evidence | Enforced by | Established by |
| --- | --- | --- | --- | --- | --- |
| INV-01 | Every amount is an exact decimal with at most two places. No float enters a financial comparison. | Holds | `backend/app/utils/money.py:11`, `backend/app/models/payment.py:13-26` | Model validators; existing tests | Exists. Property test in RP-601. |
| INV-02 | Nothing the model returns authorizes a decision by itself. There is no confidence input. | Holds | `backend/app/services/evidence_sufficiency.py:382-395` | Existing gate tests | Exists |
| INV-03 | Free text in a proposal (`semantic_claims[].claim`, `unresolved_questions`) never changes a decision. | Holds by inspection | `evidence_sufficiency.py:41-46` checks IDs only | Not yet tested | RP-601 |
| INV-04 | Every cited evidence ID resolves to a supplied record. | Holds | `evidence_sufficiency.py:27-55` | Existing tests | Exists |
| INV-05 | Text the reader could not classify is never treated as absent. | **Fails (F2)** | Three probes | Probes, then gate tests | RP-108 |
| INV-06 | An incomplete search never establishes uniqueness. | **Fails (F3)** | Two probes | Probes, then property test, then differential tests of the solver | RP-103, RP-104, RP-106, RP-502, RP-506, RP-507 |
| INV-07 | For a fixed input, at most one allocation is authorizable. The outcome does not depend on which allocation was proposed. | **Fails (F4)** | Two probes | Probes, then subset test | RP-110 |
| INV-08 | A contradiction between a proposal and a relevant instruction blocks resolution. | Holds for language the lexicon covers | `backend/app/services/proof_engine.py:353-436` | Existing tests | Measured in Phase 4 |
| INV-09 | Document text cannot change a rule, a threshold or the set of eligible records. | Holds for rules. Text can steer the reader (F2). | By design | Injection tests | RP-404, RP-604 |
| INV-10 | An investigator failure, a validation failure or an internal exception never produces an automatic decision. | Holds | `backend/app/services/pipeline.py:128-144` | Existing tests | Exists. Not extended in Phase 1: exceptions propagate, and no catch-all is scheduled. |
| INV-11 | A payment that shares a bank-transaction fingerprint with another payment in the dataset is never allocated automatically. | Holds within one dataset | `pipeline.py:51-77`, `backend/app/utils/loaders.py:28-43` | Existing tests | Exists |
| INV-12 | A cap, a budget or a timeout maps to `unknown`, and `unknown` maps to human review. | Not applicable (the state does not exist) | | Property test; solver status tests | RP-102, RP-503, RP-504, RP-507 |
| INV-13 | A reader's assertion can remove allocations from consideration. It can never add a record. | Not applicable | | Constraint-builder tests | RP-407 |
| INV-14 | An identifier mention that matches zero or several ledger records is never resolved by guessing. | Not applicable | | Resolution tests | RP-402 |
| INV-15 | Adding records that cannot take part in any allocation (wrong currency and no relation to the payer) never changes a decision. RP-601 fixes the exact input model. | Not verified | | Property test | RP-601 |
| INV-16 | Shuffling the order of input records never changes a decision. | Not verified. Holds for the verifier-only baseline on one fixture (RP-003). | | Property test | RP-601 |
| INV-17 | A decision is reproducible from its logged inputs. | Not applicable | | Replay test | RP-703 |

## Process invariants

| ID | Invariant | Enforced by | Established by |
| --- | --- | --- | --- |
| INV-P1 | Files under `data/`, `results/` and `backend/app/prompts/` change only through a reviewed generation bump. | `backend/tests/test_frozen_inputs.py` | RP-001 |
| INV-P2 | `CandidateBundle` and the retrieval that builds it are byte-stable. | Control test in RP-002; equality test in RP-101 | RP-002 |
| INV-P3 | The published result contract is unchanged through Phase 7. | Existing contract tests; rule R-03 | DD-01 |
| INV-P4 | Runtime code never reads ground truth. Only evaluation scripts and tests call `load_ground_truth`. | `test_baseline_module_never_reads_ground_truth` (RP-003); review | Exists |
| INV-P5 | Sealed test data and its gold labels never enter the repository or an implementer's context. | Leak guard (RP-207); owner control | RP-206 |
| INV-P6 | No existing test is deleted, skipped, loosened or given a changed expected value unless a contract names the test and the exact change. | Review; rule R-06 | Now |
| INV-P7 | The suite's pass count never drops between tasks. Expected counts are recorded per task in `PROGRESS_LEDGER.md`. | Verification commands | Now |
| INV-P8 | A strict expected-failure marker is removed only by the task named in its `reason`. | Review; rule R-07 | RP-002 |

## Status after Phase 1, as specified

Observed in the dry run of RP-101 to RP-111. It becomes fact when those tasks are accepted.

| ID | Status after Phase 1 | Shown by |
| --- | --- | --- |
| INV-05 | Holds for any clause that contains an invoice or credit ID and that the reader cannot classify. Does not hold for a clause the reader classifies wrongly (F2 residual, one probe still marked). | RP-108 tests; three probes pass |
| INV-06 | Holds. | RP-103 and RP-104 tests; two probes pass; property tests of RP-106 |
| INV-07 | Holds. | RP-110 tests; two probes pass; permanent single-authorizable test |
| INV-12 | Holds for the retrieval caps and the search limits. The solver budget is RP-504. | RP-102, RP-103 tests |
| INV-P2 | Holds. One hash over all 80 legacy prompt bundles is pinned. | RP-101 test |
| INV-P6 | Three pre-existing tests change what they expect, each named with its exact change in the RP-109 contract. The only other edits to existing test files are the probe marker removals (RP-103, RP-104, RP-108, RP-110) and the extra `build_report` argument in `test_audit_baseline.py` (RP-111). | RP-109 |

## Status after Phase 5, as specified

Observed in the dry run of RP-501 to RP-508. It becomes fact when those tasks are accepted.

| ID | Status after Phase 5 | Shown by |
| --- | --- | --- |
| INV-01 | Holds inside the solver as well. Amounts become integer minor units through an exact conversion that raises on a fraction of a minor unit. No float is used. | RP-501 tests 1 to 7 |
| INV-06 | Holds with the solver as the search. `search` returns alternatives only when the solver's status is `complete`. A stop at the solution limit or the node budget returns no allocation at all. | RP-503, RP-504 and RP-507 tests; the differential tests of RP-502 and RP-506; the RP-106 property tests pass unedited |
| INV-12 | Holds for every limit that exists: the retrieval caps, 64 invoices per customer, 8 credits per invoice, 2048 allocations, 2,000,000 nodes. Each maps to `unknown` and then to human review with reason `search_incomplete`. | RP-507 tests 7, 9 to 12, 19 and 20 |
| INV-P2 | Holds. The prompt bundles, the frozen files and the v1 audit report are unchanged after every Phase 5 task. | Both `--check` commands; RP-101 hash test |
| INV-P6 | Five pre-existing tests change, each named with its exact new text in the RP-507 contract: four in `test_search.py` and one in `test_pipeline_search.py`. No other existing test is edited in Phase 5. | RP-507 section 12 |

## Status after the written part of Phase 6, as specified

Observed in the dry run of RP-601, RP-604, RP-606, RP-605 and RP-603. It becomes fact when those tasks are accepted.

| ID | Status after Phase 6 | Shown by |
| --- | --- | --- |
| INV-01 | Holds as a property: every accepted amount is a whole number of cents, sums are exact and independent of order, and no float appears in any generated or legacy result. | RP-601, tests 14 to 19 |
| INV-03 | Verified. Free text in a proposal never changes a generated or a legacy result. | RP-601, tests 8 and 9 |
| INV-07 | Holds as a property: whatever is proposed, at most one allocation can be decided for a fixed input. | RP-601, test 11; RP-605, test 9 |
| INV-08 | Now holds on the rules-only path for every contradiction the proof engine records (finding F5 closed). It still depends on the reader recognising the instruction: F6 and F7 are open. | RP-606; the F6 and F7 probes of RP-604 |
| INV-09 | Holds for the cases tested: text without an identifier changes nothing, an identifier in unclassified text blocks, sender look-alikes are not trusted, very large inputs finish. | RP-604, tests 2 to 6 |
| INV-10 | Holds as a property: without a usable proposal nothing is resolved. | RP-601, test 12 |
| INV-15 | Verified inside a fixed input model: added customers that share no word with the payer, with invoices in another currency, their credits, their emails, and other payments with another bank reference never change a result. One step outside the model a result does change, correctly: an unrelated customer's invoice in the payment's currency with exactly the payment's amount. | RP-601, section 6.2 and test 13 |
| INV-16 | Verified inside a fixed input model: each of the five record lists may be permuted independently. The order of sentences inside an email is outside the model. | RP-601, section 6.1 |

Three new findings, recorded as probes by RP-604 (definitions in `AUDIT_VALIDATION.md`, section 12):

| Finding | Invariant it touches | State |
| --- | --- | --- |
| F5. A fully read instruction that names other invoices does not stop a rules-only match. | INV-08 | Closed by RP-606 |
| F6. A prohibited identifier in another spelling (`INV-C`, `INV C`, `INVC`, full-width, zero-width inside) is not seen. | INV-05, INV-14 | Open. Five strict probes. Designed answer: DD-19, Phase 4. |
| F7. A hold that names no identifier is not read. | INV-05, INV-08 | Open. Four strict probes. Measured by the reading policies of Phase 4 (DD-18), or accepted by the owner as a stated limit. |

## How a task uses this file

A contract's "Financial correctness invariants" section lists the IDs the task could affect and states, for each, the observable check. If an implementer sees any other invariant at risk, that is a stop condition.
