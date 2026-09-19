# UniHelp — an agent-first campus operations layer

UniHelp is an A2A (Agent-to-Agent) JSON-RPC service that sits in front of a
university's everyday services — mess, bus, room booking, attendance,
notices, complaints, class timetable — and gives every caller (a student's
chat client, a script, another agent) **one** natural-language interface
that plans a request, authenticates and authorizes it, and dispatches it to
the right service.

**Live demo:** https://unihelp-coral.vercel.app

It started as a single-campus (IIT Patna) prototype. It is now a
**multi-campus, config-driven platform**: a second campus (IIT Mandi) runs
on the same codebase from its own YAML profile, provisioned by an
admin chatting with a setup agent — no code changes, no fork.

## Why this is more than a chatbot wrapper

- **Deterministic first, LLM only when needed.** Common queries (today's
  menu, a bus schedule, "what's my timetable today") resolve through
  regex-based fast paths against the active campus's catalog — **0 LLM
  calls**. Ambiguous or compound requests still go through the LLM
  planner. Multi-task requests dispatch to their agents and make **one**
  synthesis call, not one call per step.
- **Conditional, chained task plans.** "If my attendance in CS101 is below
  75%, show me how to file a complaint" is a real dependency graph, not a
  single flat task list — thresholds, ordering, and if/else branches are
  evaluated once and reused, not re-asked of the model per branch.
- **Multi-campus from one codebase.** Every hostel, room, bus route, meal
  name, and complaint category lives in an org profile
  (`orgs/iit_patna.yaml`, `orgs/iit_mandi.yaml`), not in application code.
  Adding a campus is a new YAML file and a seed of people/catalog data, not
  a fork — see [`NEW_CAMPUS_SETUP.md`](NEW_CAMPUS_SETUP.md).
- **An admin can onboard a campus by chatting**, not editing YAML by hand.
  `setup_agent.py` exposes tools that patch the org profile, import a
  people roster, and register brand-new services on the fly — see below.
- **Auth and role checks are enforced at the service layer**, independent
  of what the model decides to do. A denied step in a multi-step request
  still returns the steps that succeeded, transparently.
