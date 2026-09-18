"""Attendance tools — roll_num roster schema.

# SUPERSEDED as an identity store by campus_agent.people. person_id on
# this people table links the roster row to the canonical person.
# roll_num remains the PK this release because attendance/enrollments
# still FK to it. Do not drop roll_num/name/role until those FKs are
# confirmed in production for a full cycle.

Tables:
  people(roll_num, name, role, person_id)  # student | faculty | admin
  courses(code, name, professor_name, professor_roll, ...)
  enrollments(student_roll, course_code)
  attendance(student_roll, course_code, session_date, status, marked_by_roll, ...)
"""

from __future__ import annotations

import csv
import io
import math
from datetime import date, datetime, timedelta

import db
from config import ATTENDANCE_DB_NAME

VALID_STATUSES = frozenset({"present", "absent", "late", "excused"})


def get_connection():
    """Pooled connection when psycopg_pool is installed (see db.py); env
    overrides for host/port/user/password are handled there too."""
    return db.get_connection(ATTENDANCE_DB_NAME)


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        return date.fromisoformat(value.strip()[:10])
    return None


def _norm_status(value, default="present"):
    raw = (value or default).strip().lower()
    if raw in {"absent", "a", "no", "missed"}:
        return "absent"
    if raw in {"present", "p", "yes", "attended"}:
        return "present"
    if raw in {"late", "l", "tardy"}:
        return "late"
    if raw in {"excused", "e", "medical", "leave"}:
        return "excused"
    return None


def _counts_as_present(status):
    return status in {"present", "late", "excused"}


def _roll(value):
    if value is None:
        return None
    return str(value).strip()


def _resolve_person(cursor, roll_num, roles=None):
    roll = _roll(roll_num)
    if not roll:
        return None
    if roles:
        cursor.execute(
            """
            SELECT roll_num, name, role
            FROM people
            WHERE LOWER(roll_num) = LOWER(%s)
              AND role = ANY(%s)
            """,
            (roll, list(roles)),
        )
    else:
        cursor.execute(
            """
            SELECT roll_num, name, role
            FROM people
            WHERE LOWER(roll_num) = LOWER(%s)
            """,
            (roll,),
        )
    return cursor.fetchone()


def _resolve_course(cursor, course_code=None, course_id=None):
    """Resolve by course code (preferred). course_id accepted as alias for code."""
    key = course_code or course_id
    if key is None:
        return None
    cursor.execute(
        """
        SELECT code, name, professor_name, professor_roll,
               department, min_attendance_percent, planned_sessions
        FROM courses
        WHERE LOWER(REPLACE(code, ' ', '')) = LOWER(REPLACE(%s, ' ', ''))
        """,
        (str(key),),
    )
    return cursor.fetchone()


def _assert_owns_course(course_row, professor_roll):
    if course_row is None or professor_roll is None:
        return False
    return str(course_row[3]).lower() == str(professor_roll).strip().lower()


def _upsert_one(cursor, course_code, student_roll, session_date, status, marked_by_roll):
    student = _resolve_person(cursor, student_roll)
    marker = _resolve_person(cursor, marked_by_roll)
    student_name = student[1] if student else None
    marked_by_name = marker[1] if marker else None
    cursor.execute(
        """
        INSERT INTO attendance (
            student_roll, student_name, course_code, session_date,
            attendance_status, marked_at, marked_by_roll, marked_by_name
        )
        VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s)
        ON CONFLICT (student_roll, course_code, session_date)
        DO UPDATE SET
            attendance_status = EXCLUDED.attendance_status,
            marked_at = EXCLUDED.marked_at,
            marked_by_roll = EXCLUDED.marked_by_roll,
            student_name = EXCLUDED.student_name,
            marked_by_name = EXCLUDED.marked_by_name
        RETURNING attendance_status, session_date
        """,
        (
            student_roll, student_name, course_code, session_date,
            status, marked_by_roll, marked_by_name,
        ),
    )
    return cursor.fetchone()


def _percent(present, total):
    if total <= 0:
        return None
    return round(100.0 * present / total, 2)


def skip_budget(present, total, planned, threshold_percent):
    threshold = max(0.0, min(100.0, float(threshold_percent))) / 100.0
    remaining = max(int(planned) - int(total), 0)
    denom = total + remaining
    current = _percent(present, total)
    if denom <= 0:
        return {
            "attendance_percent": current,
            "present_count": present,
            "absent_count": max(total - present, 0),
            "total_sessions": total,
            "remaining_sessions": 0,
            "threshold_percent": threshold_percent,
            "skip_budget": 0,
            "must_attend": 0,
            "can_skip": 0,
            "below_threshold": False,
        }
    need = math.ceil(threshold * denom - 1e-9)
    can_skip = max(0, present + remaining - need)
    can_skip = min(can_skip, remaining)
    must_attend = remaining - can_skip
    projected = _percent(present + (remaining - can_skip), denom)
    return {
        "attendance_percent": current,
        "present_count": present,
        "absent_count": max(total - present, 0),
        "total_sessions": total,
        "remaining_sessions": remaining,
        "planned_sessions": planned,
        "threshold_percent": threshold_percent,
        "skip_budget": can_skip,
        "must_attend": must_attend,
        "can_skip": can_skip,
        "below_threshold": current is not None and current < threshold_percent,
        "projected_percent_if_skip_budget": projected,
    }


# student_id / professor_id args are roll numbers (kept for tool-schema continuity)


