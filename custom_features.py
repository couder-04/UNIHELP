"""JSON-backed campus features created by the admin setup agent.

Admin describes a service (library, lost-and-found, …) in chat. We store a
field schema and rows as JSONB in campus_agent — never execute model-supplied
SQL. Planner/executor pick these up after reload as extra AgentSpecs.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any

import db
from config import AUTH_DB_NAME

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
_FIELD_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_ALLOWED_FIELD_TYPES = frozenset({"string", "number", "boolean", "date"})
RESERVED_SLUGS = frozenset(
    {
        "mess",
        "bus",
        "complaint",
        "room_booking",
        "attendance",
        "notice",
        "timetable",
        "setup",
        "planner",
        "executor",
        "people",
        "users",
        "admin",
        "custom",
        "org",
        "feature",
    }
)

_FEATURES_DDL = """
CREATE TABLE IF NOT EXISTS custom_features (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    planner_blurb TEXT NOT NULL,
    keywords JSONB NOT NULL,
    fields JSONB NOT NULL,
    roles JSONB NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

_RECORDS_DDL = """
CREATE TABLE IF NOT EXISTS custom_feature_records (
    id UUID PRIMARY KEY,
    feature_id TEXT NOT NULL REFERENCES custom_features(id),
    payload JSONB NOT NULL,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


@dataclass(frozen=True)
class FeatureSpec:
    slug: str
    title: str
    description: str
    planner_blurb: str
    keywords: tuple[str, ...]
    fields: tuple[dict[str, Any], ...]
    roles: tuple[str, ...]
    enabled: bool


def _conn():
    return db.get_connection(AUTH_DB_NAME)


def ensure_schema() -> None:
    connection = _conn()
    try:
        cursor = connection.cursor()
        cursor.execute(_FEATURES_DDL)
        cursor.execute(_RECORDS_DDL)
        connection.commit()
        cursor.close()
    finally:
        connection.close()


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")
    if len(slug) > 32:
        slug = slug[:32].rstrip("_")
    return slug


def _validate_fields(fields: list[Any]) -> list[dict[str, Any]]:
    if not isinstance(fields, list) or not fields:
        raise ValueError("fields must be a non-empty list")
    if len(fields) > 20:
        raise ValueError("fields: at most 20 columns")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for raw in fields:
        if not isinstance(raw, dict):
            raise ValueError("each field must be {name, type, ...}")
        name = str(raw.get("name") or "").strip().lower()
        ftype = str(raw.get("type") or "string").strip().lower()
        if not _FIELD_NAME_RE.fullmatch(name):
            raise ValueError(f"invalid field name {name!r}")
        if name in seen:
            raise ValueError(f"duplicate field {name!r}")
        if ftype not in _ALLOWED_FIELD_TYPES:
            raise ValueError(
                f"field {name!r} type {ftype!r} not in {sorted(_ALLOWED_FIELD_TYPES)}"
            )
        seen.add(name)
        out.append(
            {
                "name": name,
                "type": ftype,
                "required": bool(raw.get("required", True)),
                "description": str(raw.get("description") or name),
            }
        )
    return out


def add_feature(
    *,
    name: str,
    title: str = "",
    description: str,
    keywords: list[str] | None = None,
    fields: list[dict[str, Any]],
    roles: list[str] | None = None,
    created_by: str = "",
) -> dict[str, Any]:
    """Register a JSON-backed feature. No DDL beyond the two shared tables."""
    slug = slugify(name)
    if not _SLUG_RE.fullmatch(slug):
        return {
            "status": "error",
            "message": f"Feature name {name!r} is not a usable slug ({slug!r}).",
        }
    if slug in RESERVED_SLUGS:
        return {
            "status": "error",
            "message": f"{slug!r} is a built-in agent name and cannot be reused.",
        }
    try:
        field_list = _validate_fields(fields)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    ensure_schema()

    kw = tuple(
        str(k).strip().lower()
        for k in (keywords or [title or name, slug])
        if str(k).strip()
    )
    if not kw:
        kw = (slug,)
    role_tuple = tuple(
        r.strip().lower()
        for r in (roles or ["student", "faculty", "admin"])
        if str(r).strip()
    )
    if not role_tuple:
        role_tuple = ("student", "faculty", "admin")
    display = (title or name).strip()
    blurb = (
        f"{slug}:\n"
        f"- {description.strip()}\n"
        f"- Records: {', '.join(f['name'] for f in field_list)}"
    )
    connection = _conn()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM custom_features WHERE id = %s", (slug,))
        if cursor.fetchone():
            cursor.close()
            return {
                "status": "error",
                "message": f"Feature {slug!r} already exists. Disable it first or pick another name.",
            }
        cursor.execute(
            """
            INSERT INTO custom_features (
                id, title, description, planner_blurb, keywords, fields, roles,
                enabled, created_by
            ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, TRUE, %s)
            """,
            (
                slug,
                display,
                description.strip(),
                blurb,
                json.dumps(list(kw)),
                json.dumps(field_list),
                json.dumps(list(role_tuple)),
                created_by or None,
            ),
        )
        connection.commit()
        cursor.close()
    finally:
        connection.close()
    return {
        "status": "ok",
        "slug": slug,
        "title": display,
        "fields": field_list,
        "keywords": list(kw),
        "roles": list(role_tuple),
        "message": (
            f"Feature {slug!r} is live. Students/faculty use it by name "
            f"({display}). Data lives in custom_feature_records, not a new table."
        ),
    }


def disable_feature(slug: str) -> dict[str, Any]:
    ensure_schema()
    slug = slugify(slug)
    connection = _conn()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE custom_features SET enabled = FALSE WHERE id = %s RETURNING id",
            (slug,),
        )
        row = cursor.fetchone()
        connection.commit()
        cursor.close()
    finally:
        connection.close()
    if not row:
        return {"status": "error", "message": f"No feature named {slug!r}."}
    return {"status": "ok", "slug": slug, "enabled": False}


def _row_to_spec(row: tuple[Any, ...]) -> FeatureSpec:
    keywords = row[3]
    fields = row[4]
    roles = row[5]
    if isinstance(keywords, str):
        keywords = json.loads(keywords)
    if isinstance(fields, str):
        fields = json.loads(fields)
    if isinstance(roles, str):
        roles = json.loads(roles)
    return FeatureSpec(
        slug=row[0],
        title=row[1],
        description=row[2],
        planner_blurb=row[6],
        keywords=tuple(str(k) for k in (keywords or [])),
        fields=tuple(fields or ()),
        roles=tuple(str(r) for r in (roles or ())),
        enabled=bool(row[7]),
    )


def list_features(*, enabled_only: bool = True) -> list[FeatureSpec]:
    """Return configured features. Empty list if the table is missing."""
    try:
        ensure_schema()
        connection = _conn()
        try:
            cursor = connection.cursor()
            sql = """
                SELECT id, title, description, keywords, fields, roles,
                       planner_blurb, enabled
                FROM custom_features
            """
            if enabled_only:
                sql += " WHERE enabled = TRUE"
            sql += " ORDER BY id"
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()
        finally:
            connection.close()
        return [_row_to_spec(row) for row in rows]
    except Exception:
        logger.exception("custom_features.list_features failed")
        return []


def get_feature(slug: str) -> FeatureSpec | None:
    slug = slugify(slug)
    for spec in list_features(enabled_only=False):
        if spec.slug == slug:
            return spec
    return None


def _coerce(value: Any, ftype: str) -> Any:
    if value is None:
        return None
    if ftype == "string" or ftype == "date":
        return str(value)
    if ftype == "number":
        return float(value)
    if ftype == "boolean":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "y"}
    return value


def _validate_payload(spec: FeatureSpec, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    allowed = {f["name"]: f for f in spec.fields}
    unknown = set(payload) - set(allowed)
    if unknown:
        raise ValueError(f"unknown fields: {sorted(unknown)}")
    out: dict[str, Any] = {}
    for name, field in allowed.items():
        if name not in payload or payload[name] is None or payload[name] == "":
            if field["required"]:
                raise ValueError(f"missing required field {name!r}")
            continue
        out[name] = _coerce(payload[name], field["type"])
    return out


def add_record(
    slug: str,
    payload: dict[str, Any],
    *,
    created_by: str = "",
) -> dict[str, Any]:
    spec = get_feature(slug)
    if spec is None or not spec.enabled:
        return {"status": "error", "message": f"Unknown feature {slug!r}."}
    try:
        clean = _validate_payload(spec, payload)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}
    record_id = str(uuid.uuid4())
    connection = _conn()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO custom_feature_records (id, feature_id, payload, created_by)
            VALUES (%s, %s, %s::jsonb, %s)
            """,
            (record_id, spec.slug, json.dumps(clean), created_by or None),
        )
        connection.commit()
        cursor.close()
    finally:
        connection.close()
    return {"status": "ok", "id": record_id, "payload": clean}


