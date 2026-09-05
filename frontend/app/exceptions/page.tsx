import { ArrowLeft, ListChecks } from "lucide-react";
import Link from "next/link";
import { AppFooter } from "@/components/AppFooter";
import { AppHeader } from "@/components/AppHeader";
import { ExceptionTable } from "@/components/ExceptionTable";
import { getExceptions } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ExceptionQueuePage() {
  const exceptions = await getExceptions();

  return (
    <div className="case-site min-h-screen bg-canvas">
      <AppHeader />
      <main className="mx-auto min-w-0 max-w-[1440px] px-4 py-8 sm:px-6 sm:py-10">
        <nav aria-label="Breadcrumb">
          <Link className="case-back-link inline-flex items-center gap-2 rounded-md py-1 text-sm font-semibold text-muted hover:text-primary" href="/">
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to dashboard
          </Link>
        </nav>

        <header className="case-page-heading mt-7 border-b border-line pb-8">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-[10px] bg-primary-soft text-primary-dark">
              <ListChecks className="size-5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h1 className="text-3xl font-semibold tracking-[-0.035em] text-ink sm:text-4xl">Exception queue</h1>
              <p className="mt-2 max-w-[68ch] text-sm leading-6 text-muted">
                Every unresolved-payment investigation in the published result set is reachable here.
              </p>
            </div>
          </div>
          <p className="numeric mt-5 text-sm font-semibold text-primary-dark">{exceptions.length} cases</p>
        </header>

        <section className="mt-8" aria-labelledby="all-exceptions-title">
          <h2 id="all-exceptions-title" className="sr-only">All exception investigations</h2>
          <ExceptionTable exceptions={exceptions} caption="All unresolved-payment investigations" />
        </section>
      </main>
      <AppFooter />
    </div>
  );
}
