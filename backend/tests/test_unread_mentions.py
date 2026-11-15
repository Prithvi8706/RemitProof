import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from app.utils.loaders import load_dataset
from app.utils.remittance_semantics import DocumentSemantics, classify_document_semantics


ROOT = Path(__file__).resolve().parents[2]

PINNED_FIELDS = [
    "affirmative_invoice_ids", "affirmative_credit_ids", "prohibited_invoice_ids",
    "prohibited_credit_ids", "noncurrent_invoice_ids",
    "affirmative_credit_amounts", "prohibited_credit_amounts",
]
LEGACY_READER_SHA256 = "4a4473d8a7a6f659f1e205b7d0aa5a26b47d58e63d1b1b9ba0b4c4f0211775fc"


def test_unread_ids_is_the_last_field_and_defaults_to_empty():
    assert [f.name for f in dataclasses.fields(DocumentSemantics)] == PINNED_FIELDS + [
        "unread_ids"
    ]
    assert DocumentSemantics().unread_ids == set()


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "This transfer settles INV_C in full. We will use a separate transfer "
            "for INV_A and INV_B next month.",
            {"INV_C"},
        ),
        (
            "This transfer clears INV_C. INV_A and INV_B are booked for our next "
            "payment run.",
            {"INV_C"},
        ),
        (
            "Today's wire covers INV_C only. Please post INV_A and INV_B to the vendor "
            "portal so we can approve them.",
            {"INV_C"},
        ),
        ("CR_1 relates to the March delivery.", {"CR_1"}),
        ("INV_A is not included in this payment.", {"INV_A"}),
    ],
)
def test_ids_in_an_unclassified_clause_are_unread(text, expected):
    assert classify_document_semantics(text).unread_ids == expected


@pytest.mark.parametrize(
    "text",
    [
        "Please apply this payment to INV_A.",
        "Do not apply this payment to INV_A.",
        "INV_A was paid last month.",
        "Deduct credit CR_1 from INV_A.",
        "Payment advice attached.",
        "",
        "We will use a separate transfer for INV_A and INV_B next month.",
    ],
)
def test_ids_in_a_classified_clause_are_not_unread(text):
    assert classify_document_semantics(text).unread_ids == set()


def test_the_rule_is_per_clause_not_per_document():
    semantics = classify_document_semantics(
        "Apply BNK-1 only to INV_A and INV_B. INV_A is the June invoice."
    )

    assert semantics.affirmative_invoice_ids == {"INV_A", "INV_B"}
    assert semantics.unread_ids == {"INV_A"}


def test_bare_reference_mode_never_reports_unread_ids():
    semantics = classify_document_semantics(
        "This transfer settles INV_C in full.", bare_references_are_affirmative=True
    )

    assert semantics.affirmative_invoice_ids == {"INV_C"}
    assert semantics.unread_ids == set()


def test_no_legacy_email_has_an_unread_id():
    dataset = load_dataset(ROOT / "data")

    assert len(dataset.emails) == 24
    for email in dataset.emails:
        semantics = classify_document_semantics(f"{email.subject} {email.body}")
        assert semantics.unread_ids == set(), email.email_id


def test_the_other_reader_fields_are_unchanged_on_the_legacy_corpus():
    dataset = load_dataset(ROOT / "data")
    pairs = [
        (email.email_id, f"{email.subject} {email.body}")
        for email in sorted(dataset.emails, key=lambda item: item.email_id)
    ] + [
        (
            payment.payment_id,
            " ".join([payment.bank_reference, payment.remittance_reference]),
        )
        for payment in sorted(dataset.payments, key=lambda item: item.payment_id)
    ]

    rows = []
    for label, text in pairs:
        for bare in (False, True):
            semantics = classify_document_semantics(
                text, bare_references_are_affirmative=bare
            )
            row = {"label": label, "bare": bare}
            for name in PINNED_FIELDS:
                row[name] = sorted(str(value) for value in getattr(semantics, name))
            rows.append(row)

    assert len(rows) == 208
    assert (
        hashlib.sha256(
            json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        == LEGACY_READER_SHA256
    )
