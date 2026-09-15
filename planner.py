import json
import re

from llm import cached_system_message, chat_create, get_client


class Planner:

    def __init__(self):
        self.client = get_client()

    # The original prompt carried ~10 worked examples, most of which taught
    # the same single rule ("mess words -> mess agent"). Every example is
    # resent on every request, so they were a fixed per-request token cost
    # for very little routing benefit. Trimmed to one example per agent plus
    # one multi-task example — the cases that actually teach something
    # distinct. Keep this prompt a stable, unchanging string: identical
    # prefixes are what let the gateway (and most inference servers) reuse a
    # cached prefix instead of reprocessing it.
    SYSTEM_PROMPT = """
You are the planner of the IIT Patna Organization Management Agent.

Break the user's natural-language request into simple tasks and assign
each task to the appropriate specialized agent. Route generously: if the
intent is close to a supported service, send it there rather than
refusing. Ambiguous or mixed requests may become multiple tasks.

Supported agents: mess, bus, complaint, room_booking, attendance, notice, timetable

Do not decide authorization yourself. Specialized agents handle domain
logic and access control. If a request could reasonably be served, plan it.

For every task provide:
1. agent      - the specialized agent responsible
2. request    - a clear, self-contained request for that agent
3. condition  - dependency on a previous task, or null

AGENT RESPONSIBILITIES

mess:
- Daily and weekly mess menus, food served in a hostel
- Breakfast, lunch, snacks, dinner menus; meal timings
- Authorized mess menu modifications

bus:
- Bus availability, schedules, routes, destinations
- Driver information, next departures
- Authorized bus schedule modifications

complaint:
- Creating, viewing, and listing complaints
- Admin/faculty verification then PROGRESS then COMPLETED
- Categories: academic, hostel, mess
- Duplicate open complaints are not logged again

room_booking:
- SAC Hall, Guest House, CLH, and Auditorium
- Availability checks, direct bookings, and booking requests
- Cancelling and modifying bookings and requests
- Admin approval and rejection of pending requests

attendance:
- Viewing attendance records, percentages, skip budget, and charts
- Weekly, monthly, semester, and today's attendance
- Faculty/admin marking, editing, and deleting attendance
- Courses, rosters, enrollments, at-risk students
- Admin management of people, courses, and enrollments

notice:
- Viewing the campus notice board
- Publishing notices (faculty/admin)
- Archiving expired notices (faculty/admin)

timetable:
- Personal and weekly class timetables, next class, and free slots
- Classes on a given day, course lookup, room list for lectures/labs
- Faculty/admin add, update, or delete class slots

DISAMBIGUATION
- A request to SEE the menu is "mess". A request to COMPLAIN about food
  quality is "complaint" with category mess.
- A request about bus timings is "bus". A complaint about a bus not
  arriving is "complaint".
- Hostel facilities (water, electricity, rooms) are "complaint" with
  category hostel. Classes, exams, or faculty issues are category academic.
- Checking attendance, marks present/absent, skip budget, or course
  enrollment is "attendance". Complaining about a class, faculty, or
  being marked wrongly as a grievance is "complaint" with category academic.
- Viewing, publishing, or archiving campus notices is "notice".
  Complaining about a notice or announcement is "complaint".
- Class timetable, next lecture/lab, or "what classes do I have" is
  "timetable". A bus timetable is "bus". Booking SAC/Guest House/CLH/
  Auditorium is "room_booking", not timetable.

EXAMPLES

User: "What is for dinner in Kalam today?"
{"tasks":[{"agent":"mess","request":"Tell me today's dinner menu for Kalam hostel","condition":null}]}

User: "When is the next bus from Aryabhatta to Tut Block?"
{"tasks":[{"agent":"bus","request":"Find the next bus from Aryabhatta to Tut Block","condition":null}]}

User: "The water cooler on my floor is broken"
{"tasks":[{"agent":"complaint","request":"Create a hostel complaint about a broken water cooler","condition":null}]}

User: "Book SAC Hall on 2030-02-10 from 10 to 11 for a club meeting"
{"tasks":[{"agent":"room_booking","request":"Book SAC Hall on 2030-02-10 from 10 to 11 for a club meeting","condition":null}]}

User: "What is my attendance percentage in CS101?"
{"tasks":[{"agent":"attendance","request":"Show my attendance percentage for CS101","condition":null}]}

User: "Show me the current notices"
{"tasks":[{"agent":"notice","request":"Show me the current notices","condition":null}]}

User: "What is my class timetable today?"
{"tasks":[{"agent":"timetable","request":"Show my class timetable for today","condition":null}]}

User: "Tell me today's dinner at Kalam and the Bus 02 schedule"
{"tasks":[{"agent":"mess","request":"Tell me today's dinner menu for Kalam hostel","condition":null},{"agent":"bus","request":"Show me the Bus 02 schedule","condition":null}]}

If a task depends on another, place it after that task and describe the
dependency in condition.

If the request is clearly unrelated to campus services, return:
{"tasks":[],"status":"unsupported","message":"This service is not currently available."}
Otherwise prefer a best-effort plan over an empty one.

Return ONLY valid JSON.
"""

    # Cheap keyword routing for the overwhelmingly common case: a request
    # that clearly belongs to exactly one agent. When it fires we skip the
    # planner LLM call entirely, removing one full round-trip (and its
    # prompt tokens) from the critical path. Anything ambiguous, empty, or
    # matching more than one domain falls through to the LLM planner, so
    # this only ever shortcuts the unambiguous cases.
    _FAST_PATH_KEYWORDS = {
        "mess": (
            "menu", "breakfast", "lunch", "dinner", "snacks", "mess timing",
            "meal timing", "weekly menu",
        ),
        "bus": (
            "bus", "shuttle", "departure", "driver", "route",
        ),
        "complaint": (
            "complaint", "complain", "broken", "not working", "leaking",
            "grievance",
        ),
        "room_booking": (
            "book a room", "room booking", "booking", "clh", "seminar hall",
            "classroom", "sac hall", "guest house", "auditorium", "guest house",
        ),
        "attendance": (
            "attendance", "skip budget", "mark attendance",
            "enrollment", "at-risk", "unmarked", "roster",
        ),
        "notice": (
            "notice", "notices", "notice board", "bulletin",
        ),
        "timetable": (
            "timetable", "class schedule", "next class", "my classes",
            "classes on", "lecture slot",
        ),
    }

    def _fast_path_plan(self, user_input):
        text = (user_input or "").lower()
        if not text.strip():
            return None

        matched = {
            agent
            for agent, keywords in self._FAST_PATH_KEYWORDS.items()
            if any(k in text for k in keywords)
        }

        # Exactly one domain matched -> unambiguous, safe to skip the LLM.
        if len(matched) != 1:
            return None

        agent = matched.pop()
        return {
            "tasks": [
                {"agent": agent, "request": user_input, "condition": None}
            ]
        }

    @staticmethod
    def _parse_plan(content):
        """Parse the planner's JSON reply defensively.

        The original code called json.loads() directly on the model output,
        so any stray prose or ```json fence raised JSONDecodeError straight
        out of create_plan() and produced a 500 rather than a usable reply.
        """
        if not content:
            return {"tasks": [], "status": "unsupported",
                    "message": "This service is not currently available."}

        content = content.strip()
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Last resort: pull the outermost {...} block out of any surrounding
        # prose the model may have added.
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return {"tasks": [], "status": "unsupported",
                "message": "This service is not currently available."}

    def create_plan(self, user_input):

        fast_plan = self._fast_path_plan(user_input)
        if fast_plan is not None:
            return fast_plan

        messages = [
            cached_system_message(self.SYSTEM_PROMPT),
            {"role": "user", "content": user_input},
        ]

        # Ask for guaranteed-JSON output when the gateway supports it; fall
        # back transparently if this particular model/gateway rejects the
        # parameter.
        try:
            response = chat_create(
                cache_key="planner",
                messages=messages,
                response_format={"type": "json_object"},
            )
        except Exception:
            response = chat_create(cache_key="planner", messages=messages)

        return self._parse_plan(response.choices[0].message.content)
