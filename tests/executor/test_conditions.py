"""Structured conditions: else, chains, same-agent, extract. No live LLM."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from tests.executor.test_dispatch import (  # noqa: E402
    USER_META,
    _patch_llm,
    _plan,
    _raise_if_llm_called,
    fake_chat_response,
)


def _threshold(depends_on, op, value, field="value"):
    return {
        "depends_on": depends_on,
        "type": "threshold",
        "field": field,
        "op": op,
        "value": value,
    }


def _pct_attendance(executor, percent):
    def attendance_fn(request, user_metadata):
        executor.call_order.append("attendance")
        executor.agent_calls.setdefault("attendance", []).append(
            {"request": request, "user_metadata": user_metadata}
        )
        return f"Your CS101 attendance is {percent}%."

    executor._agent_map["attendance"] = attendance_fn
    return attendance_fn


class TestElsePair:
    def test_evaluates_gate_once_and_runs_one_branch(self, executor, monkeypatch):
        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("else-pair reply")

        _patch_llm(monkeypatch, fake_chat_create)
        _pct_attendance(executor, 75)

        result = executor.execute(
            "if attendance < 20 then timetable else bus",
            _plan(
                {"id": "t1", "agent": "attendance", "request": "CS101 percent", "condition": None},
                {
                    "id": "t2",
                    "agent": "timetable",
                    "request": "today's timetable",
                    "condition": _threshold("t1", "<", 20),
                },
                {
                    "id": "t3",
                    "agent": "bus",
                    "request": "next bus",
                    "condition": _threshold("t1", ">=", 20),
                },
            ),
            USER_META,
        )

        assert result == "else-pair reply"
        assert executor.call_order == ["attendance", "bus"]
        assert executor.gate_eval_count == 1
        assert "timetable" not in executor.agent_calls


class TestSameAgentTwice:
    def test_two_attendance_tasks_both_dispatch(self, executor, monkeypatch):
        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("percent and skip budget")

        _patch_llm(monkeypatch, fake_chat_create)
        _pct_attendance(executor, 12)

        result = executor.execute(
            "attendance then skip budget",
            _plan(
                {"id": "t1", "agent": "attendance", "request": "CS101 percent", "condition": None},
                {
                    "id": "t2",
                    "agent": "attendance",
                    "request": "skip budget",
                    "condition": _threshold("t1", "<", 20),
                },
            ),
            USER_META,
        )

        assert result == "percent and skip budget"
        assert executor.call_order == ["attendance", "attendance"]
        assert len(executor.agent_calls["attendance"]) == 2
        assert executor.agent_calls["attendance"][0]["request"] == "CS101 percent"
        assert executor.agent_calls["attendance"][1]["request"] == "skip budget"


class TestChainedConditions:
    def test_skip_propagates_when_middle_gate_fails(self, executor, monkeypatch):
        _patch_llm(monkeypatch, _raise_if_llm_called)
        _pct_attendance(executor, 75)

        result = executor.execute(
            "if attendance < 20 then timetable then bus",
            _plan(
                {"id": "t1", "agent": "attendance", "request": "CS101 percent", "condition": None},
                {
                    "id": "t2",
                    "agent": "timetable",
                    "request": "today's timetable",
                    "condition": _threshold("t1", "<", 20),
                },
                {
                    "id": "t3",
                    "agent": "bus",
                    "request": "next bus",
                    "condition": {"depends_on": "t2", "type": "ordering"},
                },
            ),
            USER_META,
        )

        assert executor.call_order == ["attendance"]
        assert "75%" in result
        assert "bus" not in executor.agent_calls
        assert "timetable" not in executor.agent_calls

    def test_chain_runs_when_both_gates_hold(self, executor, monkeypatch):
        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("chain held")

        _patch_llm(monkeypatch, fake_chat_create)
        _pct_attendance(executor, 12)

        result = executor.execute(
            "if attendance < 20 then timetable then bus",
            _plan(
                {"id": "t1", "agent": "attendance", "request": "CS101 percent", "condition": None},
                {
                    "id": "t2",
                    "agent": "timetable",
                    "request": "today's timetable",
                    "condition": _threshold("t1", "<", 20),
                },
                {
                    "id": "t3",
                    "agent": "bus",
                    "request": "next bus",
                    "condition": {"depends_on": "t2", "type": "ordering"},
                },
            ),
            USER_META,
        )

        assert result == "chain held"
        assert executor.call_order == ["attendance", "timetable", "bus"]
        assert len(llm_calls) == 1


class TestExtract:
    def test_happy_path_fills_template_and_dispatches(self, executor, monkeypatch):
        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            system = kwargs["messages"][0]["content"]
            if isinstance(system, list):
                system_text = system[0].get("text", "")
            else:
                system_text = system
            if "extract one value" in system_text.lower():
                return fake_chat_response('{"found": true, "value": "Tutorial Block"}')
            return fake_chat_response("bus to tutorial block")

        _patch_llm(monkeypatch, fake_chat_create)

        result = executor.execute(
            "next bus to my next class building",
            _plan(
                {
                    "id": "t1",
                    "agent": "timetable",
                    "request": "next class",
                    "condition": None,
                },
                {
                    "id": "t2",
                    "agent": "bus",
                    "request_template": "Find the next bus to {{building}}",
                    "fill": [
                        {
                            "var": "building",
                            "depends_on": "t1",
                            "extract": "the building the next class is in",
                        }
                    ],
                    "condition": {"depends_on": "t1", "type": "extract"},
                },
            ),
            USER_META,
        )

        assert result == "bus to tutorial block"
        assert executor.call_order == ["timetable", "bus"]
        assert executor.agent_calls["bus"][0]["request"] == (
            "Find the next bus to Tutorial Block"
        )
        extract_calls = [
            c for c in llm_calls if c.get("cache_key") == "extract"
        ]
        assert len(extract_calls) == 1
        from config import LLM_FAST_MODEL

        assert extract_calls[0].get("model") == LLM_FAST_MODEL
        synth = [c for c in llm_calls if c.get("cache_key") == "executor"]
        assert synth and "model" not in synth[0]

    def test_failure_does_not_dispatch_or_fabricate(self, executor, monkeypatch):
        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            system = kwargs["messages"][0]["content"]
            if isinstance(system, list):
                system_text = system[0].get("text", "")
            else:
                system_text = system
            if "extract one value" in system_text.lower():
                return fake_chat_response('{"found": false, "value": ""}')
            return fake_chat_response("should include extract error")

        _patch_llm(monkeypatch, fake_chat_create)

        result = executor.execute(
            "next bus to my next class building",
            _plan(
                {
                    "id": "t1",
                    "agent": "timetable",
                    "request": "next class",
                    "condition": None,
                },
                {
                    "id": "t2",
                    "agent": "bus",
                    "request_template": "Find the next bus to {{building}}",
                    "fill": [
                        {
                            "var": "building",
                            "depends_on": "t1",
                            "extract": "the building the next class is in",
                        }
                    ],
                    "condition": {"depends_on": "t1", "type": "extract"},
                },
            ),
            USER_META,
        )

        assert result == "should include extract error"
        assert executor.call_order == ["timetable"]
        assert "bus" not in executor.agent_calls
        prompt = llm_calls[-1]["messages"][1]["content"]
        assert "Couldn't determine building from the previous result." in prompt
        assert not any(
            "Tutorial" in json.dumps(c.get("messages"), default=str)
            for c in llm_calls
            if c.get("cache_key") == "extract"
        )