def get_attendance(student_id, course_code, session_date=None, date_from=None, date_to=None):
    student_roll = _roll(student_id)
    connection = get_connection()
    cursor = connection.cursor()

    if session_date is not None:
        session_date = _as_date(session_date)
        cursor.execute(
            """
            SELECT a.session_date, a.attendance_status, c.code, c.name, p.name
            FROM attendance a
            JOIN courses c ON c.code = a.course_code
            JOIN people p ON p.roll_num = a.student_roll
            WHERE LOWER(a.student_roll) = LOWER(%s)
              AND LOWER(REPLACE(c.code, ' ', '')) = LOWER(REPLACE(%s, ' ', ''))
              AND a.session_date = %s
            """,
            (student_roll, course_code, session_date),
        )
        row = cursor.fetchone()
        cursor.close()
        connection.close()
        if row is None:
            return {
                "status": "not_found",
                "message": (
                    f"No attendance found for {student_roll} "
                    f"in {course_code} on {session_date}."
                ),
            }
        return {
            "status": "success",
            "student_roll": student_roll,
            "student_name": row[4],
            "course_code": row[2],
            "course_name": row[3],
            "session_date": str(row[0]),
            "attendance_status": row[1],
        }

    date_from = _as_date(date_from)
    date_to = _as_date(date_to)
    clauses = [
        "LOWER(a.student_roll) = LOWER(%s)",
        "LOWER(REPLACE(c.code, ' ', '')) = LOWER(REPLACE(%s, ' ', ''))",
    ]
    params: list = [student_roll, course_code]
    if date_from is not None:
        clauses.append("a.session_date >= %s")
        params.append(date_from)
    if date_to is not None:
        clauses.append("a.session_date <= %s")
        params.append(date_to)

    cursor.execute(
        f"""
        SELECT a.session_date, a.attendance_status, c.code, c.name
        FROM attendance a
        JOIN courses c ON c.code = a.course_code
        WHERE {' AND '.join(clauses)}
        ORDER BY a.session_date
        """,
        params,
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    if not rows:
        return {
            "status": "not_found",
            "message": f"No attendance found for {student_roll} in {course_code}.",
        }
    return {
        "status": "success",
        "student_roll": student_roll,
        "course_code": course_code,
        "date_from": str(date_from) if date_from else None,
        "date_to": str(date_to) if date_to else None,
        "records": [
            {
                "session_date": str(r[0]),
                "attendance_status": r[1],
                "course_code": r[2],
                "course_name": r[3],
            }
            for r in rows
        ],
    }


def get_weekly_attendance(student_id, week_start=None):
    student_roll = _roll(student_id)
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
    else:
        week_start = _as_date(week_start)
    week_end = week_start + timedelta(days=6)

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT a.session_date, c.code, c.name, a.attendance_status
        FROM attendance a
        JOIN courses c ON c.code = a.course_code
        WHERE LOWER(a.student_roll) = LOWER(%s)
          AND a.session_date BETWEEN %s AND %s
        ORDER BY a.session_date, c.code
        """,
        (student_roll, week_start, week_end),
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    if not rows:
        return {
            "status": "not_found",
            "message": f"No attendance found for {student_roll} this week.",
        }
    return {
        "status": "success",
        "student_roll": student_roll,
        "week_start": str(week_start),
        "week_end": str(week_end),
        "records": [
            {
                "session_date": str(r[0]),
                "course_code": r[1],
                "course_name": r[2],
                "attendance_status": r[3],
            }
            for r in rows
        ],
    }


def get_attendance_summary(student_id, course_code=None):
    student_roll = _roll(student_id)
    connection = get_connection()
    cursor = connection.cursor()

    if course_code:
        cursor.execute(
            """
            SELECT c.code, c.name, c.min_attendance_percent, c.planned_sessions,
                   COUNT(a.session_date) AS total_sessions,
                   COUNT(a.session_date) FILTER (
                       WHERE LOWER(a.attendance_status) IN ('present','late','excused')
                   ) AS present_count
            FROM courses c
            JOIN enrollments e ON e.course_code = c.code
            LEFT JOIN attendance a
                ON a.course_code = c.code AND LOWER(a.student_roll) = LOWER(e.student_roll)
            WHERE LOWER(e.student_roll) = LOWER(%s)
              AND LOWER(REPLACE(c.code, ' ', '')) = LOWER(REPLACE(%s, ' ', ''))
            GROUP BY c.code, c.name, c.min_attendance_percent, c.planned_sessions
            """,
            (student_roll, course_code),
        )
    else:
        cursor.execute(
            """
            SELECT c.code, c.name, c.min_attendance_percent, c.planned_sessions,
                   COUNT(a.session_date) AS total_sessions,
                   COUNT(a.session_date) FILTER (
                       WHERE LOWER(a.attendance_status) IN ('present','late','excused')
                   ) AS present_count
            FROM courses c
            JOIN enrollments e ON e.course_code = c.code
            LEFT JOIN attendance a
                ON a.course_code = c.code AND LOWER(a.student_roll) = LOWER(e.student_roll)
            WHERE LOWER(e.student_roll) = LOWER(%s)
            GROUP BY c.code, c.name, c.min_attendance_percent, c.planned_sessions
            ORDER BY c.code
            """,
            (student_roll,),
        )

    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    if not rows:
        return {
            "status": "not_found",
            "message": f"No courses/attendance found for {student_roll}.",
        }

    summaries = []
    for code, name, threshold, planned, total, present in rows:
        budget = skip_budget(present or 0, total or 0, planned or 40, threshold or 75)
        summaries.append({"course_code": code, "course_name": name, **budget})
    return {"status": "success", "student_roll": student_roll, "summaries": summaries}


def get_skip_budget(student_id, course_code):
    result = get_attendance_summary(student_id, course_code)
    if result["status"] != "success":
        return result
    summary = result["summaries"][0]
    return {"status": "success", "student_roll": _roll(student_id), **summary}


def get_course_attendance(course_code, session_date=None):
    connection = get_connection()
    cursor = connection.cursor()
    course = _resolve_course(cursor, course_code=course_code)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Course not found: {course_code}."}

    code, name = course[0], course[1]

    if session_date is not None:
        session_date = _as_date(session_date)
        cursor.execute(
            """
            SELECT e.student_roll, p.name, a.attendance_status
            FROM enrollments e
            JOIN people p ON p.roll_num = e.student_roll
            LEFT JOIN attendance a
                ON LOWER(a.student_roll) = LOWER(e.student_roll)
               AND a.course_code = e.course_code
               AND a.session_date = %s
            WHERE e.course_code = %s
            ORDER BY e.student_roll
            """,
            (session_date, code),
        )
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        if not rows:
            return {"status": "not_found", "message": f"No enrolled students for {code}."}
        present_count = sum(
            1 for r in rows if r[2] and r[2].lower() in {"present", "late", "excused"}
        )
        absent_count = sum(1 for r in rows if r[2] and r[2].lower() == "absent")
        unmarked_count = sum(1 for r in rows if r[2] is None)
        return {
            "status": "success",
            "course_code": code,
            "course_name": name,
            "session_date": str(session_date),
            "present_count": present_count,
            "absent_count": absent_count,
            "unmarked_count": unmarked_count,
            "roster": [
                {
                    "student_roll": r[0],
                    "student_name": r[1],
                    "attendance_status": r[2] or "unmarked",
                }
                for r in rows
            ],
        }

    cursor.execute(
        """
        SELECT a.student_roll, p.name, a.session_date, a.attendance_status
        FROM attendance a
        JOIN people p ON p.roll_num = a.student_roll
        WHERE a.course_code = %s
        ORDER BY a.session_date, a.student_roll
        """,
        (code,),
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    if not rows:
        return {"status": "not_found", "message": f"No attendance records for {code}."}
    return {
        "status": "success",
        "course_code": code,
        "course_name": name,
        "records": [
            {
                "student_roll": r[0],
                "student_name": r[1],
                "session_date": str(r[2]),
                "attendance_status": r[3],
            }
            for r in rows
        ],
    }


def get_course_attendance_summary(course_code):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT c.code, c.name, c.min_attendance_percent, c.planned_sessions,
               e.student_roll, p.name,
               COUNT(a.session_date) AS total_sessions,
               COUNT(a.session_date) FILTER (
                   WHERE LOWER(a.attendance_status) IN ('present','late','excused')
               ) AS present_count
        FROM courses c
        JOIN enrollments e ON e.course_code = c.code
        JOIN people p ON p.roll_num = e.student_roll
        LEFT JOIN attendance a
            ON a.course_code = c.code AND LOWER(a.student_roll) = LOWER(e.student_roll)
        WHERE LOWER(REPLACE(c.code, ' ', '')) = LOWER(REPLACE(%s, ' ', ''))
        GROUP BY c.code, c.name, c.min_attendance_percent, c.planned_sessions,
                 e.student_roll, p.name
        ORDER BY e.student_roll
        """,
        (course_code,),
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    if not rows:
        return {"status": "not_found", "message": f"No enrolled students for {course_code}."}

    code, name, threshold, planned = rows[0][0], rows[0][1], rows[0][2] or 75, rows[0][3] or 40
    students = []
    at_risk = []
    for row in rows:
        student_roll, student_name, total, present = row[4], row[5], row[6] or 0, row[7] or 0
        budget = skip_budget(present, total, planned, threshold)
        entry = {"student_roll": student_roll, "student_name": student_name, **budget}
        students.append(entry)
        if budget["below_threshold"]:
            at_risk.append(student_roll)
    return {
        "status": "success",
        "course_code": code,
        "course_name": name,
        "threshold_percent": threshold,
        "planned_sessions": planned,
        "enrolled_count": len(students),
        "at_risk_count": len(at_risk),
        "at_risk_students": at_risk,
        "students": students,
    }


def mark_attendance(
    student_id,
    course_code,
    session_date,
    attendance_status,
    professor_id,
    course_id=None,
):
    connection = get_connection()
    cursor = connection.cursor()

    professor = _resolve_person(cursor, professor_id, roles=["faculty", "admin"])
    if professor is None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": "Only faculty/admin can mark attendance."}

    status = _norm_status(attendance_status)
    if status is None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": f"Invalid attendance status: {attendance_status}."}

    session_date = _as_date(session_date)
    if session_date is None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": "session_date is required (YYYY-MM-DD)."}

    course = _resolve_course(cursor, course_code=course_code, course_id=course_id)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Course not found: {course_id or course_code}."}

    # Faculty must own the course; admin may mark any course
    if professor[2] == "faculty" and not _assert_owns_course(course, professor[0]):
        cursor.close()
        connection.close()
        return {"status": "error", "message": "Professor does not own this course."}

    student = _resolve_person(cursor, student_id, roles=["student"])
    if student is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Student not found: {student_id}."}

    cursor.execute(
        """
        SELECT 1 FROM enrollments
        WHERE LOWER(student_roll) = LOWER(%s) AND course_code = %s
        """,
        (student[0], course[0]),
    )
    if cursor.fetchone() is None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": f"{student[0]} is not enrolled in {course[0]}."}

    row = _upsert_one(cursor, course[0], student[0], session_date, status, professor[0])
    connection.commit()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "message": "Attendance marked.",
        "student_roll": student[0],
        "student_name": student[1],
        "course_code": course[0],
        "course_name": course[1],
        "session_date": str(row[1]),
        "attendance_status": row[0],
        "marked_by_roll": professor[0],
        "marked_by_name": professor[1],
    }


