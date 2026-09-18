import json
import logging
import re

import metrics
from agent_registry import enabled_call_map, ensure_agent
from config import LLM_FAST_MODEL
from llm import (
    cached_system_message,
    chat_create,
    describe_llm_error,
    fast_tier_kwargs,
    get_client,
)
from task_conditions import (
    assign_task_ids,
    canonical_gate_key,
    canonicalize_op,
    compare_threshold,
    condition_from_text,
    is_empty_condition,
    looks_like_predicate,
    numbers_from_text,
    parse_threshold_from_text,
    threshold_eval_op,
)

logger = logging.getLogger(__name__)


class Executor:

    # PERFORMANCE FIX: this prompt is only used for the multi-task synthesis
    # call. The old version taught a tool-calling model how to pick among
    # seven agents — dispatch is now a dict lookup, so that text was billed
    # on every request for no routing benefit.
    SYSTEM_PROMPT = """
You are given the results of several campus-service lookups already performed.
Write one clear, friendly reply combining them. Do not invent facts beyond
what's given. Show names/roll numbers from the results together when present.
If a lookup was skipped because its condition was not met, say so briefly
instead of inventing that result.
"""

    def __init__(self):
        self.client = get_client()

        # PERFORMANCE FIX: the planner already returns structured
        # {agent, request} tasks. A dict lookup replaces the LLM
        # tool-calling loop that previously re-selected among the same
        # seven agents on every request. enabled_agents is what makes
        # this org-profile-aware, not just a refactor for its own sake.
        self._agent_map = enabled_call_map()
        # PERFORMANCE FIX: still construct enabled agents once at startup
        # so the first request does not pay seven OpenAI-client setups.
        for name in self._agent_map:
            ensure_agent(name)

    def _run_task(self, task, user_metadata, request=None):
        # PERFORMANCE FIX: the planner already named the agent, so dispatch
        # is a dict lookup rather than an LLM tool-calling round. A single
        # agent's exception is caught here so it cannot crash the whole
        # request.
        agent_name = task.get("agent")
        fn = self._agent_map.get(agent_name)
        if fn is None:
            return {
                "status": "error",
                "message": f"Unknown agent: {task.get('agent')}",
            }
        if request is None:
            request = task.get("request")
        # Keep task_timer around the direct call so /api/metrics still
        # attributes wall time to mess/bus/etc. the way the old
        # tool-call loop did.
        #
        # CRITICAL FIX: task_timer's finally clause returns early when no
        # request_scope is active, and a return in finally discards a
        # pending exception. Catch inside the timer so a failed agent
        # still becomes an error result instead of None.
        with metrics.task_timer(agent_name, **self._task_fields(task)):
            try:
                return fn(request, user_metadata)
            except Exception as exc:
                return describe_llm_error(exc)

    def _task_fields(self, task, structured=None, skipped=None):
        cond = task.get("condition")
        structured = structured if structured is not None else (
            cond if isinstance(cond, dict) else None
        )
        fields = {
            "task_id": task.get("id"),
            "agent": task.get("agent"),
            "condition": cond,
            "depends_on": (structured or {}).get("depends_on") if structured else None,
            "condition_type": (structured or {}).get("type") if structured else None,
        }
        if skipped is not None:
            fields["skipped"] = skipped
        return fields

    def _legacy_depends_on(self, cond_text, tasks, index):
        """Resolve a free-text condition's depends_on using the old heuristics."""
        n = len(tasks)
        cond_l = str(cond_text).lower()
        for match in re.finditer(r"\btask\s*#?\s*(\d+)\b", cond_l):
            num = int(match.group(1))
            if 1 <= num <= n:
                return tasks[num - 1].get("id")
            if num == 0 and tasks:
                return tasks[0].get("id")
        prior = None
        later = None
        for j, other in enumerate(tasks):
            if j == index:
                continue
            agent = other.get("agent")
            if not agent:
                continue
            if re.search(rf"\b{re.escape(str(agent).lower())}\b", cond_l):
                if j < index:
                    prior = other.get("id")
                elif later is None:
                    later = other.get("id")
        if prior:
            return prior
        if later:
            return later
        if index > 0:
            return tasks[index - 1].get("id")
        return None

    def _condition_dep_ids(self, task, tasks, index):
        refs = []
        condition = task.get("condition")
        if is_empty_condition(condition):
            pass
        elif isinstance(condition, dict):
            if condition.get("depends_on"):
                refs.append(condition["depends_on"])
        else:
            dep = self._legacy_depends_on(condition, tasks, index)
            if dep:
                refs.append(dep)
            else:
                refs.extend(
                    tasks[j].get("id") for j in range(index) if tasks[j].get("id")
                )
        for item in task.get("fill") or []:
            if isinstance(item, dict) and item.get("depends_on"):
                refs.append(item["depends_on"])
        return refs

    def _order_tasks(self, tasks):
        # A task whose condition references another task's result must run
        # after it. Independent tasks keep their original relative order;
        # concurrent dispatch is a later change. Gating is by task id, so
        # two tasks may target the same agent.
        assign_task_ids(tasks)
        n = len(tasks)
        if n <= 1:
            return list(tasks)

        id_to_idx = {task.get("id"): i for i, task in enumerate(tasks)}
        deps = [set() for _ in range(n)]
        for i, task in enumerate(tasks):
            for dep_id in self._condition_dep_ids(task, tasks, i):
                j = id_to_idx.get(dep_id)
                if j is not None and j != i:
                    deps[i].add(j)

        indegree = [len(d) for d in deps]
        succ = [[] for _ in range(n)]
        for i, d in enumerate(deps):
            for j in d:
                succ[j].append(i)

        ready = [i for i in range(n) if indegree[i] == 0]
        ordered_idx = []
        while ready:
            i = min(ready)
            ready.remove(i)
            ordered_idx.append(i)
            for j in succ[i]:
                indegree[j] -= 1
                if indegree[j] == 0:
                    ready.append(j)

        if len(ordered_idx) < n:
            leftover = [i for i in range(n) if i not in set(ordered_idx)]
            ordered_idx.extend(leftover)

        return [tasks[i] for i in ordered_idx]

    _CMP = re.compile(
        r"(?P<op>less than|greater than|more than|at least|at most|"
        r"below|under|above|over|"
        r"<=|>=|<|>|=|==)\s*(?P<num>\d+(?:\.\d+)?)\s*%?",
        re.IGNORECASE,
    )
    _PERCENT = re.compile(
        r"(\d+(?:\.\d+)?)\s*(?:%|percent)",
        re.IGNORECASE,
    )

    @staticmethod
    def _looks_like_predicate(condition):
        return looks_like_predicate(condition)

    def _numbers_from_results(self, collected, depends_on=None):
        nums = []
        items = collected
        if depends_on:
            targeted = [item for item in collected if item.get("id") == depends_on]
            if targeted:
                items = targeted
        for item in items:
            if item.get("skipped"):
                continue
            text = item.get("result")
            if not isinstance(text, str):
                text = json.dumps(text, default=str)
            nums.extend(numbers_from_text(text))
        return nums

    def _eval_numeric_condition(self, condition, collected):
        parsed = parse_threshold_from_text(str(condition))
        if not parsed:
            return None
        nums = self._numbers_from_results(collected)
        if not nums:
            return None
        return compare_threshold(nums[0], parsed["op"], parsed["value"])

    def _eval_threshold(self, cond, collected):
        nums = self._numbers_from_results(
            collected, depends_on=cond.get("depends_on")
        )
        if not nums:
            return None
        try:
            threshold = float(cond.get("value"))
        except (TypeError, ValueError):
            return None
        return compare_threshold(nums[0], cond.get("op"), threshold)

    def _llm_condition_met(self, condition, collected):
        # The old tool-calling executor used an LLM round to decide whether
        # a dependent task should run. Keep one cheap YES/NO call only when
        # the condition cannot be evaluated from numbers in prior results.
        user_message = (
            f"Condition:\n{condition}\n\n"
            f"Results so far:\n{json.dumps(collected, indent=2, default=str)}\n\n"
            "Does the condition hold? Reply YES or NO only."
        )
        response = chat_create(
            cache_key="executor",
            messages=[
                cached_system_message(
                    "You decide whether a follow-up campus lookup should run. "
                    "Reply YES or NO only. Do not invent facts."
                ),
                {"role": "user", "content": user_message},
            ],
            model=LLM_FAST_MODEL,
            **fast_tier_kwargs(),
        )
        answer = (response.choices[0].message.content or "").strip().upper()
        return answer.startswith("YES")

    def _condition_met(self, condition, collected):
        if is_empty_condition(condition):
            return True
        if isinstance(condition, dict):
            return self._cached_gate(condition, collected, {})

        numeric = self._eval_numeric_condition(condition, collected)
        if numeric is not None:
            logger.info(
                "Executor condition numeric eval %r -> %s",
                condition,
                numeric,
            )
            return numeric

        # Ordering hints ("after the mess result") are not predicates.
        if not self._looks_like_predicate(condition):
            return True

        return self._llm_condition_met(condition, collected)

    def _structured_condition(self, task, tasks):
        cond = task.get("condition")
        if is_empty_condition(cond):
            return None
        if isinstance(cond, dict):
            structured = dict(cond)
            canon = canonicalize_op(structured.get("op"))
            if canon:
                structured["op"] = canon
            return structured
        tid = task.get("id")
        idx = next(
            (i for i, other in enumerate(tasks) if other.get("id") == tid),
            0,
        )
        dep = self._legacy_depends_on(cond, tasks, idx)
        return condition_from_text(str(cond), dep)

    def _compute_gate_value(self, cond, collected):
        """Evaluate a unique gate once. Inverse siblings reuse the cache."""
        self.gate_eval_count = getattr(self, "gate_eval_count", 0) + 1
        ctype = cond.get("type")
        if ctype == "threshold":
            eval_cond = dict(cond)
            eval_cond["op"] = threshold_eval_op(cond) or cond.get("op")
            result = self._eval_threshold(eval_cond, collected)
            if result is None:
                return False
            return result
        if ctype == "predicate":
            return self._llm_condition_met(cond.get("text"), collected)
        return True

    def _cached_gate(self, cond, collected, cache):
        key, invert = canonical_gate_key(cond)
        if key not in cache:
            cache[key] = self._compute_gate_value(cond, collected)
        result = cache[key]
        if result is None:
            result = False
        return (not result) if invert else bool(result)

    _EXTRACT_SYSTEM = """
You extract one value from a campus-service lookup result.
Return JSON only: {"found": true, "value": "<the value>"} or {"found": false, "value": ""}.
Do not guess. If the result does not clearly contain what was asked, found must be false.
"""

    def _fill_items(self, task):
        fill = [
            item for item in (task.get("fill") or []) if isinstance(item, dict)
        ]
        cond = task.get("condition")
        if (
            isinstance(cond, dict)
            and cond.get("type") == "extract"
            and not fill
        ):
            fill.append({
                "var": cond.get("var") or "value",
                "depends_on": cond.get("depends_on"),
                "extract": (
                    cond.get("extract")
                    or cond.get("field")
                    or "the needed value"
                ),
            })
        return fill

    @staticmethod
    def _parse_extract_response(content):
        if not content:
            return False, ""
        content = content.strip()
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        data = None
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    data = None
        if not isinstance(data, dict):
            return False, ""
        found = data.get("found")
        value = data.get("value")
        if found is True and value is not None and str(value).strip():
            return True, str(value).strip()
        return False, ""

    def _extract_value(self, result_text, extract_desc):
        # Exactly one bounded call per fill item; never retried.
        user_message = (
            f"Value to extract:\n{extract_desc}\n\n"
            f"Previous lookup result:\n{result_text}\n"
        )
        try:
            response = chat_create(
                cache_key="extract",
                messages=[
                    cached_system_message(self._EXTRACT_SYSTEM),
                    {"role": "user", "content": user_message},
                ],
                model=LLM_FAST_MODEL,
                **fast_tier_kwargs(),
            )
        except Exception:
            return False, ""
        content = ""
        try:
            content = response.choices[0].message.content or ""
        except Exception:
            return False, ""
        return self._parse_extract_response(content)

    def _resolve_request(self, task, results_by_id):
        fill = self._fill_items(task)
        template = task.get("request_template")
        if not template and not fill:
            return task.get("request"), None
        if not template:
            template = task.get("request") or ""

        blocks = []
        for item in fill:
            var = item.get("var") or "value"
            dep = item.get("depends_on")
            desc = item.get("extract") or ""
            missing_msg = {
                "status": "error",
                "message": (
                    f"Couldn't determine {var} from the previous result."
                ),
            }
            dep_item = results_by_id.get(dep) if dep else None
            if not dep_item or dep_item.get("skipped"):
                return None, missing_msg
            result_text = dep_item.get("result")
            if not isinstance(result_text, str):
                result_text = json.dumps(result_text, default=str)
            blocks.append((var, desc, result_text, missing_msg))

        if not blocks:
            return template, None

        # Exactly one extraction call per task that uses fill, never retried.
        mapping = {}
        if len(blocks) == 1:
            var, desc, result_text, missing_msg = blocks[0]
            found, value = self._extract_value(result_text, desc)
            if not found:
                return None, missing_msg
            mapping[var] = value
        else:
            lines = [
                f"Field {var}: {desc}\nSource result:\n{result_text}"
                for var, desc, result_text, _ in blocks
            ]
            user_message = (
                "Extract these values.\n\n"
                + "\n\n".join(lines)
                + '\n\nReturn JSON: {"found": true, "values": {"<var>": "<value>"}} '
                'or {"found": false, "values": {}}.'
            )
            try:
                response = chat_create(
                    cache_key="extract",
                    messages=[
                        cached_system_message(self._EXTRACT_SYSTEM),
                        {"role": "user", "content": user_message},
                    ],
                    model=LLM_FAST_MODEL,
                    **fast_tier_kwargs(),
                )
                content = response.choices[0].message.content or ""
            except Exception:
                content = ""
            data = None
            try:
                stripped = re.sub(r"^```(?:json)?\s*", "", content.strip())
                stripped = re.sub(r"\s*```$", "", stripped)
                data = json.loads(stripped)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(0))
                    except json.JSONDecodeError:
                        data = None
            values = {}
            if isinstance(data, dict) and data.get("found") is True:
                if isinstance(data.get("values"), dict):
                    values = data["values"]
                elif data.get("value") is not None:
                    values = {blocks[0][0]: data.get("value")}
            for var, _, _, missing_msg in blocks:
                raw = values.get(var)
                if raw is None or not str(raw).strip():
                    return None, missing_msg
                mapping[var] = str(raw).strip()

        request = template
        for var, value in mapping.items():
            request = request.replace("{{" + str(var) + "}}", str(value))
        return request, None

    @staticmethod
    def _condition_label(condition):
        if isinstance(condition, dict):
            ctype = condition.get("type")
            if ctype == "threshold":
                field = condition.get("field") or "value"
                return f"{field} {condition.get('op')} {condition.get('value')}"
            if ctype == "predicate":
                return condition.get("text") or condition
            return condition
        return condition

    def _skipped_item(self, task, condition):
        label = self._condition_label(condition)
        return {
            "id": task.get("id"),
            "agent": task.get("agent"),
            "request": task.get("request") or task.get("request_template"),
            "condition": condition,
            "skipped": True,
            "result": f"Skipped because the condition was not met: {label}",
        }

    def execute(self, user_input, plan, user_metadata):
        plan = plan or {}
        tasks = plan.get("tasks") or []

        # PERFORMANCE FIX: unsupported / empty plans used to still enter
        # the executor LLM loop. The message is already in the plan —
        # return it with zero LLM calls.
        if plan.get("status") == "unsupported" or not tasks:
            logger.info("Executor empty/unsupported plan: 0 executor LLM calls")
            return plan.get(
                "message",
                "This service is not currently available.",
            )

        assign_task_ids(tasks)
        self.gate_eval_count = 0
        has_fill = any(
            (task.get("fill") or task.get("request_template"))
            for task in tasks
        )
        if len(tasks) == 1 and not has_fill:
            task = tasks[0]
            # PERFORMANCE FIX: a single-task plan is just one function
            # call. The old loop spent 1–2 executor LLM rounds only to
            # pick which tool to invoke.
            logger.info(
                "Executor single-task agent=%s: 0 executor LLM calls "
                "(direct dispatch)",
                task.get("agent"),
            )
            result = self._run_task(task, user_metadata)
            if isinstance(result, str):
                return result
            # Non-string (error dicts) still become a readable message,
            # matching the old tool-result json.dumps path, but with no
            # LLM round.
            return json.dumps(result, default=str)

        ordered = self._order_tasks(tasks)
        collected = []
        results_by_id = {}
        skipped_ids = set()
        gate_cache = {}
        for task in ordered:
            tid = task.get("id")
            condition = task.get("condition")
            structured = self._structured_condition(task, ordered)
            dep_ids = []
            if structured and structured.get("depends_on"):
                dep_ids.append(structured["depends_on"])
            for item in self._fill_items(task):
                if item.get("depends_on"):
                    dep_ids.append(item["depends_on"])

            # A task whose depends_on target was skipped is also skipped.
            if any(dep in skipped_ids for dep in dep_ids):
                logger.info(
                    "Executor skipped agent=%s id=%s (depends_on was skipped)",
                    task.get("agent"),
                    tid,
                )
                item = self._skipped_item(task, condition)
                collected.append(item)
                results_by_id[tid] = item
                skipped_ids.add(tid)
                metrics.record_task(
                    task.get("agent") or "unknown",
                    **self._task_fields(task, structured, skipped=True),
                    latency_ms=0.0,
                )
                continue

            ctype = (structured or {}).get("type")
            # CRITICAL FIX: the old tool-calling loop read prior tool
            # results and skipped a follow-up whose condition failed
            # ("if attendance < 20% then timetable"). Blind dispatch
            # always ran every agent, and an unmet gate never stopped
            # the second call. Evaluate first; skip when it fails.
            # Unique gates are evaluated once and reused for else siblings.
            if structured and ctype not in (None, "ordering", "extract"):
                if not self._cached_gate(structured, collected, gate_cache):
                    logger.info(
                        "Executor skipped agent=%s (condition not met: %s)",
                        task.get("agent"),
                        condition,
                    )
                    item = self._skipped_item(task, condition)
                    collected.append(item)
                    results_by_id[tid] = item
                    skipped_ids.add(tid)
                    metrics.record_task(
                        task.get("agent") or "unknown",
                        **self._task_fields(task, structured, skipped=True),
                        latency_ms=0.0,
                    )
                    continue

            request, extract_error = self._resolve_request(task, results_by_id)
            if extract_error is not None:
                item = {
                    "id": tid,
                    "agent": task.get("agent"),
                    "request": (
                        task.get("request_template") or task.get("request")
                    ),
                    "condition": condition,
                    "result": extract_error,
                }
                collected.append(item)
                results_by_id[tid] = item
                continue

            collected.append({
                "id": tid,
                "agent": task.get("agent"),
                "request": request,
                "condition": condition,
                "result": self._run_task(task, user_metadata, request=request),
            })
            results_by_id[tid] = collected[-1]

        executed = [item for item in collected if not item.get("skipped")]
        skipped = [item for item in collected if item.get("skipped")]

        # After skips, a single remaining result is the same as the
        # single-task path: return it directly. Mention skipped follow-ups
        # so the user knows why timetable/etc. was not included.
        if len(executed) <= 1:
            logger.info(
                "Executor multi-task after conditions: %d ran, %d skipped, "
                "0 synthesis LLM calls",
                len(executed),
                len(skipped),
            )
            if not executed:
                return (
                    "The follow-up lookups were not run because their "
                    "conditions were not met."
                )
            result = executed[0]["result"]
            if not isinstance(result, str):
                result = json.dumps(result, default=str)
            if skipped:
                names = ", ".join(
                    str(item.get("agent") or "lookup") for item in skipped
                )
                cond = self._condition_label(
                    skipped[0].get("condition")
                ) or "the stated condition"
                result = (
                    f"{result}\n\n"
                    f"I did not look up {names} because this condition "
                    f"was not met: {cond}."
                )
            return result

        logger.info(
            "Executor multi-task: %d agents dispatched, %d skipped, "
            "1 synthesis LLM call",
            len(executed),
            len(skipped),
        )

        # Diagnostic: log what actually goes into the synthesis prompt so
        # a 10k-token average can be attributed to payload bloat vs. the
        # model rambling on a small prompt.
        compact_results = [
            {
                "id": item.get("id"),
                "agent": item.get("agent"),
                "result": item.get("result"),
                "skipped": bool(item.get("skipped")),
            }
            for item in collected
        ]
        raw_dump = json.dumps(collected, indent=2, default=str)
        compact_dump = json.dumps(compact_results, indent=2, default=str)
        logger.info(
            "Executor synthesis payload raw_chars=%d compact_chars=%d "
            "n_collected=%d n_executed=%d keys=%s",
            len(raw_dump),
            len(compact_dump),
            len(collected),
            len(executed),
            sorted({k for item in collected if isinstance(item, dict) for k in item}),
        )
        logger.info(
            "Executor synthesis compact results:\n%s",
            compact_dump[:4000],
        )

        user_message = f"""
Original user request:
{user_input}

Results of the campus-service lookups already performed:
{raw_dump}

Write one clear, friendly reply that combines these results.
"""

        messages = [
            cached_system_message(self.SYSTEM_PROMPT),
            {
                "role": "user",
                "content": user_message,
            },
        ]

        # PERFORMANCE FIX: one plain completion replaces the old
        # tool-calling loop (an executor LLM round per tool batch plus a
        # final summary round). tools= is omitted because dispatch
        # already happened.
        with metrics.task_timer("executor"):
            response = chat_create(
                cache_key="executor",
                messages=messages,
            )
            return response.choices[0].message.content
