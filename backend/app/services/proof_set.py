from dataclasses import dataclass
from typing import Tuple

from app.models import CandidateBundle, Payment
from app.services.candidate_retriever import retrieve_with_trace
from app.utils.loaders import Dataset


REASON_EMAIL_CAP = "email_cap"
REASON_CUSTOMER_CAP = "customer_cap"


@dataclass(frozen=True)
class ProofSet:
    prompt_bundle: CandidateBundle
    proof_bundle: CandidateBundle
    complete: bool
    incomplete_reasons: Tuple[str, ...]


def build_proof_set(payment: Payment, dataset: Dataset) -> ProofSet:
    prompt_bundle, trace = retrieve_with_trace(payment, dataset)
    invoices = list(trace.ranked_invoices)
    invoice_ids = {invoice.invoice_id for invoice in invoices}
    credits = list(trace.ranked_credits)
    credit_ids = {credit.credit_id for credit in credits}
    extra = [
        credit
        for credit in dataset.credits
        if credit.invoice_id in invoice_ids and credit.credit_id not in credit_ids
    ]
    credits += sorted(extra, key=lambda credit: credit.credit_id)
    reasons = []
    if trace.dropped_email_ids:
        reasons.append(REASON_EMAIL_CAP)
    if trace.dropped_strong_customer_ids:
        reasons.append(REASON_CUSTOMER_CAP)
    proof_bundle = CandidateBundle(
        payment=prompt_bundle.payment,
        candidate_customers=prompt_bundle.candidate_customers,
        candidate_invoices=invoices,
        candidate_credits=credits,
        candidate_emails=prompt_bundle.candidate_emails,
    )
    return ProofSet(prompt_bundle, proof_bundle, not reasons, tuple(reasons))