def mark_students_attendance(
    student_ids,
    session_date,
    course_id,
    professor_id,
    attendance_status="present",
    status_by_student=None,
    course_code=None,
):
    connection = get_connection()
    cursor = connection.cursor()

    professor = _resolve_person(cursor, professor_id, roles=["faculty", "admin"])
    if professor is None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": "Only faculty/admin can mark attendance."}

    session_date = _as_date(session_date)
    if session_date is None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": "session_date is required (YYYY-MM-DD)."}

    if not student_ids:
        cursor.close()
        connection.close()
        return {"status": "error", "message": "student_ids must be a non-empty list."}

    course = _resolve_course(cursor, course_code=course_code or course_id, course_id=course_id)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Course not found: {course_id}."}

    if professor[2] == "faculty" and not _assert_owns_course(course, professor[0]):
        cursor.close()
        connection.close()
        return {"status": "error", "message": "Professor does not own this course."}

    default_status = _norm_status(attendance_status)
    if default_status is None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": f"Invalid attendance status: {attendance_status}."}

    overrides = {}
    for key, value in (status_by_student or {}).items():
        normalized = _norm_status(value)
        if normalized is None:
            cursor.close()
            connection.close()
            return {"status": "error", "message": f"Invalid status for {key}: {value}."}
        overrides[str(key).strip().lower()] = normalized

    marked, skipped = [], []
    for raw_id in student_ids:
        student = _resolve_person(cursor, raw_id, roles=["student"])
        if student is None:
            skipped.append({"student_roll": _roll(raw_id), "reason": "not_found"})
            continue
        cursor.execute(
            """
            SELECT 1 FROM enrollments
            WHERE LOWER(student_roll) = LOWER(%s) AND course_code = %s
            """,
            (student[0], course[0]),
        )
        if cursor.fetchone() is None:
            skipped.append({"student_roll": student[0], "reason": "not_enrolled"})
            continue
        status = overrides.get(student[0].lower(), default_status)
        row = _upsert_one(cursor, course[0], student[0], session_date, status, professor[0])
        marked.append(
            {
                "student_roll": student[0],
                "student_name": student[1],
                "session_date": str(row[1]),
                "attendance_status": row[0],
            }
        )

    connection.commit()
    cursor.close()
    connection.close()
    present_n = sum(1 for m in marked if _counts_as_present(m["attendance_status"]))
    absent_n = sum(1 for m in marked if m["attendance_status"] == "absent")
    return {
        "status": "success",
        "message": "Attendance marked for student set.",
        "course_code": course[0],
        "course_name": course[1],
        "session_date": str(session_date),
        "marked_by_roll": professor[0],
        "marked_count": len(marked),
        "skipped_count": len(skipped),
        "present_count": present_n,
        "absent_count": absent_n,
        "marked": marked,
        "skipped": skipped,
    }


