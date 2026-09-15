"""
Bus agent tools — single database architecture using the bus_schedule table.

Schema:
    id, day, time, bus_name, start_point, destination, driver_name, driver_no

Every function returns data or a structured error dict
{"error": ..., "available_options": [...]} — never raises to the agent.
Use call_tool(name, **kwargs) for name-based dispatch (returns a JSON string).
"""

import json
import logging
import os
from datetime import date as ddate, datetime, time as dtime
from typing import List, Optional, Union

import time
import threading

import db
from config import BUS_DB_NAME

try:
    from psycopg.rows import dict_row
except ImportError:
    # Only reachable if psycopg itself isn't installed (pg8000-only
    # environment). NOTE: _fetch()'s `row_factory=dict_row` is psycopg-
    # specific and does not work against a raw pg8000 connection either —
    # this was already true before this change. Recommend standardizing on
    # psycopg (+ psycopg_pool, which requires it anyway) rather than
    # supporting both drivers long-term; see CURSOR_PROMPT.md.
    dict_row = None

logger = logging.getLogger(__name__)

Result = Union[list, dict]


# ── DB helpers ──────────────────────────────────────────────────────────── #

def get_connection():
    # Pooled connection when psycopg_pool is installed (see db.py); env
    # overrides for host/port/user/password are handled there too.
    return db.get_connection(BUS_DB_NAME)


def _fetch(query: str, params: tuple = ()) -> List[dict]:
    con = get_connection()
    try:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        con.close()


def _execute(query: str, params: tuple = ()) -> int:
    con = get_connection()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount
    finally:
        con.close()


# ── parsing / formatting helpers ────────────────────────────────────────── #

def _parse_time(s):
    try:
        return datetime.strptime(s.strip(), "%H:%M").time()
    except (ValueError, AttributeError):
        return None


def _parse_date(s: str) -> ddate:
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def _t(t) -> Optional[str]:
    if t is None:
        return None
    return t.strftime("%H:%M") if hasattr(t, "strftime") else str(t)


def _error(message: str, available_options=None, hint=None) -> dict:
    r: dict = {"error": message}
    if available_options:
        r["available_options"] = available_options
    if hint:
        r["hint"] = hint
    return r


def _row_to_dict(row: dict) -> dict:
    dep = row["time"]
    dep_s = _t(dep) if dep else str(dep)
    return {
        "schedule_id": row["id"],
        "route_name": row["bus_name"],
        "day": row["day"],
        "arrival_time": dep_s,
        "departure_time": dep_s,
        "bus_id": row["bus_name"],
        "start_point": row["start_point"],
        "destination": row["destination"],
        "stops": f"{row['start_point']} -> {row['destination']}",
        "driver_name": row.get("driver_name") or "",
        "driver_no": row.get("driver_no") or "",
    }


def _resolve_bus(want: str, rows: List[dict]) -> tuple:
    """Exact (case-insensitive) bus match, else partial fallback. Returns (bus, rows)."""
    norm = want.strip().lower()
    names = sorted({r["bus_name"] for r in rows})
    exact = [r for r in rows if r["bus_name"].strip().lower() == norm]
    if exact:
        return exact[0]["bus_name"], exact
    for name in names:
        if norm in name.lower():
            return name, [r for r in rows if r["bus_name"] == name]
    return None, names


# Route topology (which stops exist, which bus goes where) only changes when
# a schedule is added/removed/changed — not on every read. _all_stops() and
# _legs() used to re-scan the whole table on every single call (and
# find_route_by_destination/next_departure call them repeatedly within one
# conversation turn). Cache them for a short TTL and invalidate explicitly
# on any successful write.
_TOPOLOGY_CACHE_TTL_SECONDS = 60
_topology_cache_lock = threading.Lock()
_topology_cache: dict = {}  # key -> (expires_at, value)


