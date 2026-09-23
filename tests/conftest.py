import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kyb import rulebook  # noqa: E402

AS_OF = "2026-09-23T10:00:00Z"


@pytest.fixture
def rb():
    return rulebook.load()


@pytest.fixture
def cases():
    return {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "data" / "cases").glob("*.json"))}


@pytest.fixture
def clean(cases):
    """A low-risk application that passes every rule. Tests mutate a copy."""
    return copy.deepcopy(cases["C001"])
