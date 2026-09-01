from typing import List

from pydantic import BaseModel, ConfigDict, Field


class Customer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    legal_name: str
    aliases: List[str] = Field(default_factory=list)
    parent_entities: List[str] = Field(default_factory=list)
    subsidiaries: List[str] = Field(default_factory=list)
    known_payers: List[str] = Field(default_factory=list)
