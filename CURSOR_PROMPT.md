# Cursor Prompt — IIT Campus Agent refactor

Paste everything below the line into Cursor (Composer / Agent mode, with the
whole repo in context). It is written to be executed in one pass.

---

You are refactoring an existing Python A2A campus-assistant service (IIT Patna
Organization Management Agent). The repo contains an A2A/Starlette entry point,
a Planner → Executor → specialized-agent pipeline, four domain agents, their
PostgreSQL function layers, and a combined SQL dump.

Apply **all** of the changes below in a single pass. Do not ask me to confirm
between steps. Do not refactor anything not listed here. Preserve existing
behavior, function signatures, return shapes (`{"status": ..., "message": ...}`
dicts), and prompt wording except where a change explicitly requires otherwise.

## Ground rules

- Keep every public function name and return shape stable — other modules and
  the LLM tool schemas depend on them.
- Add a brief comment at each non-obvious fix explaining *why*, so the next
  reader doesn't undo it.
- Do not introduce new frameworks. Use the standard library, `psycopg`/
  `psycopg_pool`, and the existing `openai` client.
- After all edits, every file must pass `python -m compileall .` cleanly.

---

## 1. Fix the critical state-wiping bug in `mess_agent_1.py`

In `MessAgent.chat()`, after the first round of tool calls appends tool results
to `messages`, the code falls through into a **second, near-identical block**
that rebuilds `messages` from scratch as `[system, user]` — discarding the
assistant tool-call message and the tool results just appended. The model never
sees its own tool output, so it re-issues the same tool call. For `modify_menu`
(a write) this risks **applying the same menu edit twice**.

- Delete the entire duplicated tail: the second `system_prompt = f"""..."""`
  assignment, the second `messages = [...]` reassignment, and the nested
  `while True:` loop that follows it.
- The original outer `while True:` loop is already correct on its own — it
  loops back with accumulated `messages` and returns when the model stops
  requesting tools. Leave it as the only loop.
- Also replace that outer `while True:` with a bounded `for _ in range(10):`
  and return a "exceeded its tool-call limit" string after the loop, matching
  `ComplaintAgent`.

## 2. Make the server actually non-blocking (`main.py`)

`OrganizationAgent.execute()` is `async def`, but `authenticate()`,
`planner.create_plan()` and `executor.execute()` are all **synchronous
blocking I/O** (psycopg + the sync OpenAI client), and each request chains
several seconds of them. On the single event-loop thread, one user's request
blocks every other user's request for its full duration — the service is
effectively single-user despite being async.

- Wrap each blocking call in `await asyncio.to_thread(...)`.
- Add a module-level `asyncio.Semaphore(8)` and acquire it around the whole
  request body, so a burst can't spawn unbounded threads or exhaust the DB
  pool. Keep this value ≤ the DB pool max size.
