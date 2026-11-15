"""Verifier-only evaluation baseline.

Decides a payment with the existing deterministic checks and no model: for
every financially valid allocation it asks the unchanged proof engine and
sufficiency gate whether that allocation would be authorized, and resolves
only when exactly one would. It is an evaluation baseline and is never
imported by the pipeline or the API.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from app.models import CandidateBundle, InvestigationProposal
from app.services.alternative_finder import find_valid_alternatives
from app.services.authorization import (
    REASON_MULTIPLE_AUTHORIZABLE,
    authorizable_allocations,
    canonical_proposal,
)


REASON_UNIQUE = "unique_authorizable_allocation"
REASON_NO_ALLOCATION = "no_financially_valid_allocation"
REASON_NONE_AUTHORIZABLE = "no_authorizable_allocation"


@dataclass(frozen=True)
class VerifierOnlyOutcome:
    payment_id: str
    decision: str
    reason: str
    alternatives_considered: int
    authorizable_allocation_ids: Tuple[str, ...]
    proposal: Optional[InvestigationProposal]


def verifier_only_decision(bundle: CandidateBundle) -> VerifierOnlyOutcome:
    alternatives = find_valid_alternatives(bundle)
    authorizable = authorizable_allocations(bundle, alternatives)

    selected: Optional[InvestigationProposal] = None
    if len(authorizable) == 1:
        decision, reason = "resolve", REASON_UNIQUE
        selected = authorizable[0][1]
    elif not alternatives:
        decision, reason = "abstain", REASON_NO_ALLOCATION
    elif not authorizable:
        decision, reason = "abstain", REASON_NONE_AUTHORIZABLE
    else:
        decision, reason = "abstain", REASON_MULTIPLE_AUTHORIZABLE

    return VerifierOnlyOutcome(
        payment_id=bundle.payment.payment_id,
        decision=decision,
        reason=reason,
        alternatives_considered=len(alternatives),
        authorizable_allocation_ids=tuple(
            alternative.allocation_id for alternative, _ in authorizable
        ),
        proposal=selected,
    )


class VerifierOnlyInvestigator:
    def __init__(self) -> None:
        self.outcomes: Dict[str, VerifierOnlyOutcome] = {}

    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        outcome = verifier_only_decision(bundle)
        self.outcomes[bundle.payment.payment_id] = outcome
        if outcome.proposal is not None:
            return outcome.proposal
        return InvestigationProposal(payment_id=bundle.payment.payment_id)
