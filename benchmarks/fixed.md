# UniHelp benchmark — `fixed`

- Benchmark timestamp: 2026-09-18 20:13:39 IST
- Base URL: `http://127.0.0.1:8002`
- Repeat count: 3
- Total requests: 54
- Successful requests (`status == ok`): 54
- Failed requests (`status != ok`): 0
- Pricing supplied: no (estimated_cost is 0.0)

## Headline metrics

Across successful requests:

| Metric | Mean |
| --- | ---: |
| LLM calls/request | 0.96 |
| Executor LLM calls/request | 0.17 |
| Total tokens/request | 1546.5 |
| Mean latency (ms) | 5550.9 |
| P50 latency (ms) | 2870.8 |
| P95 latency (ms) | 25319.5 |
| Estimated cost/request | 0.000000 |

## Query-type breakdown

Same headline metrics grouped by `query_type`. Rows whose type starts with `edge_` are grouped as `edge_*`.

| query_type | n_ok | LLM calls | Executor calls | Tokens | Mean latency (ms) | P50 (ms) | P95 (ms) | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| single | 18 | 0.00 | 0.00 | 0.0 | 4.8 | 0.2 | 26.2 | 0.000000 |
| multi_independent | 9 | 1.00 | 1.00 | 552.6 | 3246.9 | 3201.6 | 4220.9 | 0.000000 |
| multi_dependent | 6 | 1.00 | 0.00 | 2126.5 | 3886.4 | 3630.6 | 5056.8 | 0.000000 |
| ambiguous | 9 | 2.67 | 0.00 | 4224.0 | 20455.3 | 10832.3 | 51263.2 | 0.000000 |
| edge_* | 12 | 1.08 | 0.00 | 2313.8 | 5251.9 | 3474.8 | 13987.7 | 0.000000 |

## Per-feature LLM calls

Averaged per successful request. Counts come from `request.llm_calls[].feature` only — not from task count or latency.

| Feature | Avg calls/request |
| --- | ---: |
| Planner | 0.11 |
| Executor | 0.17 |
| Mess | 0.06 |
| Bus | 0.07 |
| Complaint | 0.28 |
| Room Booking | 0.11 |
| Attendance | 0.00 |
| Notice | 0.17 |
| Timetable | 0.00 |

## Fast-path observations

`fast_path`, `planner_llm_used`, `executor_llm_used`, and `synthesis_llm_used` are **not** named fields on the `/api/ask` metrics record. The values below are taken only from `request.llm_calls` feature counts (or listed as not exposed).

- `planner_llm_used`: true when `planner_calls > 0` on that row.
- `executor_llm_used`: true when `executor_calls > 0` on that row.
- `synthesis_llm_used`: **not exposed**. Metrics do not distinguish an Executor synthesis completion from any other Executor LLM call.
- `fast_path`: **not exposed**. A row with `llm_calls_total == 0` completed with no LLM round; the record does not name the mechanism (parser, keyword planner, single-task dispatch, unsupported short-circuit, etc.).

Queries with **zero LLM calls** (successful rows only):

| query_id | query | run_index | latency_ms | planner_llm_used | executor_llm_used |
| --- | --- | ---: | ---: | --- | --- |
| 1 | What's today's breakfast at Kalam hostel? | 1 | 24.7 | no | no |
| 1 | What's today's breakfast at Kalam hostel? | 2 | 0.2 | no | no |
| 1 | What's today's breakfast at Kalam hostel? | 3 | 0.2 | no | no |
| 2 | What's today's lunch at Kalam hostel? | 1 | 0.2 | no | no |
| 2 | What's today's lunch at Kalam hostel? | 2 | 0.2 | no | no |
| 2 | What's today's lunch at Kalam hostel? | 3 | 0.1 | no | no |
| 3 | What's today's dinner at Kalam hostel? | 1 | 0.2 | no | no |
| 3 | What's today's dinner at Kalam hostel? | 2 | 0.2 | no | no |
| 3 | What's today's dinner at Kalam hostel? | 3 | 0.1 | no | no |
| 4 | What is the bus schedule for Bus 02? | 1 | 23.3 | no | no |
| 4 | What is the bus schedule for Bus 02? | 2 | 0.3 | no | no |
| 4 | What is the bus schedule for Bus 02? | 3 | 0.2 | no | no |
| 5 | Show today's notices. | 1 | 0.1 | no | no |
| 5 | Show today's notices. | 2 | 0.1 | no | no |
| 5 | Show today's notices. | 3 | 0.1 | no | no |
| 6 | What's my timetable today? | 1 | 34.9 | no | no |
| 6 | What's my timetable today? | 2 | 0.3 | no | no |
| 6 | What's my timetable today? | 3 | 0.2 | no | no |

## Dependency verification

Queries 10 and 11 are labeled `multi_dependent`. Planner `condition` / `depends_on` / task `id` / per-task `request` are **not** fields on `request.tasks` as returned by `/api/ask`. `metrics.task_timer` records only `{feature, latency_ms}`.

The tables below dump the actual `request.tasks` payload. Missing `condition` is reported as not present — it is **not** inferred from the user phrasing or from which features ran.

### Query 10 — run 1

- status: `ok`
- query_type: `multi_dependent`
- planner `plan`:

```json
{
  "tasks": [
    {
      "id": "t1",
      "agent": "room_booking",
      "request": "What time does my last class end today, and is SAC Hall free right after for a club meeting?",
      "condition": null
    }
  ]
}
```


