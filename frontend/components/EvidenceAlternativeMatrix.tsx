import { FileKey2, Scale, ShieldAlert } from "lucide-react";
import type { ExceptionDetail } from "@/lib/types";

const relationshipLabel = {
  supports: "Supports",
  contradicts: "Contradicts",
  shared_fact: "Shared fact",
  superseded: "Superseded",
  irrelevant: "No bearing",
} as const;

export function EvidenceAlternativeMatrix({ detail }: { detail: ExceptionDetail }) {
  const matrix = detail.sufficiency?.evidence_alternative_matrix ?? [];
  const evidenceIds = Array.from(new Set(matrix.map((row) => row.evidence_id)));
  const critical = detail.counterfactuals.filter((row) => row.decision_critical);

  if (detail.alternatives.length === 0 || matrix.length === 0) return null;

  return (
    <section className="mt-12 border-y border-line" aria-labelledby="evidence-matrix-title">
      <div className="flex flex-col gap-3 bg-surface px-5 py-5 sm:flex-row sm:items-start sm:justify-between sm:px-6">
        <div className="flex items-start gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-[10px] bg-accent-soft text-accent">
            <Scale className="size-4.5" aria-hidden="true" />
          </span>
          <div>
            <h2 id="evidence-matrix-title" className="text-xl font-semibold tracking-[-0.02em] text-ink">
              Why this proposal, not the alternative?
            </h2>
            <p className="mt-1 max-w-[68ch] text-sm leading-6 text-muted">
              Financial validity gets an allocation into the comparison. Evidence determines whether any allocation is justified.
            </p>
          </div>
        </div>
        {detail.conflict && (
          <div className="text-sm sm:text-right">
            <div className="numeric font-semibold text-ink">{detail.conflict.conflict_id}</div>
            <div className={detail.conflict.status === "cleared" ? "text-primary-dark" : "text-warning"}>
              {detail.conflict.status === "cleared" ? "Conflict cleared" : "Conflict unresolved"}
            </div>
          </div>
        )}
      </div>

      <div className="table-scroll border-y border-line">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead className="bg-canvas">
            <tr className="border-b border-line">
              <th scope="col" className="px-5 py-3 text-left text-xs font-semibold text-muted">Evidence</th>
              {detail.alternatives.map((alternative, index) => (
                <th key={alternative.allocation_id} scope="col" className="px-5 py-3 text-left">
                  <span className="block font-semibold text-ink">
                    {alternative.customer_id === detail.decision.customer_id &&
                    sameSet(alternative.invoice_ids, detail.decision.invoice_ids) &&
                    sameSet(alternative.credit_ids, detail.decision.credit_ids)
                      ? "Proposal"
                      : `Alternative ${index + 1}`}
                  </span>
                  <span className="numeric mt-0.5 block text-xs font-normal text-muted">{alternative.allocation_id}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {evidenceIds.map((evidenceId) => (
              <tr key={evidenceId}>
                <th scope="row" className="numeric px-5 py-4 text-left font-semibold text-ink">{evidenceId}</th>
                {detail.alternatives.map((alternative) => {
                  const assessment = matrix.find(
                    (row) => row.evidence_id === evidenceId && row.allocation_id === alternative.allocation_id,
                  );
                  const relationship = assessment?.relationship ?? "irrelevant";
                  return (
                    <td key={alternative.allocation_id} className="px-5 py-4 align-top">
                      <span className={`font-semibold ${
                        relationship === "supports"
                          ? "text-primary-dark"
                          : relationship === "contradicts"
                            ? "text-danger"
                            : "text-muted"
                      }`}>
                        {relationshipLabel[relationship]}
                      </span>
                      <span className="mt-1 block max-w-[34ch] text-xs leading-5 text-muted">{assessment?.reason}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {critical.length > 0 && (
        <div className="grid gap-4 bg-primary-soft px-5 py-5 sm:grid-cols-[auto_1fr] sm:px-6">
          <FileKey2 className="size-5 text-primary-dark" aria-hidden="true" />
          <div>
            <h3 className="text-sm font-semibold text-ink">Decision-critical evidence</h3>
            {critical.map((item) => (
              <div key={item.evidence_id} className="mt-2">
                <span className="numeric font-semibold text-primary-dark">{item.evidence_id}</span>
                <p className="mt-1 text-sm leading-6 text-muted">{item.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {detail.conflict?.status === "unresolved" && (
        <div className="flex items-start gap-3 bg-warning-soft px-5 py-5 sm:px-6">
          <ShieldAlert className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden="true" />
          <div>
            <h3 className="text-sm font-semibold text-ink">Required disambiguation</h3>
            <p className="mt-1 text-sm leading-6 text-muted">{detail.conflict.required_disambiguation.join("; ")}</p>
          </div>
        </div>
      )}
    </section>
  );
}

function sameSet(first: string[], second: string[]) {
  return first.length === second.length && first.every((item) => second.includes(item));
}
