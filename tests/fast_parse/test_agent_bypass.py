"""Agent chat() uses the LLM path only when the parser returns None."""

from __future__ import annotations

import sys
from pathlib import Path

from types import SimpleNamespace

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

NOW = "Friday, 2026-09-18 17:04:00 IST"
USER_META = {
    "role": "student",
    "name": "Test Student",
    "roll_number": "2501CS00",
    "Time and Date": NOW,
}


def fake_chat_response(content="llm reply"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, tool_calls=None)
            )
        ]
    )


PARSED_MESS = {
    "hostel": "Kalam",
    "meal": "dinner",
    "date": "2026-09-18",
    "weekly": False,
}
MESS_RESULT = {
    "status": "success",
    "hostel": "Kalam",
    "date": "2026-09-18",
    "day": "Friday",
    "menu": {
        "breakfast": "Poha",
        "lunch": "Dal",
        "snacks": "Samosa",
        "dinner": "Paneer",
        "dessert": None,
    },
}

PARSED_BUS = {
    "route_name": "Bus 02",
    "day": "Saturday",
    "date": "2026-09-19",
}
BUS_RESULT = [
    {
        "departure_time": "08:00",
        "start_point": "Aryabhatta",
        "destination": "Tut Block",
    }
]

PARSED_TT = {
    "target_id": "2501CS00",
    "target_type": "student",
    "timetable_day": "Friday",
}
TT_RESULT = {
    "status": "success",
    "items": [
        {
            "timetable_day": "Friday",
            "timetable_slot": "10:00:00-11:00:00",
            "slot_start": "10:00:00",
            "slot_end": "11:00:00",
            "course_code": "CS101",
            "course_name": "Algorithms",
            "room_id": "B204",
        }
    ],
}


def _raise_if_llm_called(*args, **kwargs):
    raise AssertionError("chat_create should not be called")


class TestMessAgentBypass:
    def test_parser_none_reaches_llm(self, monkeypatch):
        import mess_agent_1

        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("llm mess reply")

        monkeypatch.setattr(mess_agent_1, "parse_mess_query", lambda *a, **k: None)
        monkeypatch.setattr(mess_agent_1, "chat_create", fake_chat_create)

        agent = mess_agent_1.MessAgent()
        result = agent.chat("unclear mess question", USER_META)

        assert result == "llm mess reply"
        assert len(llm_calls) == 1

    def test_parser_hit_skips_llm(self, monkeypatch):
        import mess_agent_1

        monkeypatch.setattr(
            mess_agent_1, "parse_mess_query", lambda *a, **k: dict(PARSED_MESS)
        )
        monkeypatch.setattr(mess_agent_1, "get_menu", lambda *a, **k: dict(MESS_RESULT))
        monkeypatch.setattr(mess_agent_1, "chat_create", _raise_if_llm_called)

        agent = mess_agent_1.MessAgent()
        result = agent.chat("today's dinner at Kalam", USER_META)

        assert "Paneer" in result
        assert "Dinner" in result


class TestBusAgentBypass:
    def test_parser_none_reaches_llm(self, monkeypatch):
        import Bus_agent

        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("llm bus reply")

        monkeypatch.setattr(Bus_agent, "parse_bus_query", lambda *a, **k: None)
        monkeypatch.setattr(Bus_agent, "chat_create", fake_chat_create)

        agent = Bus_agent.BusAgent()
        result = agent.chat("unclear bus question", USER_META)

        assert result == "llm bus reply"
        assert len(llm_calls) == 1

    def test_parser_hit_skips_llm(self, monkeypatch):
        import Bus_agent

        monkeypatch.setattr(
            Bus_agent, "parse_bus_query", lambda *a, **k: dict(PARSED_BUS)
        )
        monkeypatch.setattr(
            Bus_agent, "query_schedule", lambda *a, **k: list(BUS_RESULT)
        )
        monkeypatch.setattr(Bus_agent, "chat_create", _raise_if_llm_called)

        agent = Bus_agent.BusAgent()
        result = agent.chat("Bus 02 schedule tomorrow", USER_META)

        assert "Bus 02" in result
        assert "08:00" in result


class TestTimetableAgentBypass:
    def test_parser_none_reaches_llm(self, monkeypatch):
        import timetable_agent

        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("llm timetable reply")

        monkeypatch.setattr(
            timetable_agent, "parse_timetable_query", lambda *a, **k: None
        )
        monkeypatch.setattr(timetable_agent, "chat_create", fake_chat_create)

        agent = timetable_agent.TimetableAgent()
        result = agent.chat("unclear timetable question", USER_META)

        assert result == "llm timetable reply"
        assert len(llm_calls) == 1

    def test_parser_hit_skips_llm(self, monkeypatch):
        import timetable_agent

        monkeypatch.setattr(
            timetable_agent,
            "parse_timetable_query",
            lambda *a, **k: dict(PARSED_TT),
        )
        monkeypatch.setattr(
            timetable_agent.timetable_fns,
            "get_schedule",
            lambda *a, **k: dict(TT_RESULT),
        )
        monkeypatch.setattr(timetable_agent, "chat_create", _raise_if_llm_called)

        agent = timetable_agent.TimetableAgent()
        result = agent.chat("what classes do I have today", USER_META)

        assert "CS101" in result
        assert "B204" in result


class TestNoticeAgentBypass:
    def test_parser_none_reaches_llm(self, monkeypatch):
        import Notice_agent

        llm_calls = []

        def fake_chat_create(**kwargs):
            llm_calls.append(kwargs)
            return fake_chat_response("llm notice reply")

        monkeypatch.setattr(Notice_agent, "parse_notice_query", lambda *a, **k: None)
        monkeypatch.setattr(Notice_agent, "chat_create", fake_chat_create)

        agent = Notice_agent.NoticeAgent()
        result = agent.chat("unclear notice question", USER_META)

        assert result == "llm notice reply"
        assert len(llm_calls) == 1

    def test_parser_hit_skips_llm(self, monkeypatch):
        import Notice_agent

        rows = [
            {
                "notice_type": "General",
                "publish_timestamp": "2026-09-18 10:00:00",
                "author_id": "PF001",
                "content": "Fest this weekend",
            }
        ]
        monkeypatch.setattr(
            Notice_agent, "parse_notice_query", lambda *a, **k: {"action": "view"}
        )
        monkeypatch.setattr(Notice_agent, "view_notices", lambda *a, **k: rows)
        monkeypatch.setattr(Notice_agent, "chat_create", _raise_if_llm_called)

        agent = Notice_agent.NoticeAgent()
        result = agent.chat("Show today's notices.", USER_META)

        assert "Fest this weekend" in result
        assert "Active Notices" in result
