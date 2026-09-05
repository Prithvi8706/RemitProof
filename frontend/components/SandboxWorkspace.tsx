"use client";

import { useEffect, useRef, useState } from "react";
import { AlternativesPanel } from "./AlternativesPanel";
import { EvidencePanel } from "./EvidencePanel";
import { EvidenceAlternativeMatrix } from "./EvidenceAlternativeMatrix";
import { ProofPanel } from "./ProofPanel";
import { PaymentPanel } from "./PaymentPanel";
import { DecisionBadge } from "./DecisionBadge";
import { blankScenario, errorMessage, parseScenario } from "@/lib/sandbox";
import type { Scenario, SandboxExample, SandboxRun } from "@/lib/sandbox";

const control = "w-full min-w-0 rounded-md border border-line-strong bg-canvas px-3 py-2 text-sm text-ink disabled:opacity-50";
const button = "rounded-md border border-line-strong px-3 py-2 text-sm font-semibold hover:bg-surface-raised disabled:cursor-wait disabled:opacity-50";
type Collection = "customers" | "invoices" | "credits" | "emails" | "related_payments";
const limits: Record<Collection, number> = { customers: 3, invoices: 8, credits: 3, emails: 4, related_payments: 4 };

function ListInput({ values, onChange }: { values: unknown[]; onChange: (values: string[]) => void }) {
  const [draft, setDraft] = useState<string | null>(null);
  return <input className={`${control} mt-1`} maxLength={4000} value={draft ?? values.join(", ")}
    onChange={event => setDraft(event.target.value)}
    onBlur={() => {
      if (draft !== null) onChange(draft.split(",").map(value => value.trim()).filter(Boolean));
      setDraft(null);
    }} />;
}

