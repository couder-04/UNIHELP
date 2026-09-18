import json
import logging
import time

from llm import cached_system_message, chat_create, get_client, identity_message
from prompt_common import COMMON_AGENT_INSTRUCTIONS
from bus_function import call_tool, query_schedule
from fast_parse import format_bus_reply, parse_bus_query

logger = logging.getLogger(__name__)

class BusAgent:

    SYSTEM_PROMPT = COMMON_AGENT_INSTRUCTIONS + """

You are the IIT Patna Bus Agent.

Your job is to answer questions and perform authorized bus schedule operations
using the available tools.

READ OPERATIONS:
- Query schedules.
- Find active buses.
- Find drivers.
- Search departures within a time window.
- Find routes between locations.
- Find the next departure.
- Get database status.

WRITE OPERATIONS:
- Add a bus schedule.
- Remove a bus schedule.
- Change a bus schedule.

For write operations:
- Students are not authorized.
- Faculty are authorized.
- Admins are authorized.

The database functions independently enforce authorization.
Never claim that a write operation succeeded unless the tool reports success.

If a tool returns:
"Not authorised."
explain that the current role cannot perform that write.

Do not expose internal tool names, database details, SQL queries,
authentication mechanisms, or implementation details.

Use tools whenever the user's request requires bus schedule information
or a database operation.

Do not invent bus schedules, routes, drivers, times, or locations.

If required information is missing, ask a concise clarification.

Keep responses clear and useful. If a tool reports an error, explain it
in plain language.
"""

    def __init__(self):
        self.client = get_client()

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "query_schedule",
                    "description": "Query bus schedules for a bus route, optionally for a specific day or date.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "route_name": {
                                "type": "string",
                                "description": "Bus name or route name."
                            },
                            "day": {
                                "type": ["string", "null"],
                                "description": "Day of week such as Monday."
                            },
                            "date": {
                                "type": ["string", "null"],
                                "description": "Date in YYYY-MM-DD format."
                            }
                        },
                        "required": ["route_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_active_buses",
                    "description": "Find buses whose departure was within the last 45 minutes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "time_str": {
                                "type": ["string", "null"],
                                "description": "Reference time in HH:MM format."
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_driver",
                    "description": "Find the driver and contact number for a bus.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "bus_id": {
                                "type": "string",
                                "description": "Bus name or bus ID."
                            }
                        },
                        "required": ["bus_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_time_window",
                    "description": "Find all bus departures strictly between two times.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_time": {
                                "type": "string",
                                "description": "Start time in HH:MM."
                            },
                            "end_time": {
                                "type": "string",
                                "description": "End time in HH:MM."
                            },
                            "date": {
                                "type": ["string", "null"],
                                "description": "Date in YYYY-MM-DD format."
                            }
                        },
                        "required": ["start_time", "end_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_route_by_destination",
                    "description": "Find direct or one-transfer bus routes between two locations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "current_location": {
                                "type": "string",
                                "description": "Starting location."
                            },
                            "destination": {
                                "type": "string",
                                "description": "Destination."
                            },
                            "date": {
                                "type": ["string", "null"],
                                "description": "Date in YYYY-MM-DD format."
                            }
                        },
                        "required": ["current_location", "destination"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "next_departure",
                    "description": "Find the earliest bus departure from one location to another at or after a given time.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "current_location": {
                                "type": "string",
                                "description": "Starting location."
                            },
                            "destination": {
                                "type": "string",
                                "description": "Destination."
                            },
                            "at_time": {
                                "type": ["string", "null"],
                                "description": "Earliest acceptable departure time in HH:MM."
                            },
                            "date": {
                                "type": ["string", "null"],
                                "description": "Date in YYYY-MM-DD format."
                            }
                        },
                        "required": ["current_location", "destination"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_db_status",
                    "description": "Get basic information about the bus schedule database.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_schedule",
                    "description": "Add a new bus schedule.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "day": {
                                "type": "string"
                            },
                            "time_str": {
                                "type": "string",
                                "description": "Departure time in HH:MM."
                            },
                            "bus_name": {
                                "type": "string"
                            },
                            "start_point": {
                                "type": "string"
                            },
                            "destination": {
                                "type": "string"
                            },
                            "driver_name": {
                                "type": "string"
                            },
                            "driver_no": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "day",
                            "time_str",
                            "bus_name",
                            "start_point",
                            "destination",
                            "driver_name",
                            "driver_no"
                        ]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_schedule",
                    "description": "Remove a bus schedule.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "schedule_id": {
                                "type": "integer"
                            }
                        },
                        "required": ["schedule_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "change_schedule",
                    "description": "Change one or more fields of an existing bus schedule.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "schedule_id": {
                                "type": "integer"
                            },
                            "day": {
                                "type": ["string", "null"]
                            },
                            "time_str": {
                                "type": ["string", "null"]
                            },
                            "bus_name": {
                                "type": ["string", "null"]
                            },
                            "start_point": {
                                "type": ["string", "null"]
                            },
                            "destination": {
                                "type": ["string", "null"]
                            },
                            "driver_name": {
                                "type": ["string", "null"]
                            },
                            "driver_no": {
                                "type": ["string", "null"]
                            }
                        },
                        "required": ["schedule_id"]
                    }
                }
            }
        ]

    def chat(self, user_input: str, user_metadata: dict):

        role = str(user_metadata.get("role", "")).lower().strip()

        parsed = parse_bus_query(
            user_input, user_metadata.get("Time and Date")
        )
        if parsed is not None:
            logger.debug("fast_parse hit: %s -> %s", user_input, parsed)
            result = query_schedule(
                parsed["route_name"],
                day=parsed["day"],
                date=parsed["date"],
            )
            return format_bus_reply(parsed, result)

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

        # Bounded, like the other agents: an unbounded `while True` here
        # meant a model that kept re-issuing tool calls (e.g. retrying a
        # tool that keeps erroring) would loop and burn LLM calls forever.
        max_rounds = 10
        for _ in range(max_rounds):

            start = time.time()
            response = chat_create(
                cache_key="bus",
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                # observed LLM max 515; long schedule round 739 in metrics fixture
                max_tokens=800,
            )
            logger.debug("Bus LLM round took %.2fs", time.time() - start)
            message = response.choices[0].message

            if not message.tool_calls:
                return message.content

            messages.append(message)

            for tool_call in message.tool_calls:

                tool_name = tool_call.function.name

                try:
                    arguments = json.loads(
                        tool_call.function.arguments
                    )
                except json.JSONDecodeError:
                    arguments = {}

                if tool_name in {
                    "add_schedule",
                    "remove_schedule",
                    "change_schedule"
                }:
                    # Overwrite, never merge: `arguments` comes from the
                    # model, so a model that emitted its own "user" field
                    # would otherwise get to pick the role it writes as.
                    arguments["user"] = role

                try:
                    result = call_tool(
                        tool_name,
                        **arguments
                    )
                except Exception as exc:
                    # call_tool dispatches on a model-supplied name with
                    # model-supplied kwargs; a bad name or an unexpected
                    # kwarg raised TypeError straight out of chat() and
                    # crashed the whole request. Feed the error back to the
                    # model instead so it can correct itself.
                    result = json.dumps({
                        "status": "error",
                        "message": f"Tool execution failed: {exc}"
                    })

                if not isinstance(result, str):
                    result = json.dumps(result, default=str)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    }
                )

        return (
            "The bus request could not be completed because the agent "
            "exceeded its tool-call limit."
        )


