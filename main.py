import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from a2a.server.agent_execution import AgentExecutor
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentInterface,
    AgentSkill,
    Message,
    Part,
    Role,
)
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route
import uvicorn

import db
import metrics
from authenticator import authenticate
from planner import Planner
from executor import Executor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_card = AgentCard(
    name="IIT Patna Organization Management Agent",

    description=(
        "This is an A2A v1.0 JSON-RPC agent that acts as the entry point "
        "to the IIT Patna Organization Management system. Other agents "
        "can invoke this agent by sending a SendMessage request to the "
        "endpoint specified in supportedInterfaces. The user's request "
        "must be provided as plain text inside message.parts[].text. "
        "The caller's authentication credential MUST be provided "
        "separately in the SendMessage request-level metadata using "
        "the key 'authentication_key'. The credential MUST NOT be "
        "included in the message text. The agent authenticates the "
        "caller and passes the authorized request to the organization's "
        "planning system, which determines the specialized services "
        "and tasks required to fulfill the request."
    ),

    version="1.0.0",

    supported_interfaces=[
        AgentInterface(
            url="http://127.0.0.1:8002/a2a",
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        )
    ],

    capabilities=AgentCapabilities(
        streaming=False,
        push_notifications=False,
    ),

    default_input_modes=[
        "text/plain",
    ],

    default_output_modes=[
        "text/plain",
    ],

    skills=[
        AgentSkill(
            id="organization_request_planning",

            name="Organization Request Planning",

            description=(
                "Use this skill to submit organization-related requests "
                "to the IIT Patna Organization Management system.\n\n"

                "CURRENTLY SUPPORTED SERVICES:\n"
                "1. Mess services:\n"
                "   - Daily and weekly mess menus\n"
                "   - Meal timings\n"
                "   - Authorized mess menu modifications\n\n"
                "2. Bus services:\n"
                "   - Bus schedules\n"
                "   - Bus routes and destinations\n"
                "   - Driver information\n"
                "   - Next departures\n"
                "   - Bus availability\n"
                "   - Authorized bus schedule modifications\n\n"
                "3. Complaint services:\n"
                "   - Create, view, and list complaints tagged academic, hostel, or mess\n"
                "   - Admin/faculty verify, then mark PROGRESS, then COMPLETED\n"
                "   - Duplicate open complaints are not logged again\n\n"
                "4. Room booking services:\n"
                "   - SAC Hall, Guest House, CLH, and Auditorium\n"
                "   - Availability, direct bookings, and booking requests\n"
                "   - Cancel or modify bookings and requests\n"
                "   - Admin approve/reject of pending requests\n\n"
                "5. Attendance services:\n"
                "   - Attendance records, percentages, skip budget, and charts\n"
                "   - Weekly, monthly, semester, and today's attendance\n"
                "   - Faculty/admin marking, editing, and deleting attendance\n"
                "   - Courses, rosters, enrollments, and at-risk students\n"
                "   - Admin management of people, courses, and enrollments\n\n"
                "6. Notice board services:\n"
                "   - View campus notices\n"
                "   - Faculty/admin publish notices\n"
                "   - Faculty/admin archive expired notices\n\n"
                "7. Timetable services:\n"
                "   - Personal and weekly class timetables\n"
                "   - Next class, classes on a given day, and free slots\n"
                "   - Course lookup and lecture/lab rooms\n"
                "   - Faculty/admin add, update, or delete class slots\n\n"

                "INVOCATION:\n"
                "1. Send an A2A v1.0 JSON-RPC request.\n"
                "2. Use the method 'SendMessage'.\n"
                "3. Send the request to the endpoint advertised in "
                "supportedInterfaces.\n"
                "4. Put the user's request in "
                "params.message.parts[].text.\n"
                "5. Put the caller's authentication credential in "
                "params.metadata.authentication_key.\n\n"

                "IMPORTANT:\n"
                "The authentication_key belongs to the request-level "
                "metadata. It does NOT belong inside message.parts, "
                "message text, or message metadata.\n\n"

                "REQUEST STRUCTURE:\n"
                "params.message.parts[0].text = user's request\n"
                "params.metadata.authentication_key = caller credential\n\n"

                "PROCESSING:\n"
                "The agent first authenticates the supplied credential "
                "and identifies the caller. The request is then passed "
                "to the planning system, which determines which "
                "specialized services are required and constructs the "
                "tasks needed to fulfill the request.\n\n"

                "The planning system does not perform the requested "
                "operations itself. Execution, authorization, and "
                "interaction with the specialized agents are handled by "
                "subsequent components of the system.\n\n"

                "Do not place the authentication credential in the "
                "natural-language task. Do not invent or modify the "
                "authentication credential."
            ),

            tags=[
                "a2a",
                "jsonrpc",
                "organization",
                "campus",
                "mess",
                "bus",
                "complaint",
                "room booking",
                "attendance",
                "notice",
                "timetable",
                "planning",
                "authentication",
                "authorization",
            ],

            examples=[
                (
                    "SendMessage example: "
                    "message.parts[0].text='What is today's dinner at Kalam hostel?'; "
                    "metadata.authentication_key='<caller credential>'"
                ),
                (
                    "SendMessage example: "
                    "message.parts[0].text='Show me the Bus 02 schedule'; "
                    "metadata.authentication_key='<caller credential>'"
                ),
                (
                    "SendMessage example: "
                    "message.parts[0].text='Book SAC Hall on 2030-02-10 from 10 to 11 for a club meeting'; "
                    "metadata.authentication_key='<caller credential>'"
                ),
                (
                    "SendMessage example: "
                    "message.parts[0].text='What is my attendance percentage in CS101?'; "
                    "metadata.authentication_key='<caller credential>'"
                ),
                (
                    "SendMessage example: "
                    "message.parts[0].text='Show me the current notices'; "
                    "metadata.authentication_key='<caller credential>'"
                ),
                (
                    "SendMessage example: "
                    "message.parts[0].text='What is my class timetable today?'; "
                    "metadata.authentication_key='<caller credential>'"
                ),
                (
                    "Submit a mess, bus, complaint, room booking, attendance, notice, or timetable request "
                    "using the caller's authentication_key in request-level "
                    "metadata."
                ),
            ],
        )
    ],
)


