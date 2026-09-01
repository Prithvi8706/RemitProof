import { ShieldCheck } from "lucide-react";
import Link from "next/link";

export function AppHeader() {
  return (
    <header className="border-b border-primary bg-primary-dark text-white">
      <div className="mx-auto flex min-h-16 max-w-[1440px] items-center justify-between gap-3 px-4 py-2 sm:gap-6 sm:px-6">
        <Link
          href="/"
          className="flex items-center gap-3 rounded-md text-white hover:text-white/90"
          aria-label="RemitProof dashboard"
        >
          <span className="grid size-9 place-items-center rounded-[10px] bg-white text-primary-dark">
            <ShieldCheck aria-hidden="true" className="size-5" strokeWidth={2.2} />
          </span>
          <span>
            <span className="block text-[15px] font-semibold tracking-[-0.01em]">RemitProof</span>
            <span className="hidden text-xs text-white/70 sm:block">AI Finance Controller</span>
          </span>
        </Link>
        <div className="flex min-w-0 items-center justify-end gap-2 sm:gap-4">
          <nav aria-label="Primary navigation" className="flex items-center gap-1 text-xs font-semibold sm:text-sm">
            <Link className="hidden rounded-md px-2.5 py-2 text-white/80 hover:bg-white/10 hover:text-white sm:inline-flex" href="/">
              Dashboard
            </Link>
            <Link className="rounded-md px-2.5 py-2 text-white/80 hover:bg-white/10 hover:text-white" href="/exceptions">
              Exception queue
            </Link>
          </nav>
          <div className="hidden items-center gap-2 text-xs font-medium text-white/80 lg:flex">
            <span className="size-2 rounded-full bg-[oklch(0.78_0.16_145)]" aria-hidden="true" />
            <span>Benchmark frozen</span>
          </div>
        </div>
      </div>
    </header>
  );
}
