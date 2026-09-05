import { AppHeader } from "@/components/AppHeader";

export default function BenchmarkLoading() {
  return (
    <div className="case-site min-h-screen bg-canvas">
      <AppHeader />
      <main className="mx-auto max-w-[1440px] px-4 py-12 sm:px-6" aria-busy="true" aria-label="Loading benchmark">
        <p className="sr-only" role="status">Loading benchmark</p>
        <div className="skeleton h-5 w-40 rounded-md" />
        <div className="skeleton mt-8 h-10 max-w-sm rounded-md" />
        <div className="skeleton mt-3 h-6 max-w-2xl rounded-md" />
        <div className="skeleton mt-10 h-40 rounded-[12px]" />
        <div className="skeleton mt-6 h-80 rounded-[12px]" />
      </main>
    </div>
  );
}
