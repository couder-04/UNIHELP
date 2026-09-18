#!/usr/bin/env python3
"""HTTP-client benchmark harness for a running UniHelp server.

The Starlette app must already be listening (typically ``python main.py``
on 127.0.0.1:8002). This script only POSTs to ``/api/ask``; it does not
import planner/executor/agents or start the server in-process.

Usage:
    python benchmarks/run_benchmark.py --label current --repeats 3
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
DEFAULT_QUERIES = HERE / "queries.csv"
DEFAULT_BASE_URL = "http://127.0.0.1:8002"
DEFAULT_TIMEOUT_S = 180

DOMAIN_FEATURES = (
    "mess",
    "bus",
    "complaint",
    "room_booking",
    "attendance",
    "notice",
    "timetable",
)
FEATURE_COUNT_COLUMNS = ("planner", "executor") + DOMAIN_FEATURES

CSV_COLUMNS = (
    "query_id",
    "run_index",
    "query_type",
    "llm_calls_total",
    "planner_calls",
    "executor_calls",
    "mess_calls",
    "bus_calls",
    "complaint_calls",
    "room_booking_calls",
    "attendance_calls",
    "notice_calls",
    "timetable_calls",
    "domain_agent_calls_total",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_tokens",
    "latency_ms",
    "llm_latency_ms",
    "approx_non_llm_latency_ms",
    "estimated_cost",
    "status",
    "error",
)

DB_LIMITATION_NOTE = (
    "Note: db_calls/db_latency_ms count get_connection() checkout-to-close "
    "time (DB + whatever the caller did while holding the connection), not "
    "per-query SQL timing."
)


# ---------------------------------------------------------------------------
# Query loading
# ---------------------------------------------------------------------------

def load_queries(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    required = {"query_id", "query_type", "user_input", "authentication_key"}
    missing = required - set(rows[0].keys() if rows else required)
    if missing:
        raise SystemExit(f"{path} is missing columns: {sorted(missing)}")
    return rows


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def post_ask(
    base_url: str,
    message: str,
    authentication_key: str,
    timeout: float,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """POST /api/ask. Returns (parsed_json_or_none, error_or_none)."""
    url = base_url.rstrip("/") + "/api/ask"
    payload = json.dumps(
        {"message": message, "authentication_key": authentication_key}
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return None, f"HTTP {exc.code}: {body[:500]}"
        extra = data.get("error") or body[:500]
        return data, f"HTTP {exc.code}: {extra}"
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return None, f"connection error: {reason}"
    except TimeoutError:
        return None, f"timeout after {timeout}s"
    except Exception as exc:  # noqa: BLE001 — one row must not abort the run
        return None, f"{type(exc).__name__}: {exc}"

    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"


# ---------------------------------------------------------------------------
# Per-request derivation
# ---------------------------------------------------------------------------

def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def count_llm_calls_by_feature(llm_calls: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = {name: 0 for name in FEATURE_COUNT_COLUMNS}
    for call in llm_calls:
        feature = str(call.get("feature") or "").strip()
        if feature in counts:
            counts[feature] += 1
    return counts


def llm_latency_ms(llm_calls: Iterable[dict[str, Any]]) -> float:
    return round(
        sum(_as_float(call.get("latency_ms")) for call in llm_calls),
        1,
    )


def approx_non_llm_latency_ms(
    tasks: Iterable[dict[str, Any]],
    llm_calls: Iterable[dict[str, Any]],
) -> float:
    """Task wall-clock minus LLM wait for the same feature, summed.

    This is NOT DB-only time. It folds together DB, Python, tool execution,
    serialization, and other application overhead. LLM latency is subtracted
    once per feature so two tasks of the same feature do not double-count.
    """
    llm_by_feature: dict[str, float] = defaultdict(float)
    for call in llm_calls:
        feature = str(call.get("feature") or "").strip()
        llm_by_feature[feature] += _as_float(call.get("latency_ms"))

    task_by_feature: dict[str, float] = defaultdict(float)
    for task in tasks:
        feature = str(task.get("feature") or "").strip()
        task_by_feature[feature] += _as_float(task.get("latency_ms"))

    total = 0.0
    for feature, task_ms in task_by_feature.items():
        total += task_ms - llm_by_feature.get(feature, 0.0)
    return round(total, 1)


def estimated_cost(
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    input_price: Optional[float],
    output_price: Optional[float],
    cached_price: Optional[float],
) -> float:
    if input_price is None and output_price is None:
        return 0.0
    inp = (input_price or 0.0) * (input_tokens / 1000.0)
    out = (output_price or 0.0) * (output_tokens / 1000.0)
    cost = inp + out
    if cached_price is not None and input_price is not None:
        cost -= (cached_tokens / 1000.0) * (input_price - cached_price)
    return round(cost, 8)


def empty_row(
    query_id: str,
    run_index: int,
    query_type: str,
    status: str,
    error: str,
    input_price: Optional[float],
    output_price: Optional[float],
    cached_price: Optional[float],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "query_id": query_id,
        "run_index": run_index,
        "query_type": query_type,
        "llm_calls_total": 0,
        "domain_agent_calls_total": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_tokens": 0,
        "latency_ms": 0.0,
        "llm_latency_ms": 0.0,
        "approx_non_llm_latency_ms": 0.0,
        "estimated_cost": estimated_cost(
            0, 0, 0, input_price, output_price, cached_price
        ),
        "status": status,
        "error": error,
    }
    for name in FEATURE_COUNT_COLUMNS:
        row[f"{name}_calls"] = 0
    return row


def derive_row(
    query_id: str,
    run_index: int,
    query_type: str,
    rec: dict[str, Any],
    input_price: Optional[float],
    output_price: Optional[float],
    cached_price: Optional[float],
) -> dict[str, Any]:
    llm_calls = rec.get("llm_calls") or []
    if not isinstance(llm_calls, list):
        raise ValueError("llm_calls is not a list")
    tasks = rec.get("tasks") or []
    if not isinstance(tasks, list):
        raise ValueError("tasks is not a list")
    tokens = rec.get("tokens") or {}
    if not isinstance(tokens, dict):
        raise ValueError("tokens is not an object")

    counts = count_llm_calls_by_feature(llm_calls)
    domain_total = sum(counts[name] for name in DOMAIN_FEATURES)
    input_tokens = _as_int(tokens.get("prompt"))
    output_tokens = _as_int(tokens.get("completion"))
    total_tokens = _as_int(tokens.get("total"), input_tokens + output_tokens)
    cached_tokens = _as_int(tokens.get("cached"))

    row: dict[str, Any] = {
        "query_id": query_id,
        "run_index": run_index,
        "query_type": query_type,
        "llm_calls_total": len(llm_calls),
        "domain_agent_calls_total": domain_total,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cached_tokens": cached_tokens,
        "latency_ms": round(_as_float(rec.get("latency_ms")), 1),
        "llm_latency_ms": llm_latency_ms(llm_calls),
        "approx_non_llm_latency_ms": approx_non_llm_latency_ms(tasks, llm_calls),
        "estimated_cost": estimated_cost(
            input_tokens,
            output_tokens,
            cached_tokens,
            input_price,
            output_price,
            cached_price,
        ),
        "status": rec.get("status") or "",
        "error": rec.get("error") or "",
    }
    for name in FEATURE_COUNT_COLUMNS:
        row[f"{name}_calls"] = counts[name]
    return row


def measure_one(
    query: dict[str, str],
    run_index: int,
    base_url: str,
    timeout: float,
    input_price: Optional[float],
    output_price: Optional[float],
    cached_price: Optional[float],
) -> tuple[dict[str, Any], Optional[dict[str, Any]], Any]:
    """Run one POST. Returns (csv_row, metrics_record_or_none, result)."""
    query_id = str(query["query_id"])
    query_type = str(query["query_type"])
    data, transport_error = post_ask(
        base_url,
        query["user_input"],
        query["authentication_key"],
        timeout,
    )
    if data is None:
        return (
            empty_row(
                query_id,
                run_index,
                query_type,
                "request_failed",
                transport_error or "unknown transport error",
                input_price,
                output_price,
                cached_price,
            ),
            None,
            None,
        )

    rec = data.get("request")
    result = data.get("result")
    if rec is None:
        reason = transport_error or data.get("error") or (
            "request is None (handshake-detection path or no metrics record)"
        )
        if result not in (None, ""):
            reason = f"{reason}; result={result!r}"[:500]
        return (
            empty_row(
                query_id,
                run_index,
                query_type,
                "request_failed",
                str(reason),
                input_price,
                output_price,
                cached_price,
            ),
            None,
            result,
        )

    if not isinstance(rec, dict):
        return (
            empty_row(
                query_id,
                run_index,
                query_type,
                "request_failed",
                "malformed metrics: request is not an object",
                input_price,
                output_price,
                cached_price,
            ),
            None,
            result,
        )

    try:
        row = derive_row(
            query_id,
            run_index,
            query_type,
            rec,
            input_price,
            output_price,
            cached_price,
        )
    except (TypeError, ValueError, KeyError) as exc:
        return (
            empty_row(
                query_id,
                run_index,
                query_type,
                "request_failed",
                f"malformed metrics: {exc}",
                input_price,
                output_price,
                cached_price,
            ),
            rec if isinstance(rec, dict) else None,
            result,
        )

    if transport_error and row["status"] in ("", "ok"):
        # HTTP error body still carried a metrics record; keep the record
        # but surface the transport failure.
        row["status"] = "request_failed"
        row["error"] = transport_error
    return row, rec, result


# ---------------------------------------------------------------------------
# Aggregation / reporting
# ---------------------------------------------------------------------------

def percentile(values: list[float], p: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    k = (len(ordered) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def mean(values: list[float]) -> Optional[float]:
    if not values:
        return None
    return statistics.fmean(values)


def fmt_num(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def is_success(row: dict[str, Any]) -> bool:
    return str(row.get("status") or "") == "ok"


def query_type_group(query_type: str) -> str:
    if str(query_type).startswith("edge_"):
        return "edge_*"
    return str(query_type)


def successful_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if is_success(row)]


def headline_metrics(rows: list[dict[str, Any]]) -> dict[str, Optional[float]]:
    ok = successful_rows(rows)
    latencies = [_as_float(r["latency_ms"]) for r in ok]
    return {
        "llm_calls_per_request": mean(
            [_as_float(r["llm_calls_total"]) for r in ok]
        ),
        "executor_calls_per_request": mean(
            [_as_float(r["executor_calls"]) for r in ok]
        ),
        "tokens_per_request": mean([_as_float(r["total_tokens"]) for r in ok]),
        "mean_latency_ms": mean(latencies),
        "p50_latency_ms": percentile(latencies, 50),
        "p95_latency_ms": percentile(latencies, 95),
        "estimated_cost_per_request": mean(
            [_as_float(r["estimated_cost"]) for r in ok]
        ),
        "n_success": float(len(ok)),
        "n_total": float(len(list(rows))),
    }


def per_query_type_metrics(
    rows: list[dict[str, Any]],
) -> list[tuple[str, dict[str, Optional[float]]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for row in rows:
        key = query_type_group(row.get("query_type") or "")
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(row)
    preferred = ["single", "multi_independent", "multi_dependent", "ambiguous", "edge_*"]
    seen = set()
    ordered_keys: list[str] = []
    for key in preferred + order:
        if key in grouped and key not in seen:
            ordered_keys.append(key)
            seen.add(key)
    return [(key, headline_metrics(grouped[key])) for key in ordered_keys]


def per_feature_means(rows: list[dict[str, Any]]) -> dict[str, Optional[float]]:
    ok = successful_rows(rows)
    out: dict[str, Optional[float]] = {}
    for name in FEATURE_COUNT_COLUMNS:
        col = f"{name}_calls"
        out[name] = mean([_as_float(r[col]) for r in ok]) if ok else None
    return out


def load_result_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as fh:
        raw_rows = list(csv.DictReader(fh))
    rows: list[dict[str, Any]] = []
    numeric_int = {
        "query_id",
        "run_index",
        "llm_calls_total",
        "domain_agent_calls_total",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cached_tokens",
        *[f"{name}_calls" for name in FEATURE_COUNT_COLUMNS],
    }
    numeric_float = {
        "latency_ms",
        "llm_latency_ms",
        "approx_non_llm_latency_ms",
        "estimated_cost",
    }
    for raw in raw_rows:
        row: dict[str, Any] = dict(raw)
        for key in numeric_int:
            if key in row:
                row[key] = _as_int(row[key])
        for key in numeric_float:
            if key in row:
                row[key] = _as_float(row[key])
        rows.append(row)
    return rows


def _headline_table(metrics: dict[str, Optional[float]]) -> list[str]:
    rows = [
        ("LLM calls/request", fmt_num(metrics["llm_calls_per_request"])),
        (
            "Executor LLM calls/request",
            fmt_num(metrics["executor_calls_per_request"]),
        ),
        ("Total tokens/request", fmt_num(metrics["tokens_per_request"], 1)),
        ("Mean latency (ms)", fmt_num(metrics["mean_latency_ms"], 1)),
        ("P50 latency (ms)", fmt_num(metrics["p50_latency_ms"], 1)),
        ("P95 latency (ms)", fmt_num(metrics["p95_latency_ms"], 1)),
        (
            "Estimated cost/request",
            fmt_num(metrics["estimated_cost_per_request"], 6),
        ),
    ]
    lines = [
        "| Metric | Mean |",
        "| --- | ---: |",
    ]
    for label, value in rows:
        lines.append(f"| {label} | {value} |")
    return lines


FEATURE_LABELS = {
    "planner": "Planner",
    "executor": "Executor",
    "mess": "Mess",
    "bus": "Bus",
    "complaint": "Complaint",
    "room_booking": "Room Booking",
    "attendance": "Attendance",
    "notice": "Notice",
    "timetable": "Timetable",
}


def write_report(
    path: Path,
    *,
    label: str,
    base_url: str,
    repeats: int,
    timestamp: str,
    queries: list[dict[str, str]],
    rows: list[dict[str, Any]],
    dep_observations: list[dict[str, Any]],
    pricing_supplied: bool,
) -> None:
    ok = successful_rows(rows)
    failed = [r for r in rows if not is_success(r)]
    head = headline_metrics(rows)
    query_by_id = {str(q["query_id"]): q for q in queries}

    lines: list[str] = [
        f"# UniHelp benchmark — `{label}`",
        "",
        f"- Benchmark timestamp: {timestamp}",
        f"- Base URL: `{base_url}`",
        f"- Repeat count: {repeats}",
        f"- Total requests: {len(rows)}",
        f"- Successful requests (`status == ok`): {len(ok)}",
        f"- Failed requests (`status != ok`): {len(failed)}",
        f"- Pricing supplied: {'yes' if pricing_supplied else 'no (estimated_cost is 0.0)'}",
        "",
        "## Headline metrics",
        "",
        "Across successful requests:",
        "",
        *_headline_table(head),
        "",
        "## Query-type breakdown",
        "",
        "Same headline metrics grouped by `query_type`. Rows whose type "
        "starts with `edge_` are grouped as `edge_*`.",
        "",
    ]

    type_rows = per_query_type_metrics(rows)
    if type_rows:
        lines.append(
            "| query_type | n_ok | LLM calls | Executor calls | "
            "Tokens | Mean latency (ms) | P50 (ms) | P95 (ms) | Cost |"
        )
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for key, metrics in type_rows:
            lines.append(
                "| {key} | {n} | {llm} | {exe} | {tok} | {mean} | {p50} | {p95} | {cost} |".format(
                    key=key,
                    n=fmt_num(metrics["n_success"], 0),
                    llm=fmt_num(metrics["llm_calls_per_request"]),
                    exe=fmt_num(metrics["executor_calls_per_request"]),
                    tok=fmt_num(metrics["tokens_per_request"], 1),
                    mean=fmt_num(metrics["mean_latency_ms"], 1),
                    p50=fmt_num(metrics["p50_latency_ms"], 1),
                    p95=fmt_num(metrics["p95_latency_ms"], 1),
                    cost=fmt_num(metrics["estimated_cost_per_request"], 6),
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Per-feature LLM calls",
            "",
            "Averaged per successful request. Counts come from "
            "`request.llm_calls[].feature` only — not from task count or latency.",
            "",
            "| Feature | Avg calls/request |",
            "| --- | ---: |",
        ]
    )
    feature_means = per_feature_means(rows)
    for name in FEATURE_COUNT_COLUMNS:
        lines.append(
            f"| {FEATURE_LABELS[name]} | {fmt_num(feature_means[name])} |"
        )

    lines.extend(
        [
            "",
            "## Fast-path observations",
            "",
            "`fast_path`, `planner_llm_used`, `executor_llm_used`, and "
            "`synthesis_llm_used` are **not** named fields on the `/api/ask` "
            "metrics record. The values below are taken only from "
            "`request.llm_calls` feature counts (or listed as not exposed).",
            "",
            "- `planner_llm_used`: true when `planner_calls > 0` on that row.",
            "- `executor_llm_used`: true when `executor_calls > 0` on that row.",
            "- `synthesis_llm_used`: **not exposed**. Metrics do not distinguish "
            "an Executor synthesis completion from any other Executor LLM call.",
            "- `fast_path`: **not exposed**. A row with `llm_calls_total == 0` "
            "completed with no LLM round; the record does not name the mechanism "
            "(parser, keyword planner, single-task dispatch, unsupported short-"
            "circuit, etc.).",
            "",
            "Queries with **zero LLM calls** (successful rows only):",
            "",
        ]
    )
    zero = [
        r
        for r in ok
        if _as_int(r.get("llm_calls_total")) == 0
    ]
    if not zero:
        lines.append("_None in this run._")
        lines.append("")
    else:
        lines.append("| query_id | query | run_index | latency_ms | planner_llm_used | executor_llm_used |")
        lines.append("| --- | --- | ---: | ---: | --- | --- |")
        for r in zero:
            qid = str(r["query_id"])
            qtext = (query_by_id.get(qid) or {}).get("user_input", "")
            lines.append(
                "| {qid} | {q} | {run} | {lat} | no | no |".format(
                    qid=qid,
                    q=qtext.replace("|", "\\|"),
                    run=r["run_index"],
                    lat=fmt_num(_as_float(r["latency_ms"]), 1),
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Dependency verification",
            "",
            "Queries 10 and 11 are labeled `multi_dependent`. Planner "
            "`condition` / `depends_on` / task `id` / per-task `request` are "
            "**not** fields on `request.tasks` as returned by `/api/ask`. "
            "`metrics.task_timer` records only `{feature, latency_ms}`.",
            "",
            "The tables below dump the actual `request.tasks` payload. "
            "Missing `condition` is reported as not present — it is **not** "
            "inferred from the user phrasing or from which features ran.",
            "",
        ]
    )
    if not dep_observations:
        lines.append("_No responses captured for query IDs 10 and 11._")
        lines.append("")
    else:
        for obs in dep_observations:
            lines.append(
                f"### Query {obs['query_id']} — run {obs['run_index']}"
            )
            lines.append("")
            lines.append(f"- status: `{obs.get('status')}`")
            lines.append(f"- query_type: `{obs.get('query_type')}`")
            if obs.get("plan") is not None:
                lines.append("- planner `plan`:")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(obs.get("plan"), indent=2, default=str)[:4000])
                lines.append("```")
                lines.append("")
            tasks = obs.get("tasks") or []
            if not tasks:
                lines.append("- `request.tasks`: empty or missing")
                lines.append("")
                lines.append(
                    "No task entries, so **condition cannot be verified**. "
                    "This row did not expose dependency handling."
                )
                lines.append("")
                continue
            lines.append("")
            lines.append(
                "| task index | feature | latency_ms | task IDs | agent | "
                "request | condition | depends_on | condition type |"
            )
            lines.append(
                "| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |"
            )
            any_condition = False
            for idx, task in enumerate(tasks):
                if not isinstance(task, dict):
                    lines.append(
                        f"| {idx} | _(not an object)_ |  | not present | "
                        "not present | not present | not present | "
                        "not present | not present |"
                    )
                    continue
                condition = task.get("condition", "not present")
                if "condition" in task and task.get("condition") not in (None,):
                    any_condition = True
                    cond_cell = json.dumps(task.get("condition"), default=str)
                elif "condition" in task:
                    cond_cell = "null"
                else:
                    cond_cell = "not present"
                depends = task.get("depends_on", "not present")
                if "depends_on" not in task:
                    depends_cell = "not present"
                else:
                    depends_cell = json.dumps(depends, default=str)
                ctype = "not present"
                if isinstance(task.get("condition"), dict):
                    ctype = str(task["condition"].get("type") or "null")
                    any_condition = True
                tid = task.get("task_id", task.get("id", "not present"))
                if "task_id" not in task and "id" not in task:
                    tid = "not present"
                agent = task.get("agent", task.get("feature", "not present"))
                req = task.get("request", "not present")
                if "request" not in task:
                    req = "not present"
                lines.append(
                    "| {idx} | {feat} | {lat} | {tid} | {agent} | {req} | "
                    "{cond} | {dep} | {ctype} |".format(
                        idx=idx,
                        feat=task.get("feature", ""),
                        lat=fmt_num(_as_float(task.get("latency_ms")), 1),
                        tid=_cell(tid),
                        agent=_cell(agent),
                        req=_cell(req),
                        cond=_cell(cond_cell),
                        dep=_cell(depends_cell),
                        ctype=_cell(ctype),
                    )
                )
            lines.append("")
            if not any_condition:
                lines.append(
                    "**condition is not present (or null) on every task.** "
                    "This query did not expose dependency handling through "
                    "`request.tasks`. Do not treat the `multi_dependent` label "
                    "as confirmed by this run."
                )
                lines.append("")

    lines.extend(
        [
            "## Failures",
            "",
        ]
    )
    if not failed:
        lines.append("_No rows with `status != ok`._")
        lines.append("")
    else:
        lines.append("| query_id | run_index | status | error |")
        lines.append("| --- | ---: | --- | --- |")
        for r in failed:
            err = str(r.get("error") or "").replace("\n", " ").replace("|", "\\|")
            if len(err) > 300:
                err = err[:297] + "..."
            lines.append(
                f"| {r['query_id']} | {r['run_index']} | {r['status']} | {err} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Known limitations",
            "",
            f"- {DB_LIMITATION_NOTE}",
            "- `cached_tokens` is LLM/provider prompt-cache usage from "
            "`request.tokens.cached`. It is **not** an application-level "
            "cache hit (bus schedule cache, auth cache, etc.). Those hits "
            "are not exposed on the metrics record.",
            "- Planner structured conditions are not serialized onto "
            "`request.tasks`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _cell(value: Any) -> str:
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")[:120]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(CSV_COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = dict(row)
            err = out.get("error")
            if err is None:
                out["error"] = ""
            writer.writerow(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark a running UniHelp server via POST /api/ask."
    )
    parser.add_argument("--label", required=True, help="Output stem, e.g. current / baseline / optimized")
    parser.add_argument("--repeats", type=int, default=3, help="Repeats per query (default 3)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--input-price-per-1k", type=float, default=None)
    parser.add_argument("--output-price-per-1k", type=float, default=None)
    parser.add_argument("--cached-price-per-1k", type=float, default=None)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="Per-request HTTP timeout in seconds")
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    if args.repeats < 1:
        raise SystemExit("--repeats must be >= 1")

    queries = load_queries(args.queries)
    pricing_supplied = (
        args.input_price_per_1k is not None or args.output_price_per_1k is not None
    )
    if not pricing_supplied:
        print(
            "WARNING: no --input-price-per-1k / --output-price-per-1k; "
            "estimated_cost is 0.0",
            file=sys.stderr,
        )

    timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S %Z")
    rows: list[dict[str, Any]] = []
    dep_observations: list[dict[str, Any]] = []
    total = len(queries) * args.repeats
    n = 0

    for query in queries:
        for run_index in range(1, args.repeats + 1):
            n += 1
            qid = query["query_id"]
            print(
                f"[{n}/{total}] query_id={qid} run={run_index} "
                f"type={query['query_type']} ...",
                flush=True,
            )
            row, rec, _result = measure_one(
                query,
                run_index,
                args.base_url,
                args.timeout,
                args.input_price_per_1k,
                args.output_price_per_1k,
                args.cached_price_per_1k,
            )
            rows.append(row)
            print(
                f"    status={row['status']} llm_calls={row['llm_calls_total']} "
                f"latency_ms={row['latency_ms']}",
                flush=True,
            )
            if str(qid) in {"10", "11"}:
                dep_observations.append(
                    {
                        "query_id": qid,
                        "run_index": run_index,
                        "query_type": query["query_type"],
                        "status": row.get("status"),
                        "tasks": (rec or {}).get("tasks") if rec else None,
                        "plan": (rec or {}).get("plan") if rec else None,
                    }
                )

    csv_path = HERE / f"{args.label}.csv"
    md_path = HERE / f"{args.label}.md"
    write_csv(csv_path, rows)
    write_report(
        md_path,
        label=args.label,
        base_url=args.base_url,
        repeats=args.repeats,
        timestamp=timestamp,
        queries=queries,
        rows=rows,
        dep_observations=dep_observations,
        pricing_supplied=pricing_supplied,
    )

    ok = successful_rows(rows)
    print(f"Wrote {csv_path} ({len(rows)} rows)")
    print(f"Wrote {md_path}")
    print(f"Successful: {len(ok)} / {len(rows)}")
    print(DB_LIMITATION_NOTE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
