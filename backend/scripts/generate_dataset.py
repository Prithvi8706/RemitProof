import argparse
import csv
import io
import json
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Sequence


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
DATA_ROOT = REPO_ROOT / "data"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.utils.atomic import atomic_write_text  # noqa: E402


PAYMENT_FIELDS = [
    "payment_id",
    "date",
    "amount",
    "currency",
    "payer_name",
    "bank_reference",
    "remittance_reference",
    "status",
]
INVOICE_FIELDS = [
    "invoice_id",
    "customer_id",
    "amount",
    "currency",
    "issue_date",
    "due_date",
    "description",
    "status",
    "allocated_payment_id",
]
CREDIT_FIELDS = [
    "credit_id",
    "customer_id",
    "invoice_id",
    "amount",
    "currency",
    "reason",
    "status",
    "consumed_by_payment_id",
]


RESOLVABLE_KINDS = {
    "detached_remittance_email",
    "credit_deduction",
    "multiple_allocations_email",
    "parent_entity_multi_invoice",
    "known_payer_disambiguated",
    "multi_invoice_remittance",
    "semantic_credit_reason",
    "treasury_bank_on_behalf",
    "alternative_allocation_email",
}


CASE_ORDER = [
    "detached_remittance_email",
    "same_amount_ambiguity",
    "credit_deduction",
    "conflicting_evidence",
    "multiple_allocations_email",
    "missing_credit_note",
    "parent_entity_multi_invoice",
    "uncertain_payer_relationship",
    "known_payer_disambiguated",
    "stale_or_duplicate_candidate",
    "multi_invoice_remittance",
    "unsupported_currency_or_short_pay",
    "semantic_credit_reason",
    "treasury_bank_on_behalf",
    "alternative_allocation_email",
] + [
    "detached_remittance_email",
    "same_amount_ambiguity",
    "credit_deduction",
    "conflicting_evidence",
    "multiple_allocations_email",
    "missing_credit_note",
    "parent_entity_multi_invoice",
    "uncertain_payer_relationship",
    "known_payer_disambiguated",
    "stale_or_duplicate_candidate",
    "multi_invoice_remittance",
    "unsupported_currency_or_short_pay",
    "semantic_credit_reason",
    "treasury_bank_on_behalf",
    "alternative_allocation_email",
]


COMPANY_ROOTS = [
    "Asteria Commerce",
    "Boreal Systems",
    "Cobalt Ridge",
    "Driftwood Analytics",
    "Evergreen Mobility",
    "Fableworks Media",
    "Granite Cloud",
    "Horizon Foods",
    "Indigo Networks",
    "Juniper Labs",
    "Keystone Retail",
    "Lattice Health",
    "Meridian Robotics",
    "Northwind Digital",
    "Oakline Software",
    "Pioneer Logistics",
    "Quartz Financial",
    "Redwood Energy",
    "Summit Learning",
    "Tidalwave Travel",
    "Umber Design",
    "Vector Manufacturing",
    "Westbridge Telecom",
    "Xenon Biotech",
    "Yellowfin Markets",
    "Zenith Operations",
    "Arcadia Studios",
    "Brightpath Security",
    "Copperleaf Foods",
    "Deepfield AI",
]


def partition_metadata(split: str) -> Dict[str, object]:
    return {
        "split": split,
        "partition_label": (
            "synthetic benchmark/regression partition"
            if split == "benchmark"
            else "synthetic development regression partition"
        ),
        "independent_held_out": False,
    }


