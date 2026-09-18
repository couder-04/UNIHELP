"""Positive and negative cases for parse_mess_query. No DB/LLM."""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from fast_parse import parse_mess_query


NOW = "Friday, 2026-09-18 17:04:00 IST"


class TestParseMessPositive:
    def test_today(self):
        out = parse_mess_query("What is today's dinner at Kalam?", NOW)
        assert out == {
            "hostel": "Kalam",
            "meal": "dinner",
            "date": "2026-09-18",
            "weekly": False,
        }

    def test_tomorrow(self):
        out = parse_mess_query("What's tomorrow's lunch at Asima", NOW)
        assert out["hostel"] == "Asima"
        assert out["meal"] == "lunch"
        assert out["date"] == "2026-09-19"
        assert out["weekly"] is False

    def test_tonight(self):
        out = parse_mess_query("tonight's menu at Kalam", NOW)
        assert out["hostel"] == "Kalam"
        assert out["meal"] is None
        assert out["date"] == "2026-09-18"

    def test_explicit_weekday(self):
        out = parse_mess_query("Monday breakfast at Aryabhatta", NOW)
        assert out["hostel"] == "Aryabhatta"
        assert out["meal"] == "breakfast"
        assert out["date"] == "2026-09-21"

    def test_explicit_iso_date(self):
        out = parse_mess_query("Kalam snacks on 2026-09-20", NOW)
        assert out["hostel"] == "Kalam"
        assert out["meal"] == "snacks"
        assert out["date"] == "2026-09-20"

    def test_hostel_alias_cv_raman(self):
        out = parse_mess_query("today's menu at c v raman", NOW)
        assert out["hostel"] == "CV Raman"
        assert out["meal"] is None
        assert out["date"] == "2026-09-18"

    def test_full_day_when_no_meal_named(self):
        out = parse_mess_query("today's menu at Kalam", NOW)
        assert out["meal"] is None
        assert out["weekly"] is False

    def test_weekly_menu(self):
        out = parse_mess_query("show me the weekly menu for Kalam", NOW)
        assert out["hostel"] == "Kalam"
        assert out["meal"] is None
        assert out["weekly"] is True
        assert out["date"] == "2026-09-18"

    def test_schedule_without_day_is_weekly(self):
        out = parse_mess_query("Show me the mess schedule for Kalam", NOW)
        assert out["hostel"] == "Kalam"
        assert out["meal"] is None
        assert out["weekly"] is True

    def test_schedule_with_day_is_daily(self):
        out = parse_mess_query("What's tomorrow's mess schedule at Kalam?", NOW)
        assert out["hostel"] == "Kalam"
        assert out["meal"] is None
        assert out["weekly"] is False
        assert out["date"] == "2026-09-19"


class TestParseMessNegative:
    def test_ambiguous_schedule_wording(self):
        assert (
            parse_mess_query(
                "What's the mess schedule for dinner tonight at Kalam?",
                NOW,
            )
            is None
        )

    def test_write_intent(self):
        assert (
            parse_mess_query(
                "change Monday's dinner at Kalam to Paneer",
                NOW,
            )
            is None
        )

    def test_missing_hostel(self):
        out = parse_mess_query("What is today's dinner?", NOW)
        assert out is not None
        assert out["need_hostel"] is True
        assert out["meal"] == "dinner"
        assert out["hostel"] is None

    def test_todays_mess_menu_asks_hostel(self):
        out = parse_mess_query("today's mess menu", NOW)
        assert out is not None
        assert out["need_hostel"] is True
        assert out["meal"] is None

    def test_aryabhatta_hostel_word(self):
        out = parse_mess_query(
            "What is today's dinner at aryabhatta hostel?", NOW
        )
        assert out["hostel"] == "Aryabhatta"
        assert out["meal"] == "dinner"

    def test_unrecognized_hostel(self):
        out = parse_mess_query("today's dinner at Hogwarts", NOW)
        assert out is not None
        assert out["need_hostel"] is True

    def test_garbled_date(self):
        assert parse_mess_query("Kalam dinner on 2026-13-45", NOW) is None

    def test_meal_timing_not_menu(self):
        assert parse_mess_query("what time is dinner at Kalam", NOW) is None