def _topology_cached(key, compute_fn):
    with _topology_cache_lock:
        entry = _topology_cache.get(key)
        if entry is not None and time.time() < entry[0]:
            return entry[1]
    value = compute_fn()
    with _topology_cache_lock:
        _topology_cache[key] = (time.time() + _TOPOLOGY_CACHE_TTL_SECONDS, value)
    return value


def _invalidate_topology_cache():
    with _topology_cache_lock:
        _topology_cache.clear()


def _all_stops() -> List[str]:
    def _compute():
        rows = _fetch(
            "SELECT DISTINCT start_point AS s FROM bus_schedule "
            "UNION SELECT DISTINCT destination FROM bus_schedule ORDER BY 1"
        )
        return [r["s"] for r in rows]

    return _topology_cached("all_stops", _compute)


def _match_stop(want: str, stops: List[str]) -> Optional[str]:
    norm = want.strip().lower()
    for s in stops:
        if s.strip().lower() == norm:
            return s
    for s in stops:
        if norm in s.lower():
            return s
    return None


# ── 1. query_schedule ───────────────────────────────────────────────────── #

def query_schedule(route_name: str, day: Optional[str] = None,
                   date: Optional[str] = None) -> Result:
    """Timetable for a bus; optional day or date filter."""
    try:
        on_date = _parse_date(date) if date else None
    except ValueError:
        return _error(f"'{date}' is not a valid date — use YYYY-MM-DD, e.g. '2026-09-15'.")

    if on_date:
        day = on_date.strftime("%A")

    rows = _fetch("SELECT * FROM bus_schedule ORDER BY time")
    bus, matched = _resolve_bus(route_name, rows)
    if bus is None:
        return _error(f"I couldn't find a route called '{route_name}'.",
                      available_options=matched)
    if day:
        want = day.strip().lower()
        matched = [r for r in matched if (r["day"] or "").strip().lower() == want]
        if not matched:
            days = sorted({r["day"] for r in rows if r["bus_name"] == bus})
            return _error(f"No departures for '{bus}' on '{day}'.",
                          available_options=days)
    return [_row_to_dict(r) for r in matched]


# ── 2. query_active_buses ───────────────────────────────────────────────── #

def query_active_buses(time_str: Optional[str] = None) -> Result:
    """Buses whose departure was within the last 45 minutes."""
    _ACTIVE_WINDOW_MINUTES = 45
    if not time_str:
        qt = datetime.now().time()
        time_str = qt.strftime("%H:%M")
    else:
        try:
            qt = _parse_time(time_str)
        except ValueError:
            return _error(f"'{time_str}' doesn't look like HH:MM — e.g. '09:30'.")

        if qt is None:
            return _error(f"'{time_str}' doesn't look like HH:MM — e.g. '09:30'.")

    today_name = datetime.now().strftime("%A")
    qmin = qt.hour * 60 + qt.minute
    rows = _fetch("SELECT * FROM bus_schedule WHERE day = %s ORDER BY time", (today_name,))
    out, seen = [], set()
    for r in rows:
        dep = r["time"]
        if dep is None:
            continue
        dep_min = dep.hour * 60 + dep.minute if hasattr(dep, "hour") else 0
        diff = qmin - dep_min
        if 0 <= diff <= _ACTIVE_WINDOW_MINUTES and r["bus_name"] not in seen:
            seen.add(r["bus_name"])
            out.append({
                "bus_id": r["bus_name"],
                "route_name": r["bus_name"],
                "departure_time": _t(dep),
                "stops": f"{r['start_point']} -> {r['destination']}",
                "driver_name": r["driver_name"] or "",
                "status": "Active",
            })
    if not out:
        return _error(f"Nothing on the road right around {time_str} (45-min window). Try a later time?")
    return out


# ── 3. query_driver ─────────────────────────────────────────────────────── #

