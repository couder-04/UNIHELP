"""Allowlisted admin tools for org profile, roster import, and features.

Every function re-checks role == admin. None of them take raw SQL.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import secrets
import uuid
from typing import Any, Callable

import db
import org_profile
from authenticator import invalidate_auth_cache
from canonical_people import hash_auth_key
from config import (
    ATTENDANCE_DB_NAME,
    AUTH_DB_NAME,
    COMPLAINTS_DB_NAME,
    TIMETABLE_DB_NAME,
)
from custom_features import add_feature as _add_feature
from custom_features import disable_feature as _disable_feature
from custom_features import list_features
from org_profile import OrgProfileError

logger = logging.getLogger(__name__)

_reload_callbacks: list[Callable[[], None]] = []


def register_reload(callback: Callable[[], None]) -> None:
    _reload_callbacks.append(callback)


def reload_campus(role: str | None = None) -> dict[str, Any]:
    """Re-read YAML and refresh planner/executor routing."""
    if role is not None:
        denied = _require_admin(role)
        if denied:
            return denied
    org_profile.reload_org_profile(org_profile.ORG.path)
    for cb in list(_reload_callbacks):
        cb()
    return {
        "status": "ok",
        "org_id": org_profile.ORG.org_id,
        "display_name": org_profile.ORG.display_name,
        "enabled_agents": list(org_profile.ORG.enabled_agents),
        "features": [f.slug for f in list_features()],
    }


def _require_admin(role: str) -> dict[str, Any] | None:
    if str(role or "").strip().lower() != "admin":
        return {
            "status": "error",
            "message": "Only an authenticated admin can change campus setup.",
        }
    return None


def show_org_profile(role: str) -> dict[str, Any]:
    denied = _require_admin(role)
    if denied:
        return denied
    data = org_profile.profile_as_dict()
    data["status"] = "ok"
    data["features"] = [
        {"slug": f.slug, "title": f.title, "enabled": f.enabled}
        for f in list_features(enabled_only=False)
    ]
    return data


def _as_item_list(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        raise OrgProfileError("catalog patch must be a list of names or {name, aliases}")
    items: list[dict[str, Any]] = []
    for entry in raw:
        if isinstance(entry, str):
            items.append({"name": entry.strip()})
        elif isinstance(entry, dict):
            name = str(entry.get("name") or "").strip()
            aliases = entry.get("aliases") or []
            if not isinstance(aliases, list):
                aliases = [aliases]
            items.append(
                {
                    "name": name,
                    "aliases": [str(a).strip() for a in aliases if str(a).strip()],
                }
            )
        else:
            raise OrgProfileError("catalog entry must be a string or mapping")
        if not items[-1]["name"]:
            raise OrgProfileError("catalog entry missing name")
    return items


def _names(entries: list[dict[str, Any]]) -> list[str]:
    return [e["name"] for e in entries]


_UPDATE_KEYS = frozenset(
    {
        "display_name",
        "timezone",
        "student_id_pattern",
        "student_id_field",
        "enabled_agents",
        "add_hostels",
        "remove_hostels",
        "add_rooms",
        "remove_rooms",
        "add_buses",
        "remove_buses",
        "add_meals",
        "remove_meals",
        "add_complaint_categories",
        "remove_complaint_categories",
        "replace_hostels",
        "replace_rooms",
        "replace_buses",
        "replace_meals",
        "replace_complaint_categories",
    }
)


def update_org_profile(role: str, **kwargs: Any) -> dict[str, Any]:
    denied = _require_admin(role)
    if denied:
        return denied
    kwargs = {k: v for k, v in kwargs.items() if k in _UPDATE_KEYS}
    display_name = kwargs.get("display_name")
    timezone = kwargs.get("timezone")
    student_id_pattern = kwargs.get("student_id_pattern")
    student_id_field = kwargs.get("student_id_field")
    enabled_agents = kwargs.get("enabled_agents")
    add_hostels = kwargs.get("add_hostels")
    remove_hostels = kwargs.get("remove_hostels")
    add_rooms = kwargs.get("add_rooms")
    remove_rooms = kwargs.get("remove_rooms")
    add_buses = kwargs.get("add_buses")
    remove_buses = kwargs.get("remove_buses")
    add_meals = kwargs.get("add_meals")
    remove_meals = kwargs.get("remove_meals")
    add_complaint_categories = kwargs.get("add_complaint_categories")
    remove_complaint_categories = kwargs.get("remove_complaint_categories")
    replace_hostels = kwargs.get("replace_hostels")
    replace_rooms = kwargs.get("replace_rooms")
    replace_buses = kwargs.get("replace_buses")
    replace_meals = kwargs.get("replace_meals")
    replace_complaint_categories = kwargs.get("replace_complaint_categories")

    data = org_profile.profile_as_dict()
    if display_name:
        data["display_name"] = display_name.strip()
    if timezone:
        data["timezone"] = timezone.strip()
    if student_id_pattern:
        data["identity"]["student_id_pattern"] = student_id_pattern.strip()
    if student_id_field:
        data["identity"]["student_id_field"] = student_id_field.strip()
    if enabled_agents is not None:
        data["enabled_agents"] = [str(a).strip() for a in enabled_agents if str(a).strip()]

    catalog = data["catalog"]
    patches = {
        "hostels": (add_hostels, remove_hostels, replace_hostels),
        "rooms": (add_rooms, remove_rooms, replace_rooms),
        "buses": (add_buses, remove_buses, replace_buses),
        "meals": (add_meals, remove_meals, replace_meals),
        "complaint_categories": (
            add_complaint_categories,
            remove_complaint_categories,
            replace_complaint_categories,
        ),
    }
    try:
        for field, (add, remove, replace) in patches.items():
            if replace is not None:
                if field == "complaint_categories":
                    catalog[field] = [
                        e["name"] for e in _as_item_list(replace)
                    ]
                else:
                    catalog[field] = _as_item_list(replace)
                continue
            if add is None and remove is None:
                continue
            current = catalog[field]
            if field == "complaint_categories":
                current_items = [{"name": c} for c in current]
            else:
                current_items = [
                    e if isinstance(e, dict) else {"name": e} for e in current
                ]
            if remove:
                drop = {n.lower() for n in _names(_as_item_list(remove))}
                current_items = [
                    e for e in current_items if e["name"].lower() not in drop
                ]
            if add:
                existing = {e["name"].lower() for e in current_items}
                for item in _as_item_list(add):
                    if item["name"].lower() in existing:
                        raise OrgProfileError(
                            f"catalog.{field} already has {item['name']!r}"
                        )
                    current_items.append(item)
                    existing.add(item["name"].lower())
            if field == "complaint_categories":
                catalog[field] = [e["name"] for e in current_items]
            else:
                catalog[field] = current_items
    except OrgProfileError as exc:
        return {"status": "error", "message": str(exc)}

    try:
        org_profile.save_org_profile(data)
    except OrgProfileError as exc:
        return {"status": "error", "message": str(exc)}

    refreshed = reload_campus()
    refreshed["message"] = "Org profile saved and routing reloaded."
    return refreshed


def _parse_people_blob(people: Any, csv_text: str | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if csv_text:
        reader = csv.DictReader(io.StringIO(csv_text))
        for raw in reader:
            rows.append({k.strip(): (v or "").strip() for k, v in raw.items() if k})
    if people is None:
        return rows
    if isinstance(people, str):
        people = json.loads(people)
    if not isinstance(people, list):
        raise ValueError("people must be a list of objects")
    for raw in people:
        if not isinstance(raw, dict):
            raise ValueError("each person must be an object")
        rows.append({str(k): "" if v is None else str(v).strip() for k, v in raw.items()})
    return rows


def _normalize_person(raw: dict[str, str]) -> dict[str, str]:
    role = (raw.get("role") or "student").strip().lower()
    if role not in {"student", "faculty", "admin"}:
        raise ValueError(f"invalid role {role!r}")
    external = (
        raw.get("external_id")
        or raw.get("roll_number")
        or raw.get("roll_num")
        or raw.get("roll")
        or ""
    ).strip()
    name = (raw.get("display_name") or raw.get("name") or raw.get("names") or "").strip()
    if not external or not name:
        raise ValueError("each person needs display_name/name and external_id/roll_number")
    auth_key = (
        raw.get("authentication_key") or raw.get("auth_key") or raw.get("key") or ""
    ).strip()
    generated = False
    if not auth_key:
        auth_key = f"{role}-{external.lower()}-{secrets.token_urlsafe(4)}"
        generated = True
    return {
        "role": role,
        "external_id": external,
        "display_name": name,
        "authentication_key": auth_key,
        "generated_key": "1" if generated else "0",
    }


def _mirror_person(person: dict[str, str], person_id: str) -> None:
    """Keep the old per-domain identity tables in sync for this release."""
    role, name, ext, key = (
        person["role"],
        person["display_name"],
        person["external_id"],
        person["authentication_key"],
    )
    users = db.get_connection(AUTH_DB_NAME)
    try:
        cur = users.cursor()
        cur.execute(
            """
            INSERT INTO users (authentication_key, role, names, roll_number)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (authentication_key) DO UPDATE
              SET role = EXCLUDED.role,
                  names = EXCLUDED.names,
                  roll_number = EXCLUDED.roll_number
            """,
            (key, role, name, ext),
        )
        users.commit()
        cur.close()
    except Exception:
        logger.exception("mirror campus_agent.users failed for %s", ext)
        users.rollback()
    finally:
        users.close()

    try:
        complaints = db.get_connection(COMPLAINTS_DB_NAME)
        try:
            cur = complaints.cursor()
            cur.execute(
                """
                INSERT INTO users (
                    id, authentication_key, role, names, roll_number, is_active, person_id
                ) VALUES (%s, %s, %s, %s, %s, TRUE, %s)
                ON CONFLICT (id) DO UPDATE
                  SET authentication_key = EXCLUDED.authentication_key,
                      role = EXCLUDED.role,
                      names = EXCLUDED.names,
                      roll_number = EXCLUDED.roll_number,
                      person_id = EXCLUDED.person_id
                """,
                (ext, key, role, name, ext, person_id),
            )
            complaints.commit()
            cur.close()
        finally:
            complaints.close()
    except Exception:
        logger.exception("mirror complaints.users failed for %s", ext)

    for dbname, sql, args in (
        (
            ATTENDANCE_DB_NAME,
            """
            INSERT INTO people (roll_num, name, role, person_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (roll_num) DO UPDATE
              SET name = EXCLUDED.name,
                  role = EXCLUDED.role,
                  person_id = EXCLUDED.person_id
            """,
            (ext, name, role, person_id),
        ),
        (
            TIMETABLE_DB_NAME,
            """
            INSERT INTO people (roll_num, name, role, person_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (roll_num) DO UPDATE
              SET name = EXCLUDED.name,
                  role = EXCLUDED.role,
                  person_id = EXCLUDED.person_id
            """,
            (ext, name, role, person_id),
        ),
    ):
        try:
            conn = db.get_connection(dbname)
            try:
                cur = conn.cursor()
                cur.execute(sql, args)
                conn.commit()
                cur.close()
            finally:
                conn.close()
        except Exception:
            logger.exception("mirror %s.people failed for %s", dbname, ext)


def import_people(
    role: str,
    people: Any = None,
    csv_text: str | None = None,
) -> dict[str, Any]:
    denied = _require_admin(role)
    if denied:
        return denied
    try:
        raw_rows = _parse_people_blob(people, csv_text)
    except (ValueError, json.JSONDecodeError) as exc:
        return {"status": "error", "message": str(exc)}
    if not raw_rows:
        return {"status": "error", "message": "No people rows to import."}
    if len(raw_rows) > 500:
        return {"status": "error", "message": "Import at most 500 people per prompt."}

    identity = org_profile.ORG.identity
    prepared: list[dict[str, str]] = []
    errors: list[str] = []
    for index, raw in enumerate(raw_rows, start=1):
        try:
            person = _normalize_person(raw)
            if person["role"] == "student":
                identity.validate_student_external_id(person["external_id"])
            prepared.append(person)
        except (ValueError, OrgProfileError) as exc:
            errors.append(f"row {index}: {exc}")
    if errors:
        return {
            "status": "error",
            "message": "Import aborted; no rows written.",
            "errors": errors,
        }

    org_id = org_profile.ORG.org_id
    created_keys: list[dict[str, str]] = []
    connection = db.get_connection(AUTH_DB_NAME)
    try:
        cursor = connection.cursor()
        for person in prepared:
            person_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO people (
                    id, org_id, external_id, role, display_name,
                    auth_key_hash, authentication_key
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (org_id, external_id) DO UPDATE
                  SET role = EXCLUDED.role,
                      display_name = EXCLUDED.display_name,
                      auth_key_hash = EXCLUDED.auth_key_hash,
                      authentication_key = EXCLUDED.authentication_key
                RETURNING id::text
                """,
                (
                    person_id,
                    org_id,
                    person["external_id"],
                    person["role"],
                    person["display_name"],
                    hash_auth_key(person["authentication_key"]),
                    person["authentication_key"],
                ),
            )
            row = cursor.fetchone()
            resolved_id = row[0] if row else person_id
            _mirror_person(person, resolved_id)
            if person["generated_key"] == "1":
                created_keys.append(
                    {
                        "external_id": person["external_id"],
                        "authentication_key": person["authentication_key"],
                        "role": person["role"],
                    }
                )
        connection.commit()
        cursor.close()
    except Exception as exc:
        connection.rollback()
        logger.exception("import_people failed")
        return {"status": "error", "message": f"Database import failed: {exc}"}
    finally:
        connection.close()

    invalidate_auth_cache()
    return {
        "status": "ok",
        "imported": len(prepared),
        "generated_authentication_keys": created_keys,
        "message": (
            f"Imported {len(prepared)} people into campus_agent.people "
            "and mirrored identity copies. Store generated keys now; "
            "they are not shown again."
        ),
    }


def add_campus_feature(
    role: str,
    *,
    name: str,
    description: str,
    fields: list[dict[str, Any]],
    title: str = "",
    keywords: list[str] | None = None,
    roles: list[str] | None = None,
    created_by: str = "",
) -> dict[str, Any]:
    denied = _require_admin(role)
    if denied:
        return denied
    result = _add_feature(
        name=name,
        title=title,
        description=description,
        keywords=keywords,
        fields=fields,
        roles=roles,
        created_by=created_by,
    )
    if result.get("status") == "ok":
        reload_campus()
        result["routing"] = "reloaded"
    return result


def disable_campus_feature(role: str, name: str) -> dict[str, Any]:
    denied = _require_admin(role)
    if denied:
        return denied
    result = _disable_feature(name)
    if result.get("status") == "ok":
        reload_campus()
        result["routing"] = "reloaded"
    return result


def list_campus_features(role: str) -> dict[str, Any]:
    denied = _require_admin(role)
    if denied:
        return denied
    return {
        "status": "ok",
        "features": [
            {
                "slug": f.slug,
                "title": f.title,
                "description": f.description,
                "keywords": list(f.keywords),
                "fields": list(f.fields),
                "roles": list(f.roles),
                "enabled": f.enabled,
            }
            for f in list_features(enabled_only=False)
        ],
    }
