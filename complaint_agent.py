import json

from llm import cached_system_message, chat_create, get_client, identity_message
from complaint_functions import (
    create_complaint,
    get_complaint,
    list_complaints,
    verify_complaint,
    complete_complaint,
    search_duplicates,
)


ROLE_NAMES = {
    "student": "Student",
    "faculty": "Faculty",
    "warden": "Warden",
    "technician": "Technician",
    "hod": "HOD",
    "admin": "Admin",
    "guest": "Guest",
}

SYSTEM_PROMPT = """
You are the Complaint Agent for IIT Patna campus.

AUTHENTICATED USER
- Role, identifier, name, and Time and Date (IST) are provided in the following message.
- Students are identified by roll number.
- Faculty and Admin are identified by email or roll number.
- NEVER ask for or output a UUID.
- NEVER replace the authenticated identifier with an identifier supplied by the user.
- Tool-side RBAC is authoritative.

WORKFLOW
1. User files a complaint with category academic, hostel, or mess.
   Status starts as PENDING_VERIFICATION.
2. Admin or faculty verifies it. Status becomes PROGRESS.
3. When the issue is solved, admin or faculty marks it COMPLETED.
Only the latest 50 completed complaints in each category are kept.

CAPABILITIES
- Create complaints
- View and list complaints
- Verify pending complaints (faculty/admin)
- Complete complaints that are in PROGRESS (faculty/admin)
- Search open duplicates before creating

ROLE RULES
- Student: create, view own complaints, list own complaints.
- Faculty / Admin: student powers + verify pending complaints + complete complaints in PROGRESS.
- Students cannot verify or complete complaints.

CREATION
- Ask only for missing information.
- Category must be one of: academic, hostel, mess.
- Infer the category from the request when obvious (food -> mess, room/hostel facilities -> hostel, classes/exams -> academic).
- Before creating, search for an open duplicate with the same category.
- If an open duplicate exists (PENDING_VERIFICATION or PROGRESS), do NOT create a new complaint. Tell the user the existing complaint number and its status.
- create_complaint itself also rejects duplicates.

IDENTIFIERS
- Complaint identifiers are human complaint numbers such as C-123456.
- User identifiers are student roll numbers or staff emails.
- Do not mention database UUIDs to the user.

STATUS FLOW
PENDING_VERIFICATION -> PROGRESS -> COMPLETED
Do not invent other statuses.

OUTPUT
- Be concise and factual.
- Use markdown tables for complaint lists.
- Show complaint number, category, and status.
- No greetings, emojis, or unnecessary follow-up questions.
"""