def query_driver(bus_id: str) -> dict:
    """Driver name + contact for a bus."""
    rows = _fetch("SELECT DISTINCT bus_name, driver_name, driver_no FROM bus_schedule")
    norm = bus_id.strip().upper()
    hit = next((r for r in rows if r["bus_name"].strip().upper() == norm), None)
    if hit is None:
        for r in rows:
            if norm in r["bus_name"].upper():
                hit = r
                break
    if hit is None:
        return _error(f"I couldn't find a driver for bus '{bus_id}'.",
                      available_options=sorted({r["bus_name"] for r in rows}))
    return {"bus_id": hit["bus_name"], "driver_name": hit["driver_name"] or "",
            "contact_number": hit["driver_no"] or ""}


# ── 4. query_time_window ────────────────────────────────────────────────── #

def query_time_window(start_time: str, end_time: str,
                      date: Optional[str] = None) -> Result:
    """All departures strictly between two HH:MM times."""
    try:
        start = _parse_time(start_time)
    except ValueError:
        return _error(f"'{start_time}' invalid — use HH:MM, e.g. '08:00'.")

    if start is None:
        return _error(f"'{start_time}' invalid — use HH:MM, e.g. '08:00'.")

    try:
        end = _parse_time(end_time)
    except ValueError:
        return _error(f"'{end_time}' invalid — use HH:MM, e.g. '12:00'.")

    if end is None:
        return _error(f"'{end_time}' invalid — use HH:MM, e.g. '12:00'.")

    if start >= end:
        return _error("Start must be earlier than end — e.g. 08:00 to 12:00.")

    if date:
        try:
            on_date = _parse_date(date)
            day = on_date.strftime("%A")
        except ValueError:
            return _error(f"'{date}' invalid — use YYYY-MM-DD.")
        rows = _fetch("SELECT * FROM bus_schedule WHERE day = %s ORDER BY time", (day,))
    else:
        rows = _fetch("SELECT * FROM bus_schedule ORDER BY time")

    out = []
    start_s = start.strftime("%H:%M")
    end_s = end.strftime("%H:%M")

    for r in rows:
        d = _row_to_dict(r)
        dep = d["departure_time"] or ""
        if start_s < dep < end_s:
            out.append(d)

    if not out:
        return _error(f"Nothing departs strictly between {start_time} and {end_time}. Try a wider window?")

    return out


# ── 5. find_route_by_destination ────────────────────────────────────────── #

def _legs() -> dict:
    """bus_name -> set of (start, destination) legs."""
    def _compute():
        legs: dict = {}
        for r in _fetch("SELECT DISTINCT bus_name, start_point, destination FROM bus_schedule"):
            legs.setdefault(r["bus_name"], set()).add((r["start_point"], r["destination"]))
        return legs

    return _topology_cached("legs", _compute)


def find_route_by_destination(current_location: str, destination: str,
                              date: Optional[str] = None) -> Result:
    """Direct buses first, else one-transfer connections, between two stops."""
    if date:
        try:
            _parse_date(date)
        except ValueError:
            return _error(f"'{date}' invalid — use YYYY-MM-DD.")
    stops = _all_stops()
    s_from = _match_stop(current_location, stops)
    if s_from is None:
        return _error(f"'{current_location}' isn't a known stop.", available_options=stops)
    s_to = _match_stop(destination, stops)
    if s_to is None:
        return _error(f"'{destination}' isn't a known stop.", available_options=stops)
    legs = _legs()
    results = []
    for bus, pairs in legs.items():
        if (s_from, s_to) in pairs:
            results.append({"type": "direct", "route_name": bus,
                            "board_at": s_from, "alight_at": s_to,
                            "stops_sequence": [s_from, s_to]})
    if not results:
        seen = set()
        for bus_f, pairs_f in legs.items():
            middles = sorted({d for s, d in pairs_f if s == s_from})
            for inter in middles:
                for bus_s, pairs_s in legs.items():
                    if bus_s == bus_f:
                        continue
                    if (inter, s_to) in pairs_s:
                        key = (bus_f, inter.lower(), bus_s)
                        if key in seen:
                            continue
                        seen.add(key)
                        results.append({
                            "type": "one_transfer",
                            "leg_1": {"route_name": bus_f, "board_at": s_from, "alight_at": inter},
                            "transfer_at": inter,
                            "leg_2": {"route_name": bus_s, "board_at": inter, "alight_at": s_to},
                        })
    if not results:
        return _error(f"No trip from '{current_location}' to '{destination}'. Try nearby stops?",
                      available_options=stops)
    return results


