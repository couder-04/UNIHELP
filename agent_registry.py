"""In-repo agent registry: one spec per domain agent.

This is the lightweight seed of the design-doc pack directory — planner,
executor, and the agent card read from here instead of each hardcoding the
same seven names. Agents themselves stay in their current modules; the
chat(user_input, user_metadata) contract is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

import org_profile

CallFn = Callable[[str, dict[str, Any]], Any]


@dataclass(frozen=True)
class AgentSpec:
    name: str
    call: CallFn
    keywords: tuple[str, ...]
    planner_blurb: str
    roles: tuple[str, ...]
    skill_title: str
    skill_bullets: tuple[str, ...]
    skill_tags: tuple[str, ...]


_agent_instances: dict[str, Any] = {}


def _agent(name: str, factory: Callable[[], Any]) -> Any:
    inst = _agent_instances.get(name)
    if inst is None:
        inst = factory()
        _agent_instances[name] = inst
    return inst


def _call_mess(request: str, user_metadata: dict[str, Any]) -> Any:
    from mess_agent_1 import MessAgent

    return _agent("mess", MessAgent).chat(request, user_metadata)


def _call_bus(request: str, user_metadata: dict[str, Any]) -> Any:
    from Bus_agent import BusAgent

    return _agent("bus", BusAgent).chat(request, user_metadata)


def _call_complaint(request: str, user_metadata: dict[str, Any]) -> Any:
    from complaint_agent import ComplaintAgent

    # ComplaintAgent uses (role, user_identifier). roll_number is the
    # user's id string (campus_agent.users.roll_number = complaints.users.id).
    # Staff email lookup still works when an email is present.
    role = user_metadata.get("role", "")
    user_identifier = user_metadata.get("roll_number") or user_metadata.get("name")
    return _agent("complaint", ComplaintAgent).chat(
        request, role, user_identifier, user_metadata
    )


def _call_room_booking(request: str, user_metadata: dict[str, Any]) -> Any:
    from room_booking_agent import RoomBookingAgent

    return _agent("room_booking", RoomBookingAgent).chat(request, user_metadata)


def _call_attendance(request: str, user_metadata: dict[str, Any]) -> Any:
    from attendance_agent import AttendanceAgent

    return _agent("attendance", AttendanceAgent).chat(request, user_metadata)


def _call_notice(request: str, user_metadata: dict[str, Any]) -> Any:
    from Notice_agent import NoticeAgent

    return _agent("notice", NoticeAgent).chat(request, user_metadata)


def _call_timetable(request: str, user_metadata: dict[str, Any]) -> Any:
    from timetable_agent import TimetableAgent

    return _agent("timetable", TimetableAgent).chat(request, user_metadata)


def _call_setup(request: str, user_metadata: dict[str, Any]) -> Any:
    from setup_agent import SetupAgent

    return _agent("setup", SetupAgent).chat(request, user_metadata)


def _call_custom(slug: str) -> CallFn:
    def _call(request: str, user_metadata: dict[str, Any]) -> Any:
        from custom_feature_agent import CustomFeatureAgent

        return _agent(f"feature:{slug}", lambda: CustomFeatureAgent(slug)).chat(
            request, user_metadata
        )

    return _call


def ensure_agent(name: str) -> None:
    """Instantiate the agent so Executor.__init__ still warms them at startup."""
    if name == "setup":
        from setup_agent import SetupAgent

        _agent("setup", SetupAgent)
        return
    warmer = _CALL_WARMERS.get(name)
    if warmer is not None:
        warmer()
        return
    from custom_features import get_feature
    from custom_feature_agent import CustomFeatureAgent

    if get_feature(name) is not None:
        _agent(f"feature:{name}", lambda: CustomFeatureAgent(name))


def _warm_mess() -> None:
    from mess_agent_1 import MessAgent

    _agent("mess", MessAgent)


def _warm_bus() -> None:
    from Bus_agent import BusAgent

    _agent("bus", BusAgent)


def _warm_complaint() -> None:
    from complaint_agent import ComplaintAgent

    _agent("complaint", ComplaintAgent)


def _warm_room_booking() -> None:
    from room_booking_agent import RoomBookingAgent

    _agent("room_booking", RoomBookingAgent)


def _warm_attendance() -> None:
    from attendance_agent import AttendanceAgent

    _agent("attendance", AttendanceAgent)


def _warm_notice() -> None:
    from Notice_agent import NoticeAgent

    _agent("notice", NoticeAgent)


def _warm_timetable() -> None:
    from timetable_agent import TimetableAgent

    _agent("timetable", TimetableAgent)


_CALL_WARMERS = {
    "mess": _warm_mess,
    "bus": _warm_bus,
    "complaint": _warm_complaint,
    "room_booking": _warm_room_booking,
    "attendance": _warm_attendance,
    "notice": _warm_notice,
    "timetable": _warm_timetable,
}

# Keywords/blurbs copied from planner.py's previous hand-written tables so
# the generated prompt and fast-path stay identical for all-seven-enabled.
AGENTS: dict[str, AgentSpec] = {
    "mess": AgentSpec(
        name="mess",
        call=_call_mess,
        keywords=(
            "menu",
            "breakfast",
            "lunch",
            "dinner",
            "snacks",
            "mess timing",
            "meal timing",
            "weekly menu",
        ),
        planner_blurb=(
            "mess:\n"
            "- Daily and weekly mess menus, food served in a hostel\n"
            "- Breakfast, lunch, snacks, dinner menus; meal timings\n"
            "- Authorized mess menu modifications"
        ),
        roles=("student", "faculty", "admin"),
        skill_title="Mess services",
        skill_bullets=(
            "Daily and weekly mess menus",
            "Meal timings",
            "Authorized mess menu modifications",
        ),
        skill_tags=("mess",),
    ),
    "bus": AgentSpec(
        name="bus",
        call=_call_bus,
        keywords=(
            "bus",
            "shuttle",
            "departure",
            "driver",
            "route",
        ),
        planner_blurb=(
            "bus:\n"
            "- Bus availability, schedules, routes, destinations\n"
            "- Driver information, next departures\n"
            "- Authorized bus schedule modifications"
        ),
        roles=("student", "faculty", "admin"),
        skill_title="Bus services",
        skill_bullets=(
            "Bus schedules",
            "Bus routes and destinations",
            "Driver information",
            "Next departures",
            "Bus availability",
            "Authorized bus schedule modifications",
        ),
        skill_tags=("bus",),
    ),
    "complaint": AgentSpec(
        name="complaint",
        call=_call_complaint,
        keywords=(
            "complaint",
            "complain",
            "broken",
            "not working",
            "leaking",
            "grievance",
        ),
        planner_blurb=(
            "complaint:\n"
            "- Creating, viewing, and listing complaints\n"
            "- Admin/faculty verification then PROGRESS then COMPLETED\n"
            "- Categories: academic, hostel, mess\n"
            "- Duplicate open complaints are not logged again"
        ),
        roles=("student", "faculty", "admin"),
        skill_title="Complaint services",
        skill_bullets=(
            "Create, view, and list complaints tagged academic, hostel, or mess",
            "Admin/faculty verify, then mark PROGRESS, then COMPLETED",
            "Duplicate open complaints are not logged again",
        ),
        skill_tags=("complaint",),
    ),
    "room_booking": AgentSpec(
        name="room_booking",
        call=_call_room_booking,
        keywords=(
            "book a room",
            "room booking",
            "booking",
            "clh",
            "seminar hall",
            "classroom",
            "sac hall",
            "guest house",
            "auditorium",
            "guest house",
        ),
        planner_blurb=(
            "room_booking:\n"
            "- SAC Hall, Guest House, CLH, and Auditorium\n"
            "- Availability checks, direct bookings, and booking requests\n"
            "- Cancelling and modifying bookings and requests\n"
            "- Admin approval and rejection of pending requests"
        ),
        roles=("student", "faculty", "admin"),
        skill_title="Room booking services",
        skill_bullets=(
            "SAC Hall, Guest House, CLH, and Auditorium",
            "Availability, direct bookings, and booking requests",
            "Cancel or modify bookings and requests",
            "Admin approve/reject of pending requests",
        ),
        skill_tags=("room booking",),
    ),
    "attendance": AgentSpec(
        name="attendance",
        call=_call_attendance,
        keywords=(
            "attendance",
            "skip budget",
            "mark attendance",
            "enrollment",
            "at-risk",
            "unmarked",
            "roster",
        ),
        planner_blurb=(
            "attendance:\n"
            "- Viewing attendance records, percentages, skip budget, and charts\n"
            "- Weekly, monthly, semester, and today's attendance\n"
            "- Faculty/admin marking, editing, and deleting attendance\n"
            "- Courses, rosters, enrollments, at-risk students\n"
            "- Admin management of people, courses, and enrollments"
        ),
        roles=("student", "faculty", "admin"),
        skill_title="Attendance services",
        skill_bullets=(
            "Attendance records, percentages, skip budget, and charts",
            "Weekly, monthly, semester, and today's attendance",
            "Faculty/admin marking, editing, and deleting attendance",
            "Courses, rosters, enrollments, and at-risk students",
            "Admin management of people, courses, and enrollments",
        ),
        skill_tags=("attendance",),
    ),
    "notice": AgentSpec(
        name="notice",
        call=_call_notice,
        keywords=(
            "notice",
            "notices",
            "notice board",
            "bulletin",
            "important alert",
            "campus-wide",
            "campus wide",
        ),
        planner_blurb=(
            "notice:\n"
            "- Viewing the campus notice board\n"
            "- Publishing notices (faculty/admin)\n"
            "- Archiving expired notices (faculty/admin)"
        ),
        roles=("student", "faculty", "admin"),
        skill_title="Notice board services",
        skill_bullets=(
            "View campus notices",
            "Faculty/admin publish notices",
            "Faculty/admin archive expired notices",
        ),
        skill_tags=("notice",),
    ),
    "timetable": AgentSpec(
        name="timetable",
        call=_call_timetable,
        keywords=(
            "timetable",
            "class schedule",
            "next class",
            "my classes",
            "classes on",
            "lecture slot",
        ),
        planner_blurb=(
            "timetable:\n"
            "- Personal and weekly class timetables, next class, and free slots\n"
            "- Classes on a given day, course lookup, room list for lectures/labs\n"
            "- Faculty/admin add, update, or delete class slots"
        ),
        roles=("student", "faculty", "admin"),
        skill_title="Timetable services",
        skill_bullets=(
            "Personal and weekly class timetables",
            "Next class, classes on a given day, and free slots",
            "Course lookup and lecture/lab rooms",
            "Faculty/admin add, update, or delete class slots",
        ),
        skill_tags=("timetable",),
    ),
}

AGENT_REGISTRY = AGENTS

# Admin-only. Always dispatchable; never listed in the student planner prompt
# so the IIT Patna gold prompt stays byte-identical.
SETUP_SPEC = AgentSpec(
    name="setup",
    call=_call_setup,
    keywords=(
        "org profile",
        "configure campus",
        "onboard university",
        "onboard campus",
        "import students",
        "import people",
        "import roster",
        "add a feature",
        "add feature",
        "new feature",
        "disable feature",
        "enable agent",
        "disable agent",
        "reload profile",
        "roll number pattern",
        "student id pattern",
        "add hostel",
        "add a hostel",
        "rename the campus",
        "change timezone",
        "enabled agents",
    ),
    planner_blurb=(
        "setup:\n"
        "- Change org display name, timezone, roll-number pattern, enabled agents\n"
        "- Add/remove catalog hostels, buses, rooms, meals, complaint categories\n"
        "- Import people (students/faculty/admin)\n"
        "- Add or disable a JSON-backed campus feature (not raw SQL)\n"
        "- Reload the org profile after on-disk edits"
    ),
    roles=("admin",),
    skill_title="Campus setup (admin)",
    skill_bullets=(
        "Configure org profile and catalog from chat",
        "Import people",
        "Add JSON-backed campus features",
    ),
    skill_tags=("setup",),
)

SETUP_PLANNER_ADDENDUM = """

