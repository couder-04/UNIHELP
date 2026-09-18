"""Live latency cases against a running UniHelp server.

These hit the real planner → executor → specialized-agent path, including
the OpenRouter LLM and Postgres. They are skipped unless UNIHELP_LIVE=1.

  UNIHELP_LIVE=1 .venv/bin/python -m pytest tests/live/test_real_latency.py -v
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

pytestmark = pytest.mark.skipif(
    os.getenv("UNIHELP_LIVE") != "1",
    reason="Set UNIHELP_LIVE=1 to run against a live UniHelp server",
)

BASE = os.getenv("UNIHELP_BASE", "http://127.0.0.1:8002")
AUTH = os.getenv("UNIHELP_AUTH_KEY", "student-demo")
TIMEOUT_S = int(os.getenv("UNIHELP_LIVE_TIMEOUT", "120"))


def _post(path, payload=None, method="POST"):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode())


def _server_up():
    try:
        urllib.request.urlopen(f"{BASE}/api/metrics", timeout=3).read()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module", autouse=True)
def _require_server():
    if not _server_up():
        pytest.skip(f"UniHelp server is not reachable at {BASE}")


def ask(message: str) -> dict:
    try:
        return _post(
            "/api/ask",
            {"message": message, "authentication_key": AUTH},
        )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        pytest.fail(f"HTTP {exc.code} for {message!r}: {body[:500]}")


def _agent_task(rec, name):
    matches = [t for t in rec.get("tasks") or [] if t.get("feature") == name]
    assert matches, f"expected a {name} task, got {rec.get('tasks')}"
    return matches[0]


def _llm_for(rec, name):
    return [c for c in rec.get("llm_calls") or [] if c.get("feature") == name]


class TestSingleAgentTwoLlmRounds:
    """The common campus lookup: planner keyword-hit, then one tool loop."""

    @pytest.mark.parametrize(
        "query,agent",
        [
            ("What is today's dinner at Kalam hostel?", "mess"),
            ("Show me the Bus 02 schedule", "bus"),
            ("What is my attendance percentage in CS101?", "attendance"),
            ("What is my class timetable today?", "timetable"),
            ("Show me the current notices", "notice"),
        ],
    )
    def test_task_wall_clock_matches_llm_sum_not_llm_average(self, query, agent):
        data = ask(query)
        rec = data.get("request")
        assert rec, f"no metrics record for {query!r}: {data}"
        assert rec.get("status") == "ok", rec.get("error")
        assert data.get("result"), f"empty reply for {query!r}"

        calls = _llm_for(rec, agent)
        task = _agent_task(rec, agent)
        llm_sum = sum(float(c["latency_ms"]) for c in calls)
        overhead = float(rec["latency_ms"]) - sum(
            float(c["latency_ms"]) for c in rec.get("llm_calls") or []
        )

        planner = [t for t in rec["tasks"] if t["feature"] == "planner"]
        assert planner, "planner task should still be timed"
        assert planner[0]["latency_ms"] < 50, "keyword fast-path should skip the planner LLM"

        if not calls:
            # fast_parse already resolved this lookup; the task is DB only.
            assert task["latency_ms"] < 800
            assert overhead < 800
            return

        assert len(calls) >= 2, (
            f"{agent} should run a tool-calling loop (pick tool + answer); "
            f"got {len(calls)} LLM call(s)"
        )

        # Non-LLM work (DB, JSON, Python) is tens of milliseconds, not seconds.
        assert task["latency_ms"] == pytest.approx(llm_sum, rel=0.08, abs=250)

        avg_llm = llm_sum / len(calls)
        ratio = task["latency_ms"] / avg_llm
        assert ratio == pytest.approx(len(calls), rel=0.1), (
            f"{agent}: task {task['latency_ms']} ms vs per-call avg {avg_llm:.1f} ms "
            f"looks like {ratio:.2f}× because there were {len(calls)} sequential rounds"
        )

        assert overhead < 500
        assert overhead / rec["latency_ms"] < 0.08


class TestMultiTaskAddsASynthesisRound:
    def test_independent_lookups_run_sequentially_then_synthesize(self):
        data = ask("Tell me today's dinner at Kalam and the Bus 02 schedule")
        rec = data.get("request")
        assert rec and rec.get("status") == "ok", rec

        mess_calls = _llm_for(rec, "mess")
        bus_calls = _llm_for(rec, "bus")
        exe_calls = _llm_for(rec, "executor")
        mess_task = _agent_task(rec, "mess")
        bus_task = _agent_task(rec, "bus")

        if mess_calls:
            assert len(mess_calls) >= 2
            mess_sum = sum(c["latency_ms"] for c in mess_calls)
            assert mess_task["latency_ms"] == pytest.approx(mess_sum, rel=0.08, abs=250)
        else:
            assert mess_task["latency_ms"] < 800

        if bus_calls:
            assert len(bus_calls) >= 2
            bus_sum = sum(c["latency_ms"] for c in bus_calls)
            assert bus_task["latency_ms"] == pytest.approx(bus_sum, rel=0.08, abs=250)
        else:
            assert bus_task["latency_ms"] < 800

        # Two agent results still need one synthesis completion.
        assert len(exe_calls) == 1
        exe_tasks = [t for t in rec["tasks"] if t["feature"] == "executor"]
        if exe_tasks:
            assert exe_tasks[0]["latency_ms"] == pytest.approx(
                exe_calls[0]["latency_ms"], rel=0.08, abs=250
            )

        assert rec["latency_ms"] >= mess_task["latency_ms"] + bus_task["latency_ms"]


class TestConditionalSkipsUnmetFollowUp:
    def test_if_then_does_not_pay_for_a_skipped_agent(self):
        data = ask(
            "What is my attendance percentage in CS101 if it is less than 20% "
            "then send me today's timetable"
        )
        rec = data.get("request")
        assert rec and rec.get("status") == "ok", rec

        attendance_calls = _llm_for(rec, "attendance")
        timetable_calls = _llm_for(rec, "timetable")
        assert len(attendance_calls) >= 2
        # Either the gate skips timetable (0 LLM) or it runs (2 LLM). Either
        # way, a skipped follow-up must not still cost an LLM round.
        assert len(timetable_calls) in (0, 2)
        if not timetable_calls:
            assert all(t["feature"] != "timetable" for t in rec["tasks"])
            reply = str(data.get("result") or "").lower()
            assert "condition" in reply or "not" in reply or "attendance" in reply
