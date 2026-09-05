import assert from "node:assert/strict";
import test from "node:test";
import { describeBenchmarkRun, getBenchmarkRunMode } from "./benchmark-provenance.ts";

const cacheOnly = {
  result_status: "offline_verifier_regression_only",
  evaluation_mode: "cache_only_legacy_identity_unverified_proposal_replay",
  timing_scope: "pipeline/verifier replay timing; model inference was not attempted",
  cache: {
    status: "cache_only",
    hits: 30,
    misses: 0,
    model_inference_attempted: false,
    model_inference_included: false,
  },
  provenance: { live_model_calls: 0 },
};

test("identifies cache-only replay from published metadata", () => {
  const view = describeBenchmarkRun(cacheOnly);

  assert.equal(getBenchmarkRunMode(cacheOnly), "cache_only");
  assert.equal(view.badgeLabel, "Offline verifier regression");
  assert.match(view.description, /Model inference was not attempted/);
  assert.match(view.timingDescription, /pipeline\/verifier replay timing/);
});

test("identifies a live run when model inference was attempted without cached proposals", () => {
  const view = describeBenchmarkRun({
    result_status: "model_backed_benchmark",
    evaluation_mode: "live_or_mixed_proposal_evaluation",
    timing_scope: "end-to-end pipeline timing including attempted model inference",
    cache: {
      status: "live_or_mixed",
      hits: 0,
      misses: 30,
      model_inference_attempted: true,
      model_inference_included: true,
    },
    provenance: { live_model_calls: 30 },
  });

  assert.equal(view.mode, "live");
  assert.equal(view.badgeLabel, "Live model evaluation");
  assert.match(view.description, /includes attempted model inference/);
});

test("identifies mixed runs and keeps regression status visible", () => {
  const view = describeBenchmarkRun({
    result_status: "offline_verifier_regression_only",
    evaluation_mode: "live_or_mixed_proposal_evaluation",
    timing_scope: "end-to-end pipeline timing including attempted model inference",
    cache: {
      status: "live_or_mixed",
      hits: 12,
      misses: 18,
      model_inference_attempted: true,
      model_inference_included: true,
    },
    provenance: { live_model_calls: 18 },
  });

  assert.equal(view.mode, "mixed");
  assert.equal(view.badgeLabel, "Offline regression, mixed proposals");
  assert.match(view.description, /combines cached proposals with attempted model inference/);
  assert.match(view.description, /regression-only/);
});

test("does not invent a mode when the publication omits mode metadata", () => {
  const view = describeBenchmarkRun({ result_status: "model_backed_benchmark" });

  assert.equal(view.mode, "unknown");
  assert.equal(view.badgeLabel, "Benchmark mode unavailable");
  assert.match(view.description, /does not declare whether model inference was attempted/);
});
