"""Timetable functions — sync helpers against the `timetable` database.

Tables used:
  people(roll_num, name, role, student_group)
  courses(code, name, professor_name, professor_roll, ...)
  rooms(room_id, capacity, building)
  timetable(id, course_code, timetable_day, slot_start, slot_end, room_id)
"""

from __future__ import annotations

import os
import re
import threading
import uuid
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import db
from config import TIMETABLE_DB_NAME
from ttl_cache import TtlCache

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_DAY_INDEX = {name: idx for idx, name in enumerate(WEEKDAYS)}
_SLOT_GRID = ("09:00:00", "10:00:00", "11:00:00", "14:00:00", "15:00:00")

_SEED_SLOTS = [
    ("CS101", "Monday", "10:00", "11:00", "B204"),
    ("MA201", "Monday", "14:00", "15:00", "B205"),
    ("CS102", "Tuesday", "09:00", "10:00", "B204"),
    ("PHY101", "Tuesday", "11:00", "12:00", "B205"),
    ("CS101", "Wednesday", "10:00", "11:00", "B204"),
    ("HS101", "Wednesday", "14:00", "15:00", "B205"),
    ("MA201", "Thursday", "09:00", "10:00", "B205"),
    ("CS102", "Thursday", "15:00", "16:00", "B204"),
    ("PHY101", "Friday", "11:00", "12:00", "B205"),
    ("CS101", "Friday", "14:00", "15:00", "B204"),
]


_schema_ready = False
_schema_lock = threading.Lock()
_tt_cache = TtlCache("timetable", ttl_seconds=60)


def get_connection():
    _ensure_schema_once()
    return db.get_connection(TIMETABLE_DB_NAME)


def _ensure_schema_once() -> None:
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        ensure_schema()
        _schema_ready = True


def ensure_schema() -> None:
    """Create rooms/timetable tables if missing; seed demo slots once."""
    connection = db.get_connection(TIMETABLE_DB_NAME)
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS people (
            roll_num TEXT PRIMARY KEY,
            name VARCHAR(128),
            role VARCHAR(32)
        )
        """
    )
    # SUPERSEDED as identity by campus_agent.people; person_id is the link.
    # roll_num stays the PK this release (no domain FKs point at people here).
    cursor.execute(
        "ALTER TABLE people ADD COLUMN IF NOT EXISTS person_id UUID"
    )
    cursor.execute(
        """
        ALTER TABLE people ADD COLUMN IF NOT EXISTS student_group VARCHAR(64)
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            room_id VARCHAR(32) PRIMARY KEY,
            capacity INTEGER NOT NULL DEFAULT 20,
            building VARCHAR(128) NOT NULL DEFAULT 'Main'
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS timetable (
            id UUID PRIMARY KEY,
            course_code VARCHAR(32) NOT NULL REFERENCES courses(code),
            timetable_day VARCHAR(16) NOT NULL,
            slot_start TIME NOT NULL,
            slot_end TIME NOT NULL,
            room_id VARCHAR(32) NOT NULL
        )
        """
    )
    cursor.execute(
        """
        ALTER TABLE timetable
        ADD COLUMN IF NOT EXISTS class_type VARCHAR(32),
        ADD COLUMN IF NOT EXISTS student_group VARCHAR(64),
        ADD COLUMN IF NOT EXISTS department VARCHAR(32)
        """
    )
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_timetable_course_day_start
        ON timetable (course_code, timetable_day, slot_start)
        """
    )
    cursor.execute("SELECT COUNT(*) FROM rooms")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO rooms (room_id, capacity, building) VALUES (%s, %s, %s)",
            [("B204", 25, "Main"), ("B205", 20, "Main")],
        )
    cursor.execute("SELECT COUNT(*) FROM timetable")
    if cursor.fetchone()[0] == 0:
        for code, day, start, end, room in _SEED_SLOTS:
            cursor.execute("SELECT 1 FROM courses WHERE code = %s", (code,))
            if cursor.fetchone() is None:
                continue
            cursor.execute(
                """
                INSERT INTO timetable (id, course_code, timetable_day, slot_start, slot_end, room_id)
                VALUES (%s, %s, %s, %s::time, %s::time, %s)
                ON CONFLICT DO NOTHING
                """,
                (uuid.uuid4(), code, day, start, end, room),
            )
    connection.commit()
    cursor.close()
    connection.close()


