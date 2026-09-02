import type { ComparisonMetrics } from "@/lib/types";

interface SafetyFrontierProps {
  comparisonRecordCount: number;
  comparison: {
    baseline: ComparisonMetrics;
    llm_only: ComparisonMetrics;
    remitproof: ComparisonMetrics;
  };
}

const systems = [
  { key: "baseline", label: "Baseline", tone: "muted" },
  { key: "llm_only", label: "Proposal only", tone: "danger" },
  { key: "remitproof", label: "RemitProof", tone: "primary" },
] as const;

export function SafetyFrontier({ comparisonRecordCount, comparison }: SafetyFrontierProps) {
  const points = systems.map((system) => {
    const metrics = comparison[system.key];
    return {
      ...system,
      resolved: metrics.resolved,
      wrong: metrics.wrong_auto_resolutions,
      automationRate: comparisonRecordCount > 0 ? metrics.resolved / comparisonRecordCount : 0,
      wrongActionRate:
        comparisonRecordCount > 0 ? metrics.wrong_auto_resolutions / comparisonRecordCount : 0,
    };
  });
  const maxWrongRate = Math.max(...points.map((point) => point.wrongActionRate), 0.01);

  return (
    <section className="mt-12" aria-labelledby="frontier-title">
      <h2 id="frontier-title" className="text-xl font-semibold tracking-[-0.02em] text-ink">
        The safety frontier
      </h2>
      <p className="mt-2 max-w-[78ch] text-sm leading-6 text-muted">
        Automation is useful only when the resulting action is justified. The chart uses all {comparisonRecordCount}{" "}
        hard exceptions as the denominator on both axes.
      </p>

      <div className="mt-5 grid gap-6 rounded-[12px] border border-line bg-surface p-5 lg:grid-cols-[minmax(0,1fr)_300px] lg:p-6">
        <div>
          <div
            className="relative h-[320px] border-b border-l border-line-strong"
            role="img"
            aria-label={points
              .map(
                (point) =>
                  `${point.label}: ${point.resolved} of ${comparisonRecordCount} exceptions automated, ${point.wrong} wrong automatic resolutions`,
              )
              .join(". ")}
          >
            <span className="absolute -left-1 top-0 -translate-x-full text-[11px] font-medium text-muted">
              More wrong actions
            </span>
            <span className="absolute -bottom-7 right-0 text-[11px] font-medium text-muted">
              More automation
            </span>
            <div className="absolute inset-0 grid grid-cols-4 grid-rows-4" aria-hidden="true">
              {Array.from({ length: 16 }, (_, index) => (
                <span key={index} className="border-r border-t border-line/60" />
              ))}
            </div>
            {points.map((point) => {
              const left = Math.min(96, Math.max(2, point.automationRate * 100));
              const bottom = Math.min(92, Math.max(3, (point.wrongActionRate / maxWrongRate) * 82));
              const pointClass =
                point.tone === "danger"
                  ? "border-danger bg-danger text-white"
                  : point.tone === "primary"
                    ? "border-primary bg-primary text-white"
                    : "border-line-strong bg-surface-raised text-ink";
              return (
                <div
                  key={point.key}
                  className="absolute z-[1] -translate-x-1/2 translate-y-1/2"
                  style={{ left: `${left}%`, bottom: `${bottom}%` }}
                  aria-hidden="true"
                >
                  <span className={`grid size-8 place-items-center rounded-full border-2 text-xs font-bold ${pointClass}`}>
                    {point.label.slice(0, 1)}
                  </span>
                  <span className="absolute left-1/2 top-10 w-max -translate-x-1/2 text-xs font-semibold text-ink">
                    {point.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="divide-y divide-line lg:border-l lg:border-line lg:pl-6">
          {points.map((point) => (
            <div key={point.key} className="py-3 first:pt-0 last:pb-0">
              <p className="text-sm font-semibold text-ink">{point.label}</p>
              <dl className="mt-2 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <dt className="text-muted">Automated</dt>
                  <dd className="numeric mt-0.5 font-semibold text-ink">
                    {point.resolved}/{comparisonRecordCount}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted">Wrong actions</dt>
                  <dd className={`numeric mt-0.5 font-semibold ${point.wrong > 0 ? "text-danger" : "text-primary-dark"}`}>
                    {point.wrong}/{comparisonRecordCount}
                  </dd>
                </div>
              </dl>
            </div>
          ))}
        </div>
      </div>
      <p className="mt-4 max-w-[78ch] text-sm leading-6 text-ink">
        RemitProof recovers useful automation from the baseline while refusing every wrong automatic resolution in
        this publication. Its current cost is conservative escalation, not hidden error.
      </p>
    </section>
  );
}
