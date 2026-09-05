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
  model_inference_attempted?: boolean;
  proposal_source_identity_verified?: boolean;
}

export interface EvaluationProvenance {
  evaluator_version: string;
  evaluation_mode: string;
  dataset_sha256: string;
  proposal_cache_sha256: string;
  proposal_source_identity_verified: boolean;
  live_model_calls: number;
  successful_live_model_calls: number;
  failed_live_model_calls: number;
  investigator: {
    investigator_version: string;
    model: string;
    model_digest: string | null;
    prompt_sha256: string;
    proposal_schema_sha256: string;
  };
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
  evaluation_generation_id: string;
  result_status: "model_backed_benchmark" | "offline_verifier_regression_only";
  benchmark_claim_eligible: boolean;
  partition_label: string;
  independent_held_out: boolean;
  model: string;
  timing_scope: string;
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
  alternative_detection_accuracy: number;
  ambiguity_detection_accuracy: number;
  contradiction_detection_accuracy: number;
  decision_critical_evidence_accuracy: number;
  throughput_per_minute: number;
  mean_latency_ms: number;
  evaluation_mode: string;
  cache: EvaluationCacheMetadata;
  provenance: EvaluationProvenance;
  comparison_record_count: number;
  comparison_scope: string;
  comparison: {
    baseline: ComparisonMetrics;
    llm_only: ComparisonMetrics;
    remitproof: ComparisonMetrics;
  };
  held_out: Omit<BenchmarkData, "held_out">;
}

export interface BenchmarkCaseRow {
  payment_id: string;
  split: string;
  exception_class: string;
  payer: string;
  amount: string;
  currency: string;
  expected_should_resolve: boolean;
  baseline_decision: "human_review";
  llm_only_decision: "resolve" | "abstain";
  llm_only_wrong_resolution: boolean;
  remitproof_decision: "resolved" | "human_review";
  remitproof_correct_resolution: boolean;
  correct_abstention: boolean;
  false_escalation: boolean;
  wrong_auto_resolution: boolean;
  recovered_from_baseline: boolean;
  reason: string;
}

export interface ClassBreakdownRow {
  exception_class: string;
  records: number;
  resolved: number;
  correct_resolutions: number;
  human_review: number;
  wrong_auto_resolutions: number;
  false_escalations: number;
}

export interface BenchmarkCasesData {
  evaluation_generation_id: string;
  result_status: string;
  evaluation_mode: string;
  comparison_scope: string;
  comparator_mode: string;
  comparator_label: string;
  summary: {
    comparison_record_count: number;
    llm_only_wrong_resolutions: number;
    remitproof_wrong_auto_resolutions: number;
    recovered_from_baseline: number;
    correct_abstentions: number;
    false_escalations: number;
  };
  cases: BenchmarkCaseRow[];
  by_class: ClassBreakdownRow[];
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
  chosen_proposal_supported: boolean;
  alternatives_eliminated: boolean;
  uniquely_distinguishing_evidence: string[];
  evidence_alternative_matrix: EvidenceAlternativeAssessment[];
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
  allocation_id: string;
  customer_id: string;
  invoice_ids: string[];
  credit_ids: string[];
  calculated_total: string;
  financially_valid: boolean;
}

export interface EvidenceAlternativeAssessment {
  evidence_id: string;
  allocation_id: string;
  relationship: "supports" | "contradicts" | "shared_fact" | "superseded" | "irrelevant";
  reason: string;
}

export interface ConflictRecord {
  conflict_id: string;
  payment_id: string;
  type: string;
  allocation_ids: string[];
  reason: string;
  required_disambiguation: string[];
  status: "cleared" | "unresolved";
}

export interface CounterfactualRecord {
  evidence_id: string;
  decision_with_evidence: "resolved" | "human_review";
  decision_without_evidence: "resolved" | "human_review";
  decision_critical: boolean;
  reason: string;
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
  conflict: ConflictRecord | null;
  sufficiency: SufficiencyRecord | null;
  counterfactuals: CounterfactualRecord[];
  resolution_proof: Record<string, unknown> | null;
  blocked_decision: Record<string, unknown> | null;
  investigator_error: string | null;
}
