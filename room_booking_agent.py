# room_agent.py
from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

from llm import cached_system_message, chat_create, get_client, identity_message
from room_functions import (
    approve_request,
    cancel_booking,
    cancel_request,
    check_availability,
    create_direct_booking,
    create_request,
    get_booking,
    get_request,
    list_all_pending_requests,
    list_facilities,
    list_my_bookings,
    list_my_requests,
    modify_booking,
    modify_request,
    reject_request,
)

SYSTEM_PROMPT = """
You are the Room Booking Agent for an institution.

You handle only:
1. SAC Hall
2. Guest House
3. CLH
4. Auditorium

AUTHORITY RULES
- SAC Hall: students can book directly. Faculty and admin cannot book it.
- Guest House: students, faculty, and admin can book directly. Other roles cannot.
- CLH: faculty/admin can book directly. Students must submit a request.
- Auditorium: admin can book directly. Students/faculty must submit a request.
- Never ask the user for their role. Role comes from authenticated metadata.
- Never allow the user to override authenticated role.
- Current Time and Date (IST) is in authenticated metadata. Use it for "today", "now", and relative dates.

TIME RULES
- SAC Hall: exactly 1 hour; start/end must be integer hours; 24x7.
- CLH: exactly 1 hour; start/end must be integer hours.
- Auditorium: exactly 3 hours; start/end must be integer hours.
- Guest House: date-based, using check-in/check-out dates.
- Guest House does not require a purpose.
- Never invent availability. Use tools.

TOOL USAGE RULES
- Use list_facilities only when the user asks what facilities are available.
- If the user explicitly names a facility, do NOT call list_facilities.
- For a direct booking request, use create_direct_booking when the authenticated role permits it.
- For a request-based booking, use create_request.
- After a tool returns a successful result, respond to the user instead of repeating the same tool call.
- Never call the same tool with the same arguments repeatedly.

SAC HALL
- Task/purpose is required.
- Booking identity is the authenticated user's name and roll number.

REQUESTS
- Student CLH bookings are requests.
- Student/faculty Auditorium bookings are requests.
- Pending requests can be inspected, cancelled, and shifted.
- Admin can approve/reject pending requests.
- Approval creates the actual booking.
- A request itself does not reserve a room permanently; approval rechecks availability.

BOOKINGS
- A confirmed booking can be inspected, cancelled, and shifted by its owner.
- Admin can manage bookings.
- Never claim a booking or request succeeded unless the tool result says it succeeded.

STYLE
- Answer only what the user asked.
- Keep answers concise.
- Do not expose database or tool implementation details.
- Do not add recommendations, greetings, or unrelated information.
- When a tool returns "Not in your authority.", return exactly that.
- Ask for clarification only when a required booking detail is genuinely missing.
"""

