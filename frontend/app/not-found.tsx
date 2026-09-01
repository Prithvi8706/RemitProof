import { FileQuestion } from "lucide-react";
import Link from "next/link";
import { AppHeader } from "@/components/AppHeader";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-canvas">
      <AppHeader />
      <main className="mx-auto max-w-[720px] px-4 py-20 sm:px-6">
        <FileQuestion className="size-8 text-muted" aria-hidden="true" />
        <h1 className="mt-5 text-3xl font-semibold tracking-[-0.03em] text-ink">Exception not found</h1>
        <p className="mt-3 text-sm leading-6 text-muted">This payment is not present in the generated benchmark results.</p>
        <Link
          href="/"
          className="mt-7 inline-flex rounded-[10px] bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-dark"
        >
          Return to dashboard
        </Link>
      </main>
    </div>
  );
}
