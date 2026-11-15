# Audit baseline (v0)

This file records the state of RemitProof at commit `80fc1d7` (2026-10-24), tagged `v0-audit-baseline`. It is a fixed reference. Later work is compared against it.

All figures are computed on the 80-receipt synthetic corpus in `data/`. That corpus is a regression fixture. It was written together with the verifier's lexical rules, so no figure here is evidence of how the system behaves on text it was not written against.

## Measured figures

Scope: the 30 truth-labelled exceptions that the rules-only baseline does not resolve. 18 of them should be resolved. 12 should go to human review.

| System | Correct resolutions | Wrong automatic resolutions | Correct abstentions | False escalations |
| --- | --- | --- | --- | --- |
| Rules only | 0 | 0 | 12 | 18 |
| Model proposal alone (forced to answer) | 12 | 18 | 0 | 0 |
| Published pipeline: cached model proposals plus verifier | 9 | 0 | 12 | 9 |
| Verifier only: no model | 18 | 0 | 12 | 0 |

Sources: rows 1 to 3 are in `results/metrics.json`. Row 4 is in `audit/v0/verifier_only_baseline.json`, written by `backend/scripts/audit_baseline.py`.

The published run replays 30 cached proposals whose model identity is not verified. Its own status is `offline_verifier_regression_only`.

Uncertainty: 0 wrong in 9 automatic resolutions gives a one-sided 95% upper bound of 28.3% on the wrong-resolution rate. 9 correct in 18 gives a 95% Wilson interval of 29.0% to 71.0% on coverage.

## Findings

Each finding is recorded as a test in `backend/tests/test_soundness_probes.py`. A probe states the safe behaviour, fails today, and is marked as a strict expected failure. The suite reports 8 expected failures until the fixes land.

### F1. The model adds nothing on this corpus

Trying every financially valid allocation against the unchanged proof and sufficiency checks, and resolving only when exactly one passes, gives 18 correct resolutions and 0 wrong. The pipeline with model proposals gives 9. The nine false escalations come from the model's choice of allocation and citations, not from a hard case.

This is a property of the corpus as much as of the verifier. All 18 resolvable cases carry the same instruction sentence, and the verifier's rules were written for that sentence.

Reproduce: `python backend/scripts/audit_baseline.py --check`.

### F2. The verifier can authorize the wrong invoices when it cannot read an instruction

When an email names the paid invoice with a verb the lexical reader does not know ("this transfer settles INV_C") and names other invoices in a clause the reader does classify ("we will use a separate transfer for INV_A and INV_B"), the reader treats the second clause as the instruction. A proposal for INV_A and INV_B resolves. A proposal for INV_C is rejected as contradictory.

Probes: `test_f2_unread_instruction_must_not_authorize_the_wrong_invoices` (three wordings) and `test_f2_residual_misread_sentence_must_not_authorize_the_wrong_invoices`.

### F3. Uniqueness is claimed on a truncated search

Retrieval keeps at most eight invoices in total and does not say when it drops one. With ten open invoices, where one equals the payment and two dropped invoices also sum to it, the rules-only path returns `matched_normally`. No model is involved.

Probes: `test_f3_truncated_search_must_not_match_in_the_rules_only_path` and `test_f3_truncated_search_must_not_resolve_a_proposal`.

### F4. Authorization depends on which customer is proposed

Evidence is evaluated relative to the proposed customer. When two customers share a known payer and each customer's own mailbox instructs that the same payment be applied to its own invoice, a proposal for either customer resolves. The instructions conflict, so the safe outcome is human review.

Probe: `test_f4_conflicting_customer_instructions_must_not_resolve` (both directions). The verifier-only baseline reports this situation as `multiple_authorizable_allocations`.

## What this baseline does not show

- Behaviour on remittance text written by anyone other than the author of the verifier.
- Behaviour with a live model. No identity-verified model run is recorded.
- Behaviour on ledgers where payments share customers. No two payments in the corpus do.

## Reproducing this file

| Check | Command |
| --- | --- |
| Frozen inputs are unchanged | `python backend/scripts/freeze_manifest.py --check` |
| Verifier-only report matches a fresh run | `python backend/scripts/audit_baseline.py --check` |
| Probes fail for the documented reason | `python -m pytest -q backend/tests/test_soundness_probes.py --runxfail` |
| Full suite | `python -m pytest -q backend/tests` |

Expected at this baseline: 60 frozen files, the report matches, 8 probes fail and 6 control tests pass under `--runxfail`, and the full suite reports 318 passed and 8 expected failures.