client = get_client()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_facilities",
            "description": (
                "List the available facilities and room counts. "
                "Use this tool only when the user asks what facilities are available. "
                "Do not use it when the user has already named a specific facility."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check available rooms/facilities for a requested time or Guest House stay.",
            "parameters": {
                "type": "object",
                "properties": {
                    "facility": {"type": "string"},
                    "booking_date": {"type": "string", "description": "YYYY-MM-DD for hourly facilities"},
                    "start_hour": {"type": "integer", "description": "0-23 integer hour"},
                    "duration_hours": {"type": "integer", "description": "1 for SAC/CLH, 3 for Auditorium"},
                    "check_in": {"type": "string", "description": "YYYY-MM-DD for Guest House"},
                    "check_out": {"type": "string", "description": "YYYY-MM-DD for Guest House"},
                    "room_type": {"type": "string", "description": "SINGLE or DOUBLE for Guest House"},
                },
                "required": ["facility"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_direct_booking",
            "description": "Create a direct booking when the authenticated role allows it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "facility": {"type": "string"},
                    "purpose": {"type": "string"},
                    "room_code": {"type": "string"},
                    "booking_date": {"type": "string"},
                    "start_hour": {"type": "integer"},
                    "duration_hours": {"type": "integer"},
                    "check_in": {"type": "string"},
                    "check_out": {"type": "string"},
                    "guest_name": {"type": "string"},
                    "room_type": {"type": "string"},
                },
                "required": ["facility"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_request",
            "description": "Submit an approval request for CLH or Auditorium when the authenticated role requires a request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "facility": {"type": "string"},
                    "purpose": {"type": "string"},
                    "room_code": {"type": "string"},
                    "booking_date": {"type": "string"},
                    "start_hour": {"type": "integer"},
                    "duration_hours": {"type": "integer"},
                },
                "required": ["facility"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_my_bookings",
            "description": "List the authenticated user's bookings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_cancelled": {"type": "boolean"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_my_requests",
            "description": "List the authenticated user's room booking requests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_closed": {"type": "boolean"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_booking",
            "description": "Get one booking by booking ID. Users can only access their own bookings; admin can access any.",
            "parameters": {
                "type": "object",
                "properties": {"booking_id": {"type": "integer"}},
                "required": ["booking_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_request",
            "description": "Get one request by request ID. Users can only access their own requests; admin can access any.",
            "parameters": {
                "type": "object",
                "properties": {"request_id": {"type": "integer"}},
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancel a confirmed booking owned by the caller or managed by admin.",
            "parameters": {
                "type": "object",
                "properties": {"booking_id": {"type": "integer"}},
                "required": ["booking_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_request",
            "description": "Cancel a pending booking request owned by the caller or managed by admin.",
            "parameters": {
                "type": "object",
                "properties": {"request_id": {"type": "integer"}},
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modify_booking",
            "description": "Shift/move a confirmed booking. Duration rules cannot be changed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {"type": "integer"},
                    "booking_date": {"type": "string"},
                    "start_hour": {"type": "integer"},
                    "check_in": {"type": "string"},
                    "check_out": {"type": "string"},
                    "room_code": {"type": "string"},
                },
                "required": ["booking_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modify_request",
            "description": "Shift a pending CLH/Auditorium request before approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "integer"},
                    "booking_date": {"type": "string"},
                    "start_hour": {"type": "integer"},
                    "room_code": {"type": "string"},
                },
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_pending_requests",
            "description": "Admin-only list of all pending requests.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "approve_request",
            "description": "Admin-only approval of a pending request. Rechecks availability and creates a booking.",
            "parameters": {
                "type": "object",
                "properties": {"request_id": {"type": "integer"}},
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reject_request",
            "description": "Admin-only rejection of a pending request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "integer"},
                    "reason": {"type": "string"},
                },
                "required": ["request_id"],
            },
        },
    },
]

FUNCTIONS = {
    "list_facilities": lambda a, u: list_facilities(),
    "check_availability": lambda a, u: check_availability(
        facility=a["facility"],
        booking_date=date.fromisoformat(a["booking_date"]) if a.get("booking_date") else None,
        start_hour=a.get("start_hour"),
        duration_hours=a.get("duration_hours"),
        check_in=date.fromisoformat(a["check_in"]) if a.get("check_in") else None,
        check_out=date.fromisoformat(a["check_out"]) if a.get("check_out") else None,
        room_type=a.get("room_type"),
    ),
    "create_direct_booking": lambda a, u: create_direct_booking(
        facility=a["facility"],
        user=u,
        purpose=a.get("purpose"),
        room_code=a.get("room_code"),
        booking_date=date.fromisoformat(a["booking_date"]) if a.get("booking_date") else None,
        start_hour=a.get("start_hour"),
        duration_hours=a.get("duration_hours"),
        check_in=date.fromisoformat(a["check_in"]) if a.get("check_in") else None,
        check_out=date.fromisoformat(a["check_out"]) if a.get("check_out") else None,
        guest_name=a.get("guest_name"),
        room_type=a.get("room_type"),
    ),
    "create_request": lambda a, u: create_request(
        facility=a["facility"],
        user=u,
        purpose=a.get("purpose"),
        room_code=a.get("room_code"),
        booking_date=date.fromisoformat(a["booking_date"]) if a.get("booking_date") else None,
        start_hour=a.get("start_hour"),
        duration_hours=a.get("duration_hours"),
    ),
    "list_my_bookings": lambda a, u: list_my_bookings(u, a.get("include_cancelled", False)),
    "list_my_requests": lambda a, u: list_my_requests(u, a.get("include_closed", False)),
    "get_booking": lambda a, u: get_booking(a["booking_id"], u),
    "get_request": lambda a, u: get_request(a["request_id"], u),
    "cancel_booking": lambda a, u: cancel_booking(a["booking_id"], u),
    "cancel_request": lambda a, u: cancel_request(a["request_id"], u),
    "modify_booking": lambda a, u: modify_booking(
        booking_id=a["booking_id"],
        user=u,
        booking_date=date.fromisoformat(a["booking_date"]) if a.get("booking_date") else None,
        start_hour=a.get("start_hour"),
        check_in=date.fromisoformat(a["check_in"]) if a.get("check_in") else None,
        check_out=date.fromisoformat(a["check_out"]) if a.get("check_out") else None,
        room_code=a.get("room_code"),
    ),
    "modify_request": lambda a, u: modify_request(
        request_id=a["request_id"],
        user=u,
        booking_date=date.fromisoformat(a["booking_date"]) if a.get("booking_date") else None,
        start_hour=a.get("start_hour"),
        room_code=a.get("room_code"),
    ),
    "list_all_pending_requests": lambda a, u: list_all_pending_requests(u),
    "approve_request": lambda a, u: approve_request(a["request_id"], u),
    "reject_request": lambda a, u: reject_request(a["request_id"], u, a.get("reason")),
}


class RoomAgent:
    def __init__(self):
        self.client = client

    def chat(self, user_input: str, user_metadata: dict[str, Any]) -> str:
        if not user_metadata or not user_metadata.get("role"):
            return "ERROR: Authentication metadata missing."

        messages = [
            cached_system_message(SYSTEM_PROMPT),
            identity_message(user_metadata),
            {"role": "user", "content": user_input},
        ]

        all_seen_tool_calls = set()

        for round_no in range(8):
            print(f"\n[DEBUG] Tool round {round_no + 1}")

            response = chat_create(
                cache_key="room_booking",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )

            msg = response.choices[0].message

            print("[DEBUG] Model response:", msg.content)
            print("[DEBUG] Tool calls:", [
                tc.function.name for tc in (msg.tool_calls or [])
            ])

            assistant_message = {
                "role": "assistant",
                "content": msg.content or "",
            }

            if msg.tool_calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]

            messages.append(assistant_message)

            if not msg.tool_calls:
                return (msg.content or "").strip()

            current_tool_calls = set()
            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                raw_args = tool_call.function.arguments or "{}"

                # Normalize JSON arguments so the same call with different
                # whitespace/key ordering is still detected as the same call.
                try:
                    normalized_args = json.dumps(
                        json.loads(raw_args),
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                except Exception:
                    normalized_args = raw_args.strip()

                current_tool_calls.add((name, normalized_args))

            # If the model repeats any exact tool+arguments combination that
            # has already appeared in this chat() call, force a final answer.
            if current_tool_calls & all_seen_tool_calls:
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "You already called this tool with the same arguments "
                            "and its result is above in the conversation. "
                            "Do not call any tool again. Respond to the user now, "
                            "in plain text, using the available results."
                        ),
                    }
                )

                print("[DEBUG] Repeated tool call detected; forcing final response.")

                recovery_response = chat_create(
                    cache_key="room_booking",
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="none",
                )
                recovery_msg = recovery_response.choices[0].message

                print("[DEBUG] Recovery response:", recovery_msg.content)

                return (recovery_msg.content or "").strip()

            all_seen_tool_calls |= current_tool_calls

            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                    if name not in FUNCTIONS:
                        result = {"status": "error", "message": "Unknown room operation."}
                    else:
                        result = FUNCTIONS[name](args, user_metadata)
                except Exception as exc:
                    result = {"status": "error", "message": str(exc)}

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str),
                    }
                )

        return "ERROR: Room Agent exceeded the maximum number of tool rounds."