def mark_class_attendance(
    course_id,
    session_date,
    professor_id,
    default_status="present",
    present_numbers=None,
    absent_numbers=None,
    course_code=None,
):
    connection = get_connection()
    cursor = connection.cursor()

    professor = _resolve_person(cursor, professor_id, roles=["faculty", "admin"])
    if professor is None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": "Only faculty/admin can mark attendance."}

    session_date = _as_date(session_date)
    if session_date is None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": "session_date is required (YYYY-MM-DD)."}

    course = _resolve_course(cursor, course_code=course_code or course_id, course_id=course_id)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Course not found: {course_id or course_code}."}

    if professor[2] == "faculty" and not _assert_owns_course(course, professor[0]):
        cursor.close()
        connection.close()
        return {"status": "error", "message": "Professor does not own this course."}

    default = _norm_status(default_status)
    if default is None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": f"Invalid default_status: {default_status}."}

    cursor.execute(
        """
        SELECT e.student_roll, p.name
        FROM enrollments e
        JOIN people p ON p.roll_num = e.student_roll
        WHERE e.course_code = %s
        ORDER BY e.student_roll
        """,
        (course[0],),
    )
    roster = cursor.fetchall()
    if not roster:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"No enrolled students for {course[0]}."}

    present_set = {str(x).strip().lower() for x in (present_numbers or [])}
    absent_set = {str(x).strip().lower() for x in (absent_numbers or [])}

    marked = []
    for student_roll, student_name in roster:
        key = student_roll.lower()
        if key in absent_set:
            status = "absent"
        elif key in present_set:
            status = "present"
        else:
            status = default
        row = _upsert_one(cursor, course[0], student_roll, session_date, status, professor[0])
        marked.append(
            {
                "student_roll": student_roll,
                "student_name": student_name,
                "session_date": str(row[1]),
                "attendance_status": row[0],
            }
        )

    connection.commit()
    cursor.close()
    connection.close()
    present_n = sum(1 for m in marked if _counts_as_present(m["attendance_status"]))
    return {
        "status": "success",
        "message": "Class attendance marked.",
        "course_code": course[0],
        "course_name": course[1],
        "session_date": str(session_date),
        "marked_by_roll": professor[0],
        "marked_count": len(marked),
        "present_count": present_n,
        "absent_count": len(marked) - present_n,
        "marked": marked,
    }


def edit_attendance(
    student_id,
    course_id,
    session_date,
    attendance_status,
    professor_id,
    course_code=None,
):
    return mark_attendance(
        student_id=student_id,
        course_code=course_code,
        session_date=session_date,
        attendance_status=attendance_status,
        professor_id=professor_id,
        course_id=course_id,
    )


def delete_attendance(student_id, course_id, session_date, professor_id, course_code=None):
    connection = get_connection()
    cursor = connection.cursor()

    professor = _resolve_person(cursor, professor_id, roles=["faculty", "admin"])
    if professor is None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": "Only faculty/admin can delete attendance."}

    session_date = _as_date(session_date)
    course = _resolve_course(cursor, course_code=course_code or course_id, course_id=course_id)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Course not found: {course_id or course_code}."}

    if professor[2] == "faculty" and not _assert_owns_course(course, professor[0]):
        cursor.close()
        connection.close()
        return {"status": "error", "message": "Professor does not own this course."}

    cursor.execute(
        """
        DELETE FROM attendance
        WHERE LOWER(student_roll) = LOWER(%s)
          AND course_code = %s
          AND session_date = %s
        RETURNING student_roll
        """,
        (_roll(student_id), course[0], session_date),
    )
    deleted = cursor.fetchone()
    if deleted is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": "Attendance record not found."}

    connection.commit()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "message": "Attendance deleted.",
        "student_roll": deleted[0],
        "course_code": course[0],
        "session_date": str(session_date),
        "deleted_by_roll": professor[0],
    }


def get_monthly_attendance(student_id, year, month, course_code=None):
    start = date(int(year), int(month), 1)
    if month == 12:
        end = date(int(year) + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(int(year), int(month) + 1, 1) - timedelta(days=1)

    if course_code:
        result = get_attendance(student_id, course_code, date_from=start, date_to=end)
    else:
        student_roll = _roll(student_id)
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT a.session_date, c.code, c.name, a.attendance_status
            FROM attendance a
            JOIN courses c ON c.code = a.course_code
            WHERE LOWER(a.student_roll) = LOWER(%s)
              AND a.session_date BETWEEN %s AND %s
            ORDER BY a.session_date, c.code
            """,
            (student_roll, start, end),
        )
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        if not rows:
            return {
                "status": "not_found",
                "message": f"No attendance for {student_roll} in {year}-{int(month):02d}.",
            }
        result = {
            "status": "success",
            "student_roll": student_roll,
            "records": [
                {
                    "session_date": str(r[0]),
                    "course_code": r[1],
                    "course_name": r[2],
                    "attendance_status": r[3],
                }
                for r in rows
            ],
        }

    if result.get("status") != "success":
        return result
    result["view"] = "monthly"
    result["year"] = int(year)
    result["month"] = int(month)
    result["date_from"] = str(start)
    result["date_to"] = str(end)
    return result


def get_semester_attendance(student_id, date_from, date_to, course_code=None):
    date_from = _as_date(date_from)
    date_to = _as_date(date_to)
    if date_from is None or date_to is None:
        return {"status": "error", "message": "date_from and date_to are required."}

    if course_code:
        result = get_attendance(student_id, course_code, date_from=date_from, date_to=date_to)
    else:
        summary = get_attendance_summary(student_id)
        if summary["status"] != "success":
            return summary
        student_roll = _roll(student_id)
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT a.session_date, c.code, c.name, a.attendance_status
            FROM attendance a
            JOIN courses c ON c.code = a.course_code
            WHERE LOWER(a.student_roll) = LOWER(%s)
              AND a.session_date BETWEEN %s AND %s
            ORDER BY a.session_date, c.code
            """,
            (student_roll, date_from, date_to),
        )
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        result = {
            "status": "success",
            "student_roll": student_roll,
            "summaries": summary["summaries"],
            "records": [
                {
                    "session_date": str(r[0]),
                    "course_code": r[1],
                    "course_name": r[2],
                    "attendance_status": r[3],
                }
                for r in rows
            ],
        }

    if result.get("status") != "success":
        return result
    result["view"] = "semester"
    result["date_from"] = str(date_from)
    result["date_to"] = str(date_to)
    return result


