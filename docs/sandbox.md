# Self-service sandbox

Open `/sandbox`, choose an editable example or start a new scenario, and click **Run reconciliation**. The backend calls the same `process_payment` pipeline used by the evaluation. Inputs and results are isolated from the committed benchmark publication.

## What you can test

- A payment, up to 3 customers, 8 invoices, 3 credits, 4 emails, and 4 related payments.
- Your own untrusted hypothesis, or a freshly generated Ollama proposal when live mode is enabled.
- Amount, currency, record state, customer relationships, credit validity, contradictory instructions, duplicate records, and competing allocations.
- Removing decisive evidence and rerunning: select **Evidence resolves ambiguity**, run it, remove its email, and rerun. The original supplied hypothesis resolves with the email and abstains without it.

The three editable examples copy synthetic input records and supplied hypotheses from the existing publication. Unrelated candidate records whose owning customers are absent were omitted to make each scenario a valid self-contained dataset. No ground truth or benchmark outcome is sent to the investigation pipeline. Editing an example reruns the actual verifier; it does not select a stored answer.

## Modes

**Test my hypothesis** runs the normal matcher first. If unresolved, a user-supplied proposal goes through the existing proof, alternative search, evidence sufficiency, and counterfactual code. It makes no model call. The report explicitly identifies this source.

**Live AI investigation** runs the normal matcher first and calls Ollama only for unresolved exceptions. No cached proposal or manual fallback is used. Model failure produces an explicit unavailable-investigator result with human review. Each Ollama attempt has a 40-second transport timeout; the existing schema-correction loop permits at most three attempts. The frontend proxy allows 135 seconds, with a 140-second browser timeout.

## Run live AI locally

Start the installed Ollama service and ensure the model is available:

```powershell
ollama serve
# In another terminal if the model is not already installed:
ollama pull llama3.2
```

Start the backend from the repository root:

```powershell
$env:SANDBOX_LIVE_AI_ENABLED='true'
$env:OLLAMA_HOST='http://127.0.0.1:11434'
$env:OLLAMA_MODEL='llama3.2'
python -m uvicorn app.main:app --app-dir backend --port 8001
```

Then start the frontend, pointing at that API:

```powershell
Set-Location frontend
$env:NEXT_PUBLIC_API_URL='http://127.0.0.1:8001'
npm run dev
```

Open `http://localhost:3000/sandbox`. Model configuration is server-controlled. The browser never accepts or exposes model credentials or destination URLs.

## Public deployment

Manual proposal mode works without Ollama. Live AI is disabled unless `SANDBOX_LIVE_AI_ENABLED=true` is set on the API server. A Vercel function cannot reach Ollama on your laptop through `127.0.0.1`; public live AI requires an independently reachable model service. Configure infrastructure access controls and distributed request limits before publicly enabling it. The two concurrent-run slots in the API are only per-process backpressure, not a distributed rate limit or a spending cap.

The Next.js `/api/sandbox/{action}` proxy uses the existing backend URL configuration. It forwards only the three named sandbox actions, applies a 64 KiB request limit, rejects cross-origin browser submissions, and never caches results. Direct API requests receive the same body-size and domain validation.

## Reports and boundaries

The latest five runs remain in browser memory until reload. Export a scenario to reimport it later; download an audit report to keep its exact inputs, result, input SHA-256, UUID, timestamp, and proposal source. The input hash is a reproducibility fingerprint, not a signature or proof of source authenticity.

The application does not persist submitted records or append them to benchmark files. It does not log request bodies in sandbox code. Hosting infrastructure and a configured model provider may retain their own operational logs; submit dummy records only. All customer relationships and email senders are simulated assertions supplied by the visitor. A resolved result is conditional on those inputs, not authenticated bank or payer authorization. Nothing is posted, settled, or paid.

## API

| Route | Behavior |
|---|---|
| `GET /api/sandbox/capabilities` | Runtime modes, limits, and trust boundary |
| `GET /api/sandbox/examples` | Editable synthetic scenarios with supplied hypotheses |
| `POST /api/sandbox/investigate` | Validate one scenario and return a newly computed report |

The input contract is `SandboxInput` in `backend/app/api/sandbox.py`. Unknown fields, duplicate IDs, missing relationships, oversized collections, and invalid money are rejected. Live requests cannot include a supplied proposal or set model hosts. The API requires `application/json` and caps streamed request bodies at 65,536 bytes. There is no shared sandbox dataset or posting endpoint.

Run sandbox regression tests with `python -m pytest -q backend/tests/test_sandbox.py`; frontend import-contract tests are included in `npm test`.
