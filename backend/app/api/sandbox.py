"""Bounded, ephemeral investigations using the unchanged reconciliation pipeline."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import BoundedSemaphore
from typing import List, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from starlette.concurrency import run_in_threadpool

from app.models import Customer, Credit, Invoice, Payment, RemittanceEmail, InvestigationProposal
from app.api.exceptions import _public_exception_detail
from app.services.ai_investigator import InvestigatorError, OllamaInvestigator
from app.services.pipeline import process_payment
from app.utils.loaders import Dataset, _require_unique_ids, _validate_relationships


router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])
MAX_BODY_BYTES = 65536
_RUN_SLOTS = BoundedSemaphore(2)


@router.get("/examples")
def examples():
    return json.loads((Path(__file__).resolve().parents[1] / "sandbox_examples.json").read_text(encoding="utf-8"))


class SandboxInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    mode: Literal["manual_proposal", "live_ai"] = "manual_proposal"
    payment: Payment
    customers: List[Customer] = Field(min_length=1, max_length=3)
    invoices: List[Invoice] = Field(min_length=1, max_length=8)
    credits: List[Credit] = Field(default_factory=list, max_length=3)
    emails: List[RemittanceEmail] = Field(default_factory=list, max_length=4)
    related_payments: List[Payment] = Field(default_factory=list, max_length=4)
    proposal: Optional[InvestigationProposal] = None

    def dataset(self) -> Dataset:
        return Dataset(
            payments=[self.payment, *self.related_payments], customers=self.customers,
            invoices=self.invoices, credits=self.credits, emails=self.emails,
        )

    @model_validator(mode="after")
    def validate_records(self):
        dataset = self.dataset()
        for records, key, name in (
            (dataset.payments, "payment_id", "payment"),
            (self.customers, "customer_id", "customer"),
            (self.invoices, "invoice_id", "invoice"),
            (self.credits, "credit_id", "credit"),
            (self.emails, "email_id", "email"),
        ):
            _require_unique_ids(records, key, name)
            for record in records:
                identifier = getattr(record, key)
                if not identifier.strip() or len(identifier) > 100:
                    raise ValueError("Record IDs must contain 1 to 100 characters")
        _validate_relationships(dataset)
        if self.mode == "manual_proposal" and self.proposal is None:
            raise ValueError("Supply a proposal when testing a manual hypothesis")
        if self.mode == "live_ai" and self.proposal is not None:
            raise ValueError("Live AI constructs its own proposal; omit the manual proposal")
        if self.proposal and self.proposal.payment_id != self.payment.payment_id:
            raise ValueError("Proposal payment_id must match the submitted payment")
        return self


class ManualInvestigator:
    def __init__(self, proposal):
        self.proposal = proposal

    def investigate(self, bundle):
        return self.proposal


class SandboxInvestigator:
    def investigate(self, bundle):
        # Never accept model hosts, credentials, or model names from a visitor.
        try:
            return OllamaInvestigator(timeout_seconds=40).investigate(bundle)
        except InvestigatorError as exc:
            raise InvestigatorError("Live model did not return a usable proposal. Try again or test a manual hypothesis.") from exc


def _run(scenario, investigator):
    # Per-process backpressure, not a distributed/public model spending limit.
    if not _RUN_SLOTS.acquire(blocking=False):
        raise HTTPException(429, "The sandbox is busy. Retry in a moment.", headers={"Retry-After": "5"})
    try:
        return process_payment(scenario.payment.payment_id, scenario.dataset(), investigator)
    finally:
        _RUN_SLOTS.release()


@router.get("/capabilities")
def capabilities(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {
        "schema_version": 1,
        "live_ai_enabled": os.getenv("SANDBOX_LIVE_AI_ENABLED") == "true",
        "manual_proposal_enabled": True,
        "max_body_bytes": MAX_BODY_BYTES,
        "limits": {"customers": 3, "invoices": 8, "credits": 3, "emails": 4, "related_payments": 4},
        "storage": "ephemeral",
        "trust_boundary": "All records are user-supplied simulation facts, not authenticated financial records.",
    }


@router.post("/investigate")
async def investigate(request: Request):
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise HTTPException(415, "Send an application/json scenario")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise HTTPException(413, "Scenario exceeds the 64 KiB limit")
    try:
        scenario = SandboxInput.model_validate_json(bytes(body))
    except ValidationError as exc:
        # Do not echo raw records or Pydantic context (which may contain input).
        raise HTTPException(422, [
            {"path": ".".join(str(part) for part in item["loc"]), "message": item["msg"]}
            for item in exc.errors(include_input=False, include_context=False)[:20]
        ]) from exc
    if scenario.mode == "live_ai" and os.getenv("SANDBOX_LIVE_AI_ENABLED") != "true":
        raise HTTPException(503, "Live AI is not configured on this server. Select manual proposal to run the verifier.")
    investigator = SandboxInvestigator() if scenario.mode == "live_ai" else ManualInvestigator(scenario.proposal)
    result = await run_in_threadpool(_run, scenario, investigator)
    raw = result.model_dump(mode="json")
    raw["operational_exception_class"] = "sandbox"
    raw["operational_is_exception"] = result.baseline.status != "matched"
    canonical = json.dumps(scenario.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return Response(
        content=json.dumps({
            "schema_version": 1, "run_id": str(uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "input_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "mode": scenario.mode,
            "proposal_source": (
                "not_needed" if result.baseline.status == "matched" else
                "unavailable" if result.proposal is None else scenario.mode
            ),
            "simulation_only": True, "stored": False,
            "detail": _public_exception_detail(raw),
        }), media_type="application/json", headers={"Cache-Control": "no-store"},
    )
