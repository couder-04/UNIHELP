"""Positive and negative cases for parse_bus_query. No DB/LLM."""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from fast_parse import parse_bus_query


NOW = "Friday, 2026-09-18 17:04:00 IST"


class TestParseBusPositive:
    def test_today(self):
        out = parse_bus_query("Bus 02 schedule today", NOW)
        assert out == {
            "route_name": "Bus 02",
            "day": "Friday",
            "date": "2026-09-18",
        }

    def test_tomorrow(self):
        out = parse_bus_query("Bus 01 schedule tomorrow", NOW)
        assert out["route_name"] == "Bus 01"
        assert out["day"] == "Saturday"
        assert out["date"] == "2026-09-19"

    def test_tonight(self):
        out = parse_bus_query("Bus 04 schedule tonight", NOW)
        assert out["route_name"] == "Bus 04"
        assert out["day"] == "Friday"
        assert out["date"] == "2026-09-18"

    def test_explicit_weekday(self):
        out = parse_bus_query("Monday schedule for Bus 05", NOW)
        assert out["route_name"] == "Bus 05"
        assert out["day"] == "Monday"
        assert out["date"] == "2026-09-21"

    def test_explicit_iso_date(self):
        out = parse_bus_query("Bus 02 on 2026-09-20", NOW)
        assert out["route_name"] == "Bus 02"
        assert out["day"] == "Sunday"
        assert out["date"] == "2026-09-20"

    def test_route_alias(self):
        out = parse_bus_query("Route 3 schedule tomorrow", NOW)
        assert out["route_name"] == "Bus 03"
        assert out["day"] == "Saturday"
        assert out["date"] == "2026-09-19"


class TestParseBusNegative:
    def test_unrecognized_route(self):
        assert parse_bus_query("Bus 99 schedule tomorrow", NOW) is None

    def test_garbled_date(self):
        assert parse_bus_query("Bus 02 schedule on 2026-13-45", NOW) is None

    def test_driver_lookup(self):
        assert parse_bus_query("Who is the driver of Bus 02?", NOW) is None

    def test_route_finding(self):
        assert (
            parse_bus_query(
                "next bus from Aryabhatta to Tut Block",
                NOW,
            )
            is None
        )

    def test_next_departure(self):
        assert parse_bus_query("next departure for Bus 02", NOW) is None

    def test_write_intent(self):
        assert (
            parse_bus_query(
                "change Bus 02 Monday schedule to 18:00",
                NOW,
            )
            is None
        )
