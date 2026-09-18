"""Attendance agent for the UNIHELP campus assistant.

Takes role metadata (student / faculty / admin), plans tool calls with the
Kado OpenAI-compatible LLM, then executes tools from attendance_functions.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from llm import cached_system_message, chat_create, identity_message
import attendance_functions as attendance_tools

ROLES = frozenset({"student", "faculty", "admin"})

# Role → allowed tool names from attendance_functions.py
ROLE_TOOLS: dict[str, frozenset[str]] = {
    "student": frozenset(
        {
            "get_attendance",
            "get_weekly_attendance",
            "get_attendance_summary",
            "get_skip_budget",
            "get_monthly_attendance",
            "get_semester_attendance",
            "get_consecutive_absences",
            "get_attendance_chart",
            "get_today_attendance",
            "list_courses",
            "resolve_course",
            "list_people",
        }
    ),
    "faculty": frozenset(
        {
            "get_attendance",
            "get_weekly_attendance",
            "get_attendance_summary",
            "get_skip_budget",
            "get_course_attendance",
            "get_course_attendance_summary",
            "get_monthly_attendance",
            "get_semester_attendance",
            "get_at_risk_students",
            "get_consecutive_absences",
            "get_attendance_chart",
            "get_today_attendance",
            "get_unmarked_students",
            "list_course_sessions",
            "list_courses",
            "list_roster",
            "list_people",
            "resolve_course",
            "rank_course_attendance",
            "export_course_attendance_csv",
            "mark_attendance",
            "mark_students_attendance",
            "mark_class_attendance",
            "edit_attendance",
            "delete_attendance",
        }
    ),
    "admin": frozenset(
        {
            "get_attendance",
            "get_weekly_attendance",
            "get_attendance_summary",
            "get_skip_budget",
            "get_course_attendance",
            "get_course_attendance_summary",
            "get_monthly_attendance",
            "get_semester_attendance",
            "get_at_risk_students",
            "get_consecutive_absences",
            "get_attendance_chart",
            "get_today_attendance",
            "get_unmarked_students",
            "list_course_sessions",
            "list_courses",
            "list_roster",
            "list_people",
            "resolve_course",
            "rank_course_attendance",
            "export_course_attendance_csv",
            "mark_attendance",
            "mark_students_attendance",
            "mark_class_attendance",
            "edit_attendance",
            "delete_attendance",
            "add_person",
            "edit_person",
            "delete_person",
            "add_course",
            "edit_course",
            "delete_course",
            "add_enrollment",
            "delete_enrollment",
            "list_enrollments",
        }
    ),
}

TOOL_IMPL: dict[str, Callable[..., Any]] = {
    "get_attendance": attendance_tools.get_attendance,
    "get_weekly_attendance": attendance_tools.get_weekly_attendance,
    "get_attendance_summary": attendance_tools.get_attendance_summary,
    "get_skip_budget": attendance_tools.get_skip_budget,
    "get_course_attendance": attendance_tools.get_course_attendance,
    "get_course_attendance_summary": attendance_tools.get_course_attendance_summary,
    "get_monthly_attendance": attendance_tools.get_monthly_attendance,
    "get_semester_attendance": attendance_tools.get_semester_attendance,
    "get_at_risk_students": attendance_tools.get_at_risk_students,
    "get_consecutive_absences": attendance_tools.get_consecutive_absences,
    "get_attendance_chart": attendance_tools.get_attendance_chart,
    "get_today_attendance": attendance_tools.get_today_attendance,
    "get_unmarked_students": attendance_tools.get_unmarked_students,
    "list_course_sessions": attendance_tools.list_course_sessions,
    "list_courses": attendance_tools.list_courses,
    "list_roster": attendance_tools.list_roster,
    "list_people": attendance_tools.list_people,
    "list_enrollments": attendance_tools.list_enrollments,
    "resolve_course": attendance_tools.resolve_course,
    "rank_course_attendance": attendance_tools.rank_course_attendance,
    "export_course_attendance_csv": attendance_tools.export_course_attendance_csv,
    "mark_attendance": attendance_tools.mark_attendance,
    "mark_students_attendance": attendance_tools.mark_students_attendance,
    "mark_class_attendance": attendance_tools.mark_class_attendance,
    "edit_attendance": attendance_tools.edit_attendance,
    "delete_attendance": attendance_tools.delete_attendance,
    "add_person": attendance_tools.add_person,
    "edit_person": attendance_tools.edit_person,
    "delete_person": attendance_tools.delete_person,
    "add_course": attendance_tools.add_course,
    "edit_course": attendance_tools.edit_course,
    "delete_course": attendance_tools.delete_course,
    "add_enrollment": attendance_tools.add_enrollment,
    "delete_enrollment": attendance_tools.delete_enrollment,
}

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "get_attendance": {
        "description": "Get attendance records for a student in a course.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "course_code": {"type": "string"},
                "session_date": {"type": "string", "description": "YYYY-MM-DD"},
                "date_from": {"type": "string"},
                "date_to": {"type": "string"},
            },
            "required": ["student_id", "course_code"],
        },
    },
    "get_weekly_attendance": {
        "description": "Get a student's attendance for the current or given week.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "week_start": {"type": "string", "description": "Monday YYYY-MM-DD"},
            },
            "required": ["student_id"],
        },
    },
    "get_attendance_summary": {
        "description": "Attendance % and skip budget per enrolled course for a student.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "course_code": {"type": "string"},
            },
            "required": ["student_id"],
        },
    },
    "get_skip_budget": {
        "description": "How many classes a student can still skip in a course.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "course_code": {"type": "string"},
            },
            "required": ["student_id", "course_code"],
        },
    },
    "get_course_attendance": {
        "description": "Course-wise attendance for all students (optionally one date).",
        "parameters": {
            "type": "object",
            "properties": {
                "course_code": {"type": "string"},
                "session_date": {"type": "string"},
            },
            "required": ["course_code"],
        },
    },
    "get_course_attendance_summary": {
        "description": "Per-student attendance summary for one course.",
        "parameters": {
            "type": "object",
            "properties": {"course_code": {"type": "string"}},
            "required": ["course_code"],
        },
    },
    "get_monthly_attendance": {
        "description": "Monthly attendance for a student.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "year": {"type": "integer"},
                "month": {"type": "integer"},
                "course_code": {"type": "string"},
            },
            "required": ["student_id", "year", "month"],
        },
    },
    "get_semester_attendance": {
        "description": "Semester / date-range attendance for a student.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "date_from": {"type": "string"},
                "date_to": {"type": "string"},
                "course_code": {"type": "string"},
            },
            "required": ["student_id", "date_from", "date_to"],
        },
    },
    "get_at_risk_students": {
        "description": "List students below attendance threshold.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {"type": "string"},
                "course_code": {"type": "string"},
                "professor_id": {"type": "string"},
            },
        },
    },
    "get_consecutive_absences": {
        "description": "Find consecutive absence streaks for a student.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "course_code": {"type": "string"},
                "min_streak": {"type": "integer"},
            },
            "required": ["student_id"],
        },
    },
    "list_course_sessions": {
        "description": "List distinct class dates marked for a course.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {"type": "string"},
                "course_code": {"type": "string"},
            },
        },
    },
    "rank_course_attendance": {
        "description": "Rank enrolled students by attendance percent.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {"type": "string"},
                "course_code": {"type": "string"},
            },
        },
    },
    "export_course_attendance_csv": {
        "description": "Export course attendance as CSV text.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {"type": "string"},
                "course_code": {"type": "string"},
                "session_date": {"type": "string"},
            },
        },
    },
    "mark_attendance": {
        "description": "Professor-only: mark one student present/absent/late/excused.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "course_code": {"type": "string"},
                "course_id": {"type": "string"},
                "session_date": {"type": "string"},
                "attendance_status": {"type": "string"},
                "professor_id": {"type": "string"},
            },
            "required": [
                "student_id",
                "session_date",
                "attendance_status",
                "professor_id",
            ],
        },
    },
    "mark_students_attendance": {
        "description": (
            "Professor-only: mark attendance for a set of students given "
            "date and course id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "student_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "session_date": {"type": "string"},
                "course_id": {"type": "string"},
                "professor_id": {"type": "string"},
                "attendance_status": {"type": "string"},
                "status_by_student": {"type": "object"},
            },
            "required": ["student_ids", "session_date", "course_id", "professor_id"],
        },
    },
    "mark_class_attendance": {
        "description": "Professor-only: mark the full class roster for one session.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {"type": "string"},
                "course_code": {"type": "string"},
                "session_date": {"type": "string"},
                "professor_id": {"type": "string"},
                "default_status": {"type": "string"},
                "present_numbers": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "absent_numbers": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["course_id", "session_date", "professor_id"],
        },
    },
    "edit_attendance": {
        "description": "Professor-only: correct an existing attendance mark.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "course_id": {"type": "string"},
                "course_code": {"type": "string"},
                "session_date": {"type": "string"},
                "attendance_status": {"type": "string"},
                "professor_id": {"type": "string"},
            },
            "required": [
                "student_id",
                "course_id",
                "session_date",
                "attendance_status",
                "professor_id",
            ],
        },
    },
    "delete_attendance": {
        "description": "Professor-only: delete one attendance mark.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "course_id": {"type": "string"},
                "course_code": {"type": "string"},
                "session_date": {"type": "string"},
                "professor_id": {"type": "string"},
            },
            "required": ["student_id", "course_id", "session_date", "professor_id"],
        },
    },
    "resolve_course": {
        "description": "Resolve a course by id, code, or name.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {"type": "string"},
                "course_code": {"type": "string"},
                "course_name": {"type": "string"},
            },
        },
    },
    "list_courses": {
        "description": "List courses for a student, professor, or all courses.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "professor_id": {"type": "string"},
            },
        },
    },
    "list_roster": {
        "description": "List enrolled students for a course.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {"type": "string"},
                "course_code": {"type": "string"},
            },
        },
    },
    "list_people": {
        "description": "List people (name, roll_num, role). Optional role filter.",
        "parameters": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "student | faculty | admin",
                },
            },
        },
    },
    "get_unmarked_students": {
        "description": "List enrolled students not yet marked for a session.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_date": {"type": "string"},
                "course_id": {"type": "string"},
                "course_code": {"type": "string"},
            },
            "required": ["session_date"],
        },
    },
    "get_today_attendance": {
        "description": "Attendance for today for a student and/or course.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "course_id": {"type": "string"},
                "course_code": {"type": "string"},
            },
        },
    },
    "get_attendance_chart": {
        "description": "Chart-friendly daily attendance series for a student.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string"},
                "course_code": {"type": "string"},
                "date_from": {"type": "string"},
                "date_to": {"type": "string"},
            },
            "required": ["student_id"],
        },
    },
    "add_person": {
        "description": "Admin-only: add a person (name, roll_num, role).",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "roll_num": {"type": "string"},
                "role": {"type": "string", "description": "student | faculty | admin"},
            },
            "required": ["name", "roll_num", "role"],
        },
    },
    "edit_person": {
        "description": "Admin-only: edit a person's name, role, or roll_num.",
        "parameters": {
            "type": "object",
            "properties": {
                "roll_num": {"type": "string"},
                "name": {"type": "string"},
                "role": {"type": "string"},
                "new_roll_num": {"type": "string"},
            },
            "required": ["roll_num"],
        },
    },
    "delete_person": {
        "description": "Admin-only: delete a person (must have no references).",
        "parameters": {
            "type": "object",
            "properties": {"roll_num": {"type": "string"}},
            "required": ["roll_num"],
        },
    },
    "add_course": {
        "description": "Admin-only: create a course with professor_roll.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_code": {"type": "string"},
                "name": {"type": "string"},
                "professor_roll": {"type": "string"},
                "professor_name": {"type": "string"},
                "department": {"type": "string"},
                "min_attendance_percent": {"type": "integer"},
                "planned_sessions": {"type": "integer"},
            },
            "required": ["course_code", "name", "professor_roll"],
        },
    },
    "edit_course": {
        "description": "Admin-only: update course fields.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_code": {"type": "string"},
                "name": {"type": "string"},
                "professor_roll": {"type": "string"},
                "professor_name": {"type": "string"},
                "department": {"type": "string"},
                "min_attendance_percent": {"type": "integer"},
                "planned_sessions": {"type": "integer"},
                "new_course_code": {"type": "string"},
            },
            "required": ["course_code"],
        },
    },
    "delete_course": {
        "description": "Admin-only: delete a course and its enrollments/attendance.",
        "parameters": {
            "type": "object",
            "properties": {"course_code": {"type": "string"}},
            "required": ["course_code"],
        },
    },
    "add_enrollment": {
        "description": "Admin-only: enroll a student in a course.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_roll": {"type": "string"},
                "course_code": {"type": "string"},
            },
            "required": ["student_roll", "course_code"],
        },
    },
    "delete_enrollment": {
        "description": "Admin-only: remove a student enrollment.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_roll": {"type": "string"},
                "course_code": {"type": "string"},
            },
            "required": ["student_roll", "course_code"],
        },
    },
    "list_enrollments": {
        "description": "List enrollments (optional student_roll / course_code filter).",
        "parameters": {
            "type": "object",
            "properties": {
                "student_roll": {"type": "string"},
                "course_code": {"type": "string"},
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


SYSTEM_PROMPT = """You are the Attendance Agent for a campus assistant.

