from dataclasses import dataclass
from typing import Tuple

from app.models import CandidateBundle
from app.utils.remittance_semantics import classify_document_semantics


REASON_UNREAD_INSTRUCTION = "unread_instruction"


@dataclass(frozen=True)
class UnreadFinding:
    email_ids: Tuple[str, ...]
    document_ids: Tuple[str, ...]

    @property
    def blocks(self) -> bool:
        return bool(self.email_ids)


def find_unread_instructions(bundle: CandidateBundle) -> UnreadFinding:
    email_ids = []
    document_ids = set()
    for email in bundle.candidate_emails:
        unread_ids = classify_document_semantics(f"{email.subject} {email.body}").unread_ids
        if unread_ids:
            email_ids.append(email.email_id)
            document_ids.update(unread_ids)
    return UnreadFinding(email_ids=tuple(email_ids), document_ids=tuple(sorted(document_ids)))
