#!/usr/bin/env python3
"""Create isolated mandi_* databases and seed the IIT Mandi demo campus.

Schema is copied from the live Patna databases (no rows). Seed data is
Mandi-only: three people, Chandra/Suvalsar menus, Bus 01 weekdays,
one notice, library books, CS101 attendance, a Monday timetable slot,
and empty room-booking catalogs (the four facility types).

Re-run drops the mandi_* databases first. Does not touch campus_agent,
mess_menu, or the other Patna databases.

Usage (repo root, .env loaded for PG* + password):

    .venv/bin/python scripts/create_iit_mandi_demo_db.py
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")

PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")
PGUSER = os.getenv("PGUSER", "postgres")
PGPASSWORD = os.getenv("PGPASSWORD", "")

SOURCE_TO_MANDI = {
    "campus_agent": "mandi_campus_agent",
    "mess_menu": "mandi_mess_menu",
    "room_booking": "mandi_room_booking",
    "bus_schedule": "mandi_bus_schedule",
    "complaints": "mandi_complaints",
    "organization_agent": "mandi_organization_agent",
    "notice_board": "mandi_notice_board",
    "timetable": "mandi_timetable",
}

ORG_ID = "iit_mandi"
PEOPLE = (
    {
        "key": "mandi-admin",
        "role": "admin",
        "name": "Campus Admin",
        "roll": "AD001",
        "id": str(uuid.uuid4()),
    },
    {
        "key": "mandi-faculty",
        "role": "faculty",
        "name": "Priya Patel",
        "roll": "PF001",
        "id": str(uuid.uuid4()),
    },
    {
        "key": "mandi-asha",
        "role": "student",
        "name": "Asha Rao",
        "roll": "2501CS99",
        "id": str(uuid.uuid4()),
    },
)


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PGPASSWORD"] = PGPASSWORD
    env["PGHOST"] = PGHOST
    env["PGPORT"] = PGPORT
    env["PGUSER"] = PGUSER
    return env


def _run(args: list[str], stdin: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        args,
        input=stdin,
        text=True,
        env=_env(),
        capture_output=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"{args[0]} failed ({result.returncode}):\n{result.stderr or result.stdout}"
        )
    return result


def _psql(dbname: str, sql: str) -> None:
    result = _run(
        [
            "psql",
            "-h",
            PGHOST,
            "-p",
            PGPORT,
            "-U",
            PGUSER,
            "-d",
            dbname,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"psql {dbname} failed:\n{result.stderr or result.stdout}"
        )


def _psql_file_stdin(dbname: str, sql: str) -> None:
    result = _run(
        [
            "psql",
            "-h",
            PGHOST,
            "-p",
            PGPORT,
            "-U",
            PGUSER,
            "-d",
            dbname,
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            "-",
        ],
        stdin=sql,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"psql {dbname} restore failed:\n{result.stderr or result.stdout}"
        )


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def recreate_databases() -> None:
    names = ", ".join(f"'{n}'" for n in SOURCE_TO_MANDI.values())
    _psql(
        "postgres",
        f"""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname IN ({names})
          AND pid <> pg_backend_pid();
        """,
    )
    for dest in SOURCE_TO_MANDI.values():
        _psql("postgres", f"DROP DATABASE IF EXISTS {dest};")
        _psql("postgres", f"CREATE DATABASE {dest} OWNER {PGUSER};")
        print(f"created {dest}")


def _sanitize_dump(sql: str) -> str:
    skip_prefixes = (
        "SET transaction_timeout",
        "\\restrict",
        "\\unrestrict",
    )
    kept = []
    for line in sql.splitlines(keepends=True):
        if line.startswith(skip_prefixes):
            continue
        kept.append(line)
    return "".join(kept)


def copy_schema() -> None:
    for source, dest in SOURCE_TO_MANDI.items():
        dump = _run(
            [
                "pg_dump",
                "-h",
                PGHOST,
                "-p",
                PGPORT,
                "-U",
                PGUSER,
                "--schema-only",
                "--no-owner",
                "--no-acl",
                source,
            ]
        )
        if dump.returncode != 0:
            raise RuntimeError(f"pg_dump {source} failed:\n{dump.stderr}")
        _psql_file_stdin(dest, _sanitize_dump(dump.stdout))
        print(f"schema {source} -> {dest}")


def seed_campus_agent() -> None:
    user_rows = []
    people_rows = []
    complaint_users = []
    for person in PEOPLE:
        user_rows.append(
            f"('{person['key']}', '{person['role']}', '{person['name']}', '{person['roll']}')"
        )
        people_rows.append(
            "("
            f"'{person['id']}'::uuid, '{ORG_ID}', '{person['roll']}', "
            f"'{person['role']}', '{person['name']}', '{hash_key(person['key'])}', "
            f"'{person['key']}'"
            ")"
        )
        complaint_users.append(
            "("
            f"'{person['roll']}', '{person['key']}', '{person['role']}', "
            f"'{person['name']}', '{person['roll']}', TRUE, '{person['id']}'::uuid"
            ")"
        )
    _psql(
        "mandi_campus_agent",
        f"""
        INSERT INTO users (authentication_key, role, names, roll_number)
        VALUES {", ".join(user_rows)};
        INSERT INTO people (
            id, org_id, external_id, role, display_name,
            auth_key_hash, authentication_key
        ) VALUES {", ".join(people_rows)};
        """,
    )
    fields = json.dumps(
        [
            {
                "name": "title",
                "type": "string",
                "required": True,
                "description": "book title",
            },
            {
                "name": "author",
                "type": "string",
                "required": True,
                "description": "author name",
            },
            {
                "name": "isbn",
                "type": "string",
                "required": False,
                "description": "ISBN-13",
            },
        ]
    )
    blurb = (
        "library:\n"
        "- Search and add holds for campus library books\n"
        "- Records: title, author, isbn"
    )
    books = [
        (
            str(uuid.uuid4()),
            json.dumps(
                {
                    "title": "Introduction to Algorithms",
                    "author": "Cormen",
                    "isbn": "9780262033848",
                }
            ),
        ),
        (
            str(uuid.uuid4()),
            json.dumps(
                {
                    "title": "Operating Systems",
                    "author": "Galvin",
                    "isbn": "9781118063330",
                }
            ),
        ),
    ]
    asha = PEOPLE[2]["key"]
    _psql(
        "mandi_campus_agent",
        f"""
        INSERT INTO custom_features (
            id, title, description, planner_blurb, keywords, fields, roles,
            enabled, created_by
        ) VALUES (
            'library',
            'Campus Library',
            'Search and add holds for campus library books',
            {psql_literal(blurb)},
            '["library","book","isbn"]'::jsonb,
            {psql_literal(fields)}::jsonb,
            '["student","faculty","admin"]'::jsonb,
            TRUE,
            'mandi-admin'
        );
        INSERT INTO custom_feature_records (id, feature_id, payload, created_by)
        VALUES
            ('{books[0][0]}'::uuid, 'library', {psql_literal(books[0][1])}::jsonb, '{asha}'),
            ('{books[1][0]}'::uuid, 'library', {psql_literal(books[1][1])}::jsonb, '{asha}');
        """,
    )
    _psql(
        "mandi_complaints",
        f"""
        INSERT INTO users (
            id, authentication_key, role, names, roll_number, is_active, person_id
        ) VALUES {", ".join(complaint_users)};
        """,
    )


def psql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def seed_mess() -> None:
    days = (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    )
    weekly = {
        "Monday": (
            "Poha, banana, tea",
            "Rice, dal, mixed veg, roti",
            "Samosa, tea",
            "Roti, dal, paneer, rice",
        ),
        "Tuesday": (
            "Idli, sambar, coffee",
            "Jeera rice, chole, salad",
            "Bhel, lemonade",
            "Roti, palak paneer, rice",
        ),
        "Wednesday": (
            "Paratha, curd, tea",
            "Rice, sambar, cabbage, roti",
            "Pakora, tea",
            "Roti, egg curry, rice",
        ),
        "Thursday": (
            "Upma, fruit, tea",
            "Rice, rajma, beans, roti",
            "Sandwich, juice",
            "Roti, chicken curry, rice",
        ),
        "Friday": (
            "Bread omelette, tea",
            "Fried rice, dal tadka, roti",
            "Vada, coffee",
            "Roti, fish curry, rice",
        ),
        "Saturday": (
            "poha and tea",
            "Rice, kadhi, aloo gobi, roti",
            "Noodles, tea",
            "Roti, mix veg, rice",
        ),
        "Sunday": (
            "Chole bhature, tea",
            "Veg biryani, raita, papad",
            "Cake, coffee",
            "Roti, malai kofta, rice",
        ),
    }
    rows = []
    for hostel in ("Chandra", "Suvalsar"):
        for day in days:
            b, l, s, d = weekly[day]
            if hostel == "Suvalsar" and day == "Saturday":
                b = "Aloo paratha, pickle, tea"
            rows.append(
                f"('{hostel}', '{day}', '{b}', '{l}', '{s}', '{d}')"
            )
    values = ", ".join(rows)
    _psql(
        "mandi_mess_menu",
        f"""
        INSERT INTO temporary (hostel, day, breakfast, lunch, snacks, dinner)
        VALUES {values};
        INSERT INTO permanent (hostel, day, breakfast, lunch, snacks, dinner)
        VALUES {values};
        """,
    )


def seed_bus() -> None:
    days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
    rows = [
        f"('{day}', '08:00', 'Bus 01', 'Chandra', 'academic block', 'Test', '9999999999')"
        for day in days
    ]
    _psql(
        "mandi_bus_schedule",
        f"""
        INSERT INTO bus_schedule
            (day, time, bus_name, start_point, destination, driver_name, driver_no)
        VALUES {", ".join(rows)};
        """,
    )


def seed_notice() -> None:
    _psql(
        "mandi_notice_board",
        """
        INSERT INTO notices (
            content, notice_type, author_id, author_authority,
            target_audience, status
        ) VALUES (
            'Orientation Monday 9am, Auditorium.',
            'General',
            'AD001',
            'admin',
            ARRAY['All'],
            'Active'
        );
        """,
    )


def seed_rooms() -> None:
    _psql(
        "mandi_room_booking",
        """
        INSERT INTO facilities (name, facility_type)
        VALUES
            ('SAC Hall', 'SAC_HALL'),
            ('Guest House', 'GUEST_HOUSE'),
            ('CLH', 'CLH'),
            ('Auditorium', 'AUDITORIUM');

        INSERT INTO rooms (facility_id, room_code, room_type)
        SELECT facility_id, 'SAC-HALL', 'STANDARD'
        FROM facilities WHERE facility_type = 'SAC_HALL';

        INSERT INTO rooms (facility_id, room_code, room_type, price_per_day)
        SELECT facility_id, 'GH-S-' || LPAD(i::TEXT, 2, '0'), 'SINGLE', 1200.00
        FROM facilities, generate_series(1,10) AS i
        WHERE facility_type = 'GUEST_HOUSE';

        INSERT INTO rooms (facility_id, room_code, room_type, price_per_day)
        SELECT facility_id, 'GH-D-' || LPAD(i::TEXT, 2, '0'), 'DOUBLE', 1800.00
        FROM facilities, generate_series(1,10) AS i
        WHERE facility_type = 'GUEST_HOUSE';

        INSERT INTO rooms (facility_id, room_code, room_type)
        SELECT facility_id, 'CLH-' || LPAD(i::TEXT, 2, '0'), 'STANDARD'
        FROM facilities, generate_series(1,6) AS i
        WHERE facility_type = 'CLH';

        INSERT INTO rooms (facility_id, room_code, room_type)
        SELECT facility_id, 'AUDITORIUM', 'STANDARD'
        FROM facilities WHERE facility_type = 'AUDITORIUM';
        """,
    )


def seed_attendance_and_timetable() -> None:
    asha = PEOPLE[2]
    faculty = PEOPLE[1]
    admin = PEOPLE[0]
    _psql(
        "mandi_organization_agent",
        f"""
        INSERT INTO people (roll_num, name, role, person_id) VALUES
            ('{admin["roll"]}', '{admin["name"]}', '{admin["role"]}', '{admin["id"]}'::uuid),
            ('{faculty["roll"]}', '{faculty["name"]}', '{faculty["role"]}', '{faculty["id"]}'::uuid),
            ('{asha["roll"]}', '{asha["name"]}', '{asha["role"]}', '{asha["id"]}'::uuid);
        INSERT INTO courses (
            code, name, professor_name, professor_roll, department,
            min_attendance_percent, planned_sessions
        ) VALUES (
            'CS101', 'Algorithms', '{faculty["name"]}', '{faculty["roll"]}',
            'CSE', 75, 40
        );
        INSERT INTO enrollments (student_roll, student_name, course_code)
        VALUES ('{asha["roll"]}', '{asha["name"]}', 'CS101');
        INSERT INTO attendance (
            student_roll, student_name, course_code, session_date,
            attendance_status, marked_at, marked_by_roll, marked_by_name
        )
        SELECT
            '{asha["roll"]}', '{asha["name"]}', 'CS101',
            (DATE '2026-09-07' + g.n),
            CASE WHEN g.n = 5 THEN 'absent' ELSE 'present' END,
            NOW(),
            '{faculty["roll"]}', '{faculty["name"]}'
        FROM generate_series(0, 11) AS g(n);
        INSERT INTO rooms (room_id, capacity, building)
        VALUES ('CLH-01', 60, 'Academic Block');
        INSERT INTO timetable (
            id, course_code, timetable_day, slot_start, slot_end, room_id
        ) VALUES (
            '{uuid.uuid4()}'::uuid, 'CS101', 'Monday', '09:00', '10:00', 'CLH-01'
        );
        """,
    )
    _psql(
        "mandi_timetable",
        f"""
        INSERT INTO people (roll_num, name, role, student_group, person_id) VALUES
            ('{admin["roll"]}', '{admin["name"]}', '{admin["role"]}', NULL, '{admin["id"]}'::uuid),
            ('{faculty["roll"]}', '{faculty["name"]}', '{faculty["role"]}', NULL, '{faculty["id"]}'::uuid),
            ('{asha["roll"]}', '{asha["name"]}', '{asha["role"]}', 'G1', '{asha["id"]}'::uuid);
        INSERT INTO courses (
            code, name, professor_name, professor_roll, department
        ) VALUES (
            'CS101', 'Algorithms', '{faculty["name"]}', '{faculty["roll"]}', 'CSE'
        );
        INSERT INTO rooms (room_id, capacity, building)
        VALUES ('CLH-01', 60, 'Academic Block');
        INSERT INTO timetable (
            course_code, timetable_day, slot_start, slot_end, room_id,
            class_type, student_group, department
        ) VALUES (
            'CS101', 'Monday', '09:00', '10:00', 'CLH-01',
            'lecture', 'G1', 'CSE'
        );
        """,
    )


def verify() -> None:
    checks = [
        ("mandi_campus_agent", "SELECT COUNT(*) FROM people"),
        ("mandi_mess_menu", "SELECT COUNT(*) FROM temporary WHERE hostel='Chandra'"),
        ("mandi_bus_schedule", "SELECT COUNT(*) FROM bus_schedule"),
        ("mandi_notice_board", "SELECT COUNT(*) FROM notices"),
        ("mandi_campus_agent", "SELECT COUNT(*) FROM custom_feature_records"),
    ]
    for dbname, sql in checks:
        out = _run(
            [
                "psql",
                "-h",
                PGHOST,
                "-p",
                PGPORT,
                "-U",
                PGUSER,
                "-d",
                dbname,
                "-tAc",
                sql,
            ]
        )
        print(f"{dbname}: {sql} -> {out.stdout.strip()}")


def main() -> int:
    recreate_databases()
    copy_schema()
    seed_campus_agent()
    seed_mess()
    seed_bus()
    seed_notice()
    seed_rooms()
    seed_attendance_and_timetable()
    verify()
    print("IIT Mandi demo databases are ready.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
