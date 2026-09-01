import type { BenchmarkData, ComparisonMetrics } from "@/lib/types";

interface Column {
  key: "baseline" | "llm_only" | "remitproof";
  label: string;
  supporting: string;
  metrics: ComparisonMetrics;
}

export function ComparisonTable({ benchmark }: { benchmark: BenchmarkData }) {
  const columns: Column[] = [
    {
      key: "baseline",
      label: "Baseline",
      supporting: "Deterministic rules",
      metrics: benchmark.comparison.baseline,
    },
    {
      key: "llm_only",
      label: "Model only",
      supporting: "Proposal trusted directly",
      metrics: benchmark.comparison.llm_only,
    },
    {
      key: "remitproof",
      label: "RemitProof",
      supporting: "Model plus verifier",
      metrics: benchmark.comparison.remitproof,
    },
  ];
  const rows: Array<{ label: string; key: keyof ComparisonMetrics; critical?: boolean }> = [
    { label: "Resolved", key: "resolved" },
    { label: "Correct resolutions", key: "correct_resolutions" },
    { label: "Wrong auto-resolutions", key: "wrong_auto_resolutions", critical: true },
    { label: "Correct abstentions", key: "correct_abstentions" },
    { label: "False escalations", key: "false_escalations" },
  ];

  return (
    <div className="table-scroll border border-line">
      <table className="w-full min-w-[700px] border-collapse text-sm">
        <caption className="sr-only">Baseline, model-only, and RemitProof benchmark comparison</caption>
        <thead>
          <tr className="border-b border-line bg-surface">
            <th className="w-[34%] px-5 py-4 text-left text-xs font-semibold text-muted" scope="col">
              Unresolved exceptions
            </th>
            {columns.map((column) => (
              <th
                key={column.key}
                className={column.key === "remitproof" ? "bg-primary-soft px-5 py-4 text-left" : "px-5 py-4 text-left"}
                scope="col"
              >
                <span className="block font-semibold text-ink">{column.label}</span>
                <span className="mt-0.5 block text-xs font-normal text-muted">{column.supporting}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row) => (
            <tr key={row.key}>
              <th className="px-5 py-3.5 text-left font-medium text-muted" scope="row">{row.label}</th>
              {columns.map((column) => {
                const value = column.metrics[row.key];
                const className = row.critical
                  ? value === 0
                    ? "text-primary-dark"
                    : "text-danger"
                  : "text-ink";
                return (
                  <td
                    key={column.key}
                    className={`numeric px-5 py-3.5 text-lg font-semibold ${className} ${
                      column.key === "remitproof" ? "bg-primary-soft/55" : ""
                    }`}
                  >
                    {value}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
