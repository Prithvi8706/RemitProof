import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.models import Credit, Customer, Invoice, Payment, RemittanceEmail


@dataclass(frozen=True)
class Dataset:
    payments: List[Payment]
    invoices: List[Invoice]
    customers: List[Customer]
    credits: List[Credit]
    emails: List[RemittanceEmail]

    @property
    def payments_by_id(self) -> Dict[str, Payment]:
        return {payment.payment_id: payment for payment in self.payments}


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _none_if_blank(value: Optional[str]) -> Optional[str]:
    return value if value else None


def _require_unique_ids(records: List[object], id_field: str, record_type: str) -> None:
    seen = set()
    duplicates = set()
    for record in records:
        record_id = getattr(record, id_field)
        if record_id in seen:
            duplicates.add(record_id)
        seen.add(record_id)
    if duplicates:
        duplicate_list = ", ".join(sorted(duplicates))
        raise ValueError(f"duplicate {record_type} identifiers: {duplicate_list}")


def _validate_relationships(dataset: Dataset) -> None:
    customer_ids = {customer.customer_id for customer in dataset.customers}
    invoice_by_id = {invoice.invoice_id: invoice for invoice in dataset.invoices}

    # Historical allocation/consumption IDs may point to payments outside this
    # extract. Their presence still makes records ineligible for new matching,
    # but source integrity does not require those historical payments locally.

    for payment in dataset.payments:
        if (
            payment.allocated_customer_id is not None
            and payment.allocated_customer_id not in customer_ids
        ):
            raise ValueError(
                f"payment {payment.payment_id} references unknown customer "
                f"{payment.allocated_customer_id}"
            )

    for invoice in dataset.invoices:
        if invoice.customer_id not in customer_ids:
            raise ValueError(
                f"invoice {invoice.invoice_id} references unknown customer {invoice.customer_id}"
            )

    for credit in dataset.credits:
        if credit.customer_id not in customer_ids:
            raise ValueError(
                f"credit {credit.credit_id} references unknown customer {credit.customer_id}"
            )
        invoice = invoice_by_id.get(credit.invoice_id)
        if invoice is None:
            raise ValueError(
                f"credit {credit.credit_id} references unknown invoice {credit.invoice_id}"
            )
        if invoice.customer_id != credit.customer_id:
            raise ValueError(
                f"credit {credit.credit_id} customer {credit.customer_id} does not match "
                f"invoice {credit.invoice_id} customer {invoice.customer_id}"
            )

    for email in dataset.emails:
        if email.customer_id not in customer_ids:
            raise ValueError(
                f"email {email.email_id} references unknown customer {email.customer_id}"
            )


def load_dataset(data_dir: Path) -> Dataset:
    payments = []
    for row in _read_csv(data_dir / "payments.csv"):
        row["allocated_customer_id"] = _none_if_blank(row.get("allocated_customer_id"))
        payments.append(Payment.model_validate(row))

    invoices = []
    for row in _read_csv(data_dir / "invoices.csv"):
        row["allocated_payment_id"] = _none_if_blank(row.get("allocated_payment_id"))
        invoices.append(Invoice.model_validate(row))

    credits = []
    for row in _read_csv(data_dir / "credits.csv"):
        row["consumed_by_payment_id"] = _none_if_blank(row.get("consumed_by_payment_id"))
        credits.append(Credit.model_validate(row))

    customers = [
        Customer.model_validate(item)
        for item in json.loads((data_dir / "customers.json").read_text(encoding="utf-8"))
    ]
    emails = []
    with (data_dir / "emails.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                emails.append(RemittanceEmail.model_validate_json(line))

    dataset = Dataset(
        payments=payments,
        invoices=invoices,
        customers=customers,
        credits=credits,
        emails=emails,
    )
    _require_unique_ids(dataset.payments, "payment_id", "payment")
    _require_unique_ids(dataset.invoices, "invoice_id", "invoice")
    _require_unique_ids(dataset.customers, "customer_id", "customer")
    _require_unique_ids(dataset.credits, "credit_id", "credit")
    _require_unique_ids(dataset.emails, "email_id", "email")
    _validate_relationships(dataset)
    return dataset


def load_ground_truth(data_dir: Path) -> List[Dict[str, object]]:
    """Evaluation-only loader. Runtime retrieval and investigation never call it."""

    return json.loads((data_dir / "ground_truth.json").read_text(encoding="utf-8"))
