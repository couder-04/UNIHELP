"""Fixtures for roll_num people schema."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import attendance_functions as T  # noqa: E402

PREFIX = "HXTEST"
COURSE_A = f"{PREFIX}101"
COURSE_B = f"{PREFIX}202"
COURSE_OTHER = f"{PREFIX}999"
STUDENT_A = f"{PREFIX}-S-A"
STUDENT_B = f"{PREFIX}-S-B"
STUDENT_C = f"{PREFIX}-S-C"
PROF_OWNER = f"{PREFIX}-E-OWN"
PROF_OTHER = f"{PREFIX}-E-OTH"
ADMIN = f"{PREFIX}-A-1"


def _conn():
    return T.get_connection()


def _cleanup(cur):
    cur.execute("DELETE FROM attendance WHERE course_code LIKE %s", (f"{PREFIX}%",))
    cur.execute("DELETE FROM enrollments WHERE course_code LIKE %s", (f"{PREFIX}%",))
    cur.execute("DELETE FROM courses WHERE code LIKE %s", (f"{PREFIX}%",))
    cur.execute("DELETE FROM people WHERE roll_num LIKE %s", (f"{PREFIX}%",))


@pytest.fixture(scope="session")
def campus():
    conn = _conn()
    cur = conn.cursor()
    _cleanup(cur)
    conn.commit()

    people = [
        (STUDENT_A, "HX Student A", "student"),
        (STUDENT_B, "HX Student B", "student"),
        (STUDENT_C, "HX Student C", "student"),
        (PROF_OWNER, "HX Owner", "faculty"),
        (PROF_OTHER, "HX Other", "faculty"),
        (ADMIN, "HX Admin", "admin"),
    ]
    for roll, name, role in people:
        cur.execute(
            "INSERT INTO people (roll_num, name, role) VALUES (%s,%s,%s)",
            (roll, name, role),
        )

    courses = [
        (COURSE_A, "HX Algorithms", "HX Owner", PROF_OWNER),
        (COURSE_B, "HX Databases", "HX Owner", PROF_OWNER),
        (COURSE_OTHER, "HX Circuits", "HX Other", PROF_OTHER),
    ]
    for code, name, pname, proll in courses:
        cur.execute(
            """
            INSERT INTO courses (
                code, name, professor_name, professor_roll,
                department, min_attendance_percent, planned_sessions
            ) VALUES (%s,%s,%s,%s,'CSE',75,10)
            """,
            (code, name, pname, proll),
        )

    for student, course in [
        (STUDENT_A, COURSE_A),
        (STUDENT_B, COURSE_A),
        (STUDENT_A, COURSE_B),
        (STUDENT_B, COURSE_OTHER),
    ]:
        cur.execute(
            "INSERT INTO enrollments (student_roll, course_code) VALUES (%s,%s)",
            (student, course),
        )

    base = date.today() - timedelta(days=21)
    sessions = [base + timedelta(days=d) for d in (0, 2, 4, 7, 9, 11)]
    pattern_a = ["present", "present", "absent", "absent", "absent", "present"]
    pattern_b = ["present", "present", "present", "present", "present", "absent"]
    for day, sa, sb in zip(sessions, pattern_a, pattern_b):
        for roll, status in ((STUDENT_A, sa), (STUDENT_B, sb)):
            cur.execute(
                """
                INSERT INTO attendance (
                    student_roll, course_code, session_date,
                    attendance_status, marked_at, marked_by_roll
                ) VALUES (%s,%s,%s,%s,NOW(),%s)
                """,
                (roll, COURSE_A, day, status, PROF_OWNER),
            )

    cur.execute(
        """
        INSERT INTO attendance (
            student_roll, course_code, session_date,
            attendance_status, marked_at, marked_by_roll
        ) VALUES (%s,%s,%s,'late',NOW(),%s)
        """,
        (STUDENT_A, COURSE_B, sessions[0], PROF_OWNER),
    )

    conn.commit()
    cur.close()
    conn.close()

    data = {
        "course_a": COURSE_A,
        "course_b": COURSE_B,
        "course_other": COURSE_OTHER,
        "course_a_id": COURSE_A,
        "student_a": STUDENT_A,
        "student_b": STUDENT_B,
        "student_c": STUDENT_C,
        "prof_owner": PROF_OWNER,
        "prof_other": PROF_OTHER,
        "admin": ADMIN,
        "sessions": [str(d) for d in sessions],
        "write_date": str(date.today() + timedelta(days=3)),
    }
    yield data

    conn = _conn()
    cur = conn.cursor()
    _cleanup(cur)
    conn.commit()
    cur.close()
    conn.close()