- **It's benchmarked, not just believed to be fast.** See
  [Results](#results) — real numbers from a fixed 18-query regression
  suite, run before and after each optimization pass.

## Architecture

```
Caller (A2A / GUI / CLI)
        |
        v
main.py — Starlette app, port 8002 (or Vercel, see api/index.py)
        |
   authenticate()            canonical_people.py — one identity table,
        |                    not one per domain database
        v
   org_profile.py            active campus: catalog, enabled agents,
        |                    roles, timezone   (orgs/*.yaml)
        v
     Planner  ── fast-path keyword/if-then split, 0 LLM calls when possible
        |     └─ falls back to an LLM call for ambiguous/compound requests
        v
    task_conditions.py — evaluates thresholds / ordering / if-else gates
        |                once per unique condition, chains multi-step plans
        v
     Executor — dict dispatch via agent_registry.py, no LLM call to route
        |
        +---------+--------+-----------+--------------+------------+--------+-----------+------------------+
        | mess    | bus    | complaint | room_booking | attendance | notice | timetable | custom features  |
        v         v        v           v              v            v        v           v
   fast_parse.py tries a regex match against the active org's catalog first;
   on a miss, the domain agent's own LLM + tools take over.
```

`custom_feature_agent.py` is a generic agent driven by a JSON field spec —
when an admin defines a new service (library, lost-and-found, …) through
the setup agent, it becomes a real, planner-routable agent without a new
Python file.

## Results

Benchmarked on a fixed 18-query, 3-repeat regression suite
(`benchmarks/`) — single-task, independent and dependent multi-task,
ambiguous, and edge-case requests — comparing the pre-optimization commit
against the current code:

| Metric | Before | After | Change |
| --- | ---: | ---: | ---: |
| Mean LLM calls / request | 1.48 | 0.96 | **−35%** |
| Mean tokens / request | 3,832 | 1,547 | **−60%** |
| Mean latency | 27.4 s | 5.6 s | **−80%** |
| P95 latency | 125.9 s | 25.3 s | **−80%** |
| Multi-independent latency (mean) | 112.9 s | 3.2 s | **−97%** |

The full breakdown, including per-query-type numbers and what each
optimization pass actually changed, is in
[`benchmarks/comparison_fixed.md`](benchmarks/comparison_fixed.md) and
[`benchmarks/README.md`](benchmarks/README.md). Re-run it yourself:

```bash
python benchmarks/run_benchmark.py --label mine --repeats 3
python benchmarks/compare.py benchmarks/current.csv benchmarks/mine.csv -o benchmarks/comparison_mine.md
```

## Multi-campus and self-service onboarding

One running process serves one campus, selected by `ORG_PROFILE_PATH`
(default `orgs/iit_patna.yaml`). Everything campus-specific — hostel names
and aliases, bookable rooms, bus routes, meal names, complaint categories,
which of the seven agents are even enabled, the student-ID regex — lives in
that YAML, validated at startup by `org_profile.py`.

An authenticated **admin** can extend or reconfigure the active campus by
talking to `setup_agent.py` in plain language: it can patch the org
profile, import a people roster from CSV, and — through
`custom_features.py` — define an entirely new JSON-backed service (a field
schema plus rows in Postgres, never model-generated SQL) that
`agent_registry.py` picks up as a normal, planner-routable agent after a
reload. Step-by-step walkthrough, including the exact admin chat prompts
used to provision IIT Mandi: [`NEW_CAMPUS_SETUP.md`](NEW_CAMPUS_SETUP.md).

## Requirements

| Tool | Version | Notes |
| --- | --- | --- |
| Python | 3.12 (3.11+ should work) | Project venv was built with 3.12 |
| PostgreSQL | 14+ | Needs `createdb` / `psql`. `btree_gist` and `pgcrypto` extensions are used |
| pip | bundled with Python | |
| An OpenRouter API key | — | Default is `https://openrouter.ai/api/v1` |

Optional: `curl` to smoke-test the server.

On macOS with Homebrew:

```bash
brew install python@3.12 postgresql@16
brew services start postgresql@16
```

On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip postgresql postgresql-contrib
sudo systemctl start postgresql
```

Confirm Postgres is reachable:

```bash
psql -U postgres -c 'SELECT version();'
```

If that fails, your cluster may use a different user, socket, or port. Note the host, port, user, and password — you will put them in `.env`.

## 1. Get the code

```bash
git clone https://github.com/couder-04/UNIHELP.git
cd UNIHELP
```

## 2. Python environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`psycopg[binary,pool]` is the supported Postgres driver. `pg8000` is only a fallback and does not work for every query (bus lookups use psycopg's `dict_row`).

## 3. Environment file

```bash
cp .env.example .env
```

Edit `.env`. At minimum set:

```dotenv
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=your_postgres_password_here

AUTH_DB_NAME=campus_agent
MESS_DB_NAME=mess_menu
ROOM_DB_NAME=room_booking
BUS_DB_NAME=bus_schedule
COMPLAINTS_DB_NAME=complaints
ATTENDANCE_DB_NAME=organization_agent
NOTICE_DB_NAME=notice_board
TIMETABLE_DB_NAME=timetable

LLM_API_KEY=your_llm_api_key_here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=deepseek/deepseek-v4-flash-0731
LLM_FAST_MODEL=qwen/qwen3.8-27b

ORG_PROFILE_PATH=orgs/iit_patna.yaml
```

Notes:

- `.env.example` uses port `5434`. Homebrew and most Linux installs use `5432`. Set `PGPORT` to whatever `psql` actually uses (`SHOW port;` inside `psql`).
- Never commit `.env`. It is gitignored.
- Default LLM is OpenRouter. Set `LLM_BASE_URL`, `LLM_MODEL`, `LLM_FAST_MODEL`, and `LLM_API_KEY`. `LLM_FAST_MODEL` is used for classification/dispatch-style calls (planner, multi-task synthesis); domain agents' natural-language replies use `LLM_MODEL`.
- `ORG_PROFILE_PATH` picks the active campus. Omit it to run IIT Patna; point it at `orgs/iit_mandi.yaml` (after seeding Mandi's databases, see `NEW_CAMPUS_SETUP.md`) to run that campus instead.
- Optional pool tuning: `DB_POOL_MIN_SIZE` (default `1`) and `DB_POOL_MAX_SIZE` (default `10`). Keep the pool max ≥ 8, the server's concurrent-request cap.

## 4. Load the full databases

The complete dump is in `database/` (schema + live rows for all eight databases). Names must match the `*_DB_NAME` values above.

```bash
export PGHOST=localhost PGPORT=5432 PGUSER=postgres
export PGPASSWORD='your_postgres_password_here'

psql -d postgres -v ON_ERROR_STOP=1 -f database/unihelp_full.sql
```

Or:

```bash
PGUSER=postgres PGPASSWORD='your_postgres_password_here' database/restore.sh
```

`database/unihelp_full.sql` creates the eight databases if needed, then restores every table, including ~81k attendance rows, enrollments, complaints, and the full timetable roster. Re-running it **replaces** existing tables in those databases. Run it with `psql` (not another client).

Per-database files are also in `database/` (`campus_agent.sql`, `mess_menu.sql`, …). `database/timetable_users.csv` is the student roster; it is already baked into the timetable dump.

Seed-only alternative (much smaller, demo keys only): `psql -d postgres -f unihelp_databases.sql` then `\copy` from `timetable_users.csv`.

### Demo login keys

These keys are in `database/unihelp_full.sql` (campus_agent / complaints / organization_agent):

| Key | Role | Name | `roll_number` |
| --- | --- | --- | --- |
| `student-demo` | student | Aarav Sharma | `2501CS09` |
| `faculty-demo` | faculty | Priya Patel | `PF001` |
| `admin-demo` | admin | Rohan Verma | `AD001` |

Additional seeded people use the same convention: students keep IIT-style rolls (`2501CS90`, …), faculty are `PF001`–`PF016`, and admins are `AD001`–`AD002`.

Replace them before any shared or production use.

Identity now resolves through one canonical table (`canonical_people.py`) rather than a separate row per domain database — see `INSERT` examples in the previous README revision's history if you're adding a person by hand to a legacy table; the current path is `import_people` via the setup agent (CSV in, validated against the active org's student-ID regex).

## 5. Run the server

```bash
source .venv/bin/activate
python main.py
```

You should see uvicorn bind to `127.0.0.1:8002`. Leave this terminal open.

Sanity checks in another terminal:

```bash
# Agent card
curl -s http://127.0.0.1:8002/.well-known/agent-card.json | head

# Authenticated request (student)
curl -s http://127.0.0.1:8002/a2a \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "SendMessage",
    "params": {
      "message": {
        "role": "ROLE_USER",
        "messageId": "msg-1",
        "parts": [
          { "text": "What is today'\''s dinner at Kalam hostel?" }
        ]
      },
      "metadata": {
        "authentication_key": "student-demo"
      }
    }
  }'