function download(value: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function newRecord(kind: Collection, scenario: Scenario): Record<string, unknown> {
  const customer = String(scenario.customers[0]?.customer_id ?? "CUS_DEMO");
  const currency = scenario.payment.currency;
  const suffix = crypto.randomUUID().slice(0, 6).toUpperCase();
  if (kind === "customers") return { customer_id: `CUS_${suffix}`, legal_name: "New customer", aliases: [], parent_entities: [], subsidiaries: [], known_payers: [] };
  if (kind === "invoices") return { invoice_id: `INV_${suffix}`, customer_id: customer, amount: "100.00", currency, issue_date: "2026-08-01", due_date: "2026-09-01", description: "Dummy invoice", status: "open" };
  if (kind === "credits") return { credit_id: `CR_${suffix}`, customer_id: customer, invoice_id: String(scenario.invoices[0]?.invoice_id ?? ""), amount: "10.00", currency, reason: "Service adjustment", status: "valid" };
  if (kind === "emails") return { email_id: `EMAIL_${suffix}`, customer_id: customer, sender: "accounts@example.test", date: scenario.payment.date, subject: `Remittance for ${scenario.payment.payment_id}`, body: "" };
  return { ...scenario.payment, payment_id: `PAY_${suffix}` };
}

function RecordFields({ record, onChange }: { record: Record<string, unknown>; onChange: (row: Record<string, unknown>) => void }) {
  return <div className="grid gap-4 sm:grid-cols-2">
    {Object.entries(record).map(([key, value]) => <label key={key} className={`block text-xs font-medium text-muted ${key === "body" ? "sm:col-span-2" : ""}`}>
      {key.replaceAll("_", " ")}{Array.isArray(value) ? " (comma separated)" : ""}
      {key === "body" ? <textarea className={`${control} mt-1 min-h-28`} maxLength={12000} value={String(value ?? "")} onChange={e => onChange({ ...record, [key]: e.target.value })} /> :
        Array.isArray(value) ? <ListInput values={value} onChange={values => onChange({ ...record, [key]: values })} /> : <input className={`${control} mt-1`} type={key.includes("date") || key === "date" ? "date" : "text"} maxLength={2000}
          value={Array.isArray(value) ? value.join(", ") : String(value ?? "")}
          onChange={e => onChange({ ...record, [key]: Array.isArray(value) ? e.target.value.split(",").map(x => x.trim()).filter(Boolean) : value === null && !e.target.value ? null : e.target.value })} />}
    </label>)}
  </div>;
}

export function SandboxWorkspace() {
  const [scenario, setScenario] = useState<Scenario>(blankScenario);
  const [examples, setExamples] = useState<SandboxExample[]>([]);
  const [liveEnabled, setLiveEnabled] = useState(false);
  const [serviceStatus, setServiceStatus] = useState("Checking investigation service…");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [jsonEditor, setJsonEditor] = useState<string | null>(null);
  const [history, setHistory] = useState<{ run: SandboxRun; input: Scenario }[]>([]);
  const [selected, setSelected] = useState(0);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const active = history[selected];
  const stale = active && JSON.stringify(active.input) !== JSON.stringify(scenario);

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const [capabilities, sampleResponse] = await Promise.all([
          fetch("/api/sandbox/capabilities"), fetch("/api/sandbox/examples"),
        ]);
        if (!capabilities.ok || !sampleResponse.ok) throw new Error("Unavailable");
        const caps = await capabilities.json();
        const samples = await sampleResponse.json();
        if (!Array.isArray(samples)) throw new Error("Invalid examples");
        const validated = samples.map(item => ({ ...item, scenario: parseScenario(JSON.stringify(item.scenario)) }));
        if (!ignore) {
          setLiveEnabled(caps.live_ai_enabled === true);
          setExamples(validated);
          setServiceStatus(caps.live_ai_enabled ? "Live AI configured; availability checked when you run." : "Verifier ready. Live AI is not configured on this server.");
        }
      } catch {
        if (!ignore) setServiceStatus("Service unavailable. You can edit and export your scenario, then retry a run.");
      }
    }
    void load();
    return () => { ignore = true; };
  }, []);

  function loadScenario(next: Scenario) {
    setScenario(structuredClone(next)); setJsonEditor(null); setError("");
  }

  async function run() {
    setBusy(true); setError("");
    const input = structuredClone(scenario);
    try {
      const response = await fetch("/api/sandbox/investigate", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input), signal: AbortSignal.timeout(140000),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(errorMessage(data));
      if (data.schema_version !== 1 || !data.detail?.decision || !data.run_id) throw new Error("The service returned an invalid report. Try again.");
      setHistory(previous => [{ run: data, input }, ...previous].slice(0, 5)); setSelected(0);
      resultHeading.current?.focus();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not run investigation. Try again.");
    } finally { setBusy(false); }
  }

  return <>
    <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
      <p role="status" className="text-xs text-muted">{serviceStatus}</p>
      <div className="flex flex-wrap gap-2">
        <button className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-50" disabled={busy || jsonEditor !== null || (scenario.mode === "live_ai" && !liveEnabled)} onClick={() => void run()}>{busy ? "Investigating…" : "Run reconciliation"}</button>
        <button className={button} disabled={busy} onClick={() => loadScenario(blankScenario())}>New scenario</button>
        <button className={button} onClick={() => download(scenario, "remitproof-scenario.json")}>Export scenario</button>
        <label className={`${button} cursor-pointer`}>Import JSON<input type="file" accept=".json,application/json" className="sr-only" disabled={busy} onChange={async event => {
          const file = event.target.files?.[0]; event.target.value = "";
          if (!file) return;
          try { if (file.size > 65536) throw new Error("Scenario exceeds the 64 KiB limit"); loadScenario(parseScenario(await file.text())); }
          catch (failure) { setError(failure instanceof Error ? failure.message : "Invalid scenario file"); }
        }} /></label>
      </div>
    </div>
    <div className="mt-5 border-y border-line py-4">
      <p className="text-sm font-semibold">Start with an editable example</p>
      <div className="mt-3 flex flex-wrap gap-2">{examples.map(example => <button key={example.name} title={example.description} className={button} disabled={busy} onClick={() => loadScenario(example.scenario)}>{example.name}</button>)}</div>
      <p className="mt-2 text-xs text-muted">Examples use synthetic benchmark records with supplied hypotheses. Each run recomputes the decision from your current inputs.</p>
    </div>

    <div className="mt-7 grid items-start gap-8 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <section aria-labelledby="scenario-title" className="min-w-0">
        <h2 id="scenario-title" className="text-xl font-semibold">Scenario editor</h2>
        <p className="mt-2 text-sm leading-6 text-muted">Amounts use decimal strings. Record IDs must be unique; customer and invoice references must point to records in this scenario.</p>
        <fieldset disabled={busy} className="mt-5 space-y-3">
          <details open className="rounded-lg border border-line p-4"><summary className="cursor-pointer text-sm font-semibold">Payment</summary><div className="mt-4"><RecordFields record={{ ...scenario.payment }} onChange={payment => setScenario({ ...scenario, payment: payment as unknown as Scenario["payment"], proposal: scenario.proposal ? { ...scenario.proposal, payment_id: String(payment.payment_id) } : null })} /></div></details>
          {(Object.keys(limits) as Collection[]).map(kind => <details key={kind} className="rounded-lg border border-line p-4">
            <summary className="cursor-pointer text-sm font-semibold capitalize">{kind.replaceAll("_", " ")} <span className="font-normal text-muted">({scenario[kind].length}/{limits[kind]})</span></summary>
            <div className="mt-4 space-y-6">
              {scenario[kind].map((row, index) => <div key={index} className="border-t border-line pt-4">
                <div className="mb-3 flex items-center justify-between gap-2"><p className="text-xs font-semibold">Record {index + 1}</p><button className="rounded px-2 py-1 text-xs font-semibold text-danger hover:bg-danger-soft" onClick={() => setScenario({ ...scenario, [kind]: scenario[kind].filter((_, i) => i !== index) })}>Remove record {index + 1}</button></div>
                <RecordFields record={row} onChange={next => setScenario({ ...scenario, [kind]: scenario[kind].map((old, i) => i === index ? next : old) })} />
              </div>)}
              <button className={button} disabled={scenario[kind].length >= limits[kind]} onClick={() => setScenario({ ...scenario, [kind]: [...scenario[kind], newRecord(kind, scenario)] })}>Add {kind === "related_payments" ? "related payment" : kind.slice(0, -1)}</button>
            </div>
          </details>)}
          <section className="rounded-lg border border-line p-4" aria-labelledby="mode-title">
            <h3 id="mode-title" className="text-sm font-semibold">Investigation mode</h3>
            <label className="mt-3 block text-xs text-muted">Proposal source<select className={`${control} mt-1`} value={scenario.mode} onChange={event => setScenario({ ...scenario, mode: event.target.value as Scenario["mode"], proposal: event.target.value === "live_ai" ? null : { ...blankScenario().proposal!, payment_id: scenario.payment.payment_id, proposed_customer: String(scenario.customers[0]?.customer_id ?? ""), invoice_ids: [], evidence_ids: [] } })}>
              <option value="manual_proposal">Test my hypothesis (no model call)</option>
              <option value="live_ai" disabled={!liveEnabled}>Live AI investigation{!liveEnabled ? " (not configured)" : ""}</option>
            </select></label>
            <p className="mt-3 text-xs leading-5 text-muted">The baseline always runs first. In manual mode, you supply the untrusted proposal; the backend still checks money, state, evidence, and competing allocations. This is not an AI-generated answer.</p>
            {scenario.proposal && <div className="mt-4 space-y-3">
              <label className="block text-xs text-muted">Proposed customer<input className={`${control} mt-1`} value={scenario.proposal.proposed_customer ?? ""} onChange={e => setScenario({ ...scenario, proposal: { ...scenario.proposal!, proposed_customer: e.target.value || null } })} /></label>
              {(["invoice_ids", "credit_ids", "evidence_ids", "unresolved_questions"] as const).map(key => <label className="block text-xs text-muted" key={key}>{key.replaceAll("_", " ")} (comma separated)<ListInput values={scenario.proposal![key]} onChange={values => setScenario({ ...scenario, proposal: { ...scenario.proposal!, [key]: values } })} /></label>)}
              <p className="text-xs text-muted">Semantic claims are preserved from the example. Use the full JSON editor to edit them or optional record fields.</p>
            </div>}
          </section>
          <button className={button} onClick={() => setJsonEditor(jsonEditor === null ? JSON.stringify(scenario, null, 2) : null)}>{jsonEditor === null ? "Open full JSON editor" : "Close JSON editor"}</button>
          {jsonEditor !== null && <div><label className="block text-xs text-muted">Full scenario JSON<textarea className={`${control} mt-2 min-h-80 font-mono text-xs`} value={jsonEditor} onChange={e => setJsonEditor(e.target.value)} /></label><button className={`${button} mt-2`} onClick={() => { try { loadScenario(parseScenario(jsonEditor)); } catch (failure) { setError(failure instanceof Error ? failure.message : "Invalid JSON"); } }}>Apply JSON changes</button><p className="mt-2 text-xs text-muted">Apply or close this editor before running.</p></div>}
        </fieldset>
        {error && <p role="alert" className="mt-4 whitespace-pre-wrap rounded-md border border-danger bg-danger-soft p-4 text-sm text-danger">{error}</p>}
        <button className="mt-5 w-full rounded-md bg-primary px-5 py-3 text-sm font-semibold text-white hover:bg-primary-dark disabled:cursor-wait disabled:opacity-50" disabled={busy || jsonEditor !== null || (scenario.mode === "live_ai" && !liveEnabled)} onClick={() => void run()}>{busy ? "Investigating your scenario…" : "Run reconciliation"}</button>
      </section>

      <section aria-labelledby="result-title" aria-busy={busy} className="min-w-0">
        <h2 id="result-title" ref={resultHeading} tabIndex={-1} className="text-xl font-semibold">Investigation result</h2>
        <p className="mt-2 text-xs leading-5 text-muted">Up to five runs stay in this tab’s memory. Refreshing clears them. Download a report to keep it.</p>
        {history.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{history.map((item, index) => <button key={item.run.run_id} aria-pressed={selected === index} className={`${button} ${selected === index ? "bg-surface-raised" : ""}`} onClick={() => setSelected(index)}>Run {history.length - index}: {item.run.detail.decision.decision.replaceAll("_", " ")}</button>)}<button className={button} onClick={() => { setHistory([]); setSelected(0); }}>Clear history</button></div>}
        <div role="status" className="mt-4 text-sm text-muted">{busy ? "Running the pipeline. Previous results below remain unchanged until this run finishes." : stale ? "The editor differs from this report. Run again to evaluate your changes." : active ? "Report matches the current scenario." : "Run a scenario to see the decision, proof checks, and competing explanations here."}</div>
        {active && <div className="mt-5 space-y-7">
          <div className="border-y border-line py-5">
            <DecisionBadge decision={active.run.detail.decision.decision} />
            <p className="mt-3 text-sm leading-6">{active.run.detail.decision.reason}</p>
            <p className="mt-3 text-xs text-muted">Proposal source: {active.run.proposal_source.replaceAll("_", " ")} · Pipeline: {active.run.detail.decision.latency_ms} ms</p>
            <p className="mt-2 text-xs text-muted">Simulation decision only. No accounting entry was posted.</p>
            <div className="mt-4 flex flex-wrap gap-2"><button className={button} onClick={() => download(active, `remitproof-report-${active.run.run_id}.json`)}>Download audit report</button><button className={button} disabled={busy} onClick={() => loadScenario(active.input)}>Restore these inputs</button></div>
            {selected + 1 < history.length && <p className="mt-3 text-sm text-muted">Compared with the previous run: {history[selected + 1].run.detail.decision.decision.replaceAll("_", " ")} → {active.run.detail.decision.decision.replaceAll("_", " ")}. Financial allocations found: {history[selected + 1].run.detail.proof ? history[selected + 1].run.detail.alternatives.length : "not evaluated"} → {active.run.detail.proof ? active.run.detail.alternatives.length : "not evaluated"}.</p>}
          </div>
          <PaymentPanel payment={active.run.detail.payment} />
          <div><h3 className="text-base font-semibold">Baseline decision</h3><p className="mt-2 text-sm text-muted">{active.run.detail.baseline.reason.replaceAll("_", " ")}</p></div>
          {active.run.detail.proposal && <section><h3 className="text-base font-semibold">{active.run.mode === "manual_proposal" ? "Your submitted hypothesis" : "AI proposal"}</h3><p className="mt-2 text-sm text-muted">Customer: {active.run.detail.proposal.proposed_customer ?? "Unidentified"}. Invoices: {active.run.detail.proposal.invoice_ids.join(" + ") || "None"}. Credits: {active.run.detail.proposal.credit_ids.join(", ") || "None"}.</p><details className="mt-3"><summary className="cursor-pointer text-sm font-semibold">Inspect complete proposal</summary><pre className="mt-2 max-h-80 overflow-auto bg-surface p-3 text-xs">{JSON.stringify(active.run.detail.proposal, null, 2)}</pre></details></section>}
          {active.run.detail.proof && <><ProofPanel detail={active.run.detail} /><EvidencePanel citedEvidence={active.run.detail.model_cited_evidence} auditRecords={active.run.detail.audit_records} missingEvidenceIds={active.run.detail.proof.missing_required_evidence} claims={active.run.detail.proposal?.semantic_claims ?? []} /><EvidenceAlternativeMatrix detail={active.run.detail} /><AlternativesPanel alternatives={active.run.detail.alternatives} decision={active.run.detail.decision} sufficiency={active.run.detail.sufficiency} currency={active.run.detail.payment.currency} /></>}
          {active.run.detail.investigator_error && <p className="border border-warning bg-warning-soft p-4 text-sm">{active.run.detail.investigator_error}</p>}
          <details className="border-t border-line pt-4"><summary className="cursor-pointer text-sm font-semibold">Run provenance and complete audit artifact</summary><p className="mt-3 break-all text-xs text-muted">Input SHA-256: {active.run.input_sha256}<br />Created: {active.run.created_at}<br />Run ID: {active.run.run_id}</p><pre className="mt-3 max-h-96 overflow-auto bg-surface p-3 text-xs">{JSON.stringify(active.run.detail, null, 2)}</pre></details>
        </div>}
      </section>
    </div>
  </>;
}
