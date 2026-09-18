import json
import logging
import re

from config import LLM_FAST_MODEL
from llm import cached_system_message, chat_create, describe_llm_error, fast_tier_kwargs, get_client
from task_conditions import (
    assign_task_ids,
    condition_from_text,
    invert_condition,
    plan_deps_valid,
)

logger = logging.getLogger(__name__)


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
1. id         - short unique id ("t1", "t2", ...)
2. agent      - the specialized agent responsible
3. request    - a clear, self-contained request for that agent
   (or request_template + fill when a later task needs a value from an earlier result)
4. condition  - null, or a structured object:
   {"depends_on": "<task id>", "type": "threshold"|"ordering"|"predicate"|"extract", ...}
   - threshold: {"depends_on","type":"threshold","field","op":"<"|">"|"<="|">="|"==","value"}
   - ordering:  {"depends_on","type":"ordering"}  (just run after that task)
   - predicate: {"depends_on","type":"predicate","text":"<YES/NO check>"}
     optional "negate": true inverts the predicate
   - extract:   {"depends_on","type":"extract"} with request_template / fill (see below)
   An if/else pair is two tasks on the SAME depends_on: one op and its inverse
   (e.g. "<" and ">=" against the same value), or a predicate and negate:true.
   Nested "if X then if Y then Z" is a chain: t2.depends_on=t1, t3.depends_on=t2.
   Two tasks MAY target the same agent when their conditions differ.

