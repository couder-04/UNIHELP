"""Positive and negative cases for parse_notice_query. No DB/LLM."""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from fast_parse import parse_notice_query


NOW = "Friday, 2026-09-18 17:04:00 IST"


class TestParseNoticePositive:
    def test_show_todays_notices(self):
        assert parse_notice_query("Show today's notices.", NOW) == {"action": "view"}

    def test_show_current_notices(self):
        assert parse_notice_query("Show me the current notices", NOW) == {
            "action": "view"
        }

    def test_what_are_todays_notices(self):
        assert parse_notice_query("What are today's notices", NOW) == {"action": "view"}

    def test_active_notices(self):
        assert parse_notice_query("list active notices", NOW) == {"action": "view"}

    def test_notice_board(self):
        assert parse_notice_query("show the notice board", NOW) == {"action": "view"}


class TestParseNoticeNegative:
    def test_publish_intent(self):
        assert (
            parse_notice_query(
                "Publish a notice that CS101 lab is cancelled tomorrow",
                NOW,
            )
            is None
        )

    def test_archive_intent(self):
        assert parse_notice_query("Archive expired notices", NOW) is None

    def test_specific_notice_content(self):
        assert (
            parse_notice_query(
                "Can you explain what this notice about the fest means?",
                NOW,
            )
            is None
        )

    def test_notice_about_topic(self):
        assert parse_notice_query("What does the notice about the fest say?", NOW) is None