ADMIN SETUP (authenticated admin only)
setup:
- Change org display name, timezone, roll-number pattern, enabled agents
- Add/remove catalog hostels, buses, rooms, meals, complaint categories
- Import people (students/faculty/admin)
- Add or disable a campus feature (JSON records; never raw SQL)
Route configuration, onboarding, roster import, and "add a feature" to setup.
"""


def _custom_specs() -> list[AgentSpec]:
    try:
        from custom_features import feature_to_agent_kwargs, list_features
    except Exception:
        return []
    specs: list[AgentSpec] = []
    for feat in list_features():
        kw = feature_to_agent_kwargs(feat)
        specs.append(
            AgentSpec(
                name=kw["name"],
                call=_call_custom(feat.slug),
                keywords=tuple(kw["keywords"]),
                planner_blurb=kw["planner_blurb"],
                roles=tuple(kw["roles"]),
                skill_title=kw["skill_title"],
                skill_bullets=kw["skill_bullets"],
                skill_tags=kw["skill_tags"],
            )
        )
    return specs


def enabled_specs(
    org: Optional[org_profile.OrgProfile] = None,
    *,
    include_custom: bool = True,
) -> list[AgentSpec]:
    profile = org or org_profile.ORG
    enabled = set(profile.enabled_agents)
    specs = [spec for name, spec in AGENTS.items() if name in enabled]
    if include_custom:
        specs.extend(_custom_specs())
    return specs


def enabled_call_map(org: Optional[org_profile.OrgProfile] = None) -> dict[str, CallFn]:
    mapping = {spec.name: spec.call for spec in enabled_specs(org, include_custom=True)}
    mapping["setup"] = SETUP_SPEC.call
    return mapping


def fast_path_keywords(
    org: Optional[org_profile.OrgProfile] = None,
    *,
    include_custom: bool = True,
) -> dict[str, tuple[str, ...]]:
    return {
        spec.name: spec.keywords
        for spec in enabled_specs(org, include_custom=include_custom)
    }


_PLANNER_PREFIX = """
You are the planner of the {display_name} Organization Management Agent.

