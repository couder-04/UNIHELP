"""Planner routing: if/then and empty-LLM fallback. No live LLM."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def _raise_if_llm_called(*args, **kwargs):
    raise AssertionError("chat_create should not be called")


def _patch_llm(monkeypatch, fn):
    monkeypatch.setattr("unihelp_planner.chat_create", fn)


def _empty_chat_response():
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=""))]
    )


IF_THEN = (
    "What is my attendance percentage in CS101 if it is less than 20% "
    "then send me today's timetable"
)


class TestConditionalPlan:
    def test_if_then_attendance_timetable_skips_llm(self, planner, monkeypatch):
        _patch_llm(monkeypatch, _raise_if_llm_called)

        plan = planner.create_plan(IF_THEN)

        assert [t["agent"] for t in plan["tasks"]] == ["attendance", "timetable"]
        assert [t["id"] for t in plan["tasks"]] == ["t1", "t2"]
        assert plan["tasks"][0]["condition"] is None
        cond = plan["tasks"][1]["condition"]
        assert isinstance(cond, dict)
        assert cond["depends_on"] == "t1"
        assert cond["type"] == "threshold"
        assert cond["op"] == "<"
        assert float(cond["value"]) == 20
        assert "attendance" in plan["tasks"][0]["request"].lower()
        assert "timetable" in plan["tasks"][1]["request"].lower()


class TestKeywordFallback:
    def test_empty_llm_still_plans_mess_and_bus(self, planner, monkeypatch):
        def fake_chat_create(**kwargs):
            return _empty_chat_response()

        _patch_llm(monkeypatch, fake_chat_create)

        plan = planner.create_plan(
            "Tell me today's dinner at Kalam and the Bus 02 schedule"
        )

        agents = [t["agent"] for t in plan["tasks"]]
        assert agents == ["mess", "bus"]


class TestSingleAgentFastPath:
    def test_attendance_only_skips_llm(self, planner, monkeypatch):
        _patch_llm(monkeypatch, _raise_if_llm_called)

        plan = planner.create_plan("What is my attendance percentage in CS101?")

        assert len(plan["tasks"]) == 1
        assert plan["tasks"][0]["agent"] == "attendance"
        assert plan["tasks"][0]["id"] == "t1"


def _threshold(cond, op, value, depends_on="t1"):
    assert isinstance(cond, dict)
    assert cond["type"] == "threshold"
    assert cond["depends_on"] == depends_on
    assert cond["op"] == op
    assert float(cond["value"]) == float(value)


class TestSplitterConnectives:
    def test_if_comma_no_then(self, planner, monkeypatch):
        _patch_llm(monkeypatch, _raise_if_llm_called)

        plan = planner.create_plan(
            "If my attendance is less than 20%, send me today's timetable"
        )

        assert [t["agent"] for t in plan["tasks"]] == ["attendance", "timetable"]
        assert plan["tasks"][0]["condition"] is None
        _threshold(plan["tasks"][1]["condition"], "<", 20)

    def test_consequence_first_y_if_x(self, planner, monkeypatch):
        _patch_llm(monkeypatch, _raise_if_llm_called)

        plan = planner.create_plan(
            "Send me today's timetable if my attendance is less than 20%"
        )

        assert [t["agent"] for t in plan["tasks"]] == ["attendance", "timetable"]
        assert [t["id"] for t in plan["tasks"]] == ["t1", "t2"]
        _threshold(plan["tasks"][1]["condition"], "<", 20)
        assert "timetable" in plan["tasks"][1]["request"].lower()

    def test_unless_negates_gate(self, planner, monkeypatch):
        _patch_llm(monkeypatch, _raise_if_llm_called)

        plan = planner.create_plan(
            "Unless my attendance is at least 75%, send me today's timetable"
        )

        assert [t["agent"] for t in plan["tasks"]] == ["attendance", "timetable"]
        # unless (>= 75) -> inverse op < 75
        _threshold(plan["tasks"][1]["condition"], "<", 75)

    def test_if_comma_else_three_tasks(self, planner, monkeypatch):
        _patch_llm(monkeypatch, _raise_if_llm_called)

        plan = planner.create_plan(
            "If my attendance is less than 20%, send me today's timetable, "
            "else show me the next bus"
        )

        assert [t["agent"] for t in plan["tasks"]] == [
            "attendance",
            "timetable",
            "bus",
        ]
        _threshold(plan["tasks"][1]["condition"], "<", 20)
        _threshold(plan["tasks"][2]["condition"], ">=", 20)
        assert plan["tasks"][1]["condition"]["depends_on"] == "t1"
        assert plan["tasks"][2]["condition"]["depends_on"] == "t1"

    def test_same_agent_if_then_is_split(self, planner, monkeypatch):
        _patch_llm(monkeypatch, _raise_if_llm_called)

        plan = planner.create_plan(
            "What is my attendance percentage in CS101 if it is less than 20% "
            "then tell me my skip budget"
        )

        assert [t["agent"] for t in plan["tasks"]] == ["attendance", "attendance"]
        _threshold(plan["tasks"][1]["condition"], "<", 20)
        assert "skip budget" in plan["tasks"][1]["request"].lower()

    def test_nested_if_falls_through_to_llm_planner(self, planner, monkeypatch):
        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"tasks":['
                                '{"id":"t1","agent":"attendance",'
                                '"request":"Show attendance","condition":null},'
                                '{"id":"t2","agent":"timetable",'
                                '"request":"Show timetable",'
                                '"condition":{"depends_on":"t1",'
                                '"type":"threshold","field":"value",'
                                '"op":"<","value":20}},'
                                '{"id":"t3","agent":"bus",'
                                '"request":"Next bus",'
                                '"condition":{"depends_on":"t2",'
                                '"type":"predicate",'
                                '"text":"only if there is a class today"}}'
                                "]}"
                            )
                        )
                    )
                ]
            )

        _patch_llm(monkeypatch, fake_chat_create)

        nested = (
            "If my attendance is less than 20% then if I have a class today "
            "send me the next bus"
        )
        assert planner._conditional_plan(nested) is None

        plan = planner.create_plan(nested)

        assert llm_calls, "nested phrasing must call the LLM-planner fallback"
        from config import LLM_FAST_MODEL

        assert all(c.get("model") == LLM_FAST_MODEL for c in llm_calls)
        assert [t["id"] for t in plan["tasks"]] == ["t1", "t2", "t3"]
        assert plan["tasks"][2]["condition"]["depends_on"] == "t2"


class TestDependsOnValidation:
    def test_invalid_depends_on_retries_once(self, planner, monkeypatch):
        calls = {"n": 0}

        def fake_chat_create(**kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                content = (
                    '{"tasks":[{"id":"t1","agent":"attendance",'
                    '"request":"percent","condition":null},'
                    '{"id":"t2","agent":"timetable","request":"today",'
                    '"condition":{"depends_on":"missing",'
                    '"type":"ordering"}}]}'
                )
            else:
                content = (
                    '{"tasks":[{"id":"t1","agent":"attendance",'
                    '"request":"percent","condition":null},'
                    '{"id":"t2","agent":"timetable","request":"today",'
                    '"condition":{"depends_on":"t1",'
                    '"type":"ordering"}}]}'
                )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

        _patch_llm(monkeypatch, fake_chat_create)

        plan = planner.create_plan(
            "Show attendance and then the timetable after that"
        )

        assert calls["n"] == 2
        assert plan["tasks"][1]["condition"]["depends_on"] == "t1"
