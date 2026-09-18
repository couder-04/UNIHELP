"""The generated planner prompt must match the previous hand-written one."""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from agent_registry import build_planner_system_prompt

_LEGACY = Path(__file__).resolve().parent / "_legacy_system_prompt.txt"


def test_iit_patna_planner_prompt_is_byte_identical():
    expected = _LEGACY.read_text(encoding="utf-8")
    got = build_planner_system_prompt(include_custom=False)
    if got != expected:
        import difflib

        diff = "".join(
            difflib.unified_diff(
                expected.splitlines(True),
                got.splitlines(True),
                fromfile="legacy_handwritten",
                tofile="generated",
            )
        )
        raise AssertionError(
            "Generated planner prompt diverged from the IIT Patna "
            f"hand-written prompt.\n{diff}"
        )
