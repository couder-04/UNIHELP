"""Timetable agent for the UNIHELP campus assistant.

Takes role metadata (student / faculty / admin), plans tool calls with the
shared LLM client from llm.py (LLM_API_KEY in the project .env), then executes
tools from timetable_functions.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from llm import cached_system_message, chat_create, identity_message
import timetable_functions as timetable_fns

READ_TOOLS = frozenset(
    {
        "list_subjects",
        "resolve_course",
        "get_timetable",
        "get_schedule",
        "get_week",
        "get_day",
        "count_classes",
        "next_class",
        "get_free_slots",
        "list_rooms",
    }
)
WRITE_TOOLS = frozenset({"add_slot", "update_slot", "delete_slot"})

ROLE_TOOLS: dict[str, frozenset[str]] = {
    "student": READ_TOOLS,
    "faculty": READ_TOOLS | WRITE_TOOLS,
    "admin": READ_TOOLS | WRITE_TOOLS,
}

TOOL_IMPL: dict[str, Callable[..., Any]] = {
    "list_subjects": timetable_fns.list_subjects,
    "resolve_course": timetable_fns.resolve_course,
    "get_timetable": timetable_fns.get_timetable,
    "get_schedule": timetable_fns.get_schedule,
    "get_week": timetable_fns.get_week,
    "get_day": timetable_fns.get_day,
    "count_classes": timetable_fns.count_classes,
    "next_class": timetable_fns.next_class,
    "get_free_slots": timetable_fns.get_free_slots,
    "list_rooms": timetable_fns.list_rooms,
    "add_slot": timetable_fns.add_slot,
    "update_slot": timetable_fns.update_slot,
    "delete_slot": timetable_fns.delete_slot,
}

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "list_subjects": {
        "description": "List all courses/subjects in the catalog.",
        "parameters": {"type": "object", "properties": {}},
    },
    "resolve_course": {
        "description": "Resolve a course by code or name.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_code": {"type": "string"},
                "course_name": {"type": "string"},
            },
        },
    },
    "get_timetable": {
        "description": "Get week timetable, or one day if timetable_day is set.",
        "parameters": {
            "type": "object",
            "properties": {
                "timetable_day": {
                    "type": "string",
                    "description": "Monday..Sunday or today/tomorrow",
                },
                "subject": {"type": "string"},
                "course_code": {"type": "string"},
                "class_type": {"type": "string", "enum": ["lecture", "lab", "tutorial"]},
                "student_group": {"type": "string", "description": "e.g., G1-G6, G19-24"},
            },
        },
    },
    "get_schedule": {
        "description": "Get the personal schedule for a specific user.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_id": {"type": "string", "description": "Roll number of the user"},
                "target_type": {"type": "string", "enum": ["student", "faculty"]},
            },
            "required": ["target_id", "target_type"],
        },
    },
    "get_week": {
        "description": "Full week timetable, optionally filtered by subject.",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "course_code": {"type": "string"},
            },
        },
    },
    "get_day": {
        "description": "Classes on one day (default today).",
        "parameters": {
            "type": "object",
            "properties": {
                "timetable_day": {"type": "string"},
                "subject": {"type": "string"},
                "course_code": {"type": "string"},
            },
        },
    },
    "count_classes": {
        "description": "Count weekly classes, optionally for one subject.",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "course_code": {"type": "string"},
            },
        },
    },
    "next_class": {
        "description": "Find the next upcoming class (optionally for a subject).",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "course_code": {"type": "string"},
                "now": {"type": "string", "description": "ISO datetime override"},
            },
        },
    },
    "get_free_slots": {
        "description": "List free one-hour slots on a day (default today).",
        "parameters": {
            "type": "object",
            "properties": {"timetable_day": {"type": "string"}},
        },
    },
    "list_rooms": {
        "description": "List campus rooms usable for scheduling.",
        "parameters": {"type": "object", "properties": {}},
    },
    "add_slot": {
        "description": "Faculty/admin only: add a class slot.",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "course_code": {"type": "string"},
                "timetable_day": {"type": "string"},
                "slot_start": {"type": "string", "description": "HH:MM"},
                "slot_end": {"type": "string", "description": "HH:MM"},
                "room_id": {"type": "string"},
                "professor_roll": {"type": "string"},
                "class_type": {"type": "string", "enum": ["lecture", "lab", "tutorial"]},
                "student_group": {"type": "string", "description": "e.g., G1-G24 or G7-12"},
            },
            "required": ["timetable_day", "slot_start", "slot_end", "room_id", "class_type", "student_group"],
        },
    },
    "update_slot": {
        "description": "Faculty/admin only: update a slot by slot_id or day+start+subject.",
        "parameters": {
            "type": "object",
            "properties": {
                "slot_id": {"type": "string"},
                "subject": {"type": "string"},
                "course_code": {"type": "string"},
                "timetable_day": {"type": "string"},
                "slot_start": {"type": "string"},
                "slot_end": {"type": "string"},
                "room_id": {"type": "string"},
                "new_day": {"type": "string"},
                "new_start": {"type": "string"},
                "new_end": {"type": "string"},
                "new_room_id": {"type": "string"},
                "new_subject": {"type": "string"},
                "professor_roll": {"type": "string"},
            },
        },
    },
    "delete_slot": {
        "description": "Faculty/admin only: delete a slot by slot_id or day+start+subject.",
        "parameters": {
            "type": "object",
            "properties": {
                "slot_id": {"type": "string"},
                "subject": {"type": "string"},
                "course_code": {"type": "string"},
                "timetable_day": {"type": "string"},
                "slot_start": {"type": "string"},
                "professor_roll": {"type": "string"},
            },
        },
    },
}


def _normalize_role(role: str) -> str:
    raw = (role or "").strip().lower()
    aliases = {
        "student": "student",
        "faculty": "faculty",
        "professor": "faculty",
        "prof": "faculty",
        "teacher": "faculty",
        "hod": "admin",
        "admin": "admin",
        "administrator": "admin",
    }
    if raw not in aliases:
        raise ValueError(
            f"Unsupported role {role!r}. Use one of: student, faculty, admin."
        )
    return aliases[raw]


def _openai_tools_for_role(role: str) -> list[dict[str, Any]]:
    allowed = ROLE_TOOLS[role]
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": TOOL_SCHEMAS[name]["description"],
                "parameters": TOOL_SCHEMAS[name]["parameters"],
            },
        }
        for name in sorted(allowed)
        if name in TOOL_SCHEMAS
    ]


def _system_prompt() -> str:
    return """You are the Timetable Agent for a campus assistant.

