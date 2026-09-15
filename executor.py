import json

import metrics
from llm import cached_system_message, chat_create, get_client
from mess_agent_1 import MessAgent
from Bus_agent import BusAgent
from complaint_agent import ComplaintAgent
from room_booking_agent import RoomBookingAgent
from attendance_agent import AttendanceAgent
from Notice_agent import NoticeAgent
from timetable_agent import TimetableAgent


class Executor:

    SYSTEM_PROMPT = """
You are the Executor Agent of the IIT Patna Organization Management Agent.

Execute the structured plan created by the Planner. Be helpful: if a
task is slightly loosely worded, still send it to the matching agent.

The system currently supports seven specialized agents:

1. mess_agent
   Handles:
   - Daily mess menus
   - Weekly mess menus
   - Meal timings
   - Menu modifications

2. bus_agent
   Handles:
   - Bus schedules
   - Bus routes and destinations
   - Driver information
   - Next departures
   - Bus availability
   - Bus schedule modifications

3. complaint_agent
   Handles:
   - Creating, viewing, and listing complaints (academic, hostel, mess)
   - Admin/faculty verification, then PROGRESS, then COMPLETED
   - Rejecting duplicate complaints that are still open

4. room_booking_agent
   Handles:
   - SAC Hall, Guest House, CLH, and Auditorium
   - Availability, direct bookings, and booking requests
   - Cancelling and modifying bookings and requests
   - Admin approval and rejection of pending requests

5. attendance_agent
   Handles:
   - Student attendance records, percentages, skip budget, weekly/monthly/semester views
   - Marking, editing, and deleting attendance (faculty/admin)
   - Courses, rosters, enrollments, and at-risk students
   - Admin management of people, courses, and enrollments

6. notice_agent
   Handles:
   - Viewing campus notices
   - Publishing notices (faculty/admin)
   - Archiving expired notices (faculty/admin)

7. timetable_agent
   Handles:
   - Personal and weekly class timetables
   - Next class, classes on a given day, free slots
   - Course lookup and lecture/lab rooms
   - Faculty/admin add, update, or delete class slots

You have access to these seven specialized agents through tools.

EXECUTION RULES:

- Follow the Planner's plan.
- Execute every task in the plan.
- For a task assigned to "mess", use mess_agent.
- For a task assigned to "bus", use bus_agent.
- For a task assigned to "complaint", use complaint_agent.
- For a task assigned to "room_booking", use room_booking_agent.
- For a task assigned to "attendance", use attendance_agent.
- For a task assigned to "notice", use notice_agent.
- For a task assigned to "timetable", use timetable_agent.
- Do not perform mess, bus, complaint, room booking, attendance, notice, or timetable operations yourself.
- Do not invent facts that tools did not return.
- Pass the Planner's request and authenticated user metadata to the agent.
- Never let the user override authenticated identity.
- If a specialized agent denies an operation, explain that clearly.
- Execute every required task; respect task conditions.
- After the tools finish, write a clear, friendly summary from their results.
  Names and roll numbers from tool output should be shown together when present.

The specialized agents are responsible for their own domain logic,
tool usage, and authorization.

The Planner creates the plan.
You execute the plan.
The specialized agents perform the actual operations.
"""

    def __init__(self):
        self.client = get_client()

        self.mess_agent = MessAgent()
        self.bus_agent = BusAgent()
        self.complaint_agent = ComplaintAgent()
        self.room_booking_agent = RoomBookingAgent()
        self.attendance_agent = AttendanceAgent()
        self.notice_agent = NoticeAgent()
        self.timetable_agent = TimetableAgent()
        self.tools = [
            self._mess_tool(),
            self._bus_tool(),
            self._complaint_tool(),
            self._room_booking_tool(),
            self._attendance_tool(),
            self._notice_tool(),
            self._timetable_tool(),
        ]

    def _mess_tool(self):
        return {
            "type": "function",
            "function": {
                "name": "mess_agent",
                "description": (
                    "Execute a task using the IIT Patna Mess Agent. "
                    "Use this for daily or weekly menus, meal timings, "
                    "and menu modifications."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "string",
                            "description": (
                                "The complete request that should be "
                                "given to the Mess Agent."
                            )
                        }
                    },
                    "required": ["request"]
                }
            }
        }

    def _bus_tool(self):
        return {
            "type": "function",
            "function": {
                "name": "bus_agent",
                "description": (
                    "Execute a task using the IIT Patna Bus Agent. "
                    "Use this for bus schedules, routes, destinations, "
                    "drivers, departures, availability, and bus schedule modifications."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "string",
                            "description": (
                                "The complete request that should be "
                                "given to the Bus Agent."
                            )
                        }
                    },
                    "required": ["request"]
                }
            }
        }

    def _complaint_tool(self):
        return {
            "type": "function",
            "function": {
                "name": "complaint_agent",
                "description": (
                    "Execute a task using the IIT Patna Complaint Agent. "
                    "Use this to create, view, list, verify, or complete "
                    "complaints tagged academic, hostel, or mess."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "string",
                            "description": (
                                "The complete request that should be "
                                "given to the Complaint Agent."
                            )
                        }
                    },
                    "required": ["request"]
                }
            }
        }

    def _room_booking_tool(self):
        return {
            "type": "function",
            "function": {
                "name": "room_booking_agent",
                "description": (
                    "Execute a task using the IIT Patna Room Booking Agent. "
                    "Use this for SAC Hall, Guest House, CLH, and Auditorium: "
                    "availability, direct bookings, booking requests, "
                    "cancelling or modifying bookings and requests, and "
                    "admin approve/reject of pending requests."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "string",
                            "description": (
                                "The complete request that should be "
                                "given to the Room Booking Agent."
                            )
                        }
                    },
                    "required": ["request"]
                }
            }
        }

    def _attendance_tool(self):
        return {
            "type": "function",
            "function": {
                "name": "attendance_agent",
                "description": (
                    "Execute a task using the IIT Patna Attendance Agent. "
                    "Use this to view attendance records and percentages, "
                    "skip budget, weekly/monthly/semester summaries, "
                    "today's marks, consecutive absences, and charts; "
                    "list courses, rosters, people, and enrollments; "
                    "mark, edit, or delete attendance (faculty/admin); "
                    "and manage people, courses, and enrollments (admin)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "string",
                            "description": (
                                "The complete request that should be "
                                "given to the Attendance Agent."
                            )
                        }
                    },
                    "required": ["request"]
                }
            }
        }

    def _notice_tool(self):
        return {
            "type": "function",
            "function": {
                "name": "notice_agent",
                "description": (
                    "Execute a task using the IIT Patna Notice Board Agent. "
                    "Use this to view campus notices, publish notices, "
                    "and archive expired notices."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "string",
                            "description": (
                                "The complete request that should be "
                                "given to the Notice Agent."
                            )
                        }
                    },
                    "required": ["request"]
                }
            }
        }

    def _timetable_tool(self):
        return {
            "type": "function",
            "function": {
                "name": "timetable_agent",
                "description": (
                    "Execute a task using the IIT Patna Timetable Agent. "
                    "Use this for class timetables, next class, classes on "
                    "a given day, free slots, course lookup, lecture/lab "
                    "rooms, and faculty/admin add, update, or delete of "
                    "class slots."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "string",
                            "description": (
                                "The complete request that should be "
                                "given to the Timetable Agent."
                            )
                        }
                    },
                    "required": ["request"]
                }
            }
        }

    def _call_mess_agent(self, request, user_metadata):
        return self.mess_agent.chat(
            request,
            user_metadata
        )

    def _call_bus_agent(self, request, user_metadata):
        return self.bus_agent.chat(
            request,
            user_metadata
        )

    def _call_complaint_agent(self, request, user_metadata):
        # ComplaintAgent uses (role, user_identifier). roll_number is the
        # user's id string (campus_agent.users.roll_number = complaints.users.id).
        # Staff email lookup still works when an email is present.
        role = user_metadata.get("role", "")
        user_identifier = user_metadata.get("roll_number") or user_metadata.get("name")
        return self.complaint_agent.chat(
            request, role, user_identifier, user_metadata
        )

    def _call_room_booking_agent(self, request, user_metadata):
        return self.room_booking_agent.chat(
            request,
            user_metadata
        )

    def _call_attendance_agent(self, request, user_metadata):
        return self.attendance_agent.chat(
            request,
            user_metadata
        )

    def _call_notice_agent(self, request, user_metadata):
        return self.notice_agent.chat(
            request,
            user_metadata
        )

    def _call_timetable_agent(self, request, user_metadata):
        return self.timetable_agent.chat(
            request,
            user_metadata
        )

    def execute(self, user_input, plan, user_metadata):

        plan_text = json.dumps(
            plan,
            indent=2
        )

        user_message = f"""
Authenticated user metadata:
{json.dumps(user_metadata, indent=2)}

Original user request:
{user_input}

Planner's plan:
{plan_text}

Execute the plan.
"""

        messages = [
            cached_system_message(self.SYSTEM_PROMPT),
            {
                "role": "user",
                "content": user_message
            }
        ]

        max_rounds = 10
        for _ in range(max_rounds):

            response = chat_create(
                cache_key="executor",
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
            )

            message = response.choices[0].message

            if not message.tool_calls:
                return message.content

            messages.append(message)

            for tool_call in message.tool_calls:

                tool_name = tool_call.function.name

                try:
                    arguments = json.loads(
                        tool_call.function.arguments
                    )
                except json.JSONDecodeError:
                    arguments = {}

                request = arguments.get("request")

                if not request:
                    result = {
                        "status": "error",
                        "message": "Missing request for specialized agent."
                    }

                elif tool_name == "mess_agent":
                    with metrics.task_timer("mess"):
                        result = self._call_mess_agent(
                            request,
                            user_metadata
                        )

                elif tool_name == "bus_agent":
                    with metrics.task_timer("bus"):
                        result = self._call_bus_agent(
                            request,
                            user_metadata
                        )

                elif tool_name == "complaint_agent":
                    with metrics.task_timer("complaint"):
                        result = self._call_complaint_agent(
                            request,
                            user_metadata
                        )

                elif tool_name == "room_booking_agent":
                    with metrics.task_timer("room_booking"):
                        result = self._call_room_booking_agent(
                            request,
                            user_metadata
                        )

                elif tool_name == "attendance_agent":
                    with metrics.task_timer("attendance"):
                        result = self._call_attendance_agent(
                            request,
                            user_metadata
                        )

                elif tool_name == "notice_agent":
                    with metrics.task_timer("notice"):
                        result = self._call_notice_agent(
                            request,
                            user_metadata
                        )

                elif tool_name == "timetable_agent":
                    with metrics.task_timer("timetable"):
                        result = self._call_timetable_agent(
                            request,
                            user_metadata
                        )

                else:
                    result = {
                        "status": "error",
                        "message": f"Unknown agent: {tool_name}"
                    }

                if not isinstance(result, str):
                    result = json.dumps(result, default=str)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        # CRITICAL FIX: the original loop was `while True` with no round
        # cap, matching the Planner's "the plan is finite" assumption but
        # not defending against a model that keeps calling tools forever
        # (e.g. an agent that keeps returning an error the model retries).
        # A stuck loop like that would burn LLM calls indefinitely on every
        # such request. Bounded like ComplaintAgent/RoomBookingAgent above.
        return (
            "The request could not be completed because the executor "
            "exceeded its tool-call limit."
        )