- Wrap the request body in `try/except Exception`, log with `logger.exception`,
  and return a generic error string. Previously any exception (e.g. the
  planner's `json.loads` failing on a non-JSON model reply) escaped and
  produced an opaque framework 500.
- Replace the `print("USER INPUT:", ...)` / `print("CONTEXT METADATA:", ...)`
  calls with `logging`. **Never log `context.metadata`** — it contains the
  caller's `authentication_key`. Log only a length/summary of the user input.
- Construct `Planner()` and `Executor()` **once at module level**, not per
  request. They hold no per-request state (identity is passed per call), and
  `Executor.__init__` builds four sub-agents plus five OpenAI clients — all of
  that was being rebuilt on every request.
- Register a Starlette `on_shutdown` handler that calls `db.close_all_pools()`
  (see step 3) via `asyncio.to_thread`.

## 3. Add a shared connection pool — new file `db.py`

Every function module (`authenticator.py`, `mess_functions_1.py`,
`bus_function.py`, `complaint_functions.py`, `Room_booking_functions.py`)
currently opens a **brand-new connection per query** and closes it. Under
concurrency this means constant connect/auth handshakes and a real risk of
exhausting `max_connections`.

Create `db.py` exposing:

```python
def get_connection(dbname: str): ...
def close_all_pools(): ...
```

Requirements:

- Keep one `psycopg_pool.ConnectionPool` per database name, created lazily and
  guarded by a `threading.Lock` with a double-checked `if dbname not in _pools`
  re-check inside the lock.
- Read `PGHOST`/`PGPORT`/`PGUSER`/`PGPASSWORD` env overrides here, once, so
  every module gets consistent behavior.
- Pool size configurable via `DB_POOL_MIN_SIZE` / `DB_POOL_MAX_SIZE`
  (defaults 1 / 10).
- Return a small `_PooledConnection` proxy whose `.close()` calls
  `pool.putconn()` instead of closing the socket, and which forwards
  everything else via `__getattr__` plus `__enter__`/`__exit__`. **This is what
  lets every existing call site keep its `conn = get_connection()` /
  `conn.close()` shape unchanged** — do not rewrite those call sites.
- `.close()` must be idempotent and must swallow exceptions from `putconn`,
  since callers invoke it from `finally:` blocks.
- If `psycopg_pool` is not importable, fall back to the old per-call
  connection behavior (pg8000 first, then psycopg) so nothing hard-breaks.

Then update all five modules to delegate:

```python
import db
from config import <THEIR_DB_NAME>

def get_connection():
    return db.get_connection(<THEIR_DB_NAME>)
```

Delete their now-dead `os.getenv` blocks and driver-selection `try/except
ImportError` blocks, and remove any imports that become unused.

**Note the pre-existing inconsistency this fixes:** `authenticator.py` and
`Room_booking_functions.py` connected using `config.DB_HOST`/`DB_PORT`
*directly*, ignoring the `PGHOST`/`PGPORT`/`PGDATABASE` env overrides that the
other three modules honored. Under a Docker env override, auth and room booking
would silently point at the wrong host/database while everything else worked.

## 4. Kill the N+1 and add caching

**`mess_functions_1.py` → `get_weekly_menu()`** runs **7 separate queries in a
loop**, one per day. Replace with a single query using
`WHERE LOWER(day) = ANY(%s)` against a list of the 7 lowercased day names, then
build the week from a `{day_lower: row}` dict. Preserve the existing `"—"`
placeholder behavior for missing days and the `status: not_found` check.

**`bus_function.py` → `_all_stops()` and `_legs()`** re-scan the whole table on
every call, and `find_route_by_destination()` / `next_departure()` call them
repeatedly *within a single conversation turn*. Add a module-level TTL cache
(60s) with a `threading.Lock`, a `_topology_cached(key, compute_fn)` helper,
and an `_invalidate_topology_cache()` function. Call the invalidator after
every successful `conn.commit()` in `add_schedule`, `remove_schedule`, and
`change_schedule`.

**`authenticator.py`** is on the critical path of *every* request. Add a TTL
cache (300s for hits, 30s for misses — so a typo'd key doesn't hammer the DB
but a newly-added user still works quickly), a `threading.Lock`, and an
exported `invalidate_auth_cache(key=None)` for when user records change.

## 5. Add the missing indexes — new file `postgres_indexes.sql`

`bus_schedule` (528 rows) has **only a primary key on `id`**, yet every lookup
filters on `bus_name` / `day` / `start_point` / `destination`. The mess tables
are likewise unindexed on `hostel`/`day`.

Create a migration with `CREATE INDEX IF NOT EXISTS` for:

- `bus_schedule (bus_name)`, `(day)`, `(start_point, destination)`, and
  `(LOWER(bus_name))` — the code matches case-insensitively throughout, so the
  functional index is what actually gets used.
- `temporary (LOWER(hostel), LOWER(day))` and the same on `permanent`.

Use `\connect <db>` between sections since these live in different databases.
`rooms` is 7 rows and already keyed on `room_number` — no index needed; say so
in a comment.

## 6. Harden the f-string SQL interpolation

`Room_booking_functions.py` (`book_room`, `cancel_booking`) and
`mess_functions_1.py` (`modify_menu`) build SQL with f-string **column name**
interpolation. These are currently validated against a list first, so they are
not exploitable today — but the pattern is fragile: one future edit that
forgets the check reintroduces SQL injection.

Replace the membership checks with explicit dict allow-lists that map input to
a hardcoded literal column name, and interpolate **the dict's value**, never
the caller's string:

```python
_DAY_COLUMNS = {"day_1": "day_1", "day_2": "day_2", "day_3": "day_3"}
...
if day not in _DAY_COLUMNS:
    return {"status": "error", "message": "Day must be day_1, day_2, or day_3."}
day_column = _DAY_COLUMNS[day]
```

Same shape for `modify_menu`'s meal column (`breakfast`/`lunch`/`snacks`/
`dinner`). Keep the existing error messages byte-identical.

## 7. Fix module-level side effects and the filename mismatch

- **`Room_booking_functions.py` ends with an unguarded test script** that runs
  at *import* time — meaning `import Room_booking_functions` anywhere would
  silently **book and cancel a real room (CLH-101)** against whatever database
  is configured. Wrap the whole block in `if __name__ == "__main__":`.
- `complaint_agent_2_.py` imports `from complaint_functions import ...` but the
  file is named `complaint_functions_2___1_.py`. Rename to
  `complaint_agent.py` and `complaint_functions.py` and fix all imports.

## 8. Build the missing `room_booking_agent.py`

The file exists but is **empty**, so room booking is unreachable. Create a
`RoomBookingAgent` class mirroring `BusAgent`/`ComplaintAgent`:

- `__init__` builds the OpenAI client and a `self.tools` list with schemas for
  `get_room_availability`, `get_room_details`, `book_room`, `cancel_booking`,
  `get_my_bookings`.
- `chat(self, user_input, user_metadata)` with a bounded 10-round tool loop,
  `temperature=0`, per-tool-call `try/except`, and JSON-serialized tool results.