```

A missing or unknown key returns `ERROR: KEY NOT FOUND`.

More example prompts (same envelope, change `parts[0].text` and the key):

- Student: `Show me the Bus 02 schedule`
- Student: `What is my attendance percentage in CS101?`
- Student: `Show me the current notices`
- Student: `What is my class timetable today?`
- Student: `Book SAC Hall on 2030-02-10 from 10 to 11 for a club meeting`
- Student: `What's my attendance in CS101, and if it's below 75%, how do I file a complaint about it?` (chained/conditional plan)
- Faculty: `Publish a notice that CS101 lab is cancelled tomorrow`
- Admin: `The water cooler on my floor is broken` (files a hostel complaint)
- Admin (setup agent, separate endpoint): `Add a new campus called IIT Mandi with hostels Chandra and Suvalsar` — see `NEW_CAMPUS_SETUP.md`

There's also a browser GUI at `/connect`, `/ask`, `/activity`, `/commands`, and `/users` (see `gui/`), served both locally and on the Vercel deployment.

## 6. Run the timetable agent (CLI)

Uses `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` from the project `.env`, and the `timetable` database (`TIMETABLE_DB_NAME`).

Caller metadata is the same dict `main.py` passes to every specialized agent:

```python
{
    "role": "student",          # or faculty / admin
    "name": "Abhirup Dhara",
    "roll_number": "2501CS36",  # campus_agent.users.roll_number
    "Time and Date": "Tuesday, 2026-09-15 21:12:00 IST",
}
```

`TimetableAgent.chat(user_input, user_metadata)` takes that object. `roll_num` is still accepted as an alias for `roll_number`. If `Time and Date` is missing, it is filled in IST (`%A, %Y-%m-%d %H:%M:%S IST`).

```bash
source .venv/bin/activate

