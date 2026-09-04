export type BenchmarkRunMode = "cache_only" | "live" | "mixed" | "unknown";

export interface BenchmarkProvenanceInput {
  result_status?: string | null;
  evaluation_mode?: string | null;
  timing_scope?: string | null;
  cache?: {
    status?: string | null;
    hits?: number | null;
    misses?: number | null;
    model_inference_included?: boolean | null;
    model_inference_attempted?: boolean | null;
  } | null;
  provenance?: {
    live_model_calls?: number | null;
  } | null;
}

export interface BenchmarkProvenanceView {
  mode: BenchmarkRunMode;
  badgeLabel: string;
  shortLabel: string;
  kickerLabel: string;
  description: string;
  timingDescription: string;
  systemLimitNote: string;
}

function isPositiveNumber(value: number | null | undefined): boolean {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

export function getBenchmarkRunMode(input: BenchmarkProvenanceInput): BenchmarkRunMode {
  const cache = input.cache;
  const evaluationMode = input.evaluation_mode?.toLowerCase() ?? "";
  const cacheStatus = cache?.status?.toLowerCase() ?? "";
  const liveCalls = input.provenance?.live_model_calls;
  const inferenceAttempted =
    cache?.model_inference_attempted ??
    cache?.model_inference_included ??
    (typeof liveCalls === "number" ? liveCalls > 0 : undefined);
  const cachedProposals = isPositiveNumber(cache?.hits);

  if (inferenceAttempted === true) {
    return cachedProposals ? "mixed" : "live";
  }

  if (
    cacheStatus === "cache_only" ||
    evaluationMode.startsWith("cache_only") ||
    (input.result_status === "offline_verifier_regression_only" && inferenceAttempted === false)
  ) {
    return "cache_only";
  }

  return "unknown";
}

export function describeBenchmarkRun(input: BenchmarkProvenanceInput): BenchmarkProvenanceView {
  const mode = getBenchmarkRunMode(input);
  const offline = input.result_status === "offline_verifier_regression_only";
  const timingScope = input.timing_scope?.trim();
  const timingDescription = timingScope
    ? `Timing scope: ${timingScope}.`
    : "Timing scope is not declared in the publication.";

  if (mode === "cache_only") {
    return {
      mode,
      badgeLabel: offline ? "Offline verifier regression" : "Cached proposal replay",
      shortLabel: offline ? "Benchmark regression" : "Benchmark cached",
      kickerLabel: offline ? "OFFLINE VERIFIER REGRESSION" : "CACHED PROPOSAL REPLAY",
      description:
        "This run replays cached model proposals. Model inference was not attempted, so throughput and latency exclude model time.",
      timingDescription,
      systemLimitNote:
        "This publication uses cached proposal replay. It measures verifier behavior, not fresh end-to-end model inference.",
    };
  }

  if (mode === "live") {
    return {
      mode,
      badgeLabel: offline ? "Offline regression, inference attempted" : "Live model evaluation",
      shortLabel: offline ? "Benchmark regression" : "Benchmark live",
      kickerLabel: offline ? "INFERENCE ATTEMPTED, REGRESSION ONLY" : "LIVE MODEL EVALUATION",
      description: offline
        ? "Model inference was attempted, but this publication is regression-only. Read the timing scope and eligibility metadata before comparing performance."
        : "This run includes attempted model inference. Read the timing scope and eligibility metadata before comparing performance.",
      timingDescription,
      systemLimitNote: offline
        ? "Model inference was attempted, but this publication is labeled regression-only and is not an end-to-end benchmark claim."
        : "This publication includes attempted model inference; its timing scope is shown in the provenance record.",
    };
  }

  if (mode === "mixed") {
    return {
      mode,
      badgeLabel: offline ? "Offline regression, mixed proposals" : "Mixed cache/live evaluation",
      shortLabel: offline ? "Benchmark regression" : "Benchmark mixed",
      kickerLabel: offline ? "MIXED PROPOSALS, REGRESSION ONLY" : "MIXED CACHE/LIVE EVALUATION",
      description: offline
        ? "This run combines cached proposals with attempted model inference, but the publication is regression-only. Read the timing scope and eligibility metadata before comparing performance."
        : "This run combines cached proposals with attempted model inference. Read the timing scope and eligibility metadata before comparing performance.",
      timingDescription,
      systemLimitNote: offline
        ? "This publication combines cached and attempted live proposals and is labeled regression-only."
        : "This publication combines cached and attempted live proposals; its timing scope is shown in the provenance record.",
    };
  }

  return {
    mode,
    badgeLabel: offline ? "Offline regression, mode unclear" : "Benchmark mode unavailable",
    shortLabel: "Benchmark mode unclear",
    kickerLabel: "BENCHMARK PROVENANCE UNCLEAR",
    description:
      "The publication does not declare whether model inference was attempted. Treat throughput and latency as unverified until the provenance record is corrected.",
    timingDescription,
    systemLimitNote:
      "The publication does not declare its model-inference mode, so performance comparisons should be treated as unverified.",
  };
}
