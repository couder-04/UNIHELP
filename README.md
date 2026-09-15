# UniHelp — IIT Patna Organization Management Agent

A local A2A (Agent-to-Agent) JSON-RPC service that authenticates a campus user, plans their request, and routes it to specialized agents for mess, bus, complaints, room booking, attendance, notices, and class timetable.

This README is enough to run the same stack on a clean machine.

## What you get

```
Caller  --SendMessage-->  main.py (Starlette, port 8002)
                              |
                         authenticate()   # campus_agent.users
                              |
                           Planner        # LLM: which agent(s)?
                              |
                           Executor       # LLM: call the right agent tools
                              |
        +---------+--------+--------+------------+-------------+
        | mess    | bus    | complaint | room_booking | attendance | notice | timetable
        v         v        v           v              v            v         v
     mess_menu  bus_schedule  complaints  room_booking  organization_agent  notice_board  timetable
```

The HTTP server listens only on `127.0.0.1:8002`. Each request must include an `authentication_key` in **request metadata**, not in the message text.

## Requirements

| Tool | Version | Notes |
| --- | --- | --- |
| Python | 3.12 (3.11+ should work) | Project venv was built with 3.12 |
| PostgreSQL | 14+ | Needs `createdb` / `psql`. `btree_gist` and `pgcrypto` extensions are used |
| pip | bundled with Python | |
| An OpenAI-compatible LLM key | — | Default gateway is `https://awesome.kado.so/openai/v1` |

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
git clone -b final https://github.com/Goutam-2702/AGENTIC-SYSTEMS-KADO.git unihelp
cd unihelp
```

If you already have the repo, check out the `final` branch:

```bash
git fetch origin
git checkout final
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
LLM_BASE_URL=https://awesome.kado.so/openai/v1
LLM_MODEL=kado
```

Notes:

- `.env.example` uses port `5434`. Homebrew and most Linux installs use `5432`. Set `PGPORT` to whatever `psql` actually uses (`SHOW port;` inside `psql`).
- Never commit `.env`. It is gitignored.
- Any OpenAI-compatible endpoint works: set `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY`.
- Optional pool tuning: `DB_POOL_MIN_SIZE` (default `1`) and `DB_POOL_MAX_SIZE` (default `10`). Keep the pool max ≥ 8, the server's concurrent-request cap.

## 4. Create the eight databases

The app does **not** create databases for you. Names must match the `*_DB_NAME` values above.

```bash
createdb -h localhost -p 5432 -U postgres campus_agent
createdb -h localhost -p 5432 -U postgres mess_menu
createdb -h localhost -p 5432 -U postgres bus_schedule
createdb -h localhost -p 5432 -U postgres room_booking
createdb -h localhost -p 5432 -U postgres complaints
createdb -h localhost -p 5432 -U postgres organization_agent
createdb -h localhost -p 5432 -U postgres notice_board
createdb -h localhost -p 5432 -U postgres timetable
```

If `createdb` asks for a password, either type it or export it first:

```bash
export PGPASSWORD='your_postgres_password_here'
```

## 5. Load schemas and demo data

From the repo root, with the same host/port/user as `.env`:

```bash
export PGHOST=localhost PGPORT=5432 PGUSER=postgres

psql -d postgres -f unihelp_databases.sql

# Optional: load the 1,500+ student roster into timetable.people
psql -d timetable -c "\\copy people(roll_num, name, role, student_group) FROM 'timetable_users.csv' DELIMITER ',' CSV HEADER"
```

`unihelp_databases.sql` creates the eight databases if needed, then `\connect`s into each one to load tables, seed rows, and indexes. Run it with `psql` (not another client).

The room-booking, attendance, and timetable sections drop and recreate their tables. Re-running the file **wipes** existing rows in those databases.

The timetable section creates `people`, `courses`, `rooms`, and `timetable`, and seeds faculty/admin, courses, rooms, and 12 class slots. `timetable_users.csv` is the student roster (about 1,537 rows: `roll_num,name,role,student_group`). Load the SQL first, then `\copy` the CSV. The CSV has no faculty/admin rows; those come from the dump (`AD001` / `AD002` plus faculty `PF001`, `PF006` … `PF016`).

### Demo login keys

These keys are inserted by `unihelp_databases.sql` (campus_agent / complaints / organization_agent sections):

| Key | Role | Name | `roll_number` |
| --- | --- | --- | --- |
| `student-demo` | student | Aarav Sharma | `2501CS09` |
| `faculty-demo` | faculty | Priya Patel | `PF001` |
| `admin-demo` | admin | Rohan Verma | `AD001` |

Additional seeded people use the same convention: students keep IIT-style rolls (`2501CS90`, …), faculty are `PF001`–`PF016`, and admins are `AD001`–`AD002`.

Replace them before any shared or production use.

To add your own user later:

```sql
-- campus_agent
INSERT INTO users (authentication_key, role, names, roll_number)
VALUES ('my-secret-key', 'student', 'Your Name', '2501CS99');

