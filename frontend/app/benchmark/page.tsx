import { ArrowLeft, ArrowRight, FlaskConical, ShieldAlert, ShieldCheck, Undo2 } from "lucide-react";
import Link from "next/link";
import { AppFooter } from "@/components/AppFooter";
import { AppHeader } from "@/components/AppHeader";
import { BenchmarkCaseExplorer } from "@/components/BenchmarkCaseExplorer";
import { SafetyFrontier } from "@/components/SafetyFrontier";
import { getConsistentBenchmarkPublication } from "@/lib/api";
import { describeBenchmarkRun } from "@/lib/benchmark-provenance";
import { explainReason, formatMoney, formatPercent, titleCase } from "@/lib/format";
import type { BenchmarkCaseRow } from "@/lib/types";

export const dynamic = "force-dynamic";

const METRIC_DEFINITIONS: Array<{ key: string; label: string; definition: string }> = [
  {
    key: "incorrect_auto_resolution_rate",
    label: "Incorrect auto-resolution rate",
    definition: "Wrong automatic resolutions ÷ all automatic resolutions.",
  },
  {
    key: "correct_abstention_rate",
    label: "Correct abstention rate",
    definition: "Ambiguous or unsafe cases correctly sent to review ÷ all ambiguous or unsafe cases.",
  },
  {
    key: "resolution_accuracy",
    label: "Safe exception resolution rate",
    definition: "Correctly resolved hard exceptions ÷ resolvable hard exceptions.",
  },
  {
    key: "false_escalation_rate",
    label: "False escalation rate",
    definition: "Resolvable exceptions unnecessarily sent to review ÷ all resolvable exceptions.",
  },
  {
    key: "arithmetic_correctness",
    label: "Arithmetic correctness",
    definition: "Decisions whose recomputed Decimal totals match ÷ all decisions.",
  },
  {
    key: "alternative_detection_accuracy",
    label: "Alternative detection accuracy",
    definition: "Exceptions where the competing-allocation search matched ground truth ÷ all exceptions.",
  },
  {
    key: "contradiction_detection_accuracy",
    label: "Contradiction detection accuracy",
    definition: "Exceptions where contradiction status matched ground truth ÷ all exceptions.",
  },
  {
    key: "evidence_precision",
    label: "Evidence precision",
    definition: "Relevant cited records ÷ all records cited by accepted proposals.",
  },
];

