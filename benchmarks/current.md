# UniHelp benchmark — `current`

- Benchmark timestamp: 2026-09-18 18:46:08 IST
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
| LLM calls/request | 1.48 |
| Executor LLM calls/request | 0.17 |
| Total tokens/request | 3832.3 |
| Mean latency (ms) | 27394.1 |
| P50 latency (ms) | 6145.5 |
| P95 latency (ms) | 125947.4 |
| Estimated cost/request | 0.000000 |

## Query-type breakdown

Same headline metrics grouped by `query_type`. Rows whose type starts with `edge_` are grouped as `edge_*`.

| query_type | n_ok | LLM calls | Executor calls | Tokens | Mean latency (ms) | P50 (ms) | P95 (ms) | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| single | 18 | 0.39 | 0.00 | 407.7 | 2231.9 | 6.0 | 13925.3 | 0.000000 |
| multi_independent | 9 | 2.89 | 1.00 | 11057.6 | 112885.2 | 118320.4 | 137879.3 | 0.000000 |
| multi_dependent | 6 | 1.17 | 0.00 | 2523.8 | 8798.9 | 9593.8 | 12256.4 | 0.000000 |
| ambiguous | 9 | 2.56 | 0.00 | 5829.7 | 29145.5 | 7084.4 | 111241.0 | 0.000000 |
| edge_* | 12 | 1.42 | 0.00 | 2706.4 | 9003.1 | 6083.4 | 21475.7 | 0.000000 |

## Per-feature LLM calls

Averaged per successful request. Counts come from `request.llm_calls[].feature` only — not from task count or latency.

| Feature | Avg calls/request |
| --- | ---: |
| Planner | 0.28 |
| Executor | 0.17 |
| Mess | 0.06 |
| Bus | 0.06 |
| Complaint | 0.30 |
| Room Booking | 0.11 |
| Attendance | 0.00 |
| Notice | 0.52 |
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
| 1 | What's today's breakfast at Kalam hostel? | 1 | 7.6 | no | no |
| 1 | What's today's breakfast at Kalam hostel? | 2 | 4.9 | no | no |
| 1 | What's today's breakfast at Kalam hostel? | 3 | 5.0 | no | no |
| 2 | What's today's lunch at Kalam hostel? | 1 | 2.8 | no | no |
| 2 | What's today's lunch at Kalam hostel? | 2 | 3.2 | no | no |
| 2 | What's today's lunch at Kalam hostel? | 3 | 3.5 | no | no |
| 3 | What's today's dinner at Kalam hostel? | 1 | 3.7 | no | no |
| 3 | What's today's dinner at Kalam hostel? | 2 | 3.2 | no | no |
| 3 | What's today's dinner at Kalam hostel? | 3 | 7.4 | no | no |
| 4 | What is the bus schedule for Bus 02? | 1 | 43.0 | no | no |
| 4 | What is the bus schedule for Bus 02? | 2 | 6.9 | no | no |
| 4 | What is the bus schedule for Bus 02? | 3 | 4.3 | no | no |
| 6 | What's my timetable today? | 1 | 13.9 | no | no |
| 6 | What's my timetable today? | 2 | 7.3 | no | no |
| 6 | What's my timetable today? | 3 | 5.1 | no | no |

## Dependency verification

Queries 10 and 11 are labeled `multi_dependent`. Planner `condition` / `depends_on` / task `id` / per-task `request` are **not** fields on `request.tasks` as returned by `/api/ask`. `metrics.task_timer` records only `{feature, latency_ms}`.

The tables below dump the actual `request.tasks` payload. Missing `condition` is reported as not present — it is **not** inferred from the user phrasing or from which features ran.

### Query 10 — run 1

- status: `ok`
- query_type: `multi_dependent`

| task index | feature | latency_ms | task IDs | agent | request | condition | depends_on | condition type |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| 0 | planner | 0.1 | not present | planner | not present | not present | not present | not present |
| 1 | room_booking | 10692.1 | not present | room_booking | not present | not present | not present | not present |

**condition is not present (or null) on every task.** This query did not expose dependency handling through `request.tasks`. Do not treat the `multi_dependent` label as confirmed by this run.

### Query 10 — run 2

- status: `ok`
- query_type: `multi_dependent`

| task index | feature | latency_ms | task IDs | agent | request | condition | depends_on | condition type |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| 0 | planner | 0.1 | not present | planner | not present | not present | not present | not present |
| 1 | room_booking | 12623.3 | not present | room_booking | not present | not present | not present | not present |

**condition is not present (or null) on every task.** This query did not expose dependency handling through `request.tasks`. Do not treat the `multi_dependent` label as confirmed by this run.

### Query 10 — run 3

- status: `ok`
- query_type: `multi_dependent`

| task index | feature | latency_ms | task IDs | agent | request | condition | depends_on | condition type |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| 0 | planner | 0.1 | not present | planner | not present | not present | not present | not present |
| 1 | room_booking | 8495.0 | not present | room_booking | not present | not present | not present | not present |

**condition is not present (or null) on every task.** This query did not expose dependency handling through `request.tasks`. Do not treat the `multi_dependent` label as confirmed by this run.

### Query 11 — run 1

- status: `ok`
- query_type: `multi_dependent`

| task index | feature | latency_ms | task IDs | agent | request | condition | depends_on | condition type |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| 0 | planner | 0.2 | not present | planner | not present | not present | not present | not present |
| 1 | complaint | 5319.2 | not present | complaint | not present | not present | not present | not present |

**condition is not present (or null) on every task.** This query did not expose dependency handling through `request.tasks`. Do not treat the `multi_dependent` label as confirmed by this run.

### Query 11 — run 2

- status: `ok`
- query_type: `multi_dependent`

| task index | feature | latency_ms | task IDs | agent | request | condition | depends_on | condition type |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| 0 | planner | 0.1 | not present | planner | not present | not present | not present | not present |
| 1 | complaint | 11154.4 | not present | complaint | not present | not present | not present | not present |

**condition is not present (or null) on every task.** This query did not expose dependency handling through `request.tasks`. Do not treat the `multi_dependent` label as confirmed by this run.

### Query 11 — run 3

- status: `ok`
- query_type: `multi_dependent`

| task index | feature | latency_ms | task IDs | agent | request | condition | depends_on | condition type |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| 0 | planner | 0.1 | not present | planner | not present | not present | not present | not present |
| 1 | complaint | 4504.9 | not present | complaint | not present | not present | not present | not present |

**condition is not present (or null) on every task.** This query did not expose dependency handling through `request.tasks`. Do not treat the `multi_dependent` label as confirmed by this run.

## Failures

_No rows with `status != ok`._

## Known limitations

- Note: metrics.py does not expose DB call count or DB-only latency; approx_non_llm_latency_ms is DB time plus Python/tool/application overhead, not a true db_latency_ms.
- `cached_tokens` is LLM/provider prompt-cache usage from `request.tokens.cached`. It is **not** an application-level cache hit (bus schedule cache, auth cache, etc.). Those hits are not exposed on the metrics record.
- Planner structured conditions are not serialized onto `request.tasks`.
