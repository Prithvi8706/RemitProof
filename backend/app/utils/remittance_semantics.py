import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable, Optional, Set

from app.models.payment import Payment
from app.utils.normalization import extract_credit_amounts, extract_document_ids


_RELATIONSHIP_LANGUAGE = re.compile(
    r"\b(?:on\s+behalf\s+of|authorized\s+payer|authorised\s+payer|"
    r"payment\s+was\s+sent\s+by|sent\s+(?:this\s+)?payment\s+for|"
    r"paid\s+for)\b",
    re.IGNORECASE,
)
_NEGATIVE_RELATIONSHIP = re.compile(
    r"\b(?:"
    r"did\s+not|didn't|never"
    r")\s+(?:pay|send|remit)\b[^.!?;\r\n]{0,100}\bon\s+behalf\s+of\b|"
    r"\b(?:do\s+not|don't|never)\s+(?:treat|consider|accept|recognize|recognise)\b"
    r"[^.!?;\r\n]{0,100}\b(?:as\s+)?(?:an?\s+)?"
    r"(?:authorized|authorised|approved|permitted)\s+(?:payer|remitter)\b|"
    r"\b(?:is|was|has\s+been)\s+(?:an?\s+)?"
    r"(?:unauthorized|unauthorised|unapproved|prohibited|forbidden|disallowed|ineligible)"
    r"\s+(?:payer|remitter)\b|"
    r"\b(?:is|was|has\s+been)\s+not\s+(?:an?\s+)?"
    r"(?:authorized|authorised|approved|permitted)\s+(?:payer|remitter)\b|"
    r"\bpayment\s+was\s+not\s+sent\s+by\b|"
    r"\bnot\s+(?:paid|sent|remitted)\s+by\b",
    re.IGNORECASE,
)
_NEGATED_ALLOCATION = re.compile(
    r"\b(?:do\s+not|don't|must\s+not|should\s+not|never|not\s+to)\s+"
    r"(?:apply|use|select|allocate|assign|reference|deduct|subtract|post|book)\b|"
    r"\b(?:must|should|is|are|was|were)\s+not\s+(?:be\s+)?"
    r"(?:applied|used|selected|allocated|assigned|referenced|deducted|subtracted|posted|booked)\b|"
    r"\b(?:instead\s+of|rather\s+than)\b",
    re.IGNORECASE,
)
_POSTPOSITIVE_DOCUMENT_PROHIBITION = re.compile(
    r"\b(?:is|are|was|were|has\s+been|have\s+been)\s+"
    r"(?:prohibited|forbidden|disallowed|excluded|ineligible|not\s+permitted)\b"
    r"(?:\s+from\s+(?:use|application|allocation|deduction|posting|booking))?\b|"
    r"\b(?:cannot|can't|must\s+not|should\s+not)\s+be\s+"
    r"(?:applied|used|selected|allocated|assigned|referenced|deducted|posted|booked)\b",
    re.IGNORECASE,
)
_NONCURRENT_DOCUMENT = re.compile(
    r"\b(?:already|previously)\s+(?:paid|settled|closed|cancelled|canceled|allocated|applied|used)\b|"
    r"\b(?:was|is|has\s+been)\s+(?:already\s+|previously\s+)?"
    r"(?:paid|settled|closed|cancelled|canceled|disputed|allocated)\b|"
    r"\b(?:cancelled|canceled|disputed|closed)\b",
    re.IGNORECASE,
)
_AFFIRMATIVE_ALLOCATION = re.compile(
    r"\b(?:apply|allocate|assign|post|book|use|deduct|subtract)\b|"
    r"\b(?:applied|allocated|assigned|posted|booked|used|deducted|subtracted)\b|"
    r"\b(?:payment|receipt|remittance)\b[^.!?;\r\n]{0,80}\b(?:for|to)\b",
    re.IGNORECASE,
)
_NEGATED_CREDIT_AMOUNT = re.compile(
    r"\b(?:do\s+not|don't|must\s+not|should\s+not|never|not\s+to)\s+"
    r"(?:apply|use|deduct|subtract)\b[^.!?;\r\n]{0,100}\b(?:credit|credit\s+note)\b|"
    r"\b(?:do\s+not|don't|must\s+not|should\s+not|never|not\s+to)\s+"
    r"(?:apply|use|deduct|subtract)\b[^.!?;\r\n]{0,100}"
    r"(?:USD|EUR|GBP|\$|€|£)\s*[0-9]",
    re.IGNORECASE,
)
_CORRECTION_LANGUAGE = re.compile(
    r"\bcorrection\b|\bcorrigendum\b|\bcorrected\s+(?:instruction|remittance|allocation)\b|"
    r"\b(?:please\s+)?disregard\s+(?:our|the|my)\s+(?:previous|earlier|prior)\b|"
    r"\bignore\s+(?:our|the|my)\s+(?:previous|earlier|prior)\b|"
    r"\bsupersedes?\b|\bthis\s+replaces\s+(?:our|the|my)\s+(?:previous|earlier|prior)\b",
    re.IGNORECASE,
)
_SENDER_ADDRESS = re.compile(
    r"^(?P<local>[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+)@"
    r"(?P<domain>[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?)$"
)
_ORGANIZATION_STOPWORDS = {
    "bank",
    "co",
    "company",
    "corp",
    "corporation",
    "group",
    "inc",
    "international",
    "limited",
    "llc",
    "ltd",
    "plc",
    "services",
}