# PERFORMANCE FIX: Planner/Executor (and, via Executor.__init__, all seven
# sub-agents plus their OpenAI clients and tool-schema lists) used to be
# constructed fresh inside every single request. None of them hold
# per-request mutable state — user identity is passed in per call — so they
# are built once here at import time and reused. This removes six agent
# constructions and extra OpenAI client setups from every request.
_planner = Planner()
_executor = Executor()


# CONCURRENCY FIX: the handler below is `async def`, but authenticate(),
# planner.create_plan() and executor.execute() are all *synchronous*
# blocking network I/O (psycopg + the sync OpenAI client), and each request
# chains several seconds' worth of them. Running that directly on the event
# loop meant one user's request blocked every other user's request for its
# full duration — the server was effectively single-user despite being
# async. asyncio.to_thread() moves each blocking call onto a worker thread
# so the loop stays free.
#
# The semaphore bounds how many requests can be in flight at once, so a
# burst of traffic can't spawn unbounded threads or exhaust the DB pool
# (keep MAX_CONCURRENT_REQUESTS <= DB_POOL_MAX_SIZE in db.py).
MAX_CONCURRENT_REQUESTS = 8
_request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
_GUI_DIR = Path(__file__).resolve().parent / "gui"


def _run_authenticated_request(user_input, authentication_key):
    """Authenticate, plan, and execute. Time/token flags are recorded here."""
    user = authenticate(authentication_key)

    if user is None:
        return "ERROR: KEY NOT FOUND", None

    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    user_metadata = {
        "role": user["role"],
        "name": user["name"],
        "roll_number": user["roll_number"],
        "Time and Date": now_ist.strftime(
            "%A, %Y-%m-%d %H:%M:%S IST"
        ),
    }
    logger.info(
        "Request state role=%s name=%s roll=%s time=%s",
        user_metadata["role"],
        user_metadata["name"],
        user_metadata["roll_number"],
        user_metadata["Time and Date"],
    )

    with metrics.request_scope(
        user_name=user["name"],
        user_role=user["role"],
        roll_number=user["roll_number"],
        query=user_input,
    ) as rec:
        started = time.time()

        with metrics.task_timer("planner"):
            plan = _planner.create_plan(user_input)
        logger.info("Planner took %.2fs", time.time() - started)

        result = _executor.execute(user_input, plan, user_metadata)
        logger.info("Total took %.2fs", time.time() - started)
        return result, rec


