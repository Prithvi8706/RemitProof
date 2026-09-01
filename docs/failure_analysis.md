# Failure analysis

The final benchmark contains no incorrect automatic RemitProof resolution. That does not mean the system is complete: it conservatively escalated nine exception cases that ground truth marked safely resolvable.

## Observed misses

The nine false escalations occurred in:

- detached remittance email;
- credit deduction (twice);
- alternative-allocation email;
- parent-entity multi-invoice payment (twice);
- semantic credit reason (twice);
- treasury-bank-on-behalf payment.

These are proposal and evidence-citation failures rather than retrieval or arithmetic failures. Required records were retained in every case, but the local investigator sometimes chose an extra invoice or credit, omitted a required record, failed to cite a selected credit, or selected the wrong entity. The verifier correctly rejected those proposals instead of repairing or silently authorizing them.

That trade is visible in the aggregate metrics:

- entity resolution accuracy: 70.0% across exception proposals;
- evidence precision: 76.79%;
- false escalation rate: 50.0% across safely resolvable exception records;
- incorrect auto-resolution rate: 0%;
- retrieval and arithmetic correctness: 100%.

The 60-record synthetic benchmark/regression subset contains seven of the nine false escalations and still has zero wrong automatic resolutions under the supplied truth. Because it reuses scenario templates represented in development, this is regression evidence rather than an independent generalization result.

## Why the safety layer matters

The forced-proposal-without-verification ablation treated all 30 complete exception proposals as authorized and made 18 wrong automatic resolutions. It is a proposal-only verifier ablation, not an independently prompted standalone LLM comparison. Typical unsafe proposal behaviors included guessing between same-amount invoices, trusting unsupported payer relationships, applying absent or contradictory credits, selecting closed or previously allocated records, and ignoring currency or unexplained short-pay problems.

RemitProof blocked those actions through independent checks. It does not convert a bad proposal into a different allocation; a failed proposal becomes human review. This is deliberately conservative and prevents the proof layer from becoming a second opaque matcher.

## Known limitations

The evaluator's arithmetic correctness metric measures whether final system behavior authorizes only arithmetic-valid results; it is not a claim that the language model performs arithmetic correctly. All monetary calculations are recomputed with `Decimal`.

Evidence precision is identifier-level. It does not score sentence quality, provenance strength, or whether a human would find the explanation persuasive. Entity accuracy scores the model proposal even when the final system abstains.

Candidate retrieval is deterministic and perfect on this generated benchmark, but it relies on identifiers, names, amounts, dates, and lexical email signals. It has not been tested against OCR errors, multilingual remittances, noisy production aliases, or very large ledgers.

Alternative enumeration is exact only inside the retrieved set and current MVP limits: up to eight invoices, three credits, four invoices per allocation, no FX, and no partial-payment schedule.

The local model is fixed to one family in the recorded run. Model updates, quantization, and hardware can alter proposal quality and latency even with temperature zero and a fixed seed.

## Highest-value next work

1. Add proposal-level membership validation so invented or cross-customer record combinations fail before deeper proof and produce clearer review reasons.
2. Improve the investigator prompt and examples against development-only false escalations, then run a separately authored, access-controlled benchmark once.
3. Add evidence provenance scoring and explicit support for each semantic claim, rather than identifier precision alone.
4. Test retrieval on noisy, independently authored remittances before increasing candidate limits.
5. Calibrate a production review workflow without weakening any current proof invariant.

Improving exception resolution rate is worthwhile only if zero incorrect automatic resolutions remains the release gate.
