# UniHelp benchmark harness

Measurement-only HTTP client for a **running** UniHelp server. It does not
start the app, does not import planner/executor/agents, and does not change
production behavior.

## Prerequisites

1. The server must already be running:

   ```bash
   python main.py
   ```

   Default bind is `http://127.0.0.1:8002`.

2. This harness talks to **`POST /api/ask`** only:

   ```json
   {"message": "<user_input>", "authentication_key": "<key>"}
   ```

3. This is **not** an in-process benchmark. If nothing is listening on the
   base URL, rows are recorded as `status=request_failed` and the rest of
   the run continues.

## Files

| Path | Role |
| --- | --- |
| `queries.csv` | Fixed 18-query set. Do not regenerate or shuffle between runs. |
| `run_benchmark.py` | Drives `/api/ask`, writes `{label}.csv` and `{label}.md`. |
| `compare.py` | Side-by-side before/after report with `% change`. |

## Run a labeled measurement

```bash
python benchmarks/run_benchmark.py --label current --repeats 3
```

Later, against the same query file:

```bash
python benchmarks/run_benchmark.py --label baseline --repeats 3
python benchmarks/run_benchmark.py --label optimized --repeats 3
```

Optional flags:

- `--base-url` (default `http://127.0.0.1:8002`)
- `--timeout` (default 180 seconds per request)
- `--input-price-per-1k X`
- `--output-price-per-1k Y`
- `--cached-price-per-1k Z`

If no pricing flags are passed, `estimated_cost` is `0.0` and the script
prints a warning. It does not invent a price.

A typical run is `18 queries × 3 repeats = 54` CSV rows. Fewer rows appear
only when the process itself is interrupted; HTTP-level failures still
write a row (`status=request_failed`).

## Compare two runs

```bash
python benchmarks/compare.py \
    benchmarks/baseline.csv \
    benchmarks/optimized.csv \
    -o benchmarks/comparison.md
```

`% change` is `(before - after) / before * 100`. The report does not label
a change as an improvement. If a `query_id` exists in only one CSV, compare
warns, lists the unmatched IDs, excludes those rows from paired tables, and
still prints each file's own aggregate.

## Known limitations

1. The server must already be running with `python main.py`.
2. The benchmark communicates through `/api/ask`.
3. This is not an in-process benchmark.
4. `db_calls` / `db_latency_ms` count `db.get_connection()` checkout-to-close
   time, not per-statement SQL. That includes Python work while the
   connection is held.
5. `approx_non_llm_latency_ms` still combines DB time with Python/tool
   overhead; use `db_latency_ms` for the connection-held slice.
6. Application cache events are on `request.cache_events` /
   `tasks[].cache_hit` / `tasks[].cache_source`. `cached_tokens` remains
   LLM/provider prompt caching and must not be read as an app cache hit.
7. Planner `plan` is now attached to the metrics record. `request.tasks`
   also carries additive `task_id`, `agent`, `condition`, `depends_on`,
   `condition_type`, and `skipped` when the Executor recorded them.
8. `fast_path` / `synthesis_llm_used` are still not named metrics fields.
   Zero `llm_calls` is reported as observed, without naming the mechanism.