def campus_now() -> datetime:
    tz = os.getenv("CAMPUS_TIMEZONE", "Asia/Kolkata")
    return datetime.now(ZoneInfo(tz))


def _parse_time(value) -> time | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    text = str(value).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def normalize_day(value: str | None) -> str | None:
    if not value:
        return None
    token = value.strip().lower()
    aliases = {
        "mon": "Monday",
        "monday": "Monday",
        "tue": "Tuesday",
        "tues": "Tuesday",
        "tuesday": "Tuesday",
        "wed": "Wednesday",
        "wednesday": "Wednesday",
        "thu": "Thursday",
        "thur": "Thursday",
        "thurs": "Thursday",
        "thursday": "Thursday",
        "fri": "Friday",
        "friday": "Friday",
        "sat": "Saturday",
        "saturday": "Saturday",
        "sun": "Sunday",
        "sunday": "Sunday",
    }
    if token in {"today", "tonight"}:
        return campus_now().strftime("%A")
    if token == "tomorrow":
        return (campus_now() + timedelta(days=1)).strftime("%A")
    return aliases.get(token)


def _serialize_row(slot_id, course_code, course_name, day, start, end, room_id, class_type=None, student_group=None) -> dict:
    start_s = start.isoformat() if isinstance(start, time) else str(start)
    end_s = end.isoformat() if isinstance(end, time) else str(end)
    return {
        "slot_id": str(slot_id),
        "course_code": course_code,
        "course_name": course_name,
        "subject": course_name,
        "timetable_day": day,
        "timetable_slot": f"{start_s}-{end_s}",
        "slot_start": start_s,
        "slot_end": end_s,
        "room_id": room_id,
        "weekday": day,
        "class_type": class_type,
        "student_group": student_group,
    }


def _sort_key(item: dict) -> tuple[int, str]:
    return (_DAY_INDEX.get(item["timetable_day"], 99), item["slot_start"])


def _find_course(cursor, subject: str | None):
    if not subject or not str(subject).strip():
        return None
    token = str(subject).strip()
    cursor.execute(
        """
        SELECT code, name, professor_name, professor_roll
        FROM courses
        WHERE LOWER(code) = LOWER(%s)
        """,
        (token,),
    )
    row = cursor.fetchone()
    if row is not None:
        return row
    cursor.execute(
        """
        SELECT code, name, professor_name, professor_roll
        FROM courses
        WHERE name ILIKE %s
        ORDER BY code
        LIMIT 1
        """,
        (f"%{token}%",),
    )
    return cursor.fetchone()


def _load_rows(cursor, timetable_day: str | None = None, course_code: str | None = None, class_type: str | None = None, student_group: str | None = None):
    clauses = []
    params: list = []
    if timetable_day:
        clauses.append("t.timetable_day = %s")
        params.append(timetable_day)
    if course_code:
        clauses.append("LOWER(t.course_code) = LOWER(%s)")
        params.append(course_code)
    if class_type:
        clauses.append("t.class_type = %s")
        params.append(class_type)
    if student_group:
        clauses.append("t.student_group = %s")
        params.append(student_group)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    cursor.execute(
        f"""
        SELECT t.id, t.course_code, c.name, t.timetable_day,
               t.slot_start, t.slot_end, t.room_id, t.class_type, t.student_group
        FROM timetable t
        JOIN courses c ON c.code = t.course_code
        {where}
        """,
        params,
    )
    items = [_serialize_row(*row) for row in cursor.fetchall()]
    return sorted(items, key=_sort_key)


def _next_item(items: list[dict], moment: datetime) -> dict | None:
    if not items:
        return None
    current_idx = moment.weekday()
    current_time = moment.time()
    later: list[dict] = []
    for item in sorted(items, key=_sort_key):
        day_idx = _DAY_INDEX.get(item["timetable_day"], 99)
        start = _parse_time(item["slot_start"])
        if start is None:
            continue
        if day_idx > current_idx or (day_idx == current_idx and start > current_time):
            later.append(item)
    if later:
        return later[0]
    return sorted(items, key=_sort_key)[0]