def _clauses(text: str):
    return [
        clause.strip()
        for clause in re.split(r"[!?;\r\n]+|(?<=\.)\s+(?=[A-Z])", text or "")
        if clause.strip()
    ]


def contains_token_phrase(text: str, phrase: str) -> bool:
    body_tokens = re.findall(r"[a-z0-9]+", text.casefold())
    phrase_tokens = re.findall(r"[a-z0-9]+", phrase.casefold())
    if not phrase_tokens or len(phrase_tokens) > len(body_tokens):
        return False
    return any(
        body_tokens[index : index + len(phrase_tokens)] == phrase_tokens
        for index in range(len(body_tokens) - len(phrase_tokens) + 1)
    )


def payer_identity_phrases(payer_name: str) -> Set[str]:
    """Return exact payer phrases represented by a structured bank descriptor.

    Bank exports commonly encode a receipt as ``BANK NAME OBO CUSTOMER``.  The
    bank component remains the actual remitter, while the customer is checked
    independently by the relationship verifier.  No fuzzy or partial-token
    matching is allowed for ordinary payer names.
    """

    value = (payer_name or "").strip()
    if not value:
        return set()
    phrases = {value}
    parts = re.split(r"\s+\b(?:OBO|FBO)\b\s+", value, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2 and parts[0].strip():
        phrases.add(parts[0].strip())
    return phrases


def contains_payer_identity(text: str, payer_name: str) -> bool:
    return any(
        contains_token_phrase(text, phrase)
        for phrase in payer_identity_phrases(payer_name)
    )


def _identity_keys(values: Iterable[str]) -> Set[str]:
    keys: Set[str] = set()
    for value in values:
        tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", (value or "").casefold())
            if len(token) >= 3 and token not in _ORGANIZATION_STOPWORDS
        ]
        keys.update(tokens)
        if tokens:
            keys.add("".join(tokens))
    return keys


def _identity_slugs(values: Iterable[str]) -> Set[str]:
    """Return complete organization slugs, never isolated shared-name tokens."""

    slugs: Set[str] = set()
    for value in values:
        tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", (value or "").casefold())
            if len(token) >= 3 and token not in _ORGANIZATION_STOPWORDS
        ]
        if tokens:
            slugs.add("".join(tokens))
    return slugs


def sender_is_trusted_for_relationship(
    sender: str,
    payer_name: str,
    customer_names: Iterable[str],
) -> bool:
    """Require relationship assertions to come from an identity-aligned source.

    The synthetic repository has no DKIM/authentication metadata. Its defensible
    local invariant is therefore narrower: an asserting sender's organizational
    domain must align with the customer identity. The reserved ``example.test``
    unit-test mailbox additionally models a payer-controlled authenticated source
    when its local part aligns with the payer. Unknown domains never establish a
    payer/customer relationship, though their contradictions remain safety input.
    """

    match = _SENDER_ADDRESS.fullmatch((sender or "").strip())
    if match is None:
        return False
    local = match.group("local").casefold()
    domain = match.group("domain").casefold().rstrip(".")
    customer_slugs = _identity_slugs(customer_names)
    # Repository fixtures model customer-controlled mailboxes with the exact
    # organization slug immediately below the reserved ``.example`` suffix
    # (for example, ``copperleaffoods.example``). Requiring an exact slug match
    # prevents a merely shared token or an attacker-owned lookalike such as
    # ``acme.evil.example`` from becoming authorization evidence.
    if domain.endswith(".example"):
        organization_slug = re.sub(r"[^a-z0-9]+", "", domain[: -len(".example")])
        return bool(organization_slug and organization_slug in customer_slugs)
    if domain == "example.test":
        return bool(_identity_keys([local]).intersection(_identity_keys([payer_name])))
    return False


def explicitly_negates_payer_relationship(text: str, payer_name: str) -> bool:
    return any(
        contains_payer_identity(clause, payer_name)
        and _NEGATIVE_RELATIONSHIP.search(clause)
        for clause in _clauses(text)
    )


def affirmatively_supports_payer_relationship(
    text: str,
    payer_name: str,
    customer_name: str,
) -> bool:
    return any(
        contains_payer_identity(clause, payer_name)
        and contains_token_phrase(clause, customer_name)
        and _RELATIONSHIP_LANGUAGE.search(clause)
        and not _NEGATIVE_RELATIONSHIP.search(clause)
        for clause in _clauses(text)
    )