# 2nd-year CSE student from timetable_users.csv
python timetable_agent.py "What is my class schedule this week?" \
  --name "Abhirup Dhara" --roll-num 2501CS36 --role student

# 1st-year student (group-filtered core slots)
python timetable_agent.py "What do I have on Wednesday?" \
  --name "Mahak Shakya" --roll-num 2603PH03 --role student

# Faculty (seeded by unihelp_databases.sql)
python timetable_agent.py "Show my teaching schedule." \
  --name "Harsh Vardhan" --roll-num PF007 --role faculty

# Admin
python timetable_agent.py "List the rooms used for classes." \
  --name "Rohan Verma" --roll-num AD001 --role admin
```

Students get read tools only (`get_schedule`, `get_day`, `list_subjects`, …). Faculty and admin can also `add_slot` / `update_slot` / `delete_slot`. Roll numbers are forced from `--roll-num`; a student cannot fetch someone else's schedule.

Helpers without the LLM:

```bash
python -c "import timetable_functions as T; print(T.list_subjects())"
```

## 7. Tests

```bash
source .venv/bin/activate

python -m pytest tests/attendance -q   # live organization_agent DB; inserts/deletes HXTEST-prefixed rows
python -m pytest tests/executor -q     # dict dispatch, single/multi-task, condition gating — no live DB
python -m pytest tests/fast_parse -q   # catalog-driven regex parsers, incl. a non-Patna fake org profile
python -m pytest tests/planner -q      # fast-path splitter, if/then/else, LLM-planner fallback shape
python -m pytest tests/cache -q        # TTL cache + write-path invalidation
python -m pytest tests/setup -q        # setup agent tools: org profile patching, people import, custom features
python -m pytest tests/latency -q      # mocked latency-accounting sanity checks
python -m pytest tests/live -q         # opt-in live-server smoke test, gated behind UNIHELP_LIVE=1
```

Syntax check without hitting the network:

```bash
python -m compileall -q .
```

## Architecture map

| Path | Role |
| --- | --- |
| `main.py` | A2A Starlette app, auth, planner/executor, port 8002 (also the Vercel entrypoint via `api/index.py`) |
| `org_profile.py` + `orgs/*.yaml` | Active campus: catalog, enabled agents, roles, timezone, student-ID pattern |
| `agent_registry.py` | One `AgentSpec` per domain (+ custom features) — planner/executor/agent-card all read from here |
| `authenticator.py` + `canonical_people.py` | Resolves `authentication_key` against one identity table, not one per domain DB |
| `planner.py` | Fast-path keyword/if-then/else split (0 LLM calls) with an LLM fallback for ambiguous or compound requests |
| `task_conditions.py` | Evaluates threshold / ordering / if-else gates once per condition; chains dependent multi-step plans |
| `executor.py` | Dict dispatch to the right domain agent(s); one synthesis call only when 2+ tasks actually ran |
| `fast_parse.py` | Catalog-driven regex fast paths for mess/bus/timetable/notice reads |
| `ttl_cache.py` | Shared TTL cache used by the read-heavy domain functions, invalidated on the matching write |
| `llm.py` | Shared OpenAI-compatible client, prompt caching, model tiering (`LLM_MODEL` / `LLM_FAST_MODEL`) |
| `config.py` / `db.py` | Env loading and Postgres connection pools |
| `mess_agent_1.py` + `mess_functions_1.py` | Mess menus |
| `Bus_agent.py` + `bus_function.py` | Bus timetable |
| `complaint_agent.py` + `complaint_functions.py` | Complaints |
| `room_booking_agent.py` + `room_functions.py` | SAC / Guest House / CLH / Auditorium |
| `attendance_agent.py` + `attendance_functions.py` | Attendance |
| `Notice_agent.py` + `notice_functions.py` | Notice board |
| `timetable_agent.py` + `timetable_functions.py` | Class timetable |
| `setup_agent.py` + `setup_functions.py` | Admin-only: patch the org profile, import people, register/disable custom features |
| `custom_feature_agent.py` + `custom_features.py` | Generic agent for an admin-defined, JSON-backed service — never executes model-supplied SQL |
| `benchmarks/` | Fixed-query regression suite + before/after comparison tooling |
| `gui/` | Browser UI (`/connect`, `/ask`, `/activity`, `/commands`, `/users`) |
| `tests/` | `attendance`, `executor`, `fast_parse`, `planner`, `cache`, `setup`, `latency`, `live` |

SQL dumps:

| File | Database |
| --- | --- |
| `database/unihelp_full.sql` | **full** dump of all eight UniHelp databases (schema + live data) |
| `database/*.sql` | per-database dumps |
| `database/timetable_users.csv` | student roster (already included in the timetable dump) |
| `unihelp_databases.sql` | seed-only combined dump |

## Common failures

| Symptom | Likely cause |
| --- | --- |
| `connection refused` on port 5432/5434 | Postgres not running, or `PGPORT` does not match the cluster |
| `password authentication failed` | `PGUSER` / `PGPASSWORD` in `.env` |
| `database "…" does not exist` | `createdb` step skipped or name mismatch with `*_DB_NAME` |
| `ERROR: KEY NOT FOUND` | Wrong `authentication_key`, or `database/unihelp_full.sql` not loaded |
| LLM errors / empty plans | Missing `LLM_API_KEY`, or `LLM_BASE_URL` / `LLM_MODEL` wrong |
| Bus queries crash under `pg8000` | Install `psycopg[binary,pool]` as in `requirements.txt` |
| Attendance tests fail | `organization_agent` not restored, or `.env` points at a different cluster |
| Timetable agent: no API key / empty plans | `LLM_API_KEY` missing from the project `.env` |
| Timetable: `database "timetable" does not exist` | `createdb timetable` or `TIMETABLE_DB_NAME` mismatch |
| Timetable: empty student schedules | `database/unihelp_full.sql` not restored |
| `role "postgres" does not exist` | Homebrew Postgres uses your macOS username. Set `PGUSER` to that name (and often no password) |
| Server starts but every request 404s on a campus noun | `ORG_PROFILE_PATH` points at a profile whose catalog doesn't include that noun — check `orgs/<campus>.yaml` |
| A new custom feature doesn't show up in the planner | Setup agent registers it, but the running process needs `reload_campus` (or a restart) to pick it up |

## Security

- Treat every `authentication_key` as a password.
- Do not put keys in chat text, logs, or git.
- Bind is localhost-only (`127.0.0.1`) unless deployed behind Vercel's own routing. Do not expose port 8002 directly to the internet without auth in front of it.
- `setup_agent.py` is admin-only and never accepts or executes model-supplied SQL — custom features are stored as JSONB rows with a validated field schema, not arbitrary queries.
- `canonical_people.py` is the single source of truth for identity; domain agents receive `role`/`name`/`roll_number` from the executor, never from parsing the user's own message text.