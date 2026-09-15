"""Hardcore coverage for the standalone attendance agent tools + guards.

Uses isolated HXTEST campus fixtures (see conftest.py). Does not call the LLM.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import attendance_agent  # noqa: E402
import attendance_functions as T  # noqa: E402


# ---------------------------------------------------------------------------
# Pure math / helpers
# ---------------------------------------------------------------------------


class TestSkipBudgetMath:
    def test_healthy_budget(self):
        # 8/10 present, 30 remaining of 40 planned, 75% threshold
        out = T.skip_budget(8, 10, 40, 75)
        assert out["attendance_percent"] == 80.0
        assert out["can_skip"] == out["skip_budget"]
        assert out["can_skip"] + out["must_attend"] == out["remaining_sessions"]
        assert out["below_threshold"] is False

    def test_already_below(self):
        out = T.skip_budget(1, 10, 40, 75)
        assert out["below_threshold"] is True
        assert out["attendance_percent"] == 10.0

    def test_zero_sessions(self):
        out = T.skip_budget(0, 0, 40, 75)
        assert out["attendance_percent"] is None
        assert out["remaining_sessions"] == 40
        assert out["can_skip"] >= 0

    def test_planned_exhausted(self):
        out = T.skip_budget(30, 40, 40, 75)
        assert out["remaining_sessions"] == 0
        assert out["can_skip"] == 0

    def test_threshold_clamped(self):
        out = T.skip_budget(5, 5, 10, 150)
        assert out["threshold_percent"] == 150
        # internal math clamps to 100%
        assert out["must_attend"] == out["remaining_sessions"]

    def test_late_and_excused_count_present(self):
        assert T._counts_as_present("present")
        assert T._counts_as_present("late")
        assert T._counts_as_present("excused")
        assert not T._counts_as_present("absent")


class TestStatusNormalization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("present", "present"),
            ("P", "present"),
            ("yes", "present"),
            ("attended", "present"),
            ("absent", "absent"),
            ("A", "absent"),
            ("missed", "absent"),
            ("late", "late"),
            ("tardy", "late"),
            ("excused", "excused"),
            ("medical", "excused"),
            ("leave", "excused"),
            ("bogus", None),
            ("", None),
        ],
    )
    def test_aliases(self, raw, expected):
        assert T._norm_status(raw if raw != "" else None, default="") == expected


class TestDateParsing:
    def test_iso_string(self):
        assert T._as_date("2026-09-13") == date(2026, 9, 13)

    def test_datetime_truncates(self):
        from datetime import datetime

        assert T._as_date(datetime(2026, 1, 2, 15, 30)) == date(2026, 1, 2)

    def test_none(self):
        assert T._as_date(None) is None

    def test_garbage(self):
        with pytest.raises(ValueError):
            T._as_date("not-a-date")


# ---------------------------------------------------------------------------
# Agent role / identity guards (no LLM)
# ---------------------------------------------------------------------------


class TestAgentGuards:
    def test_role_aliases(self):
        assert attendance_agent._normalize_role("professor") == "faculty"
        assert attendance_agent._normalize_role("Teacher") == "faculty"
        assert attendance_agent._normalize_role("administrator") == "admin"

    def test_bad_role(self):
        with pytest.raises(ValueError):
            attendance_agent._normalize_role("guest")

    def test_student_forced_identity(self):
        args = attendance_agent._enforce_identity(
            "student",
            {"roll_num": "HXTEST-S-A", "name": "A", "role": "student"},
            "get_attendance_summary",
            {"student_id": "HXTEST-S-B"},
        )
        assert args["student_id"] == "HXTEST-S-A"

    def test_student_cannot_mark(self):
        with pytest.raises(PermissionError):
            attendance_agent._enforce_identity(
                "student",
                {"roll_num": "HXTEST-S-A", "name": "A", "role": "student"},
                "mark_attendance",
                {},
            )

    def test_student_denied_faculty_tool(self):
        with pytest.raises(PermissionError):
            attendance_agent._enforce_identity(
                "student",
                {"roll_num": "HXTEST-S-A", "name": "A", "role": "student"},
                "get_course_attendance",
                {"course_code": "X"},
            )

    def test_faculty_injects_professor_id(self):
        args = attendance_agent._enforce_identity(
            "faculty",
            {"roll_num": "HXTEST-E-OWN", "name": "P", "role": "faculty"},
            "mark_attendance",
            {"professor_id": "HXTEST-E-OTH", "student_id": "X"},
        )
        assert args["professor_id"] == "HXTEST-E-OWN"

    def test_faculty_list_courses_defaults_owned(self):
        args = attendance_agent._enforce_identity(
            "faculty",
            {"roll_num": "HXTEST-E-OWN", "name": "P", "role": "faculty"},
            "list_courses",
            {},
        )
        assert args["professor_id"] == "HXTEST-E-OWN"

    def test_faculty_list_courses_keeps_student_query(self):
        args = attendance_agent._enforce_identity(
            "faculty",
            {"roll_num": "HXTEST-E-OWN", "name": "P", "role": "faculty"},
            "list_courses",
            {"student_id": "HXTEST-S-A"},
        )
        assert args["student_id"] == "HXTEST-S-A"
        assert "professor_id" not in args

    def test_all_impls_have_schemas(self):
        for name in attendance_agent.TOOL_IMPL:
            assert name in attendance_agent.TOOL_SCHEMAS

    def test_role_tools_subset_of_impl(self):
        for role, tools in attendance_agent.ROLE_TOOLS.items():
            missing = tools - set(attendance_agent.TOOL_IMPL)
            assert not missing, f"{role} missing impls: {missing}"

    def test_openai_tool_list_for_student_excludes_writes(self):
        names = {
            t["function"]["name"]
            for t in attendance_agent._openai_tools_for_role("student")
        }
        assert "mark_attendance" not in names
        assert "get_attendance_summary" in names
        assert "list_courses" in names
        assert "get_attendance_chart" in names


# ---------------------------------------------------------------------------
# Discovery tools
# ---------------------------------------------------------------------------


class TestDiscovery:
    def test_resolve_by_code(self, campus):
        out = T.resolve_course(course_code=campus["course_a"])
        assert out["status"] == "success"
        assert out["course"]["course_code"] == campus["course_a"]

    def test_resolve_by_id(self, campus):
        out = T.resolve_course(course_id=campus["course_a_id"])
        assert out["status"] == "success"
        assert out["course"]["course_code"] == campus["course_a"]

    def test_resolve_by_name(self, campus):
        out = T.resolve_course(course_name="HX Algorithms")
        assert out["status"] == "success"
        assert out["course"]["course_code"] == campus["course_a"]

    def test_resolve_space_insensitive(self, campus):
        spaced = campus["course_a"][:2] + " " + campus["course_a"][2:]
        out = T.resolve_course(course_code=spaced)
        assert out["status"] == "success"

    def test_resolve_missing(self):
        out = T.resolve_course(course_code="NOPE999")
        assert out["status"] == "not_found"

    def test_list_courses_student(self, campus):
        out = T.list_courses(student_id=campus["student_a"])
        assert out["status"] == "success"
        codes = {c["course_code"] for c in out["courses"]}
        assert campus["course_a"] in codes
        assert campus["course_b"] in codes
        assert campus["course_other"] not in codes

    def test_list_courses_professor(self, campus):
        out = T.list_courses(professor_id=campus["prof_owner"])
        codes = {c["course_code"] for c in out["courses"]}
        assert campus["course_a"] in codes
        assert campus["course_b"] in codes
        assert campus["course_other"] not in codes

    def test_list_roster(self, campus):
        out = T.list_roster(course_code=campus["course_a"])
        assert out["status"] == "success"
        ids = {r["student_roll"] for r in out["roster"]}
        assert ids == {campus["student_a"], campus["student_b"]}

    def test_list_roster_missing_course(self):
        out = T.list_roster(course_code="ZZZ0")
        assert out["status"] == "not_found"


# ---------------------------------------------------------------------------
# Student read path
# ---------------------------------------------------------------------------


class TestStudentReads:
    def test_get_attendance_all(self, campus):
        out = T.get_attendance(campus["student_a"], campus["course_a"])
        assert out["status"] == "success"
        assert len(out["records"]) == 6

    def test_get_attendance_one_day(self, campus):
        day = campus["sessions"][0]
        out = T.get_attendance(
            campus["student_a"], campus["course_a"], session_date=day
        )
        assert out["status"] == "success"
        assert out["attendance_status"] == "present"

    def test_get_attendance_range(self, campus):
        out = T.get_attendance(
            campus["student_a"],
            campus["course_a"],
            date_from=campus["sessions"][2],
            date_to=campus["sessions"][4],
        )
        assert out["status"] == "success"
        assert len(out["records"]) == 3
        assert all(r["attendance_status"] == "absent" for r in out["records"])

    def test_get_attendance_not_found(self, campus):
        out = T.get_attendance(campus["student_c"], campus["course_a"])
        assert out["status"] == "not_found"

    def test_weekly_empty_far_future(self, campus):
        out = T.get_weekly_attendance(
            campus["student_a"], week_start="2099-01-05"
        )
        assert out["status"] == "not_found"

    def test_weekly_with_known_week(self, campus):
        start = date.fromisoformat(campus["sessions"][0])
        monday = start - timedelta(days=start.weekday())
        out = T.get_weekly_attendance(campus["student_a"], week_start=str(monday))
        assert out["status"] == "success"
        assert out["records"]

    def test_summary_all_courses(self, campus):
        out = T.get_attendance_summary(campus["student_a"])
        assert out["status"] == "success"
        codes = {s["course_code"] for s in out["summaries"]}
        assert campus["course_a"] in codes
        assert campus["course_b"] in codes

    def test_summary_one_course(self, campus):
        out = T.get_attendance_summary(
            campus["student_a"], course_code=campus["course_a"]
        )
        assert out["status"] == "success"
        assert len(out["summaries"]) == 1
        s = out["summaries"][0]
        assert s["present_count"] == 3
        assert s["absent_count"] == 3
        assert s["attendance_percent"] == 50.0
        assert s["below_threshold"] is True

    def test_skip_budget(self, campus):
        out = T.get_skip_budget(campus["student_a"], campus["course_a"])
        assert out["status"] == "success"
        assert out["below_threshold"] is True
        assert "can_skip" in out

    def test_monthly(self, campus):
        d = date.fromisoformat(campus["sessions"][0])
        out = T.get_monthly_attendance(
            campus["student_a"], d.year, d.month, course_code=campus["course_a"]
        )
        assert out["status"] == "success"
        assert out["view"] == "monthly"

    def test_semester(self, campus):
        out = T.get_semester_attendance(
            campus["student_a"],
            campus["sessions"][0],
            campus["sessions"][-1],
            course_code=campus["course_a"],
        )
        assert out["status"] == "success"
        assert out["view"] == "semester"
        assert len(out["records"]) == 6

    def test_semester_bad_dates(self, campus):
        out = T.get_semester_attendance(campus["student_a"], None, None)
        assert out["status"] == "error"

    def test_consecutive_absences(self, campus):
        out = T.get_consecutive_absences(
            campus["student_a"], course_code=campus["course_a"], min_streak=3
        )
        assert out["status"] == "success"
        assert any(s["streak_length"] >= 3 for s in out["streaks"])

    def test_consecutive_absences_high_threshold(self, campus):
        out = T.get_consecutive_absences(
            campus["student_a"], course_code=campus["course_a"], min_streak=10
        )
        assert out["streaks"] == []

    def test_attendance_chart(self, campus):
        out = T.get_attendance_chart(
            campus["student_a"],
            course_code=campus["course_a"],
            date_from=campus["sessions"][0],
            date_to=campus["sessions"][-1],
        )
        assert out["status"] == "success"
        assert out["view"] == "chart"
        assert out["point_count"] == 6
        assert out["chart"]

    def test_today_student_no_mark(self, campus):
        # today is intentionally unmarked for HXTEST courses
        out = T.get_today_attendance(student_id=campus["student_a"])
        assert out["status"] in {"not_found", "success"}


# ---------------------------------------------------------------------------
# Faculty / course reads
# ---------------------------------------------------------------------------


class TestFacultyReads:
    def test_course_attendance_all(self, campus):
        out = T.get_course_attendance(campus["course_a"])
        assert out["status"] == "success"
        assert len(out["records"]) == 12  # 6 days * 2 students

    def test_course_attendance_session_roster(self, campus):
        out = T.get_course_attendance(
            campus["course_a"], session_date=campus["sessions"][0]
        )
        assert out["status"] == "success"
        assert out["present_count"] == 2
        assert out["unmarked_count"] == 0
        assert len(out["roster"]) == 2

    def test_course_summary_at_risk(self, campus):
        out = T.get_course_attendance_summary(campus["course_a"])
        assert out["status"] == "success"
        assert campus["student_a"] in out["at_risk_students"]
        assert campus["student_b"] not in out["at_risk_students"]

    def test_at_risk_by_professor(self, campus):
        out = T.get_at_risk_students(professor_id=campus["prof_owner"])
        assert out["status"] == "success"
        ids = {s["student_roll"] for s in out["students"]}
        assert campus["student_a"] in ids

    def test_at_risk_bad_professor(self):
        out = T.get_at_risk_students(professor_id="NO-SUCH-PROF")
        assert out["status"] == "error"

    def test_list_sessions(self, campus):
        out = T.list_course_sessions(course_code=campus["course_a"])
        assert out["status"] == "success"
        assert out["session_count"] == 6

    def test_rank(self, campus):
        out = T.rank_course_attendance(course_code=campus["course_a"])
        assert out["status"] == "success"
        assert out["ranked"][0]["student_roll"] == campus["student_b"]
        assert out["ranked"][0]["rank"] == 1

    def test_export_csv(self, campus):
        out = T.export_course_attendance_csv(
            course_code=campus["course_a"], session_date=campus["sessions"][0]
        )
        assert out["status"] == "success"
        assert "student_roll,student_name,session_date,attendance_status" in out["csv"]
        assert campus["student_a"] in out["csv"]

    def test_unmarked_after_partial(self, campus):
        # Before any mark on write_date, both enrolled are unmarked
        out = T.get_unmarked_students(
            campus["write_date"], course_code=campus["course_a"]
        )
        assert out["status"] == "success"
        assert out["unmarked_count"] == 2


# ---------------------------------------------------------------------------
# Writes: mark / edit / delete + ownership + enrollment gates
# ---------------------------------------------------------------------------


class TestWrites:
    def test_mark_one_present(self, campus):
        out = T.mark_attendance(
            campus["student_a"],
            campus["course_a"],
            campus["write_date"],
            "present",
            campus["prof_owner"],
        )
        assert out["status"] == "success"
        assert out["attendance_status"] == "present"

        again = T.get_attendance(
            campus["student_a"],
            campus["course_a"],
            session_date=campus["write_date"],
        )
        assert again["attendance_status"] == "present"

    def test_mark_status_aliases(self, campus):
        day = str(date.fromisoformat(campus["write_date"]) + timedelta(days=1))
        out = T.mark_attendance(
            campus["student_a"],
            campus["course_a"],
            day,
            "tardy",
            campus["prof_owner"],
        )
        assert out["status"] == "success"
        assert out["attendance_status"] == "late"

    def test_mark_invalid_status(self, campus):
        out = T.mark_attendance(
            campus["student_a"],
            campus["course_a"],
            campus["write_date"],
            "sleeping",
            campus["prof_owner"],
        )
        assert out["status"] == "error"

    def test_mark_non_professor(self, campus):
        out = T.mark_attendance(
            campus["student_a"],
            campus["course_a"],
            campus["write_date"],
            "present",
            "NOT-A-PROF",
        )
        assert out["status"] == "error"
        assert "faculty" in out["message"].lower() or "professor" in out["message"].lower()

    def test_mark_wrong_owner(self, campus):
        out = T.mark_attendance(
            campus["student_a"],
            campus["course_a"],
            campus["write_date"],
            "absent",
            campus["prof_other"],
        )
        assert out["status"] == "error"
        assert "own" in out["message"].lower()

    def test_mark_not_enrolled(self, campus):
        out = T.mark_attendance(
            campus["student_c"],
            campus["course_a"],
            campus["write_date"],
            "present",
            campus["prof_owner"],
        )
        assert out["status"] == "error"
        assert "not enrolled" in out["message"].lower()

    def test_mark_unknown_student(self, campus):
        out = T.mark_attendance(
            "HXTEST-S-ZZZ",
            campus["course_a"],
            campus["write_date"],
            "present",
            campus["prof_owner"],
        )
        assert out["status"] == "not_found"

    def test_mark_unknown_course(self, campus):
        out = T.mark_attendance(
            campus["student_a"],
            "NOPE101",
            campus["write_date"],
            "present",
            campus["prof_owner"],
        )
        assert out["status"] == "not_found"

    def test_mark_students_set_with_overrides(self, campus):
        day = str(date.fromisoformat(campus["write_date"]) + timedelta(days=2))
        out = T.mark_students_attendance(
            [campus["student_a"], campus["student_b"], campus["student_c"]],
            day,
            campus["course_a"],
            campus["prof_owner"],
            attendance_status="present",
            status_by_student={campus["student_b"]: "absent"},
        )
        assert out["status"] == "success"
        assert out["marked_count"] == 2
        assert out["skipped_count"] == 1
        statuses = {m["student_roll"]: m["attendance_status"] for m in out["marked"]}
        assert statuses[campus["student_a"]] == "present"
        assert statuses[campus["student_b"]] == "absent"
        assert out["skipped"][0]["reason"] == "not_enrolled"

    def test_mark_students_empty(self, campus):
        out = T.mark_students_attendance(
            [],
            campus["write_date"],
            campus["course_a"],
            campus["prof_owner"],
        )
        assert out["status"] == "error"

    def test_mark_class_default_absent_overrides(self, campus):
        day = str(date.fromisoformat(campus["write_date"]) + timedelta(days=3))
        out = T.mark_class_attendance(
            campus["course_a"],
            day,
            campus["prof_owner"],
            default_status="absent",
            present_numbers=[campus["student_a"]],
        )
        assert out["status"] == "success"
        assert out["marked_count"] == 2
        statuses = {m["student_roll"]: m["attendance_status"] for m in out["marked"]}
        assert statuses[campus["student_a"]] == "present"
        assert statuses[campus["student_b"]] == "absent"

        unmarked = T.get_unmarked_students(day, course_code=campus["course_a"])
        assert unmarked["unmarked_count"] == 0

    def test_edit_then_delete(self, campus):
        day = str(date.fromisoformat(campus["write_date"]) + timedelta(days=4))
        marked = T.mark_attendance(
            campus["student_a"],
            campus["course_a"],
            day,
            "present",
            campus["prof_owner"],
            course_id=campus["course_a_id"],
        )
        assert marked["status"] == "success"

        edited = T.edit_attendance(
            campus["student_a"],
            campus["course_a_id"],
            day,
            "excused",
            campus["prof_owner"],
            course_code=campus["course_a"],
        )
        assert edited["status"] == "success"
        assert edited["attendance_status"] == "excused"

        deleted = T.delete_attendance(
            campus["student_a"],
            campus["course_a_id"],
            day,
            campus["prof_owner"],
            course_code=campus["course_a"],
        )
        assert deleted["status"] == "success"

        missing = T.get_attendance(
            campus["student_a"], campus["course_a"], session_date=day
        )
        assert missing["status"] == "not_found"

    def test_delete_missing(self, campus):
        out = T.delete_attendance(
            campus["student_a"],
            campus["course_a_id"],
            "2099-01-01",
            campus["prof_owner"],
        )
        assert out["status"] == "not_found"

    def test_upsert_idempotent(self, campus):
        day = str(date.fromisoformat(campus["write_date"]) + timedelta(days=5))
        first = T.mark_attendance(
            campus["student_a"],
            campus["course_a"],
            day,
            "present",
            campus["prof_owner"],
        )
        second = T.mark_attendance(
            campus["student_a"],
            campus["course_a"],
            day,
            "absent",
            campus["prof_owner"],
        )
        assert first["status"] == second["status"] == "success"
        check = T.get_attendance(
            campus["student_a"], campus["course_a"], session_date=day
        )
        assert check["attendance_status"] == "absent"


# ---------------------------------------------------------------------------
# End-to-end tool dispatch through agent._call_tool
# ---------------------------------------------------------------------------


class TestAgentDispatch:
    def test_call_known_tool(self, campus):
        result = attendance_agent._call_tool(
            "get_skip_budget",
            {
                "student_id": campus["student_a"],
                "course_code": campus["course_a"],
            },
        )
        assert result["status"] == "success"

    def test_call_unknown_tool(self):
        result = attendance_agent._call_tool("drop_table", {})
        assert result["status"] == "error"

    def test_call_bad_args(self):
        result = attendance_agent._call_tool("get_attendance", {})
        assert result["status"] == "error"

    def test_student_pipeline_forces_id(self, campus):
        args = attendance_agent._enforce_identity(
            "student",
            {
                "role": "student",
                "name": "HX Student A",
                "roll_num": campus["student_a"],
            },
            "get_attendance_chart",
            {"student_id": campus["student_b"], "course_code": campus["course_a"]},
        )
        result = attendance_agent._call_tool("get_attendance_chart", args)
        assert result["status"] == "success"
        assert result["student_roll"] == campus["student_a"]