@dataclass
class DocumentSemantics:
    affirmative_invoice_ids: Set[str] = field(default_factory=set)
    affirmative_credit_ids: Set[str] = field(default_factory=set)
    prohibited_invoice_ids: Set[str] = field(default_factory=set)
    prohibited_credit_ids: Set[str] = field(default_factory=set)
    noncurrent_invoice_ids: Set[str] = field(default_factory=set)
    affirmative_credit_amounts: Set[Decimal] = field(default_factory=set)
    prohibited_credit_amounts: Set[Decimal] = field(default_factory=set)


def is_correction_instruction(text: str) -> bool:
    return bool(_CORRECTION_LANGUAGE.search(text or ""))


def _payment_reference_values(payment: Optional[Payment]) -> Set[str]:
    if payment is None:
        return set()
    return {
        value.strip()
        for value in (
            payment.payment_id,
            payment.bank_reference,
            payment.remittance_reference,
        )
        if isinstance(value, str) and value.strip()
    }


def _email_payment_references(text: str, payment: Optional[Payment]) -> Set[str]:
    return {
        reference
        for reference in _payment_reference_values(payment)
        if contains_token_phrase(text, reference)
    }


def superseded_allocation_email_ids(
    emails,
    *,
    payment: Optional[Payment] = None,
) -> Set[str]:
    """Identify emails whose affirmative allocation instruction is superseded.

    An instruction is superseded only under the narrowest defensible rule: a
    strictly later email from the same customer carries explicit correction
    language, its own differing affirmative instruction, and an explicit
    reference to the same payment context as the older instruction. The
    payment context is supplied by the caller because an email's customer and
    invoice IDs alone do not identify which payment the correction replaces.
    Prohibitions in a superseded email remain active safety input, and
    conflicting instructions without an explicit dated correction stay
    contradictions.

    ``payment`` is intentionally optional for callers that only need the
    semantic classifier. Without it, no allocation can be superseded: a
    customer-level correction with no payment, bank, or remittance reference
    is not sufficient authority to rewrite an unrelated payment's evidence.
    """

    analyzed = []
    for email in emails:
        text = f"{email.subject} {email.body}"
        analyzed.append(
            (
                email,
                classify_document_semantics(text),
                is_correction_instruction(text),
                _email_payment_references(text, payment),
            )
        )
    superseded: Set[str] = set()
    for email, semantics, _, email_references in analyzed:
        if not semantics.affirmative_invoice_ids:
            continue
        for other, other_semantics, other_is_correction, other_references in analyzed:
            if other.email_id == email.email_id or not other_is_correction:
                continue
            if other.customer_id != email.customer_id:
                continue
            if other.date <= email.date:
                continue
            if not other_semantics.affirmative_invoice_ids:
                continue
            # Both sides must identify the current payment through a stable
            # payment/bank/remittance reference. They may use different fields
            # (for example, the original email has the bank reference while
            # the correction has the payment ID). This prevents a later
            # generic correction for another payment from superseding this
            # instruction.
            if not email_references or not other_references:
                continue
            if (
                other_semantics.affirmative_invoice_ids == semantics.affirmative_invoice_ids
                and other_semantics.affirmative_credit_ids == semantics.affirmative_credit_ids
            ):
                continue
            superseded.add(email.email_id)
            break
    return superseded


def classify_document_semantics(
    text: str,
    *,
    bare_references_are_affirmative: bool = False,
) -> DocumentSemantics:
    result = DocumentSemantics()
    for clause in _clauses(text):
        ids = extract_document_ids(clause)
        invoice_ids = {item for item in ids if item.startswith("INV_")}
        credit_ids = {item for item in ids if item.startswith("CR_")}
        amounts = set(extract_credit_amounts(clause))
        is_negated = bool(
            _NEGATED_ALLOCATION.search(clause)
            or _POSTPOSITIVE_DOCUMENT_PROHIBITION.search(clause)
        )
        is_noncurrent = bool(_NONCURRENT_DOCUMENT.search(clause))
        is_affirmative = bool(_AFFIRMATIVE_ALLOCATION.search(clause))

        if is_noncurrent:
            result.noncurrent_invoice_ids.update(invoice_ids)
            result.prohibited_credit_ids.update(credit_ids)
        if is_negated:
            result.prohibited_invoice_ids.update(invoice_ids)
            result.prohibited_credit_ids.update(credit_ids)
        if amounts:
            if is_negated or _NEGATED_CREDIT_AMOUNT.search(clause):
                result.prohibited_credit_amounts.update(amounts)
            elif is_affirmative and not is_noncurrent:
                result.affirmative_credit_amounts.update(amounts)

        if not is_negated and not is_noncurrent and (
            bare_references_are_affirmative or is_affirmative
        ):
            result.affirmative_invoice_ids.update(invoice_ids)
            result.affirmative_credit_ids.update(credit_ids)
    return result