Identity model:
- people(roll_num, name, role) — student | faculty | admin
- Faculty rolls are PF001, PF002, ... Admin rolls are AD001, AD002, ...
- Students use IIT-style rolls such as 2501CS09.
- courses(code, name, professor_name, professor_roll, ...)
- timetable(course_code, timetable_day, slot_start, slot_end, room_id)

Be helpful with relative times (today, now, tomorrow) using Time and Date
from the identity message. Do not invent identity.

If a user asks for their schedule, call get_schedule. Year and department
are encoded in student roll numbers. If get_schedule returns 0 items, say
they have no classes scheduled rather than guessing other courses.
"""


def _now_ist() -> str:
    return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%A, %Y-%m-%d %H:%M:%S IST")


def _standard_metadata(user_metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize UNIHELP caller metadata.

    Standard input (same as main.py / other agents):
      {
        "role": "student" | "faculty" | "admin",
        "name": "Abhirup Dhara",
        "roll_number": "2501CS36",
        "Time and Date": "Tuesday, 2026-09-15 21:12:00 IST",
      }
    """
    raw = dict(user_metadata or {})
    roll = raw.get("roll_number") or raw.get("roll_num")
    if roll is not None:
        roll = str(roll).strip()
    return {
        "role": raw.get("role"),
        "name": raw.get("name"),
        "roll_number": roll,
        "Time and Date": raw.get("Time and Date") or _now_ist(),
        "roll_num": roll,
    }


def _enforce_identity(
    role: str, metadata: dict[str, Any], name: str, args: dict[str, Any]
) -> dict[str, Any]:
    cleaned = dict(args or {})
    roll = metadata.get("roll_number") or metadata.get("roll_num")
    if not roll:
        raise PermissionError("metadata.roll_number is required")

    if name not in ROLE_TOOLS[role]:
        raise PermissionError(f"Role {role!r} cannot use tool {name!r}.")

    if role == "student":
        if name in WRITE_TOOLS:
            raise PermissionError("Students cannot edit the timetable.")
        # FIX: Prevent students from snooping on other schedules
        if name == "get_schedule":
            cleaned["target_id"] = roll
            cleaned["target_type"] = "student"

    if role == "faculty":
        if name in WRITE_TOOLS:
            cleaned["professor_roll"] = roll
        # FIX: Prevent faculty from snooping on other schedules
        if name == "get_schedule":
            cleaned["target_id"] = roll
            cleaned["target_type"] = "faculty"

    # Admin writes: do not force professor_roll so ownership check is skipped.
    return cleaned