# ── 6. next_departure ───────────────────────────────────────────────────── #

def next_departure(current_location: str, destination: str,
                   at_time: Optional[str] = None,
                   date: Optional[str] = None) -> dict:
    """Single earliest run from A to B at or after at_time (default: now)."""
    if at_time:
        try:
            parsed_time = _parse_time(at_time)
        except ValueError:
            return _error(f"'{at_time}' doesn't look like HH:MM — e.g. '08:15'.")

        if parsed_time is None:
            return _error(f"'{at_time}' doesn't look like HH:MM — e.g. '08:15'.")

        ref = parsed_time.strftime("%H:%M")
    else:
        ref = datetime.now().strftime("%H:%M")

    on_date = None
    if date:
        try:
            on_date = _parse_date(date)
        except ValueError:
            return _error(f"'{date}' invalid — use YYYY-MM-DD.")

    day_name = (on_date or ddate.today()).strftime("%A")

    routes = find_route_by_destination(current_location, destination, date)
    if isinstance(routes, dict) and "error" in routes:
        return routes

    best: Optional[dict] = None
    days_seen: set = set()

    for r in routes:
        if r["type"] == "direct":
            route_name, board, alight = r["route_name"], r["board_at"], r["alight_at"]
            extra = {"type": "direct", "stops_sequence": r.get("stops_sequence", [])}
        else:
            leg = r["leg_1"]
            route_name, board = leg["route_name"], leg["board_at"]
            alight = r["leg_2"]["alight_at"]
            extra = {
                "type": "one_transfer",
                "transfer_at": r["transfer_at"],
                "leg_2_route": r["leg_2"]["route_name"]
            }

        scheds = query_schedule(route_name, date=date)

        if not isinstance(scheds, list) or not scheds:
            continue

        for s in scheds:
            days_seen.add(s.get("day", ""))

        pool = [s for s in scheds if (s.get("day") or "") == day_name]

        if not pool:
            continue

        for s in pool:
            dep = s.get("departure_time") or ""

            if dep >= ref and (best is None or dep < best["departure_time"]):
                best = {
                    "route_name": route_name,
                    "board_at": board,
                    "alight_at": alight,
                    "departure_time": dep,
                    "arrival_time": s.get("arrival_time"),
                    "bus_id": s.get("bus_id", ""),
                    "day": s.get("day", ""),
                    **extra
                }

    if best is None:
        extra_msg = f" It runs on: {', '.join(sorted(days_seen))}." if days_seen else ""

        return _error(
            f"No departures from '{current_location}' to '{destination}' "
            f"on {day_name} after {ref}.{extra_msg}",
            hint="Try an earlier time or another day."
        )

    return {
        "status": "success",
        "reference_time": ref,
        "day_type": day_name,
        "target_date": date,
        **best
    }


# ── 7. get_db_status ───────────────────────────────────────────────────── #

def get_db_status() -> dict:
    """Return row counts from bus_schedule."""
    rows = _fetch("SELECT COUNT(*) AS cnt FROM bus_schedule")
    total = rows[0]["cnt"] if rows else 0
    day_rows = _fetch("SELECT day, COUNT(*) AS cnt FROM bus_schedule GROUP BY day ORDER BY day")
    by_day = {r["day"]: r["cnt"] for r in day_rows}
    return {"total_schedules": total, "by_day": by_day}

#-------8 . write in database------
def _check_write_authorization(user):
    if not isinstance(user, str):
        return {"status": "error", "message": "Not authorised."}

    if user.lower() not in ("faculty", "admin"):
        return {"status": "error", "message": "Not authorised."}

    return None


