import { AlertTriangle, Building2, FileBadge2, FileText, Mail } from "lucide-react";
import { titleCase } from "@/lib/format";
import type { EvidenceRecord } from "@/lib/types";

const ICONS = {
  customer_record: Building2,
  invoice_record: FileText,
  remittance_email: Mail,
  credit_note: FileBadge2,
};

function renderContent(content: EvidenceRecord["content"]) {
  if (typeof content === "string") {
    return <p className="text-sm leading-6 text-muted">{content}</p>;
  }
  return (
    <dl className="grid gap-2 text-xs text-muted">
      {Object.entries(content).map(([key, value]) => (
        <div key={key} className="grid gap-1 sm:grid-cols-[120px_minmax(0,1fr)] sm:gap-3">
          <dt className="font-medium">{titleCase(key)}</dt>
          <dd className="break-words text-ink">{Array.isArray(value) ? value.join(", ") || "None" : String(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function EvidenceList({ evidence }: { evidence: EvidenceRecord[] }) {
  return (
    <div className="border-y border-line">
      {evidence.map((item) => {
        const Icon = ICONS[item.evidence_type];
        return (
          <details key={item.evidence_id} className="group border-b border-line last:border-b-0">
            <summary className="flex cursor-pointer list-none items-center gap-3 px-1 py-4 hover:text-primary">
              <span className="grid size-8 shrink-0 place-items-center rounded-[9px] bg-surface text-primary-dark">
                <Icon className="size-4" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block break-words text-sm font-semibold text-ink">{item.title}</span>
                <span className="mt-0.5 block break-all text-xs text-muted">
                  {item.evidence_id} · {titleCase(item.evidence_type)}
                </span>
              </span>
              <span className="shrink-0 text-xs font-semibold text-primary group-open:hidden">Inspect</span>
              <span className="hidden shrink-0 text-xs font-semibold text-primary group-open:inline">Close</span>
            </summary>
            <div className="pb-5 pl-1 pr-2 sm:pl-12">{renderContent(item.content)}</div>
          </details>
        );
      })}
    </div>
  );
}

export function EvidencePanel({
  citedEvidence,
  auditRecords,
  missingEvidenceIds,
}: {
  citedEvidence: EvidenceRecord[];
  auditRecords: EvidenceRecord[];
  missingEvidenceIds: string[];
}) {
  return (
    <section aria-labelledby="evidence-title">
      <div className="mb-4">
        <h2 id="evidence-title" className="text-xl font-semibold tracking-[-0.02em] text-ink">
          Evidence and audit records
        </h2>
        <p className="mt-1 text-sm text-muted">Model citations are kept separate from records appended for allocation context.</p>
      </div>

      {missingEvidenceIds.length > 0 && (
        <div className="mb-6 border border-warning/35 bg-warning-soft p-4" role="status">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden="true" />
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-ink">Required citations are missing</h3>
              <p className="mt-1 text-xs leading-5 text-muted">These records are required before autonomous resolution:</p>
              <ul className="mt-2 flex flex-wrap gap-2" aria-label="Missing evidence IDs">
                {missingEvidenceIds.map((evidenceId) => (
                  <li key={evidenceId} className="numeric break-all rounded-md bg-canvas px-2 py-1 text-xs font-semibold text-ink">
                    {evidenceId}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      <div>
        <h3 className="mb-1 text-sm font-semibold text-ink">Model-cited evidence</h3>
        <p className="mb-3 text-xs leading-5 text-muted">Records explicitly named in the investigator proposal.</p>
      </div>
      {citedEvidence.length ? (
        <EvidenceList evidence={citedEvidence} />
      ) : (
        <div className="border border-line bg-surface p-5 text-sm leading-6 text-muted">
          No supporting evidence was cited. RemitProof cannot authorize an autonomous resolution.
        </div>
      )}

      {auditRecords.length > 0 && (
        <div className="mt-8">
          <h3 className="mb-1 text-sm font-semibold text-ink">Allocation and audit context</h3>
          <p className="mb-3 text-xs leading-5 text-muted">Related records retained for inspection. These were not cited by the model.</p>
          <EvidenceList evidence={auditRecords} />
        </div>
      )}
    </section>
  );
}
