"""Admin setup: denied for students; org YAML patch; planner fast-path."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import org_profile
from custom_features import RESERVED_SLUGS, add_feature, slugify
from fast_parse import parse_mess_query
from setup_agent import SetupAgent
from setup_functions import import_people, update_org_profile
from tests.fast_parse.conftest import NOW

TINY = Path(__file__).resolve().parents[1] / "fast_parse" / "tiny_org.yaml"


@pytest.fixture
def isolated_org(tmp_path, monkeypatch):
    dest = tmp_path / "org.yaml"
    shutil.copy(TINY, dest)
    profile = org_profile.load_org_profile(dest)
    monkeypatch.setattr(org_profile, "ORG", profile)
    return dest


class TestAdminGate:
    def test_student_chat_is_refused_without_tools(self):
        reply = SetupAgent().chat(
            "Add a library feature",
            {"role": "student", "name": "Ada", "roll_number": "2501CS00"},
        )
        assert "admin" in reply.lower()

    def test_student_cannot_update_profile(self, isolated_org):
        result = update_org_profile("student", add_hostels=["East"])
        assert result["status"] == "error"
        assert "admin" in result["message"].lower()

    def test_student_cannot_import_people(self):
        result = import_people(
            "student",
            people=[{"role": "student", "name": "Ada", "external_id": "2501CS00"}],
        )
        assert result["status"] == "error"


class TestUpdateOrgProfile:
    def test_admin_add_hostel_is_used_by_fast_parse(self, isolated_org):
        result = update_org_profile(
            "admin",
            add_hostels=[{"name": "East", "aliases": ["east hall"]}],
        )
        assert result["status"] == "ok"
        names = [h.name for h in org_profile.ORG.catalog.hostels]
        assert "East" in names
        parsed = parse_mess_query("What is today's dinner at East?", NOW)
        assert parsed is not None
        assert parsed["hostel"] == "East"

    def test_invalid_pattern_is_rejected_and_file_kept(self, isolated_org):
        before = isolated_org.read_text(encoding="utf-8")
        result = update_org_profile("admin", student_id_pattern="[unterminated")
        assert result["status"] == "error"
        assert isolated_org.read_text(encoding="utf-8") == before


class TestAddFeatureValidation:
    def test_reserved_slug_rejected(self):
        result = add_feature(
            name="mess",
            description="nope",
            fields=[{"name": "item", "type": "string"}],
        )
        assert result["status"] == "error"
        assert "mess" in RESERVED_SLUGS

    def test_slugify_library(self):
        assert slugify("Lost and Found") == "lost_and_found"
