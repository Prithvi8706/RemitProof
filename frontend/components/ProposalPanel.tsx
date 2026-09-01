import { AlertCircle, Bot, FileCheck2 } from "lucide-react";
import { formatMoney } from "@/lib/format";
import type { ExceptionDetail } from "@/lib/types";

export function ProposalPanel({ detail }: { detail: ExceptionDetail }) {
  const proposal = detail.proposal;

  return (
    <section aria-labelledby="proposal-title" className="border border-line bg-canvas">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line bg-surface px-5 py-4 sm:px-6">
        <div className="flex items-start gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-[10px] bg-accent-soft text-accent">
            <Bot className="size-4.5" aria-hidden="true" />
          </span>
          <div>
            <h2 id="proposal-title" className="text-base font-semibold text-ink">AI proposal</h2>
            <p className="mt-0.5 text-xs leading-5 text-muted">A hypothesis for verification, not an authorization.</p>
          </div>
        </div>
        <span className="rounded-full border border-line-strong px-2.5 py-1 text-[11px] font-semibold text-muted">
          UNAUTHORIZED
        </span>
      </div>

      {proposal ? (
        <>
          <dl className="grid gap-px border-b border-line bg-line sm:grid-cols-2">
            <div className="bg-canvas px-5 py-4 sm:px-6">
              <dt className="text-xs font-medium text-muted">Proposed customer</dt>
              <dd className="numeric mt-1 text-sm font-semibold text-ink">{proposal.proposed_customer ?? "Not identified"}</dd>
            </div>
            <div className="bg-canvas px-5 py-4 sm:px-6">
              <dt className="text-xs font-medium text-muted">Cited evidence</dt>
              <dd className="numeric mt-1 text-sm font-semibold text-ink">{proposal.evidence_ids.length} records</dd>
            </div>
          </dl>

          <div className="px-5 py-5 sm:px-6">
            <h3 className="text-xs font-semibold text-muted">Proposed allocation</h3>
            {detail.proposed_allocation.length ? (
              <div className="mt-2 divide-y divide-line">
                {detail.proposed_allocation.map((row) => (
                  <div key={row.record_id} className="grid grid-cols-[24px_minmax(0,1fr)_auto] items-center gap-3 py-3">
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
              <p className="mt-3 text-sm text-muted">No complete allocation was proposed.</p>
            )}

            <div className="mt-4 flex items-end justify-between gap-4 border-t-2 border-ink pt-4">
              <div>
                <div className="text-xs font-medium text-muted">Payment to explain</div>
                <div className="mt-1 text-xs text-muted">Independent proof recomputes this total.</div>
              </div>
              <div className="numeric text-xl font-semibold tracking-[-0.02em] text-ink">
                {formatMoney(detail.payment.amount, detail.payment.currency)}
              </div>
            </div>
          </div>

          {proposal.unresolved_questions.length > 0 && (
            <div className="border-t border-warning/30 bg-warning-soft px-5 py-4 sm:px-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden="true" />
                <div>
                  <h3 className="text-xs font-semibold text-ink">Unresolved questions</h3>
                  <ul className="mt-1 space-y-1 text-xs leading-5 text-muted">
                    {proposal.unresolved_questions.map((question) => <li key={question}>{question}</li>)}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="flex items-start gap-3 px-5 py-6 text-sm leading-6 text-muted sm:px-6">
          <FileCheck2 className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          No valid structured proposal was produced. The case remains blocked.
        </div>
      )}
    </section>
  );
}