def get_at_risk_students(course_id=None, course_code=None, professor_id=None):
    connection = get_connection()
    cursor = connection.cursor()

    professor_roll = None
    if professor_id is not None:
        professor = _resolve_person(cursor, professor_id, roles=["faculty", "admin"])
        if professor is None:
            cursor.close()
            connection.close()
            return {"status": "error", "message": "Person not found."}
        professor_roll = professor[0]

    course = None
    if course_id is not None or course_code is not None:
        course = _resolve_course(cursor, course_id=course_id, course_code=course_code)
        if course is None:
            cursor.close()
            connection.close()
            return {"status": "not_found", "message": "Course not found."}

    clauses = []
    params: list = []
    if course is not None:
        clauses.append("c.code = %s")
        params.append(course[0])
    if professor_roll is not None:
        clauses.append("LOWER(c.professor_roll) = LOWER(%s)")
        params.append(professor_roll)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    cursor.execute(
        f"""
        SELECT c.code, c.name, c.min_attendance_percent, c.planned_sessions,
               e.student_roll, p.name,
               COUNT(a.session_date) AS total_sessions,
               COUNT(a.session_date) FILTER (
                   WHERE LOWER(a.attendance_status) IN ('present','late','excused')
               ) AS present_count
        FROM courses c
        JOIN enrollments e ON e.course_code = c.code
        JOIN people p ON p.roll_num = e.student_roll
        LEFT JOIN attendance a
            ON a.course_code = c.code AND LOWER(a.student_roll) = LOWER(e.student_roll)
        {where}
        GROUP BY c.code, c.name, c.min_attendance_percent, c.planned_sessions,
                 e.student_roll, p.name
        ORDER BY c.code, e.student_roll
        """,
        params,
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    at_risk = []
    for code, name, threshold, planned, student_roll, student_name, total, present in rows:
        budget = skip_budget(present or 0, total or 0, planned or 40, threshold or 75)
        if budget["below_threshold"]:
            at_risk.append(
                {
                    "student_roll": student_roll,
                    "student_name": student_name,
                    "course_code": code,
                    "course_name": name,
                    **budget,
                }
            )
    return {"status": "success", "at_risk_count": len(at_risk), "students": at_risk}


def get_consecutive_absences(student_id, course_code=None, min_streak=3):
    student_roll = _roll(student_id)
    connection = get_connection()
    cursor = connection.cursor()
    if course_code:
        cursor.execute(
            """
            SELECT c.code, a.session_date, a.attendance_status
            FROM attendance a
            JOIN courses c ON c.code = a.course_code
            WHERE LOWER(a.student_roll) = LOWER(%s)
              AND LOWER(REPLACE(c.code, ' ', '')) = LOWER(REPLACE(%s, ' ', ''))
            ORDER BY c.code, a.session_date
            """,
            (student_roll, course_code),
        )
    else:
        cursor.execute(
            """
            SELECT c.code, a.session_date, a.attendance_status
            FROM attendance a
            JOIN courses c ON c.code = a.course_code
            WHERE LOWER(a.student_roll) = LOWER(%s)
            ORDER BY c.code, a.session_date
            """,
            (student_roll,),
        )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    streaks = []
    current_course = None
    streak_start = None
    streak_len = 0

    def flush():
        nonlocal streak_start, streak_len
        if streak_len >= min_streak:
            streaks.append(
                {
                    "course_code": current_course,
                    "streak_length": streak_len,
                    "from_date": str(streak_start),
                }
            )
        streak_start = None
        streak_len = 0

    for code, session_date, status in rows:
        if code != current_course:
            flush()
            current_course = code
        if status and status.lower() == "absent":
            if streak_len == 0:
                streak_start = session_date
            streak_len += 1
        else:
            flush()
    flush()

    return {
        "status": "success",
        "student_roll": student_roll,
        "min_streak": min_streak,
        "streaks": streaks,
    }


def list_course_sessions(course_id=None, course_code=None):
    connection = get_connection()
    cursor = connection.cursor()
    course = _resolve_course(cursor, course_id=course_id, course_code=course_code)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": "Course not found."}

    cursor.execute(
        """
        SELECT session_date,
               COUNT(*) AS marked,
               COUNT(*) FILTER (
                   WHERE LOWER(attendance_status) IN ('present','late','excused')
               ) AS present_count,
               COUNT(*) FILTER (WHERE LOWER(attendance_status) = 'absent') AS absent_count
        FROM attendance
        WHERE course_code = %s
        GROUP BY session_date
        ORDER BY session_date
        """,
        (course[0],),
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "course_code": course[0],
        "course_name": course[1],
        "professor_name": course[2],
        "professor_roll": course[3],
        "session_count": len(rows),
        "sessions": [
            {
                "session_date": str(r[0]),
                "marked": r[1],
                "present_count": r[2],
                "absent_count": r[3],
            }
            for r in rows
        ],
    }


def rank_course_attendance(course_id=None, course_code=None):
    connection = get_connection()
    cursor = connection.cursor()
    course = _resolve_course(cursor, course_id=course_id, course_code=course_code)
    cursor.close()
    connection.close()
    if course is None:
        return {"status": "not_found", "message": "Course not found."}

    summary = get_course_attendance_summary(course[0])
    if summary.get("status") != "success":
        return summary

    ranked = sorted(
        summary["students"],
        key=lambda s: (
            s["attendance_percent"] is not None,
            s["attendance_percent"] or 0,
            s["present_count"],
        ),
        reverse=True,
    )
    for index, student in enumerate(ranked, start=1):
        student["rank"] = index
    return {
        "status": "success",
        "course_code": summary["course_code"],
        "course_name": summary["course_name"],
        "ranked": ranked,
    }


def export_course_attendance_csv(course_id=None, course_code=None, session_date=None):
    connection = get_connection()
    cursor = connection.cursor()
    course = _resolve_course(cursor, course_id=course_id, course_code=course_code)
    cursor.close()
    connection.close()
    if course is None:
        return {"status": "not_found", "message": "Course not found."}

    data = get_course_attendance(course[0], session_date=session_date)
    if data.get("status") != "success":
        return data

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["student_roll", "student_name", "session_date", "attendance_status"])
    if "roster" in data:
        for row in data["roster"]:
            writer.writerow(
                [
                    row["student_roll"],
                    row.get("student_name", ""),
                    data["session_date"],
                    row["attendance_status"],
                ]
            )
    else:
        for row in data["records"]:
            writer.writerow(
                [
                    row["student_roll"],
                    row.get("student_name", ""),
                    row["session_date"],
                    row["attendance_status"],
                ]
            )
    return {
        "status": "success",
        "course_code": data["course_code"],
        "course_name": data["course_name"],
        "session_date": data.get("session_date"),
        "csv": buffer.getvalue(),
    }


def resolve_course(course_id=None, course_code=None, course_name=None):
    connection = get_connection()
    cursor = connection.cursor()
    course = _resolve_course(cursor, course_id=course_id, course_code=course_code)
    if course is None and course_name:
        cursor.execute(
            """
            SELECT code, name, professor_name, professor_roll,
                   department, min_attendance_percent, planned_sessions
            FROM courses
            WHERE name ILIKE %s
               OR LOWER(REPLACE(code, ' ', '')) = LOWER(REPLACE(%s, ' ', ''))
            ORDER BY code
            LIMIT 1
            """,
            (f"%{course_name.strip()}%", course_name),
        )
        course = cursor.fetchone()
    cursor.close()
    connection.close()
    if course is None:
        return {
            "status": "not_found",
            "message": f"Course not found: {course_id or course_code or course_name}.",
        }
    return {
        "status": "success",
        "course": {
            "course_code": course[0],
            "course_name": course[1],
            "professor_name": course[2],
            "professor_roll": course[3],
            "department": course[4],
            "threshold_percent": course[5],
            "planned_sessions": course[6],
        },
    }


