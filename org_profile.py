"""Load and validate the single-org profile used by planner/fast_parse/auth.

There is exactly one org per deploy. ORG_PROFILE_PATH selects the YAML
(default: orgs/iit_patna.yaml). Request-time org switching is Phase 9 of
the multi-org design and is intentionally not built here.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

_REPO_ROOT = Path(__file__).resolve().parent
_DEFAULT_PROFILE = _REPO_ROOT / "orgs" / "iit_patna.yaml"

# Agents that actually exist in this repo. enabled_agents may only name
# these; a typo should fail at startup, not silently drop a route.
KNOWN_AGENTS = frozenset(
    {
        "mess",
        "bus",
        "complaint",
        "room_booking",
        "attendance",
        "notice",
        "timetable",
    }
)

_REQUIRED_TOP = (
    "org_id",
    "display_name",
    "timezone",
    "roles",
    "enabled_agents",
    "catalog",
    "identity",
)
_REQUIRED_CATALOG = (
    "hostels",
    "rooms",
    "buses",
    "meals",
    "complaint_categories",
)
_REQUIRED_IDENTITY = ("student_id_field", "student_id_pattern")


class OrgProfileError(ValueError):
    """Malformed or incomplete org profile. Fail loud at startup."""


@dataclass(frozen=True)
class CatalogItem:
    name: str
    aliases: tuple[str, ...] = ()

    @property
    def labels(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


@dataclass(frozen=True)
class Catalog:
    hostels: tuple[CatalogItem, ...]
    rooms: tuple[CatalogItem, ...]
    buses: tuple[CatalogItem, ...]
    meals: tuple[CatalogItem, ...]
    complaint_categories: tuple[str, ...]


@dataclass(frozen=True)
class IdentitySpec:
    student_id_field: str
    student_id_pattern: str
    student_id_re: re.Pattern[str] = field(repr=False)

    def validate_student_external_id(self, value: str) -> None:
        if not self.student_id_re.fullmatch(value or ""):
            raise OrgProfileError(
                f"Student {self.student_id_field} {value!r} does not match "
                f"{self.student_id_pattern}"
            )


@dataclass(frozen=True)
class OrgProfile:
    org_id: str
    display_name: str
    timezone: str
    roles: tuple[str, ...]
    enabled_agents: tuple[str, ...]
    catalog: Catalog
    identity: IdentitySpec
    path: Path


def _require_str(data: dict[str, Any], key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OrgProfileError(f"{where}.{key} must be a non-empty string")
    return value.strip()


def _require_list(data: dict[str, Any], key: str, where: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list) or len(value) == 0:
        raise OrgProfileError(
            f"{where}.{key} must be a non-empty list (refusing to start "
            f"with a missing catalog/field that would silently disable a route)"
        )
    return value


def _parse_items(raw: Iterable[Any], field: str) -> tuple[CatalogItem, ...]:
    items: list[CatalogItem] = []
    seen: set[str] = set()
    for entry in raw:
        if isinstance(entry, str):
            name = entry.strip()
            aliases: tuple[str, ...] = ()
        elif isinstance(entry, dict):
            name = str(entry.get("name") or "").strip()
            raw_aliases = entry.get("aliases") or []
            if raw_aliases and not isinstance(raw_aliases, list):
                raise OrgProfileError(f"catalog.{field} aliases must be a list")
            aliases = tuple(str(a).strip() for a in raw_aliases if str(a).strip())
        else:
            raise OrgProfileError(
                f"catalog.{field} entries must be a name string or "
                f"{{name, aliases}} mapping"
            )
        if not name:
            raise OrgProfileError(f"catalog.{field} entry is missing name")
        key = name.lower()
        if key in seen:
            raise OrgProfileError(f"catalog.{field} has duplicate name {name!r}")
        seen.add(key)
        items.append(CatalogItem(name=name, aliases=aliases))
    if not items:
        raise OrgProfileError(f"catalog.{field} must not be empty")
    return tuple(items)


def _parse_categories(raw: Iterable[Any]) -> tuple[str, ...]:
    cats: list[str] = []
    seen: set[str] = set()
    for entry in raw:
        if isinstance(entry, dict):
            name = str(entry.get("name") or "").strip()
        else:
            name = str(entry).strip()
        if not name:
            raise OrgProfileError("catalog.complaint_categories has an empty name")
        key = name.lower()
        if key in seen:
            raise OrgProfileError(
                f"catalog.complaint_categories has duplicate {name!r}"
            )
        seen.add(key)
        cats.append(name)
    if not cats:
        raise OrgProfileError("catalog.complaint_categories must not be empty")
    return tuple(cats)


def load_org_profile(path: str | Path | None = None) -> OrgProfile:
    """Load YAML, validate required fields, return an immutable profile."""
    raw_path = path or os.getenv("ORG_PROFILE_PATH") or _DEFAULT_PROFILE
    profile_path = Path(raw_path)
    if not profile_path.is_absolute():
        profile_path = (_REPO_ROOT / profile_path).resolve()
    else:
        profile_path = profile_path.resolve()

    if not profile_path.is_file():
        raise OrgProfileError(f"Org profile not found: {profile_path}")

    try:
        with profile_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise OrgProfileError(f"Invalid YAML in {profile_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise OrgProfileError(f"{profile_path} must contain a mapping at the root")

    missing = [key for key in _REQUIRED_TOP if key not in data]
    if missing:
        raise OrgProfileError(
            f"{profile_path} missing required fields: {', '.join(missing)}"
        )

    org_id = _require_str(data, "org_id", "org")
    display_name = _require_str(data, "display_name", "org")
    timezone = _require_str(data, "timezone", "org")
    roles = tuple(str(r).strip() for r in _require_list(data, "roles", "org") if str(r).strip())
    if not roles:
        raise OrgProfileError("roles must be a non-empty list")

    enabled_raw = _require_list(data, "enabled_agents", "org")
    enabled: list[str] = []
    seen_agents: set[str] = set()
    for name in enabled_raw:
        agent = str(name).strip()
        if not agent:
            raise OrgProfileError("enabled_agents contains an empty name")
        if agent not in KNOWN_AGENTS:
            raise OrgProfileError(
                f"enabled_agents names unknown agent {agent!r}. "
                f"Known agents in this repo: {sorted(KNOWN_AGENTS)}"
            )
        if agent in seen_agents:
            raise OrgProfileError(f"enabled_agents has duplicate {agent!r}")
        seen_agents.add(agent)
        enabled.append(agent)

    catalog_raw = data.get("catalog")
    if not isinstance(catalog_raw, dict):
        raise OrgProfileError("catalog must be a mapping")
    missing_cat = [key for key in _REQUIRED_CATALOG if key not in catalog_raw]
    if missing_cat:
        raise OrgProfileError(
            f"catalog missing required fields: {', '.join(missing_cat)}"
        )

    catalog = Catalog(
        hostels=_parse_items(_require_list(catalog_raw, "hostels", "catalog"), "hostels"),
        rooms=_parse_items(_require_list(catalog_raw, "rooms", "catalog"), "rooms"),
        buses=_parse_items(_require_list(catalog_raw, "buses", "catalog"), "buses"),
        meals=_parse_items(_require_list(catalog_raw, "meals", "catalog"), "meals"),
        complaint_categories=_parse_categories(
            _require_list(catalog_raw, "complaint_categories", "catalog")
        ),
    )

    identity_raw = data.get("identity")
    if not isinstance(identity_raw, dict):
        raise OrgProfileError("identity must be a mapping")
    missing_id = [key for key in _REQUIRED_IDENTITY if key not in identity_raw]
    if missing_id:
        raise OrgProfileError(
            f"identity missing required fields: {', '.join(missing_id)}"
        )
    pattern = _require_str(identity_raw, "student_id_pattern", "identity")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise OrgProfileError(
            f"identity.student_id_pattern is not a valid regex: {exc}"
        ) from exc

    identity = IdentitySpec(
        student_id_field=_require_str(identity_raw, "student_id_field", "identity"),
        student_id_pattern=pattern,
        student_id_re=compiled,
    )

    return OrgProfile(
        org_id=org_id,
        display_name=display_name,
        timezone=timezone,
        roles=roles,
        enabled_agents=tuple(enabled),
        catalog=catalog,
        identity=identity,
        path=profile_path,
    )


def catalog_item_to_raw(item: CatalogItem) -> str | dict[str, Any]:
    if item.aliases:
        return {"name": item.name, "aliases": list(item.aliases)}
    return {"name": item.name}


def profile_as_dict(profile: OrgProfile | None = None) -> dict[str, Any]:
    """Serialize the live profile so admin setup can patch and write YAML."""
    org = profile or ORG
    return {
        "org_id": org.org_id,
        "display_name": org.display_name,
        "timezone": org.timezone,
        "roles": list(org.roles),
        "enabled_agents": list(org.enabled_agents),
        "catalog": {
            "hostels": [catalog_item_to_raw(i) for i in org.catalog.hostels],
            "rooms": [catalog_item_to_raw(i) for i in org.catalog.rooms],
            "buses": [catalog_item_to_raw(i) for i in org.catalog.buses],
            "meals": [catalog_item_to_raw(i) for i in org.catalog.meals],
            "complaint_categories": list(org.catalog.complaint_categories),
        },
        "identity": {
            "student_id_field": org.identity.student_id_field,
            "student_id_pattern": org.identity.student_id_pattern,
        },
    }


def save_org_profile(
    data: dict[str, Any],
    path: str | Path | None = None,
) -> OrgProfile:
    """Validate then atomically replace the YAML. Fail loud if invalid.

    Writes a sibling .bak of the previous file so an admin prompt cannot
    destroy the only working profile.
    """
    target = Path(path) if path is not None else ORG.path
    if not target.is_absolute():
        target = (_REPO_ROOT / target).resolve()
    tmp = target.with_name(target.name + ".tmp")
    body = (
        "# Written by the admin setup agent. Invalid values are rejected "
        "before this file is replaced (see org_profile.save_org_profile).\n"
        + yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    )
    tmp.write_text(body, encoding="utf-8")
    try:
        load_org_profile(tmp)
    except OrgProfileError:
        tmp.unlink(missing_ok=True)
        raise
    if target.is_file():
        backup = target.with_name(target.name + ".bak")
        backup.write_bytes(target.read_bytes())
    tmp.replace(target)
    return reload_org_profile(target)


def reload_org_profile(path: str | Path | None = None) -> OrgProfile:
    """Replace the process-wide ORG singleton. Used by tests and admin setup."""
    global ORG
    ORG = load_org_profile(path)
    return ORG


ORG: OrgProfile = load_org_profile()
