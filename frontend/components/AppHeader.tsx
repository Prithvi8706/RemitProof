import { ShieldCheck } from "lucide-react";
import Link from "next/link";
import type { BenchmarkData } from "@/lib/types";
import { describeBenchmarkRun } from "@/lib/benchmark-provenance";

export function AppHeader({ benchmark }: { benchmark?: BenchmarkData } = {}) {
  const benchmarkRun = benchmark ? describeBenchmarkRun(benchmark) : null;

  return (
    <header className="case-header border-b border-line text-ink">
      <div className="mx-auto flex min-h-16 max-w-[1440px] flex-wrap items-center justify-between gap-3 px-4 py-2 sm:gap-6 sm:px-6">
        <Link
          href="/"
          className="flex shrink-0 items-center gap-3 whitespace-nowrap rounded-md text-ink hover:text-primary"
          aria-label="RemitProof dashboard"
        >
          <span className="case-brand-mark grid size-9 place-items-center rounded-[10px] bg-surface-raised text-primary">
            <ShieldCheck aria-hidden="true" className="size-5" strokeWidth={2.2} />
          </span>
          <span>
            <span className="block text-[15px] font-semibold tracking-[-0.01em]">RemitProof</span>
            <span className="hidden text-xs text-muted sm:block">Financial conflict control</span>
          </span>
        </Link>
        <div className="flex shrink-0 items-center justify-end gap-2 sm:gap-4">
          <nav aria-label="Primary navigation" className="flex shrink-0 items-center gap-1 text-xs font-semibold sm:text-sm">
            <Link className="hidden whitespace-nowrap rounded-md px-2.5 py-2 text-muted hover:bg-surface-raised hover:text-ink sm:inline-flex" href="/">
              Dashboard
            </Link>
            <Link className="whitespace-nowrap rounded-md px-2.5 py-2 text-muted hover:bg-surface-raised hover:text-ink" href="/exceptions">
              Exception queue
            </Link>
            <Link className="whitespace-nowrap rounded-md px-2.5 py-2 text-muted hover:bg-surface-raised hover:text-ink" href="/benchmark">
              Benchmark
            </Link>
          </nav>
          {benchmarkRun && (
            <div className="hidden items-center gap-2 text-xs font-medium text-muted lg:flex">
              <span className="size-2 rounded-full bg-primary" aria-hidden="true" />
              <span>{benchmarkRun.shortLabel}</span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