class ComplaintAgent:
    """LLM complaint agent with authenticated identity and tool-side RBAC."""

    def __init__(self):
        self.client = get_client()

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "create_complaint",
                    "description": (
                        "Log a new complaint tagged academic, hostel, or mess. "
                        "Rejected if the same complaint is already waiting for "
                        "verification or under PROGRESS."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_identifier": {
                                "type": "string",
                                "description": "Student roll number or staff email",
                            },
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "category": {
                                "type": "string",
                                "enum": ["academic", "hostel", "mess"],
                            },
                        },
                        "required": ["user_identifier", "title", "description", "category"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_complaint",
                    "description": "Get a complaint by human complaint number such as C-123456. Never use UUID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "complaint_number": {
                                "type": "string",
                                "description": "Human complaint number, e.g. C-123456",
                            },
                            "user_identifier": {
                                "type": "string",
                                "description": "Authenticated roll number or email",
                            },
                        },
                        "required": ["complaint_number", "user_identifier"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_complaints",
                    "description": "List complaints visible to the authenticated user.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_identifier": {
                                "type": "string",
                                "description": "Authenticated roll number or email",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["PENDING_VERIFICATION", "PROGRESS", "COMPLETED"],
                            },
                            "category": {
                                "type": "string",
                                "enum": ["academic", "hostel", "mess"],
                            },
                            "limit": {"type": "integer", "default": 50},
                        },
                        "required": ["user_identifier"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "verify_complaint",
                    "description": (
                        "Admin or faculty verifies a pending complaint. "
                        "Moves it from PENDING_VERIFICATION to PROGRESS."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "complaint_number": {"type": "string"},
                            "verifier_identifier": {
                                "type": "string",
                                "description": "Faculty or admin email / roll number",
                            },
                        },
                        "required": ["complaint_number", "verifier_identifier"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "complete_complaint",
                    "description": (
                        "Admin or faculty marks a complaint under PROGRESS as COMPLETED. "
                        "Older completed complaints beyond the last 50 in that category are deleted."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "complaint_number": {"type": "string"},
                            "actor_identifier": {
                                "type": "string",
                                "description": "Faculty or admin email / roll number",
                            },
                        },
                        "required": ["complaint_number", "actor_identifier"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_duplicates",
                    "description": (
                        "Find an already-open complaint with the same category "
                        "before creating a new one."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "enum": ["academic", "hostel", "mess"],
                            },
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "query": {"type": "string"},
                        },
                        "required": ["category"],
                    },
                },
            },
        ]

    def _authenticated_identifier(self, requested_identifier, authenticated_identifier):
        """Prevent the model from acting as another user."""
        return authenticated_identifier or requested_identifier

    def execute_tool(self, name, arguments, authenticated_identifier=None):
        """Execute tools and force the authenticated identity for actor actions."""
        args = dict(arguments or {})

        if name == "create_complaint":
            args["user_identifier"] = self._authenticated_identifier(
                args.get("user_identifier"), authenticated_identifier
            )
            return create_complaint(
                args["user_identifier"], args["title"], args["description"], args["category"]
            )

        if name == "get_complaint":
            args["user_identifier"] = self._authenticated_identifier(
                args.get("user_identifier"), authenticated_identifier
            )
            return get_complaint(args["complaint_number"], args["user_identifier"])

        if name == "list_complaints":
            args["user_identifier"] = self._authenticated_identifier(
                args.get("user_identifier"), authenticated_identifier
            )
            return list_complaints(
                args["user_identifier"],
                args.get("status"),
                args.get("category"),
                limit=args.get("limit", 50),
            )

        if name == "verify_complaint":
            args["verifier_identifier"] = authenticated_identifier or args.get("verifier_identifier")
            return verify_complaint(args["complaint_number"], args["verifier_identifier"])

        if name == "complete_complaint":
            args["actor_identifier"] = authenticated_identifier or args.get("actor_identifier")
            return complete_complaint(args["complaint_number"], args["actor_identifier"])

        if name == "search_duplicates":
            return search_duplicates(
                args.get("category"),
                query=args.get("query"),
                title=args.get("title"),
                description=args.get("description"),
            )

        return {"status": "error", "message": f"Unknown tool: {name}"}

    def chat(
        self,
        user_input: str,
        role: str,
        user_identifier: str,
        user_metadata: dict | None = None,
    ):
        """
        Chat with the complaint agent.

        IMPORTANT:
        user_identifier must come from your authenticated application session:
          Student -> roll number
          Staff -> email
        The LLM is never trusted to select the actor identity.
        """
        if not user_identifier:
            return "Authentication required: provide the student's roll number or staff email."

        role = ROLE_NAMES.get(str(role).strip().lower(), str(role).strip())
        user_metadata = user_metadata or {}

        messages = [
            cached_system_message(SYSTEM_PROMPT),
            identity_message({
                "role": role,
                "name": user_metadata.get("name"),
                "identifier": user_identifier,
                "Time and Date": user_metadata.get("Time and Date"),
            }),
            {"role": "user", "content": user_input},
        ]

        max_rounds = 10
        for _ in range(max_rounds):
            response = chat_create(
                cache_key="complaint",
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
            )

            message = response.choices[0].message
            if not message.tool_calls:
                return message.content or ""

            messages.append(message)

            for tool_call in message.tool_calls:
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                    result = self.execute_tool(
                        tool_call.function.name,
                        arguments,
                        authenticated_identifier=user_identifier,
                    )
                except Exception as exc:
                    result = {"status": "error", "message": f"Tool execution failed: {exc}"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                })

        return "The complaint request could not be completed because the agent exceeded its tool-call limit."


if __name__ == "__main__":
    agent = ComplaintAgent()

    print(agent.chat(
        "Create a mess complaint about cold lunch at CV Raman hostel.",
        "Student",
        "3a63c6fe-18be-4110-8bfc-02f8538eaaab",
    ))

    print(agent.chat(
        "Show pending complaints.",
        "Admin",
        "3af87d28-f359-4494-9dbe-f6d765b40d8b",
    ))
