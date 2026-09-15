#!/usr/bin/env python3
"""Sync campus_agent.users (and complaints.users) from timetable.people.

Includes students whose schedule is defined by the current timetable seed:
  - 1st year (2601*): student_group falls in G1-G24, G1-G6, or G7-G12
  - 2nd year CS/CB (2501CS*, 2501CB*): department timetable slots (CS2%, CB2%)

authentication_key uses role-name format (e.g. student-aarav, faculty-priya),
never the roll number. Collisions append last-name then a numeric suffix.
Existing named keys (student-demo, faculty-*, …) are preserved.
"""

from __future__ import annotations

import os
import re
import sys

import psycopg

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from timetable_functions import is_group_in_range, parse_roll_number  # noqa: E402

SLOT_GROUPS = ("G1-G24", "G1-G6", "G7-G12")
DEPT_YEAR2 = frozenset({"CS", "CB"})

CONN = (
    "host={host} port={port} user={user} password={password} dbname={{db}} sslmode={sslmode}"
).format(
    host=os.getenv("PGHOST", "localhost"),
    port=os.getenv("PGPORT", "5432"),
    user=os.getenv("PGUSER", "agentx"),
    password=os.getenv("PGPASSWORD", "agentx"),
    sslmode=os.getenv("PGSSLMODE", "disable"),
)