RoomBookingAgent = RoomAgent


if __name__ == "__main__":
    agent = RoomAgent()

    student = {
        "role": "student",
        "name": "Test Student",
        "roll_number": "TEST001",
    }

    faculty = {
        "role": "faculty",
        "name": "Test Faculty",
        "roll_number": "FAC001",
    }

    admin = {
        "role": "admin",
        "name": "Test Admin",
        "roll_number": "ADM001",
    }

    visitor = {
        "role": "visitor",
        "name": "Test Visitor",
        "roll_number": "VIS001",
    }

    # print("\n================ TEST 1 ================")
    # print("Student asks for available facilities")
    # print(agent.chat(
    #     "What facilities are available?",
    #     student
    # ))

    # print("\n================ TEST 2 ================")
    # print("Student books SAC Hall for 1 hour")
    # print(agent.chat(
    #     "Book SAC Hall on 2030-02-10 from 10 to 11 for a student club meeting.",
    #     student
    # ))

    # print("\n================ TEST 3 ================")
    # print("Student tries SAC Hall for 2 hours")
    # print(agent.chat(
    #     "Book SAC Hall on 2030-02-10 from 12 to 14 for a student event.",
    #     student
    # ))

    # print("\n================ TEST 4 ================")
    # print("Faculty tries to directly book SAC Hall")
    # print(agent.chat(
    #     "Book SAC Hall on 2030-02-11 from 10 to 11 for a meeting.",
    #     faculty
    # ))

    # print("\n================ TEST 5 ================")
    # print("Student requests CLH")
    # print(agent.chat(
    #     "I need CLH on 2030-02-12 from 14 to 15 for a student meeting.",
    #     student
    # ))

    # print("\n================ TEST 6 ================")
    # print("Faculty directly books CLH")
    # print(agent.chat(
    #     "Book CLH on 2030-02-13 from 10 to 11 for a faculty meeting.",
    #     faculty
    # ))

    # print("\n================ TEST 7 ================")
    # print("Student requests Auditorium")
    # print(agent.chat(
    #     "I need the Auditorium on 2030-02-14 from 10 to 13 for a student event.",
    #     student
    # ))

    # print("\n================ TEST 8 ================")
    # print("Admin directly books Auditorium")
    # print(agent.chat(
    #     "Book the Auditorium on 2030-02-15 from 14 to 17 for an official event.",
    #     admin
    # ))

    # print("\n================ TEST 9 ================")
    # print("Student books Guest House")
    # print(agent.chat(
    #     "Book a single Guest House room from 2030-02-20 to 2030-02-22.",
    #     student
    # ))

    # print("\n================ TEST 10 ================")
    # print("Visitor tries to book Guest House")
    # print(agent.chat(
    #     "Book a single Guest House room from 2030-02-20 to 2030-02-22.",
    #     visitor
    # ))

    # print("\n================ TEST 11 ================")
    # print("Student asks to see their bookings")
    # print(agent.chat(
    #     "Show me my room bookings.",
    #     student
    # ))

    # print("\n================ TEST 12 ================")
    # print("Student asks to see their requests")
    # print(agent.chat(
    #     "Show me my pending room booking requests.",
    #     student
    # ))