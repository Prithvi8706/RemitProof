import { Check, CircleAlert, LockKeyhole, Minus } from "lucide-react";
import type { ExceptionDetail } from "@/lib/types";

type StepState = "complete" | "attention" | "blocked";

function StepIcon({ state }: { state: StepState }) {
  if (state === "complete") {
    return <Check className="size-3.5" strokeWidth={2.5} aria-hidden="true" />;
  }
  if (state === "attention") {
    return <CircleAlert className="size-3.5" aria-hidden="true" />;
  }
  return <Minus className="size-3.5" aria-hidden="true" />;
}

export function InvestigationPath({ detail }: { detail: ExceptionDetail }) {
  const proofPassed = Boolean(
    detail.proof?.financial_validity &&
    detail.proof.state_validity &&
    detail.proof.currency_validity,
  );
  const alternativesFound = detail.alternatives.length > 1;
  const conflictCleared = Boolean(
    alternativesFound &&
    detail.sufficiency?.evidence_disambiguates_alternatives &&
    detail.conflict?.status === "cleared",
  );
  const resolved = detail.decision.decision === "resolved";
  const unresolvedNonAllocationConflict = Boolean(
    detail.conflict?.status === "unresolved" && !alternativesFound,
  );
  const steps: Array<{ label: string; detail: string; state: StepState }> = [
    {
      label: "Normal match stopped",
      detail: detail.baseline.reason.replaceAll("_", " "),
      state: "attention",
    },
    {
      label: "Proposal constructed",
      detail: detail.proposal ? "Structured hypothesis available" : "No valid proposal",
      state: detail.proposal ? "complete" : "blocked",
    },
    {
      label: "Financial proof",
      detail: proofPassed ? "Arithmetic and record constraints passed" : "A deterministic check failed",
      state: proofPassed ? "complete" : "blocked",
    },
    {
      label: "Alternative search",
      detail: "Financially valid competing allocations enumerated",
      state: "complete",
    },
    {
      label: alternativesFound
        ? `${detail.alternatives.length} explanations found`
        : detail.proof?.financial_validity
          ? "Unique financial solution"
          : "No valid allocation",
      detail: alternativesFound
        ? "Arithmetic alone cannot authorize the proposal"
        : detail.proof?.financial_validity
          ? "No competing allocation survived"
          : "The proposal failed financial constraints",
      state: alternativesFound ? "attention" : detail.proof?.financial_validity ? "complete" : "blocked",
    },
    {
      label: "Evidence compared",
      detail: detail.sufficiency?.chosen_proposal_supported
        ? "Proposal support evaluated against every alternative"
        : "Proposal support is incomplete or contradicted",
      state: detail.sufficiency?.chosen_proposal_supported ? "complete" : "blocked",
    },
    {
      label: conflictCleared
        ? "Conflict cleared"
        : alternativesFound
          ? "Conflict remains"
          : unresolvedNonAllocationConflict
            ? "Contradiction found"
            : "No conflict remains",
      detail: conflictCleared
        ? "Cited evidence uniquely selects the proposal"
        : alternativesFound
          ? "Available evidence does not establish one intent"
          : unresolvedNonAllocationConflict
            ? detail.conflict?.reason ?? "Evidence conflicts with the proposal"
            : "No unresolved alternative requires disambiguation",
      state: conflictCleared || (!alternativesFound && !unresolvedNonAllocationConflict) ? "complete" : "blocked",
    },
    {
      label: resolved ? "Safe to resolve" : "Decision blocked",
      detail: resolved ? "Deterministic authorization issued" : "Human review required",
      state: resolved ? "complete" : "blocked",
    },
  ];

  return (
    <section aria-labelledby="investigation-path-title" className="mt-8 border-y border-line bg-surface">
      <div className="flex items-center gap-2 px-4 py-3 sm:px-5">
        <LockKeyhole className="size-4 text-primary" aria-hidden="true" />
        <h2 id="investigation-path-title" className="text-sm font-semibold text-ink">Investigation path</h2>
      </div>
      <ol className="grid border-t border-line sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        {steps.map((step, index) => (
          <li key={step.label} className="relative border-b border-line px-4 py-4 sm:border-r xl:border-b-0 last:border-r-0">
            <div className="flex items-center gap-2">
              <span className={`grid size-6 shrink-0 place-items-center rounded-full ${
                step.state === "complete"
                  ? "bg-primary-soft text-primary-dark"
                  : step.state === "attention"
                    ? "bg-warning-soft text-warning"
                    : "bg-danger-soft text-danger"
              }`}>
                <StepIcon state={step.state} />
              </span>
              <span className="numeric text-[11px] font-semibold text-muted">{index + 1}</span>
            </div>
            <h3 className="mt-3 text-sm font-semibold text-ink">{step.label}</h3>
            <p className="mt-1 text-xs leading-5 text-muted">{step.detail}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
