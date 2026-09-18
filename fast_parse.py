"""Deterministic fast-path parsers for unambiguous mess/bus/timetable/notice queries.

Every public parser returns a fully populated argument dict, or None.
Nothing is guessed: missing hostel/route, write intent, mixed schedule/
timing language, or an unparseable date all fall through to the LLM.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

TIME_AND_DATE_FMT = "%A, %Y-%m-%d %H:%M:%S IST"

# Canonical hostel names as stored / accepted by mess_functions_1.get_menu
# (case-insensitive DB match). Aliases cover the phrasings the mess agent
# already treats as those hostels (tool schema + commented examples).
_HOSTEL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bc\s*\.?\s*v\s*\.?\s*raman\b", re.I), "CV Raman"),
    (re.compile(r"\bcvraman\b", re.I), "CV Raman"),
    (re.compile(r"\bcv-raman\b", re.I), "CV Raman"),
    (re.compile(r"\baryabhatta\b", re.I), "Aryabhatta"),
    (re.compile(r"\barya\s+bhatta\b", re.I), "Aryabhatta"),
    (re.compile(r"\bkalam\b", re.I), "Kalam"),
    (re.compile(r"\basima\b", re.I), "Asima"),
]

# query_schedule expects the bus_schedule.bus_name form, e.g. "Bus 02".
_KNOWN_BUS_NUMBERS = frozenset({"01", "02", "03", "04", "05"})
_BUS_RE = re.compile(
    r"\b(?:bus|route)\s*0?([1-9]\d?)\b",
    re.I,
)

_MEAL_ALIASES = {
    "breakfast": "breakfast",
    "lunch": "lunch",
    "snacks": "snacks",
    "snack": "snacks",
    "dinner": "dinner",
    "supper": "dinner",
}

_WEEKDAY_INDEX = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}
_WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

_ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_SLASH_DATE_RE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
_ORDINAL_DATE_RE = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)\b",
    re.I,
)

_WRITE_RE = re.compile(
    r"\b(change|modify|update|set|add|remove|delete|replace|edit)\b",
    re.I,
)
_SCHEDULE_AMBIGUOUS_RE = re.compile(
    r"\b(schedule|timetable|chart|plan|routine)\b",
    re.I,
)
_TIMING_RE = re.compile(
    r"\b(time|timing|timings|when|how late|open|close|closes|opens|"
    r"starts|ends|hours)\b",
    re.I,
)
_WEEKLY_RE = re.compile(
    r"\b(weekly|full week|entire week|whole week|all days|this week|all week)\b",
    re.I,
)
_MEAL_NAMED_RE = re.compile(
    r"\b(breakfast|lunch|snacks?|dinner|supper)\b",
    re.I,
)
_MENU_CONTENT_RE = re.compile(
    r"\b(menu|food|khana|cooking|served|what's there|whats there|"
    r"what do we get)\b",
    re.I,
)

_DRIVER_RE = re.compile(r"\b(driver|contact number|phone number)\b", re.I)
_NEXT_BUS_RE = re.compile(
    r"\b(next\s+(bus|departure)|when is the next)\b",
    re.I,
)
_ROUTE_FIND_RE = re.compile(
    r"\bfrom\b.+\bto\b|\bbetween\b.+\band\b",
    re.I,
)
_ACTIVE_BUS_RE = re.compile(r"\b(active buses|on the road)\b", re.I)

_NEXT_CLASS_RE = re.compile(r"\bnext class\b", re.I)
_FREE_SLOT_RE = re.compile(
    r"\b(free slot|free slots|free period|free time|when am i free)\b",
    re.I,
)
_COURSE_CODE_RE = re.compile(r"\b[A-Z]{2,3}\d{3}\b")
_ROOM_LOOKUP_RE = re.compile(r"\b(which room|what room|room number)\b", re.I)
_OTHER_ROLL_RE = re.compile(
    r"\b(\d{4}[A-Z]{2}\d{2,}|(?:PF|AD)\d{3,})\b",
    re.I,
)
_PERSONAL_TT_RE = re.compile(
    r"\b("
    r"my classes|my class|my timetable|my schedule|"
    r"classes do i|do i have|i have|"
    r"what(?:'s| is| are)? my|"
    r"for me|am i having"
    r")\b",
    re.I,
)
_WEEKDAY_TOKEN_RE = re.compile(
    r"\b(monday|mon|tuesday|tue|tues|wednesday|wed|thursday|thu|thur|"
    r"thurs|friday|fri|saturday|sat|sunday|sun)\b",
    re.I,
)
_RELATIVE_DAY_RE = re.compile(r"\b(today|tomorrow|tonight)\b", re.I)


def _parse_now(time_and_date: Optional[str]) -> Optional[datetime]:
    if not time_and_date or not str(time_and_date).strip():
        return None
    text = str(time_and_date).strip()
    if text.endswith(" IST"):
        text = text[: -len(" IST")].strip()
    for fmt in ("%A, %Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _resolve_date(user_input: str, now: datetime) -> Optional[datetime]:
    """Resolve an explicit or relative date, or default to `now`.

    Returns None only when the input contains a date-like token that cannot
    be parsed confidently (invalid ISO, slash date, bare ordinal).
    """
    iso = _ISO_DATE_RE.search(user_input)
    if iso:
        try:
            return datetime.strptime(iso.group(1), "%Y-%m-%d")
        except ValueError:
            return None

    if _SLASH_DATE_RE.search(user_input) or _ORDINAL_DATE_RE.search(user_input):
        return None

    lower = user_input.lower()
    if re.search(r"\btomorrow\b", lower):
        return now + timedelta(days=1)
    if re.search(r"\b(today|tonight)\b", lower):
        return now

    weekday_hit = _WEEKDAY_TOKEN_RE.search(lower)
    if weekday_hit:
        token = weekday_hit.group(1).lower()
        target = _WEEKDAY_INDEX[token]
        delta = (target - now.weekday()) % 7
        return now + timedelta(days=delta)

    return now


def _resolve_hostel(user_input: str) -> Optional[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for pattern, canonical in _HOSTEL_PATTERNS:
        if pattern.search(user_input) and canonical not in seen:
            seen.add(canonical)
            hits.append(canonical)
    if len(hits) != 1:
        return None
    return hits[0]


def _resolve_meal(user_input: str) -> Optional[str]:
    """Return a canonical meal name, or None if no meal is named.

    None is a defined value (full-day / weekly lookup), not a guess.
    """
    found: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(
        r"\b(breakfast|lunch|snacks?|dinner|supper)\b",
        user_input,
        re.I,
    ):
        canonical = _MEAL_ALIASES[match.group(1).lower()]
        if canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    if len(found) > 1:
        # Two named meals in one query is not a single lookup.
        return "__ambiguous__"
    if len(found) == 1:
        return found[0]
    return None


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _weekday(dt: datetime) -> str:
    return _WEEKDAY_NAMES[dt.weekday()]


def parse_mess_query(
    user_input: str, time_and_date: Optional[str]
) -> Optional[dict[str, Any]]:
    """Resolve (hostel, meal, date) for a mess menu lookup, or None."""
    if not user_input or not str(user_input).strip():
        return None
    text = str(user_input).strip()

    if _WRITE_RE.search(text):
        return None

    # Mixed menu + meal-timing / ambiguous "schedule" language → LLM.
    if _SCHEDULE_AMBIGUOUS_RE.search(text) and (
        _TIMING_RE.search(text) or _MEAL_NAMED_RE.search(text)
    ):
        return None
    # Clock-time questions ("when is dinner", "mess timings") are not
    # menu lookups — leave them to get_meal_timing via the LLM.
    if _TIMING_RE.search(text) and not _MENU_CONTENT_RE.search(text):
        return None

    now = _parse_now(time_and_date)
    if now is None:
        return None

    hostel = _resolve_hostel(text)
    if hostel is None:
        return None

    meal = _resolve_meal(text)
    if meal == "__ambiguous__":
        return None

    resolved = _resolve_date(text, now)
    if resolved is None:
        return None

    has_day = bool(
        _RELATIVE_DAY_RE.search(text)
        or _WEEKDAY_TOKEN_RE.search(text)
        or _ISO_DATE_RE.search(text)
    )
    weekly = bool(_WEEKLY_RE.search(text)) or (
        bool(_SCHEDULE_AMBIGUOUS_RE.search(text)) and not has_day
    )
    return {
        "hostel": hostel,
        "meal": meal,
        "date": _iso(resolved),
        "weekly": weekly,
    }


def parse_bus_query(
    user_input: str, time_and_date: Optional[str]
) -> Optional[dict[str, Any]]:
    """Resolve (route_name, day, date) for a schedule lookup, or None."""
    if not user_input or not str(user_input).strip():
        return None
    text = str(user_input).strip()

    if _WRITE_RE.search(text):
        return None
    if _DRIVER_RE.search(text):
        return None
    if _NEXT_BUS_RE.search(text):
        return None
    if _ROUTE_FIND_RE.search(text):
        return None
    if _ACTIVE_BUS_RE.search(text):
        return None

    now = _parse_now(time_and_date)
    if now is None:
        return None

    bus_hit = _BUS_RE.search(text)
    if not bus_hit:
        return None
    number = bus_hit.group(1).zfill(2)
    if number not in _KNOWN_BUS_NUMBERS:
        return None
    route_name = f"Bus {number}"

    resolved = _resolve_date(text, now)
    if resolved is None:
        return None

    return {
        "route_name": route_name,
        "day": _weekday(resolved),
        "date": _iso(resolved),
    }


def parse_timetable_query(
    user_input: str,
    time_and_date: Optional[str],
    user_metadata: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Resolve a personal day-schedule lookup for the authenticated caller."""
    if not user_input or not str(user_input).strip():
        return None
    text = str(user_input).strip()
    meta = user_metadata or {}

    if _WRITE_RE.search(text):
        return None
    if _NEXT_CLASS_RE.search(text):
        return None
    if _WEEKLY_RE.search(text):
        return None
    if _FREE_SLOT_RE.search(text):
        return None
    if _COURSE_CODE_RE.search(text):
        return None
    if _ROOM_LOOKUP_RE.search(text):
        return None
    if not _PERSONAL_TT_RE.search(text):
        return None

    roll = meta.get("roll_number") or meta.get("roll_num")
    if not roll or not str(roll).strip():
        return None
    roll = str(roll).strip()

    mentioned = _OTHER_ROLL_RE.search(text)
    if mentioned and mentioned.group(1).upper() != roll.upper():
        return None

    # Must name a day — "what classes do I have" with no day is a week view.
    if not _RELATIVE_DAY_RE.search(text) and not _WEEKDAY_TOKEN_RE.search(text):
        if not _ISO_DATE_RE.search(text):
            return None

    now = _parse_now(time_and_date)
    if now is None:
        return None

    resolved = _resolve_date(text, now)
    if resolved is None:
        return None

    role = str(meta.get("role") or "student").strip().lower()
    faculty_aliases = {"faculty", "professor", "prof", "teacher"}
    target_type = "faculty" if role in faculty_aliases else "student"

    return {
        "target_id": roll,
        "target_type": target_type,
        "timetable_day": _weekday(resolved),
    }


