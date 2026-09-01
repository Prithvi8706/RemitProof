from decimal import Decimal
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class BaselineResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: str
    status: Literal["matched", "unresolved"]
    matched_invoices: List[str] = Field(default_factory=list)
    matched_credits: List[str] = Field(default_factory=list)
    customer_id: Optional[str] = None
    reason: str
    candidate_count: int = 0


class ProofResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    financial_validity: bool
    state_validity: bool
    currency_validity: bool
    entity_support: bool
    credit_support: bool
    duplicate_risk: bool
    contradictions: List[str] = Field(default_factory=list)
    missing_required_evidence: List[str] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)
    invoice_total: Decimal = Decimal("0")
    credit_total: Decimal = Decimal("0")
    calculated_total: Decimal = Decimal("0")
    payment_total: Decimal = Decimal("0")


class AlternativeAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    invoice_ids: List[str]
    credit_ids: List[str] = Field(default_factory=list)
    calculated_total: Decimal


class SufficiencyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    financial_validity: bool
    entity_support: bool
    credit_support: bool
    alternative_allocations_exist: bool
    evidence_disambiguates_alternatives: bool
    contradictions_exist: bool
    missing_required_evidence: List[str] = Field(default_factory=list)
    duplicate_risk: bool
    safe_to_resolve: bool
    abstention_reason: Optional[str] = None


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: str
    decision: Literal["matched_normally", "resolved", "human_review"]
    customer_id: Optional[str] = None
    invoice_ids: List[str] = Field(default_factory=list)
    credit_ids: List[str] = Field(default_factory=list)
    proof: Dict[str, object] = Field(default_factory=dict)
    evidence: List[str] = Field(default_factory=list)
    reason: str
    latency_ms: int = 0


class ProcessingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment: Dict[str, object]
    baseline: BaselineResult
    decision: Decision
    proposal: Optional[Dict[str, object]] = None
    candidates: Dict[str, List[Dict[str, object]]] = Field(default_factory=dict)
    proposed_allocation: List[Dict[str, object]] = Field(default_factory=list)
    evidence: List[Dict[str, object]] = Field(default_factory=list)
    proof: Optional[ProofResult] = None
    alternatives: List[AlternativeAllocation] = Field(default_factory=list)
    sufficiency: Optional[SufficiencyResult] = None
    counterfactuals: List[Dict[str, object]] = Field(default_factory=list)
    investigator_error: Optional[str] = None
