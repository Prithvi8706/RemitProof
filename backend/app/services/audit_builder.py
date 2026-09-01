from typing import Dict, List

from app.models import CandidateBundle, InvestigationProposal


def build_evidence_records(bundle: CandidateBundle) -> Dict[str, Dict[str, object]]:
    """Build the complete evidence index for the candidate bundle.

    The proposal controls which records are cited, but every candidate record
    must have a serializable audit representation before citations are selected.
    Keeping the index complete prevents valid invoice citations from being
    silently discarded alongside the records that were already supported.
    """
    records: Dict[str, Dict[str, object]] = {}
    for customer in bundle.candidate_customers:
        records[customer.customer_id] = {
            "evidence_id": customer.customer_id,
            "evidence_type": "customer_record",
            "title": customer.legal_name,
            "content": {
                "aliases": customer.aliases,
                "parent_entities": customer.parent_entities,
                "known_payers": customer.known_payers,
            },
        }
    for invoice in bundle.candidate_invoices:
        records[invoice.invoice_id] = {
            "evidence_id": invoice.invoice_id,
            "evidence_type": "invoice_record",
            "title": invoice.description,
            "content": {
                "customer_id": invoice.customer_id,
                "amount": str(invoice.amount),
                "currency": invoice.currency,
                "issue_date": invoice.issue_date.isoformat(),
                "due_date": invoice.due_date.isoformat(),
                "status": invoice.status,
                "allocated_payment_id": invoice.allocated_payment_id,
            },
        }
    for email in bundle.candidate_emails:
        records[email.email_id] = {
            "evidence_id": email.email_id,
            "evidence_type": "remittance_email",
            "title": email.subject,
            "content": email.body,
            "sender": email.sender,
            "date": email.date.isoformat(),
        }
    for credit in bundle.candidate_credits:
        records[credit.credit_id] = {
            "evidence_id": credit.credit_id,
            "evidence_type": "credit_note",
            "title": credit.reason,
            "content": {
                "amount": str(credit.amount),
                "currency": credit.currency,
                "status": credit.status,
                "invoice_id": credit.invoice_id,
            },
        }
    return records


def build_allocation(
    bundle: CandidateBundle,
    proposal: InvestigationProposal,
) -> List[Dict[str, object]]:
    invoices_by_id = {invoice.invoice_id: invoice for invoice in bundle.candidate_invoices}
    credits_by_id = {credit.credit_id: credit for credit in bundle.candidate_credits}
    rows: List[Dict[str, object]] = []
    for invoice_id in proposal.invoice_ids:
        invoice = invoices_by_id.get(invoice_id)
        if invoice:
            rows.append(
                {
                    "record_type": "invoice",
                    "record_id": invoice.invoice_id,
                    "description": invoice.description,
                    "amount": str(invoice.amount),
                    "currency": invoice.currency,
                    "operator": "+",
                }
            )
    for credit_id in proposal.credit_ids:
        credit = credits_by_id.get(credit_id)
        if credit:
            rows.append(
                {
                    "record_type": "credit",
                    "record_id": credit.credit_id,
                    "description": credit.reason,
                    "amount": str(credit.amount),
                    "currency": credit.currency,
                    "operator": "-",
                }
            )
    return rows


def build_evidence(
    bundle: CandidateBundle,
    proposal: InvestigationProposal,
) -> List[Dict[str, object]]:
    records = build_evidence_records(bundle)
    requested_ids = list(dict.fromkeys(proposal.evidence_ids))

    # Allocation and entity records are required for a useful audit even when
    # the model cited only the email that describes them. Claim citations are
    # included as well so an inconsistent proposal cannot cause valid evidence
    # to disappear from the returned audit payload.
    required_ids = [
        proposal.proposed_customer,
        *proposal.invoice_ids,
        *proposal.credit_ids,
        *(evidence_id for claim in proposal.semantic_claims for evidence_id in claim.evidence_ids),
    ]
    for evidence_id in required_ids:
        if evidence_id and evidence_id not in requested_ids:
            requested_ids.append(evidence_id)

    cited_ids = set(proposal.evidence_ids)
    return [
        {
            **records[evidence_id],
            "evidence_role": (
                "model_citation" if evidence_id in cited_ids else "audit_context"
            ),
        }
        for evidence_id in requested_ids
        if evidence_id in records
    ]
