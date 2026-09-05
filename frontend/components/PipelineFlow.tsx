import { ArrowDown, ArrowRight, ShieldCheck } from "lucide-react";

interface PipelineFlowProps {
  total: number;
  matched: number;
  exceptions: number;
  resolved: number;
  review: number;
}

function FlowNode({
  value,
  label,
  detail,
  emphasis = false,
}: {
  value: number;
  label: string;
  detail?: string;
  emphasis?: boolean;
}) {
  return (
    <div className="min-w-0">
      <div className={`numeric text-3xl font-semibold tracking-[-0.035em] sm:text-4xl ${emphasis ? "text-primary-dark" : "text-ink"}`}>
        {value}
      </div>
      <div className="mt-1 text-sm font-semibold leading-5 text-ink">{label}</div>
      {detail && <div className="mt-1 max-w-[24ch] text-xs leading-5 text-muted">{detail}</div>}
    </div>
  );
}

function Connector() {
  return (
    <>
      <ArrowDown className="size-4 text-line-strong sm:hidden" aria-hidden="true" />
      <ArrowRight className="hidden size-5 shrink-0 text-line-strong sm:block" aria-hidden="true" />
    </>
  );
}

export function PipelineFlow({ total, matched, exceptions, resolved, review }: PipelineFlowProps) {
  return (
    <section aria-labelledby="receipt-flow-title" className="border-y border-line bg-surface">
      <div className="mx-auto max-w-[1440px] px-4 py-8 sm:px-6 sm:py-10">
        <div className="mb-7">
          <h2 id="receipt-flow-title" className="text-lg font-semibold text-ink">
            Normal reconciliation first. RemitProof only sees unresolved cases.
          </h2>
          <p className="mt-1 max-w-[70ch] text-sm leading-6 text-muted">
            Structured references, amounts, customer mappings, currencies, and ordinary credits stay with the deterministic matcher.
          </p>
        </div>

        <div className="grid border border-line bg-canvas lg:grid-cols-[minmax(0,1fr)_210px_minmax(0,1fr)]">
          <div className="px-5 py-6 sm:px-7">
            <div className="mb-5 text-xs font-semibold text-muted">DETERMINISTIC RECONCILIATION</div>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <FlowNode value={total} label="Incoming receipts" />
              <Connector />
              <FlowNode value={matched} label="Resolved normally" detail="Structured financial signals were sufficient." />
            </div>
          </div>

          <div className="flex flex-col items-start justify-center border-y border-primary/25 bg-primary-soft px-5 py-5 lg:border-x lg:border-y-0">
            <div className="numeric text-3xl font-semibold tracking-[-0.035em] text-primary-dark">{exceptions}</div>
            <div className="mt-1 text-sm font-semibold text-ink">Unresolved exceptions</div>
            <div className="mt-3 flex items-center gap-2 text-xs font-semibold text-primary-dark">
              <ShieldCheck className="size-4" aria-hidden="true" />
              REMITPROOF STARTS
            </div>
          </div>

          <div className="px-5 py-6 sm:px-7">
            <div className="mb-5 text-xs font-semibold text-primary-dark">PROOF-GATED INVESTIGATION</div>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <FlowNode value={resolved} label="Justified resolutions" detail="One explanation was uniquely supported." emphasis />
              <Connector />
              <FlowNode value={review} label="Deliberate abstentions" detail="Conflict or missing evidence remained." />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