# agent = BusAgent()

# print("\nTEST 1: QUERY BUS SCHEDULE")
# print("=" * 50)

# result = agent.chat(
#     "Show me the Monday schedule for Bus 02.",
#     user="student"
# )

# print(result)


# print("\nTEST 2: FIND NEXT BUS")
# print("=" * 50)

# result = agent.chat(
#     "What is the next bus from Aryabhatta to Tut Block after 9 AM?",
#     user="student"
# )

# print(result)


# print("\nTEST 3: FIND DRIVER")
# print("=" * 50)

# result = agent.chat(
#     "Who is the driver of Bus 02?",
#     user="student"
# )

# print(result)


# print("\nTEST 4: FIND ROUTE")
# print("=" * 50)

# result = agent.chat(
#     "Can I get from Aryabhatta to Tut Block by bus?",
#     user="student"
# )

# print(result)


# print("\nTEST 5: STUDENT TRIES TO ADD BUS")
# print("=" * 50)

# result = agent.chat(
#     "Add a new Bus 100 schedule on Monday at 18:00 from Kalam to Tut Block. The driver is Test Driver and his number is 9999999999.",
#     user="student"
# )

# print(result)


# print("\nTEST 6: FACULTY ADDS BUS")
# print("=" * 50)

# result = agent.chat(
#     "Add a new Bus 100 schedule on Monday at 18:00 from Kalam to Tut Block. The driver is Test Driver and his number is 9999999999.",
#     user="faculty"
# )

# print(result)


# print("\nTEST 7: FACULTY CHANGES BUS")
# print("=" * 50)

# result = agent.chat(
#     "Change schedule ID 525 so that its destination is Rajeev Nagar.",
#     user="faculty"
# )

# print(result)


# print("\nTEST 8: STUDENT TRIES TO CHANGE BUS")
# print("=" * 50)

# result = agent.chat(
#     "Change schedule ID 525 so that its destination is Patna.",
#     user="student"
# )

# print(result)


# print("\nTEST 9: ADMIN REMOVES BUS")
# print("=" * 50)

# result = agent.chat(
#     "Remove schedule ID 525.",
#     user="admin"
# )

# print(result)


# print("\nTEST 10: STUDENT TRIES TO REMOVE BUS")
# print("=" * 50)

# result = agent.chat(
#     "Remove schedule ID 526.",
#     user="student"
# )

# print(result)