from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .payment import is_valid_monetary_amount


class Credit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credit_id: str
    customer_id: str
    invoice_id: str
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str
    reason: str
    status: Literal["valid", "invalid", "consumed"] = "valid"
    consumed_by_payment_id: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_valid(cls, value: Decimal) -> Decimal:
        if not is_valid_monetary_amount(value):
            raise ValueError("amount must be a finite, positive value with at most two decimals")
        return value
