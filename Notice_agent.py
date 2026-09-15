import json
import time
from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from notice_functions import call_tool

class NoticeAgent:

    def __init__(self):
        self.client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
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

        system_prompt = f"""
    You are the IIT Patna Notice Board Agent.

    AUTHENTICATED USER:
    - Name: {name}
    - Role: {role}
    - Time and Date: {time_and_date}

    Your job is to answer questions and handle notices using your tools.
    NEVER ask the user for their role, name, authorization, or the current time.
    Use Time and Date for relative times such as today, now, and notice expiry.
    
    For publishing or archiving, student roles are not authorized; only faculty and admin are authorized.
    If a tool returns an error about authorization, explain it clearly to the user.

    FORMATTING RULES:
    When a user asks to view notices, you MUST present them in the following Bulletin Feed format. Do not use tables.

    ### 📢 Active Notices
    
    🔴 **[Notice Type]** | *[Date]* | By: [Author]
    > [Content of the notice]
    
    Use a 🔴 emoji for Important/Urgent Alerts, and a 🔵 emoji for General notices.
    """
        
        # This line is now perfectly aligned with system_prompt
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]

        while True:
            response = self.client.chat.completions.create(
                model=LLM_MODEL, messages=messages, tools=self.tools, tool_choice="auto"
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