class OrganizationAgent(AgentExecutor):

    async def execute(self, context, event_queue):

        user_input = context.get_user_input()
        metadata = context.metadata or {}
        authentication_key = metadata.get("authentication_key")

        # Never log the raw credential or the full metadata dict (which
        # contains it) — the original code printed both on every request.
        logger.info("Received request (%d chars)", len(user_input or ""))

        async with _request_semaphore:
            try:
                result, _rec = await asyncio.to_thread(
                    _run_authenticated_request,
                    user_input,
                    authentication_key,
                )

            except Exception:
                # Previously any exception (e.g. the planner's json.loads
                # failing on a non-JSON model reply) escaped this handler and
                # produced an opaque framework-level 500 with a stack trace.
                # Log it server-side, return something the caller can act on.
                logger.exception("Request failed")
                result = (
                    "ERROR: The request could not be completed due to an "
                    "internal error. Please try again."
                )

        response = Message(
            role=Role.ROLE_AGENT,
            message_id="response-1",
            parts=[
                Part(text=json.dumps(result, indent=2))
            ],
        )

        await event_queue.enqueue_event(response)

    async def cancel(self, context, event_queue: EventQueue) -> None:
        pass


task_store = InMemoryTaskStore()

request_handler = DefaultRequestHandler(
    agent_executor=OrganizationAgent(),
    task_store=task_store,
    agent_card=agent_card,
)

async def _gui_index(request):
    return FileResponse(_GUI_DIR / "index.html")


async def _api_metrics(request):
    return JSONResponse(metrics.snapshot())


async def _api_metrics_reset(request):
    metrics.reset()
    return JSONResponse({"ok": True})


async def _api_ask(request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    message = (body.get("message") or "").strip()
    authentication_key = body.get("authentication_key") or ""
    if not message:
        return JSONResponse({"error": "message is required"}, status_code=400)

    async with _request_semaphore:
        try:
            result, rec = await asyncio.to_thread(
                _run_authenticated_request,
                message,
                authentication_key,
            )
        except Exception:
            logger.exception("GUI request failed")
            return JSONResponse(
                {
                    "error": (
                        "The request could not be completed due to an "
                        "internal error. Please try again."
                    )
                },
                status_code=500,
            )

    return JSONResponse({"result": result, "request": rec})


routes = [
    Route("/", _gui_index),
    Route("/gui", _gui_index),
    Route("/api/metrics", _api_metrics),
    Route("/api/metrics/reset", _api_metrics_reset, methods=["POST"]),
    Route("/api/ask", _api_ask, methods=["POST"]),
]

routes.extend(
    create_agent_card_routes(agent_card)
)

routes.extend(
    create_jsonrpc_routes(
        request_handler,
        rpc_url="/a2a",
    )
)


@asynccontextmanager
async def _lifespan(app):
    """Close pooled DB connections cleanly on shutdown.

    Starlette 1.x dropped the on_startup/on_shutdown kwargs in favor of a
    single lifespan context manager.
    """
    yield
    await asyncio.to_thread(db.close_all_pools)


app = Starlette(routes=routes, lifespan=_lifespan)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8002,
    )
