"""Structured task conditions: ids, gates, and legacy string compatibility."""

from __future__ import annotations

import re
from typing import Any, Optional

OP_ALIASES = {
    "less than": "<",
    "below": "<",
    "under": "<",
    "<": "<",
    "greater than": ">",
    "more than": ">",
    "above": ">",
    "over": ">",
    ">": ">",
    "at least": ">=",
    ">=": ">=",
    "at most": "<=",
    "<=": "<=",
    "=": "==",
    "==": "==",
    "!=": "!=",
}

INVERSE_OP = {
    "<": ">=",
    ">": "<=",
    "<=": ">",
    ">=": "<",
    "==": "!=",
    "!=": "==",
}

CMP_RE = re.compile(
    r"(?P<op>less than|greater than|more than|at least|at most|"
    r"below|under|above|over|"
    r"<=|>=|<|>|=|==|!=)\s*(?P<num>\d+(?:\.\d+)?)\s*%?",
    re.IGNORECASE,
)

PERCENT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:%|percent)",
    re.IGNORECASE,
)

PREDICATE_KEYS = (
    " if ", "only if", "less than", "greater than", "more than",
    "below", "under ", "above", "over ", "at least", "at most",
    "<", ">", "=", " when ", " unless ",
)

_COMPARE = {
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def canonicalize_op(op: Any) -> Optional[str]:
    if op is None:
        return None
    return OP_ALIASES.get(str(op).strip().lower())


def looks_like_predicate(condition: Any) -> bool:
    text = f" {str(condition).lower()} "
    raw = str(condition).lower()
    return any(k in text or raw.startswith("if ") for k in PREDICATE_KEYS)


def parse_threshold_from_text(text: str) -> Optional[dict]:
    match = CMP_RE.search(text or "")
    if not match:
        return None
    op = canonicalize_op(match.group("op"))
    if op is None:
        return None
    return {"op": op, "value": float(match.group("num"))}


def condition_from_text(text: str, depends_on: Optional[str], negate: bool = False) -> dict:
    """Turn a free-text gate into a structured condition."""
    parsed = parse_threshold_from_text(text)
    if parsed:
        op = parsed["op"]
        if negate:
            op = INVERSE_OP.get(op, op)
        return {
            "depends_on": depends_on,
            "type": "threshold",
            "field": "value",
            "op": op,
            "value": parsed["value"],
        }
    if not looks_like_predicate(text):
        return {"depends_on": depends_on, "type": "ordering"}
    cond = {
        "depends_on": depends_on,
        "type": "predicate",
        "text": text,
    }
    if negate:
        cond["negate"] = True
    return cond


def invert_condition(cond: dict) -> dict:
    if not isinstance(cond, dict):
        return cond
    inverted = dict(cond)
    ctype = inverted.get("type")
    if ctype == "threshold":
        op = canonicalize_op(inverted.get("op")) or inverted.get("op")
        inverted["op"] = INVERSE_OP.get(op, op)
        inverted.pop("negate", None)
        return inverted
    if ctype == "predicate":
        inverted["negate"] = not inverted.get("negate")
        return inverted
    return inverted


def is_empty_condition(condition: Any) -> bool:
    if condition is None or condition is False:
        return True
    if isinstance(condition, str) and not condition.strip():
        return True
    if isinstance(condition, str) and condition.strip().lower() == "null":
        return True
    return False


def assign_task_ids(tasks: list) -> list:
    used = set()
    for i, task in enumerate(tasks or []):
        if not isinstance(task, dict):
            continue
        tid = task.get("id")
        if not tid or tid in used:
            n = i + 1
            while f"t{n}" in used:
                n += 1
            tid = f"t{n}"
            task["id"] = tid
        used.add(tid)
    return tasks


def task_ids(tasks: list) -> set:
    return {
        t.get("id") for t in (tasks or [])
        if isinstance(t, dict) and t.get("id")
    }


def depends_on_refs(task: dict) -> list:
    refs = []
    if not isinstance(task, dict):
        return refs
    cond = task.get("condition")
    if isinstance(cond, dict) and cond.get("depends_on"):
        refs.append(cond["depends_on"])
    for item in task.get("fill") or []:
        if isinstance(item, dict) and item.get("depends_on"):
            refs.append(item["depends_on"])
    return refs


def plan_deps_valid(plan: dict) -> bool:
    tasks = (plan or {}).get("tasks") or []
    ids = task_ids(tasks)
    for task in tasks:
        for ref in depends_on_refs(task):
            if ref not in ids:
                return False
    return True


def canonical_gate_key(cond: dict) -> tuple:
    """Return ((key), invert) so inverse ops share one evaluation."""
    ctype = cond.get("type")
    depends_on = cond.get("depends_on")
    if ctype == "threshold":
        op = canonicalize_op(cond.get("op")) or cond.get("op")
        invert = False
        if op in (">=", ">"):
            op = INVERSE_OP[op]
            invert = True
        elif op == "!=":
            op = "=="
            invert = True
        try:
            value = float(cond.get("value"))
        except (TypeError, ValueError):
            value = cond.get("value")
        field = cond.get("field") or "value"
        return ("threshold", depends_on, field, op, value), invert
    if ctype == "predicate":
        text = (cond.get("text") or "").strip()
        invert = bool(cond.get("negate"))
        return ("predicate", depends_on, text), invert
    return (ctype, depends_on), False


def compare_threshold(value: float, op: str, threshold: float) -> Optional[bool]:
    op = canonicalize_op(op) or op
    fn = _COMPARE.get(op)
    if fn is None:
        return None
    return fn(value, threshold)


def numbers_from_text(text: str) -> list:
    return [float(m) for m in PERCENT_RE.findall(text or "")]


def threshold_eval_op(cond: dict) -> Optional[str]:
    """Op to evaluate for the canonical (non-inverted) form of a threshold."""
    op = canonicalize_op(cond.get("op")) or cond.get("op")
    if op in (">=", ">"):
        return INVERSE_OP[op]
    if op == "!=":
        return "=="
    return op