def list_courses(student_id=None, professor_id=None):
    connection = get_connection()
    cursor = connection.cursor()
    if student_id is not None:
        cursor.execute(
            """
            SELECT c.code, c.name, c.department, c.min_attendance_percent,
                   c.planned_sessions, c.professor_name, c.professor_roll
            FROM courses c
            JOIN enrollments e ON e.course_code = c.code
            WHERE LOWER(e.student_roll) = LOWER(%s)
            ORDER BY c.code
            """,
            (_roll(student_id),),
        )
    elif professor_id is not None:
        cursor.execute(
            """
            SELECT code, name, department, min_attendance_percent,
                   planned_sessions, professor_name, professor_roll
            FROM courses
            WHERE LOWER(professor_roll) = LOWER(%s)
            ORDER BY code
            """,
            (_roll(professor_id),),
        )
    else:
        cursor.execute(
            """
            SELECT code, name, department, min_attendance_percent,
                   planned_sessions, professor_name, professor_roll
            FROM courses
            ORDER BY code
            """
        )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "count": len(rows),
        "courses": [
            {
                "course_code": r[0],
                "course_name": r[1],
                "department": r[2],
                "threshold_percent": r[3],
                "planned_sessions": r[4],
                "professor_name": r[5],
                "professor_roll": r[6],
            }
            for r in rows
        ],
    }


def list_roster(course_id=None, course_code=None):
    connection = get_connection()
    cursor = connection.cursor()
    course = _resolve_course(cursor, course_id=course_id, course_code=course_code)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": "Course not found."}

    cursor.execute(
        """
        SELECT e.student_roll, p.name, p.role
        FROM enrollments e
        JOIN people p ON p.roll_num = e.student_roll
        WHERE e.course_code = %s
        ORDER BY e.student_roll
        """,
        (course[0],),
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "course_code": course[0],
        "course_name": course[1],
        "professor_name": course[2],
        "professor_roll": course[3],
        "enrolled_count": len(rows),
        "roster": [
            {"student_roll": r[0], "name": r[1], "role": r[2]} for r in rows
        ],
    }


def list_people(role=None):
    """List people (name, roll_num, role). Optional role filter."""
    connection = get_connection()
    cursor = connection.cursor()
    if role:
        cursor.execute(
            """
            SELECT name, roll_num, role FROM people
            WHERE LOWER(role) = LOWER(%s)
            ORDER BY roll_num
            """,
            (role,),
        )
    else:
        cursor.execute("SELECT name, roll_num, role FROM people ORDER BY role, roll_num")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "count": len(rows),
        "people": [{"name": r[0], "roll_num": r[1], "role": r[2]} for r in rows],
    }


def get_unmarked_students(session_date, course_id=None, course_code=None):
    session_date = _as_date(session_date)
    if session_date is None:
        return {"status": "error", "message": "session_date is required (YYYY-MM-DD)."}

    connection = get_connection()
    cursor = connection.cursor()
    course = _resolve_course(cursor, course_id=course_id, course_code=course_code)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": "Course not found."}

    cursor.execute(
        """
        SELECT e.student_roll, p.name
        FROM enrollments e
        JOIN people p ON p.roll_num = e.student_roll
        LEFT JOIN attendance a
            ON LOWER(a.student_roll) = LOWER(e.student_roll)
           AND a.course_code = e.course_code
           AND a.session_date = %s
        WHERE e.course_code = %s AND a.session_date IS NULL
        ORDER BY e.student_roll
        """,
        (session_date, course[0]),
    )
    unmarked = [{"student_roll": r[0], "name": r[1]} for r in cursor.fetchall()]
    cursor.execute("SELECT COUNT(*) FROM enrollments WHERE course_code = %s", (course[0],))
    enrolled = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "course_code": course[0],
        "course_name": course[1],
        "session_date": str(session_date),
        "enrolled_count": enrolled,
        "unmarked_count": len(unmarked),
        "unmarked_students": unmarked,
    }


