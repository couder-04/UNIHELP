"""Catalog-driven fast_parse: parsers must resolve against ORG, not IIT Patna."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import org_profile
from fast_parse import parse_bus_query, parse_mess_query
from tests.fast_parse.conftest import NOW

TINY_ORG = Path(__file__).resolve().parent / "tiny_org.yaml"


@pytest.fixture
def tiny_org(monkeypatch):
    profile = org_profile.load_org_profile(TINY_ORG)
    monkeypatch.setattr(org_profile, "ORG", profile)
    return profile


class TestCatalogSwap:
    def test_tiny_hostel_resolves(self, tiny_org):
        out = parse_mess_query("What is today's dinner at North?", NOW)
        assert out is not None
        assert out["hostel"] == "North"
        assert out["meal"] == "dinner"

    def test_tiny_hostel_alias(self, tiny_org):
        out = parse_mess_query("today's lunch at north hall", NOW)
        assert out is not None
        assert out["hostel"] == "North"
        assert out["meal"] == "lunch"

    def test_iit_patna_hostel_is_unknown_under_tiny_catalog(self, tiny_org):
        out = parse_mess_query("What is today's dinner at Kalam?", NOW)
        assert out is not None
        assert out.get("need_hostel") is True
        assert out["hostel"] is None

    def test_tiny_bus_resolves(self, tiny_org):
        out = parse_bus_query("Bus 07 schedule today", NOW)
        assert out == {
            "route_name": "Bus 07",
            "day": "Friday",
            "date": "2026-09-18",
        }

    def test_iit_patna_bus_is_unknown_under_tiny_catalog(self, tiny_org):
        assert parse_bus_query("Bus 02 schedule today", NOW) is None

    def test_south_hostel_without_alias_still_matches_name(self, tiny_org):
        out = parse_mess_query("today's menu at South", NOW)
        assert out is not None
        assert out["hostel"] == "South"
        assert out["meal"] is None
