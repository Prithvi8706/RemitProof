# RemitProof Engineering Review Retrospective

## Final outcome

RemitProof was implemented, hardened through multiple independent review cycles, and merged through GitHub PR #1 into the `dev` branch.

- PR: https://github.com/Prithvi8706/RemitProof/pull/1
- Final merge commit on `dev`: `5276a63`
- Final backend suite: 230 tests passed
- Final CI: Python 3.9, Python 3.13, and Node 24 jobs all passed
- Frontend tests, lint, type-check, production build, and dependency audit passed
- `main` was never created, checked out, modified, or merged into

The final review found no unresolved P0, P1, or P2 defect after the last portability repair.

## Why the work took several review cycles

The repository began without an established implementation history: the remote was effectively empty, `dev` had to be initialized, and the complete MVP had to be constructed from the implementation specification. The product handles financial reconciliation, so a superficially working implementation was not enough. A false positive could authorize the wrong invoice allocation, payer relationship, credit, or duplicate transaction.

The review strategy deliberately used independent Sol reviewers with different scopes. Each cycle attempted to disprove the implementation rather than relying on its tests or prior author claims. This exposed defects that ordinary happy-path testing did not cover.

Work was also interrupted several times by model-usage limits. Partial patches were preserved, replacement Sol agents were assigned the same non-overlapping scopes, and work resumed without discarding completed changes.

## Major problems discovered and resolved

### 1. False uniqueness from incomplete allocation search

The allocation search originally considered invoice groups containing at most four invoices. A payment could therefore appear to have one unique allocation even when a valid five-invoice allocation existed.

Example:

- one invoice for 100
- five invoices for 20 each
- payment for 100

The four-invoice cap found only the single 100 invoice and could incorrectly authorize it.

Resolution:

- Exhaustively enumerate all subsets of the bounded eight-invoice candidate set.
- Added an end-to-end regression for the 100 versus five-times-20 ambiguity.
- Ambiguous allocations now require human review.

### 2. Forged payer authorization through arbitrary email text

An email row with a valid customer ID could claim that a payer acted on behalf of a customer. The proof engine initially trusted the email body without establishing whether its sender was connected to that organization.

Resolution:

- Relationship assertions now require sender provenance aligned with the customer or payer identity represented by the repository.
- Unknown and lookalike domains cannot establish payer authorization.
- Contradictory emails remain safety evidence even when they are not trusted as positive authorization.
- Added regressions for attacker-controlled senders and lookalike domains.

Residual boundary:

The synthetic repository has no DKIM or cryptographic email-authentication metadata. The implemented rule is a defensible local provenance rule, not a replacement for production email authentication.

### 3. Duplicate bank-transaction replay

Two payment records with different payment IDs but identical bank transaction facts could each appear safe and be applied to the same invoice.

Resolution:

- Added a normalized transaction fingerprint using bank reference, date, amount, currency, and payer.
- Every record participating in a high-confidence replay is blocked from autonomous allocation.
- Duplicate-risk decisions are routed to human review.

Residual boundary:

Detection is snapshot-scoped. A future persistent write path should also enforce an atomic database uniqueness or reservation constraint.

### 4. Negated and contradictory evidence was inconsistently handled

Relationship denials and remittance prohibitions could be missed depending on whether they appeared in:

- bank reference
- remittance reference
- email subject
- email body

There were also cases where phrases such as “do not apply,” “already paid,” or explicit payer denials could be interpreted as positive evidence.

Resolution:

- Centralized remittance semantics.
- Applied contradiction checks consistently across payment fields and email subject/body.
- Negated invoice and credit references no longer become affirmative evidence.
- “Already paid” and non-current invoice language cannot disambiguate a payment as a safe allocation.
- Added field-by-field regressions for baseline and proposal paths.

### 5. Relevant email truncation could hide a denial

Candidate retrieval kept only four emails. Four positive messages could suppress a fifth authoritative contradiction.

Resolution:

- Safety contradictions are prioritized ahead of supportive correspondence.
- The regression with a contradictory fifth email now reaches the authorization checks and forces abstention.

### 6. Credit over-application

Aggregate arithmetic could pass while a credit linked to a small invoice exceeded that invoice’s amount and silently offset another invoice.

Resolution:

