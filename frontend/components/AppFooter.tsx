export function AppFooter() {
  return (
    <footer className="case-footer mt-16 border-t border-line bg-surface">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-2 px-4 py-7 text-xs leading-5 text-muted sm:px-6 lg:flex-row lg:items-center lg:justify-between">
        <p>Prototype only. No production accounting write-back or settlement is performed.</p>
        <p>Payment records are API-compatible; ERP, email, and credit data are synthetic.</p>
      </div>
    </footer>
  );
}
