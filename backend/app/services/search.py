from collections import Counter
from dataclasses import dataclass
from typing import Optional, Tuple

from app.models import AlternativeAllocation
from app.services.alternative_finder import (
    eligible_credits,
    eligible_invoices,
    find_valid_alternatives,
)
from app.services.proof_set import ProofSet


INVOICE_SEARCH_LIMIT = 16
CREDIT_SEARCH_LIMIT = 3

STATUS_UNIQUE = "unique"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_NONE = "none"
STATUS_UNKNOWN = "unknown"

DETAIL_RETRIEVAL_INCOMPLETE = "retrieval_incomplete"
DETAIL_INVOICE_LIMIT = "invoice_limit"
DETAIL_CREDIT_LIMIT = "credit_limit"


@dataclass(frozen=True)
class SearchOutcome:
    status: str
    complete: bool
    alternatives: Tuple[AlternativeAllocation, ...]
    detail: Optional[str]
    incomplete_reasons: Tuple[str, ...]


def search(proof_set: ProofSet) -> SearchOutcome:
    if not proof_set.complete:
        return SearchOutcome(
            status=STATUS_UNKNOWN,
            complete=False,
            alternatives=(),
            detail=DETAIL_RETRIEVAL_INCOMPLETE,
            incomplete_reasons=proof_set.incomplete_reasons,
        )
    bundle = proof_set.proof_bundle
    invoice_counts = Counter(invoice.customer_id for invoice in eligible_invoices(bundle))
    if any(count > INVOICE_SEARCH_LIMIT for count in invoice_counts.values()):
        return SearchOutcome(
            status=STATUS_UNKNOWN,
            complete=False,
            alternatives=(),
            detail=DETAIL_INVOICE_LIMIT,
            incomplete_reasons=(),
        )
    credit_counts = Counter(credit.customer_id for credit in eligible_credits(bundle))
    if any(count > CREDIT_SEARCH_LIMIT for count in credit_counts.values()):
        return SearchOutcome(
            status=STATUS_UNKNOWN,
            complete=False,
            alternatives=(),
            detail=DETAIL_CREDIT_LIMIT,
            incomplete_reasons=(),
        )
    alternatives = tuple(find_valid_alternatives(bundle))
    if len(alternatives) == 0:
        status = STATUS_NONE
    elif len(alternatives) == 1:
        status = STATUS_UNIQUE
    else:
        status = STATUS_AMBIGUOUS
    return SearchOutcome(
        status=status,
        complete=True,
        alternatives=alternatives,
        detail=None,
        incomplete_reasons=(),
    )
