"""Admin-only campus setup agent.

chat(user_input, user_metadata) matches the frozen plugin contract.
Tools never accept SQL; they patch YAML, import people, or register a
JSON-backed feature.
"""

from __future__ import annotations

import json
import logging

from llm import cached_system_message, chat_create, identity_message
from setup_functions import (
    add_campus_feature,
    disable_campus_feature,
    import_people,
    list_campus_features,
    reload_campus,
    show_org_profile,
    update_org_profile,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are the campus SETUP agent. Only an authenticated admin reaches you.

You configure this deployment so it matches a university, using tools:
- show_org_profile: current YAML catalog, enabled agents, custom features
- update_org_profile: display name, timezone, roll-number regex, enable/disable
  the built-in agents (mess, bus, complaint, room_booking, attendance, notice,
  timetable), and add/remove/replace catalog hostels, buses, rooms, meals,
  complaint categories. Aliases are optional.
- import_people: JSON list or CSV text of people. Columns: role, display_name
  (or name), external_id (or roll_number), optional authentication_key.
  Missing keys are generated and MUST be quoted back to the admin.
- add_feature: stand up a new campus service WITHOUT new SQL tables. You supply
  a name, description, keywords, and a field schema
  (name/type/required/description). Types: string, number, boolean, date.
  Students then talk to that feature by name (e.g. library).
- disable_feature / list_features
- reload_campus: re-read YAML after an on-disk edit (update_org_profile already reloads)

Never invent SQL. Never claim you created a PostgreSQL table. Features store
JSON rows. If a tool returns status=error, explain it and stop.

After a successful configure/import/add_feature, summarize what changed and
how a student would query it.
"""


class SetupAgent:
    def __init__(self):
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "show_org_profile",
                    "description": "Show the live org profile and custom features.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_org_profile",
                    "description": (
                        "Patch org YAML: campus name, timezone, student id "
                        "pattern, enabled built-in agents, catalog add/remove/replace."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "display_name": {"type": "string"},
                            "timezone": {"type": "string"},
                            "student_id_pattern": {"type": "string"},
                            "student_id_field": {"type": "string"},
                            "enabled_agents": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "add_hostels": {"type": "array", "items": {"type": "object"}},
                            "remove_hostels": {"type": "array", "items": {"type": "string"}},
                            "replace_hostels": {"type": "array"},
                            "add_rooms": {"type": "array"},
                            "remove_rooms": {"type": "array", "items": {"type": "string"}},
                            "replace_rooms": {"type": "array"},
                            "add_buses": {"type": "array"},
                            "remove_buses": {"type": "array", "items": {"type": "string"}},
                            "replace_buses": {"type": "array"},
                            "add_meals": {"type": "array"},
                            "remove_meals": {"type": "array", "items": {"type": "string"}},
                            "replace_meals": {"type": "array"},
                            "add_complaint_categories": {"type": "array"},
                            "remove_complaint_categories": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "replace_complaint_categories": {"type": "array"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "import_people",
                    "description": (
                        "Import students/faculty/admin. people is a JSON array; "
                        "csv_text is header+rows. Students must match the org roll pattern."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "people": {
                                "type": "array",
                                "items": {"type": "object"},
                            },
                            "csv_text": {"type": "string"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "add_feature",
                    "description": (
                        "Add a JSON-backed campus feature. fields is the record "
                        "schema (string|number|boolean|date). No raw SQL."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "fields": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "type": {"type": "string"},
                                        "required": {"type": "boolean"},
                                        "description": {"type": "string"},
                                    },
                                    "required": ["name", "type"],
                                },
                            },
                            "roles": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["name", "description", "fields"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "disable_feature",
                    "description": "Turn off a custom feature so the planner stops routing to it.",
                    "parameters": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_features",
                    "description": "List custom features.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "reload_campus",
                    "description": "Re-read the org YAML and refresh planner/executor.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    def execute_tool(self, name: str, arguments: dict, user_metadata: dict) -> dict:
        role = user_metadata.get("role") or ""
        admin_name = user_metadata.get("name") or ""
        if name == "show_org_profile":
            return show_org_profile(role)
        if name == "update_org_profile":
            return update_org_profile(role, **arguments)
        if name == "import_people":
            return import_people(
                role,
                people=arguments.get("people"),
                csv_text=arguments.get("csv_text"),
            )
        if name == "add_feature":
            return add_campus_feature(
                role,
                name=arguments.get("name") or "",
                title=arguments.get("title") or "",
                description=arguments.get("description") or "",
                fields=arguments.get("fields") or [],
                keywords=arguments.get("keywords"),
                roles=arguments.get("roles"),
                created_by=admin_name,
            )
        if name == "disable_feature":
            return disable_campus_feature(role, arguments.get("name") or "")
        if name == "list_features":
            return list_campus_features(role)
        if name == "reload_campus":
            return reload_campus(role)
        return {"status": "error", "message": f"Unknown tool: {name}"}

    def chat(self, user_input: str, user_metadata: dict):
        role = str(user_metadata.get("role") or "").strip().lower()
        if role != "admin":
            return "Only an authenticated admin can configure the campus or add features."

        messages = [
            cached_system_message(SYSTEM_PROMPT),
            identity_message(
                {
                    "role": user_metadata.get("role"),
                    "name": user_metadata.get("name"),
                    "Time and Date": user_metadata.get("Time and Date"),
                }
            ),
            {"role": "user", "content": user_input},
        ]

        for _ in range(8):
            response = chat_create(
                cache_key="setup",
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
            )
            message = response.choices[0].message
            if not message.tool_calls:
                return message.content

            messages.append(message)
            for tool_call in message.tool_calls:
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                if not isinstance(arguments, dict):
                    arguments = {}
                result = self.execute_tool(tool_call.function.name, arguments, user_metadata)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str),
                    }
                )

        return "ERROR: Setup agent exceeded the maximum number of tool rounds."
