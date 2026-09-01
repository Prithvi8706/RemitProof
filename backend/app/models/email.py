from datetime import date

from pydantic import BaseModel, ConfigDict


class RemittanceEmail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_id: str
    sender: str
    customer_id: str
    date: date
    subject: str
    body: str