| task index | feature | latency_ms | task IDs | agent | request | condition | depends_on | condition type |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| 0 | planner | 0.1 | not present | planner | not present | not present | not present | not present |
| 1 | room_booking | 3329.5 | t1 | room_booking | not present | null | null | not present |

**condition is not present (or null) on every task.** This query did not expose dependency handling through `request.tasks`. Do not treat the `multi_dependent` label as confirmed by this run.

### Query 10 — run 2

- status: `ok`
- query_type: `multi_dependent`
- planner `plan`:

```json
{
  "tasks": [
    {
      "id": "t1",
      "agent": "room_booking",
      "request": "What time does my last class end today, and is SAC Hall free right after for a club meeting?",
      "condition": null
    }
  ]
}
```


| task index | feature | latency_ms | task IDs | agent | request | condition | depends_on | condition type |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| 0 | planner | 0.0 | not present | planner | not present | not present | not present | not present |
| 1 | room_booking | 3165.1 | t1 | room_booking | not present | null | null | not present |

**condition is not present (or null) on every task.** This query did not expose dependency handling through `request.tasks`. Do not treat the `multi_dependent` label as confirmed by this run.

### Query 10 — run 3

- status: `ok`
- query_type: `multi_dependent`
- planner `plan`:

```json
{
  "tasks": [
    {
      "id": "t1",
      "agent": "room_booking",
      "request": "What time does my last class end today, and is SAC Hall free right after for a club meeting?",
      "condition": null
    }
  ]
}
```


| task index | feature | latency_ms | task IDs | agent | request | condition | depends_on | condition type |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| 0 | planner | 0.1 | not present | planner | not present | not present | not present | not present |
| 1 | room_booking | 5082.9 | t1 | room_booking | not present | null | null | not present |

**condition is not present (or null) on every task.** This query did not expose dependency handling through `request.tasks`. Do not treat the `multi_dependent` label as confirmed by this run.

### Query 11 — run 1

- status: `ok`
- query_type: `multi_dependent`
- planner `plan`:

```json
{
  "tasks": [
    {
      "id": "t1",
      "agent": "complaint",
      "request": "it's below 75%, how do I file a complaint about it?",
      "condition": null
    },
    {
      "id": "t2",
      "agent": "attendance",
      "request": "What's my attendance percentage in CS101, and",
      "condition": {
        "depends_on": "t1",
        "type": "threshold",
        "field": "value",
        "op": "<",
        "value": 75.0
      }
    }
  ]
}
```


| task index | feature | latency_ms | task IDs | agent | request | condition | depends_on | condition type |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| 0 | planner | 0.1 | not present | planner | not present | not present | not present | not present |
| 1 | complaint | 2830.3 | t1 | complaint | not present | null | null | not present |
| 2 | attendance | 0.0 | t2 | attendance | not present | {"depends_on": "t1", "type": "threshold", "field": "value", "op": "<", "value": 75.0} | "t1" | threshold |

### Query 11 — run 2

- status: `ok`
- query_type: `multi_dependent`
- planner `plan`:

```json
{
  "tasks": [
    {
      "id": "t1",
      "agent": "complaint",
      "request": "it's below 75%, how do I file a complaint about it?",
      "condition": null
    },
    {
      "id": "t2",
      "agent": "attendance",
      "request": "What's my attendance percentage in CS101, and",
      "condition": {
        "depends_on": "t1",
        "type": "threshold",
        "field": "value",
        "op": "<",
        "value": 75.0
      }
    }
  ]
}
```


| task index | feature | latency_ms | task IDs | agent | request | condition | depends_on | condition type |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| 0 | planner | 0.2 | not present | planner | not present | not present | not present | not present |
| 1 | complaint | 3931.1 | t1 | complaint | not present | null | null | not present |
| 2 | attendance | 0.0 | t2 | attendance | not present | {"depends_on": "t1", "type": "threshold", "field": "value", "op": "<", "value": 75.0} | "t1" | threshold |

### Query 11 — run 3

- status: `ok`
- query_type: `multi_dependent`
- planner `plan`:

```json
{
  "tasks": [
    {
      "id": "t1",
      "agent": "complaint",
      "request": "it's below 75%, how do I file a complaint about it?",
      "condition": null
    },
    {
      "id": "t2",
      "agent": "attendance",
      "request": "What's my attendance percentage in CS101, and",
      "condition": {
        "depends_on": "t1",
        "type": "threshold",
        "field": "value",
        "op": "<",
        "value": 75.0
      }
    }
  ]
}
```


| task index | feature | latency_ms | task IDs | agent | request | condition | depends_on | condition type |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| 0 | planner | 0.1 | not present | planner | not present | not present | not present | not present |
| 1 | complaint | 4977.4 | t1 | complaint | not present | null | null | not present |
| 2 | attendance | 0.0 | t2 | attendance | not present | {"depends_on": "t1", "type": "threshold", "field": "value", "op": "<", "value": 75.0} | "t1" | threshold |

## Failures

_No rows with `status != ok`._

## Known limitations

- Note: db_calls/db_latency_ms count get_connection() checkout-to-close time (DB + whatever the caller did while holding the connection), not per-query SQL timing.
- `cached_tokens` is LLM/provider prompt-cache usage from `request.tokens.cached`. It is **not** an application-level cache hit (bus schedule cache, auth cache, etc.). Those hits are not exposed on the metrics record.
- Planner structured conditions are not serialized onto `request.tasks`.
