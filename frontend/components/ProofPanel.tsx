import { Check, Minus, X } from "lucide-react";
import type { ExceptionDetail } from "@/lib/types";

interface CheckRow {
  label: string;
  description: string;
  passed: boolean | null;
}

function statusLabel(passed: boolean | null): "Passed" | "Failed" | "Not evaluated" {
  if (passed === null) return "Not evaluated";
  return passed ? "Passed" : "Failed";
}

function StatusIcon({ passed }: { passed: boolean | null }) {
  if (passed === null) {
    return (
      <span aria-hidden="true" className="grid size-6 place-items-center rounded-full bg-surface-raised text-muted">
        <Minus className="size-3.5" aria-hidden="true" />
      </span>
    );
  }
  if (passed) {
    return (
      <span aria-hidden="true" className="grid size-6 place-items-center rounded-full bg-primary-soft text-primary-dark">
        <Check className="size-3.5" strokeWidth={2.5} aria-hidden="true" />
      </span>
    );
  }
  return (
    <span aria-hidden="true" className="grid size-6 place-items-center rounded-full bg-danger-soft text-danger">
      <X className="size-3.5" strokeWidth={2.5} aria-hidden="true" />
    </span>
  );
}

export function ProofPanel({ detail }: { detail: ExceptionDetail }) {
  const proof = detail.proof;
  const sufficiency = detail.sufficiency;
  const rows: CheckRow[] = [
    {
      label: "Arithmetic",
      description: "Selected invoices minus valid credits equal the payment.",
      passed: proof?.financial_validity ?? null,
    },
    {
      label: "Record state",
      description: "Payment, invoices, and credits are eligible for allocation.",
      passed: proof?.state_validity ?? null,
    },
    {
      label: "Currency",
      description: "Payment, invoices, and credits use one supported currency.",
      passed: proof?.currency_validity ?? null,
    },
    {
      label: "Entity support",
      description: "The payer relationship is explicitly supported by a record.",
      passed: proof?.entity_support ?? null,
    },
    {
      label: "Credit support",
      description: "Every deduction has a valid, applicable credit note.",
      passed: proof?.credit_support ?? null,
    },
    {
      label: "No duplicate risk",
      description: "No selected record is already consumed or allocated.",
      passed: proof ? !proof.duplicate_risk : null,
    },
    {
      label: "No contradiction",
      description: "Remittance evidence and financial records agree.",
      passed: proof ? proof.contradictions.length === 0 : null,
    },
    {
      label: "Uniqueness",
      description: "Evidence eliminates every competing financial allocation.",
      passed: sufficiency
        ? !sufficiency.alternative_allocations_exist || sufficiency.evidence_disambiguates_alternatives
        : null,
    },
  ];

  return (
    <section aria-labelledby="proof-title">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div>
          <h2 id="proof-title" className="text-xl font-semibold tracking-[-0.02em] text-ink">Deterministic proof</h2>
          <p className="mt-1 text-sm text-muted">The model cannot override these checks.</p>
        </div>
        {sufficiency && (
          <span className="numeric text-xs font-semibold text-muted">
            {rows.filter((row) => row.passed).length}/{rows.length} passed
          </span>
        )}
      </div>
      <ul className="border-y border-line" aria-label="Deterministic proof checks">
        {rows.map((row) => (
          <li key={row.label} className="grid grid-cols-[24px_minmax(0,1fr)] gap-3 border-b border-line px-1 py-3.5 last:border-b-0">
            <StatusIcon passed={row.passed} />
            <div className="min-w-0">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <span className="text-sm font-semibold text-ink">{row.label}</span>
                <span className={`text-xs font-semibold ${
                  row.passed === null ? "text-muted" : row.passed ? "text-primary-dark" : "text-danger"
                }`}>
                  {statusLabel(row.passed)}
                </span>
              </div>
              <div className="mt-0.5 text-xs leading-5 text-muted">{row.description}</div>
            </div>
          </li>
        ))}
      </ul>
      {proof?.contradictions && proof.contradictions.length > 0 && (
        <div className="mt-4 border border-danger/25 bg-danger-soft p-4 text-sm leading-6 text-[oklch(0.38_0.12_28)]">
          {proof.contradictions.map((item) => <p key={item}>{item}</p>)}
        </div>
      )}
    </section>
  );
}