def amount_text(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def make_customer(customer_id: str, legal_name: str) -> Dict[str, object]:
    return {
        "customer_id": customer_id,
        "legal_name": legal_name,
        "aliases": [legal_name.replace(" Ltd", ""), legal_name.replace(" Inc", "")],
        "parent_entities": [],
        "subsidiaries": [],
        "known_payers": [],
    }


def make_invoice(
    invoice_id: str,
    customer_id: str,
    amount: Decimal,
    currency: str,
    payment_date: date,
    description: str,
    status: str = "open",
    allocated_payment_id: str = "",
) -> Dict[str, str]:
    return {
        "invoice_id": invoice_id,
        "customer_id": customer_id,
        "amount": amount_text(amount),
        "currency": currency,
        "issue_date": (payment_date - timedelta(days=55)).isoformat(),
        "due_date": (payment_date - timedelta(days=25)).isoformat(),
        "description": description,
        "status": status,
        "allocated_payment_id": allocated_payment_id,
    }


def make_credit(
    credit_id: str,
    customer_id: str,
    invoice_id: str,
    amount: Decimal,
    currency: str,
    reason: str,
) -> Dict[str, str]:
    return {
        "credit_id": credit_id,
        "customer_id": customer_id,
        "invoice_id": invoice_id,
        "amount": amount_text(amount),
        "currency": currency,
        "reason": reason,
        "status": "valid",
        "consumed_by_payment_id": "",
    }


def build_easy_case(serial: int) -> Dict[str, object]:
    payment_id = f"PAY_{serial:03d}"
    customer_id = f"CUS_E{serial:03d}"
    invoice_id = f"INV_E{serial:03d}"
    root = COMPANY_ROOTS[(serial - 1) % len(COMPANY_ROOTS)]
    legal_name = f"{root} {serial:02d} Ltd"
    customer = make_customer(customer_id, legal_name)
    payer_name = legal_name
    if serial % 5 == 0:
        alias = f"{root} {serial:02d}"
        customer["aliases"] = [alias]
        payer_name = alias
    elif serial % 7 == 0:
        payer_name = f"{root} Global Treasury {serial:02d}"
        customer["known_payers"] = [payer_name]

    payment_date = date(2026, 8, 1) + timedelta(days=(serial - 1) % 27)
    amount = Decimal("2100.00") + Decimal(serial * 137)
    currency = "EUR" if serial % 4 == 0 else "USD"
    payment = {
        "payment_id": payment_id,
        "date": payment_date.isoformat(),
        "amount": amount_text(amount),
        "currency": currency,
        "payer_name": payer_name,
        "bank_reference": f"BNK-E-{serial:05d}",
        "remittance_reference": invoice_id,
        "status": "unmatched",
    }
    invoice = make_invoice(
        invoice_id,
        customer_id,
        amount,
        currency,
        payment_date,
        "Monthly software and support services",
    )
    truth = {
        "payment_id": payment_id,
        "exception_class": "conventional_exact_reference",
        "correct_customer": customer_id,
        "correct_invoices": [invoice_id],
        "correct_credits": [],
        "should_resolve": True,
        "required_evidence": [customer_id, invoice_id],
        "required_retrieval_ids": [customer_id, invoice_id],
        "expected_reason": "Explicit invoice reference, supported payer identity, currency, and amount agree.",
        "is_exception": False,
        **partition_metadata("dev" if serial <= 10 else "benchmark"),
    }
    return {
        "payment": payment,
        "customers": [customer],
        "invoices": [invoice],
        "credits": [],
        "emails": [],
        "truth": truth,
    }


def build_resolvable_exception(serial: int, kind: str, occurrence: int) -> Dict[str, object]:
    payment_id = f"PAY_{serial:03d}"
    customer_id = f"CUS_X{serial:03d}"
    root = COMPANY_ROOTS[(serial + 7) % len(COMPANY_ROOTS)]
    legal_name = f"{root} International Ltd"
    customer = make_customer(customer_id, legal_name)
    payment_date = date(2026, 8, 1) + timedelta(days=(serial - 1) % 27)
    currency = "EUR" if serial % 6 == 0 else "USD"
    bank_reference = f"BNK-X-{serial:05d}"
    base_payment = Decimal("9000.00") + Decimal(serial * 113)
    uses_credit = kind in {"credit_deduction", "semantic_credit_reason", "parent_entity_multi_invoice"}
    credit_amount = Decimal("350.00") + Decimal(occurrence * 25) if uses_credit else Decimal("0.00")
    invoice_total = base_payment + credit_amount
    first_amount = (invoice_total * Decimal("0.56")).quantize(Decimal("0.01"))
    second_amount = invoice_total - first_amount
    alternative_first = (base_payment * Decimal("0.63")).quantize(Decimal("0.01"))
    alternative_second = base_payment - alternative_first

    invoice_ids = [f"INV_X{serial:03d}A", f"INV_X{serial:03d}B"]
    alternative_ids = [f"INV_X{serial:03d}C", f"INV_X{serial:03d}D"]
    invoices = [
        make_invoice(invoice_ids[0], customer_id, first_amount, currency, payment_date, "Platform subscription"),
        make_invoice(invoice_ids[1], customer_id, second_amount, currency, payment_date, "Implementation services"),
        make_invoice(alternative_ids[0], customer_id, alternative_first, currency, payment_date, "Legacy integration"),
        make_invoice(alternative_ids[1], customer_id, alternative_second, currency, payment_date, "Support retainer"),
    ]

    payer_name = legal_name
    relationship_sentence = ""
    if kind in {"detached_remittance_email", "treasury_bank_on_behalf"}:
        payer_name = f"CITIBANK N.A. OBO {root.upper()}"
        relationship_sentence = (
            f"Payment {bank_reference} was sent by our treasury bank, Citibank N.A., "
            f"on behalf of {legal_name}. "
        )
    elif kind == "parent_entity_multi_invoice":
        payer_name = f"{root.upper()} GLOBAL HOLDINGS LLC"
        customer["parent_entities"] = [payer_name]
        relationship_sentence = f"{payer_name} sent this payment for {legal_name}. "
    elif kind == "known_payer_disambiguated":
        payer_name = f"{root.upper()} TREASURY SERVICES LTD"
        customer["known_payers"] = [payer_name]

    credits = []
    credit_ids: List[str] = []
    credit_sentence = ""
    if uses_credit:
        selected_credit_id = f"CR_X{serial:03d}A"
        distractor_credit_id = f"CR_X{serial:03d}B"
        credits = [
            make_credit(
                selected_credit_id,
                customer_id,
                invoice_ids[1],
                credit_amount,
                currency,
                "Approved SLA service credit" if kind != "semantic_credit_reason" else "Launch delay rebate",
            ),
            make_credit(
                distractor_credit_id,
                customer_id,
                invoice_ids[1],
                credit_amount,
                currency,
                "Disputed quality adjustment",
            ),
        ]
        credit_ids = [selected_credit_id]
        credit_sentence = (
            f" Deduct the approved {currency} {amount_text(credit_amount)} credit {selected_credit_id}; "
            "do not use the disputed adjustment."
        )

    email_id = f"EMAIL_X{serial:03d}"
    body = (
        relationship_sentence
        + f"Apply the {currency} {amount_text(base_payment)} receipt only to "
        + f"{invoice_ids[0]} and {invoice_ids[1]}. "
        + "The other open invoices will be paid separately."
        + credit_sentence
    )
    email = {
        "email_id": email_id,
        "sender": f"controller{serial}@{root.lower().replace(' ', '')}.example",
        "customer_id": customer_id,
        "date": (payment_date - timedelta(days=1)).isoformat(),
        "subject": f"Remittance {bank_reference}",
        "body": body,
    }
    payment = {
        "payment_id": payment_id,
        "date": payment_date.isoformat(),
        "amount": amount_text(base_payment),
        "currency": currency,
        "payer_name": payer_name,
        "bank_reference": bank_reference,
        "remittance_reference": "",
        "status": "unmatched",
    }
    required_evidence = [email_id, customer_id]
    required_evidence.extend(credit_ids)
    required_retrieval_ids = [
        customer_id,
        *(invoice["invoice_id"] for invoice in invoices),
        *(credit["credit_id"] for credit in credits),
        email_id,
    ]
    truth = {
        "payment_id": payment_id,
        "exception_class": kind,
        "correct_customer": customer_id,
        "correct_invoices": invoice_ids,
        "correct_credits": credit_ids,
        "should_resolve": True,
        "required_evidence": required_evidence,
        "required_retrieval_ids": required_retrieval_ids,
        "expected_reason": "Remittance evidence uniquely selects one financially valid allocation.",
        "is_exception": True,
        **partition_metadata("dev" if serial <= 60 else "benchmark"),
    }
    return {
        "payment": payment,
        "customers": [customer],
        "invoices": invoices,
        "credits": credits,
        "emails": [email],
        "truth": truth,
    }


def build_abstention_exception(serial: int, kind: str, occurrence: int) -> Dict[str, object]:
    payment_id = f"PAY_{serial:03d}"
    customer_id = f"CUS_X{serial:03d}"
    root = COMPANY_ROOTS[(serial + 7) % len(COMPANY_ROOTS)]
    legal_name = f"{root} International Ltd"
    customer = make_customer(customer_id, legal_name)
    payment_date = date(2026, 8, 1) + timedelta(days=(serial - 1) % 27)
    currency = "USD"
    bank_reference = f"BNK-X-{serial:05d}"
    payment_amount = Decimal("6500.00") + Decimal(serial * 97)
    payer_name = legal_name
    invoices: List[Dict[str, str]] = []
    credits: List[Dict[str, str]] = []
    emails: List[Dict[str, str]] = []
    expected_reason = "Available evidence is insufficient for a unique safe allocation."

    if kind == "same_amount_ambiguity":
        invoices = [
            make_invoice(f"INV_X{serial:03d}A", customer_id, payment_amount, currency, payment_date, "Region A services"),
            make_invoice(f"INV_X{serial:03d}B", customer_id, payment_amount, currency, payment_date, "Region B services"),
        ]
        expected_reason = "Two same-amount invoices remain and no remittance instruction disambiguates them."
    elif kind == "conflicting_evidence":
        invoice_id = f"INV_X{serial:03d}A"
        credit_id = f"CR_X{serial:03d}A"
        credit_amount = Decimal("350.00")
        invoices = [
            make_invoice(invoice_id, customer_id, payment_amount + credit_amount, currency, payment_date, "Network retainer")
        ]
        credits = [
            make_credit(credit_id, customer_id, invoice_id, credit_amount, currency, "SLA service credit")
        ]
        claimed_amount = credit_amount + Decimal("150.00")
        emails = [
            {
                "email_id": f"EMAIL_X{serial:03d}",
                "sender": f"ap{serial}@conflict.example",
                "customer_id": customer_id,
                "date": (payment_date - timedelta(days=1)).isoformat(),
                "subject": f"Conflicting remittance {bank_reference}",
                "body": (
                    f"For {bank_reference}, apply payment to {invoice_id}. We deducted a USD "
                    f"{amount_text(claimed_amount)} credit under {credit_id}."
                ),
            }
        ]
        expected_reason = "The remittance credit amount conflicts with the valid credit note."
    elif kind == "missing_credit_note":
        invoice_id = f"INV_X{serial:03d}A"
        missing_credit_id = f"CR_X{serial:03d}A"
        invoices = [
            make_invoice(invoice_id, customer_id, payment_amount + Decimal("200.00"), currency, payment_date, "Quality program")
        ]
        emails = [
            {
                "email_id": f"EMAIL_X{serial:03d}",
                "sender": f"finance{serial}@missing.example",
                "customer_id": customer_id,
                "date": (payment_date - timedelta(days=1)).isoformat(),
                "subject": f"Short payment {bank_reference}",
                "body": (
                    f"Apply {bank_reference} to {invoice_id} after our USD 200 credit {missing_credit_id}. "
                    "Please send the credit note copy."
                ),
            }
        ]
        expected_reason = "A deduction is claimed but the required valid credit note is absent."
    elif kind == "uncertain_payer_relationship":
        payer_name = "UNKNOWN ORIGINATOR" if occurrence == 2 else "HARBOR BRIDGE SERVICES"
        invoices = [
            make_invoice(f"INV_X{serial:03d}A", customer_id, payment_amount, currency, payment_date, "Advisory services")
        ]
        expected_reason = "No customer record or remittance evidence supports the payer relationship."
    elif kind == "stale_or_duplicate_candidate":
        invoice_id = f"INV_X{serial:03d}A"
        if occurrence == 1:
            invoices = [
                make_invoice(invoice_id, customer_id, payment_amount, currency, payment_date, "Closed implementation", status="closed")
            ]
            expected_reason = "The only proposed invoice is closed."
        else:
            invoices = [
                make_invoice(
                    invoice_id,
                    customer_id,
                    payment_amount,
                    currency,
                    payment_date,
                    "Previously allocated support",
                    allocated_payment_id="PAY_PREVIOUS",
                )
            ]
            expected_reason = "The invoice already has an allocation, creating duplicate risk."
        emails = [
            {
                "email_id": f"EMAIL_X{serial:03d}",
                "sender": f"ap{serial}@stale.example",
                "customer_id": customer_id,
                "date": (payment_date - timedelta(days=1)).isoformat(),
                "subject": f"Remittance {bank_reference}",
                "body": f"Please apply {bank_reference} to {invoice_id}.",
            }
        ]
    elif kind == "unsupported_currency_or_short_pay":
        invoice_id = f"INV_X{serial:03d}A"
        if occurrence == 1:
            invoices = [
                make_invoice(invoice_id, customer_id, payment_amount, "EUR", payment_date, "EUR consulting invoice")
            ]
            expected_reason = "Payment and invoice currencies differ; FX is outside MVP scope."
        else:
            invoices = [
                make_invoice(invoice_id, customer_id, payment_amount + Decimal("125.00"), currency, payment_date, "Unexplained short pay")
            ]
            expected_reason = "The short payment has no credit note or remittance explanation."
    else:
        raise ValueError(f"Unsupported abstention kind: {kind}")

    remittance_reference = ""
    if kind == "unsupported_currency_or_short_pay" and occurrence == 1:
        remittance_reference = invoices[0]["invoice_id"]
    payment = {
        "payment_id": payment_id,
        "date": payment_date.isoformat(),
        "amount": amount_text(payment_amount),
        "currency": currency,
        "payer_name": payer_name,
        "bank_reference": bank_reference,
        "remittance_reference": remittance_reference,
        "status": "unmatched",
    }
    truth = {
        "payment_id": payment_id,
        "exception_class": kind,
        "correct_customer": customer_id,
        "correct_invoices": [],
        "correct_credits": [],
        "should_resolve": False,
        "required_evidence": [email["email_id"] for email in emails],
        "required_retrieval_ids": [
            customer_id,
            *(invoice["invoice_id"] for invoice in invoices),
            *(credit["credit_id"] for credit in credits),
            *(email["email_id"] for email in emails),
        ],
        "expected_reason": expected_reason,
        "is_exception": True,
        **partition_metadata("dev" if serial <= 60 else "benchmark"),
    }
    return {
        "payment": payment,
        "customers": [customer],
        "invoices": invoices,
        "credits": credits,
        "emails": emails,
        "truth": truth,
    }


def build_dataset() -> List[Dict[str, object]]:
    cases = [build_easy_case(serial) for serial in range(1, 51)]
    occurrences: Dict[str, int] = {}
    for offset, kind in enumerate(CASE_ORDER, start=51):
        occurrences[kind] = occurrences.get(kind, 0) + 1
        occurrence = occurrences[kind]
        if kind in RESOLVABLE_KINDS:
            case = build_resolvable_exception(offset, kind, occurrence)
        else:
            case = build_abstention_exception(offset, kind, occurrence)
        cases.append(case)
    return cases


def _write_csv(path: Path, rows: Sequence[Dict[str, object]], fieldnames: List[str]) -> None:
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write_text(path, handle.getvalue())


def _write_jsonl(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    content = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows)
    atomic_write_text(path, content)


def write_partition(target: Path, cases: Sequence[Dict[str, object]]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    payments = [case["payment"] for case in cases]
    invoices = [invoice for case in cases for invoice in case["invoices"]]
    customers = [customer for case in cases for customer in case["customers"]]
    credits = [credit for case in cases for credit in case["credits"]]
    emails = [email for case in cases for email in case["emails"]]
    truth = [case["truth"] for case in cases]

    _write_csv(target / "payments.csv", payments, PAYMENT_FIELDS)
    _write_csv(target / "invoices.csv", invoices, INVOICE_FIELDS)
    _write_csv(target / "credits.csv", credits, CREDIT_FIELDS)
    atomic_write_text(target / "customers.json", json.dumps(customers, indent=2) + "\n")
    _write_jsonl(target / "emails.jsonl", emails)
    atomic_write_text(target / "ground_truth.json", json.dumps(truth, indent=2) + "\n")


def write_ground_truth_partition(
    target: Path, cases: Sequence[Dict[str, object]]
) -> None:
    truth = [case["truth"] for case in cases]
    atomic_write_text(target / "ground_truth.json", json.dumps(truth, indent=2) + "\n")


def validate_dataset(cases: Sequence[Dict[str, object]]) -> None:
    assert len(cases) == 80
    assert sum(not case["truth"]["is_exception"] for case in cases) == 50
    assert sum(case["truth"]["is_exception"] for case in cases) == 30
    assert sum(case["truth"]["split"] == "dev" for case in cases) == 20
    assert sum(case["truth"]["split"] == "benchmark" for case in cases) == 60
    assert sum(case["truth"]["should_resolve"] for case in cases if case["truth"]["is_exception"]) == 18
    assert len({case["payment"]["payment_id"] for case in cases}) == 80
    for case in cases:
        existing_ids = {
            *(record["customer_id"] for record in case["customers"]),
            *(record["invoice_id"] for record in case["invoices"]),
            *(record["credit_id"] for record in case["credits"]),
            *(record["email_id"] for record in case["emails"]),
        }
        assert set(case["truth"]["required_retrieval_ids"]) == existing_ids
        assert case["truth"]["independent_held_out"] is False


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic regression corpus.")
    parser.add_argument(
        "--ground-truth-only",
        action="store_true",
        help="Refresh only evaluation truth files, leaving source-record fixtures unchanged.",
    )
    arguments = parser.parse_args()
    cases = build_dataset()
    validate_dataset(cases)
    partitions = {
        DATA_ROOT: cases,
        DATA_ROOT / "dev": [
            case for case in cases if case["truth"]["split"] == "dev"
        ],
        DATA_ROOT / "benchmark": [
            case for case in cases if case["truth"]["split"] == "benchmark"
        ],
    }
    for target, partition_cases in partitions.items():
        if arguments.ground_truth_only:
            write_ground_truth_partition(target, partition_cases)
        else:
            write_partition(target, partition_cases)
    mode = "ground truth" if arguments.ground_truth_only else "all fixtures"
    print(
        f"Generated {mode} for 80 synthetic records: 50 conventional, "
        "30 exceptions; 20 development regression, 60 benchmark/regression."
    )


if __name__ == "__main__":
    main()