def get_today_attendance(student_id=None, course_id=None, course_code=None):
    today = date.today()
    if student_id and (course_id or course_code):
        resolved = resolve_course(course_id=course_id, course_code=course_code)
        if resolved.get("status") != "success":
            return resolved
        result = get_attendance(
            student_id, resolved["course"]["course_code"], session_date=today
        )
        if result.get("status") == "success":
            result["view"] = "today"
        return result

    if student_id:
        student_roll = _roll(student_id)
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT a.session_date, c.code, c.name, a.attendance_status
            FROM attendance a
            JOIN courses c ON c.code = a.course_code
            WHERE LOWER(a.student_roll) = LOWER(%s) AND a.session_date = %s
            ORDER BY c.code
            """,
            (student_roll, today),
        )
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        if not rows:
            return {
                "status": "not_found",
                "message": f"No attendance for {student_roll} on {today}.",
                "session_date": str(today),
            }
        return {
            "status": "success",
            "view": "today",
            "student_roll": student_roll,
            "session_date": str(today),
            "records": [
                {
                    "session_date": str(r[0]),
                    "course_code": r[1],
                    "course_name": r[2],
                    "attendance_status": r[3],
                }
                for r in rows
            ],
        }

    if course_id or course_code:
        resolved = resolve_course(course_id=course_id, course_code=course_code)
        if resolved.get("status") != "success":
            return resolved
        result = get_course_attendance(resolved["course"]["course_code"], session_date=today)
        if result.get("status") == "success":
            result["view"] = "today"
        return result

    return {"status": "error", "message": "Provide student_id (roll) and/or course_code."}


def get_attendance_chart(student_id, course_code=None, date_from=None, date_to=None):
    student_roll = _roll(student_id)
    date_from = _as_date(date_from)
    date_to = _as_date(date_to)
    if date_from is None or date_to is None:
        today = date.today()
        date_from = today - timedelta(days=today.weekday())
        date_to = date_from + timedelta(days=6)

    connection = get_connection()
    cursor = connection.cursor()
    clauses = [
        "LOWER(a.student_roll) = LOWER(%s)",
        "a.session_date BETWEEN %s AND %s",
    ]
    params: list = [student_roll, date_from, date_to]
    if course_code:
        clauses.append("LOWER(REPLACE(c.code, ' ', '')) = LOWER(REPLACE(%s, ' ', ''))")
        params.append(course_code)

    cursor.execute(
        f"""
        SELECT a.session_date, c.code, a.attendance_status
        FROM attendance a
        JOIN courses c ON c.code = a.course_code
        WHERE {' AND '.join(clauses)}
        ORDER BY a.session_date, c.code
        """,
        params,
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    by_date: dict[str, dict[str, int]] = {}
    series = []
    for session_date, code, status in rows:
        key = str(session_date)
        bucket = by_date.setdefault(
            key, {"present": 0, "absent": 0, "late": 0, "excused": 0, "total": 0}
        )
        status_l = (status or "").lower()
        if status_l in bucket:
            bucket[status_l] += 1
        bucket["total"] += 1
        series.append(
            {
                "session_date": key,
                "course_code": code,
                "attendance_status": status,
                "counts_as_present": _counts_as_present(status_l),
            }
        )

    return {
        "status": "success",
        "view": "chart",
        "student_roll": student_roll,
        "course_code": course_code,
        "date_from": str(date_from),
        "date_to": str(date_to),
        "chart": [{"session_date": day, **counts} for day, counts in sorted(by_date.items())],
        "series": series,
        "point_count": len(series),
    }


# ---------------------------------------------------------------------------
# Admin management: people / courses / enrollments
# ---------------------------------------------------------------------------

_VALID_ROLES = frozenset({"student", "faculty", "admin"})


def add_person(name, roll_num, role):
    """Admin: create a person (name, roll_num, role)."""
    roll = _roll(roll_num)
    role_n = (role or "").strip().lower()
    name_n = (name or "").strip()
    if not name_n or not roll:
        return {"status": "error", "message": "name and roll_num are required."}
    if role_n not in _VALID_ROLES:
        return {"status": "error", "message": f"role must be one of {sorted(_VALID_ROLES)}."}

    connection = get_connection()
    cursor = connection.cursor()
    if _resolve_person(cursor, roll) is not None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": f"roll_num already exists: {roll}."}

    cursor.execute(
        "INSERT INTO people (roll_num, name, role) VALUES (%s, %s, %s)",
        (roll, name_n, role_n),
    )
    connection.commit()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "message": "Person added.",
        "person": {"name": name_n, "roll_num": roll, "role": role_n},
    }


def edit_person(roll_num, name=None, role=None, new_roll_num=None):
    """Admin: update a person's name, role, and/or roll_num."""
    roll = _roll(roll_num)
    connection = get_connection()
    cursor = connection.cursor()
    person = _resolve_person(cursor, roll)
    if person is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Person not found: {roll}."}

    new_name = (name if name is not None else person[1]).strip()
    new_role = (role if role is not None else person[2]).strip().lower()
    new_roll = _roll(new_roll_num) if new_roll_num is not None else person[0]

    if new_role not in _VALID_ROLES:
        cursor.close()
        connection.close()
        return {"status": "error", "message": f"role must be one of {sorted(_VALID_ROLES)}."}
    if not new_name or not new_roll:
        cursor.close()
        connection.close()
        return {"status": "error", "message": "name and roll_num cannot be empty."}

    # If roll changes: insert new → retarget FKs → delete old (FK-safe).
    if new_roll.lower() != person[0].lower():
        existing = _resolve_person(cursor, new_roll)
        if existing is not None:
            cursor.close()
            connection.close()
            return {"status": "error", "message": f"roll_num already exists: {new_roll}."}
        cursor.execute(
            "INSERT INTO people (roll_num, name, role) VALUES (%s, %s, %s)",
            (new_roll, new_name, new_role),
        )
        cursor.execute(
            "UPDATE courses SET professor_roll = %s WHERE LOWER(professor_roll) = LOWER(%s)",
            (new_roll, person[0]),
        )
        cursor.execute(
            "UPDATE enrollments SET student_roll = %s WHERE LOWER(student_roll) = LOWER(%s)",
            (new_roll, person[0]),
        )
        cursor.execute(
            "UPDATE attendance SET student_roll = %s WHERE LOWER(student_roll) = LOWER(%s)",
            (new_roll, person[0]),
        )
        cursor.execute(
            "UPDATE attendance SET marked_by_roll = %s WHERE LOWER(marked_by_roll) = LOWER(%s)",
            (new_roll, person[0]),
        )
        cursor.execute(
            "DELETE FROM people WHERE LOWER(roll_num) = LOWER(%s)",
            (person[0],),
        )
    else:
        cursor.execute(
            """
            UPDATE people SET name = %s, role = %s
            WHERE LOWER(roll_num) = LOWER(%s)
            """,
            (new_name, new_role, person[0]),
        )

    # Keep professor_name in sync when faculty name changes
    if new_role == "faculty" or person[2] == "faculty":
        cursor.execute(
            """
            UPDATE courses SET professor_name = %s
            WHERE LOWER(professor_roll) = LOWER(%s)
            """,
            (new_name, new_roll),
        )

    connection.commit()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "message": "Person updated.",
        "person": {"name": new_name, "roll_num": new_roll, "role": new_role},
    }


def delete_person(roll_num):
    """Admin: delete a person (fails if still referenced by courses/enrollments/attendance)."""
    roll = _roll(roll_num)
    connection = get_connection()
    cursor = connection.cursor()
    person = _resolve_person(cursor, roll)
    if person is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Person not found: {roll}."}

    cursor.execute(
        "SELECT COUNT(*) FROM courses WHERE LOWER(professor_roll) = LOWER(%s)", (roll,)
    )
    courses_n = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM enrollments WHERE LOWER(student_roll) = LOWER(%s)", (roll,)
    )
    enroll_n = cursor.fetchone()[0]
    cursor.execute(
        """
        SELECT COUNT(*) FROM attendance
        WHERE LOWER(student_roll) = LOWER(%s) OR LOWER(marked_by_roll) = LOWER(%s)
        """,
        (roll, roll),
    )
    att_n = cursor.fetchone()[0]
    if courses_n or enroll_n or att_n:
        cursor.close()
        connection.close()
        return {
            "status": "error",
            "message": (
                f"Cannot delete {roll}: still referenced "
                f"(courses={courses_n}, enrollments={enroll_n}, attendance={att_n})."
            ),
        }

    cursor.execute("DELETE FROM people WHERE LOWER(roll_num) = LOWER(%s)", (roll,))
    connection.commit()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "message": "Person deleted.",
        "person": {"name": person[1], "roll_num": person[0], "role": person[2]},
    }