def _call_tool(name: str, args: dict[str, Any]) -> Any:
    fn = TOOL_IMPL.get(name)
    if fn is None:
        return {"status": "error", "message": f"Unknown tool: {name}"}
    try:
        return fn(**args)
    except TypeError as exc:
        return {"status": "error", "message": f"Bad arguments for {name}: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc)}


def run_timetable_agent(
    query: str,
    metadata: dict[str, Any],
    *,
    max_rounds: int = 6,
) -> dict[str, Any]:
    """Run the timetable agent for one user query.

    metadata (required, same shape as main.py):
      {
        "role": "student",
        "name": "Abhirup Dhara",
        "roll_number": "2501CS36",
        "Time and Date": "Tuesday, 2026-09-15 21:12:00 IST",
      }
    """
    metadata = _standard_metadata(metadata)
    role = _normalize_role(str(metadata.get("role", "")))
    roll = metadata.get("roll_number")
    if not roll:
        raise ValueError("metadata.roll_number is required")
    metadata = {**metadata, "role": role, "roll_number": roll, "roll_num": roll}

    openai_tools = _openai_tools_for_role(role)

    messages: list[dict[str, Any]] = [
        cached_system_message(_system_prompt()),
        identity_message(
            {
                "role": role,
                "name": metadata.get("name"),
                "roll_number": roll,
                "Time and Date": metadata.get("Time and Date"),
            },
            label="Authenticated caller identity",
        ),
        {"role": "user", "content": query},
    ]
    tool_trace: list[dict[str, Any]] = []

    for _ in range(max_rounds):
        response = chat_create(
            cache_key=f"timetable-{role}",
            messages=messages,
            tools=openai_tools,
            tool_choice="auto",
        )
        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        if not tool_calls:
            answer = (message.content or "").strip()
            return {
                "status": "success",
                "role": role,
                "name": metadata.get("name"),
                "roll_num": roll,
                "answer": answer,
                "tool_calls": tool_trace,
            }

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        for tc in tool_calls:
            name = tc.function.name
            try:
                raw_args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                raw_args = {}
            if not isinstance(raw_args, dict):
                raw_args = {}

            try:
                args = _enforce_identity(role, metadata, name, raw_args)
                result = _call_tool(name, args)
            except PermissionError as exc:
                result = {"status": "error", "message": str(exc)}
                args = raw_args

            tool_trace.append({"tool": name, "args": args, "result": result})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str),
                }
            )

    return {
        "status": "error",
        "role": role,
        "name": metadata.get("name"),
        "roll_num": roll,
        "answer": "Stopped after too many tool rounds without a final answer.",
        "tool_calls": tool_trace,
    }


class TimetableAgent:
    """UNIHELP wrapper: maps campus metadata and returns a string reply."""

    def chat(self, user_input: str, user_metadata: dict) -> str:
        user_metadata = user_metadata or {}
        metadata = _standard_metadata(user_metadata)
        try:
            result = run_timetable_agent(user_input, metadata)
        except Exception as exc:
            return str(exc)
        if isinstance(result, dict):
            answer = result.get("answer")
            if answer is not None and answer != "":
                return answer
            return json.dumps(result, default=str)
        return str(result)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the timetable agent from the terminal.")
    parser.add_argument("query", nargs="?", help="Natural-language timetable question")
    parser.add_argument("--name", required=True, help="Person name")
    parser.add_argument("--roll-num", required=True, help="Universal roll number")
    parser.add_argument(
        "--role",
        choices=["student", "faculty", "admin"],
        required=True,
        help="Caller role",
    )
    args = parser.parse_args()

    query = args.query or "Show this week's timetable"
    metadata = {
        "role": args.role,
        "name": args.name,
        "roll_number": args.roll_num,
        "Time and Date": _now_ist(),
    }
    result = run_timetable_agent(query, metadata)
    print(json.dumps(result, indent=2, default=str))