def _name_tokens(name: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", name or "")
    return [t.lower() for t in cleaned.split() if t]


def _auth_key(role: str, name: str, roll: str, used: set[str]) -> str:
    """Build role-firstname style key; disambiguate with last name / counter."""
    tokens = _name_tokens(name)
    first = tokens[0] if tokens else "user"
    last = tokens[-1] if len(tokens) > 1 else ""

    candidates = [f"{role}-{first}"]
    if last and last != first:
        candidates.append(f"{role}-{first}-{last}")
    # more name parts if present
    if len(tokens) > 2:
        candidates.append(f"{role}-{'-'.join(tokens)}")

    for base in candidates:
        if base not in used:
            used.add(base)
            return base

    base = candidates[-1]
    n = 2
    while True:
        key = f"{base}-{n}"
        if key not in used:
            used.add(key)
            return key
        n += 1


def _matches_timetable(roll_num: str, student_group: str | None) -> bool:
    parsed = parse_roll_number(roll_num)
    year, dept = parsed["year"], parsed["dept"]
    if year == 1:
        return any(is_group_in_range(student_group, sg) for sg in SLOT_GROUPS)
    if year == 2 and dept in DEPT_YEAR2:
        return True
    return False


def _fetch_students() -> list[tuple[str, str, str | None]]:
    with psycopg.connect(CONN.format(db=os.getenv("TIMETABLE_DB_NAME", "timetable"))) as conn:
        rows = conn.execute(
            """
            SELECT roll_num, name, student_group
            FROM people
            WHERE role = 'student'
            ORDER BY roll_num
            """
        ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows if _matches_timetable(r[0], r[2])]


def _load_existing_keys(cur) -> dict[str, str]:
    """roll_number -> authentication_key for rows that already use role-name keys."""
    rows = cur.execute(
        """
        SELECT roll_number, authentication_key
        FROM users
        WHERE roll_number IS NOT NULL
          AND authentication_key IS DISTINCT FROM roll_number
        """
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _reserve_used_keys(cur) -> set[str]:
    rows = cur.execute("SELECT authentication_key FROM users").fetchall()
    return {r[0] for r in rows}


def sync_campus(students: list[tuple[str, str, str | None]]) -> int:
    db = os.getenv("AUTH_DB_NAME", "campus_agent")
    with psycopg.connect(CONN.format(db=db)) as conn:
        with conn.cursor() as cur:
            preserved = _load_existing_keys(cur)
            used = _reserve_used_keys(cur)

            # Drop roll-as-key rows first so we can re-insert with name keys
            # without colliding with authentication_key PK. Keep named-key rows.
            cur.execute(
                """
                DELETE FROM users
                WHERE role = 'student'
                  AND authentication_key = roll_number
                """
            )
            used = _reserve_used_keys(cur)

            for roll, name, _group in students:
                if roll in preserved:
                    key = preserved[roll]
                    cur.execute(
                        """
                        UPDATE users
                        SET names = %s, role = 'student'
                        WHERE roll_number = %s
                        """,
                        (name, roll),
                    )
                    used.add(key)
                    continue

                key = _auth_key("student", name, roll, used)
                cur.execute(
                    """
                    INSERT INTO users (authentication_key, role, names, roll_number)
                    SELECT %s, 'student', %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM users WHERE roll_number = %s
                    )
                    """,
                    (key, name, roll, roll),
                )
        conn.commit()
    return len(students)


def sync_complaints(students: list[tuple[str, str, str | None]]) -> int:
    db = os.getenv("COMPLAINTS_DB_NAME", "complaints")
    campus_db = os.getenv("AUTH_DB_NAME", "campus_agent")

    # Prefer campus named keys so demos stay aligned across DBs.
    campus_by_roll: dict[str, str] = {}
    with psycopg.connect(CONN.format(db=campus_db)) as campus:
        for roll, key in campus.execute(
            """
            SELECT roll_number, authentication_key
            FROM users
            WHERE roll_number IS NOT NULL
            """
        ).fetchall():
            campus_by_roll[roll] = key

    with psycopg.connect(CONN.format(db=db)) as conn:
        with conn.cursor() as cur:
            preserved = _load_existing_keys(cur)
            used = _reserve_used_keys(cur)

            for roll, name, _group in students:
                email = f"{roll.lower()}@example.edu"
                if roll in campus_by_roll:
                    key = campus_by_roll[roll]
                    used.add(key)
                elif roll in preserved:
                    key = preserved[roll]
                    used.add(key)
                else:
                    if roll in used:
                        used.discard(roll)
                    key = _auth_key("student", name, roll, used)

                cur.execute(
                    """
                    INSERT INTO users (
                        id, authentication_key, role, names, roll_number,
                        email, hierarchy_level, is_active
                    ) VALUES (%s, %s, 'student', %s, %s, %s, 'student', TRUE)
                    ON CONFLICT (id) DO UPDATE
                    SET authentication_key = EXCLUDED.authentication_key,
                        names = EXCLUDED.names,
                        roll_number = EXCLUDED.roll_number,
                        email = EXCLUDED.email,
                        role = EXCLUDED.role,
                        hierarchy_level = EXCLUDED.hierarchy_level,
                        is_active = EXCLUDED.is_active
                    """,
                    (roll, key, name, roll, email),
                )
        conn.commit()
    return len(students)


def rewrite_existing_roll_keys() -> None:
    """One-shot: convert any remaining auth_key == roll_number to role-name keys."""
    for dbname, role_col_ok in (
        (os.getenv("AUTH_DB_NAME", "campus_agent"), True),
        (os.getenv("COMPLAINTS_DB_NAME", "complaints"), True),
    ):
        with psycopg.connect(CONN.format(db=dbname)) as conn:
            with conn.cursor() as cur:
                used = _reserve_used_keys(cur)
                rows = cur.execute(
                    """
                    SELECT authentication_key, role, names, roll_number
                    FROM users
                    WHERE authentication_key = roll_number
                    ORDER BY roll_number
                    """
                ).fetchall()
                for old_key, role, name, roll in rows:
                    used.discard(old_key)
                    new_key = _auth_key(role or "student", name, roll, used)
                    if dbname.endswith("campus_agent") or dbname == "campus_agent":
                        cur.execute(
                            """
                            UPDATE users
                            SET authentication_key = %s
                            WHERE authentication_key = %s
                            """,
                            (new_key, old_key),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE users
                            SET authentication_key = %s
                            WHERE roll_number = %s
                            """,
                            (new_key, roll),
                        )
            conn.commit()
            print(f"Rewrote {len(rows)} roll-keys in {dbname}")


def main() -> None:
    students = _fetch_students()
    if not students:
        print("No matching timetable students found.")
        return
    n_campus = sync_campus(students)
    n_complaints = sync_complaints(students)
    print(f"Synced {n_campus} students -> campus_agent.users")
    print(f"Synced {n_complaints} students -> complaints.users")


if __name__ == "__main__":
    main()
