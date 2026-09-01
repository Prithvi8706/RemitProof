import json
from pathlib import Path
from typing import Dict

import pytest

from app.models import CandidateBundle


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def spike_cases() -> Dict[str, dict]:
    raw_cases = json.loads(
        (REPO_ROOT / "data" / "dev" / "spike_cases.json").read_text(encoding="utf-8")
    )
    return {case["case_id"]: case for case in raw_cases}


@pytest.fixture
def bundle_factory(spike_cases):
    def build(case_id: str) -> CandidateBundle:
        return CandidateBundle.model_validate(spike_cases[case_id]["input"])

    return build