def add_schedule(
    day,
    time_str,
    bus_name,
    start_point,
    destination,
    driver_name,
    driver_no,
    user
):
    auth_error = _check_write_authorization(user)

    if auth_error:
        return auth_error

    parsed_time = _parse_time(time_str)

    if parsed_time is None:
        return {
            "status": "error",
            "message": f"Invalid time '{time_str}'."
        }

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO bus_schedule
            (day, time, bus_name, start_point, destination, driver_name, driver_no)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                day,
                parsed_time,
                bus_name,
                start_point,
                destination,
                driver_name,
                driver_no
            )
        )

        new_id = cur.fetchone()[0]

        conn.commit()
        _invalidate_topology_cache()

        return {
            "status": "success",
            "message": "Bus schedule added successfully.",
            "id": new_id,
            "day": day,
            "time": str(parsed_time),
            "bus_name": bus_name,
            "start_point": start_point,
            "destination": destination,
            "driver_name": driver_name,
            "driver_no": driver_no
        }

    except Exception as e:
        conn.rollback()

        return {
            "status": "error",
            "message": f"Failed to add schedule: {e}"
        }

    finally:
        cur.close()
        conn.close()


def remove_schedule(schedule_id, user):
    auth_error = _check_write_authorization(user)

    if auth_error:
        return auth_error

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            DELETE FROM bus_schedule
            WHERE id = %s
            RETURNING id
            """,
            (schedule_id,)
        )

        row = cur.fetchone()

        if row is None:
            return {
                "status": "not_found",
                "message": f"No schedule found with id {schedule_id}."
            }

        conn.commit()
        _invalidate_topology_cache()

        return {
            "status": "success",
            "message": "Bus schedule removed successfully.",
            "id": row[0]
        }

    except Exception as e:
        conn.rollback()

        return {
            "status": "error",
            "message": f"Failed to remove schedule: {e}"
        }

    finally:
        cur.close()
        conn.close()


def change_schedule(
    schedule_id,
    day=None,
    time_str=None,
    bus_name=None,
    start_point=None,
    destination=None,
    driver_name=None,
    driver_no=None,
    user=None
):
    auth_error = _check_write_authorization(user)

    if auth_error:
        return auth_error

    updates = []
    values = []

    if day is not None:
        updates.append("day = %s")
        values.append(day)

    if time_str is not None:
        parsed_time = _parse_time(time_str)

        if parsed_time is None:
            return {
                "status": "error",
                "message": f"Invalid time '{time_str}'."
            }

        updates.append("time = %s")
        values.append(parsed_time)

    if bus_name is not None:
        updates.append("bus_name = %s")
        values.append(bus_name)

    if start_point is not None:
        updates.append("start_point = %s")
        values.append(start_point)

    if destination is not None:
        updates.append("destination = %s")
        values.append(destination)

    if driver_name is not None:
        updates.append("driver_name = %s")
        values.append(driver_name)

    if driver_no is not None:
        updates.append("driver_no = %s")
        values.append(driver_no)

    if not updates:
        return {
            "status": "error",
            "message": "No fields provided for modification."
        }

    values.append(schedule_id)

    conn = get_connection()
    cur = conn.cursor()

    try:
        query = f"""
            UPDATE bus_schedule
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING
                id,
                day,
                time,
                bus_name,
                start_point,
                destination,
                driver_name,
                driver_no
        """

        cur.execute(query, values)

        row = cur.fetchone()

        if row is None:
            return {
                "status": "not_found",
                "message": f"No schedule found with id {schedule_id}."
            }

        conn.commit()
        _invalidate_topology_cache()

        return {
            "status": "success",
            "message": "Bus schedule updated successfully.",
            "schedule": {
                "id": row[0],
                "day": row[1],
                "time": str(row[2]),
                "bus_name": row[3],
                "start_point": row[4],
                "destination": row[5],
                "driver_name": row[6],
                "driver_no": row[7]
            }
        }

    except Exception as e:
        conn.rollback()

        return {
            "status": "error",
            "message": f"Failed to update schedule: {e}"
        }

    finally:
        cur.close()
        conn.close()


# ── agent dispatch ──────────────────────────────────────────────────────── #

TOOLS = {
    "query_schedule": query_schedule,
    "query_active_buses": query_active_buses,
    "query_driver": query_driver,
    "query_time_window": query_time_window,
    "find_route_by_destination": find_route_by_destination,
    "next_departure": next_departure,
    "get_db_status": get_db_status,

    "add_schedule": add_schedule,
    "remove_schedule": remove_schedule,
    "change_schedule": change_schedule,
}


def call_tool(name: str, **kwargs) -> str:
    """Dispatch one tool by name for the agent. Always returns a JSON string."""
    fn = TOOLS.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool '{name}'.",
                           "available_options": sorted(TOOLS)})
    try:
        return json.dumps(fn(**kwargs), indent=2, ensure_ascii=False)
    except TypeError as exc:
        return json.dumps({"error": f"Bad arguments for '{name}': {exc}"})
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        return json.dumps({"error": f"Sorry, something glitched: {exc}"})

# print("\n" + "=" * 60)
# print("BUS AGENT FUNCTION TESTS")
# print("=" * 60)

# print("\nTEST 1: DATABASE STATUS")
# print("=" * 60)
# result = get_db_status()
# print(result)

# print("\nTEST 2: QUERY ALL SCHEDULES")
# print("=" * 60)
# result = query_schedule("Bus 02")
# print(result)

# print("\nTEST 3: QUERY MONDAY")
# print("=" * 60)
# result = query_schedule(
#     route_name="Bus 02",
#     day="Monday"
# )
# print(result)

# print("\nTEST 4: QUERY BY DATE")
# print("=" * 60)
# result = query_schedule(
#     route_name="Bus 02",
#     date="2026-09-14"
# )
# print(result)

# print("\nTEST 5: INVALID BUS")
# print("=" * 60)
# result = query_schedule("Bus 999")
# print(result)

# print("\nTEST 6: INVALID DATE")
# print("=" * 60)
# result = query_schedule(
#     route_name="Bus 02",
#     date="abc"
# )
# print(result)

# print("\nTEST 7: ACTIVE BUSES")
# print("=" * 60)
# result = query_active_buses("09:30")
# print(result)

# print("\nTEST 8: INVALID TIME")
# print("=" * 60)
# result = query_active_buses("abc")
# print(result)

# print("\nTEST 9: QUERY DRIVER")
# print("=" * 60)
# result = query_driver("Bus 02")
# print(result)

# print("\nTEST 10: INVALID DRIVER BUS")
# print("=" * 60)
# result = query_driver("Bus 999")
# print(result)

# print("\nTEST 11: TIME WINDOW")
# print("=" * 60)
# result = query_time_window(
#     start_time="08:00",
#     end_time="12:00"
# )
# print(result)

# print("\nTEST 12: INVALID TIME WINDOW")
# print("=" * 60)
# result = query_time_window(
#     start_time="12:00",
#     end_time="08:00"
# )
# print(result)

# print("\nTEST 13: INVALID START TIME")
# print("=" * 60)
# result = query_time_window(
#     start_time="abc",
#     end_time="12:00"
# )
# print(result)

# print("\nTEST 14: FIND ROUTE")
# print("=" * 60)
# result = find_route_by_destination(
#     current_location="Patna",
#     destination="IIT Patna"
# )
# print(result)

# print("\nTEST 15: INVALID START LOCATION")
# print("=" * 60)
# result = find_route_by_destination(
#     current_location="XYZ",
#     destination="IIT Patna"
# )
# print(result)

# print("\nTEST 16: INVALID DESTINATION")
# print("=" * 60)
# result = find_route_by_destination(
#     current_location="Patna",
#     destination="XYZ"
# )
# print(result)

# print("\nTEST 17: NEXT DEPARTURE")
# print("=" * 60)
# result = next_departure(
#     current_location="Patna",
#     destination="IIT Patna",
#     at_time="08:00",
#     date="2026-09-14"
# )
# print(result)

# print("\nTEST 18: INVALID NEXT DEPARTURE TIME")
# print("=" * 60)
# result = next_departure(
#     current_location="Patna",
#     destination="IIT Patna",
#     at_time="abc",
#     date="2026-09-14"
# )
# print(result)

# print("\nTEST 19: UNKNOWN TOOL")
# print("=" * 60)
# result = call_tool("unknown_tool")
# print(result)

# print("\nTEST 20: CALL TOOL DISPATCH")
# print("=" * 60)
# result = call_tool(
#     "query_driver",
#     bus_id="Bus 02"
# )
# print(result)

# print("\n" + "=" * 60)
# print("ALL TESTS COMPLETED")
# print("=" * 60)

# print("\n" + "=" * 60)
# print("BUS AGENT WRITE FUNCTION TESTS")
# print("=" * 60)


# print("\nTEST 1: ADMIN ADDS A NEW SCHEDULE")
# print("-" * 60)

# result = add_schedule(
#     day="Monday",
#     time_str="16:30",
#     bus_name="Bus 99",
#     start_point="Kalam",
#     destination="Patna",
#     driver_name="Test Driver",
#     driver_no="9999999999",
#     user="admin"
# )

# print(result)

# if result["status"] != "success":
#     raise SystemExit("TEST 1 FAILED")

# test_id = result["id"]


# print("\nTEST 2: FACULTY ADDS A NEW SCHEDULE")
# print("-" * 60)

# result = add_schedule(
#     day="Tuesday",
#     time_str="10:30",
#     bus_name="Bus 98",
#     start_point="Aryabhatta",
#     destination="Rajeev Nagar",
#     driver_name="Faculty Test Driver",
#     driver_no="8888888888",
#     user="faculty"
# )

# print(result)

# if result["status"] != "success":
#     raise SystemExit("TEST 2 FAILED")

# faculty_test_id = result["id"]


# print("\nTEST 3: STUDENT TRIES TO ADD A SCHEDULE")
# print("-" * 60)

# result = add_schedule(
#     day="Wednesday",
#     time_str="11:30",
#     bus_name="Bus 97",
#     start_point="Kalam",
#     destination="Patna",
#     driver_name="Student Test Driver",
#     driver_no="7777777777",
#     user="student"
# )

# print(result)

# if result["message"] != "Not authorised.":
#     raise SystemExit("TEST 3 FAILED")


# print("\nTEST 4: INVALID TIME")
# print("-" * 60)

# result = add_schedule(
#     day="Monday",
#     time_str="25:99",
#     bus_name="Bus 96",
#     start_point="Kalam",
#     destination="Patna",
#     driver_name="Test Driver",
#     driver_no="6666666666",
#     user="admin"
# )

# print(result)

# if result["status"] != "error":
#     raise SystemExit("TEST 4 FAILED")


# print("\nTEST 5: READ THE NEWLY ADDED SCHEDULE")
# print("-" * 60)

# result = get_room_details if False else None

# result = query_schedule(
#     route_name="Kalam",
#     day="Monday"
# )

# print(result)


# print("\nTEST 6: CHANGE SCHEDULE USING FACULTY")
# print("-" * 60)

# result = change_schedule(
#     schedule_id=test_id,
#     destination="Rajeev Nagar",
#     driver_name="Updated Driver",
#     driver_no="1111111111",
#     user="faculty"
# )

# print(result)

# if result["status"] != "success":
#     raise SystemExit("TEST 6 FAILED")


# print("\nTEST 7: CHANGE SCHEDULE USING ADMIN")
# print("-" * 60)

# result = change_schedule(
#     schedule_id=test_id,
#     time_str="17:00",
#     start_point="Aryabhatta",
#     destination="Bihar museum",
#     user="admin"
# )

# print(result)

# if result["status"] != "success":
#     raise SystemExit("TEST 7 FAILED")


# print("\nTEST 8: STUDENT TRIES TO CHANGE SCHEDULE")
# print("-" * 60)

# result = change_schedule(
#     schedule_id=test_id,
#     destination="Kalam",
#     user="student"
# )

# print(result)

# if result["message"] != "Not authorised.":
#     raise SystemExit("TEST 8 FAILED")


# print("\nTEST 9: INVALID SCHEDULE ID FOR CHANGE")
# print("-" * 60)

# result = change_schedule(
#     schedule_id=999999,
#     destination="Kalam",
#     user="admin"
# )

# print(result)

# if result["status"] != "not_found":
#     raise SystemExit("TEST 9 FAILED")


# print("\nTEST 10: NO FIELDS PROVIDED TO CHANGE")
# print("-" * 60)

# result = change_schedule(
#     schedule_id=test_id,
#     user="admin"
# )

# print(result)

# if result["status"] != "error":
#     raise SystemExit("TEST 10 FAILED")


# print("\nTEST 11: STUDENT TRIES TO REMOVE SCHEDULE")
# print("-" * 60)

# result = remove_schedule(
#     schedule_id=test_id,
#     user="student"
# )

# print(result)

# if result["message"] != "Not authorised.":
#     raise SystemExit("TEST 11 FAILED")


# print("\nTEST 12: INVALID SCHEDULE ID FOR REMOVE")
# print("-" * 60)

# result = remove_schedule(
#     schedule_id=999999,
#     user="admin"
# )

# print(result)

# if result["status"] != "not_found":
#     raise SystemExit("TEST 12 FAILED")


# print("\nTEST 13: ADMIN REMOVES SCHEDULE")
# print("-" * 60)

# result = remove_schedule(
#     schedule_id=test_id,
#     user="admin"
# )

# print(result)

# if result["status"] != "success":
#     raise SystemExit("TEST 13 FAILED")


# print("\nTEST 14: VERIFY REMOVED SCHEDULE")
# print("-" * 60)

# result = change_schedule(
#     schedule_id=test_id,
#     destination="Kalam",
#     user="admin"
# )

# print(result)

# if result["status"] != "not_found":
#     raise SystemExit("TEST 14 FAILED")


# print("\nTEST 15: FACULTY SCHEDULE STILL EXISTS")
# print("-" * 60)

# result = change_schedule(
#     schedule_id=faculty_test_id,
#     destination="Bihar museum",
#     user="faculty"
# )

# print(result)

# if result["status"] != "success":
#     raise SystemExit("TEST 15 FAILED")


# print("\nTEST 16: REMOVE FACULTY TEST SCHEDULE")
# print("-" * 60)

# result = remove_schedule(
#     schedule_id=faculty_test_id,
#     user="faculty"
# )

# print(result)

# if result["status"] != "success":
#     raise SystemExit("TEST 16 FAILED")


# print("\nTEST 17: CALL_TOOL ADD")
# print("-" * 60)

# result = call_tool(
#     "add_schedule",
#     day="Thursday",
#     time_str="18:00",
#     bus_name="Bus 97",
#     start_point="Kalam",
#     destination="Patna",
#     driver_name="Call Tool Driver",
#     driver_no="5555555555",
#     user="admin"
# )

# print(result)


# print("\nTEST 18: CALL_TOOL STUDENT AUTHORIZATION")
# print("-" * 60)

# result = call_tool(
#     "add_schedule",
#     day="Friday",
#     time_str="18:30",
#     bus_name="Bus 96",
#     start_point="Kalam",
#     destination="Patna",
#     driver_name="Student Driver",
#     driver_no="4444444444",
#     user="student"
# )

# print(result)


# print("\n" + "=" * 60)
# print("ALL WRITE FUNCTION TESTS COMPLETED")
# print("=" * 60)