- Credits are validated cumulatively against their linked invoice.
- Over-applied credits are excluded from valid alternatives and fail proof verification.
- Added single-credit and cumulative-credit regression cases.

### 7. Invalid currency values

Blank or malformed currency strings could be accepted. If both a payment and invoice used the same invalid value, equality checks could make the allocation appear valid.

Resolution:

- Payment and invoice currency values are normalized.
- Values must be nonblank, three-letter ISO-style codes.
- Currency equality remains mandatory throughout the proof.

### 8. Transport and malformed-model failures escaped fail-closed handling

Some Ollama failures, including invalid UTF-8 and connection resets, escaped as raw exceptions instead of returning a controlled human-review decision.

Resolution:

- URL, connection, timeout, HTTP, response-read, UTF-8, JSON, and response-envelope failures are normalized to `InvestigatorError`.
- The pipeline’s existing fail-closed path turns these failures into human review.
- Error messages avoid leaking hostnames, credentials, or raw transport details.
- Added malformed-response and connection-reset regressions.

### 9. Mixed evaluation artifact generations

Metrics, details, CSV output, and manifests were initially published as separate replacements. A crash during publication could leave files from different runs while readiness still reported success.

Resolution:

- Evaluation results are published as immutable, content-addressed generations.
- A single atomic pointer selects the active generation.
- Readers validate generation IDs, manifests, and SHA-256 hashes.
- Root result files are compatibility exports only; API readers use the immutable selected generation.
- Mixed, incomplete, or tampered generations now return controlled 503 responses.

### 10. Readiness validated less than the API required

Readiness could accept malformed artifacts missing fields later indexed by dashboard or exception endpoints. The deployment could report ready and subsequently return a `KeyError` or uncontrolled 500.

Resolution:

- Result validation now covers all fields, types, domains, decision values, and cross-artifact counts required by the API and frontend.
- Invalid artifacts fail readiness and relevant endpoints with a controlled 503.
- Added tests for missing baseline data, invalid decisions, malformed comparison metrics, cache types, and inconsistent counts.

### 11. Evaluation truth leaked into operational UI data

Ground-truth `exception_class` labels from the benchmark were exposed through operational APIs as though the running system had inferred them.

Resolution:

- Operational exception classes are now derived from runtime decisions and evidence.
- Benchmark truth remains confined to evaluation logic.
- Added API-contract tests ensuring truth labels are not exposed.

### 12. Misleading benchmark, cache, and timing claims

Several provenance issues were found:

- identity-unverified legacy cached proposals could appear to support a model-backed benchmark
- failed model attempts could be counted in latency while metadata claimed inference was excluded
- the cache methodology did not match the actual cache identity fields
- the synthetic 60-record partition could be mistaken for an independent held-out benchmark

Resolution:

- Identity-unverified cache replay is explicitly labeled as an offline verifier regression.
- The model-backed safety gate is ineligible and not passed without identity-verified proposals.
- Failed inference attempts are counted and timing metadata reflects whether inference was attempted.
- Cache identity documentation now matches the implementation.
- The 60-record partition is labeled synthetic and not independently held out.

Remaining limitation:

No fresh identity-verified live Ollama benchmark was run. The repository therefore makes no claim that the committed cached run is a reproducible model-quality benchmark.

### 13. Cache-only CLI incorrectly succeeded without proposals

An isolated validation run used an empty output directory. Despite 30 cache misses and no proposals, `--cache-only` exited successfully and the offline verifier gate passed through universal abstention.

Resolution:

- Cache-only execution now exits nonzero if any required proposal is missing or investigator failure occurs.
- The offline verifier gate is eligible only with complete cached-proposal coverage.
- Added exact empty-cache failure and complete-cache success tests.

### 14. Accessibility and exact-money rendering

Proof outcomes were conveyed through color and icons hidden from assistive technology. Separately, decimal strings were converted to JavaScript `Number`, losing precision for large financial values.

Resolution:

- Every proof row exposes “Passed,” “Failed,” or “Not evaluated” as accessible text.
- Currency formatting uses exact decimal-string processing and `BigInt`, including large values, signs, exponents, locale grouping, and currency-specific precision.
- Global route-state messages are generic and accurate.
- Exception routes have specific loading, error, and not-found states.
- Added frontend money-format tests.

