from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .credit import Credit
from .customer import Customer
from .email import RemittanceEmail
from .invoice import Invoice
from .payment import Payment


class SemanticClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(description="A unique claim ID such as CLAIM_001.")
    claim: str = Field(description="One concise semantic claim; never arithmetic authorization.")
    evidence_ids: List[str] = Field(
        default_factory=list,
        description="Only IDs from the supplied customer, email, credit, or invoice records.",
    )

    @field_validator("evidence_ids")
    @classmethod
    def evidence_identifiers_must_be_unique(cls, values: List[str]) -> List[str]:
        if len(values) != len(set(values)):
            raise ValueError("semantic claim evidence identifiers must be unique")
        return values


class InvestigationProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: str = Field(description="Exact payment_id string from candidate_bundle.payment.")
    proposed_customer: Optional[str] = Field(
        default=None,
        description="A customer_id string such as CUS_001, never a customer object.",
    )
    invoice_ids: List[str] = Field(
        default_factory=list,
        description="Invoice ID strings selected for the candidate allocation.",
    )
    credit_ids: List[str] = Field(
        default_factory=list,
        description="Only supplied credit ID strings that the evidence says to apply.",
    )
    semantic_claims: List[SemanticClaim] = Field(default_factory=list)
    evidence_ids: List[str] = Field(
        default_factory=list,
        description="All supplied record IDs that support this proposal.",
    )
    unresolved_questions: List[str] = Field(
        default_factory=list,
        description="Material uncertainties; these do not replace the best candidate proposal.",
    )

    @field_validator("invoice_ids", "credit_ids", "evidence_ids")
    @classmethod
    def identifiers_must_be_unique(cls, values: List[str]) -> List[str]:
        if len(values) != len(set(values)):
            raise ValueError("identifier lists must be unique")
        return values

    @model_validator(mode="after")
    def semantic_claim_identifiers_must_be_unique(self) -> "InvestigationProposal":
        claim_ids = [claim.claim_id for claim in self.semantic_claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("semantic claim identifiers must be unique")
        return self


class CandidateBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment: Payment
    candidate_customers: List[Customer] = Field(default_factory=list)
    candidate_invoices: List[Invoice] = Field(default_factory=list)
    candidate_credits: List[Credit] = Field(default_factory=list)
    candidate_emails: List[RemittanceEmail] = Field(default_factory=list)

    @model_validator(mode="after")
    def candidate_identifiers_must_be_unique(self) -> "CandidateBundle":
        collections = (
            (self.candidate_customers, "customer_id", "customer"),
            (self.candidate_invoices, "invoice_id", "invoice"),
            (self.candidate_credits, "credit_id", "credit"),
            (self.candidate_emails, "email_id", "email"),
        )
        for records, id_field, record_type in collections:
            identifiers = [getattr(record, id_field) for record in records]
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"candidate {record_type} identifiers must be unique")
        return self
