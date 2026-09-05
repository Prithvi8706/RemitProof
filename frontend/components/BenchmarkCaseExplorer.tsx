"use client";

import { useMemo, useState } from "react";
import { ArrowRight, Search } from "lucide-react";
import Link from "next/link";
import { explainReason, formatMoney, titleCase } from "@/lib/format";
import type { BenchmarkCaseRow } from "@/lib/types";

type OutcomeFilter = "all" | "prevented" | "recovered" | "abstained" | "escalated";

const outcomeOptions: Array<{ value: OutcomeFilter; label: string }> = [
  { value: "prevented", label: "Unsupported blocked" },
  { value: "recovered", label: "Safely recovered" },
  { value: "abstained", label: "Correct abstentions" },
  { value: "escalated", label: "False escalations" },
  { value: "all", label: "All hard exceptions" },
];

function matchesOutcome(row: BenchmarkCaseRow, outcome: OutcomeFilter) {
  if (outcome === "prevented") return row.llm_only_wrong_resolution && !row.wrong_auto_resolution;
  if (outcome === "recovered") return row.recovered_from_baseline;
  if (outcome === "abstained") return row.correct_abstention;
  if (outcome === "escalated") return row.false_escalation;
  return true;
}

function countOutcome(cases: BenchmarkCaseRow[], outcome: OutcomeFilter) {
  return cases.filter((row) => matchesOutcome(row, outcome)).length;
}

