"""Positive and negative cases for parse_attendance_query. No DB/LLM."""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from fast_parse import format_attendance_reply, parse_attendance_query


USER_META = {
    "role": "student",
    "name": "Aarav Sharma",
    "roll_number": "2501CS09",
}


class TestParseAttendancePositive:
    def test_percentage_in_course(self):
        out = parse_attendance_query(
            "What is my attendance percentage in CS101?", USER_META
        )
        assert out == {"student_id": "2501CS09", "course_code": "CS101"}

    def test_lowercase_course_code(self):
        out = parse_attendance_query("attendance in cs101", USER_META)
        assert out["course_code"] == "CS101"

    def test_skip_budget(self):
        out = parse_attendance_query("CS101 skip budget", USER_META)
        assert out == {"student_id": "2501CS09", "course_code": "CS101"}

    def test_all_courses(self):
        out = parse_attendance_query("what is my attendance", USER_META)
        assert out == {"student_id": "2501CS09", "course_code": None}

    def test_roll_num_alias(self):
        meta = {"role": "student", "name": "Aarav", "roll_num": "2501CS09"}
        out = parse_attendance_query("my attendance in CS101", meta)
        assert out["student_id"] == "2501CS09"


class TestParseAttendanceNegative:
    def test_faculty_falls_through(self):
        meta = {"role": "faculty", "name": "Priya", "roll_number": "PF001"}
        assert parse_attendance_query("attendance in CS101", meta) is None

    def test_mark_attendance(self):
        assert (
            parse_attendance_query("mark attendance for CS101", USER_META)
            is None
        )

    def test_today_session(self):
        assert (
            parse_attendance_query("today's attendance in CS101", USER_META)
            is None
        )

    def test_chart(self):
        assert parse_attendance_query("CS101 attendance chart", USER_META) is None

    def test_two_courses(self):
        assert (
            parse_attendance_query("attendance in CS101 and CS102", USER_META)
            is None
        )

    def test_someone_elses_roll(self):
        assert (
            parse_attendance_query(
                "attendance for 2501CS99 in CS101", USER_META
            )
            is None
        )


class TestFormatAttendanceReply:
    def test_one_course_summary(self):
        parsed = {"student_id": "2501CS09", "course_code": "CS101"}
        result = {
            "status": "success",
            "summaries": [
                {
                    "course_code": "CS101",
                    "course_name": "Algorithms",
                    "attendance_percent": 91.67,
                    "present_count": 11,
                    "absent_count": 1,
                    "total_sessions": 12,
                    "can_skip": 9,
                    "must_attend": 19,
                    "remaining_sessions": 28,
                    "threshold_percent": 75,
                }
            ],
        }
        text = format_attendance_reply(parsed, result, name="Aarav")
        assert "CS101 (Algorithms)" in text
        assert "91.67%" in text
        assert "11 out of 12" in text
        assert "Skip budget: 9" in text
        assert "Aarav" in text
