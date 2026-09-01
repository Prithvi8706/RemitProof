from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .payment import is_valid_monetary_amount


class Invoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: str
    customer_id: str
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str
    issue_date: date
    due_date: date
    description: str
    status: Literal["open", "paid", "closed"] = "open"
    allocated_payment_id: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_valid(cls, value: Decimal) -> Decimal:
        if not is_valid_monetary_amount(value):
            raise ValueError("amount must be a finite, positive value with at most two decimals")
        return value
