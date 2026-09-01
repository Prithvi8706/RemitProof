from datetime import date
from decimal import Decimal, DecimalException
import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


MONEY_QUANTUM = Decimal("0.01")
ISO_CURRENCY_PATTERN = re.compile(r"[A-Za-z]{3}")


def is_valid_monetary_amount(value: object) -> bool:
    """Return whether a value is a finite, positive amount representable in cents."""

    if not isinstance(value, Decimal):
        return False

    amount = value
    if not amount.is_finite() or amount <= 0:
        return False

    try:
        return amount.quantize(MONEY_QUANTUM) == amount
    except DecimalException:
        return False


def normalize_iso_currency(value: object) -> str:
    """Normalize a syntactically valid three-letter currency code."""

    if not isinstance(value, str):
        raise ValueError("currency must be a three-letter ISO-style code")
    currency = value.strip()
    if ISO_CURRENCY_PATTERN.fullmatch(currency) is None:
        raise ValueError("currency must be a three-letter ISO-style code")
    return currency.upper()


class Payment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: str
    date: date
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str
    payer_name: str
    bank_reference: str = ""
    remittance_reference: str = ""
    status: Literal["unmatched", "matched", "reconciled"] = "unmatched"
    allocated_customer_id: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_valid(cls, value: Decimal) -> Decimal:
        if not is_valid_monetary_amount(value):
            raise ValueError("amount must be a finite, positive value with at most two decimals")
        return value

    @field_validator("currency", mode="before")
    @classmethod
    def currency_must_be_valid(cls, value: object) -> str:
        return normalize_iso_currency(value)