Break the user's natural-language request into simple tasks and assign
each task to the appropriate specialized agent. Route generously: if the
intent is close to a supported service, send it there rather than
refusing. Ambiguous or mixed requests may become multiple tasks.

Supported agents: {supported_agents}

Do not decide authorization yourself. Specialized agents handle domain
logic and access control. If a request could reasonably be served, plan it.

For every task provide:
1. id         - short unique id ("t1", "t2", ...)
2. agent      - the specialized agent responsible
3. request    - a clear, self-contained request for that agent
   (or request_template + fill when a later task needs a value from an earlier result)
4. condition  - null, or a structured object:
   {{"depends_on": "<task id>", "type": "threshold"|"ordering"|"predicate"|"extract", ...}}
   - threshold: {{"depends_on","type":"threshold","field","op":"<"|">"|"<="|">="|"==","value"}}
   - ordering:  {{"depends_on","type":"ordering"}}  (just run after that task)
   - predicate: {{"depends_on","type":"predicate","text":"<YES/NO check>"}}
     optional "negate": true inverts the predicate
   - extract:   {{"depends_on","type":"extract"}} with request_template / fill (see below)
   An if/else pair is two tasks on the SAME depends_on: one op and its inverse
   (e.g. "<" and ">=" against the same value), or a predicate and negate:true.
   Nested "if X then if Y then Z" is a chain: t2.depends_on=t1, t3.depends_on=t2.
   Two tasks MAY target the same agent when their conditions differ.