def format_mess_reply(parsed: dict[str, Any], result: Any) -> str:
    """Markdown table for a mess lookup, matching mess_agent_1 FORMATTING."""
    if not isinstance(result, dict):
        return str(result)
    if result.get("status") != "success":
        return str(result.get("message") or result)

    hostel = result.get("hostel") or parsed.get("hostel") or ""
    meal = parsed.get("meal")

    if parsed.get("weekly") or "week_menu" in result:
        week = result.get("week_menu") or []
        lines = [
            f"**{hostel} weekly menu**",
            "",
            "| Day | Date | Breakfast | Lunch | Snacks | Dinner |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for day in week:
            lines.append(
                f"| {day.get('day', '')} | {day.get('date', '')} "
                f"| {day.get('breakfast') or '—'} "
                f"| {day.get('lunch') or '—'} "
                f"| {day.get('snacks') or '—'} "
                f"| {day.get('dinner') or '—'} |"
            )
        return "\n".join(lines)

    menu = result.get("menu") or {}
    day = result.get("day") or ""
    date = result.get("date") or parsed.get("date") or ""
    header = f"**{hostel} — {day}, {date}**" if day else f"**{hostel} — {date}**"
    meals = ("breakfast", "lunch", "snacks", "dinner")
    show = (meal,) if meal else meals
    lines = [
        header,
        "",
        "| Meal | Items |",
        "| --- | --- |",
    ]
    for name in show:
        lines.append(f"| {name.capitalize()} | {menu.get(name) or '—'} |")
    return "\n".join(lines)


def format_bus_reply(parsed: dict[str, Any], result: Any) -> str:
    """Plain table for a bus schedule lookup."""
    if isinstance(result, dict) and result.get("error"):
        return str(result["error"])
    if not isinstance(result, list):
        return str(result)

    route = parsed.get("route_name") or ""
    day = parsed.get("day") or ""
    date = parsed.get("date") or ""
    title = f"**{route} — {day}**" if day else f"**{route}**"
    if date:
        title = f"**{route} — {day}, {date}**"

    if not result:
        return f"No departures for {route} on {day}."

    lines = [
        title,
        "",
        "| Time | From | To |",
        "| --- | --- | --- |",
    ]
    for row in result:
        time_s = row.get("departure_time") or row.get("arrival_time") or "—"
        start = row.get("start_point") or "—"
        dest = row.get("destination") or "—"
        lines.append(f"| {time_s} | {start} | {dest} |")
    return "\n".join(lines)


def format_timetable_reply(parsed: dict[str, Any], result: Any) -> str:
    """Plain table for the caller's classes on one day."""
    if not isinstance(result, dict):
        return str(result)
    if result.get("status") not in (None, "success"):
        return str(result.get("message") or result)

    day = parsed.get("timetable_day") or ""
    items = list(result.get("items") or [])
    if day:
        items = [
            item
            for item in items
            if str(item.get("timetable_day") or item.get("weekday") or "") == day
        ]

    if not items:
        return f"No classes scheduled on {day}." if day else "No classes scheduled."

    lines = [
        f"**Your classes — {day}**" if day else "**Your classes**",
        "",
        "| Time | Course | Room |",
        "| --- | --- | --- |",
    ]
    for item in items:
        slot = item.get("timetable_slot") or (
            f"{item.get('slot_start', '')}-{item.get('slot_end', '')}"
        )
        course = item.get("course_code") or item.get("course_name") or "—"
        name = item.get("course_name") or item.get("subject")
        if name and name != course:
            course = f"{course} ({name})"
        room = item.get("room_id") or "—"
        lines.append(f"| {slot} | {course} | {room} |")
    return "\n".join(lines)


_NOTICE_WRITE_RE = re.compile(
    r"\b(publish|post|create|add|archive|delete|remove|expire|update|edit)\b",
    re.I,
)
_NOTICE_CONTENT_RE = re.compile(
    r"\b(explain|means?|about this|this notice|notice about)\b",
    re.I,
)
_NOTICE_WORD_RE = re.compile(
    r"\b(notices?|notice board|bulletin)\b",
    re.I,
)
_NOTICE_VIEW_RE = re.compile(
    r"\b(today|today's|todays|current|active|show|list|view|what are|"
    r"notice board|bulletin)\b",
    re.I,
)
_NOTICE_OTHER_DATE_RE = re.compile(
    r"\b(yesterday|last week|tomorrow|\d{4}-\d{2}-\d{2})\b",
    re.I,
)
_NOTICE_TYPE_FILTER_RE = re.compile(
    r"\b(important alert|notice type|of type)\b",
    re.I,
)


def parse_notice_query(
    user_input: str, time_and_date: Optional[str]
) -> Optional[dict[str, Any]]:
    """Resolve an unqualified 'show current notices' lookup, or None.

    Audience/authority are never parsed from text — the agent fills them
    from user_metadata, same as timetable's roll number.
    """
    if not user_input or not str(user_input).strip():
        return None
    text = str(user_input).strip()
    if _NOTICE_WRITE_RE.search(text):
        return None
    if _NOTICE_CONTENT_RE.search(text):
        return None
    if _NOTICE_OTHER_DATE_RE.search(text):
        return None
    if _NOTICE_TYPE_FILTER_RE.search(text):
        return None
    if not _NOTICE_WORD_RE.search(text):
        return None
    if not _NOTICE_VIEW_RE.search(text):
        return None
    # time_and_date is part of the shared parser contract; view_notices
    # already returns currently active rows, so no date is resolved here.
    _ = time_and_date
    return {"action": "view"}


def format_notice_reply(parsed: dict[str, Any], result: Any) -> str:
    """Bulletin feed matching Notice_agent FORMATTING RULES."""
    if isinstance(result, dict) and result.get("error"):
        return str(result.get("error") or result)
    if isinstance(result, list) and result and isinstance(result[0], dict) and result[0].get("error"):
        return str(result[0].get("error"))
    rows = result if isinstance(result, list) else []
    if not rows:
        return "No active notices."
    lines = ["### Active Notices", ""]
    for row in rows:
        ntype = row.get("notice_type") or "Notice"
        date = row.get("publish_timestamp") or ""
        if date:
            date = str(date).split(" ")[0]
        author = row.get("author_id") or row.get("author") or "—"
        content = row.get("content") or ""
        lines.append(f"**{ntype}** | *{date}* | By: {author}")
        lines.append(f"> {content}")
        lines.append("")
    return "\n".join(lines).rstrip()
