"use client";

import { AlertCircle, RotateCcw } from "lucide-react";
import { AppHeader } from "@/components/AppHeader";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="min-h-screen bg-canvas">
      <AppHeader />
      <main className="mx-auto max-w-[760px] px-4 py-20 sm:px-6">
        <div className="border border-danger/25 bg-danger-soft p-7 sm:p-9">
          <AlertCircle className="size-7 text-danger" aria-hidden="true" />
          <h1 className="mt-5 text-2xl font-semibold tracking-[-0.025em] text-ink">Benchmark data is unavailable.</h1>
          <p className="mt-3 max-w-[60ch] text-sm leading-6 text-muted">
            Confirm that the FastAPI service is running and that the generated evaluation artifacts are present.
          </p>
          <button
            type="button"
            onClick={reset}
            className="mt-6 inline-flex items-center gap-2 rounded-[10px] bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-dark"
          >
            <RotateCcw className="size-4" aria-hidden="true" />
            Retry benchmark
          </button>
        </div>
      </main>
    </div>
  );
}
