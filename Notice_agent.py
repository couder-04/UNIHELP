import json
import logging

from llm import cached_system_message, chat_create, identity_message
from notice_functions import (
    archive_expired_notices,
    call_tool,
    publish_notice,
    view_notices,
)
from fast_parse import format_notice_reply, parse_notice_query

logger = logging.getLogger(__name__)


class NoticeAgent:

    SYSTEM_PROMPT = """
You are the IIT Patna Notice Board Agent.

Your job is to answer questions and handle notices using your tools.
Do not ask the user for their role, name, or the current time -
they are provided in the authenticated identity message.
Use the Time and Date from identity for relative times such as today, now, and notice expiry.

Students can view notices. Faculty and admin can publish or archive.
If a tool returns an authorization error, explain it clearly.

FORMATTING RULES:
When a user asks to view notices, present them in this Bulletin Feed format.

### Active Notices

**[Notice Type]** | *[Date]* | By: [Author]
> [Content of the notice]
"""

    def __init__(self):
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "view_notices",
                    "description": "View active notices for a given audience group.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "caller_audience": {"type": "string", "description": "e.g., 'All_Students', 'Staff', 'All'"},
                            "caller_authority": {"type": "string", "description": "User role"}
                        },
                        "required": ["caller_audience", "caller_authority"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "publish_notice",
                    "description": "Publish a notice. Only faculty and admin users are authorized.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "notice_type": {"type": "string", "description": "e.g., 'Important Alert', 'General'"},
                            "author_id": {"type": "string"},
                            "author_authority": {"type": "string"},
                            "target_audience": {"type": "array", "items": {"type": "string"}},
                            "expires_at": {"type": "string", "description": "ISO format date string"}
                        },
                        "required": ["content", "notice_type", "target_audience", "expires_at"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "archive_expired_notices",
                    "description": "Archive past-due notices. Only admin users are authorized.",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    def chat(self, user_input: str, user_metadata: dict):
        role = user_metadata.get("role", "Unknown")
        name = user_metadata.get("name", "Unknown")
        time_and_date = user_metadata.get("Time and Date", "Unknown")

        parsed = parse_notice_query(user_input, time_and_date)
        if parsed is not None:
            logger.debug("fast_parse hit: %s -> %s", user_input, parsed)
            action = parsed.get("action")
            if action == "view":
                audience = "All_Students" if str(role).lower() == "student" else "Staff"
                rows = view_notices(audience, role)
                return format_notice_reply(parsed, rows)
            if action == "archive":
                result = archive_expired_notices(user=role)
                return format_notice_reply(parsed, result)
            if action == "publish":
                audience = parsed.get("target_audience") or ["All"]
                result = publish_notice(
                    content=parsed.get("content") or "",
                    notice_type=parsed.get("notice_type") or "General",
                    author_id=name,
                    author_authority=role,
                    target_audience=audience,
                    expires_at=parsed.get("expires_at") or "",
                    user=role,
                )
                return format_notice_reply(parsed, result)

        messages = [
            cached_system_message(self.SYSTEM_PROMPT),
            identity_message(
                {"name": name, "role": role, "Time and Date": time_and_date},
                label="Authenticated user",
            ),
            {"role": "user", "content": user_input},
        ]

        for _ in range(5):
            response = chat_create(
                cache_key="notice",
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
            )
            message = response.choices[0].message
            if not message.tool_calls:
                return message.content

            messages.append(message)
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                if tool_name in {"publish_notice", "archive_expired_notices"}:
                    arguments["user"] = role
                if tool_name == "publish_notice":
                    arguments["author_id"] = name
                    arguments["author_authority"] = role
                if tool_name == "view_notices":
                    arguments["caller_audience"] = "All_Students" if role.lower() == "student" else "Staff"
                    arguments["caller_authority"] = role

                result = call_tool(tool_name, **arguments)
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

        return "ERROR: Notice agent exceeded the maximum number of tool rounds."