export default async function BenchmarkPage() {
  const { benchmark, caseData } = await getConsistentBenchmarkPublication();
  const comparison = benchmark.comparison;
  const unsafe = caseData.cases.filter((row) => row.wrong_auto_resolution);
  const prevented = caseData.cases.filter(
    (row) => row.llm_only_wrong_resolution && !row.wrong_auto_resolution,
  );
  const recovered = caseData.cases.filter((row) => row.recovered_from_baseline);
  const escalated = caseData.cases.filter((row) => row.false_escalation);
  const benchmarkRun = describeBenchmarkRun(benchmark);

  return (
    <div className="case-site min-h-screen bg-canvas">
      <AppHeader benchmark={benchmark} />
      <main className="mx-auto min-w-0 max-w-[1440px] px-4 py-8 sm:px-6 sm:py-10">
        <nav aria-label="Breadcrumb">
          <Link className="case-back-link inline-flex items-center gap-2 rounded-md py-1 text-sm font-semibold text-muted hover:text-primary" href="/">
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to dashboard
          </Link>
        </nav>

        <header className="case-page-heading mt-7 border-b border-line pb-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-[10px] bg-primary-soft text-primary-dark">
                <FlaskConical className="size-5" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <h1 className="text-3xl font-semibold tracking-[-0.035em] text-ink sm:text-4xl">Benchmark</h1>
                <p className="mt-2 max-w-[72ch] text-sm leading-6 text-muted">
                  Every number on this page is read from the committed, hash-verified result publication. Nothing is
                  entered by hand.
                </p>
              </div>
            </div>
            <span className="rounded-full border border-warning/40 bg-warning-soft px-3 py-1.5 text-xs font-semibold text-ink">
              {benchmarkRun.badgeLabel}
            </span>
          </div>
          <dl className="mt-6 grid gap-x-8 gap-y-3 text-xs sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <dt className="font-semibold text-muted">Generation</dt>
              <dd className="numeric mt-0.5 break-all text-ink">{benchmark.evaluation_generation_id.slice(0, 16)}…</dd>
            </div>
            <div>
              <dt className="font-semibold text-muted">Run mode</dt>
              <dd className="mt-0.5 text-ink">{benchmark.evaluation_mode}</dd>
            </div>
            <div>
              <dt className="font-semibold text-muted">Model</dt>
              <dd className="numeric mt-0.5 text-ink">{benchmark.model}</dd>
            </div>
            <div>
              <dt className="font-semibold text-muted">Corpus</dt>
              <dd className="mt-0.5 text-ink">{benchmark.partition_label}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="font-semibold text-muted">Timing scope</dt>
              <dd className="mt-0.5 text-ink">{benchmark.timing_scope}</dd>
            </div>
          </dl>
          <p className="mt-4 max-w-[80ch] rounded-[10px] bg-surface px-4 py-3 text-xs leading-5 text-muted">
            {benchmarkRun.description}
          </p>
          <details className="mt-4 rounded-[10px] border border-line bg-surface">
            <summary className="cursor-pointer px-4 py-3 text-xs font-semibold text-ink hover:bg-surface-raised">
              Result provenance and cache metadata
            </summary>
            <dl className="grid gap-x-8 gap-y-3 border-t border-line px-4 py-4 text-xs sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="font-semibold text-muted">Evaluator</dt>
                <dd className="mt-0.5 text-ink">{benchmark.provenance.evaluator_version}</dd>
              </div>
              <div>
                <dt className="font-semibold text-muted">Cache</dt>
                <dd className="mt-0.5 text-ink">
                  {benchmark.cache.status}: {benchmark.cache.hits ?? "Not recorded"} hits, {benchmark.cache.misses ?? "Not recorded"} misses
                </dd>
              </div>
              <div>
                <dt className="font-semibold text-muted">Live model calls</dt>
                <dd className="numeric mt-0.5 text-ink">{benchmark.provenance.live_model_calls}</dd>
              </div>
              <div>
                <dt className="font-semibold text-muted">Proposal identity verified</dt>
                <dd className="mt-0.5 text-ink">
                  {benchmark.provenance.proposal_source_identity_verified ? "Yes" : "No"}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="font-semibold text-muted">Dataset SHA-256</dt>
                <dd className="numeric mt-0.5 break-all text-ink" title={benchmark.provenance.dataset_sha256}>
                  {benchmark.provenance.dataset_sha256}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="font-semibold text-muted">Proposal cache SHA-256</dt>
                <dd className="numeric mt-0.5 break-all text-ink" title={benchmark.provenance.proposal_cache_sha256}>
                  {benchmark.provenance.proposal_cache_sha256}
                </dd>
              </div>
            </dl>
          </details>
        </header>

        <section className="mt-10" aria-labelledby="funnel-title">
          <h2 id="funnel-title" className="text-xl font-semibold tracking-[-0.02em] text-ink">
            Where RemitProof operates
          </h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <FunnelStep value={benchmark.total_receipts} label="Synthetic receipts" detail="Full evaluation corpus" />
            <FunnelStep
              value={benchmark.matched_normally}
              label="Matched by deterministic rules"
              detail="No AI involvement; resolved by the conventional matcher"
            />
            <FunnelStep
              value={benchmark.exceptions}
              label="Hard exceptions"
              detail="Unresolved by structured matching; RemitProof starts here"
            />
            <div className="rounded-[12px] border border-line bg-surface p-4">
              <p className="text-xs font-semibold text-muted">RemitProof outcomes</p>
              <dl className="mt-2 space-y-1.5 text-sm">
                <FunnelOutcome label="Safely resolved" value={comparison.remitproof.correct_resolutions} tone="good" />
                <FunnelOutcome label="Correctly abstained" value={comparison.remitproof.correct_abstentions} tone="good" />
                <FunnelOutcome label="False escalations" value={comparison.remitproof.false_escalations} tone="warn" />
                <FunnelOutcome label="Wrong auto-resolutions" value={comparison.remitproof.wrong_auto_resolutions} tone="zero" />
              </dl>
            </div>
          </div>
        </section>

        <section className="mt-12" aria-labelledby="comparison-title">
          <h2 id="comparison-title" className="text-xl font-semibold tracking-[-0.02em] text-ink">
            Three systems, same {benchmark.comparison_record_count} hard exceptions
          </h2>
          <p className="mt-2 max-w-[80ch] text-sm leading-6 text-muted">
            The middle column is a verifier ablation: RemitProof&apos;s own model proposals treated as final decisions
            with every verification layer removed. It is not an independently designed standalone LLM system.
          </p>
          <div className="table-scroll mt-5 rounded-[12px] border border-line">
            <table className="w-full min-w-[680px] border-collapse text-sm">
              <thead className="bg-surface">
                <tr className="border-b border-line text-left text-xs font-semibold text-muted">
                  <th scope="col" className="px-5 py-3">System</th>
                  <th scope="col" className="px-5 py-3 text-right">Correct resolutions</th>
                  <th scope="col" className="px-5 py-3 text-right">Wrong auto-resolutions</th>
                  <th scope="col" className="px-5 py-3 text-right">Correct abstentions</th>
                  <th scope="col" className="px-5 py-3 text-right">False escalations</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                <ComparisonRow name="Baseline rules only" metrics={comparison.baseline} />
                <ComparisonRow name="Proposal only (verifier ablation)" metrics={comparison.llm_only} />
                <ComparisonRow name="RemitProof" metrics={comparison.remitproof} highlight />
              </tbody>
            </table>
          </div>
          <p className="mt-4 max-w-[80ch] text-sm leading-6 text-ink">
            Rules alone resolved {comparison.baseline.resolved} cases. Unverified proposals automatically resolved{" "}
            {comparison.llm_only.resolved} of {benchmark.comparison_record_count}: {comparison.llm_only.correct_resolutions}{" "}
            correct and {comparison.llm_only.wrong_auto_resolutions} wrong. RemitProof safely resolved{" "}
            {comparison.remitproof.correct_resolutions} and authorized {comparison.remitproof.wrong_auto_resolutions}{" "}
            wrong automatic resolutions — the cost is{" "}
            {comparison.remitproof.false_escalations} unnecessary escalations.
          </p>
        </section>

        <SafetyFrontier
          comparisonRecordCount={benchmark.comparison_record_count}
          comparison={benchmark.comparison}
        />

        <BenchmarkCaseExplorer cases={caseData.cases} />

        <CaseListSection
          id="unsafe-remitproof"
          icon={<ShieldAlert className="size-5" aria-hidden="true" />}
          iconClass="bg-danger-soft text-danger"
          title="RemitProof wrong auto-resolutions"
          intro={`${unsafe.length} cases were automatically resolved incorrectly by RemitProof. These are safety failures, not prevented decisions.`}
          cases={unsafe}
          rightLabel="RemitProof outcome"
          right={() => "Wrong automatic resolution"}
        />

        <CaseListSection
          id="prevented"
          icon={<ShieldAlert className="size-5" aria-hidden="true" />}
          iconClass="bg-danger-soft text-danger"
          title="Unsupported resolutions not authorized"
          intro={`${prevented.length} incorrect auto-resolutions observed in the forced-proposal ablation were not authorized by RemitProof. Each one is a plausible, often perfectly balanced allocation that the evidence does not support.`}
          cases={prevented}
          rightLabel="Ablation would resolve — RemitProof decision"
          right={(row) => `${titleCase(row.remitproof_decision)}`}
        />

        <CaseListSection
          id="recovered"
          icon={<ShieldCheck className="size-5" aria-hidden="true" />}
          iconClass="bg-primary-soft text-primary-dark"
          title="Exceptions safely recovered"
          intro={`${recovered.length} hard exceptions that deterministic rules could not resolve were automated by RemitProof, each with a passing financial proof and evidence that uniquely eliminated the competing allocations.`}
          cases={recovered}
          rightLabel="Baseline — RemitProof decision"
          right={() => "Resolved with proof"}
        />

        <CaseListSection
          id="failures"
          icon={<Undo2 className="size-5" aria-hidden="true" />}
          iconClass="bg-warning-soft text-warning"
          title="Where RemitProof still fails"
          intro={`${escalated.length} resolvable exceptions were escalated unnecessarily. RemitProof currently prioritizes false negatives over false positives: when evidence falls short of its sufficiency bar, it refuses to act even when a human would resolve confidently.`}
          cases={escalated}
          rightLabel="Escalation reason"
          right={(row) => explainReason(row.reason)}
        />

        <section className="mt-12" aria-labelledby="class-title">
          <h2 id="class-title" className="text-xl font-semibold tracking-[-0.02em] text-ink">
            Results by exception class
          </h2>
          <p className="mt-2 max-w-[80ch] text-sm leading-6 text-muted">
            The corpus spreads outcomes across distinct semantic failure modes rather than one hand-crafted hero case.
          </p>
          <div className="table-scroll mt-5 rounded-[12px] border border-line">
            <table className="w-full min-w-[720px] border-collapse text-sm">
              <thead className="bg-surface">
                <tr className="border-b border-line text-left text-xs font-semibold text-muted">
                  <th scope="col" className="px-5 py-3">Class</th>
                  <th scope="col" className="px-5 py-3 text-right">Records</th>
                  <th scope="col" className="px-5 py-3 text-right">Correctly resolved</th>
                  <th scope="col" className="px-5 py-3 text-right">Human review</th>
                  <th scope="col" className="px-5 py-3 text-right">Wrong auto-resolutions</th>
                  <th scope="col" className="px-5 py-3 text-right">False escalations</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {caseData.by_class.map((row) => (
                  <tr key={row.exception_class} className={row.exception_class === "conventional_exact_reference" ? "text-muted" : ""}>
                    <th scope="row" className="px-5 py-3 text-left font-semibold">
                      {titleCase(row.exception_class)}
                      {row.exception_class === "conventional_exact_reference" && (
                        <span className="ml-2 text-xs font-normal">(deterministic path, no AI)</span>
                      )}
                    </th>
                    <td className="numeric px-5 py-3 text-right">{row.records}</td>
                    <td className="numeric px-5 py-3 text-right">{row.correct_resolutions}</td>
                    <td className="numeric px-5 py-3 text-right">{row.human_review}</td>
                    <td className="numeric px-5 py-3 text-right">{row.wrong_auto_resolutions}</td>
                    <td className="numeric px-5 py-3 text-right">{row.false_escalations}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-12" aria-labelledby="metrics-title">
          <h2 id="metrics-title" className="text-xl font-semibold tracking-[-0.02em] text-ink">
            Headline metrics and their denominators
          </h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {METRIC_DEFINITIONS.map((metric) => {
              const value = benchmark[metric.key as keyof typeof benchmark];
              return (
                <div key={metric.key} className="rounded-[12px] border border-line bg-surface p-4">
                  <p className="text-xs font-semibold text-muted">{metric.label}</p>
                  <p className="numeric mt-1 text-2xl font-semibold text-ink">
                    {typeof value === "number" ? formatPercent(value, 1) : "Not measured"}
                  </p>
                  <p className="mt-2 text-xs leading-5 text-muted">{metric.definition}</p>
                </div>
              );
            })}
          </div>
          <p className="mt-4 text-xs leading-5 text-muted">
            Throughput ({benchmark.throughput_per_minute.toLocaleString("en-US")} decisions/min, mean{" "}
            {benchmark.mean_latency_ms} ms) {benchmarkRun.timingDescription}
          </p>
        </section>

        <section className="mt-12 rounded-[12px] border border-line bg-surface p-6" aria-labelledby="limits-title">
          <h2 id="limits-title" className="text-xl font-semibold tracking-[-0.02em] text-ink">
            System limits
          </h2>
          <ul className="mt-4 grid list-disc gap-2 pl-5 text-sm leading-6 text-muted sm:grid-cols-2">
            <li>All transactions, invoices, credits, and emails are synthetic records modeled on the target workflow.</li>
            <li>No live Razorpay, bank, Gmail, ERP, or settlement integration; the API is read-only.</li>
            <li>No accounting write-back, production authentication, or FX engine.</li>
            <li>{benchmarkRun.systemLimitNote}</li>
            <li>The corpus is not an independent held-out set; the benchmark partition shares generation machinery with development data.</li>
            <li>False escalations above are real conservative misses, not presentation choices.</li>
          </ul>
        </section>
      </main>
      <AppFooter />
    </div>
  );
}

function FunnelStep({ value, label, detail }: { value: number; label: string; detail: string }) {
  return (
    <div className="rounded-[12px] border border-line bg-surface p-4">
      <p className="numeric text-3xl font-semibold tracking-[-0.02em] text-ink">{value}</p>
      <p className="mt-1 text-sm font-semibold text-ink">{label}</p>
      <p className="mt-1 text-xs leading-5 text-muted">{detail}</p>
    </div>
  );
}

function FunnelOutcome({ label, value, tone }: { label: string; value: number; tone: "good" | "warn" | "zero" }) {
  const valueClass = tone === "good" ? "text-primary-dark" : tone === "warn" ? "text-warning" : "text-ink";
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-muted">{label}</dt>
      <dd className={`numeric font-semibold ${valueClass}`}>{value}</dd>
    </div>
  );
}

function ComparisonRow({
  name,
  metrics,
  highlight = false,
}: {
  name: string;
  metrics: { correct_resolutions: number; wrong_auto_resolutions: number; correct_abstentions: number; false_escalations: number };
  highlight?: boolean;
}) {
  return (
    <tr className={highlight ? "bg-primary-soft/40" : ""}>
      <th scope="row" className="px-5 py-3.5 text-left font-semibold text-ink">{name}</th>
      <td className="numeric px-5 py-3.5 text-right">{metrics.correct_resolutions}</td>
      <td className={`numeric px-5 py-3.5 text-right font-semibold ${metrics.wrong_auto_resolutions > 0 ? "text-danger" : "text-primary-dark"}`}>
        {metrics.wrong_auto_resolutions}
      </td>
      <td className="numeric px-5 py-3.5 text-right">{metrics.correct_abstentions}</td>
      <td className="numeric px-5 py-3.5 text-right">{metrics.false_escalations}</td>
    </tr>
  );
}

function CaseListSection({
  id,
  icon,
  iconClass,
  title,
  intro,
  cases,
  rightLabel,
  right,
}: {
  id: string;
  icon: React.ReactNode;
  iconClass: string;
  title: string;
  intro: string;
  cases: BenchmarkCaseRow[];
  rightLabel: string;
  right: (row: BenchmarkCaseRow) => string;
}) {
  if (cases.length === 0) return null;
  return (
    <section className="mt-12" aria-labelledby={`${id}-title`}>
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 grid size-9 shrink-0 place-items-center rounded-[10px] ${iconClass}`}>{icon}</span>
        <div className="min-w-0">
          <h2 id={`${id}-title`} className="text-xl font-semibold tracking-[-0.02em] text-ink">{title}</h2>
          <p className="mt-2 max-w-[80ch] text-sm leading-6 text-muted">{intro}</p>
        </div>
      </div>
      <ul className="mt-5 divide-y divide-line rounded-[12px] border border-line">
        {cases.map((row) => (
          <li key={row.payment_id}>
            <Link
              href={`/exceptions/${encodeURIComponent(row.payment_id)}`}
              className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1.5 px-5 py-3.5 text-sm hover:bg-surface"
            >
              <span className="flex min-w-0 flex-wrap items-baseline gap-x-4 gap-y-1">
                <span className="numeric font-semibold text-ink">{row.payment_id}</span>
                <span className="text-muted">{titleCase(row.exception_class)}</span>
                <span className="numeric text-muted">{formatMoney(row.amount, row.currency)}</span>
              </span>
              <span className="flex items-center gap-2 text-xs text-muted">
                <span className="max-w-[48ch]">
                  <span className="sr-only">{rightLabel}: </span>
                  {right(row)}
                </span>
                <ArrowRight className="size-3.5 shrink-0" aria-hidden="true" />
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