def _get_slot(cursor, slot_id=None, day=None, start=None, course_code=None):
    if slot_id:
        cursor.execute(
            """
            SELECT t.id, t.course_code, c.name, t.timetable_day,
                   t.slot_start, t.slot_end, t.room_id, t.class_type, t.student_group
            FROM timetable t
            JOIN courses c ON c.code = t.course_code
            WHERE t.id::text = %s
            """,
            (str(slot_id),),
        )
        return cursor.fetchone()

    clauses = []
    params: list = []
    if day:
        clauses.append("t.timetable_day = %s")
        params.append(day)
    if start is not None:
        clauses.append("t.slot_start = %s")
        params.append(start)
    if course_code:
        clauses.append("LOWER(t.course_code) = LOWER(%s)")
        params.append(course_code)
    if not clauses:
        return None
    cursor.execute(
        f"""
        SELECT t.id, t.course_code, c.name, t.timetable_day,
               t.slot_start, t.slot_end, t.room_id, t.class_type, t.student_group
        FROM timetable t
        JOIN courses c ON c.code = t.course_code
        WHERE {' AND '.join(clauses)}
        LIMIT 1
        """,
        params,
    )
    return cursor.fetchone()


def parse_roll_number(roll_num: str) -> dict:
    match = re.match(r"^(\d{2})(\d{2})([A-Z]{2})(\d+)$", str(roll_num).strip().upper())
    if not match:
        return {"year": 0, "dept": ""}
    admission_year = int(match.group(1))
    academic_year = 26 - admission_year + 1
    department = match.group(3)
    return {"year": academic_year, "dept": department}

def is_group_in_range(student_group: str | None, slot_group: str | None) -> bool:
    """
    Evaluates if a messy CSV group ('G-13', 'Group - 21') falls inside 
    a timetable boundary ('G1-G24', 'G13-G15', or 'G13').
    """
    if not slot_group:
        return True # Universal slot
        
    if not student_group:
        return False # Student has no group but slot requires one
        
    # Extract the integer from the student's messy group string (e.g., "G-13" -> 13)
    s_match = re.search(r'\d+', str(student_group))
    if not s_match:
        return False
    s_num = int(s_match.group())
    
    # Extract boundaries from the slot string (e.g., "G13-G18" -> [13, 18])
    slot_nums = [int(n) for n in re.findall(r'\d+', str(slot_group))]
    
    if len(slot_nums) == 1:
        return s_num == slot_nums[0]
    elif len(slot_nums) >= 2:
        return slot_nums[0] <= s_num <= slot_nums[1]
        
    return False

def get_schedule(target_id: str, target_type: str = "student"):
    key = f"schedule:{str(target_id).lower()}:{target_type}"
    return _tt_cache.get(key, lambda: _get_schedule_uncached(target_id, target_type))


def _get_schedule_uncached(target_id: str, target_type: str = "student"):
    connection = get_connection()
    cursor = connection.cursor()
    
    parsed = parse_roll_number(target_id)
    academic_year = parsed["year"]
    dept = parsed["dept"]
    
    cursor.execute("SELECT role, student_group FROM people WHERE LOWER(roll_num) = LOWER(%s)", (target_id,))
    row = cursor.fetchone()
    if row:
        target_type = row[0].lower()
        student_group = row[1]
    else:
        student_group = None

    items = []

    if target_type == "student":
        if academic_year == 1:
            # 1ST YEAR: Pull all 1st year slots, then filter mathematically by group bounds!
            cursor.execute("""
                SELECT t.id, t.course_code, c.name, t.timetable_day, t.slot_start, t.slot_end, t.room_id, t.class_type, t.student_group
                FROM timetable t JOIN courses c ON c.code = t.course_code
                WHERE t.student_group IS NOT NULL
            """)
            for r in cursor.fetchall():
                # r[8] is the slot's target group (e.g. "G1-G6")
                if is_group_in_range(student_group, r[8]): 
                    items.append(_serialize_row(*r))
        else:
            # 2ND+ YEAR: Ignore groups completely, route strictly by Department (e.g., CS2%)
            prefix = f"{dept}{academic_year}%"
            cursor.execute("""
                SELECT t.id, t.course_code, c.name, t.timetable_day, t.slot_start, t.slot_end, t.room_id, t.class_type, t.student_group
                FROM timetable t JOIN courses c ON c.code = t.course_code
                WHERE t.course_code LIKE %s
            """, (prefix,))
            items = [_serialize_row(*r) for r in cursor.fetchall()]
    else:
        # FACULTY: Route by owned courses
        cursor.execute("""
            SELECT t.id, t.course_code, c.name, t.timetable_day, t.slot_start, t.slot_end, t.room_id, t.class_type, t.student_group
            FROM timetable t JOIN courses c ON c.code = t.course_code
            WHERE LOWER(c.professor_roll) = LOWER(%s)
        """, (target_id,))
        items = [_serialize_row(*r) for r in cursor.fetchall()]

    cursor.close()
    connection.close()
    
    # Sort the items properly by Day then Time
    items = sorted(items, key=_sort_key)
    
    return {
        "status": "success",
        "query_kind": "schedule",
        "items": items,
        "count": len(items)
    }