To pass a VALUE from one result into the next request, do not guess it at
plan time. Use:
{"request_template":"...{{var}}...","fill":[{"var":"<name>","depends_on":"<id>","extract":"<what to pull out>"}],"condition":{"depends_on":"<id>","type":"extract"}}

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
            "important alert", "campus-wide", "campus wide",
        ),
        "timetable": (
            "timetable", "class schedule", "next class", "my classes",
            "classes on", "lecture slot",
        ),
    }

    # SOURCE if COND then CONSEQUENCE  (existing two-task split)
    _SOURCE_IF_THEN = re.compile(
        r"^(?P<source>.+?)\s+(?:if|only if|when)\s+(?P<cond>.+?)\s+then\s+(?P<then>.+)$",
        re.IGNORECASE | re.DOTALL,
    )
    _IF_THEN = re.compile(
        r"^(?:if|only if|when)\s+(?P<x>.+?)\s+then\s+(?P<y>.+)$",
        re.IGNORECASE | re.DOTALL,
    )
    _IF_COMMA = re.compile(
        r"^(?:if|only if|when)\s+(?P<x>.+?),\s+(?P<y>.+)$",
        re.IGNORECASE | re.DOTALL,
    )
    _Y_IF_X = re.compile(
        r"^(?P<y>.+?)\s+(?:if|only if)\s+(?P<x>.+)$",
        re.IGNORECASE | re.DOTALL,
    )
    _UNLESS_COMMA = re.compile(
        r"^unless\s+(?P<x>.+?),\s+(?P<y>.+)$",
        re.IGNORECASE | re.DOTALL,
    )
    _UNLESS_THEN = re.compile(
        r"^unless\s+(?P<x>.+?)\s+then\s+(?P<y>.+)$",
        re.IGNORECASE | re.DOTALL,
    )
    _Y_UNLESS_X = re.compile(
        r"^(?P<y>.+?)\s+unless\s+(?P<x>.+)$",
        re.IGNORECASE | re.DOTALL,
    )
    _IF_THEN_ELSE = re.compile(
        r"^(?:if|only if|when)\s+(?P<x>.+?)\s+then\s+(?P<y>.+?)\s+(?:else|otherwise)\s+(?P<z>.+)$",
        re.IGNORECASE | re.DOTALL,
    )
    _SOURCE_IF_THEN_ELSE = re.compile(
        r"^(?P<source>.+?)\s+(?:if|only if|when)\s+(?P<cond>.+?)\s+then\s+(?P<y>.+?)\s+(?:else|otherwise)\s+(?P<z>.+)$",
        re.IGNORECASE | re.DOTALL,
    )
    _IF_COMMA_ELSE = re.compile(
        r"^(?:if|only if|when)\s+(?P<x>.+?),\s+(?P<y>.+?)\s*,?\s*(?:else|otherwise)\s+(?P<z>.+)$",
        re.IGNORECASE | re.DOTALL,
    )
    _IF_UNLESS_WORD = re.compile(r"\b(?:if|unless)\b", re.IGNORECASE)
    _THEN_WORD = re.compile(r"\bthen\b", re.IGNORECASE)
    _ELSE_IF = re.compile(r"\belse\s+if\b|\belif\b", re.IGNORECASE)
    _ELSE_WORD = re.compile(r"\b(?:else|otherwise)\b", re.IGNORECASE)
    _UNLESS_WORD = re.compile(r"\bunless\b", re.IGNORECASE)

    def _matched_agents(self, text):
        """Return matched agents in the order they appear in text."""
        text_l = (text or "").lower()
        found = []
        for agent, keywords in self._FAST_PATH_KEYWORDS.items():
            idxs = [text_l.find(k) for k in keywords if k in text_l]
            if idxs:
                found.append((min(idxs), agent))
        found.sort()
        return [agent for _, agent in found]

    def _one_agent(self, text):
        agents = self._matched_agents(text)
        if len(agents) != 1:
            return None
        return agents[0]

    def _fast_path_plan(self, user_input):
        text = (user_input or "").lower()
        if not text.strip():
            return None

        matched = self._matched_agents(text)

        # Exactly one domain matched -> unambiguous, safe to skip the LLM.
        if len(matched) != 1:
            return None

        agent = matched[0]
        return {
            "tasks": [
                {"id": "t1", "agent": agent, "request": user_input, "condition": None}
            ]
        }

    def _independent_and_plan(self, user_input):
        # PERFORMANCE FIX: "dinner at Kalam and the Bus 02 schedule" used to
        # miss _fast_path_plan (two domains) and fall through to the LLM
        # planner. With a thinking FAST_MODEL that call billed ~8k hidden
        # completion tokens and ~140s for a 300-char JSON plan. Split only
        # when "and" separates two clauses that each map to exactly one
        # distinct agent — not when two keywords sit in one clause
        # ("complaint about the mess food").
        text = (user_input or "").strip()
        if not text:
            return None
        if (
            self._IF_UNLESS_WORD.search(text)
            or self._ELSE_WORD.search(text)
            or self._THEN_WORD.search(text)
        ):
            return None
        parts = re.split(r"\s+and\s+", text, maxsplit=1)
        if len(parts) != 2:
            return None
        left, right = parts[0].strip(), parts[1].strip()
        left_agent = self._one_agent(left)
        right_agent = self._one_agent(right)
        if not left_agent or not right_agent or left_agent == right_agent:
            return None
        logger.info(
            "Planner and-split: %s + %s (independent, 0 planner LLM calls)",
            left_agent,
            right_agent,
        )
        return {
            "tasks": [
                {
                    "id": "t1",
                    "agent": left_agent,
                    "request": left,
                    "condition": None,
                },
                {
                    "id": "t2",
                    "agent": right_agent,
                    "request": right,
                    "condition": None,
                },
            ]
        }

    def _is_nested_or_ambiguous(self, text):
        # Nested if/else-if is the LLM-planner fallback's job, not regex.
        if self._ELSE_IF.search(text):
            return True
        if len(self._IF_UNLESS_WORD.findall(text)) >= 2:
            return True
        if len(self._THEN_WORD.findall(text)) >= 2:
            return True
        return False

    def _two_clause_plan(self, source_text, consequence_text, cond_text=None, negate=False):
        src = self._one_agent(source_text)
        cons = self._one_agent(consequence_text)
        if not src or not cons:
            return None
        gate_text = cond_text if cond_text is not None else source_text
        gate = condition_from_text(gate_text, "t1", negate=negate)
        logger.info(
            "Planner split: %s then %s (condition=%s)",
            src,
            cons,
            gate,
        )
        return {
            "tasks": [
                {"id": "t1", "agent": src, "request": source_text, "condition": None},
                {
                    "id": "t2",
                    "agent": cons,
                    "request": consequence_text,
                    "condition": gate,
                },
            ]
        }

    def _three_clause_else_plan(self, source_text, y_text, z_text, cond_text=None):
        src = self._one_agent(source_text)
        y_agent = self._one_agent(y_text)
        z_agent = self._one_agent(z_text)
        if not src or not y_agent or not z_agent:
            return None
        gate_text = cond_text if cond_text is not None else source_text
        gate = condition_from_text(gate_text, "t1", negate=False)
        inverse = invert_condition(gate)
        logger.info(
            "Planner else split: %s then %s else %s (condition=%s)",
            src,
            y_agent,
            z_agent,
            gate,
        )
        return {
            "tasks": [
                {"id": "t1", "agent": src, "request": source_text, "condition": None},
                {"id": "t2", "agent": y_agent, "request": y_text, "condition": gate},
                {"id": "t3", "agent": z_agent, "request": z_text, "condition": inverse},
            ]
        }

    def _split_else(self, text):
        match = self._IF_THEN_ELSE.match(text)
        if match:
            return self._three_clause_else_plan(
                match.group("x").strip(),
                match.group("y").strip(),
                match.group("z").strip(),
            )
        match = self._SOURCE_IF_THEN_ELSE.match(text)
        if match:
            return self._three_clause_else_plan(
                match.group("source").strip(),
                match.group("y").strip(),
                match.group("z").strip(),
                cond_text=match.group("cond").strip(),
            )
        match = self._IF_COMMA_ELSE.match(text)
        if match:
            return self._three_clause_else_plan(
                match.group("x").strip(),
                match.group("y").strip(),
                match.group("z").strip(),
            )
        return None

    def _split_unless(self, text):
        match = self._UNLESS_COMMA.match(text) or self._UNLESS_THEN.match(text)
        if match:
            return self._two_clause_plan(
                match.group("x").strip(),
                match.group("y").strip(),
                negate=True,
            )
        match = self._Y_UNLESS_X.match(text)
        if match:
            return self._two_clause_plan(
                match.group("x").strip(),
                match.group("y").strip(),
                negate=True,
            )
        return None

    def _conditional_plan(self, user_input):
        # Deterministic connective splits. Nested/ambiguous phrasing falls
        # through to the LLM planner — do not regex-match nested if/else-if.
        text = (user_input or "").strip()
        if not text:
            return None
        if self._is_nested_or_ambiguous(text):
            return None

        if self._ELSE_WORD.search(text):
            return self._split_else(text)

        if self._UNLESS_WORD.search(text):
            return self._split_unless(text)

        match = self._SOURCE_IF_THEN.match(text)
        if match:
            plan = self._two_clause_plan(
                match.group("source").strip(),
                match.group("then").strip(),
                cond_text=match.group("cond").strip(),
            )
            if plan is not None:
                return plan

        match = self._IF_THEN.match(text)
        if match:
            plan = self._two_clause_plan(
                match.group("x").strip(),
                match.group("y").strip(),
            )
            if plan is not None:
                return plan

        match = self._IF_COMMA.match(text)
        if match:
            plan = self._two_clause_plan(
                match.group("x").strip(),
                match.group("y").strip(),
            )
            if plan is not None:
                return plan

        match = self._Y_IF_X.match(text)
        if match:
            plan = self._two_clause_plan(
                match.group("x").strip(),
                match.group("y").strip(),
            )
            if plan is not None:
                return plan

        return None

    def _keyword_fallback_plan(self, user_input):
        # Last resort when the planner LLM returns empty/unsupported but
        # the text still names campus services. Independent lookups (no
        # if/then) become one task per matched agent.
        agents = self._matched_agents(user_input)
        if len(agents) < 2:
            return None
        logger.info("Planner keyword fallback agents=%s", agents)
        return {
            "tasks": [
                {"id": f"t{i}", "agent": agent, "request": user_input, "condition": None}
                for i, agent in enumerate(agents, start=1)
            ]
        }

    @staticmethod
    def _finalize_plan(plan):
        if not isinstance(plan, dict):
            return plan
        tasks = plan.get("tasks") or []
        assign_task_ids(tasks)
        plan["tasks"] = tasks
        return plan

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

    def _planner_chat(self, messages, json_mode=True):
        extras = fast_tier_kwargs()
        if json_mode:
            try:
                return chat_create(
                    cache_key="planner",
                    messages=messages,
                    response_format={"type": "json_object"},
                    model=LLM_FAST_MODEL,
                    **extras,
                )
            except Exception:
                return chat_create(
                    cache_key="planner",
                    messages=messages,
                    model=LLM_FAST_MODEL,
                    **extras,
                )
        return chat_create(
            cache_key="planner",
            messages=messages,
            model=LLM_FAST_MODEL,
            **extras,
        )

    def create_plan(self, user_input):
        # Conditionals first so same-agent if/then is not swallowed by the
        # single-domain fast path (attendance + skip budget is still one agent).
        conditional = self._conditional_plan(user_input)
        if conditional is not None:
            return self._finalize_plan(conditional)

        fast_plan = self._fast_path_plan(user_input)
        if fast_plan is not None:
            return self._finalize_plan(fast_plan)

        independent = self._independent_and_plan(user_input)
        if independent is not None:
            return self._finalize_plan(independent)

        messages = [
            cached_system_message(self.SYSTEM_PROMPT),
            {"role": "user", "content": user_input},
        ]
        logger.info(
            "Planner LLM path model=%s prompt_chars=%d user=%r",
            LLM_FAST_MODEL,
            sum(len(str(m.get("content") or "")) for m in messages),
            (user_input or "")[:200],
        )

        try:
            # Ask for guaranteed-JSON output when the gateway supports it; fall
            # back transparently if this particular model/gateway rejects the
            # parameter.
            response = self._planner_chat(messages, json_mode=True)
            content = response.choices[0].message.content
            # CRITICAL FIX: this gateway accepts response_format=json_object
            # but often returns empty content (completion tokens, no text).
            # An empty body used to become "unsupported" for every multi-domain
            # request. Retry without the parameter so the model can emit JSON.
            retried = False
            if not (content or "").strip():
                logger.warning(
                    "Planner json_object returned empty content; retrying without it"
                )
                response = self._planner_chat(messages, json_mode=False)
                content = response.choices[0].message.content
                retried = True

            plan = self._finalize_plan(self._parse_plan(content))
            if plan.get("tasks") and not plan_deps_valid(plan) and not retried:
                logger.warning(
                    "Planner depends_on did not reference a task id; retrying"
                )
                response = self._planner_chat(messages, json_mode=False)
                plan = self._finalize_plan(
                    self._parse_plan(response.choices[0].message.content)
                )
        except Exception as exc:
            logger.exception("Planner LLM failed")
            return {
                "tasks": [],
                "status": "unsupported",
                "message": describe_llm_error(exc),
            }

        if plan.get("tasks") and plan_deps_valid(plan):
            return plan

        if plan.get("tasks") and not plan_deps_valid(plan):
            logger.warning("Planner plan still has invalid depends_on; ignoring")
            plan = {
                "tasks": [],
                "status": "unsupported",
                "message": "This service is not currently available.",
            }

        fallback = self._keyword_fallback_plan(user_input)
        if fallback is not None:
            return self._finalize_plan(fallback)

        return plan
