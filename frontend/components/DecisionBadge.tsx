import { CircleDot, ShieldCheck, TriangleAlert } from "lucide-react";
import type { DecisionState } from "@/lib/types";

const DECISIONS = {
  matched_normally: {
    label: "MATCHED NORMALLY",
    className: "border-line-strong bg-surface text-ink",
    icon: CircleDot,
  },
  resolved: {
    label: "REMITPROOF RESOLVED",
    className: "border-primary/25 bg-primary-soft text-primary-dark",
    icon: ShieldCheck,
  },
  human_review: {
    label: "HUMAN REVIEW REQUIRED",
    className: "border-warning/30 bg-warning-soft text-[oklch(0.36_0.09_65)]",
    icon: TriangleAlert,
  },
} as const;

export function DecisionBadge({ decision, compact = false }: { decision: DecisionState; compact?: boolean }) {
  const config = DECISIONS[decision];
  const Icon = config.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold tracking-[0.035em] ${
        compact ? "px-2.5 py-1 text-[10px]" : "px-3 py-1.5 text-[11px]"
      } ${config.className}`}
    >
      <Icon className={compact ? "size-3" : "size-3.5"} aria-hidden="true" />
      {config.label}
    </span>
  );
}