- **Identity:** `book_room`/`cancel_booking` take a `booked_by` string that
  `cancel_booking` later compares to decide booking ownership. The existing
  test code passed the *role* ("student"), which would make every student share
  one identity and let them cancel each other's bookings. Pass
  `user_metadata["roll_number"] or name or role` instead. Do **not** expose
  `booked_by` as an LLM-supplied tool parameter — inject it server-side.

## 9. Wire the two orphaned agents into the pipeline

`ComplaintAgent` and the new `RoomBookingAgent` are fully built but unreachable:
the Planner prompt only knows `mess`/`bus`, and the Executor only has two tools.

**`executor.py`:** import both, instantiate in `__init__`, add `_complaint_tool()`
and `_room_booking_tool()` schemas plus `_call_*` methods, extend the `tools`
list and the dispatch `elif` chain, and update the system prompt to describe
four agents and their routing rules. Replace the unbounded `while True:` with
`for _ in range(10):` + a fallback return.

`ComplaintAgent.chat()` has a different signature — `(user_input, role,
user_identifier)` — so adapt in `_call_complaint_agent`.

**Flag this in a comment (do not try to fix it):** `campus_agent.users` (what
`authenticate()` reads) has no `email` column — only `authentication_key`,
`role`, `names`, `roll_number` — while the *separate* `complaints.users` table
does. `complaint_functions._resolve_user` looks staff up **strictly by email**.
So staff-only complaint actions (`verify_complaint`, `assign_complaint`) will
return "not found" rather than running. That's a safe failure, not a security
hole, but it means those actions don't work until the two user tables are
reconciled. Student and read-only actions use `roll_number` and work fine.

**`planner.py`:** add `complaint` and `room_booking` to the supported agents,
their responsibilities, and a disambiguation section ("seeing the menu" = mess
vs "complaining about food" = complaint with category mess; bus timings = bus
vs a bus that never arrived = complaint with category transport).

## 10. Token optimization in `planner.py`

- The prompt carries ~10 worked examples, most teaching the same rule, and all
  are resent on every request. Trim to one example per agent plus one
  multi-task example.
- Move the prompt to a **class-level constant** so the string is identical
  across calls — stable prefixes are what let the gateway (and most inference
  servers) reuse a cached prefix instead of reprocessing it.
- Add a keyword **fast path**: if the request unambiguously matches exactly one
  agent's keywords, return the plan directly and **skip the planner LLM call
  entirely**, removing a full round-trip from the critical path. If zero or
  more than one domain matches, fall through to the LLM. Only shortcut
  unambiguous cases.
- Replace the bare `json.loads(content)` with a defensive `_parse_plan` that
  strips ``` fences, falls back to extracting the outermost `{...}` via regex,
  and returns the `unsupported` plan shape rather than raising.
- Pass `response_format={"type": "json_object"}` inside a `try/except` that
  retries without it, since the custom gateway may not support the parameter.

## 11. Small correctness fixes in `Bus_agent.py`

- `chat()` calls the model **without `temperature=0`** — the only agent that
  does, making its tool selection nondeterministic. Add it.
- Replace the unbounded `while True:` with `for _ in range(10):` + fallback
  return.
- Wrap `call_tool(tool_name, **arguments)` in `try/except Exception` — it
  dispatches on a *model-supplied* name with *model-supplied* kwargs, so a bad
  name or unexpected kwarg raises `TypeError` straight out of `chat()` and
  crashes the request. Feed the error back as a tool result instead.
- `json.dumps` non-string tool results before appending (currently assumes
  `call_tool` always returns a string).
- Replace `print("Bus LLM:", ...)` with `logger.debug`.
- Change `role = user_metadata["role"]` to
  `str(user_metadata.get("role", "")).lower().strip()` — a `KeyError` here
  would crash the request, and the write-authorization check downstream
  lowercases anyway.
- Keep `arguments["user"] = role` as an **overwrite, not a merge** — the model
  must never get to pick the role it writes as. Add a comment saying so.

## 12. `requirements.txt`

Create it with `openai`, `starlette`, `uvicorn`, `python-dotenv`, `a2a`, and
`psycopg[binary,pool]>=3.1.0`. Note in a comment that `psycopg_pool` is what
enables pooling and that without it `db.py` silently falls back to per-call
connections. Keep `pg8000` as an optional fallback, but note that
`bus_function._fetch()` uses psycopg's `dict_row` row factory which pg8000 does
**not** support — so the fallback is partial and standardizing on psycopg is
recommended.

---

## Verification

After the edits, confirm:

1. `python -m compileall .` passes.
2. `grep -rn "while True" *.py` returns nothing in the agent tool loops.
3. `grep -rn "psycopg.connect\|pg8000.connect" *.py` appears only in `db.py`.
4. No `print(` remains in `main.py` or `Bus_agent.py`.
5. `Room_booking_functions.py`'s test block sits under `if __name__ ==
   "__main__":`.
6. `mess_agent_1.py` contains the mess system prompt exactly **once**.
7. `importing Room_booking_functions` performs no database writes.

Then give me a short summary of what changed per file, and call out anything
you found that these instructions didn't cover.
