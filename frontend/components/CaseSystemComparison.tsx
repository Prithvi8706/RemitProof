import { CircleCheck, CircleMinus, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { explainReason } from "@/lib/format";
import type { BenchmarkCaseRow } from "@/lib/types";

export function CaseSystemComparison({ comparison }: { comparison: BenchmarkCaseRow }) {
  const remitproofResolved = comparison.remitproof_decision === "resolved";
  const remitproofCorrect = comparison.remitproof_correct_resolution || comparison.correct_abstention;

  return (
    <section className="mt-8 overflow-hidden rounded-[12px] border border-line" aria-labelledby="system-comparison-title">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line bg-surface px-5 py-4">
        <div>
          <h2 id="system-comparison-title" className="text-sm font-semibold text-ink">
            Same receipt, three authorization policies
          </h2>
          <p className="mt-1 max-w-[72ch] text-xs leading-5 text-muted">
            The proposal-only result is a forced-proposal verifier ablation. It is not a standalone model with its
            own abstention policy.
          </p>
        </div>
        <Link href="/benchmark" className="rounded-md py-1 text-xs font-semibold text-primary-dark hover:text-primary">
          Inspect benchmark methodology
        </Link>
      </div>

      <div className="grid lg:grid-cols-3">
        <PolicyDecision
          title="Baseline rules"
          decision="Human review"
          verdict={comparison.expected_should_resolve ? "False escalation" : "Correct abstention"}
          description="Structured reconciliation stopped before semantic interpretation."
          tone="neutral"
          icon={<CircleMinus className="size-5" aria-hidden="true" />}
        />
        <PolicyDecision
          title="Proposal only"
          decision={comparison.llm_only_decision === "resolve" ? "Resolve" : "Abstain"}
          verdict={comparison.llm_only_wrong_resolution ? "Wrong automatic resolution" : "Correct proposal"}
          description={
            comparison.llm_only_wrong_resolution
              ? "The semantic hypothesis would be treated as authorization without deterministic proof or conflict testing."
              : "The proposal is correct on this case, but no independent verifier owns the authorization boundary."
          }
          tone={comparison.llm_only_wrong_resolution ? "danger" : "neutral"}
          icon={<ShieldAlert className="size-5" aria-hidden="true" />}
        />
        <PolicyDecision
          title="RemitProof"
          decision={remitproofResolved ? "Resolve with proof" : "Human review"}
          verdict={
            comparison.remitproof_correct_resolution
              ? "Supported resolution"
              : comparison.correct_abstention
                ? "Correct safety control"
                : comparison.false_escalation
                  ? "Conservative miss"
                  : remitproofCorrect
                    ? "Correct decision"
                    : "Review required"
          }
          description={explainReason(comparison.reason)}
          tone={comparison.wrong_auto_resolution ? "danger" : remitproofCorrect ? "good" : "warning"}
          icon={<CircleCheck className="size-5" aria-hidden="true" />}
          emphasized
        />
      </div>
    </section>
  );
}

function PolicyDecision({
  title,
  decision,
  verdict,
  description,
  tone,
  icon,
  emphasized = false,
}: {
  title: string;
  decision: string;
  verdict: string;
  description: string;
  tone: "neutral" | "good" | "warning" | "danger";
  icon: React.ReactNode;
  emphasized?: boolean;
}) {
  const toneClass =
    tone === "danger"
      ? "text-danger"
      : tone === "good"
        ? "text-primary-dark"
        : tone === "warning"
          ? "text-warning"
          : "text-muted";
  return (
    <div className={`p-5 lg:border-r lg:border-line lg:last:border-r-0 ${emphasized ? "bg-primary-soft/40" : ""}`}>
      <div className={`flex items-center gap-2 ${toneClass}`}>
        {icon}
        <h3 className="text-xs font-semibold">{title}</h3>
      </div>
      <p className="mt-4 text-lg font-semibold tracking-[-0.02em] text-ink">{decision}</p>
      <p className={`mt-1 text-xs font-semibold ${toneClass}`}>{verdict}</p>
      <p className="mt-3 max-w-[48ch] text-xs leading-5 text-muted">{description}</p>
    </div>
  );
}
