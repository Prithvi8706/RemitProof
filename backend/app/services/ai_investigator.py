import hashlib
import http.client
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from urllib import error, request

from pydantic import ValidationError

from app.models import CandidateBundle, InvestigationProposal


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "investigator.txt"
INVESTIGATOR_VERSION = "remitproof-ollama-investigator-v2"
DEFAULT_GENERATION_OPTIONS: Dict[str, object] = {"temperature": 0, "seed": 42}


def _sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class InvestigatorError(RuntimeError):
    pass


def _read_response_json(response: object) -> object:
    """Decode an Ollama HTTP response without leaking transport details."""

    try:
        raw_body = response.read()
    except (OSError, http.client.HTTPException) as exc:
        raise InvestigatorError("Ollama response body read failed") from exc

    if not isinstance(raw_body, (bytes, bytearray)):
        raise InvestigatorError("Ollama response body must be bytes")

    try:
        decoded_body = bytes(raw_body).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvestigatorError("Ollama response body is not valid UTF-8") from exc

    try:
        return json.loads(decoded_body)
    except json.JSONDecodeError as exc:
        raise InvestigatorError("Ollama response body is not valid JSON") from exc


def _response_content(result: object) -> str:
    if not isinstance(result, dict):
        raise InvestigatorError("Ollama response envelope must be a JSON object")

    message = result.get("message")
    if not isinstance(message, dict):
        raise InvestigatorError("Ollama response is missing a message object")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise InvestigatorError("Ollama response message content must be a non-empty string")
    return content


class OllamaInvestigator:
    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: int = 120,
        generation_options: Optional[Dict[str, object]] = None,
        model_digest: Optional[str] = None,
    ) -> None:
        self.host = (host or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or "llama3.2"
        self.timeout_seconds = timeout_seconds
        self.generation_options = dict(generation_options or DEFAULT_GENERATION_OPTIONS)
        self.model_digest = model_digest or os.getenv("OLLAMA_MODEL_DIGEST") or None
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    def cache_identity(self) -> Dict[str, object]:
        """Return every model-affecting input used to isolate proposal caches."""

        schema = InvestigationProposal.model_json_schema()
        return {
            "investigator_version": INVESTIGATOR_VERSION,
            "host": self.host,
            "model": self.model,
            "model_digest": self.model_digest,
            "timeout_seconds": self.timeout_seconds,
            "generation_options": self.generation_options,
            "prompt_sha256": hashlib.sha256(
                self.system_prompt.encode("utf-8")
            ).hexdigest(),
            "proposal_schema_sha256": _sha256_json(schema),
        }

    def public_provenance(self) -> Dict[str, object]:
        """Return cache provenance without persisting credentials embedded in a host URL."""

        identity = self.cache_identity()
        host = str(identity.pop("host"))
        identity["host_sha256"] = hashlib.sha256(host.encode("utf-8")).hexdigest()
        identity["identity_sha256"] = _sha256_json(self.cache_identity())
        return identity

    def investigate(self, bundle: CandidateBundle) -> InvestigationProposal:
        user_payload = {
            "instruction": "Propose the best evidence-grounded reconciliation candidate.",
            "candidate_bundle": bundle.model_dump(mode="json"),
        }
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": json.dumps(user_payload, separators=(",", ":"))},
        ]
        validation_errors: List[str] = []

        for attempt in range(3):
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "format": InvestigationProposal.model_json_schema(),
                "options": self.generation_options,
            }
            body = json.dumps(payload).encode("utf-8")
            call = request.Request(
                f"{self.host}/api/chat",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with request.urlopen(call, timeout=self.timeout_seconds) as response:
                    result = _read_response_json(response)
            except InvestigatorError:
                raise
            except (error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
                raise InvestigatorError("Ollama request transport failed") from exc

            raw_content = _response_content(result)
            try:
                proposal = InvestigationProposal.model_validate_json(raw_content)
            except (ValidationError, json.JSONDecodeError) as exc:
                validation_errors.append(str(exc))
                messages.append({"role": "assistant", "content": raw_content})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your response failed strict schema validation. Return a corrected JSON object only. "
                            f"Validation error: {str(exc)[:1200]}"
                        ),
                    }
                )
                continue

            if proposal.payment_id != bundle.payment.payment_id:
                validation_errors.append("payment_id did not match the supplied payment")
                messages.append({"role": "assistant", "content": raw_content})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The payment_id must exactly match "
                            f"{bundle.payment.payment_id}. Return corrected JSON only."
                        ),
                    }
                )
                continue
            return proposal

        raise InvestigatorError(
            "Ollama returned no schema-valid proposal after three attempts: "
            + " | ".join(validation_errors)
        )
