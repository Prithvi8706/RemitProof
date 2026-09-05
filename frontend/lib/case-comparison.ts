import type { BenchmarkCaseRow } from "@/lib/types";

export interface ComparisonPresentation {
  decision: string;
  verdict: string;
  tone: "neutral" | "good" | "warning" | "danger";
}

export function describeProposalOnlyOutcome(comparison: BenchmarkCaseRow): ComparisonPresentation {
  if (comparison.llm_only_wrong_resolution) {
    return {
      decision: "Resolve",
      verdict: "Wrong automatic resolution",
      tone: "danger",
    };
  }
  if (comparison.llm_only_decision === "abstain") {
    return comparison.expected_should_resolve
      ? {
          decision: "Abstain",
          verdict: "Missed resolvable exception",
          tone: "warning",
        }
      : {
          decision: "Abstain",
          verdict: "Correct abstention",
          tone: "neutral",
        };
  }
  return {
    decision: "Resolve",
    verdict: "Correct proposal",
    tone: "neutral",
  };
}

export function describeRemitProofOutcome(comparison: BenchmarkCaseRow): ComparisonPresentation {
  if (comparison.wrong_auto_resolution) {
    return {
      decision: "Unsafe resolution",
      verdict: "Wrong automatic resolution",
      tone: "danger",
    };
  }
  if (comparison.remitproof_correct_resolution) {
    return {
      decision: "Resolve with proof",
      verdict: "Supported resolution",
      tone: "good",
    };
  }
  if (comparison.correct_abstention) {
    return {
      decision: "Human review",
      verdict: "Correct safety control",
      tone: "good",
    };
  }
  if (comparison.false_escalation) {
    return {
      decision: "Human review",
      verdict: "Conservative miss",
      tone: "warning",
    };
  }
  return {
    decision: comparison.remitproof_decision === "resolved" ? "Resolve" : "Human review",
    verdict: "Review required",
    tone: "warning",
  };
}
