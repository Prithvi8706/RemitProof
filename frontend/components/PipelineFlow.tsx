import { ArrowDown, ArrowRight, CornerDownRight } from "lucide-react";

interface PipelineFlowProps {
  total: number;
  matched: number;
  exceptions: number;
  resolved: number;
  review: number;
}

function FlowNode({ value, label, emphasis = false }: { value: number; label: string; emphasis?: boolean }) {
  return (
    <div className={`min-w-0 ${emphasis ? "text-primary-dark" : "text-ink"}`}>
      <div className="numeric text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">{value}</div>
      <div className="mt-1 break-words text-sm font-medium leading-5 text-muted">{label}</div>
    </div>
  );
}

export function PipelineFlow({ total, matched, exceptions, resolved, review }: PipelineFlowProps) {
  return (
    <section aria-labelledby="receipt-flow-title" className="border-y border-line bg-surface">
      <div className="mx-auto max-w-[1440px] px-4 py-7 sm:px-6 sm:py-9">
        <h2 id="receipt-flow-title" className="sr-only">
          Receipt processing flow
        </h2>
        <div className="flex min-w-0 flex-col gap-6 lg:flex-row lg:items-center">
          <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <FlowNode value={total} label="Incoming receipts" />
            <ArrowDown className="size-4 text-line-strong sm:hidden" aria-hidden="true" />
            <ArrowRight className="hidden size-5 shrink-0 text-line-strong sm:block" aria-hidden="true" />
            <FlowNode value={matched} label="Matched normally" />
            <ArrowDown className="size-4 text-line-strong sm:hidden" aria-hidden="true" />
            <ArrowRight className="hidden size-5 shrink-0 text-line-strong sm:block" aria-hidden="true" />
            <FlowNode value={exceptions} label="Exceptions investigated" emphasis />
          </div>
          <div className="hidden h-14 w-px bg-line lg:block" aria-hidden="true" />
          <div className="flex min-w-0 items-start gap-3 border-t border-line pt-5 sm:items-center lg:min-w-[330px] lg:border-0 lg:pt-0">
            <CornerDownRight className="mt-1 size-5 shrink-0 text-primary sm:mt-0" aria-hidden="true" />
            <div className="grid min-w-0 flex-1 grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5">
              <FlowNode value={resolved} label="Safely resolved" emphasis />
              <FlowNode value={review} label="Human review" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
