"""Why task latency looks ~2× LLM latency, and what the overhead really is.

The Ask page used to compare:
  avg_task_latency_ms  =  sum(task wall clocks) / number of tasks
  avg_llm_latency_ms   =  sum(LLM round trips) / number of LLM *calls*

A specialized agent is a tool-calling loop: one LLM round to pick a tool,
a cheap DB call, then a second LLM round to write the answer. That is one
task and two LLM calls, so avg_task ≈ 2 × avg_llm even when Python + DB
add almost nothing. The honest comparison is task vs sum of LLM rounds
(avg_llm_sum_ms), not vs the per-call average.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

_HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_HERE))
# pytest puts tests/ on sys.path, so sibling packages shadow production modules.
sys.modules.pop("fast_parse", None)
sys.modules.pop("metrics", None)

import llm  # noqa: E402
import metrics  # noqa: E402
from mess_agent_1 import MessAgent  # noqa: E402

USER_META = {
    "role": "student",
    "name": "Test Student",
    "roll_number": "2501CS00",
    "Time and Date": "Friday, 2026-09-18 17:00:00 IST",
}


def fake_usage(prompt=100, completion=10):
    return SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=completion,
        prompt_tokens_details=SimpleNamespace(cached_tokens=0),
    )


def fake_openai_client(create_fn):
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create_fn))
    )


def _feature(snap, name):
    return next(row for row in snap["by_feature"] if row["feature"] == name)


@pytest.fixture(autouse=True)
def _reset_metrics_and_cache_mode():
    previous = llm._cache_mode
    llm._cache_mode = "plain"
    metrics.reset()
    yield
    metrics.reset()
    llm._cache_mode = previous


class TestSnapshotAveragesAreNotComparable:
    def test_two_equal_llm_rounds_make_task_look_exactly_double(self):
        with metrics.request_scope(
            user_name="Ada",
            user_role="student",
            roll_number="2501CS00",
            query="dinner",
        ) as rec:
            rec["tasks"].append({"feature": "mess", "latency_ms": 2000.0})
            rec["llm_calls"].append(
                {
                    "feature": "mess",
                    "cache_key": "mess",
                    "prompt_tokens": 1800,
                    "completion_tokens": 40,
                    "total_tokens": 1840,
                    "cached_tokens": 0,
                    "latency_ms": 1000.0,
                }
            )
            rec["llm_calls"].append(
                {
                    "feature": "mess",
                    "cache_key": "mess",
                    "prompt_tokens": 2200,
                    "completion_tokens": 80,
                    "total_tokens": 2280,
                    "cached_tokens": 0,
                    "latency_ms": 1000.0,
                }
            )

        mess = _feature(metrics.snapshot(), "mess")
        assert mess["tasks"] == 1
        assert mess["llm_calls"] == 2
        assert mess["avg_task_latency_ms"] == 2000.0
        assert mess["avg_llm_latency_ms"] == 1000.0
        assert mess["avg_task_latency_ms"] == 2 * mess["avg_llm_latency_ms"]
        assert mess["avg_llm_calls_per_task"] == 2.0
        assert mess["avg_llm_sum_ms"] == 2000.0
        assert mess["avg_overhead_ms"] == 0.0

    def test_request_breakdown_uses_llm_sum_not_llm_average(self):
        with metrics.request_scope(
            user_name="Ada",
            user_role="student",
            roll_number="2501CS00",
            query="dinner",
        ) as rec:
            rec["tasks"].append({"feature": "bus", "latency_ms": 11290.0})
            rec["llm_calls"].append(
                {
                    "feature": "bus",
                    "cache_key": "bus",
                    "prompt_tokens": 1658,
                    "completion_tokens": 70,
                    "total_tokens": 1728,
                    "cached_tokens": 0,
                    "latency_ms": 2290.0,
                }
            )
            rec["llm_calls"].append(
                {
                    "feature": "bus",
                    "cache_key": "bus",
                    "prompt_tokens": 5733,
                    "completion_tokens": 739,
                    "total_tokens": 6472,
                    "cached_tokens": 0,
                    "latency_ms": 8978.7,
                }
            )

        row = metrics.snapshot()["requests"][0]
        assert row["llm_call_count"] == 2
        assert row["llm_sum_ms"] == 11268.7
        assert row["task_sum_ms"] == 11290.0
        assert row["overhead_ms"] == pytest.approx(row["latency_ms"] - 11268.7, abs=0.2)


class TestTwoRoundAgentLoop:
    def test_mess_tool_loop_makes_one_task_and_two_llm_calls(self, monkeypatch):
        round_s = 0.05
        n = {"calls": 0}

        def fake_create(**kwargs):
            time.sleep(round_s)
            n["calls"] += 1
            if n["calls"] == 1:
                tool = SimpleNamespace(
                    id="call_menu",
                    function=SimpleNamespace(
                        name="get_menu",
                        arguments=json.dumps(
                            {"hostel": "Kalam", "menu_date": "today"}
                        ),
                    ),
                )
                message = SimpleNamespace(content=None, tool_calls=[tool])
            else:
                message = SimpleNamespace(
                    content="Dinner at Kalam is dal and rice.",
                    tool_calls=None,
                )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message)],
                usage=fake_usage(),
            )

        monkeypatch.setattr(llm, "get_client", lambda: fake_openai_client(fake_create))
        monkeypatch.setattr("mess_agent_1.parse_mess_query", lambda *a, **k: None)

        agent = MessAgent()
        agent.execute_tool = lambda name, arguments, role: {
            "status": "ok",
            "hostel": "Kalam",
            "items": "dal, rice",
        }

        with metrics.request_scope(
            user_name="Ada",
            user_role="student",
            roll_number="2501CS00",
            query="What is dinner at Kalam?",
        ):
            with metrics.task_timer("mess"):
                reply = agent.chat("What is dinner at Kalam?", USER_META)

        assert "dal" in reply.lower() or "Dinner" in reply
        assert n["calls"] == 2

        snap = metrics.snapshot()
        rec = snap["requests"][0]
        mess = _feature(snap, "mess")

        assert rec["llm_call_count"] == 2
        assert mess["llm_calls"] == 2
        assert mess["tasks"] == 1
        assert mess["avg_llm_calls_per_task"] == 2.0

        ratio = mess["avg_task_latency_ms"] / mess["avg_llm_latency_ms"]
        assert 1.7 <= ratio <= 2.3

        assert mess["avg_llm_sum_ms"] == pytest.approx(
            mess["avg_task_latency_ms"], abs=25
        )
        assert abs(mess["avg_overhead_ms"]) < 25
        assert rec["overhead_ms"] < 25
        assert rec["llm_sum_ms"] / rec["latency_ms"] > 0.8

    def test_non_llm_work_is_visible_as_overhead_not_as_double_llm(self, monkeypatch):
        def fake_create(**kwargs):
            time.sleep(0.02)
            message = SimpleNamespace(
                content="Dinner at Kalam is dal.",
                tool_calls=None,
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message)],
                usage=fake_usage(),
            )

        monkeypatch.setattr(llm, "get_client", lambda: fake_openai_client(fake_create))
        monkeypatch.setattr("mess_agent_1.parse_mess_query", lambda *a, **k: None)
        agent = MessAgent()

        with metrics.request_scope(
            user_name="Ada",
            user_role="student",
            roll_number="2501CS00",
            query="dinner",
        ):
            with metrics.task_timer("mess"):
                time.sleep(0.05)
                agent.chat("dinner", USER_META)

        mess = _feature(metrics.snapshot(), "mess")
        assert mess["llm_calls"] == 1
        assert mess["avg_llm_calls_per_task"] == 1.0
        assert mess["avg_overhead_ms"] >= 40
        assert mess["avg_task_latency_ms"] == pytest.approx(
            mess["avg_llm_sum_ms"] + mess["avg_overhead_ms"], abs=1
        )
        assert mess["avg_llm_sum_ms"] == mess["avg_llm_latency_ms"]


class TestExecutorSynthesisIsTimed:
    def test_multi_task_records_an_executor_task_around_the_synthesis_call(
        self, monkeypatch
    ):
        spec = importlib.util.spec_from_file_location(
            "unihelp_executor_latency",
            _HERE / "executor.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        def fake_create(**kwargs):
            message = SimpleNamespace(
                content="dinner and bus combined",
                tool_calls=None,
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message)],
                usage=fake_usage(),
            )

        monkeypatch.setattr(llm, "get_client", lambda: fake_openai_client(fake_create))
        monkeypatch.setattr(module, "chat_create", llm.chat_create)

        ex = module.Executor()
        for name in list(ex._agent_map):
            ex._agent_map[name] = (
                lambda request, user_metadata, n=name: f"{n}:{request}"
            )

        with metrics.request_scope(
            user_name="Ada",
            user_role="student",
            roll_number="2501CS00",
            query="dinner and bus",
        ):
            result = ex.execute(
                "dinner and bus",
                {
                    "tasks": [
                        {"agent": "mess", "request": "Kalam dinner"},
                        {"agent": "bus", "request": "Bus 02"},
                    ]
                },
                USER_META,
            )

        assert result == "dinner and bus combined"
        snap = metrics.snapshot()
        rec = snap["requests"][0]
        features = {t["feature"] for t in rec["tasks"]}
        assert "executor" in features
        assert rec["llm_call_count"] == 1
        exe = _feature(snap, "executor")
        assert exe["tasks"] == 1
        assert exe["llm_calls"] == 1
        assert exe["avg_llm_calls_per_task"] == 1.0


class TestMessFastParseSkipsLlm:
    def test_unambiguous_menu_lookup_is_db_only(self, monkeypatch):
        monkeypatch.setattr(
            "mess_agent_1.get_menu",
            lambda hostel, date: {
                "status": "success",
                "hostel": hostel,
                "date": date,
                "meals": {"dinner": "dal, rice"},
            },
        )

        def boom(**kwargs):
            raise AssertionError("fast_parse hit must not call the LLM")

        monkeypatch.setattr(llm, "get_client", lambda: fake_openai_client(boom))

        agent = MessAgent()
        with metrics.request_scope(
            user_name="Ada",
            user_role="student",
            roll_number="2501CS00",
            query="What is today's dinner at Kalam?",
        ):
            with metrics.task_timer("mess"):
                reply = agent.chat(
                    "What is today's dinner at Kalam?",
                    USER_META,
                )

        assert "dal" in reply.lower() or "Kalam" in reply
        rec = metrics.snapshot()["requests"][0]
        assert rec["llm_call_count"] == 0
        assert rec["llm_sum_ms"] == 0.0
        mess_tasks = [t for t in rec["tasks"] if t["feature"] == "mess"]
        assert mess_tasks
        assert mess_tasks[0]["latency_ms"] < 50