def list_subjects():
    return _tt_cache.get("subjects", _list_subjects_uncached)


def _list_subjects_uncached():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT code, name, professor_name, professor_roll
        FROM courses
        ORDER BY code
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "query_kind": "subjects",
        "items": [
            {
                "course_code": row[0],
                "course_name": row[1],
                "subject": row[1],
                "professor_name": row[2],
                "professor_roll": row[3],
            }
            for row in rows
        ],
        "count": len(rows),
    }


def resolve_course(course_code: str | None = None, course_name: str | None = None):
    connection = get_connection()
    cursor = connection.cursor()
    course = _find_course(cursor, course_code or course_name)
    cursor.close()
    connection.close()
    if course is None:
        return {
            "status": "not_found",
            "message": f"Course not found: {course_code or course_name}.",
        }
    return {
        "status": "success",
        "course_code": course[0],
        "course_name": course[1],
        "subject": course[1],
        "professor_name": course[2],
        "professor_roll": course[3],
    }


def get_week(subject: str | None = None, course_code: str | None = None, class_type: str | None = None, student_group: str | None = None):
    key = f"week:{subject}|{course_code}|{class_type}|{student_group}"
    return _tt_cache.get(key, lambda: _get_week_uncached(subject, course_code, class_type, student_group))


def _get_week_uncached(subject: str | None = None, course_code: str | None = None, class_type: str | None = None, student_group: str | None = None):
    connection = get_connection()
    cursor = connection.cursor()
    course = _find_course(cursor, subject or course_code)
    if (subject or course_code) and course is None:
        cursor.close()
        connection.close()
        return {
            "status": "not_found",
            "message": f"Unknown subject: {subject or course_code}.",
            "items": [],
            "count": 0,
        }
    items = _load_rows(cursor, course_code=course[0] if course else None, class_type=class_type, student_group=student_group)
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "query_kind": "week",
        "items": items,
        "count": len(items),
        "course_code": course[0] if course else None,
    }


def get_day(
    timetable_day: str = "today",
    subject: str | None = None,
    course_code: str | None = None,
    class_type: str | None = None,
    student_group: str | None = None,
):
    key = f"day:{timetable_day}|{subject}|{course_code}|{class_type}|{student_group}"
    return _tt_cache.get(
        key,
        lambda: _get_day_uncached(
            timetable_day, subject, course_code, class_type, student_group
        ),
    )


def _get_day_uncached(
    timetable_day: str = "today",
    subject: str | None = None,
    course_code: str | None = None,
    class_type: str | None = None,
    student_group: str | None = None,
):
    day = normalize_day(timetable_day)
    if day is None:
        return {"status": "error", "message": f"Invalid day: {timetable_day}."}
    connection = get_connection()
    cursor = connection.cursor()
    course = _find_course(cursor, subject or course_code)
    if (subject or course_code) and course is None:
        cursor.close()
        connection.close()
        return {
            "status": "not_found",
            "message": f"Unknown subject: {subject or course_code}.",
            "items": [],
            "count": 0,
        }
    items = _load_rows(
        cursor, timetable_day=day, course_code=course[0] if course else None, class_type=class_type, student_group=student_group
    )
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "query_kind": "day",
        "timetable_day": day,
        "weekday": day,
        "items": items,
        "count": len(items),
        "course_code": course[0] if course else None,
    }


def get_timetable(
    timetable_day: str | None = None,
    subject: str | None = None,
    course_code: str | None = None,
    class_type: str | None = None,
    student_group: str | None = None,
):
    if timetable_day:
        return get_day(timetable_day, subject=subject, course_code=course_code, class_type=class_type, student_group=student_group)
    return get_week(subject=subject, course_code=course_code, class_type=class_type, student_group=student_group)


