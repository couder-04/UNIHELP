"""Shared fixtures for deterministic fast_parse tests. No live DB or LLM."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Friday 18 Sep 2026 — relative dates in tests resolve against this.
NOW = "Friday, 2026-09-18 17:04:00 IST"

USER_META = {
    "role": "student",
    "name": "Test Student",
    "roll_number": "2501CS00",
    "Time and Date": NOW,
}


def fake_chat_response(content="llm reply"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, tool_calls=None)
            )
        ]
    )


@pytest.fixture
def now():
    return NOW


@pytest.fixture
def user_metadata():
    return dict(USER_META)
