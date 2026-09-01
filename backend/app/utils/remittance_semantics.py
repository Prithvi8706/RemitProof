import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Set

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