### 15. Cross-platform artifact hashes failed in CI

The first immutable publication fix passed locally on Windows but failed on fresh Linux CI. CSV bytes were generated with CRLF, hashed, and then normalized by Git to LF in the committed object. The manifest therefore described the uncommitted working-tree bytes rather than the bytes present in a fresh checkout.

Resolution:

- CSV serialization now explicitly uses LF.
- Results were regenerated.
- Tests compare deterministic byte output.
- Committed Git blob hashes were compared with manifest hashes.

A final independent review then found the reverse risk: a Windows checkout with `core.autocrlf=true` could convert the committed LF artifacts back to CRLF.

Final resolution:

- Added narrowly scoped `.gitattributes` rules enforcing `text eol=lf` for result JSON and CSV artifacts.
- Simulated a Windows-style checkout with `core.autocrlf=true`.
- Verified all active manifest hashes still matched.
- Fresh Linux CI and the Windows simulation both passed.

## Vercel demonstration deployment addendum

The later Proposal/Proof/Conflict refinement was developed on
`refinement/proposal-proof-conflict` and opened as PR #3 against `dev`. The
judge-facing site was then deployed to Vercel so the visual demonstration and
the existing investigation routes could be reviewed outside the local
development environment.

- Website: https://remitproof-demo.vercel.app
- Read-only API: https://remitproof-api-preview.vercel.app
- PR: https://github.com/Prithvi8706/RemitProof/pull/3

`main` was not checked out, modified, or used as a deployment source.

### 16. Vercel required an interactive device login

The workspace had the Vercel CLI but no stored account credentials. The first
deployment command paused in an interactive device-authentication flow instead
of deploying.

Resolution:

- Used Vercel's one-time device authorization flow.
- Waited for explicit account approval before continuing.
- Did not print or persist an access token in repository files or command
  output.

### 17. A frontend-only deployment would have rendered a server error

The Next.js application is dynamic and loads dashboard, benchmark, queue, and
case data from FastAPI. Its local fallback URL is `http://127.0.0.1:8001`.
There was no existing hosted RemitProof API or production API environment
variable in the Vercel account. Deploying only `frontend/` would therefore
have produced a visually deployed site whose server-rendered routes failed at
runtime.

Resolution:

- Deployed a separate read-only FastAPI service containing the committed
  evaluation artifacts.
- Configured the Vercel frontend runtime and build to use the public API URL.
- Verified the real dashboard response before accepting the frontend
  deployment: 80 receipts, 30 exceptions, 9 RemitProof resolutions, and 21
  human-review decisions.

### 18. Backend packaging changed the repository-root calculation

The first FastAPI package copied `backend/app` to the deployment root as
`app`. The results loader intentionally locates repository artifacts relative
to `backend/app/utils/results.py`. Flattening the package by one directory
made that calculation point above the deployed project, so `/api/dashboard`
returned a controlled 503 reporting that `metrics.json` was missing even
though the artifacts had been uploaded.

Resolution:

- Probed the deployed dashboard endpoint before deploying the frontend.
- Identified that only the temporary Vercel package layout differed from the
  repository layout.
- Adjusted the root calculation in the temporary deployment adapter, leaving
  the reviewed repository implementation unchanged.
- Redeployed and confirmed the endpoint returned JSON with HTTP 200.

### 19. Protected preview URLs returned a login page with HTTP 200

The corrected FastAPI preview URL was protected by the Vercel account's
preview authentication. A basic status-code check was misleading because the
request followed a redirect and ended on a Vercel login page with HTTP 200 and
`text/html`, not the expected API JSON.

Resolution:

- Validated the response content type and final response URL in addition to
  the status code.
- Promoted the read-only backend deployment to its public project alias.
- Re-ran JSON parsing and checked specific dashboard fields before wiring the
  frontend to it.

Lesson:

An HTTP 200 does not prove an API deployment is healthy. Deployment smoke
tests must also verify content type, schema, and representative values.

### 20. Vercel created local project-link files during deployment

The CLI created `.vercel/` metadata and a new `frontend/.gitignore`. The
temporary backend packaging directory also appeared as untracked content.
These files were deployment-machine state and did not belong in the product
PR.

Resolution:

- Kept credentials and Vercel project metadata out of Git.
- Moved temporary deployment staging and project-link metadata outside the
  repository after deployment.
- Removed the CLI-generated untracked `.gitignore`.
- Rechecked that the feature branch worktree was clean.

### 21. Cleanup commands were constrained by destructive-operation policy

An attempted recursive cleanup command was rejected by the execution safety
policy even though the target had been validated. Retrying with broader or
less explicit deletion would have been unsafe.

Resolution:

- Did not weaken the path checks or retry an ambiguous recursive delete.
- Verified the exact absolute source and destination paths.
- Moved the temporary directories outside the repository instead, preserving
  a clean Git worktree without risking repository data.

### 22. The demonstration and operational screens used two visual systems

The first deployment paired the new near-black judge-facing homepage with the
earlier light green `/exceptions` and `/exceptions/[paymentId]` interface.
Both surfaces were functional, but navigating into a case created a visible
design discontinuity.

Resolution:

- Added a shared operational theme for the queue, detail, loading, error, and
  not-found routes.
- Reused the near-black, off-white, graphite, and emerald visual language
  without copying the homepage's cinematic layout or scroll choreography.
- Kept the queue as a dense case ledger and the detail page as an evidence
  dossier, preserving the information architecture and financial behavior.
- Verified resolved and blocked cases at desktop and mobile widths.

## PR #3 benchmark UI and adversarial review addendum

PR #3 began as a deliberately narrow integration task: wire the existing
`SafetyFrontier`, `BenchmarkCaseExplorer`, and `CaseSystemComparison`
components into the benchmark and exception pages, and expose already
available provenance metadata. The review nevertheless uncovered several
backend and presentation defects because the new UI made previously hidden
evaluation assumptions inspectable at case level.

- PR: https://github.com/Prithvi8706/RemitProof/pull/3
- Base branch: `dev`
- PR branch: `refinement/proposal-proof-conflict`
- Final review-fix commit: `682c5f0`
- Final local backend suite: 267 tests passed
- Published mode remained `offline_verifier_regression_only`
- Published comparison remained 9 correct resolutions, 0 wrong automatic
  resolutions, 12 correct abstentions, and 9 false escalations

The PR was prepared and reviewed without modifying `main`. This section
records merge readiness; it does not claim that GitHub merged the PR unless
the repository history shows that separately.

### 23. Evidence rows could support prohibited credit amounts

The evidence matrix checked prohibited credit IDs but initially omitted
`prohibited_credit_amounts`. An email saying “do not deduct $10” could
therefore appear to support an allocation that deducted that amount.

Resolution:

- Added selected-credit amount checks to the prohibition path.
- Classified such evidence as `contradicts`, not `supports`.
- Added regression coverage for amount-level prohibitions.

### 24. Cross-customer and unauthenticated evidence could appear supportive

Invoice-set matching originally ignored the email's customer identity in one
evidence path. A message associated with customer A could support customer B's
allocation if it named the same invoice set. A separate path also allowed an
untrusted sender to contribute positive allocation evidence.

Resolution:

- Positive support now requires the evidence customer to match the proposed
  allocation customer.
- Positive email evidence must pass the synthetic sender-provenance rule.
- Untrusted evidence can still contribute contradictions, preserving the
  fail-closed safety boundary.
- Added end-to-end cross-customer and untrusted-sender regressions.

### 25. Synthetic sender-domain shortcuts created identity collisions

An early repair accepted abbreviated domains such as `acme.example` for a
customer named Acme Technologies. That became unsafe when another customer,
such as Acme Logistics, shared the same leading brand. Checking uniqueness
only among retrieved candidates was also insufficient because retrieval could
omit the colliding customer.

Resolution:

- Removed abbreviated brand-domain trust.
- Reserved `.example` senders must match the complete normalized organization
  slug, such as `acmetechnologies.example`.
- Updated synthetic fixtures to use the complete organization identity.
- Added a regression where the colliding customer is absent from the candidate
  bundle, ensuring retrieval cannot manufacture false uniqueness.

Residual boundary:

This remains a synthetic provenance convention. A production implementation
must use authenticated sender and domain metadata rather than inferred domain
names.

### 26. Spoofed or generic corrections could supersede genuine instructions