To pass a VALUE from one result into the next request, do not guess it at
plan time. Use:
{{"request_template":"...{{{{var}}}}...","fill":[{{"var":"<name>","depends_on":"<id>","extract":"<what to pull out>"}}],"condition":{{"depends_on":"<id>","type":"extract"}}}}

AGENT RESPONSIBILITIES

"""

_PLANNER_SUFFIX = """

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
{"tasks":[{"id":"t1","agent":"mess","request":"Tell me today's dinner menu for Kalam hostel","condition":null}]}

User: "When is the next bus from Aryabhatta to Tut Block?"
{"tasks":[{"id":"t1","agent":"bus","request":"Find the next bus from Aryabhatta to Tut Block","condition":null}]}

User: "The water cooler on my floor is broken"
{"tasks":[{"id":"t1","agent":"complaint","request":"Create a hostel complaint about a broken water cooler","condition":null}]}

User: "Book SAC Hall on 2030-02-10 from 10 to 11 for a club meeting"
{"tasks":[{"id":"t1","agent":"room_booking","request":"Book SAC Hall on 2030-02-10 from 10 to 11 for a club meeting","condition":null}]}

User: "What is my attendance percentage in CS101?"
{"tasks":[{"id":"t1","agent":"attendance","request":"Show my attendance percentage for CS101","condition":null}]}

User: "Show me the current notices"
{"tasks":[{"id":"t1","agent":"notice","request":"Show me the current notices","condition":null}]}

