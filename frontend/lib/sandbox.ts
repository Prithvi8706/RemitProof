import type { ExceptionDetail, PaymentRecord, ProposalRecord } from "./types.ts";

export interface Scenario {
  schema_version: 1;
  mode: "manual_proposal" | "live_ai";
  payment: PaymentRecord;
  customers: Record<string, unknown>[];
  invoices: Record<string, unknown>[];
  credits: Record<string, unknown>[];
  emails: Record<string, unknown>[];
  related_payments: Record<string, unknown>[];
  proposal: ProposalRecord | null;
}
export interface SandboxExample { name: string; description: string; scenario: Scenario }
export interface SandboxRun {
  schema_version: 1;
  run_id: string;
  created_at: string;
  input_sha256: string;
  mode: Scenario["mode"];
  proposal_source: string;
  simulation_only: true;
  stored: false;
  detail: ExceptionDetail;
}

// Structural import checks keep the editor safe; financial validation belongs to Python.
export function parseScenario(text: string): Scenario {
  const data = JSON.parse(text);
  if (!data || typeof data !== "object" || data.schema_version !== 1 ||
      !["manual_proposal", "live_ai"].includes(data.mode) ||
      !data.payment || typeof data.payment !== "object" || Array.isArray(data.payment)) {
    throw new Error("Use a scenario JSON export with schema_version 1, a mode, and a payment object.");
  }
  for (const key of ["customers", "invoices", "credits", "emails", "related_payments"]) {
    if (!Array.isArray(data[key]) || data[key].some((row: unknown) => !row || typeof row !== "object" || Array.isArray(row))) {
      throw new Error(`${key} must be an array of records.`);
    }
  }
  const paymentFields = ["payment_id", "date", "amount", "currency", "payer_name", "bank_reference", "remittance_reference", "status"];
  if (paymentFields.some(key => typeof data.payment[key] !== "string")) {
    throw new Error("Payment fields must be strings. Use quoted decimal amounts, for example \"100.00\".");
  }
  if (data.mode === "manual_proposal") {
    const p = data.proposal;
    if (!p || typeof p !== "object" || typeof p.payment_id !== "string" ||
        (p.proposed_customer !== null && typeof p.proposed_customer !== "string") ||
        ["invoice_ids", "credit_ids", "evidence_ids", "unresolved_questions"].some(key =>
          !Array.isArray(p[key]) || p[key].some((value: unknown) => typeof value !== "string")) ||
        !Array.isArray(p.semantic_claims)) {
      throw new Error("Manual mode requires a complete proposal. Start from an exported example.");
    }
  } else if (data.proposal != null) {
    throw new Error("Set proposal to null for live AI mode.");
  }
  return data;
}

export function blankScenario(): Scenario {
  return {
    schema_version: 1, mode: "manual_proposal",
    payment: { payment_id: "PAY_DEMO", date: "2026-09-05", amount: "100.00", currency: "USD", payer_name: "Example Customer", bank_reference: "DUMMY-001", remittance_reference: "INV_DEMO", status: "unmatched" },
    customers: [{ customer_id: "CUS_DEMO", legal_name: "Example Customer", aliases: [], parent_entities: [], subsidiaries: [], known_payers: [] }],
    invoices: [{ invoice_id: "INV_DEMO", customer_id: "CUS_DEMO", amount: "100.00", currency: "USD", issue_date: "2026-08-01", due_date: "2026-09-01", description: "Dummy consulting invoice", status: "open" }],
    credits: [], emails: [], related_payments: [],
    proposal: { payment_id: "PAY_DEMO", proposed_customer: "CUS_DEMO", invoice_ids: ["INV_DEMO"], credit_ids: [], semantic_claims: [], evidence_ids: ["CUS_DEMO"], unresolved_questions: [] },
  };
}

export function errorMessage(data: unknown): string {
  if (!data || typeof data !== "object" || !("detail" in data)) return "The investigation could not be completed.";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map(item => `${item.path || "Scenario"}: ${item.message}`).join("\n");
  return "Check your scenario and try again.";
}
