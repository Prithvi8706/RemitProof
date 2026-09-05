# RemitProof

> **A financial reconciliation can be mathematically valid and still be wrong.**

RemitProof is an evaluation-grade, read-only financial-control MVP for unresolved cross-border payment exceptions. It keeps ordinary deterministic reconciliation in charge of straightforward receipts, then uses AI to interpret semantic evidence such as remittance intent and payer relationships. The AI only proposes an allocation; deterministic code recomputes the money, validates invoice/credit state, currency, entities, duplicates, and contradictions, searches for competing financially valid explanations, and authorizes a resolution only when the evidence uniquely supports it. Otherwise it abstains and produces an auditable human-review record. The repository uses realistic synthetic data and the deployed demo does not post real Razorpay or accounting transactions.

In one sentence: **rules are safe but limited, LLMs are capable but unsafe, and RemitProof combines semantic investigation with proof-gated authorization.**

```text
PLAUSIBLE
    ≠
JUSTIFIED
```

**AI proposes. RemitProof verifies.**

Normal reconciliation is deterministic.

```text
Payment reference matches.
Amount matches.
Customer matches.
Done.
```

The dangerous cases begin when several financial explanations are simultaneously plausible.

**RemitProof verifies whether an AI-generated financial reconciliation is uniquely supported by non-conflicting evidence before allowing it to resolve the transaction.**

It is not a replacement for normal reconciliation. It is a financial conflict-resolution layer for the unresolved exceptions left behind by structured matching.

## Live demonstration

The final read-only demonstration is deployed on Vercel:

- **Website:** https://remitproof-demo.vercel.app
- **Benchmark dashboard:** https://remitproof-demo.vercel.app/benchmark
- **Example resolved investigation:** https://remitproof-demo.vercel.app/exceptions/PAY_051
- **Read-only API:** https://remitproof-api-preview.vercel.app

The benchmark and exception URLs are routes in the same frontend deployment.
The API is a separate read-only service backed by the committed evaluation
artifacts. The deployment does not perform accounting write-back, settlement,
or live Razorpay operations.

```text
Incoming receipts
        |
normal deterministic reconciliation
        |
        +---- structured match ----> resolved normally
        |
        +---- unresolved exception
                    |
             REMITPROOF STARTS
                    |
               AI proposal
                    |
       financial proof + conflict search
                    |
          evidence sufficiency gate
              /             \\
         RESOLVE           ABSTAIN
```

The project is not about generating more financial decisions with AI. It determines which AI-generated financial decisions are justified enough to execute.

## Three domain primitives

### Proposal

The local model constructs one structured hypothesis: customer, invoices, credits, semantic claims, cited evidence, and unresolved questions. A proposal describes what the model thinks happened. It has no authority to resolve the receipt.

### Proof

Deterministic code recomputes the money and verifies record state, currency, credit validity, entity support, duplicate risk, contradictions, and evidence requirements. The model cannot override these checks.

### Conflict

The alternative finder searches for every other allocation that satisfies the bounded financial constraints. If more than one explanation remains and evidence does not uniquely distinguish the proposal, RemitProof blocks the decision and produces a deliberate abstention.

> A plausible financial explanation is not automatically a justified financial action.

## Product boundary

The conventional matcher is intentionally competent. It already handles:

- exact invoice references and exact amount matches;
- known customer IDs, aliases, and payer relationships;
- currency and date constraints;
- simple multi-invoice totals;
- valid ordinary credits.

RemitProof adds value only on semantic ambiguity, fragmented evidence, contradictory evidence, and multiple financially valid explanations. OCR, ERP write-back, FX, settlement, compliance, generic chat, and production integrations remain outside scope.

## What is implemented

- A conventional matcher for unique, explicit allocations.
- Deterministic candidate retrieval with bounded customer, invoice, credit, and email sets.
- A local Ollama investigator returning strict Pydantic-validated JSON.
- Decimal-based financial proof, state checks, duplicate prevention, and contradiction detection.
- Temporal instruction handling: a strictly later, explicitly marked correction from the same customer supersedes an older allocation instruction; conflicting instructions without one remain contradictions and force human review.
- Exhaustive alternative-allocation search over the bounded candidate set.
- Structured conflict records with cleared or unresolved status.
- Evidence-versus-alternative assessments and explicit evidence-sufficiency gating.
- Counterfactual tests that identify decision-critical evidence.
- Reusable resolution-proof and blocked-decision artifacts.
- Explicit abstention when alternatives survive or evidence contradicts a proposal.
- An 80-receipt synthetic dataset, a 10-case kill spike, a 60-record synthetic benchmark/regression subset, and three-way evaluation.
- A FastAPI read API and a responsive Next.js dashboard with resolved and human-review detail states.
- A dark, evidence-first demonstration website with a progressively enhanced WebGL hypothesis field, reversible GSAP/Lenis motion, accessible glass navigation, publication-style benchmark figures, and direct links into the live exception artifacts.

The home route is the judge-facing demonstration surface. The exception library and case-detail routes remain operational views backed by the generated FastAPI artifacts.

## Measured result

The committed result is generated from `results/metrics.json`; the frontend fetches it through the API and does not hardcode benchmark values.

| Result | Full 80-record run | Synthetic 60-record benchmark subset |
|---|---:|---:|
| Normal matches | 50 | 40 |
| Unresolved exceptions | 30 | 20 |
| Exceptions resolved by RemitProof | 9 | 6 |
| Sent to human review | 21 | 14 |
| Incorrect auto-resolution rate | 0% | 0% |
| Correct abstention rate | 100% | 100% |
| Arithmetic correctness | 100% | 100% |
| Retrieval accuracy | 100% | 100% |
| False escalations | 9 | 7 |

