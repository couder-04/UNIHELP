"""Fixtures for Planner tests. No live LLM."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

_spec = importlib.util.spec_from_file_location(
    "unihelp_planner",
    _HERE / "planner.py",
)
planner_mod = importlib.util.module_from_spec(_spec)
sys.modules["unihelp_planner"] = planner_mod
_spec.loader.exec_module(planner_mod)
Planner = planner_mod.Planner


def empty_chat_response():
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=""))]
    )


@pytest.fixture
def planner():
    return Planner()
