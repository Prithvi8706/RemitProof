import { AppHeader } from "@/components/AppHeader";
import { SandboxWorkspace } from "@/components/SandboxWorkspace";

export default function SandboxPage() {
  return <div className="case-site sandbox-site min-h-screen bg-canvas text-ink">
    <AppHeader />
    <main className="mx-auto max-w-[1440px] px-4 py-10 sm:px-6">
      <header className="border-b border-line pb-7">
        <h1 className="text-3xl font-semibold tracking-tight">Investigate your own payment</h1>
        <p className="mt-3 max-w-[70ch] text-sm leading-6 text-muted">Build a dummy scenario, run reconciliation, and inspect the evidence behind the decision. Change an invoice or remove an email to see what changes.</p>
        <p className="mt-3 text-xs leading-5 text-muted">Sandbox only. Records you enter are simulated facts, including customer relationships and email senders. No payment is sent or posted. Use dummy data; the server does not persist scenarios. Live mode sends the candidate records to the configured model service.</p>
      </header>
      <SandboxWorkspace />
    </main>
  </div>;
}
