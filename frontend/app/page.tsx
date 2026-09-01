import { Activity, CheckCircle2, Gauge, ListFilter, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { AppFooter } from "@/components/AppFooter";
import { AppHeader } from "@/components/AppHeader";
import { ComparisonTable } from "@/components/ComparisonTable";
import { ExceptionTable } from "@/components/ExceptionTable";
import { PipelineFlow } from "@/components/PipelineFlow";
import { formatPercent } from "@/lib/format";
import { getBenchmark, getDashboard } from "@/lib/api";

export const dynamic = "force-dynamic";

function timingPresentation(
  evaluationMode: string,
  cache: { status: string; model_inference_included: boolean | null },
) {
  const mode = evaluationMode.toLowerCase();
  const status = cache.status.toLowerCase();
  const cached = mode.includes("cached") || status.includes("cached") || cache.model_inference_included === false;

  if (cached) {
    return {
      throughput: "Verifier-only throughput",
      latency: "Verifier-only decision latency",
      note: "Cached proposals were replayed; model inference time is excluded.",
    };
  }
  if (cache.model_inference_included === true) {
    return {
      throughput: "End-to-end throughput",
      latency: "End-to-end decision latency",
      note: "This run explicitly includes model inference time.",
    };
  }
  return {
    throughput: "Recorded processing throughput",
    latency: "Recorded decision latency",
    note: "Timing scope was not recorded; model inference inclusion is unknown.",
  };
}

export default async function DashboardPage() {
  const [dashboard, benchmark] = await Promise.all([getDashboard(), getBenchmark()]);
  const autoResolutions = dashboard.matched_normally + dashboard.resolved_by_remitproof;
  const comparisonRecordCount = benchmark.comparison_record_count ?? benchmark.exceptions;
  const timing = timingPresentation(dashboard.evaluation_mode, dashboard.cache);

  return (
    <div className="min-h-screen bg-canvas">
      <AppHeader />
      <main>
        <section className="mx-auto max-w-[1440px] px-4 py-10 sm:px-6 sm:py-14">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)] lg:items-end">
            <div>
              <p className="mb-4 flex items-center gap-2 text-sm font-semibold text-primary">
                <Activity className="size-4" aria-hidden="true" />
                Cross-border receivables control
              </p>
              <h1 className="max-w-[820px] text-[2.35rem] font-semibold leading-[1.08] tracking-[-0.04em] text-ink sm:text-[3.25rem]">
                Investigate the receipts normal reconciliation could not explain.
              </h1>
              <p className="mt-5 max-w-[68ch] text-base leading-7 text-muted sm:text-lg">
                AI proposes an allocation. Deterministic code verifies the money and record state. Evidence must make the result unique, or RemitProof sends it to human review.
              </p>
            </div>
            <div className="border-t border-line pt-6 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-[10px] bg-primary-soft text-primary-dark">
                  <ShieldCheck className="size-5" aria-hidden="true" />
                </span>
                <div>
                  <h2 className="text-sm font-semibold text-ink">Proof-carrying resolution</h2>
                  <p className="mt-1 text-sm leading-6 text-muted">
                    Financial validity + entity support + evidence support + no unresolved alternative.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <PipelineFlow
          total={dashboard.total_receipts}
          matched={dashboard.matched_normally}
          exceptions={dashboard.exceptions}
          resolved={dashboard.resolved_by_remitproof}
          review={dashboard.human_review}
        />

        <section className="mx-auto max-w-[1440px] px-4 py-12 sm:px-6 sm:py-16" aria-labelledby="safety-title">
          <div className="grid overflow-hidden border border-primary/30 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
            <div className="bg-primary-dark px-6 py-8 text-white sm:px-9 sm:py-10">
              <div className="flex items-center gap-2 text-sm font-semibold text-white/75">
                <CheckCircle2 className="size-4" aria-hidden="true" />
                Primary safety metric
              </div>
              <div className="mt-7 flex flex-wrap items-end gap-x-5 gap-y-2">
                <div className="numeric text-6xl font-semibold tracking-[-0.04em] sm:text-7xl">
                  {formatPercent(dashboard.incorrect_auto_resolution_rate, 1)}
                </div>
                <div className="pb-2 text-base font-medium text-white/80">incorrect auto-resolution</div>
              </div>
              <p id="safety-title" className="mt-5 max-w-[62ch] text-sm leading-6 text-white/75">
                Zero wrong financial actions across {autoResolutions} automated decisions. Human escalation is retained whenever proof is incomplete.
              </p>
            </div>
            <dl className="divide-y divide-line bg-canvas">
              <div className="grid gap-1 px-6 py-5 sm:flex sm:items-center sm:justify-between sm:gap-4 sm:px-8">
                <dt className="flex items-center gap-2 text-sm font-medium text-muted">
                  <Gauge className="size-4 text-primary" aria-hidden="true" />
                  {timing.throughput}
                </dt>
                <dd className="numeric break-words text-lg font-semibold text-ink sm:text-right">{dashboard.throughput_per_minute} records/min</dd>
              </div>
              <div className="grid gap-1 px-6 py-5 sm:flex sm:items-center sm:justify-between sm:gap-4 sm:px-8">
                <dt className="text-sm font-medium text-muted">{timing.latency}</dt>
                <dd className="numeric text-lg font-semibold text-ink">{dashboard.mean_latency_ms} ms</dd>
              </div>
              <div className="grid gap-1 px-6 py-5 sm:flex sm:items-center sm:justify-between sm:gap-4 sm:px-8">
                <dt className="text-sm font-medium text-muted">Correct abstention</dt>
                <dd className="numeric text-lg font-semibold text-primary-dark">
                  {formatPercent(benchmark.correct_abstention_rate, 0)}
                </dd>
              </div>
              <div className="grid gap-1 px-6 py-5 sm:flex sm:items-center sm:justify-between sm:gap-4 sm:px-8">
                <dt className="text-sm font-medium text-muted">Arithmetic correctness</dt>
                <dd className="numeric text-lg font-semibold text-primary-dark">
                  {formatPercent(benchmark.arithmetic_correctness, 0)}
                </dd>
              </div>
              <div className="px-6 py-4 sm:px-8">
                <dt className="sr-only">Timing disclosure</dt>
                <dd className="text-xs leading-5 text-muted">{timing.note}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section className="mx-auto max-w-[1440px] px-4 pb-14 sm:px-6 sm:pb-18" aria-labelledby="comparison-title">
          <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 id="comparison-title" className="text-2xl font-semibold tracking-[-0.025em] text-ink">
                Plausible is not the same as justified.
              </h2>
              <p className="mt-2 max-w-[68ch] text-sm leading-6 text-muted">
                The model finds semantic explanations, but it also proposes actions on ambiguous and unsupported cases. The verifier keeps the semantic wins and blocks unsafe postings.
              </p>
            </div>
            <div className="text-sm text-muted">
              <span className="numeric font-semibold text-ink">{comparisonRecordCount}</span>{" "}
              {benchmark.comparison_scope}
            </div>
          </div>
          <ComparisonTable benchmark={benchmark} />
        </section>

        <section className="mx-auto max-w-[1440px] px-4 pb-8 sm:px-6" aria-labelledby="queue-title">
          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 id="queue-title" className="text-2xl font-semibold tracking-[-0.025em] text-ink">
                Recent exception decisions
              </h2>
              <p className="mt-2 text-sm text-muted">Open a case to inspect its evidence, arithmetic, and alternatives.</p>
            </div>
            <Link className="inline-flex items-center gap-2 self-start rounded-md px-3 py-2 text-sm font-semibold text-primary hover:bg-primary-soft sm:self-auto" href="/exceptions">
              View all {dashboard.exceptions}
              <ListFilter className="size-4" aria-hidden="true" />
            </Link>
          </div>
          <ExceptionTable exceptions={dashboard.recent_exceptions} caption="Recent unresolved-payment investigations" />
        </section>
      </main>
      <AppFooter />
    </div>
  );
}
