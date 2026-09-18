"""Fixtures for deterministic Executor dispatch tests.

No live DB or LLM: domain agents are replaced with plain functions.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# pytest prepends tests/ to sys.path, so `import executor` would resolve to
# this test package rather than executor.py. Load the production module by
# path under a dedicated name so the two never collide.
_spec = importlib.util.spec_from_file_location(
    "unihelp_executor",
    _HERE / "executor.py",
)
executor_mod = importlib.util.module_from_spec(_spec)
sys.modules["unihelp_executor"] = executor_mod
_spec.loader.exec_module(executor_mod)
Executor = executor_mod.Executor


def fake_chat_response(content="combined reply"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


@pytest.fixture
def executor():
    ex = Executor()
    calls = {}
    order = []

    def stub(name):
        def _call(request, user_metadata):
            order.append(name)
            calls.setdefault(name, []).append(
                {"request": request, "user_metadata": user_metadata}
            )
            return f"{name}:{request}"

        return _call

    ex._agent_map = {name: stub(name) for name in list(ex._agent_map)}
    ex.agent_calls = calls
    ex.call_order = order
    return ex
