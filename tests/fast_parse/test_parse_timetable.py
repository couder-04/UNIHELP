"""Positive and negative cases for parse_timetable_query. No DB/LLM."""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from fast_parse import parse_timetable_query


NOW = "Friday, 2026-09-18 17:04:00 IST"
USER_META = {
    "role": "student",
    "name": "Test Student",
    "roll_number": "2501CS00",
    "Time and Date": NOW,
}


class TestParseTimetablePositive:
    def test_today(self):
        out = parse_timetable_query(
            "what classes do I have today", NOW, USER_META
        )
        assert out == {
            "target_id": "2501CS00",
            "target_type": "student",
            "timetable_day": "Friday",
        }

    def test_tomorrow(self):
        out = parse_timetable_query(
            "what classes do I have tomorrow", NOW, USER_META
        )
        assert out["timetable_day"] == "Saturday"
        assert out["target_id"] == "2501CS00"

    def test_tonight(self):
        out = parse_timetable_query(
            "what classes do I have tonight", NOW, USER_META
        )
        assert out["timetable_day"] == "Friday"

    def test_explicit_weekday(self):
        out = parse_timetable_query(
            "what classes do I have on Monday", NOW, USER_META
        )
        assert out["timetable_day"] == "Monday"

    def test_explicit_iso_date(self):
        out = parse_timetable_query(
            "what classes do I have on 2026-09-20", NOW, USER_META
        )
        assert out["timetable_day"] == "Sunday"

    def test_classes_for_me(self):
        out = parse_timetable_query("today's classes for me", NOW, USER_META)
        assert out["target_id"] == "2501CS00"
        assert out["timetable_day"] == "Friday"

    def test_roll_num_alias_in_metadata(self):
        meta = {
            "role": "faculty",
            "name": "Prof",
            "roll_num": "PF001",
            "Time and Date": NOW,
        }
        out = parse_timetable_query("my classes tomorrow", NOW, meta)
        assert out["target_id"] == "PF001"
        assert out["target_type"] == "faculty"
        assert out["timetable_day"] == "Saturday"


class TestParseTimetableNegative:
    def test_someone_elses_roll(self):
        assert (
            parse_timetable_query(
                "what classes does 2501CS99 have today",
                NOW,
                USER_META,
            )
            is None
        )

    def test_next_class(self):
        assert (
            parse_timetable_query("what is my next class", NOW, USER_META)
            is None
        )

    def test_full_week(self):
        assert (
            parse_timetable_query(
                "what classes do I have this week",
                NOW,
                USER_META,
            )
            is None
        )

    def test_no_day_is_week_view(self):
        assert (
            parse_timetable_query("what classes do I have", NOW, USER_META)
            is None
        )

    def test_free_slots(self):
        assert (
            parse_timetable_query(
                "when am I free today",
                NOW,
                USER_META,
            )
            is None
        )

    def test_course_lookup(self):
        assert (
            parse_timetable_query(
                "when is my CS101 class today",
                NOW,
                USER_META,
            )
            is None
        )

    def test_write_intent(self):
        assert (
            parse_timetable_query(
                "add a slot for my class on Monday",
                NOW,
                USER_META,
            )
            is None
        )

    def test_garbled_date(self):
        assert (
            parse_timetable_query(
                "what classes do I have on 2026-13-45",
                NOW,
                USER_META,
            )
            is None
        )
