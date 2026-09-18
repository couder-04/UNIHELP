"""Reset llm.py's process-wide cache mode between tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import llm  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_llm_cache_mode():
    previous = llm._cache_mode
    llm._cache_mode = "full"
    yield
    llm._cache_mode = previous
