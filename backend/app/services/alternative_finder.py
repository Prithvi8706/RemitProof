from itertools import combinations
from typing import Iterable, List, Optional, Sequence, Tuple

from app.models import AlternativeAllocation, CandidateBundle
from app.models.payment import is_valid_monetary_amount
from app.utils.money import money_sum


def _subsets(
    items: Sequence[object],
    maximum_size: Optional[int] = None,
) -> Iterable[Tuple[object, ...]]:
    upper_bound = len(items) if maximum_size is None else min(len(items), maximum_size)
    for size in range(1, upper_bound + 1):
        yield from combinations(items, size)


def _credits_fit_linked_invoices(invoice_group, credit_group) -> bool:
    invoice_amounts = {invoice.invoice_id: invoice.amount for invoice in invoice_group}
    for invoice_id, invoice_amount in invoice_amounts.items():
        applied_credit = money_sum(
            credit.amount for credit in credit_group if credit.invoice_id == invoice_id
        )
        if applied_credit > invoice_amount:
            return False
    return True


def find_valid_alternatives(bundle: CandidateBundle) -> List[AlternativeAllocation]:
    """Enumerate financially valid allocations from the narrowed candidate set.

    Candidate retrieval keeps this bounded (at most eight invoices and three
    credits), making exhaustive subset checks both clearer and safer than an
    approximate optimizer for the MVP.
    """

    payment = bundle.payment
    if not is_valid_monetary_amount(payment.amount):
        return []

    open_invoices = [
        invoice
        for invoice in bundle.candidate_invoices
        if invoice.status == "open"
        and invoice.allocated_payment_id is None
        and invoice.currency == payment.currency
        and invoice.issue_date <= payment.date
        and is_valid_monetary_amount(invoice.amount)
    ]
    valid_credits = [
        credit
        for credit in bundle.candidate_credits
        if credit.status == "valid"
        and credit.consumed_by_payment_id is None
        and credit.currency == payment.currency
        and is_valid_monetary_amount(credit.amount)
    ]
    alternatives = []
    seen = set()

    customer_ids = sorted({invoice.customer_id for invoice in open_invoices})
    for customer_id in customer_ids:
        customer_invoices = [invoice for invoice in open_invoices if invoice.customer_id == customer_id]
        customer_credits = [credit for credit in valid_credits if credit.customer_id == customer_id]
        credit_choices = [tuple()]
        credit_choices.extend(_subsets(customer_credits, maximum_size=3))

        # Retrieval bounds this set to eight invoices, so all 255 non-empty
        # subsets are cheap enough to enumerate. A smaller silent cap can turn
        # a real multi-invoice alternative into a false uniqueness proof.
        for invoice_group_raw in _subsets(customer_invoices):
            invoice_group = tuple(invoice_group_raw)
            invoice_ids = {invoice.invoice_id for invoice in invoice_group}
            for credit_group_raw in credit_choices:
                credit_group = tuple(credit_group_raw)
                if any(credit.invoice_id not in invoice_ids for credit in credit_group):
                    continue
                if not _credits_fit_linked_invoices(invoice_group, credit_group):
                    continue

                calculated = money_sum(invoice.amount for invoice in invoice_group) - money_sum(
                    credit.amount for credit in credit_group
                )
                if calculated != payment.amount:
                    continue

                invoice_key = tuple(sorted(invoice.invoice_id for invoice in invoice_group))
                credit_key = tuple(sorted(credit.credit_id for credit in credit_group))
                key = (customer_id, invoice_key, credit_key)
                if key in seen:
                    continue
                seen.add(key)
                alternatives.append(
                    AlternativeAllocation(
                        customer_id=customer_id,
                        invoice_ids=list(invoice_key),
                        credit_ids=list(credit_key),
                        calculated_total=calculated,
                    )
                )

    ordered = sorted(
        alternatives,
        key=lambda alternative: (
            alternative.customer_id,
            alternative.invoice_ids,
            alternative.credit_ids,
        ),
    )
    return [
        alternative.model_copy(update={"allocation_id": f"ALT_{index:03d}"})
        for index, alternative in enumerate(ordered, start=1)
    ]
