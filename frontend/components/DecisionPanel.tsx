import { CheckCircle2, CircleHelp, TriangleAlert } from "lucide-react";
import { DecisionBadge } from "@/components/DecisionBadge";
import { explainReason, titleCase } from "@/lib/format";
import type { ExceptionDetail } from "@/lib/types";

export function DecisionPanel({ detail }: { detail: ExceptionDetail }) {
  const isResolved = detail.decision.decision === "resolved";
  const Icon = isResolved ? CheckCircle2 : detail.decision.decision === "human_review" ? TriangleAlert : CircleHelp;
  const competing = detail.alternatives.length > 1;
  const ambiguous = Boolean(
    competing &&
      detail.sufficiency &&
      !detail.sufficiency.evidence_disambiguates_alternatives,
  );
  const description = isResolved
    ? "The proposed allocation passed deterministic proof and is uniquely supported by the available evidence."
    : ambiguous
      ? `${detail.alternatives.length} financially valid explanations remain. No available evidence uniquely determines which allocation was intended.`
      : explainReason(detail.decision.reason);

  return (
    <section
      aria-labelledby="decision-title"
      className={`border p-6 sm:p-8 ${
        isResolved
          ? "border-primary/30 bg-primary-soft"
          : "border-warning/30 bg-warning-soft"
      }`}
    >
      <DecisionBadge decision={detail.decision.decision} />
      <Icon
        className={`mt-8 size-9 ${isResolved ? "text-primary-dark" : "text-warning"}`}
        strokeWidth={1.8}
        aria-hidden="true"
      />
      <h2 id="decision-title" className="mt-4 text-2xl font-semibold tracking-[-0.025em] text-ink">
        {isResolved ? "Authorized to resolve" : "Decision blocked"}
      </h2>
      <p className="mt-3 max-w-[62ch] text-sm leading-6 text-muted">{description}</p>
      <dl className="mt-7 grid grid-cols-2 gap-x-5 gap-y-4 border-t border-current/10 pt-5 text-sm">
        <div>
          <dt className="text-xs font-medium text-muted">Exception class</dt>
          <dd className="mt-1 font-semibold text-ink">{titleCase(detail.exception_class)}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-muted">Decision latency</dt>
          <dd className="numeric mt-1 font-semibold text-ink">{detail.decision.latency_ms} ms</dd>
        </div>
        {competing && (
          <div className="col-span-2">
            <dt className="text-xs font-medium text-muted">Financially valid allocations found</dt>
            <dd className="numeric mt-1 font-semibold text-ink">{detail.alternatives.length}</dd>
          </div>
        )}
      </dl>
    </section>
  );
}