def count_classes(subject: str | None = None, course_code: str | None = None):
    connection = get_connection()
    cursor = connection.cursor()
    token = subject or course_code
    course = _find_course(cursor, token)
    if token and course is None:
        cursor.close()
        connection.close()
        return {
            "status": "not_found",
            "message": "unknown subject",
            "count": 0,
            "items": [],
            "query_kind": "count",
        }
    items = _load_rows(cursor, course_code=course[0] if course else None)
    cursor.close()
    connection.close()
    if course is None:
        grouped: dict[str, dict] = {}
        for item in items:
            key = item["course_code"]
            grouped.setdefault(
                key,
                {
                    "course_code": key,
                    "course_name": item["course_name"],
                    "subject": item["subject"],
                    "count": 0,
                },
            )
            grouped[key]["count"] += 1
        return {
            "status": "success",
            "query_kind": "count",
            "items": list(grouped.values()),
            "count": len(items),
        }
    return {
        "status": "success",
        "query_kind": "count",
        "course_code": course[0],
        "course_name": course[1],
        "subject": course[1],
        "count": len(items),
        "items": items,
    }


def next_class(
    subject: str | None = None,
    course_code: str | None = None,
    now: str | None = None,
):
    connection = get_connection()
    cursor = connection.cursor()
    course = _find_course(cursor, subject or course_code)
    if (subject or course_code) and course is None:
        cursor.close()
        connection.close()
        return {
            "status": "not_found",
            "message": f"Unknown subject: {subject or course_code}.",
            "next": None,
            "items": [],
        }
    items = _load_rows(cursor, course_code=course[0] if course else None)
    cursor.close()
    connection.close()

    if now:
        moment = datetime.fromisoformat(str(now).replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(
                tzinfo=ZoneInfo(os.getenv("CAMPUS_TIMEZONE", "Asia/Kolkata"))
            )
    else:
        moment = campus_now()

    upcoming = _next_item(items, moment)
    return {
        "status": "success",
        "query_kind": "next",
        "next": upcoming,
        "items": [upcoming] if upcoming else [],
        "course_code": course[0] if course else None,
        "course_name": course[1] if course else None,
        "subject": course[1] if course else (subject or course_code),
    }


def get_free_slots(timetable_day: str | None = None):
    key = f"free:{timetable_day}"
    return _tt_cache.get(key, lambda: _get_free_slots_uncached(timetable_day))


def _get_free_slots_uncached(timetable_day: str | None = None):
    day = normalize_day(timetable_day) if timetable_day else campus_now().strftime("%A")
    if day is None:
        return {"status": "error", "message": f"Invalid day: {timetable_day}."}
    connection = get_connection()
    cursor = connection.cursor()
    items = _load_rows(cursor, timetable_day=day)
    cursor.close()
    connection.close()
    occupied = {(i["timetable_day"], i["slot_start"], i["slot_end"]) for i in items}
    free = []
    for start in _SLOT_GRID:
        hour = int(start.split(":")[0])
        end = f"{hour + 1:02d}:00:00"
        if (day, start, end) not in occupied:
            free.append(
                {
                    "timetable_day": day,
                    "weekday": day,
                    "slot_start": start,
                    "slot_end": end,
                    "available": True,
                }
            )
    return {
        "status": "success",
        "query_kind": "free",
        "timetable_day": day,
        "weekday": day,
        "items": free,
        "count": len(free),
    }


def list_rooms():
    return _tt_cache.get("rooms", _list_rooms_uncached)


def _list_rooms_uncached():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT room_id, capacity, building
        FROM rooms
        ORDER BY room_id
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return {
        "status": "success",
        "items": [
            {"room_id": row[0], "capacity": row[1], "building": row[2]}
            for row in rows
        ],
        "count": len(rows),
    }


def add_slot(
    subject: str | None = None,
    course_code: str | None = None,
    timetable_day: str | None = None,
    slot_start: str | None = None,
    slot_end: str | None = None,
    room_id: str | None = None,
    professor_roll: str | None = None,
    class_type: str | None = None,
    student_group: str | None = None,
):
    day = normalize_day(timetable_day)
    start = _parse_time(slot_start)
    end = _parse_time(slot_end)
    if not day or start is None or end is None or not room_id:
        return {
            "status": "error",
            "message": "day, start, end, and room_id are required",
            "items": [],
        }

    connection = get_connection()
    cursor = connection.cursor()
    course = _find_course(cursor, subject or course_code)
    if course is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": "unknown subject", "items": []}

    if professor_roll and course[3] and course[3].lower() != str(professor_roll).lower():
        # Faculty may only edit courses they own; admin can pass without match if empty check skipped in agent
        cursor.close()
        connection.close()
        return {
            "status": "error",
            "message": f"Course {course[0]} is owned by {course[3]}, not {professor_roll}.",
            "items": [],
        }

    # Conflict checking
    cursor.execute(
        """
        SELECT t.room_id, c.professor_roll, t.student_group
        FROM timetable t
        JOIN courses c ON t.course_code = c.code
        WHERE t.timetable_day = %s
          AND t.slot_start < %s
          AND t.slot_end > %s
        """,
        (day, end, start)
    )
    conflicts = cursor.fetchall()
    for crow in conflicts:
        c_room, c_prof, c_group = crow
        if c_room.upper() == room_id.strip().upper():
            cursor.close()
            connection.close()
            return {"status": "error", "message": f"Room Conflict: Room {room_id} is already booked at this time.", "items": []}
        if course[3] and c_prof and c_prof.lower() == course[3].lower():
            cursor.close()
            connection.close()
            return {"status": "error", "message": f"Professor Conflict: Professor {course[3]} is already teaching a class at this time.", "items": []}
        if student_group and c_group and c_group == student_group:
            cursor.close()
            connection.close()
            return {"status": "error", "message": f"Group Conflict: Student group {student_group} is already in another class at this time.", "items": []}

    slot_uuid = uuid.uuid4()
    try:
        cursor.execute(
            """
            INSERT INTO timetable (id, course_code, timetable_day, slot_start, slot_end, room_id, class_type, student_group)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, course_code, timetable_day, slot_start, slot_end, room_id, class_type, student_group
            """,
            (slot_uuid, course[0], day, start, end, room_id.strip().upper(), class_type, student_group),
        )
    except Exception as exc:  # noqa: BLE001
        connection.rollback()
        cursor.close()
        connection.close()
        return {"status": "error", "message": str(exc), "items": []}

    row = cursor.fetchone()
    connection.commit()
    item = _serialize_row(row[0], row[1], course[1], row[2], row[3], row[4], row[5], row[6], row[7])
    cursor.close()
    connection.close()
    _tt_cache.clear()
    return {
        "status": "success",
        "query_kind": "add",
        "slot_id": item["slot_id"],
        "items": [item],
        "message": "Slot added.",
    }


def update_slot(
    slot_id: str | None = None,
    subject: str | None = None,
    course_code: str | None = None,
    timetable_day: str | None = None,
    slot_start: str | None = None,
    slot_end: str | None = None,
    room_id: str | None = None,
    new_day: str | None = None,
    new_start: str | None = None,
    new_end: str | None = None,
    new_room_id: str | None = None,
    new_subject: str | None = None,
    professor_roll: str | None = None,
):
    day = normalize_day(timetable_day)
    start = _parse_time(slot_start)
    connection = get_connection()
    cursor = connection.cursor()
    course = _find_course(cursor, subject or course_code)
    row = _get_slot(
        cursor,
        slot_id=slot_id,
        day=day,
        start=start,
        course_code=course[0] if course else None,
    )
    if row is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": "slot not found", "items": []}

    # Ownership check against current course
    cursor.execute(
        "SELECT professor_roll FROM courses WHERE code = %s",
        (row[1],),
    )
    owner = cursor.fetchone()
    if (
        professor_roll
        and owner
        and owner[0]
        and owner[0].lower() != str(professor_roll).lower()
    ):
        cursor.close()
        connection.close()
        return {
            "status": "error",
            "message": f"Course {row[1]} is owned by {owner[0]}, not {professor_roll}.",
            "items": [],
        }

    next_day = normalize_day(new_day) if new_day else None
    next_start = _parse_time(new_start) if new_start else None
    next_end = _parse_time(new_end) if new_end else (_parse_time(slot_end) if slot_end else None)
    next_room = new_room_id or row[6]
    next_course = _find_course(cursor, new_subject) if new_subject else None

    next_course_info = next_course or _find_course(cursor, row[1])
    
    # Conflict checking for update
    cursor.execute(
        """
        SELECT t.room_id, c.professor_roll, t.student_group, t.id
        FROM timetable t
        JOIN courses c ON t.course_code = c.code
        WHERE t.timetable_day = %s
          AND t.slot_start < %s
          AND t.slot_end > %s
          AND t.id != %s
        """,
        (next_day or row[3], next_end or row[5], next_start or row[4], row[0])
    )
    conflicts = cursor.fetchall()
    for crow in conflicts:
        c_room, c_prof, c_group, c_id = crow
        if c_room.upper() == next_room.strip().upper():
            cursor.close()
            connection.close()
            return {"status": "error", "message": f"Room Conflict: Room {next_room} is already booked at this time.", "items": []}
        if next_course_info and next_course_info[3] and c_prof and c_prof.lower() == next_course_info[3].lower():
            cursor.close()
            connection.close()
            return {"status": "error", "message": f"Professor Conflict: Professor {next_course_info[3]} is already teaching a class at this time.", "items": []}
        if row[8] and c_group and c_group == row[8]: # row[8] is student_group from _get_slot
            cursor.close()
            connection.close()
            return {"status": "error", "message": f"Group Conflict: Student group {row[8]} is already in another class at this time.", "items": []}

    sets = []
    params: list = []
    if next_day:
        sets.append("timetable_day = %s")
        params.append(next_day)
    if next_start is not None:
        sets.append("slot_start = %s")
        params.append(next_start)
    if next_end is not None:
        sets.append("slot_end = %s")
        params.append(next_end)
    if next_room:
        sets.append("room_id = %s")
        params.append(next_room.strip().upper())
    if next_course is not None:
        sets.append("course_code = %s")
        params.append(next_course[0])

    if not sets:
        cursor.close()
        connection.close()
        return {"status": "error", "message": "No fields to update.", "items": []}

    params.append(row[0])
    cursor.execute(
        f"""
        UPDATE timetable
        SET {', '.join(sets)}
        WHERE id = %s
        RETURNING id, course_code, timetable_day, slot_start, slot_end, room_id, class_type, student_group
        """,
        params,
    )
    updated = cursor.fetchone()
    cursor.execute("SELECT name FROM courses WHERE code = %s", (updated[1],))
    name_row = cursor.fetchone()
    connection.commit()
    item = _serialize_row(
        updated[0],
        updated[1],
        name_row[0] if name_row else updated[1],
        updated[2],
        updated[3],
        updated[4],
        updated[5],
        updated[6],
        updated[7],
    )
    cursor.close()
    connection.close()
    _tt_cache.clear()
    return {
        "status": "success",
        "query_kind": "update",
        "slot_id": item["slot_id"],
        "items": [item],
        "message": "Slot updated.",
    }


def delete_slot(
    slot_id: str | None = None,
    subject: str | None = None,
    course_code: str | None = None,
    timetable_day: str | None = None,
    slot_start: str | None = None,
    professor_roll: str | None = None,
):
    day = normalize_day(timetable_day)
    start = _parse_time(slot_start)
    connection = get_connection()
    cursor = connection.cursor()
    course = _find_course(cursor, subject or course_code)
    row = _get_slot(
        cursor,
        slot_id=slot_id,
        day=day,
        start=start,
        course_code=course[0] if course else None,
    )
    if row is None:
        cursor.close()
        connection.close()
        return {"status": "not_found", "message": "slot not found", "items": []}

    cursor.execute("SELECT professor_roll FROM courses WHERE code = %s", (row[1],))
    owner = cursor.fetchone()
    if (
        professor_roll
        and owner
        and owner[0]
        and owner[0].lower() != str(professor_roll).lower()
    ):
        cursor.close()
        connection.close()
        return {
            "status": "error",
            "message": f"Course {row[1]} is owned by {owner[0]}, not {professor_roll}.",
            "items": [],
        }

    item = _serialize_row(*row)
    cursor.execute("DELETE FROM timetable WHERE id = %s", (row[0],))
    connection.commit()
    cursor.close()
    connection.close()
    _tt_cache.clear()
    return {
        "status": "success",
        "query_kind": "delete",
        "slot_id": item["slot_id"],
        "items": [item],
        "message": "Slot deleted.",
    }