def add_course(
    course_code,
    name,
    professor_roll,
    department="CSE",
    min_attendance_percent=75,
    planned_sessions=40,
    professor_name=None,
):
    """Admin: create a course taught by professor_roll."""
    code = (course_code or "").strip().upper().replace(" ", "")
    course_name = (name or "").strip()
    if not code or not course_name:
        return {"status": "error", "message": "course_code and name are required."}

    connection = get_connection()
    cursor = connection.cursor()
    if _resolve_course(cursor, course_code=code) is not None:
        cursor.close()
        connection.close()
        return {"status": "error", "message": f"Course already exists: {code}."}

    professor = _resolve_person(cursor, professor_roll, roles=["faculty", "admin"])
    if professor is None:
        cursor.close()
        connection.close()
        return {
            "status": "not_found",
            "message": f"Professor not found: {professor_roll}.",
        }

    pname = (professor_name or professor[1]).strip()
    cursor.execute(
        """
        INSERT INTO courses (
            code, name, professor_name, professor_roll,
            department, min_attendance_percent, planned_sessions
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            code,
            course_name,
            pname,
            professor[0],
            department or "CSE",
            int(min_attendance_percent),
            int(planned_sessions),
        ),
    )
    connection.commit()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "message": "Course added.",
        "course": {
            "course_code": code,
            "course_name": course_name,
            "professor_name": pname,
            "professor_roll": professor[0],
            "department": department or "CSE",
            "threshold_percent": int(min_attendance_percent),
            "planned_sessions": int(planned_sessions),
        },
    }


def edit_course(
    course_code,
    name=None,
    professor_roll=None,
    professor_name=None,
    department=None,
    min_attendance_percent=None,
    planned_sessions=None,
    new_course_code=None,
):
    """Admin: update course fields."""
    connection = get_connection()
    cursor = connection.cursor()
    course = _resolve_course(cursor, course_code=course_code)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Course not found: {course_code}."}

    code = course[0]
    new_code = (new_course_code or code).strip().upper().replace(" ", "")
    new_name = name.strip() if name is not None else course[1]
    new_dept = department if department is not None else course[4]
    new_thresh = (
        int(min_attendance_percent)
        if min_attendance_percent is not None
        else course[5]
    )
    new_planned = (
        int(planned_sessions) if planned_sessions is not None else course[6]
    )
    new_proll = course[3]
    new_pname = course[2]

    if professor_roll is not None:
        professor = _resolve_person(cursor, professor_roll, roles=["faculty", "admin"])
        if professor is None:
            cursor.close()
            connection.close()
            return {
                "status": "not_found",
                "message": f"Professor not found: {professor_roll}.",
            }
        new_proll = professor[0]
        new_pname = professor_name.strip() if professor_name else professor[1]
    elif professor_name is not None:
        new_pname = professor_name.strip()

    if new_code != code:
        if _resolve_course(cursor, course_code=new_code) is not None:
            cursor.close()
            connection.close()
            return {"status": "error", "message": f"Course already exists: {new_code}."}
        cursor.execute(
            "UPDATE enrollments SET course_code = %s WHERE course_code = %s",
            (new_code, code),
        )
        cursor.execute(
            "UPDATE attendance SET course_code = %s WHERE course_code = %s",
            (new_code, code),
        )
        cursor.execute(
            """
            UPDATE courses SET
                code = %s, name = %s, professor_name = %s, professor_roll = %s,
                department = %s, min_attendance_percent = %s, planned_sessions = %s
            WHERE code = %s
            """,
            (new_code, new_name, new_pname, new_proll, new_dept, new_thresh, new_planned, code),
        )
    else:
        cursor.execute(
            """
            UPDATE courses SET
                name = %s, professor_name = %s, professor_roll = %s,
                department = %s, min_attendance_percent = %s, planned_sessions = %s
            WHERE code = %s
            """,
            (new_name, new_pname, new_proll, new_dept, new_thresh, new_planned, code),
        )

    connection.commit()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "message": "Course updated.",
        "course": {
            "course_code": new_code,
            "course_name": new_name,
            "professor_name": new_pname,
            "professor_roll": new_proll,
            "department": new_dept,
            "threshold_percent": new_thresh,
            "planned_sessions": new_planned,
        },
    }


def delete_course(course_code):
    """Admin: delete a course and its enrollments/attendance."""
    connection = get_connection()
    cursor = connection.cursor()
    course = _resolve_course(cursor, course_code=course_code)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Course not found: {course_code}."}

    cursor.execute("DELETE FROM attendance WHERE course_code = %s", (course[0],))
    att_deleted = cursor.rowcount
    cursor.execute("DELETE FROM enrollments WHERE course_code = %s", (course[0],))
    enr_deleted = cursor.rowcount
    cursor.execute("DELETE FROM courses WHERE code = %s", (course[0],))
    connection.commit()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "message": "Course deleted.",
        "course_code": course[0],
        "deleted_enrollments": enr_deleted,
        "deleted_attendance": att_deleted,
    }


def add_enrollment(student_roll, course_code):
    """Admin: enroll a student in a course."""
    connection = get_connection()
    cursor = connection.cursor()
    student = _resolve_person(cursor, student_roll, roles=["student"])
    if student is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Student not found: {student_roll}."}

    course = _resolve_course(cursor, course_code=course_code)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Course not found: {course_code}."}

    cursor.execute(
        """
        SELECT 1 FROM enrollments
        WHERE LOWER(student_roll) = LOWER(%s) AND course_code = %s
        """,
        (student[0], course[0]),
    )
    if cursor.fetchone() is not None:
        cursor.close()
        connection.close()
        return {
            "status": "error",
            "message": f"{student[0]} is already enrolled in {course[0]}.",
        }

    cursor.execute(
        """
        INSERT INTO enrollments (student_roll, student_name, course_code)
        VALUES (%s, %s, %s)
        """,
        (student[0], student[1], course[0]),
    )
    connection.commit()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "message": "Enrollment added.",
        "student_roll": student[0],
        "student_name": student[1],
        "course_code": course[0],
        "course_name": course[1],
    }


def delete_enrollment(student_roll, course_code):
    """Admin: remove a student from a course (attendance rows kept unless cleaned)."""
    connection = get_connection()
    cursor = connection.cursor()
    course = _resolve_course(cursor, course_code=course_code)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": f"Course not found: {course_code}."}

    cursor.execute(
        """
        DELETE FROM enrollments
        WHERE LOWER(student_roll) = LOWER(%s) AND course_code = %s
        RETURNING student_roll
        """,
        (_roll(student_roll), course[0]),
    )
    row = cursor.fetchone()
    if row is None:
        cursor.close()
        connection.close()
        return {
            "status": "not_found",
            "message": f"Enrollment not found for {student_roll} in {course[0]}.",
        }

    connection.commit()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "message": "Enrollment deleted.",
        "student_roll": row[0],
        "course_code": course[0],
    }


def list_enrollments(student_roll=None, course_code=None):
    """Admin/faculty: list enrollments, optionally filtered."""
    connection = get_connection()
    cursor = connection.cursor()
    clauses = []
    params: list = []
    if student_roll:
        clauses.append("LOWER(e.student_roll) = LOWER(%s)")
        params.append(_roll(student_roll))
    if course_code:
        course = _resolve_course(cursor, course_code=course_code)
        if course is None:
            cursor.close()
            connection.close()
            return {"status": "not_found", "message": f"Course not found: {course_code}."}
        clauses.append("e.course_code = %s")
        params.append(course[0])

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    cursor.execute(
        f"""
        SELECT e.student_roll, p.name, e.course_code, c.name
        FROM enrollments e
        JOIN people p ON p.roll_num = e.student_roll
        JOIN courses c ON c.code = e.course_code
        {where}
        ORDER BY e.course_code, e.student_roll
        """,
        params,
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "count": len(rows),
        "enrollments": [
            {
                "student_roll": r[0],
                "student_name": r[1],
                "course_code": r[2],
                "course_name": r[3],
            }
            for r in rows
        ],
    }