On the 30 unresolved exceptions, the forced-proposal-without-verification ablation treated every complete proposal as authorized and got 18 of 30 wrong. This is a proposal-only verifier ablation, not an independently prompted standalone LLM system. RemitProof automatically resolved 9, all correctly, and safely blocked the remaining 21. See [benchmark methodology](docs/benchmark_methodology.md) for metric definitions and [failure analysis](docs/failure_analysis.md) for the conservative misses.

## Architecture in one sentence

The AI proposes. Deterministic code proves. Conflict detection and evidence sufficiency authorize or abstain.

```text
receipt -> retrieve -> conventional match
                       | unresolved
                       v
                 local AI proposal
                       v
        deterministic proof + alternatives
                       v
             evidence-sufficiency gate
                  /             \
             resolved       human review
```

The detailed trust boundaries and Mermaid diagram are in [docs/architecture.md](docs/architecture.md).

## Run locally

Prerequisites:

- Python 3.9 or newer (CI covers the project minimum and Python 3.13)
- Node.js 24
- Ollama with the `llama3.2` model available locally

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r backend\requirements-dev.lock
ollama pull llama3.2
```

`backend/requirements.in` contains direct runtime dependencies and compiles to the fully pinned, hash-verified `backend/requirements.lock`. Development and test dependencies are separated into `backend/requirements-dev.in` and `backend/requirements-dev.lock`. The compatibility entry points `requirements.txt` and `requirements-dev.txt` include the corresponding locks.

To regenerate both locks after intentionally changing a source manifest, use Python 3.9 and the pinned compiler version:

```powershell
python -m pip install pip-tools==7.6.1
python -m piptools compile --generate-hashes --strip-extras --output-file=backend/requirements.lock backend/requirements.in
python -m piptools compile --generate-hashes --strip-extras --output-file=backend/requirements-dev.lock backend/requirements-dev.in
```

The checked-in data and benchmark outputs are ready to use. To regenerate the deterministic dataset and run the model-backed evaluations:

```powershell
python backend\scripts\generate_dataset.py
python backend\scripts\run_spike.py --model llama3.2
python backend\scripts\evaluate.py --data data --output results\fresh --model llama3.2
```

Using a new output directory gives a fresh model-timed run. Using an output directory that already contains `proposal_cache.json` intentionally reuses model proposals, which is useful for deterministic verifier work. In a cached run, the reported throughput and mean decision latency are verifier/pipeline-only measurements: model inference is excluded, so those values are not end-to-end RemitProof performance.

Start the API in one terminal:

```powershell
Set-Location backend
python -m uvicorn app.main:app --reload --port 8001
```

Start the frontend in another terminal:

```powershell
Set-Location frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:3000`. The liveness endpoint is `http://127.0.0.1:8001/live`; readiness is `http://127.0.0.1:8001/ready`; and `/health` is a compatibility alias for readiness. Interactive API documentation is at `http://127.0.0.1:8001/docs`.

Environment defaults are documented in the root `.env.example` and `frontend/.env.example`. `OLLAMA_HOST` and `OLLAMA_MODEL` are read directly from the process environment; the defaults already target local Ollama and `llama3.2`.

## Verify

```powershell
python -m pytest -q backend\tests

Set-Location frontend
npm ci
npm test
npm run lint
.\node_modules\.bin\tsc.cmd --noEmit
npm run build
```

GitHub Actions runs these checks from clean, lockfile-driven environments on every push and pull request. It also runs `python -m pip check` and tests the backend on Python 3.9 and 3.13.

## API

| Endpoint | Purpose |
|---|---|
| `GET /live` | Process liveness; does not depend on generated benchmark artifacts |
| `GET /ready` | Readiness; returns success only when required result artifacts load and validate |
| `GET /health` | Backward-compatible alias for `/ready` |
| `GET /api/dashboard` | Dashboard totals and recent exceptions |
| `GET /api/exceptions` | Exception queue |
| `GET /api/exceptions/{payment_id}` | Payment, proposal, evidence, proof, and alternatives |
| `GET /api/benchmark` | Full generated benchmark metrics |
| `GET /api/benchmark/cases` | Per-case comparison outcomes and exception-class breakdown |

These endpoints are read-only. The prototype does not post allocations to an accounting system.

## Repository map

```text
backend/app/         domain models, services, and FastAPI routes
backend/scripts/     deterministic data generation and evaluations
backend/tests/       proof, policy, retrieval, dataset, and API tests
data/                synthetic full, development, and benchmark/regression subsets
frontend/            Next.js App Router product UI
results/             generated metrics, per-case details, and comparisons
docs/                architecture, methodology, failures, and demo script
```

## Data and integration disclosure

```text
Razorpay Invoice data:
Public-API compatible.

Bank-transfer/payment fields:
Modeled on documented Razorpay payment schemas.

International Bank Transfer records:
Realistic synthetic dataset modeled on documented exporter workflows.

Merchant ERP/customer/email data:
Synthetic.

Final posting:
Prototype only; no production accounting write-back.
```

RemitProof does not claim a live Razorpay, bank, email, ERP, settlement, or accounting integration. Authentication, persistence, FX handling, OCR, and production posting are intentionally outside this MVP.
