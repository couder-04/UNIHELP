"""Generic agent for an admin-defined JSON feature."""

from __future__ import annotations

import json
import logging

from custom_features import (
    add_record,
    get_feature,
    list_records,
    search_records,
)
from llm import cached_system_message, chat_create, identity_message

logger = logging.getLogger(__name__)


class CustomFeatureAgent:
    def __init__(self, slug: str):
        self.slug = slug
        spec = get_feature(slug)
        self.spec = spec
        title = spec.title if spec else slug
        fields = list(spec.fields) if spec else []
        field_help = ", ".join(
            f"{f['name']} ({f['type']}{' required' if f.get('required') else ''})"
            for f in fields
        )
        self.SYSTEM_PROMPT = f"""
You are the {title} campus agent.
{spec.description if spec else ''}

Records use these fields: {field_help or '(none)'}.
Use list_records, search_records, or add_record. Do not invent columns.
Do not ask for identity; it is in the authenticated message.
"""
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_records",
                    "description": f"List recent {title} records.",
                    "parameters": {
                        "type": "object",
                        "properties": {"limit": {"type": "integer"}},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_records",
                    "description": f"Search {title} records by text.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "limit": {"type": "integer"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "add_record",
                    "description": f"Add a {title} record. payload keys must match the schema.",
                    "parameters": {
                        "type": "object",
                        "properties": {"payload": {"type": "object"}},
                        "required": ["payload"],
                    },
                },
            },
        ]

    def chat(self, user_input: str, user_metadata: dict):
        spec = self.spec or get_feature(self.slug)
        if spec is None or not spec.enabled:
            return f"The {self.slug} service is not available."
        role = str(user_metadata.get("role") or "").strip().lower()
        if spec.roles and role not in spec.roles:
            return f"Your role ({role}) cannot use {spec.title}."

        text = (user_input or "").strip().lower()
        if text in {"list", "show all", "list all"} or text.startswith("list "):
            result = list_records(self.slug)
            return json.dumps(result, default=str, indent=2)

        messages = [
            cached_system_message(self.SYSTEM_PROMPT),
            identity_message(
                {
                    "role": user_metadata.get("role"),
                    "name": user_metadata.get("name"),
                    "roll_number": user_metadata.get("roll_number"),
                    "Time and Date": user_metadata.get("Time and Date"),
                }
            ),
            {"role": "user", "content": user_input},
        ]
        actor = user_metadata.get("roll_number") or user_metadata.get("name") or ""

        for _ in range(6):
            response = chat_create(
                cache_key=f"feature-{self.slug}",
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
                name = tool_call.function.name
                if name == "list_records":
                    result = list_records(self.slug, limit=arguments.get("limit") or 50)
                elif name == "search_records":
                    result = search_records(
                        self.slug,
                        arguments.get("query") or "",
                        limit=arguments.get("limit") or 20,
                    )
                elif name == "add_record":
                    result = add_record(
                        self.slug,
                        arguments.get("payload") or {},
                        created_by=str(actor),
                    )
                else:
                    result = {"status": "error", "message": f"Unknown tool: {name}"}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str),
                    }
                )

        return f"ERROR: {self.slug} agent exceeded its tool-call limit."