def list_records(slug: str, limit: int = 50) -> dict[str, Any]:
    spec = get_feature(slug)
    if spec is None:
        return {"status": "error", "message": f"Unknown feature {slug!r}."}
    connection = _conn()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id::text, payload, created_by, created_at
            FROM custom_feature_records
            WHERE feature_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (spec.slug, max(1, min(int(limit), 200))),
        )
        rows = cursor.fetchall()
        cursor.close()
    finally:
        connection.close()
    records = [
        {
            "id": row[0],
            "payload": row[1],
            "created_by": row[2],
            "created_at": str(row[3]),
        }
        for row in rows
    ]
    return {"status": "ok", "feature": spec.slug, "records": records}


def search_records(slug: str, query: str, limit: int = 20) -> dict[str, Any]:
    spec = get_feature(slug)
    if spec is None:
        return {"status": "error", "message": f"Unknown feature {slug!r}."}
    connection = _conn()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id::text, payload, created_by, created_at
            FROM custom_feature_records
            WHERE feature_id = %s
              AND payload::text ILIKE %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (spec.slug, f"%{query}%", max(1, min(int(limit), 200))),
        )
        rows = cursor.fetchall()
        cursor.close()
    finally:
        connection.close()
    return {
        "status": "ok",
        "feature": spec.slug,
        "query": query,
        "records": [
            {
                "id": row[0],
                "payload": row[1],
                "created_by": row[2],
                "created_at": str(row[3]),
            }
            for row in rows
        ],
    }


def feature_to_agent_kwargs(spec: FeatureSpec) -> dict[str, Any]:
    """Fields AgentSpec needs, without importing agent_registry here."""
    return {
        "name": spec.slug,
        "keywords": spec.keywords,
        "planner_blurb": spec.planner_blurb,
        "roles": spec.roles,
        "skill_title": spec.title,
        "skill_bullets": (spec.description,),
        "skill_tags": (spec.slug,),
    }
