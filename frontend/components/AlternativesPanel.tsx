import { GitCompareArrows } from "lucide-react";
import { formatMoney } from "@/lib/format";
import type { AlternativeRecord, DecisionRecord, SufficiencyRecord } from "@/lib/types";

function sameSet(first: string[], second: string[]) {
  return first.length === second.length && first.every((item) => second.includes(item));
}

export function AlternativesPanel({
  alternatives,
  decision,
  sufficiency,
  currency,
}: {
  alternatives: AlternativeRecord[];
  decision: DecisionRecord;
  sufficiency: SufficiencyRecord | null;
  currency: string;
}) {
  const competing = alternatives.length > 1;
  const cleared = Boolean(competing && sufficiency?.evidence_disambiguates_alternatives);
  const unresolved = Boolean(competing && !cleared);
  const status = cleared
    ? "Conflict cleared by evidence"
    : unresolved
      ? "Conflict remains"
      : "No competing allocation survived";

  return (
    <section aria-labelledby="alternatives-title" className="border border-line">
      <div className={`flex flex-wrap items-start justify-between gap-4 border-b px-5 py-4 sm:px-6 ${
        unresolved
          ? "border-warning/30 bg-warning-soft"
          : cleared
            ? "border-primary/25 bg-primary-soft"
            : "border-line bg-surface"
      }`}>
        <div className="flex items-center gap-3">
        <span className="grid size-9 place-items-center rounded-[10px] bg-accent-soft text-accent">
          <GitCompareArrows className="size-4.5" aria-hidden="true" />
        </span>
        <div>
          <h2 id="alternatives-title" className="text-xl font-semibold tracking-[-0.02em] text-ink">
            Conflict test
          </h2>
          <p className="mt-0.5 text-sm text-muted">The verifier searches beyond the model&apos;s chosen explanation.</p>
        </div>
        </div>
        <span className={`text-xs font-semibold ${unresolved ? "text-warning" : "text-primary-dark"}`}>{status}</span>
      </div>
      {alternatives.length > 0 ? (
      <div className="divide-y divide-line">
        {alternatives.map((alternative, index) => {
          const selected =
            alternative.customer_id === decision.customer_id &&
            sameSet(alternative.invoice_ids, decision.invoice_ids) &&
            sameSet(alternative.credit_ids, decision.credit_ids);
          return (
            <div key={`${alternative.customer_id}-${alternative.invoice_ids.join("-")}-${index}`} className={selected ? "bg-primary-soft px-4 py-4" : "px-4 py-4"}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-sm font-semibold text-ink">
                    Option {index + 1}
                    {selected && (
                      <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold tracking-[0.04em] text-white">
                        PROPOSED
                      </span>
                    )}
                    {!selected && competing && (
                      <span className={`text-[10px] font-semibold ${cleared ? "text-muted" : "text-warning"}`}>
                        {cleared ? "ELIMINATED BY EVIDENCE" : "STILL PLAUSIBLE"}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 text-xs leading-5 text-muted">
                    {alternative.invoice_ids.join(" + ")}
                    {alternative.credit_ids.length > 0 ? ` − ${alternative.credit_ids.join(" − ")}` : ""}
                  </div>
                </div>
                <div className="numeric text-base font-semibold text-ink">
                  {formatMoney(alternative.calculated_total, currency)}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      ) : (
        <p className="px-5 py-5 text-sm leading-6 text-muted sm:px-6">
          No financially complete allocation survived the deterministic constraints.
        </p>
      )}
    </section>
  );
}
