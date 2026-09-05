# Five-minute demo script

## Preflight

Run the API on port 8001 and the frontend on port 3000. Open the dashboard, then keep these detail routes ready:

- resolved exception: `http://localhost:3000/exceptions/PAY_051`
- human review: `http://localhost:3000/exceptions/PAY_052`
- contradicted proposal: `http://localhost:3000/exceptions/PAY_056`

Do not imply that the prototype writes to Razorpay or an accounting system.

## 0:00–0:30 — Boundary

On the dashboard, point to the operational funnel: 80 receipts, 50 reconciled normally, 30 exceptions.

Say: “Normal reconciliation already handles structured matches. RemitProof starts with the 30 exceptions where those signals were insufficient.”

## 0:30–0:55 — Thesis

Point to the pipeline.

Say: “The AI proposes. Deterministic code proves. Conflict detection asks whether another explanation survives. Evidence decides whether the system may act or must abstain.”

## 0:55–2:15 — Complex resolution

Open `PAY_051`.

Show:

- the visible investigation path from normal-match failure to authorization;
- the USD 14,763 payment from `CITIBANK N.A. OBO COPPERLEAF FOODS`;
- why the baseline stopped at an unmapped payer;
- the detached remittance email connecting the treasury bank to Copperleaf Foods International;
- the explicit instruction to use `INV_X051A` and `INV_X051B`;
- the arithmetic: USD 8,267.28 + USD 6,495.72 = USD 14,763.00;
- the competing pair `INV_X051C` and `INV_X051D`, which is also financially valid;
- the proof checklist showing that the remittance uniquely disambiguates the alternatives.

Say: “The model produced a proposal, not a decision. Code recomputed the money, checked state and entity support, found the competing allocation, and authorized only because the remittance evidence cleared that conflict.”

## 2:15–2:55 — Ambiguous proposal

Open `PAY_052`.

Show the two USD 11,544 invoices, `INV_X052A` and `INV_X052B`. There is no remittance evidence selecting one. The raw model proposal also fails deterministic proof, while the alternative finder still exposes both financially valid explanations.

Say: “Both explanations are plausible. Neither is justified strongly enough to execute. The product succeeds by blocking the decision and naming the evidence a controller needs.”

Point to `HUMAN REVIEW` and the missing/disambiguating evidence message.

## 2:55–3:25 — Contradicted proposal

Open `PAY_056`.

Show the financially plausible deduction, then the structured contradiction record and blocked-decision artifact.

Say: “Arithmetic can make a proposal plausible. Authoritative evidence can still make it unsafe. The contradiction is a successful control outcome, not a processing error.”

## 3:25–3:55 — Architecture

Open `docs/architecture.md` or use the dashboard pipeline.

Say: “The trust boundary is AI equals semantic investigation; code equals financial proof. Ground truth is evaluation-only and never enters retrieval, prompting, proof, or decisions.”

Mention the fail-closed path: invalid model output, failed arithmetic, state conflicts, duplicate risk, unsupported entities, contradictory credits, and non-unique explanations all route to review.

## 3:55–4:35 — Benchmark

Return to the dashboard comparison.

Say: “On 30 synthetic exceptions, baseline resolved none. A forced-proposal-without-verification ablation treated all 30 complete proposals as authorized and got 18 wrong. This is a verifier ablation, not an independent standalone-LLM comparison. RemitProof resolved 9, all correctly under the supplied truth, correctly abstained on all 12 unsafe cases, and conservatively escalated nine resolvable cases.”

Highlight zero percent incorrect auto-resolution, 100% correct abstention, and the honest false escalations. Avoid presenting the synthetic 60-record regression subset as independently held out, or cached verifier-only timings as end-to-end model performance.

## 4:35–5:00 — Fit and boundary

Say: “Razorpay already owns payment-side evidence and international payment workflows. RemitProof explores the residual finance work left when structured payment signals do not uniquely explain a receipt.”

Close with: “This dataset is synthetic, the schemas are public-API compatible or modeled on documented payment fields, and final posting is prototype-only. The product’s contribution is a proof-gated decision, not a fake integration.”
