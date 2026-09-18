"""In-memory latency and token tracking for the UniHelp GUI.

Agents keep doing what they already do. Callers add a request scope and
optional task timers; every LLM round is recorded automatically from llm.py.
"""

from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Iterator, Optional
from zoneinfo import ZoneInfo

_current: ContextVar[Optional[dict[str, Any]]] = ContextVar(
    "metrics_request", default=None
)
_lock = threading.Lock()
_MAX_REQUESTS = 200
_history: list[dict[str, Any]] = []
_live: dict[str, dict[str, Any]] = {}

FEATURE_LABELS = {
    "planner": "Planner",
    "executor": "Executor",
    "mess": "Mess",
    "bus": "Bus",
    "complaint": "Complaints",
    "room_booking": "Room booking",
    "attendance": "Attendance",
    "notice": "Notices",
    "timetable": "Timetable",
}


def feature_name(cache_key: str) -> str:
    key = (cache_key or "unknown").split("-", 1)[0].strip() or "unknown"
    if key.endswith("_agent"):
        key = key[: -len("_agent")]
    return key


def _empty_tokens() -> dict[str, int]:
    return {
        "prompt": 0,
        "completion": 0,
        "total": 0,
        "cached": 0,
    }


def _add_tokens(bucket: dict[str, int], prompt: int, completion: int, cached: int) -> None:
    bucket["prompt"] += prompt
    bucket["completion"] += completion
    bucket["total"] += prompt + completion
    bucket["cached"] += cached


