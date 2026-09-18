"""Re-export production parsers.

pytest puts `tests/` on sys.path, so this directory would otherwise shadow
repo-root `fast_parse.py` and break agent imports in other test packages.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "unihelp_fast_parse",
    _HERE / "fast_parse.py",
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("unihelp_fast_parse", _mod)
_spec.loader.exec_module(_mod)

parse_mess_query = _mod.parse_mess_query
parse_bus_query = _mod.parse_bus_query
parse_timetable_query = _mod.parse_timetable_query
parse_notice_query = _mod.parse_notice_query
format_mess_reply = _mod.format_mess_reply
format_bus_reply = _mod.format_bus_reply
format_timetable_reply = _mod.format_timetable_reply
format_notice_reply = _mod.format_notice_reply