User: "What is my class timetable today?"
{"tasks":[{"id":"t1","agent":"timetable","request":"Show my class timetable for today","condition":null}]}

User: "Tell me today's dinner at Kalam and the Bus 02 schedule"
{"tasks":[{"id":"t1","agent":"mess","request":"Tell me today's dinner menu for Kalam hostel","condition":null},{"id":"t2","agent":"bus","request":"Show me the Bus 02 schedule","condition":null}]}

User: "What is my attendance percentage in CS101 if it is less than 20% then send me today's timetable"
{"tasks":[{"id":"t1","agent":"attendance","request":"Show my attendance percentage for CS101","condition":null},{"id":"t2","agent":"timetable","request":"Show my class timetable for today","condition":{"depends_on":"t1","type":"threshold","field":"value","op":"<","value":20}}]}

User: "If my attendance is less than 20% then send today's timetable else show the next bus"
{"tasks":[{"id":"t1","agent":"attendance","request":"Show my attendance percentage","condition":null},{"id":"t2","agent":"timetable","request":"Show my class timetable for today","condition":{"depends_on":"t1","type":"threshold","field":"value","op":"<","value":20}},{"id":"t3","agent":"bus","request":"Find the next bus","condition":{"depends_on":"t1","type":"threshold","field":"value","op":">=","value":20}}]}

User: "What is my attendance percentage in CS101 if it is less than 20% then tell me my skip budget"
{"tasks":[{"id":"t1","agent":"attendance","request":"Show my attendance percentage for CS101","condition":null},{"id":"t2","agent":"attendance","request":"Show my skip budget for CS101","condition":{"depends_on":"t1","type":"threshold","field":"value","op":"<","value":20}}]}

User: "If my attendance is less than 20% then if I have a class today send me the next bus to that class"
{"tasks":[{"id":"t1","agent":"attendance","request":"Show my attendance percentage","condition":null},{"id":"t2","agent":"timetable","request":"Show my class timetable for today","condition":{"depends_on":"t1","type":"threshold","field":"value","op":"<","value":20}},{"id":"t3","agent":"bus","request":"Find the next bus to today's class building","condition":{"depends_on":"t2","type":"predicate","text":"only if there is a class today"}}]}

If a task depends on another, place it after that task and set condition.
depends_on MUST be an id of a task in this same plan. A follow-up that
should run only when a previous result satisfies a check belongs in
condition (not as an independent task).

If the request is clearly unrelated to campus services, return:
{"tasks":[],"status":"unsupported","message":"This service is not currently available."}
Otherwise prefer a best-effort plan over an empty one.

Return ONLY valid JSON.
"""


def build_planner_system_prompt(
    org: Optional[org_profile.OrgProfile] = None,
    *,
    include_custom: bool = True,
) -> str:
    """Assemble the planner system prompt from enabled AgentSpecs.

    For IIT Patna's seven built-in agents with include_custom=False this is
    byte-for-byte identical to the previous hand-written SYSTEM_PROMPT.
    Custom features are appended when include_custom=True (production).
    """
    specs = enabled_specs(org, include_custom=include_custom)
    profile = org or org_profile.ORG
    supported = ", ".join(spec.name for spec in specs)
    blurbs = "\n\n".join(spec.planner_blurb for spec in specs)
    prefix = _PLANNER_PREFIX.format(
        display_name=profile.display_name,
        supported_agents=supported,
    )
    return prefix + blurbs + _PLANNER_SUFFIX


def build_skill_services_block(
    org: Optional[org_profile.OrgProfile] = None,
) -> str:
    """CURRENTLY SUPPORTED SERVICES section of the A2A skill description."""
    lines = ["CURRENTLY SUPPORTED SERVICES:"]
    for index, spec in enumerate(enabled_specs(org), start=1):
        lines.append(f"{index}. {spec.skill_title}:")
        for bullet in spec.skill_bullets:
            lines.append(f"   - {bullet}")
        lines.append("")
    return "\n".join(lines) + "\n"


def skill_tags(org: Optional[org_profile.OrgProfile] = None) -> list[str]:
    tags = [
        "a2a",
        "jsonrpc",
        "organization",
        "campus",
    ]
    for spec in enabled_specs(org):
        tags.extend(spec.skill_tags)
    tags.extend(["planning", "authentication", "authorization"])
    return tags
