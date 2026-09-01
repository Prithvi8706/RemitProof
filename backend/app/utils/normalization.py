import re
from decimal import Decimal, InvalidOperation
from typing import List, Set


DOCUMENT_ID_PATTERN = re.compile(r"\b(?:INV|CR|EMAIL)_[A-Z0-9]+\b", re.IGNORECASE)


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def extract_document_ids(text: str) -> Set[str]:
    return {match.upper() for match in DOCUMENT_ID_PATTERN.findall(text or "")}


def extract_credit_amounts(text: str) -> List[Decimal]:
    """Extract amounts explicitly described as credits or deductions.

    This is deliberately narrow. It is a contradiction detector, not an NLP
    system and not a source of proposed allocations.
    """

    # IDs such as CR_S10A contain digits, but those digits are not monetary
    # amounts. Remove document IDs before looking for credit amount context.
    text_without_document_ids = DOCUMENT_ID_PATTERN.sub(" ", text or "")
    patterns = (
        r"(?:credit|deduct(?:ed|ion|ing)?)\D{0,24}(?:USD\s*|\$\s*)?([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        r"(?:USD\s*|\$\s*)([0-9][0-9,]*(?:\.[0-9]{1,2})?)\D{0,24}(?:credit|deduct(?:ed|ion|ing)?)",
    )
    amounts = []
    for pattern in patterns:
        for raw in re.findall(pattern, text_without_document_ids, flags=re.IGNORECASE):
            try:
                value = Decimal(raw.replace(",", ""))
            except InvalidOperation:
                continue
            if value not in amounts:
                amounts.append(value)
    return amounts