Temporal supersession initially trusted a later correction based on customer
ID, date, and text references. This allowed an untrusted sender to erase an
older genuine instruction. The first repair still accepted generic or weak
secondary references such as `WIRE` or `WIRE2026`, which may be shared across
payments.

Resolution:

- Only trusted senders may supersede allocation evidence.
- The canonical payment ID always qualifies as payment-specific.
- Bank and remittance references qualify only when an explicit authoritative
  payment corpus proves that the normalized reference is unique.
- Without that authoritative context, secondary references fail closed.
- Added untrusted-correction, generic-rail, digit-bearing generic-reference,
  normalization-collision, and shared-reference regressions.

### 27. Credit-only corrections and amount multiplicity were mishandled

A later instruction changing only a credit amount did not supersede the older
instruction because the comparison considered invoice and credit IDs but not
affirmative credit amounts. Separately, set-based amount matching lost
multiplicity: two separate $10 credits could look equivalent to one stated $10
deduction.

Resolution:

- Temporal comparison now includes affirmative credit amounts and supports
  credit-only correction instructions.
- Amount-only evidence preserves the number of selected credits as well as the
  set of amounts.
- Added corrected-credit and repeated-equal-amount regressions.

### 28. Payment remittance could justify a decision but disappear from proof

Payment-level bank or remittance text could disambiguate alternatives, but the
evidence matrix only rendered proposal-cited evidence IDs. The authorization
decision and its audit artifact could therefore disagree about which record
provided decisive support.

Resolution:

- Added payment-remittance rows to the evidence matrix when authoritative
  payment fields contain allocation semantics.
- Applied the same invoice, credit, amount, prohibition, and multiplicity
  rules used by evidence sufficiency.
- Counterfactual removal now clears the relevant payment references so the
  system can demonstrate whether that payment evidence was decision-critical.

### 29. Case comparison labels concealed unsafe and missed outcomes

The first case-level comparison omitted two negative branches. A RemitProof
wrong automatic resolution could be displayed as “Resolve with proof,” while
a proposal-only abstention on a resolvable case could be labeled correct.

Resolution:

- Added explicit unsafe-resolution and missed-resolution branches.
- Excluded cases where RemitProof was also wrong from the “unsupported
  resolutions prevented” group.
- Added a separate visible RemitProof-failure category when such records exist.
- Kept all labels derived from result data rather than hardcoded benchmark
  claims.

### 30. Benchmark summaries could mix generations or accept mismatched rows

Independent benchmark API requests could observe different active publication
generations during a pointer change. Result validation also checked aggregate
totals without proving that each CSV row corresponded to the same payment in
`details.json`, allowing swapped IDs, duplicates, omitted cases, or incorrect
per-class outcome counts to survive some consistency checks.

Resolution:

- The frontend retries and rejects benchmark responses with different
  evaluation generation IDs.
- Backend validation now checks payment-ID uniqueness and exact eligible ID
  sets.
- Each CSV row is linked to its detail record and checked across identity,
  decisions, outcomes, evidence counts, arithmetic, generation, and latency.
- Per-class counts are derived from and reconciled with the validated CSV.
- Added regressions for swapped IDs, duplicate cases, inconsistent outcome
  flags, and mixed publications.

### 31. Decision artifacts could misstate why authorization stopped

A blocked decision with one financially valid alternative reported financial
constraints as failed, even when the actual blocker was entity or evidence
authorization. Its counterfactual text also claimed competing allocations
remained when the only proposal had merely lost required evidence.

Resolution:

- One financially valid alternative now reports a financial pass; only zero
  alternatives reports failure.
- Counterfactual explanations distinguish remaining competing allocations
  from a proposal losing required evidence.

### 32. Investigator failures were shown as completed control stages

The investigation path initially marked alternative search complete and could
show “No conflict remains” after model investigation failed before those
stages ran. A later review found the same problem in the proof and evidence
steps, which were labeled as failed rather than unavailable.

Resolution:

- Financial proof, evidence comparison, alternative search, alternative
  evaluation, and conflict evaluation now display “not run” and a blocked
  state after `investigator_error`.
- Completed and failed control outcomes remain distinct from unavailable
  stages, preserving audit accuracy.

### 33. Review repairs temporarily changed the published result story

