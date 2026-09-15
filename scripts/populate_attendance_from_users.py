#!/usr/bin/env python3
"""Populate organization_agent courses, people, enrollments, and attendance
from campus_agent.users.

Safe to re-run: inserts use ON CONFLICT DO NOTHING.
Does not touch HXTEST* rows used by attendance tests.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

load_dotenv(os.path.join(_ROOT, ".env"))

from config import AUTH_DB_NAME, ATTENDANCE_DB_NAME, TIMETABLE_DB_NAME  # noqa: E402
from db import get_connection  # noqa: E402

COURSES = [
    # Existing demo courses are listed so a blank restore still gets them.
    ("CS101", "Algorithms", "Priya Patel", "PF001", "CSE", 75, 40),
    ("CS102", "Data Structures", "Arjun Nair", "PF002", "CSE", 75, 40),
    ("MA201", "Linear Algebra", "Meera Joshi", "PF003", "MA", 75, 40),
    ("PHY101", "Physics", "Sameer Khan", "PF004", "PHY", 75, 40),
    ("HS101", "Communication", "Kavita Desai", "PF005", "HS", 75, 40),
    ("MA1101", "Calculus and Linear Algebra", "Aditi Rao", "PF006", "MA", 75, 40),
    ("CS1101", "Foundations of Programming", "Harsh Vardhan", "PF007", "CS", 75, 40),
    ("PH1101", "Engineering Physics", "Leela Menon", "PF008", "PH", 75, 40),
    ("CE1101", "Engineering Graphics", "Omar Qureshi", "PF009", "CE", 75, 40),
    ("CS2101", "Design and Analysis of Algorithms", "Tanvi Shah", "PF010", "CS", 75, 40),
    ("CS2102", "Digital Logic", "Nikhil Rao", "PF011", "CS", 75, 40),
    ("CS2103", "AI Concepts", "Pooja Bhatt", "PF012", "CS", 75, 40),
    ("CB2101", "Process Calculations", "Farhan Ali", "PF013", "CB", 75, 40),
    ("CB2102", "Fluid Mechanics", "Diya Kulkarni", "PF014", "CB", 75, 40),
    ("CB2103", "Chemical Engineering Thermodynamics", "Yash Agarwal", "PF015", "CB", 75, 40),
    ("CB2105", "Mechanical Operations", "Sana Iqbal", "PF016", "CB", 75, 40),
    ("CS103", "Database Systems", "Priya Patel", "PF001", "CS", 75, 40),
    ("CS104", "Operating Systems", "Arjun Nair", "PF002", "CS", 75, 40),
    ("CS105", "Computer Networks", "Tanvi Shah", "PF010", "CS", 75, 40),
    ("CS106", "Machine Learning", "Pooja Bhatt", "PF012", "CS", 75, 40),
    ("CS107", "Discrete Mathematics", "Meera Joshi", "PF003", "CS", 75, 40),
    ("EE1101", "Basic Electrical Engineering", "Sameer Khan", "PF004", "EE", 75, 40),
    ("ME1101", "Engineering Mechanics", "Omar Qureshi", "PF009", "ME", 75, 40),
    ("HS102", "Professional Ethics", "Kavita Desai", "PF005", "HS", 75, 40),
    ("MA1102", "Probability and Statistics", "Aditi Rao", "PF006", "MA", 75, 40),
    ("PH1102", "Modern Physics", "Leela Menon", "PF008", "PH", 75, 40),
    ("CB2104", "Heat Transfer", "Farhan Ali", "PF013", "CB", 75, 40),
    ("AI1101", "Introduction to Artificial Intelligence", "Pooja Bhatt", "PF012", "AI", 75, 40),
    ("CE2101", "Strength of Materials", "Omar Qureshi", "PF009", "CE", 75, 40),
    ("EC1101", "Basic Electronics", "Nikhil Rao", "PF011", "EC", 75, 40),
    ("MM1101", "Materials Science", "Sana Iqbal", "PF016", "MM", 75, 40),
]

COMMON_Y1 = ["MA1101", "CS1101", "PH1101", "CE1101", "EE1101", "HS101"]

Y1_EXTRA = {
    "CS": ["CS102"],
    "AI": ["AI1101", "CS106", "CS107"],
    "ME": ["ME1101"],
    "CE": ["CE2101"],
    "EC": ["EC1101"],
    "MM": ["MM1101"],
    "PH": ["PH1102", "PHY101"],
    "CB": ["MA1102"],
}

Y2_BY_DEPT = {
    "CS": ["CS101", "CS102", "CS103", "CS104", "CS105", "CS2101", "CS2102", "CS2103", "MA201", "HS102"],
    "CB": ["CB2101", "CB2102", "CB2103", "CB2104", "CB2105", "MA201", "PH1101"],
    "AI": ["AI1101", "CS101", "CS106", "CS2103", "MA201", "PHY101", "CS107"],
    "CE": ["CE1101", "CE2101", "ME1101", "MA201", "PHY101", "HS102"],
    "ME": ["ME1101", "CE2101", "MA201", "PHY101", "HS101", "EE1101"],
    "EE": ["EE1101", "EC1101", "MA201", "PHY101", "HS102"],
    "EC": ["EC1101", "EE1101", "CS1101", "MA201", "PHY101"],
    "PH": ["PHY101", "PH1101", "PH1102", "MA201", "MA1102"],
    "MM": ["MM1101", "ME1101", "PH1101", "MA201", "HS102"],
}
DEFAULT_Y2 = ["MA201", "PHY101", "HS101", "HS102", "EE1101", "ME1101"]

SESSION_DATES = [
    date(2026, 8, 17),
    date(2026, 8, 19),
    date(2026, 8, 21),
    date(2026, 8, 24),
    date(2026, 8, 26),
    date(2026, 8, 28),
    date(2026, 8, 31),
    date(2026, 9, 2),
    date(2026, 9, 4),
    date(2026, 9, 8),
    date(2026, 9, 10),
    date(2026, 9, 12),
]

_ROLL_RE = re.compile(r"^(\d{2})(\d{2})([A-Z]{2})(\d+)$")


def _parse_roll(roll: str) -> tuple[int, str]:
    match = _ROLL_RE.match(str(roll).strip().upper())
    if not match:
        return 0, ""
    admission_year = int(match.group(1))
    academic_year = 26 - admission_year + 1
    return academic_year, match.group(3)


def _courses_for(roll: str) -> list[str]:
    year, dept = _parse_roll(roll)
    if year <= 1:
        codes = list(COMMON_Y1)
        codes.extend(Y1_EXTRA.get(dept, []))
        return list(dict.fromkeys(codes))
    return list(dict.fromkeys(Y2_BY_DEPT.get(dept, DEFAULT_Y2)))


def _status(roll: str, code: str, day: date) -> str:
    digest = hashlib.md5(f"{roll}|{code}|{day.isoformat()}".encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100
    if bucket < 78:
        return "present"
    if bucket < 90:
        return "absent"
    if bucket < 97:
        return "late"
    return "excused"


def _batch(cur, sql: str, rows: list[tuple], size: int = 1000) -> int:
    if not rows:
        return 0
    for i in range(0, len(rows), size):
        cur.executemany(sql, rows[i : i + size])
    return len(rows)


def main() -> None:
    auth = get_connection(AUTH_DB_NAME)
    att = get_connection(ATTENDANCE_DB_NAME)
    try:
        auth_cur = auth.cursor()
        att_cur = att.cursor()

        auth_cur.execute(
            """
            SELECT roll_number, names, LOWER(role)
            FROM users
            WHERE roll_number IS NOT NULL
              AND names IS NOT NULL
              AND LOWER(role) IN ('student', 'faculty', 'admin')
            ORDER BY roll_number
            """
        )
        users = [
            (str(roll).strip(), name.strip(), role)
            for roll, name, role in auth_cur.fetchall()
            if roll and name and not str(roll).upper().startswith("HXTEST")
        ]
        students = [(r, n) for r, n, role in users if role == "student"]

        _batch(
            att_cur,
            """
            INSERT INTO people (roll_num, name, role)
            VALUES (%s, %s, %s)
            ON CONFLICT (roll_num) DO UPDATE
            SET name = EXCLUDED.name,
                role = EXCLUDED.role
            """,
            users,
        )

        _batch(
            att_cur,
            """
            INSERT INTO courses (
                code, name, professor_name, professor_roll,
                department, min_attendance_percent, planned_sessions
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            """,
            COURSES,
        )

        att_cur.execute(
            "SELECT code, professor_roll, professor_name FROM courses"
        )
        course_meta = {row[0]: (row[1], row[2]) for row in att_cur.fetchall()}

        enroll_rows = []
        for roll, name in students:
            for code in _courses_for(roll):
                if code in course_meta:
                    enroll_rows.append((roll, name, code))

        _batch(
            att_cur,
            """
            INSERT INTO enrollments (student_roll, student_name, course_code)
            VALUES (%s, %s, %s)
            ON CONFLICT (student_roll, course_code) DO NOTHING
            """,
            enroll_rows,
        )

        attendance_rows = []
        for roll, name, code in enroll_rows:
            prof_roll, prof_name = course_meta[code]
            for day in SESSION_DATES:
                marked_at = datetime(
                    day.year, day.month, day.day, 10, 5, tzinfo=timezone.utc
                ) + timedelta(minutes=hash(code) % 40)
                attendance_rows.append(
                    (
                        roll,
                        name,
                        code,
                        day,
                        _status(roll, code, day),
                        marked_at,
                        prof_roll,
                        prof_name,
                    )
                )

        _batch(
            att_cur,
            """
            INSERT INTO attendance (
                student_roll, student_name, course_code, session_date,
                attendance_status, marked_at, marked_by_roll, marked_by_name
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (student_roll, course_code, session_date) DO NOTHING
            """,
            attendance_rows,
            size=2000,
        )

        att.commit()

        att_cur.execute("SELECT COUNT(*) FROM courses")
        n_courses = att_cur.fetchone()[0]
        att_cur.execute("SELECT COUNT(*) FROM people WHERE role = 'student'")
        n_people = att_cur.fetchone()[0]
        att_cur.execute("SELECT COUNT(*) FROM enrollments")
        n_enroll = att_cur.fetchone()[0]
        att_cur.execute("SELECT COUNT(*) FROM attendance")
        n_att = att_cur.fetchone()[0]
        print(
            f"organization_agent: courses={n_courses} students={n_people} "
            f"enrollments={n_enroll} attendance={n_att}"
        )
    finally:
        auth.close()
        att.close()

    timetable = get_connection(TIMETABLE_DB_NAME)
    try:
        cur = timetable.cursor()
        _batch(
            cur,
            """
            INSERT INTO courses (
                code, name, professor_name, professor_roll,
                department, min_attendance_percent, planned_sessions
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            """,
            COURSES,
        )
        timetable.commit()
        cur.execute("SELECT COUNT(*) FROM courses")
        print(f"timetable: courses={cur.fetchone()[0]}")
    finally:
        timetable.close()


if __name__ == "__main__":
    main()
