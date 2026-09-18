"""Deterministic Executor dispatch: no live DB or LLM."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def fake_chat_response(content="combined reply"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


USER_META = {
    "role": "student",
    "name": "Test Student",
    "roll_number": "2501CS00",
}


def _task(agent, request, condition=None):
    return {"agent": agent, "request": request, "condition": condition}


def _plan(*tasks, status=None, message=None):
    plan = {"tasks": list(tasks)}
    if status is not None:
        plan["status"] = status
    if message is not None:
        plan["message"] = message
    return plan


def _raise_if_llm_called(*args, **kwargs):
    raise AssertionError("chat_create should not be called")


def _patch_llm(monkeypatch, fn):
    # conftest loads executor.py as unihelp_executor so this test package
    # does not shadow the production module.
    monkeypatch.setattr("unihelp_executor.chat_create", fn)


class TestSingleTask:
    def test_returns_agent_result_without_llm(self, executor, monkeypatch):
        _patch_llm(monkeypatch, _raise_if_llm_called)

        result = executor.execute(
            "What's for dinner?",
            _plan(_task("mess", "today dinner at Kalam")),
            USER_META,
        )

        assert result == "mess:today dinner at Kalam"
        assert executor.call_order == ["mess"]
        assert len(executor.agent_calls["mess"]) == 1
        assert executor.agent_calls["mess"][0]["request"] == "today dinner at Kalam"
        assert executor.agent_calls["mess"][0]["user_metadata"] is USER_META


class TestMultiTask:
    def test_two_task_plan_one_synthesis_call(self, executor, monkeypatch):
        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("dinner and bus combined")

        _patch_llm(monkeypatch, fake_chat_create)

        result = executor.execute(
            "dinner and bus",
            _plan(
                _task("mess", "Kalam dinner"),
                _task("bus", "Bus 02 schedule"),
            ),
            USER_META,
        )

        assert result == "dinner and bus combined"
        assert executor.call_order == ["mess", "bus"]
        assert len(llm_calls) == 1
        assert llm_calls[0].get("tools") is None
        assert "tool_choice" not in llm_calls[0]
        assert llm_calls[0]["cache_key"] == "executor"
        # Synthesis is the user-facing reply: stay on the default (strong) model.
        assert "model" not in llm_calls[0]
        prefix = llm_calls[0]["messages"][0]
        assert prefix["role"] == "system"
        assert prefix["content"][0]["cache_control"] == {"type": "ephemeral"}
        prompt = llm_calls[0]["messages"][1]["content"]
        assert "mess:Kalam dinner" in prompt
        assert "bus:Bus 02 schedule" in prompt

    def test_three_task_plan_one_synthesis_call(self, executor, monkeypatch):
        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("three-way reply")

        _patch_llm(monkeypatch, fake_chat_create)

        result = executor.execute(
            "menu, bus, notices",
            _plan(
                _task("mess", "menu"),
                _task("bus", "next bus"),
                _task("notice", "current notices"),
            ),
            USER_META,
        )

        assert result == "three-way reply"
        assert executor.call_order == ["mess", "bus", "notice"]
        assert len(llm_calls) == 1
        assert llm_calls[0].get("tools") is None


class TestUnknownAgent:
    def test_unknown_agent_does_not_raise_other_tasks_still_run(
        self, executor, monkeypatch
    ):
        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("partial reply")

        _patch_llm(monkeypatch, fake_chat_create)

        result = executor.execute(
            "menu and mystery",
            _plan(
                _task("mess", "Kalam dinner"),
                _task("not_a_real_agent", "do something"),
            ),
            USER_META,
        )

        assert result == "partial reply"
        assert executor.call_order == ["mess"]
        assert "not_a_real_agent" not in executor.agent_calls
        assert len(llm_calls) == 1
        prompt = llm_calls[0]["messages"][1]["content"]
        assert "Unknown agent: not_a_real_agent" in prompt
        assert "mess:Kalam dinner" in prompt


class TestUnsupportedPlan:
    def test_empty_tasks_returns_message_without_llm(self, executor, monkeypatch):
        _patch_llm(monkeypatch, _raise_if_llm_called)

        result = executor.execute(
            "write a poem",
            _plan(
                status="unsupported",
                message="This service is not currently available.",
            ),
            USER_META,
        )

        assert result == "This service is not currently available."
        assert executor.call_order == []

    def test_unsupported_status_even_with_default_message(self, executor, monkeypatch):
        _patch_llm(monkeypatch, _raise_if_llm_called)

        result = executor.execute(
            "???",
            {"tasks": [], "status": "unsupported"},
            USER_META,
        )

        assert result == "This service is not currently available."
        assert executor.call_order == []


class TestAgentException:
    def test_raising_agent_becomes_error_result(self, executor, monkeypatch):
        _patch_llm(monkeypatch, _raise_if_llm_called)

        def boom(request, user_metadata):
            raise RuntimeError("mess db is down")

        executor._agent_map["mess"] = boom

        result = executor.execute(
            "dinner?",
            _plan(_task("mess", "today dinner")),
            USER_META,
        )

        assert result == "mess db is down"

    def test_raising_agent_does_not_block_sibling_tasks(self, executor, monkeypatch):
        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("bus still worked")

        _patch_llm(monkeypatch, fake_chat_create)

        def boom(request, user_metadata):
            raise RuntimeError("mess db is down")

        executor._agent_map["mess"] = boom

        result = executor.execute(
            "dinner and bus",
            _plan(
                _task("mess", "Kalam dinner"),
                _task("bus", "Bus 02"),
            ),
            USER_META,
        )

        assert result == "bus still worked"
        assert executor.call_order == ["bus"]
        assert len(llm_calls) == 1
        prompt = llm_calls[0]["messages"][1]["content"]
        assert "mess db is down" in prompt
        assert "bus:Bus 02" in prompt


class TestConditionOrdering:
    def test_dependent_task_runs_after_referenced_agent(self, executor, monkeypatch):
        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("ordered reply")

        _patch_llm(monkeypatch, fake_chat_create)

        result = executor.execute(
            "bus after menu",
            _plan(
                _task(
                    "bus",
                    "next bus after dinner",
                    condition="after the mess result",
                ),
                _task("mess", "Kalam dinner"),
            ),
            USER_META,
        )

        assert result == "ordered reply"
        assert executor.call_order == ["mess", "bus"]
        assert len(llm_calls) == 1


class TestConditionalSkip:
    def test_skips_followup_when_percentage_condition_fails(
        self, executor, monkeypatch
    ):
        _patch_llm(monkeypatch, _raise_if_llm_called)

        def attendance_fn(request, user_metadata):
            executor.call_order.append("attendance")
            return "Your CS101 attendance is 75%."

        def timetable_fn(request, user_metadata):
            executor.call_order.append("timetable")
            return "Today: CS101 at 10:00."

        executor._agent_map["attendance"] = attendance_fn
        executor._agent_map["timetable"] = timetable_fn

        result = executor.execute(
            "attendance then timetable",
            _plan(
                _task("attendance", "CS101 percent"),
                _task(
                    "timetable",
                    "today's timetable",
                    condition="it is less than 20%",
                ),
            ),
            USER_META,
        )

        assert executor.call_order == ["attendance"]
        assert "75%" in result
        assert "did not look up timetable" in result
        assert "Today: CS101" not in result

    def test_runs_followup_when_percentage_condition_holds(
        self, executor, monkeypatch
    ):
        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("low attendance plus timetable")

        _patch_llm(monkeypatch, fake_chat_create)

        def attendance_fn(request, user_metadata):
            executor.call_order.append("attendance")
            return "Your CS101 attendance is 12%."

        def timetable_fn(request, user_metadata):
            executor.call_order.append("timetable")
            return "Today: CS101 at 10:00."

        executor._agent_map["attendance"] = attendance_fn
        executor._agent_map["timetable"] = timetable_fn

        result = executor.execute(
            "attendance then timetable",
            _plan(
                _task("attendance", "CS101 percent"),
                _task(
                    "timetable",
                    "today's timetable",
                    condition="it is less than 20%",
                ),
            ),
            USER_META,
        )

        assert result == "low attendance plus timetable"
        assert executor.call_order == ["attendance", "timetable"]
        assert len(llm_calls) == 1