export function BenchmarkCaseExplorer({ cases }: { cases: BenchmarkCaseRow[] }) {
  const [outcome, setOutcome] = useState<OutcomeFilter>("prevented");
  const [exceptionClass, setExceptionClass] = useState("all");
  const [query, setQuery] = useState("");
  const exceptionClasses = useMemo(
    () => Array.from(new Set(cases.map((row) => row.exception_class))).sort(),
    [cases],
  );
  const visibleCases = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    return cases.filter((row) => {
      const classMatches = exceptionClass === "all" || row.exception_class === exceptionClass;
      const queryMatches =
        normalizedQuery.length === 0 ||
        [row.payment_id, row.payer, row.exception_class]
          .join(" ")
          .toLocaleLowerCase()
          .includes(normalizedQuery);
      return matchesOutcome(row, outcome) && classMatches && queryMatches;
    });
  }, [cases, exceptionClass, outcome, query]);

  return (
    <section className="mt-12" aria-labelledby="case-explorer-title">
      <h2 id="case-explorer-title" className="text-xl font-semibold tracking-[-0.02em] text-ink">
        Inspect the measured outcomes
      </h2>
      <p className="mt-2 max-w-[80ch] text-sm leading-6 text-muted">
        Every row links to the stored proposal, deterministic proof, evidence matrix, alternatives, and final
        authorization decision.
      </p>

      <div className="mt-5 flex flex-wrap gap-2" role="group" aria-label="Filter benchmark cases by outcome">
        {outcomeOptions.map((option) => {
          const selected = outcome === option.value;
          const count = countOutcome(cases, option.value);
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={selected}
              onClick={() => setOutcome(option.value)}
              className={`rounded-full border px-3 py-2 text-xs font-semibold active:translate-y-px ${
                selected
                  ? "border-primary bg-primary text-white"
                  : "border-line bg-surface text-muted hover:border-line-strong hover:text-ink"
              }`}
            >
              {option.label} <span className="numeric ml-1 opacity-80">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(220px,0.34fr)]">
        <label className="relative block">
          <span className="sr-only">Search benchmark cases</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search payment, payer, or class"
            className="h-11 w-full rounded-[10px] border border-line bg-surface pl-10 pr-3 text-sm text-ink placeholder:text-muted focus:border-primary focus:outline-none"
          />
        </label>
        <label>
          <span className="sr-only">Filter by exception class</span>
          <select
            value={exceptionClass}
            onChange={(event) => setExceptionClass(event.target.value)}
            className="h-11 w-full rounded-[10px] border border-line bg-surface px-3 text-sm text-ink focus:border-primary focus:outline-none"
          >
            <option value="all">All exception classes</option>
            {exceptionClasses.map((value) => (
              <option key={value} value={value}>
                {titleCase(value)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-4 overflow-hidden rounded-[12px] border border-line">
        <div className="flex items-center justify-between gap-4 border-b border-line bg-surface px-4 py-3 text-xs text-muted sm:px-5">
          <span>
            Showing <strong className="numeric text-ink">{visibleCases.length}</strong> cases
          </span>
          <span className="hidden sm:inline">Baseline / proposal only / RemitProof</span>
        </div>
        {visibleCases.length > 0 ? (
          <ul className="divide-y divide-line">
            {visibleCases.map((row) => (
              <li key={row.payment_id}>
                <Link
                  href={`/exceptions/${encodeURIComponent(row.payment_id)}`}
                  className="group grid gap-4 px-4 py-4 hover:bg-surface sm:px-5 lg:grid-cols-[minmax(250px,0.8fr)_minmax(420px,1.2fr)_minmax(220px,0.7fr)_auto] lg:items-center"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <span className="numeric text-sm font-semibold text-ink">{row.payment_id}</span>
                      <span className="text-xs text-muted">{titleCase(row.exception_class)}</span>
                    </div>
                    <p className="mt-1 truncate text-xs text-muted">{row.payer}</p>
                  </div>

                  <dl className="grid grid-cols-3 gap-2 text-xs">
                    <DecisionCell label="Baseline" decision="Review" tone="neutral" />
                    <DecisionCell
                      label="Proposal only"
                      decision={row.llm_only_decision === "resolve" ? "Resolve" : "Abstain"}
                      tone={row.llm_only_wrong_resolution ? "danger" : "neutral"}
                      qualifier={row.llm_only_wrong_resolution ? "Wrong" : undefined}
                    />
                    <DecisionCell
                      label="RemitProof"
                      decision={row.remitproof_decision === "resolved" ? "Resolve" : "Review"}
                      tone={row.wrong_auto_resolution ? "danger" : row.remitproof_correct_resolution || row.correct_abstention ? "good" : "warning"}
                      qualifier={
                        row.remitproof_correct_resolution
                          ? "Supported"
                          : row.correct_abstention
                            ? "Correct control"
                            : row.false_escalation
                              ? "Conservative miss"
                              : undefined
                      }
                    />
                  </dl>

                  <div className="min-w-0 lg:text-right">
                    <p className="numeric text-sm font-semibold text-ink">
                      {formatMoney(row.amount, row.currency)}
                    </p>
                    <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted">{explainReason(row.reason)}</p>
                  </div>
                  <ArrowRight className="hidden size-4 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-primary lg:block" aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <div className="px-5 py-10 text-center">
            <p className="text-sm font-semibold text-ink">No cases match these filters</p>
            <p className="mt-1 text-xs text-muted">Change the outcome, exception class, or search text.</p>
          </div>
        )}
      </div>
    </section>
  );
}

function DecisionCell({
  label,
  decision,
  tone,
  qualifier,
}: {
  label: string;
  decision: string;
  tone: "neutral" | "good" | "warning" | "danger";
  qualifier?: string;
}) {
  const toneClass =
    tone === "danger"
      ? "text-danger"
      : tone === "good"
        ? "text-primary-dark"
        : tone === "warning"
          ? "text-warning"
          : "text-ink";
  return (
    <div className="min-w-0 rounded-[10px] bg-surface-raised px-2.5 py-2">
      <dt className="truncate text-[11px] text-muted">{label}</dt>
      <dd className={`mt-0.5 truncate font-semibold ${toneClass}`}>{decision}</dd>
      {qualifier && <dd className={`mt-0.5 truncate text-[10px] font-medium ${toneClass}`}>{qualifier}</dd>}
    </div>
  );
}
