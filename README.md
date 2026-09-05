# RemitProof

**AI proposes. RemitProof tries to prove it wrong. Evidence determines whether it may act.**

RemitProof helps finance teams investigate payments that ordinary reconciliation cannot match confidently. AI interprets remittance emails and proposes an invoice allocation. Code verifies the money, checks the records, and searches for competing explanations. The result is an auditable resolution or a clear reason for human review.

Built for the **Razorpay AI Buildathon**.

[**View the demo**](https://remitproof-demo.vercel.app) · [Benchmark](https://remitproof-demo.vercel.app/benchmark) · [Inspect a resolution](https://remitproof-demo.vercel.app/exceptions/PAY_051) · [Try your own scenario locally](docs/sandbox.md)

## Why it exists

A $10,000 payment could settle one $10,000 invoice or two invoices worth $6,000 and $4,000. Both balance. Which did the payer intend?

Rules handle clear matches. AI helps interpret the exceptions. RemitProof checks whether the evidence supports the proposed action and whether another explanation survives.

```text
Normal matching → Unresolved exception → AI proposal
                                            ↓
                           Financial proof + alternative search
                                            ↓
                                Evidence sufficiency
                                            ↓
                                  Resolve / Human review
```

## What the evaluation shows

**80 synthetic receipts: 50 normal matches and 30 hard exceptions.**

| On the 30 hard exceptions | Correct resolutions | Wrong resolutions | Correct reviews | Unnecessary reviews |
|---|---:|---:|---:|---:|
| Rules only | 0 | 0 | 12 | 18 |
| Proposals without verification¹ | 12 | 18 | 0 | 0 |
| **RemitProof** | **9** | **0** | **12** | **9** |

RemitProof recovered **9 safe resolutions beyond rules alone**. The **18 incorrect resolutions** observed without verification were not authorized. The trade-off is visible: **9 resolvable cases still went to review**.

**Run label: `offline_verifier_regression_only`.** These results replay cached proposals; they are not a fresh end-to-end model benchmark or a production safety guarantee.

¹ A forced-proposal ablation, not an independently prompted LLM allowed to abstain. [Source publication](results/current_generation.json) · [Methodology](docs/benchmark_methodology.md) · [Failure analysis](docs/failure_analysis.md)

## Try it yourself

The demo lets you inspect stored decisions. The [**sandbox**](https://remitproof-demo.vercel.app/sandbox) lets you enter your own dummy payment, invoices, credits, customer records, and emails, then run the actual verifier.

- **Investigate:** use live Ollama, or supply a clearly labeled manual hypothesis.
- **Challenge:** change an amount or remove an email, rerun, and compare decisions.
- **Inspect:** review proof checks, alternatives, evidence, and a downloadable audit report.

Start with **“Evidence resolves ambiguity”**, run it, then remove its email and run again. [Sandbox setup and limits →](docs/sandbox.md)

The public sandbox uses clearly labeled manual hypotheses, with no model call. Live AI is available with local Ollama; public live AI requires a reachable model service and remains disabled.

## Scope

This is an investigation and decision-support MVP using synthetic or user-supplied dummy records. It performs **no live Razorpay integration, accounting write-back, payment, or settlement**. Sandbox records are simulated assertions, not authenticated financial evidence.

**Stack:** Next.js · TypeScript · FastAPI · Pydantic · Python Decimal · Ollama

<details>
<summary><strong>Run locally and verify</strong></summary>

Requires Python 3.9+, Node.js 24, and Ollama only for live AI. From the repository root, in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r backend\requirements-dev.lock
python -m uvicorn app.main:app --app-dir backend --port 8001
```

In a second terminal:

```powershell
Set-Location frontend
npm ci
$env:NEXT_PUBLIC_API_URL='http://127.0.0.1:8001'
npm run dev
```

Open [localhost:3000](http://localhost:3000), or [localhost:3000/sandbox](http://localhost:3000/sandbox). Enable live AI using the [sandbox guide](docs/sandbox.md). Checked-in evaluation data needs no model.

Run backend checks from the repository root with the virtual environment active:

```powershell
python -m pytest -q backend\tests
```

Run frontend checks from `frontend/`:

```powershell
npm test
npm run lint
npx tsc --noEmit
npm run build
```

[API documentation locally](http://127.0.0.1:8001/docs) · [Environment defaults](.env.example) · [Reproduce the evaluation](docs/benchmark_methodology.md#reproduce)

</details>

## Explore the engineering

[Architecture and trust boundaries](docs/architecture.md) · [Sandbox guide](docs/sandbox.md) · [Benchmark methodology](docs/benchmark_methodology.md) · [Failures](docs/failure_analysis.md) · [Demo walkthrough](docs/demo_script.md) · [Engineering review retrospective](ENGINEERING_REVIEW_RETROSPECTIVE.md)
