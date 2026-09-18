"""Admin setup requests skip the LLM planner."""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def _raise_if_llm_called(*args, **kwargs):
    raise AssertionError("chat_create should not be called")


class TestSetupFastPath:
    def test_admin_add_feature_routes_to_setup(self, planner, monkeypatch):
        monkeypatch.setattr("unihelp_planner.chat_create", _raise_if_llm_called)
        plan = planner.create_plan(
            "Add a feature called library for book search",
            role="admin",
        )
        assert [t["agent"] for t in plan["tasks"]] == ["setup"]

    def test_admin_import_people_routes_to_setup(self, planner, monkeypatch):
        monkeypatch.setattr("unihelp_planner.chat_create", _raise_if_llm_called)
        plan = planner.create_plan(
            "Import people from this roster CSV",
            role="admin",
        )
        assert plan["tasks"][0]["agent"] == "setup"

    def test_student_dinner_still_mess(self, planner, monkeypatch):
        monkeypatch.setattr("unihelp_planner.chat_create", _raise_if_llm_called)
        plan = planner.create_plan("What is dinner at Kalam today?", role="student")
        assert [t["agent"] for t in plan["tasks"]] == ["mess"]

    def test_student_add_feature_does_not_use_setup_fast_path(
        self, planner, monkeypatch
    ):
        calls = []

        def fake(**kwargs):
            calls.append(kwargs)
            from types import SimpleNamespace

            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content='{"tasks":[],"status":"unsupported","message":"no"}'
                        )
                    )
                ]
            )

        monkeypatch.setattr("unihelp_planner.chat_create", fake)
        plan = planner.create_plan("Add a feature called library", role="student")
        assert calls, "student setup-like text should fall through to the LLM"
        assert all(t.get("agent") != "setup" for t in plan.get("tasks") or [])