One candidate-scoped sender-uniqueness repair was locally plausible and passed
focused tests, but regenerating the benchmark caused all 30 hard exceptions to
escalate and reduced RemitProof's correct resolutions from 9 to 0. This exposed
that focused tests alone did not protect the published product behavior.

Resolution:

- Rejected the candidate-scoped repair in favor of strict complete-organization
  matching.
- Advanced the evaluator provenance to `remitproof-evaluator-v7` after verifier
  behavior changed.
- Regenerated the cache-only publication from the final verifier.
- Confirmed the honest comparison returned to 9 correct resolutions, 0 wrong
  automatic resolutions, 12 correct abstentions, and 9 false escalations.

Lesson:

For an evaluation product, regeneration of the published artifact is itself a
required regression test. Unit tests can pass while the benchmark's measured
capability materially disappears.

### PR #3 validation and review outcome

The final repair state was exercised with:

- 267 backend tests
- 12 frontend tests
- frontend lint and TypeScript checks
- Next.js production build
- HTTP rendering smoke tests for `/benchmark` and an exception detail route
- immutable publication loading and generation-consistency validation
- GitHub CI on Python 3.9, Python 3.13, and Node 24 for the preceding review
  checkpoint
- multiple independent read-only reviews, including adversarial attempts to
  reproduce sender spoofing, cross-customer evidence, amount multiplicity, and
  shared-reference supersession

The last UI-only correction was locally type-checked, linted, and covered by
the existing frontend test command. At the project deadline, the branch was
pushed to PR #3 for final human merge review without touching `main`.

### Deployment validation performed

- Vercel backend build on Python 3.12 - passed
- Public `/api/dashboard` request - HTTP 200 JSON
- Vercel Next.js 16 production build - passed
- Next.js TypeScript validation during deployment - passed
- Mobile homepage at 375 by 812 - rendered successfully
- `PAY_051` detail route - rendered the complete proposal, proof, evidence,
  alternative, and authorization record
- PR #3 - open, mergeable, and targeted to `dev`
- Git worktree after deployment cleanup - clean

The deployment adapter is intentionally separate from the product branch. A
future permanent deployment setup should codify the frontend/API project
linkage and environment variables in reviewed infrastructure configuration
rather than relying on a temporary packaging directory.

## Validation performed

The final repair state was validated with:

- `python -m pytest -q` — 230 passed
- `python -m pip check` — passed
- hash-locked dependency dry-run — passed
- `npm test` — passed
- `npm run lint` — passed
- `npx tsc --noEmit --incremental false` — passed
- `npm run build` — passed
- `npm audit --omit=dev --audit-level=high` — zero vulnerabilities
- FastAPI health, dashboard, benchmark, queue, and detail endpoint smoke tests — passed
- GitHub Actions on Python 3.9 and 3.13 — passed
- GitHub Actions on Node 24 — passed
- committed-artifact SHA-256 verification — passed
- simulated `core.autocrlf=true` checkout verification — passed
- credential-pattern scan — no credential-like patterns found

No live Ollama request or other cost-incurring external service call was made during review.

## Branch and PR discipline

All implementation and review work was performed on `dev` or the PR branch:

- base branch: `dev`
- PR branch: `review/sol-final-hardening`
- PR merge target: `dev`

The final squash merge created commit `5276a63` on `dev`.

`main` was intentionally left untouched throughout the complete process.

## Lessons from the review

1. Financial reconciliation must prove uniqueness, not merely find one valid equation.
2. Text that claims authorization is not authorization unless its source is trusted.
3. Fail-safe behavior must cover transport, decoding, schema, and partial-publication failures.
4. Passing tests are not enough when tests and implementation share the same assumptions.
5. Generated artifact hashes must describe committed checkout bytes, not only local working-tree bytes.
6. Readiness must validate the complete consumer contract.
7. Offline cached evaluation must be labeled separately from model-backed benchmarking.
8. Independent adversarial reviews are expensive, but they caught multiple realistic false-safe paths that normal happy-path testing missed.

## Current status

The requested implementation, hardening, PR review, CI validation, and merge into `dev` are complete.

The remaining work is optional future production hardening:

- cryptographically authenticated email provenance
- persistent transactional duplicate protection
- a fresh identity-verified live-model benchmark
- retention and cleanup policy for old immutable result generations