Caller identity is in the authenticated identity message. Treat it as
authoritative, and be helpful with reasonable inferences (today, this week,
this course).

Identity model:
- people: name, roll_num, role (student | faculty | admin).
- Students use rolls like 2501CS09. Faculty use PF001, PF002, ... Admins use AD001, AD002, ...
- Courses store a distinct professor_name and professor_roll.
- Enrollments and attendance store the person's name next to their roll.

Rules:
- Use the tools available for this role. Tool-side checks are authoritative.
- Always use metadata.roll_num as the caller's id.
- Students: query their own attendance. Pass roll_num as student_id.
- Faculty: mark/edit/delete only for courses they own
  (courses.professor_roll = their roll_num). Pass roll_num as professor_id.
- Admins can query broadly and manage people, courses, and enrollments.
- Prefer a small set of tool calls, then answer clearly using names and rolls
  from the tool results. If a tool returns an error, explain it in plain language.
"""


def _enforce_identity(role: str, metadata: dict[str, Any], name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Force identity fields so the model cannot escalate privileges."""
    cleaned = dict(args or {})
    roll = metadata.get("roll_num")
    if not roll:
        raise PermissionError("metadata.roll_num is required")

    if role == "student":
        if "student_id" in cleaned or name in {
            "get_attendance",
            "get_weekly_attendance",
            "get_attendance_summary",
            "get_skip_budget",
            "get_monthly_attendance",
            "get_semester_attendance",
            "get_consecutive_absences",
            "get_attendance_chart",
            "get_today_attendance",
            "list_courses",
        }:
            cleaned["student_id"] = roll
            if name == "list_courses":
                cleaned.pop("professor_id", None)
        if name.startswith("mark_") or name in {"edit_attendance", "delete_attendance"}:
            raise PermissionError("Students cannot mark or modify attendance.")

    if role == "faculty":
        if name in {
            "mark_attendance",
            "mark_students_attendance",
            "mark_class_attendance",
            "edit_attendance",
            "delete_attendance",
            "get_at_risk_students",
        }:
            cleaned["professor_id"] = roll
        if name == "list_courses" and not cleaned.get("student_id"):
            cleaned["professor_id"] = roll

    if role == "admin":
        # Admin queries use their roll_num only when a person id is needed;
        # write tools still need an explicit professor_id (faculty roll) unless provided.
        pass

    if name not in ROLE_TOOLS[role]:
        raise PermissionError(f"Role {role!r} cannot use tool {name!r}.")

    return cleaned


