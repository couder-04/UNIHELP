# Set up a new campus on UniHelp (localhost)

One UniHelp process loads **one** org YAML and talks to **eight** Postgres databases. A new campus is a new YAML file plus, if you want isolation, eight differently named databases and a second server process. Request-time campus switching is not built.

Filled admin chat templates live in `unihelp-admin-setup-prompts.html`. **Do not put SQL in those prompts.**

---

## 0. Prerequisites

- Local Postgres up, credentials in `.env` (`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `LLM_*`).
- `.venv` installed; from repo root `.venv/bin/python` works.
- An existing schema donor. The Mandi provisioner copies **schema only** from the live Patna databases (`campus_agent`, `mess_menu`, …). Those must already exist (see `README.md` restore).
- Port `8002` free, or pick another with `UNIHELP_PORT`.

---

## 1. Collect campus facts

You need this before writing YAML or pasting Prompt 1.

| Field | Rules |
|---|---|
| `org_id` | Stable slug, e.g. `iit_mandi`. Set in the YAML file; `update_org_profile` **cannot** change it. |
| Display name | What students see, e.g. `IIT Mandi` |
| Timezone | IANA, e.g. `Asia/Kolkata` |
| Enabled agents | Subset of `mess`, `bus`, `complaint`, `room_booking`, `attendance`, `notice`, `timetable`. Day college: omit mess and bus. |
| Student id regex | Must compile. IIT-style: `^[0-9]{4}[A-Z]{2}[0-9]{2}$` |
| Hostels | If mess is on: ≥1 name. Aliases optional. |
| Rooms | If room_booking is on: map onto **SAC Hall, Guest House, CLH, Auditorium** (those four booking types are fixed). |
| Buses | If bus is on: names like `Bus 01` |
| Meals | If mess is on: usually breakfast, lunch, snacks, dinner |
| Complaint categories | If complaint is on: ≥1, e.g. academic, hostel, mess |
| People | ≥1 admin, faculty, student. CSV header `role,name,roll_number` plus optional `authentication_key`. Students must match the regex. Max 500 rows. |
| Seeds (optional but needed to go live) | One menu, one bus trip, one notice if those agents are on. |

Empty catalog lists are rejected at YAML save. A student roll that fails the regex aborts the whole people import.

---

## 2. Create the org YAML

Copy a known-good profile and change **`org_id` first**. Startup requires every catalog list to be non-empty, so put placeholders if Prompt 1 will replace them.

```yaml
# orgs/<org_id>.yaml
org_id: iit_example
display_name: Example Campus
timezone: Asia/Kolkata
roles: [student, faculty, admin]
enabled_agents:
  - mess
  - bus
  - complaint
  - room_booking
  - attendance
  - notice
  - timetable
catalog:
  hostels:
    - name: Placeholder Hostel
  rooms:
    - name: SAC Hall
    - name: Guest House
    - name: CLH
    - name: Auditorium
  buses:
    - name: "Bus 01"
  meals:
    - name: breakfast
    - name: lunch
    - name: snacks
      aliases: [snack]
    - name: dinner
      aliases: [supper]
  complaint_categories:
    - academic
    - hostel
    - mess
identity:
  student_id_field: roll_number
  student_id_pattern: "^[0-9]{4}[A-Z]{2}[0-9]{2}$"
```

Do **not** edit `orgs/iit_patna.yaml` for a new campus. `update_org_profile` patches whichever file `ORG_PROFILE_PATH` points at.

---

## 3. Give the campus its own databases (recommended)

YAML alone does **not** isolate data. Mess, bus, notices, people, library rows, and attendance all live in Postgres. If you only switch YAML, students still see the other campus’s notices and bus trips.

On the **same** Postgres cluster, create eight new database names (example prefix `mandi_`):

| Role | Default (Patna) | Isolated example |
|---|---|---|
| Auth / people / custom features | `campus_agent` | `mandi_campus_agent` |
| Mess | `mess_menu` | `mandi_mess_menu` |
| Rooms | `room_booking` | `mandi_room_booking` |
| Bus | `bus_schedule` | `mandi_bus_schedule` |
| Complaints | `complaints` | `mandi_complaints` |
| Attendance | `organization_agent` | `mandi_organization_agent` |
| Notices | `notice_board` | `mandi_notice_board` |
| Timetable | `timetable` | `mandi_timetable` |

For IIT Mandi this is already scripted (schema copy + Mandi seed, **does not drop** Patna DBs):

```bash
.venv/bin/python scripts/create_iit_mandi_demo_db.py
```

Re-running that script **drops and recreates only** the `mandi_*` databases. Stop any server using them first.

For a different campus, copy that script, change `SOURCE_TO_MANDI`, `ORG_ID`, `PEOPLE`, hostel/bus/notice seeds, and the `AUTH_DB_NAME=…` exports in the run script.

You still need **mess `(hostel, day)` rows** before “set today’s breakfast” can succeed: `modify_menu` only `UPDATE`s. The Mandi script inserts a full week for each new hostel. Do that in the provisioner, not in the admin prompt.

---

## 4. Start a server pointed at that YAML and those DBs

One process, one campus:

```bash
export ORG_PROFILE_PATH=orgs/<org_id>.yaml
export UNIHELP_PORT=8002          # or 8003 if 8002 is Patna
export PUBLIC_BASE_URL=http://127.0.0.1:$UNIHELP_PORT
export AUTH_DB_NAME=…             # eight names from the table above
export MESS_DB_NAME=…
export ROOM_DB_NAME=…
export BUS_DB_NAME=…
export COMPLAINTS_DB_NAME=…
export ATTENDANCE_DB_NAME=…
export NOTICE_DB_NAME=…
export TIMETABLE_DB_NAME=…

.venv/bin/python main.py
```

`python-dotenv` does not override variables already in the environment, so exporting the eight names **after** `.env` is loaded (as `scripts/run_iit_mandi.sh` does) is the reliable pattern.

IIT Mandi shortcut (loads `.env` for Postgres/LLM, then overrides DB names):

```bash
bash scripts/run_iit_mandi.sh
```

If you see `[Errno 48] address already in use`, something is already on that port. Stop it, or set `UNIHELP_PORT` to a free port.

Ask UI: `http://127.0.0.1:<port>/ask`  
Agent card: `http://127.0.0.1:<port>/.well-known/agent-card.json` (name should be the new campus).

---

## 5. Bootstrap an admin key

Setup chat is **admin-only**.

- Isolated empty DBs: the provisioner must insert at least one admin in `people` (Mandi: `mandi-admin`). Patna’s `admin-demo` will **not** work on isolated Mandi DBs.
- Shared Patna DBs: you can sign in as `admin-demo` and import campus people in Prompt 1.

GUI default keys (`admin-demo` / `faculty-demo` / `student-demo`) only exist if you seeded them in **this** campus’s `people` table.

---

## 6. Prompt 1 — profile, people, seeds

Sign in as admin. Paste **one** message. Source of the blank template: `unihelp-admin-setup-prompts.html`.

```
SETUP CAMPUS DATABASE. I am an authenticated admin.
Execute every section in order. Do not invent names I did not list.
Do not run SQL or CREATE TABLE. Use setup for A and B. Use the
matching domain agents for C (only for agents I enabled).
When done, quote: saved display_name, enabled_agents, catalog names,
every generated authentication_key, and which seed writes succeeded.

A. PROFILE (update_org_profile)
- display_name: [CAMPUS NAME]
- timezone: [IANA TIMEZONE]
- student_id_field: roll_number
- student_id_pattern: [REGEX]
- enabled_agents: [mess, bus, complaint, room_booking, attendance, notice, timetable]
- replace_hostels: [NAME (aliases: ...)], ...
- replace_rooms: [SAC Hall, Guest House, CLH, Auditorium]
- replace_buses: [Bus 01, Bus 02, ...]
- replace_meals: [breakfast, lunch, snacks (alias snack), dinner (alias supper)]
- replace_complaint_categories: [academic, hostel, mess]

B. PEOPLE (import_people, csv_text). Abort the batch if any student
roll fails the regex. Max 500 rows.
role,name,roll_number,authentication_key
admin,[ADMIN NAME],[ADMIN ID],[OPTIONAL KEY]
faculty,[FACULTY NAME],[FACULTY ID],[OPTIONAL KEY]
student,[STUDENT NAME],[STUDENT ROLL],[OPTIONAL KEY]

C. SEED (skip any agent I disabled)
Mess: set today's [HOSTEL] [MEAL] to [DISH].
Bus: add [Bus NN] weekdays [HH:MM] from [STOP A] to [STOP B], driver [NAME], phone [PHONE].
Notice: publish "[NOTICE TEXT]".
```

Copy generated authentication keys from the reply (they are shown once if you omitted them in the CSV).

### Follow-ups you will likely need after Prompt 1

The planner splits A/B/C across setup, mess, bus, and notice. Mess often asks **temporary vs permanent**. Bus often asks **each weekday vs one day**. Answer those as extra admin messages, still with no SQL:

- `Temporary change: set today's [HOSTEL] breakfast to [DISH].`
- `Add [Bus NN] for each weekday Monday through Friday at [HH:MM] from [STOP A] to [STOP B], driver [NAME], phone [PHONE].`

Notices students can see need `target_audience` containing `All` (or `All_Students`). If a published notice does not show up for a student, that is the usual cause.

---

## 7. Prompt 2 — JSON feature (optional, after Prompt 1 succeeds)

This registers list/search/add records. It does **not** `CREATE TABLE` and does **not** add a Python agent file.

```
DEFINE A NEW CAMPUS AGENT. I am an authenticated admin.
Use add_feature only. Do not run SQL, do not CREATE TABLE, do not
reuse a built-in name (mess, bus, complaint, room_booking, attendance,
notice, timetable, setup). Then add the seed records onto that feature.
Finally tell me the slug, keywords, field list, and one student
smoke-test phrase.

- name: [AGENT NAME]
- title: [DISPLAY TITLE]
- description: [WHAT IT DOES IN ONE SENTENCE]
- keywords: [word1, word2, word3]
- roles that may use it: [student, faculty, admin]
- fields:
  - [field_name] ([string|number|boolean|date], required|optional) — [what it stores]
- seed records (add_record on the new agent):
  1) [field]=[value]; [field]=[value]
```

Reserved slugs cannot be reused: mess, bus, complaint, room_booking, attendance, notice, timetable, setup, planner, executor, people, users, admin, custom, org, feature.

Setup has **no** `add_record` tool. After `add_feature` succeeds, add seed rows as a **second** admin message to the new agent, e.g. `Add two library books. 1) title=…; author=…`.

A hospital/fees system with its own schema still needs a real coded agent.

---

## 8. Smoke-test as a student of the new campus

Use a key imported in Prompt 1, not leftover Patna keys (unless you are on the shared Patna DBs).

| Check | Example |
|---|---|
| Catalog names | Mess should offer **this** campus’s hostels, not Kalam/Asima |
| Menu seed | `What is breakfast at [HOSTEL] today?` |
| Bus seed | `When is Bus 01 from [STOP] on Monday?` |
| Notice seed | `Show me the latest notices.` — only this campus if DBs are isolated |
| Feature seed | `Search the library for algorithms.` |
| Attendance (if seeded) | `What is my CS101 attendance?` |
| Users list | `GET /api/users` should be this campus’s roster only when isolated |

Before students: confirm a hostel alias resolves and one live query per enabled agent uses the new names.

---

## 9. Worked example: IIT Mandi (already in this repo)

| Piece | Value |
|---|---|
| YAML | `orgs/iit_mandi.yaml` (`org_id: iit_mandi`) |
| Create DBs | `.venv/bin/python scripts/create_iit_mandi_demo_db.py` |
| Run | `bash scripts/run_iit_mandi.sh` → `http://127.0.0.1:8002` |
| Admin / faculty / student | `mandi-admin` / `mandi-faculty` / `mandi-asha` |
| Hostels | Chandra (alias C hostel), Suvalsar |
| Seeds | Chandra Saturday breakfast `poha and tea`; Bus 01 weekdays 08:00 Chandra → academic block; notice “Orientation Monday 9am, Auditorium.”; library Cormen + Galvin; Asha CS101 91.67% |

Prompt 1 filled example and library Prompt 2 are in `unihelp-admin-setup-prompts.html`. A blow-by-blow of the first local run is `IIT_MANDI_LOCAL_SETUP.txt`. Env name list: `iit_mandi.env.example`.

---

## 10. Run Patna and the new campus at the same time

Two processes, two ports, two sets of `*_DB_NAME`:

```bash
# Patna (defaults from .env)
UNIHELP_PORT=8003 PUBLIC_BASE_URL=http://127.0.0.1:8003 .venv/bin/python main.py

# New campus
UNIHELP_PORT=8002 bash scripts/run_iit_mandi.sh
```

Do not point two processes at the same database names if you care about isolation.

---

## 11. What this path will not do

| Request | What happens |
|---|---|
| SQL / `CREATE TABLE` in chat | Rejected. Setup has no SQL tool. |
| Empty hostels/buses catalog | Save fails; previous YAML kept as `.bak` |
| Student or faculty running setup | Planner does not offer setup; the agent refuses |
| `add_feature` named `mess` / `bus` / … | Error; reserved slugs |
| Only changing YAML, same `*_DB_NAME` | Names/routing change; **data stays shared** |
| `org_id` via Prompt 1 | Ignored; file-owned |

---

## Quick checklist

1. Write `orgs/<org_id>.yaml` with a unique `org_id` and a valid non-empty catalog.
2. Create eight isolated databases (schema + hostel menu rows + an admin person).
3. Start `main.py` with `ORG_PROFILE_PATH` and the eight `*_DB_NAME` exports.
4. Sign in as that admin.
5. Prompt 1 (profile + people + seeds). Answer mess/bus clarifications.
6. Prompt 2 if you need a JSON feature; add seed records on the new agent.
7. Smoke-test with a student key from **this** campus.
