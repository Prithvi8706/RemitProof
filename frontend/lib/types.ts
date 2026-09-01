export type DecisionState = "matched_normally" | "resolved" | "human_review";

export interface ExceptionSummary {
  payment_id: string;
  date: string;
  payer: string;
  amount: string;
  currency: string;
  status: string;
  exception_class: string;
  decision: DecisionState;
  reason: string;
  latency_ms: number;
}

export interface EvaluationCacheMetadata {
  status: string;
  model_inference_included: boolean | null;
  hits?: number;
  misses?: number;
}

export interface DashboardData {
  total_receipts: number;
  matched_normally: number;
  exceptions: number;
  resolved_by_remitproof: number;
  human_review: number;
  incorrect_auto_resolution_rate: number;
  throughput_per_minute: number;
  mean_latency_ms: number;
  evaluation_mode: string;
  cache: EvaluationCacheMetadata;
  recent_exceptions: ExceptionSummary[];
}

export interface ComparisonMetrics {
  resolved: number;
  correct_resolutions: number;
  wrong_auto_resolutions: number;
  correct_abstentions: number;
  false_escalations: number;
}

export interface BenchmarkData {
  total_receipts: number;
  matched_normally: number;
  exceptions: number;
  resolved_by_remitproof: number;
  human_review: number;
  baseline_match_rate: number;
  exception_resolution_rate: number;
  resolution_accuracy: number;
  incorrect_auto_resolution_rate: number;
  correct_abstention_rate: number;
  false_escalation_rate: number;
  entity_resolution_accuracy: number;
  evidence_precision: number;
  arithmetic_correctness: number;
  retrieval_accuracy: number;
  throughput_per_minute: number;
  mean_latency_ms: number;
  evaluation_mode: string;
  cache: EvaluationCacheMetadata;
  comparison_record_count: number;
  comparison_scope: string;
  comparison: {
    baseline: ComparisonMetrics;
    llm_only: ComparisonMetrics;
    remitproof: ComparisonMetrics;
  };
  held_out: Omit<BenchmarkData, "held_out">;
}

export interface PaymentRecord {
  payment_id: string;
  date: string;
  amount: string;
  currency: string;
  payer_name: string;
  bank_reference: string;
  remittance_reference: string;
  status: string;
}

export interface BaselineRecord {
  payment_id: string;
  status: "matched" | "unresolved";
  matched_invoices: string[];
  matched_credits: string[];
  customer_id: string | null;
  reason: string;
  candidate_count: number;
}

export interface SemanticClaimRecord {
  claim_id: string;
  claim: string;
  evidence_ids: string[];
}

export interface ProposalRecord {
  payment_id: string;
  proposed_customer: string | null;
  invoice_ids: string[];
  credit_ids: string[];
  semantic_claims: SemanticClaimRecord[];
  evidence_ids: string[];
  unresolved_questions: string[];
}

export interface DecisionRecord {
  payment_id: string;
  decision: DecisionState;
  customer_id: string | null;
  invoice_ids: string[];
  credit_ids: string[];
  proof: Record<string, unknown>;
  evidence: string[];
  reason: string;
  latency_ms: number;
}

export interface ProofRecord {
  financial_validity: boolean;
  state_validity: boolean;
  currency_validity: boolean;
  entity_support: boolean;
  credit_support: boolean;
  duplicate_risk: boolean;
  contradictions: string[];
  missing_required_evidence: string[];
  reason_codes: string[];
  invoice_total: string;
  credit_total: string;
  calculated_total: string;
  payment_total: string;
}

export interface SufficiencyRecord {
  financial_validity: boolean;
  entity_support: boolean;
  credit_support: boolean;
  alternative_allocations_exist: boolean;
  evidence_disambiguates_alternatives: boolean;
  contradictions_exist: boolean;
  missing_required_evidence: string[];
  duplicate_risk: boolean;
  safe_to_resolve: boolean;
  abstention_reason: string | null;
}

export interface AllocationRow {
  record_type: "invoice" | "credit";
  record_id: string;
  description: string;
  amount: string;
  currency: string;
  operator: "+" | "-";
}

export interface EvidenceRecord {
  evidence_id: string;
  evidence_type: "customer_record" | "invoice_record" | "remittance_email" | "credit_note";
  title: string;
  content: string | Record<string, unknown>;
  sender?: string;
  date?: string;
  evidence_role?: "model_citation" | "audit_context";
}

export interface AlternativeRecord {
  customer_id: string;
  invoice_ids: string[];
  credit_ids: string[];
  calculated_total: string;
}

export interface ExceptionDetail {
  exception_class: string;
  payment: PaymentRecord;
  baseline: BaselineRecord;
  decision: DecisionRecord;
  proposal: ProposalRecord | null;
  candidates: Record<string, Array<Record<string, unknown>>>;
  proposed_allocation: AllocationRow[];
  evidence: EvidenceRecord[];
  model_cited_evidence: EvidenceRecord[];
  audit_records: EvidenceRecord[];
  proof: ProofRecord | null;
  alternatives: AlternativeRecord[];
  sufficiency: SufficiencyRecord | null;
  counterfactuals: Array<Record<string, unknown>>;
  investigator_error: string | null;
}