def _call_tool(name: str, args: dict[str, Any]) -> Any:
    fn = TOOL_IMPL.get(name)
    if fn is None:
        return {"status": "error", "message": f"Unknown tool: {name}"}
    try:
        return fn(**args)
    except TypeError as exc:
        return {"status": "error", "message": f"Bad arguments for {name}: {exc}"}
    except Exception as exc:  # noqa: BLE001 — surface to agent loop
        return {"status": "error", "message": str(exc)}


def run_attendance_agent(
    query: str,
    metadata: dict[str, Any],
    *,
    max_rounds: int = 6,
) -> dict[str, Any]:
    """Run the attendance agent for one user query.

    metadata (required):
        {"name": "Aarav Sharma", "roll_num": "2501CS09", "role": "student"}
        {"name": "Priya Patel", "roll_num": "PF001", "role": "faculty"}
        {"name": "Rohan Verma", "roll_num": "AD001", "role": "admin"}
    """
    role = _normalize_role(str(metadata.get("role", "")))
    if not metadata.get("roll_num"):
        raise ValueError("metadata.roll_num is required")
    # Normalize aliases so tools keep working with student_id/professor_id params.
    roll = str(metadata["roll_num"]).strip()
    metadata = {
        **metadata,
        "role": role,
        "roll_num": roll,
        "student_id": roll if role == "student" else metadata.get("student_id"),
        "professor_id": roll if role == "faculty" else metadata.get("professor_id"),
        "user_id": roll if role == "admin" else metadata.get("user_id"),
    }

    openai_tools = _openai_tools_for_role(role)

    messages: list[dict[str, Any]] = [
        cached_system_message(SYSTEM_PROMPT),
        identity_message(
            {
                "name": metadata.get("name"),
                "roll_num": roll,
                "role": role,
                "Time and Date": metadata.get("Time and Date"),
            },
            label="Authenticated caller identity",
        ),
        {"role": "user", "content": query},
    ]

    tool_trace: list[dict[str, Any]] = []

    for _ in range(max_rounds):
        response = chat_create(
            cache_key=f"attendance-{role}",
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


class AttendanceAgent:
    """UNIHELP wrapper: maps campus metadata and returns a string reply."""

    def chat(self, user_input, user_metadata) -> str:
        user_metadata = user_metadata or {}
        metadata = {
            "role": user_metadata.get("role"),
            "name": user_metadata.get("name"),
            "roll_num": user_metadata.get("roll_number")
            or user_metadata.get("roll_num"),
            "Time and Date": user_metadata.get("Time and Date"),
        }
        try:
            result = run_attendance_agent(user_input, metadata)
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

    parser = argparse.ArgumentParser(description="Run the attendance agent from the terminal.")
    parser.add_argument("query", nargs="?", help="Natural-language attendance question")
    parser.add_argument("--name", required=True, help="Person name")
    parser.add_argument("--roll-num", required=True, help="Universal roll number")
    parser.add_argument(
        "--role",
        choices=["student", "faculty", "admin"],
        required=True,
        help="Caller role",
    )
    args = parser.parse_args()

    query = args.query or "What is my attendance summary?"
    metadata = {
        "name": args.name,
        "roll_num": args.roll_num,
        "role": args.role,
    }
    result = run_attendance_agent(query, metadata)
    print(json.dumps(result, indent=2, default=str))
