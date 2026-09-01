# RemitProof

RemitProof is an evidence-grounded investigation layer for cross-border receipts that normal reconciliation cannot safely explain. A local language model proposes a semantic interpretation; deterministic code independently proves the money, record state, entity relationship, credit support, and uniqueness before any receipt is marked resolved.

The operating rule is simple: maximize justified automation subject to an incorrect auto-resolution rate near zero. If the evidence does not identify one safe explanation, RemitProof sends the case to human review.

## What is implemented

- A conventional matcher for unique, explicit allocations.
- Deterministic candidate retrieval with bounded customer, invoice, credit, and email sets.
- A local Ollama investigator returning strict Pydantic-validated JSON.
- Decimal-based financial proof, state checks, duplicate prevention, and contradiction detection.
- Exhaustive alternative-allocation search over the bounded candidate set.
- Evidence-sufficiency gating with explicit abstention.
- An 80-receipt synthetic dataset, a 10-case kill spike, a 60-record synthetic benchmark/regression subset, and three-way evaluation.
- A FastAPI read API and a responsive Next.js dashboard with resolved and human-review detail states.

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

AI proposes; code proves; evidence sufficiency authorizes or abstains.

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
