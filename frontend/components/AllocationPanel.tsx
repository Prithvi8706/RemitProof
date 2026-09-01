import { CheckCircle2 } from "lucide-react";
import { formatMoney } from "@/lib/format";
import type { AllocationRow, ProofRecord } from "@/lib/types";

export function AllocationPanel({
  allocation,
  proof,
  currency,
  paymentAmount,
}: {
  allocation: AllocationRow[];
  proof: ProofRecord | null;
  currency: string;
  paymentAmount: string;
}) {
  return (
    <section aria-labelledby="allocation-title" className="border border-line bg-canvas">
      <div className="flex items-center justify-between gap-4 border-b border-line bg-surface px-5 py-4 sm:px-6">
        <div>
          <h2 id="allocation-title" className="text-sm font-semibold text-ink">Proposed allocation</h2>
          <p className="mt-0.5 text-xs text-muted">Recomputed with Decimal arithmetic</p>
        </div>
        {proof?.financial_validity && <CheckCircle2 className="size-5 text-primary" aria-label="Arithmetic verified" />}
      </div>
      <div className="px-5 py-5 sm:px-6">
        {allocation.length ? (
          <div className="divide-y divide-line">
            {allocation.map((row) => (
              <div key={row.record_id} className="grid grid-cols-[24px_minmax(0,1fr)_auto] items-center gap-3 py-3.5">
                <span className="numeric text-center text-sm font-semibold text-muted">{row.operator}</span>
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-ink">{row.record_id}</div>
                  <div className="mt-0.5 truncate text-xs text-muted">{row.description}</div>
                </div>
                <div className={`numeric text-sm font-semibold ${row.operator === "-" ? "text-danger" : "text-ink"}`}>
                  {row.operator === "-" ? "−" : ""}{formatMoney(row.amount, row.currency)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="py-5 text-sm text-muted">No complete allocation was proposed.</p>
        )}
        <div className="mt-4 flex items-end justify-between gap-4 border-t-2 border-ink pt-4">
          <div>
            <div className="text-xs font-medium text-muted">Received payment</div>
            <div className="mt-1 text-sm font-semibold text-ink">
              {proof?.financial_validity ? "Arithmetic verified" : "Arithmetic not verified"}
            </div>
          </div>
          <div className="numeric text-2xl font-semibold tracking-[-0.025em] text-ink">
            {formatMoney(proof?.payment_total ?? paymentAmount, currency)}
          </div>
        </div>
      </div>
    </section>
  );
}