-- complaints (id MUST equal campus_agent.users.roll_number)
INSERT INTO users (id, authentication_key, role, names, roll_number, hierarchy_level, is_active)
VALUES (
  '2501CS99',
  'my-secret-key', 'student', 'Your Name',
  '2501CS99',
  'student', TRUE
);

-- organization_agent (attendance people.roll_num is text)
INSERT INTO people (roll_num, name, role)
VALUES ('2501CS99', 'Your Name', 'student');

-- timetable (people.roll_num is text; optional student_group e.g. 'G-10')
INSERT INTO people (roll_num, name, role, student_group)
VALUES ('2501CS99', 'Your Name', 'student', 'G-1');
```

## 6. Run the server

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
- Faculty: `Publish a notice that CS101 lab is cancelled tomorrow`
- Admin: `The water cooler on my floor is broken` (files a hostel complaint)

## 7. Run the timetable agent (CLI)

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

Students get read tools only (`get_schedule`, `get_day`, `list_subjects`, …). Faculty and admin can also `add_slot` / `update_slot` / `delete_slot`. Roll numbers are forced from `--roll-num`; a student cannot fetch someone else’s schedule.

Helpers without the LLM:

```bash
python -c "import timetable_functions as T; print(T.list_subjects())"
```

## 8. Tests

Attendance tool tests talk to the live `organization_agent` database (they insert and delete rows prefixed `HXTEST`):

```bash
source .venv/bin/activate
python -m pytest tests/attendance -q
```

Syntax check without hitting the network:

```bash
python -m compileall -q .
```

Timetable helpers (live `timetable` database, no LLM):

```bash
python -c "import timetable_functions as T; print(T.get_schedule('2501CS36')['count'])"
```

Timetable helpers (live `timetable` database, no LLM):

```bash
python -c "import timetable_functions as T; print(T.get_schedule('2501CS36')['count'])"
```

## Architecture map

| Path | Role |
| --- | --- |
| `main.py` | A2A Starlette app, auth, planner/executor, port 8002 |
| `authenticator.py` | Looks up `authentication_key` in `campus_agent.users` |
| `planner.py` | Turns natural language into `{agent, request}` tasks |
| `executor.py` | Calls the matching domain agent |
| `llm.py` | Shared OpenAI-compatible client |
| `config.py` / `db.py` | Env loading and Postgres connection pools |
| `mess_agent_1.py` + `mess_functions_1.py` | Mess menus |
| `Bus_agent.py` + `bus_function.py` | Bus timetable |
| `complaint_agent.py` + `complaint_functions.py` | Complaints |
| `room_booking_agent.py` + `room_functions.py` | SAC / Guest House / CLH / Auditorium |
| `attendance_agent.py` + `attendance_functions.py` | Attendance |
| `Notice_agent.py` + `notice_functions.py` | Notice board |
| `timetable_agent.py` + `timetable_functions.py` | Class timetable |

SQL dumps:

| File | Database |
| --- | --- |
| `unihelp_databases.sql` | all eight UniHelp databases (schema + seed + indexes) |
| `timetable_users.csv` | student roster for `timetable.people` (load after `unihelp_databases.sql`) |

## Common failures

| Symptom | Likely cause |
| --- | --- |
| `connection refused` on port 5432/5434 | Postgres not running, or `PGPORT` does not match the cluster |
| `password authentication failed` | `PGUSER` / `PGPASSWORD` in `.env` |
| `database "…" does not exist` | `createdb` step skipped or name mismatch with `*_DB_NAME` |
| `ERROR: KEY NOT FOUND` | Wrong `authentication_key`, or `unihelp_databases.sql` not loaded |
| LLM errors / empty plans | Missing `LLM_API_KEY`, or `LLM_BASE_URL` / `LLM_MODEL` wrong |
| Bus queries crash under `pg8000` | Install `psycopg[binary,pool]` as in `requirements.txt` |
| Attendance tests fail | `organization_agent` not restored, or `.env` points at a different cluster |
| Timetable agent: no API key / empty plans | `LLM_API_KEY` missing from the project `.env` |
| Timetable: `database "timetable" does not exist` | `createdb timetable` or `TIMETABLE_DB_NAME` mismatch |
| Timetable: empty student schedules | `timetable_users.csv` not copied into `timetable.people` |
| `role "postgres" does not exist` | Homebrew Postgres uses your macOS username. Set `PGUSER` to that name (and often no password) |

## Security

- Treat every `authentication_key` as a password.
- Do not put keys in chat text, logs, or git.
- Bind is localhost-only (`127.0.0.1`). Do not expose port 8002 to the internet without auth in front of it.
