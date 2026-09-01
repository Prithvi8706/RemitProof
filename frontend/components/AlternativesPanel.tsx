import { GitCompareArrows } from "lucide-react";
import { formatMoney } from "@/lib/format";
import type { AlternativeRecord, DecisionRecord } from "@/lib/types";

function sameSet(first: string[], second: string[]) {
  return first.length === second.length && first.every((item) => second.includes(item));
}

export function AlternativesPanel({
  alternatives,
  decision,
  currency,
}: {
  alternatives: AlternativeRecord[];
  decision: DecisionRecord;
  currency: string;
}) {
  if (alternatives.length <= 1) return null;

  return (
    <section aria-labelledby="alternatives-title">
      <div className="mb-4 flex items-center gap-3">
        <span className="grid size-9 place-items-center rounded-[10px] bg-accent-soft text-accent">
          <GitCompareArrows className="size-4.5" aria-hidden="true" />
        </span>
        <div>
          <h2 id="alternatives-title" className="text-xl font-semibold tracking-[-0.02em] text-ink">
            Alternative hypotheses
          </h2>
          <p className="mt-0.5 text-sm text-muted">Every financially valid allocation found in the candidate set.</p>
        </div>
      </div>
      <div className="divide-y divide-line border-y border-line">
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
    </section>
  );
}
