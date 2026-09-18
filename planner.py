import json
import logging
import re

from agent_registry import (
    SETUP_PLANNER_ADDENDUM,
    SETUP_SPEC,
    build_planner_system_prompt,
    fast_path_keywords,
)
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

    # Generated from AGENT_REGISTRY filtered by ORG.enabled_agents. For the
    # default IIT Patna all-seven-enabled profile this is byte-for-byte the
    # previous hand-written prompt (see tests/planner/test_prompt_generation.py).
    # Keep it a stable, unchanging string so the gateway can reuse a cached
    # prefix instead of reprocessing it.
    SYSTEM_PROMPT = build_planner_system_prompt()

    # Cheap keyword routing for the overwhelmingly common case: a request
    # that clearly belongs to exactly one agent. When it fires we skip the
    # planner LLM call entirely, removing one full round-trip (and its
    # prompt tokens) from the critical path. Anything ambiguous, empty, or
    # matching more than one domain falls through to the LLM planner, so
    # this only ever shortcuts the unambiguous cases.
    _FAST_PATH_KEYWORDS = fast_path_keywords()

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

    def _setup_fast_path(self, user_input):
        """Admin-only: config/onboard/import/add-feature skip the LLM planner."""
        text = (user_input or "").lower()
        if not text.strip():
            return None
        if not any(k in text for k in SETUP_SPEC.keywords):
            return None
        return {
            "tasks": [
                {"id": "t1", "agent": "setup", "request": user_input, "condition": None}
            ]
        }

    def create_plan(self, user_input, role=None):
        # Conditionals first so same-agent if/then is not swallowed by the
        # single-domain fast path (attendance + skip budget is still one agent).
        if str(role or "").strip().lower() == "admin":
            setup_plan = self._setup_fast_path(user_input)
            if setup_plan is not None:
                return self._finalize_plan(setup_plan)

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
            cached_system_message(
                self.SYSTEM_PROMPT + (
                    SETUP_PLANNER_ADDENDUM
                    if str(role or "").strip().lower() == "admin"
                    else ""
                )
            ),
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
