import { AppHeader } from "@/components/AppHeader";

export default function ExceptionQueueLoading() {
  return (
    <div className="min-h-screen bg-canvas">
      <AppHeader />
      <main className="mx-auto max-w-[1440px] px-4 py-12 sm:px-6" aria-busy="true" aria-label="Loading exception queue">
        <p className="sr-only" role="status">Loading exception queue</p>
        <div className="skeleton h-5 w-40 rounded-md" />
        <div className="skeleton mt-8 h-10 max-w-sm rounded-md" />
        <div className="skeleton mt-3 h-6 max-w-2xl rounded-md" />
        <div className="skeleton mt-10 h-96 rounded-[12px]" />
      </main>
    </div>
  );
}
