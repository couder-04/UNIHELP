import json
import logging

from llm import cached_system_message, chat_create, get_client, identity_message
from prompt_common import COMMON_AGENT_INSTRUCTIONS
from fast_parse import format_mess_reply, parse_mess_query

from mess_functions_1 import (
    get_menu,
    get_weekly_menu,
    get_meal_timing,
    modify_menu
)

logger = logging.getLogger(__name__)


class MessAgent:

    SYSTEM_PROMPT = COMMON_AGENT_INSTRUCTIONS + """

You are the Mess Agent for IIT Patna campus.

You handle:
- Daily mess menus
- Weekly mess menus
- Meal timings
- Menu modifications

AUTHORITY RULES:

Student:
- Can read daily menus.
- Can read weekly menus.
- Can ask for meal timings.
- CANNOT modify menus.

Faculty:
- Can read daily menus.
- Can read weekly menus.
- Can ask for meal timings.
- Can make TEMPORARY menu modifications.
- CANNOT make PERMANENT menu modifications.

Admin:
- Can read daily menus.
- Can read weekly menus.
- Can ask for meal timings.
- Can make TEMPORARY menu modifications.
- Can make PERMANENT menu modifications.

Before calling modify_menu, check the authority rules.

If the user is a Student and requests ANY menu modification,
politely say they can view menus but cannot change them.

If the user is Faculty and requests a PERMANENT menu modification,
politely say only admin can make permanent changes; offer a temporary change if that fits.

If the user is Faculty and requests a TEMPORARY modification,
call modify_menu with change_type="temporary".

If the user is Admin and requests a TEMPORARY modification,
call modify_menu with change_type="temporary".

If the user is Admin and requests a PERMANENT modification,
call modify_menu with change_type="permanent".

VOCABULARY:

Users rarely say the word "menu". Treat all of the following as valid
requests for mess information and serve them with the normal tools —
never reply that you only handle menus, and never ask the user to
rephrase:

- menu, mess menu, food, meal, mess
- mess schedule, food schedule, meal schedule, mess timetable,
  food timetable, mess chart, mess plan, mess routine, diet chart
- "what's cooking", "what's being served", "what's there for dinner",
  "what do we get", "khana", "what's in the mess"

MENU RULES:

- Use get_menu when the user asks what food is served for a specific
  day/date and hostel — however they phrase it.
- Use get_weekly_menu when the user asks about a week, full week,
  entire week, "all days", or a weekly/full mess schedule, chart,
  timetable, plan, or routine.
- Use get_meal_timing ONLY when the user is asking about CLOCK TIMES —
  when a meal starts or ends, how late the mess is open, "what time is
  dinner", "mess timings".
- Do NOT add meal timings to menu answers unless explicitly requested.

RESOLVING "SCHEDULE":

The word "schedule" (and "timetable", "chart", "plan") is ambiguous: it
can mean the food served across the week, or the clock times meals are
served. Resolve it from context:

- Paired with a week or multiple days → get_weekly_menu.
  "Show me the mess schedule for Kalam" → weekly menu.
- Paired with time words (time, timing, when, how late, open, close,
  starts, ends) → get_meal_timing.
  "What's the mess schedule for dinner tonight?" → dinner timing.
- Paired with a single day/date and no time words → get_menu.
  "What's tomorrow's mess schedule at Kalam?" → tomorrow's menu.
- Genuinely unclear with no other signal → ask exactly one short
  question: "Do you mean the food served, or the meal timings?"
  Do not guess, and do not call both tools.

MISSING INFORMATION:

If the user has not provided enough information, ask ONLY for the missing information.

Examples:

"What is Monday's dinner?"
→ "Which hostel?"

"Change Monday dinner to Paneer."
→ "Which hostel?"

"What is today's menu?"
→ "Which hostel?"

"Show me the mess schedule."
→ "Which hostel?"

Ask only about what is actually missing — never ask the user to
rephrase a request just because they didn't use the word "menu".

Do not ask for information that the user has already provided.

FORMATTING:

- Output menus as clean markdown tables.
- Keep responses concise and factual.
- No emojis.
- No opinions.
- No recommendations.
- No greetings.
- No unnecessary information.
- Do not provide meal timings unless explicitly requested.
"""

    def __init__(self):
        self.client = get_client()

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_menu",
                    "description": "Get the menu for a specific hostel and date (today/tomorrow/YYYY-MM-DD).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hostel": {
                                "type": "string",
                                "description": "Hostel name such as CV Raman, Kalam, Aryabhatta, or Asima"
                            },
                            "menu_date": {
                                "type": "string",
                                "description": "Date: 'today', 'tomorrow', or 'YYYY-MM-DD'"
                            }
                        },
                        "required": ["hostel", "menu_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_weekly_menu",
                    "description": "Get the complete weekly menu for a hostel starting from a date.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hostel": {
                                "type": "string",
                                "description": "Hostel name"
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Start date: 'today', 'tomorrow', or 'YYYY-MM-DD'."
                            }
                        },
                        "required": ["hostel"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_meal_timing",
                    "description": "Get the timing for a specific meal.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "meal": {
                                "type": "string",
                                "enum": [
                                    "breakfast",
                                    "lunch",
                                    "snacks",
                                    "dinner"
                                ]
                            }
                        },
                        "required": ["meal"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "modify_menu",
                    "description": "Modify a hostel menu temporarily or permanently. Faculty can make temporary changes. Only Admin can make permanent changes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hostel": {
                                "type": "string",
                                "description": "Hostel name"
                            },
                            "menu_date": {
                                "type": "string",
                                "description": "Date: 'today', 'tomorrow', or 'YYYY-MM-DD'"
                            },
                            "meal": {
                                "type": "string",
                                "enum": [
                                    "breakfast",
                                    "lunch",
                                    "snacks",
                                    "dinner"
                                ]
                            },
                            "new_items": {
                                "type": "string",
                                "description": "New menu items"
                            },
                            "change_type": {
                                "type": "string",
                                "enum": [
                                    "temporary",
                                    "permanent"
                                ]
                            }
                        },
                        "required": [
                            "hostel",
                            "menu_date",
                            "meal",
                            "new_items",
                            "change_type"
                        ]
                    }
                }
            }
        ]

    def execute_tool(self, name: str, arguments: dict, role: str):

        if name == "get_menu":
            return get_menu(
                arguments["hostel"],
                arguments["menu_date"]
            )

        elif name == "get_weekly_menu":
            return get_weekly_menu(
                arguments["hostel"],
                arguments.get("start_date")
            )

        elif name == "get_meal_timing":
            return get_meal_timing(
                arguments["meal"]
            )

        elif name == "modify_menu":

            return modify_menu(
                arguments["hostel"],
                arguments["menu_date"],
                arguments["meal"],
                arguments["new_items"],
                arguments["change_type"],
                role
            )

        return {
            "status": "error",
            "message": f"Unknown tool: {name}"
        }

    def chat(self, user_input: str, user_metadata: dict):

        role = user_metadata["role"].lower().strip()

        parsed = parse_mess_query(
            user_input, user_metadata.get("Time and Date")
        )
        if parsed is not None:
            logger.debug("fast_parse hit: %s -> %s", user_input, parsed)
            if parsed.get("weekly"):
                result = get_weekly_menu(parsed["hostel"], parsed["date"])
            else:
                result = get_menu(parsed["hostel"], parsed["date"])
            return format_mess_reply(parsed, result)

        messages = [
            cached_system_message(self.SYSTEM_PROMPT),
            identity_message({
                "role": role,
                "name": user_metadata.get("name"),
                "roll_number": user_metadata.get("roll_number"),
                "Time and Date": user_metadata.get("Time and Date"),
            }),
            {
                "role": "user",
                "content": user_input
            }
        ]

        # Bounded rather than `while True`: a model that keeps re-issuing
        # tool calls would otherwise loop and burn LLM calls forever.
        max_rounds = 10
        for _ in range(max_rounds):

            response = chat_create(
                cache_key="mess",
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                # observed LLM max 104; weekly mess table ~230 tokens
                max_tokens=500,
            )

            message = response.choices[0].message

            if not message.tool_calls:
                return message.content

            messages.append(message)

            for tool_call in message.tool_calls:

                name = tool_call.function.name

                try:
                    arguments = json.loads(
                        tool_call.function.arguments or "{}"
                    )
                    result = self.execute_tool(
                        name,
                        arguments,
                        role
                    )
                except Exception as exc:
                    # execute_tool indexes arguments the model supplied
                    # (e.g. arguments["hostel"]); a missing key raised
                    # KeyError straight out of chat() and crashed the
                    # request. Return the error to the model instead so it
                    # can ask the user for what's missing.
                    result = {
                        "status": "error",
                        "message": f"Tool execution failed: {exc}"
                    }

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str)
                })

            # CRITICAL FIX: this used to fall through into a second,
            # near-identical block that rebuilt `messages` from scratch
            # ([system, user] only), discarding the tool call and tool
            # result just appended above. The model never saw its own tool
            # results, so it would frequently re-issue the same tool call —
            # for modify_menu specifically, that risked applying the same
            # menu edit twice. The loop above already does the right thing
            # on its own: loop back to the top with the accumulated
            # `messages` (including the tool result), call the model again,
            # and return as soon as it stops requesting tools.

        return (
            "The mess request could not be completed because the agent "
            "exceeded its tool-call limit."
        )


