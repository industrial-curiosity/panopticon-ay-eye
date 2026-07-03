"""Shared test helpers: fixture loading."""

import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_REPO = FIXTURES / "sample_repo"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))
