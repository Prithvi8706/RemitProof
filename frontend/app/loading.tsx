import { AppHeader } from "@/components/AppHeader";

export default function Loading() {
  return (
    <div className="min-h-screen bg-canvas">
      <AppHeader />
      <main className="mx-auto max-w-[1440px] px-4 py-12 sm:px-6" aria-busy="true" aria-label="Loading benchmark">
        <div className="skeleton h-4 w-52 rounded-md" />
        <div className="skeleton mt-6 h-14 max-w-3xl rounded-md" />
        <div className="skeleton mt-4 h-6 max-w-xl rounded-md" />
        <div className="mt-12 grid gap-4 sm:grid-cols-3">
          <div className="skeleton h-32 rounded-[12px]" />
          <div className="skeleton h-32 rounded-[12px]" />
          <div className="skeleton h-32 rounded-[12px]" />
        </div>
        <div className="skeleton mt-10 h-72 rounded-[12px]" />
      </main>
    </div>
  );
}