# if __name__ == "__main__":

    # agent = MessAgent()

    # print("=== TEST 1: Student reads today's menu ===")
    # print(
    #     agent.chat(
    #         "What is today's menu for c v raman?",
    #         "student"
    #     )
    # )

    # print("\n=== TEST 2: Faculty asks meal timing ===")
    # print(
    #     agent.chat(
    #         "What are the timings for dinner?",
    #         "faculty"
    #     )
    # )

    # print("\n=== TEST 3: Student weekly menu ===")
    # print(
    #     agent.chat(
    #         "Show me the weekly menu for kalam",
    #         "student"
    #     )
    # )

    # print("\n=== TEST 4: Faculty temporary modification ===")
    # print(
    #     agent.chat(
    #         "Temporarily change c v raman today dinner to Roti, Dal, Paneer Tikka",
    #         "faculty"
    #     )
    # )

    # print("\n=== TEST 5: Verify temporary change ===")
    # print(
    #     agent.chat(
    #         "What is today's menu for c v raman?",
    #         "student"
    #     )
    # )

    # print("\n=== TEST 6: Faculty tries permanent modification ===")
    # print(
    #     agent.chat(
    #         "Permanently change c v raman today dinner to Roti, Dal, Paneer Tikka",
    #         "faculty"
    #     )
    # )

    # print("\n=== TEST 7: Admin permanent modification ===")
    # print(
    #     agent.chat(
    #         "Permanently change c v raman today dinner to Roti, Dal, Paneer Curry",
    #         "admin"
    #     )
    # )

    # print("\n=== TEST 8: Verify admin permanent change ===")
    # print(
    #     agent.chat(
    #         "What is today's menu for c v raman?",
    #         "student"
    #     )
    # )

    # print("\n=== TEST 9: Missing hostel ===")
    # print(
    #     agent.chat(
    #         "What is Monday's dinner?",
    #         "student"
    #     )
    # )

    # print("\n=== TEST 10: Invalid meal timing ===")
    # print(
    #     agent.chat(
    #         "When is brunch?",
    #         "student"
    #     )
    # )

    # print("\n=== TEST 11: Student tries modification ===")
    # print(
    #     agent.chat(
    #         "Change today lunch to Biryani",
    #         "student"
    #     )
    # )