@contextmanager
def request_scope(
    *,
    user_name: str,
    user_role: str,
    roll_number: Optional[str],
    query: str,
) -> Iterator[dict[str, Any]]:
    rec: dict[str, Any] = {
        "id": uuid.uuid4().hex[:10],
        "user": user_name or "unknown",
        "role": user_role or "",
        "roll_number": roll_number or "",
        "query": query or "",
        "started_at": datetime.now(ZoneInfo("Asia/Kolkata")).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "latency_ms": None,
        "tokens": _empty_tokens(),
        "llm_calls": [],
        "tasks": [],
        "status": "running",
        "error": None,
    }
    token = _current.set(rec)
    with _lock:
        _live[rec["id"]] = rec
    started = time.perf_counter()
    try:
        yield rec
        if rec["status"] == "running":
            rec["status"] = "ok"
    except Exception as exc:
        rec["status"] = "error"
        rec["error"] = str(exc)
        raise
    finally:
        rec["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
        with _lock:
            _live.pop(rec["id"], None)
            _history.insert(0, rec)
            del _history[_MAX_REQUESTS:]
        _current.reset(token)


@contextmanager
def task_timer(feature: str) -> Iterator[None]:
    """Wall-clock latency for one planner/executor/specialized-agent task."""
    started = time.perf_counter()
    try:
        yield
    finally:
        rec = _current.get()
        if rec is None:
            return
        rec["tasks"].append(
            {
                "feature": feature_name(feature),
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            }
        )


def record_llm_call(
    cache_key: str,
    response: Any,
    latency_ms: float,
) -> None:
    rec = _current.get()
    if rec is None:
        return

    usage = getattr(response, "usage", None)
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
    completion = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
    total = getattr(usage, "total_tokens", None) if usage else None
    if total is None:
        total = prompt + completion
    else:
        total = int(total or 0)

    details = getattr(usage, "prompt_tokens_details", None) if usage else None
    cached = getattr(details, "cached_tokens", None) if details else None
    if cached is None and usage is not None:
        cached = getattr(usage, "cache_read_input_tokens", None)
    cached = int(cached or 0)

    feature = feature_name(cache_key)
    rec["llm_calls"].append(
        {
            "feature": feature,
            "cache_key": cache_key,
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": int(total),
            "cached_tokens": cached,
            "latency_ms": round(float(latency_ms), 1),
        }
    )
    _add_tokens(rec["tokens"], prompt, completion, cached)


def reset() -> None:
    with _lock:
        _history.clear()
        _live.clear()


def snapshot() -> dict[str, Any]:
    with _lock:
        history = [dict(r) for r in _history]
        live = [dict(r) for r in _live.values()]

    all_rows = live + history
    totals = {
        "requests": len(history),
        "in_flight": len(live),
        "llm_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cached_tokens": 0,
        "avg_request_latency_ms": 0.0,
    }
    latencies: list[float] = []
    by_user: dict[str, dict[str, Any]] = {}
    by_feature: dict[str, dict[str, Any]] = {}

    def _feature(name: str) -> dict[str, Any]:
        row = by_feature.get(name)
        if row is None:
            row = {
                "feature": name,
                "label": FEATURE_LABELS.get(name, name.replace("_", " ").title()),
                "tasks": 0,
                "task_latency_ms": 0.0,
                "avg_task_latency_ms": 0.0,
                "llm_calls": 0,
                "llm_latency_ms": 0.0,
                "avg_llm_latency_ms": 0.0,
                # avg_llm_latency_ms is per *call*. A typical agent task is
                # two sequential rounds (pick tool, then write the answer),
                # so avg_task_latency_ms ≈ 2 × avg_llm_latency_ms even when
                # non-LLM work is a few dozen milliseconds. Compare a task
                # to avg_llm_sum_ms (sum of that feature's LLM rounds /
                # tasks) to see real overhead.
                "avg_llm_sum_ms": 0.0,
                "avg_overhead_ms": 0.0,
                "avg_llm_calls_per_task": 0.0,
                "tokens": _empty_tokens(),
            }
            by_feature[name] = row
        return row

    for rec in all_rows:
        if rec.get("latency_ms") is not None and rec.get("status") != "running":
            latencies.append(float(rec["latency_ms"]))
        tok = rec.get("tokens") or _empty_tokens()
        totals["prompt_tokens"] += tok.get("prompt", 0)
        totals["completion_tokens"] += tok.get("completion", 0)
        totals["cached_tokens"] += tok.get("cached", 0)
        totals["llm_calls"] += len(rec.get("llm_calls") or [])

        user_key = rec.get("user") or "unknown"
        urow = by_user.get(user_key)
        if urow is None:
            urow = {
                "user": user_key,
                "role": rec.get("role") or "",
                "requests": 0,
                "llm_calls": 0,
                "latency_ms": 0.0,
                "avg_latency_ms": 0.0,
                "tokens": _empty_tokens(),
            }
            by_user[user_key] = urow
        if rec.get("status") != "running":
            urow["requests"] += 1
            if rec.get("latency_ms") is not None:
                urow["latency_ms"] += float(rec["latency_ms"])
        urow["llm_calls"] += len(rec.get("llm_calls") or [])
        _add_tokens(
            urow["tokens"],
            tok.get("prompt", 0),
            tok.get("completion", 0),
            tok.get("cached", 0),
        )
        if rec.get("role"):
            urow["role"] = rec["role"]

        llm_calls = rec.get("llm_calls") or []
        tasks = rec.get("tasks") or []
        llm_sum = sum(float(c.get("latency_ms") or 0) for c in llm_calls)
        task_sum = sum(float(t.get("latency_ms") or 0) for t in tasks)
        rec["llm_sum_ms"] = round(llm_sum, 1)
        rec["task_sum_ms"] = round(task_sum, 1)
        rec["llm_call_count"] = len(llm_calls)
        if rec.get("latency_ms") is not None:
            rec["overhead_ms"] = round(float(rec["latency_ms"]) - llm_sum, 1)

        for task in rec.get("tasks") or []:
            frow = _feature(task.get("feature") or "unknown")
            frow["tasks"] += 1
            frow["task_latency_ms"] += float(task.get("latency_ms") or 0)

        for call in rec.get("llm_calls") or []:
            frow = _feature(call.get("feature") or "unknown")
            frow["llm_calls"] += 1
            frow["llm_latency_ms"] += float(call.get("latency_ms") or 0)
            _add_tokens(
                frow["tokens"],
                call.get("prompt_tokens", 0),
                call.get("completion_tokens", 0),
                call.get("cached_tokens", 0),
            )

    if latencies:
        totals["avg_request_latency_ms"] = round(sum(latencies) / len(latencies), 1)
    totals["total_tokens"] = totals["prompt_tokens"] + totals["completion_tokens"]

    for urow in by_user.values():
        if urow["requests"]:
            urow["avg_latency_ms"] = round(urow["latency_ms"] / urow["requests"], 1)
        urow["latency_ms"] = round(urow["latency_ms"], 1)

    for frow in by_feature.values():
        if frow["tasks"]:
            frow["avg_task_latency_ms"] = round(
                frow["task_latency_ms"] / frow["tasks"], 1
            )
            frow["avg_llm_sum_ms"] = round(
                frow["llm_latency_ms"] / frow["tasks"], 1
            )
            frow["avg_overhead_ms"] = round(
                frow["avg_task_latency_ms"] - frow["avg_llm_sum_ms"], 1
            )
            frow["avg_llm_calls_per_task"] = round(
                frow["llm_calls"] / frow["tasks"], 2
            )
        if frow["llm_calls"]:
            frow["avg_llm_latency_ms"] = round(
                frow["llm_latency_ms"] / frow["llm_calls"], 1
            )
        frow["task_latency_ms"] = round(frow["task_latency_ms"], 1)
        frow["llm_latency_ms"] = round(frow["llm_latency_ms"], 1)

    users = sorted(by_user.values(), key=lambda r: r["tokens"]["total"], reverse=True)
    features = sorted(
        by_feature.values(), key=lambda r: r["tokens"]["total"], reverse=True
    )
    return {
        "totals": totals,
        "by_user": users,
        "by_feature": features,
        "live": live,
        "requests": history[:80],
    }
