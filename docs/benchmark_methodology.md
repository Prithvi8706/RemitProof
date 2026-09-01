# Benchmark methodology

## Question

Can semantic investigation recover safe exception resolutions that a conventional matcher misses, while deterministic proof prevents the unsafe actions an unverified language model would take?

The primary metric is incorrect auto-resolution rate. Exception resolution is valuable only after that safety constraint is met.

## Dataset

`backend/scripts/generate_dataset.py` deterministically creates 80 internally consistent synthetic receipts:

- 50 conventional exact-reference cases;
- 30 unresolved exception cases across 15 exception classes;
- 20 development records: 10 conventional and 10 exceptions;
- 60 synthetic benchmark/regression records: 40 conventional and 20 exceptions.

Across the 30 exceptions, 18 have a uniquely supportable resolution and 12 should abstain. The 60-record benchmark/regression subset contains 13 resolvable and 7 should-abstain exceptions.

Inputs are stored as payments, invoices, customer masters, credit notes, and remittance emails. Ground truth is stored separately and is available only to evaluation code. The model receives the retrieved candidate bundle, never `ground_truth.json`.

## Frozen evaluation sequence

1. Build and run the 10-case kill spike.
2. Require at least two semantic wins over baseline, at least one unsafe forced proposal blocked, and zero wrong RemitProof auto-resolutions.
3. Develop against the 20-record development partition.
4. Freeze the prompt and decision logic.
5. Run the full 80-record evaluation and report both full-run and synthetic benchmark-subset metrics.

The final kill spike passed `GO`: two semantic wins, four unsafe model-only resolutions blocked, and zero incorrect RemitProof resolutions.

## Compared systems

Comparison payloads in `metrics.json` are scoped to records that remained unresolved after normal reconciliation: 30 records in the full run and 20 records in the synthetic benchmark/regression subset.

- **Baseline:** deterministic conventional matcher only. It resolves only one unique, explicit, eligible allocation.
- **Forced proposal without verification:** any syntactically complete proposal is treated as authorized, even if the proposal also signals uncertainty. The prompt asks for a best proposal because the verifier is expected to abstain when needed. This is a proposal-only verifier ablation, not a separately prompted or fairly evaluated standalone LLM system. Existing artifact/UI fields may retain the legacy `llm_only` label for compatibility.
- **RemitProof:** the same model proposal must pass deterministic proof, alternative enumeration, and evidence sufficiency.

## Metric definitions

| Metric | Definition |
|---|---|
| Incorrect auto-resolution rate | Wrong automatic decisions / all automatic decisions across evaluated records |
| Correct abstention rate | Human-review decisions on should-abstain exception cases / all should-abstain exception cases |
| False escalation rate | Human-review decisions on safely resolvable exception cases / all safely resolvable exception cases |
| Resolution accuracy | Correct automatic resolutions on safely resolvable exception cases / all safely resolvable exception cases |
| Exception resolution rate | AI-path resolutions / unresolved exceptions |
| Entity resolution accuracy | Correct proposed customer / exception records |
| Evidence precision | Cited IDs that ground truth marks relevant / all cited IDs |
| Arithmetic correctness | Records whose final behavior never authorizes failed arithmetic / all records |
| Retrieval accuracy | Records whose required customer, invoices, credits, and email evidence were retained / all records |

`resolution_accuracy` and `false_escalation_rate` are exception-only metrics. Their denominators are the safely resolvable exception records, so conventional exact-reference matches cannot inflate either metric. Metrics explicitly defined over all records or all evaluated records retain those all-receipt denominators.

The three-system comparison is restricted to unresolved exceptions to avoid easy cases obscuring the result. The metrics payload keeps `comparison_scope` and reports the corresponding `comparison_record_count` (30 for the full run and 20 for the synthetic benchmark/regression subset).

## Final result

| System on 30 exceptions | Correct resolutions | Wrong auto-resolutions | Correct abstentions | False escalations |
|---|---:|---:|---:|---:|
| Baseline | 0 | 0 | 12 | 18 |
| Forced proposal without verification | 12 | 18 | 0 | 0 |
| RemitProof | 9 | 0 | 12 | 9 |

The current artifact achieves 100% arithmetic correctness, 100% retrieval accuracy, 100% correct abstention, and 0% incorrect auto-resolution under the supplied synthetic truth. It was regenerated with existing cached proposals after verifier hardening. Its throughput and mean latency therefore measure verifier/pipeline execution with cache lookup; model inference is excluded. These are not end-to-end RemitProof/Ollama performance figures. Use a new output directory for uncached model timing; the safety counts above are the central result.

## Reproduce

Prepare local Ollama and dependencies as described in the README, then run:

```powershell
python backend\scripts\generate_dataset.py
python backend\scripts\run_spike.py --model llama3.2
python backend\scripts\evaluate.py --data data --output results\fresh --model llama3.2
```

Use a new output directory for a fresh timed run. `CachedInvestigator` keys proposals by model tag, prompt, and candidate input. Reusing an output directory with `proposal_cache.json` reproduces proposal decisions while avoiding model calls, so its resulting latency and throughput are verifier-only and must not be reported as fresh inference or end-to-end performance. The cache does not record a model digest, host, generation-option fingerprint, or code revision; cached outputs are suitable for verifier regression work, not model-to-model performance claims.

Generated artifacts:

- `metrics.json`: aggregate metrics plus the compatibility `held_out` key for the synthetic benchmark/regression subset;
- `results.csv`: one row per receipt;
- `confusion_breakdown.csv`: outcome counts by exception class;
- `details.json`: audit payloads used by the API and UI;
- `proposal_cache.json`: keyed model proposals, with no ground truth.

## Limitations

The benchmark is synthetic and authored for this MVP's supported failure modes. The 60-record subset repeats scenario templates represented in development and is inspected by repository tests, so it is a deterministic regression partition—not an independent held-out or generalization benchmark. It is useful for regression and comparative safety evidence under supplied truth, not an estimate of production prevalence or unseen-case performance. The sample is small, one local model was tested, no confidence interval is claimed, and performance was measured on one machine. A production evaluation would require a separately authored and access-controlled benchmark, blinded real-world cases, independent labeling, broader currency and document distributions, and pre-registered thresholds.
