import asyncio
import json
import logging
import os
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

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route
import uvicorn

import db
import metrics
from authenticator import authenticate, list_users
from llm import effective_api_key, using_api_key
from planner import Planner
from executor import Executor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Stable production alias. Unique *.vercel.app deployment hosts are often
# SSO-gated, so personal agents must use this origin — not VERCEL_URL.
_PRODUCTION_PUBLIC_ORIGIN = "https://unihelp-coral.vercel.app"


def _public_base_url() -> str:
    explicit = (os.getenv("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    if os.getenv("VERCEL"):
        return _PRODUCTION_PUBLIC_ORIGIN
    vercel = (os.getenv("VERCEL_URL") or "").strip().rstrip("/")
    if vercel:
        if vercel.startswith("http://") or vercel.startswith("https://"):
            return vercel
        return f"https://{vercel}"
    return "http://127.0.0.1:8002"


def _connect_prompt_text() -> str:
    origin = _public_base_url()
    return (
        f"Connect to the A2A agent at {origin}/.well-known/agent-card.json\n"
        "\n"
        f"Send JSON-RPC requests to {origin}/a2a\n"
        "(use this /a2a URL even if the card lists a different host).\n"
        "\n"
        "Use this authentication_key for all requests to that agent: student-demo\n"
        "\n"
        "Put it in SendMessage request-level metadata as authentication_key.\n"
        "Never put the key in the message text.\n"
        "Remember this connection for the rest of this conversation.\n"
        "Do not ask a campus question yet — just confirm you are connected."
    )


def _is_connection_handshake(text: str) -> bool:
    """True when a personal agent is only checking connectivity, not a campus task."""
    t = (text or "").strip().lower()
    if not t:
        return False
    campus = (
        "mess", "menu", "dinner", "lunch", "breakfast", "bus", "complaint",
        "room", "book", "attendance", "notice", "timetable", "class",
        "hostel", "kalam", "sac", "guest house",
    )
    if any(word in t for word in campus):
        return False
    markers = (
        "confirm you are connected",
        "just confirm you are connected",
        "do not ask a campus",
        "do not look up campus",
        "remember this connection",
        "are you connected",
        "connection check",
    )
    if any(m in t for m in markers):
        return True
    return t in {"hi", "hello", "hey", "connect", "connected?", "ping", "status"}


def _handshake_reply(authentication_key: str) -> str:
    user = authenticate(authentication_key)
    if user is None:
        return "ERROR: KEY NOT FOUND"
    return (
        "Connected to IIT Patna Organization Management Agent. "
        f"Authenticated as {user['name']} ({user['role']}). "
        "Ready for campus requests. Keep using this authentication_key in "
        "request-level metadata for the rest of the conversation."
    )


def _request_auth_key(metadata: dict | None) -> str:
    data = metadata or {}
    return data.get("authentication_key") or data.get("authenticationKey") or ""


agent_card = AgentCard(
    name="IIT Patna Organization Management Agent",

    description=(
        "This is an A2A JSON-RPC agent that acts as the entry point "
        "to the IIT Patna Organization Management system. Other agents "
        "can invoke this agent by sending a SendMessage (A2A v1.0) or "
        "message/send (A2A v0.3) request to the endpoint specified in "
        "supportedInterfaces. The user's request must be provided as "
        "plain text inside message.parts[].text. "
        "Obtain authentication_key ONCE from the user at connection time, "
        "store it for the rest of the conversation, and attach it on "
        "EVERY subsequent request in params.metadata.authentication_key. "
        "Never put the credential in the message text. Never ask the user "
        "to repeat the key after the first connect turn. "
        "A first message that only confirms connectivity (no campus task) "
        "should be answered with a short connected confirmation. "
        "Later turns are normal campus questions sent to this same agent "
        "with the stored key."
    ),

    version="1.0.0",

    supported_interfaces=[
        AgentInterface(
            url=f"{_public_base_url()}/a2a",
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
                "1. Send an A2A JSON-RPC request to the endpoint in "
                "supportedInterfaces.\n"
                "2. Use method 'SendMessage' (v1.0) or 'message/send' (v0.3).\n"
                "3. Put the user's request in "
                "params.message.parts[].text.\n"
                "4. Put the caller's authentication credential in "
                "params.metadata.authentication_key on every call.\n"
                "5. After the user supplies the key once, reuse that same "
                "value for the rest of the conversation. Do not ask again.\n\n"

                "CONNECTION HANDSHAKE:\n"
                "If the user only asked you to connect and confirm, send a "
                "short connectivity check (no campus question). Wait for a "
                "connected confirmation, then handle later user messages as "
                "campus requests to this agent.\n\n"

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
                    "Connect once: store metadata.authentication_key for the "
                    "conversation, then SendMessage text='Confirm you are connected. "
                    "Do not ask a campus question yet.'"
                ),
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


def _run_authenticated_request(user_input, authentication_key, llm_api_key=""):
    """Authenticate, plan, and execute. Time/token flags are recorded here."""
    with using_api_key(llm_api_key):
        if not effective_api_key():
            return (
                "ERROR: LLM API key is required. Paste it in the header field.",
                None,
            )

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
        authentication_key = _request_auth_key(metadata)
        llm_api_key = metadata.get("llm_api_key") or metadata.get("llmApiKey") or ""

        # Never log the raw credential or the full metadata dict (which
        # contains it) — the original code printed both on every request.
        logger.info("Received request (%d chars)", len(user_input or ""))

        async with _request_semaphore:
            try:
                if _is_connection_handshake(user_input):
                    result = await asyncio.to_thread(
                        _handshake_reply,
                        authentication_key,
                    )
                else:
                    result, _rec = await asyncio.to_thread(
                        _run_authenticated_request,
                        user_input,
                        authentication_key,
                        llm_api_key,
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


async def _gui_ask(request):
    return FileResponse(_GUI_DIR / "ask.html")


async def _gui_activity(request):
    return FileResponse(_GUI_DIR / "activity.html")


async def _gui_commands(request):
    return FileResponse(_GUI_DIR / "commands.html")


async def _gui_users(request):
    return FileResponse(_GUI_DIR / "users.html")


async def _api_users(request):
    try:
        users = await asyncio.to_thread(list_users)
    except Exception:
        logger.exception("Failed to list users")
        return JSONResponse(
            {"error": "Could not load users from campus_agent"},
            status_code=500,
        )
    return JSONResponse({"users": users, "count": len(users)})


async def _api_metrics(request):
    return JSONResponse(metrics.snapshot())


async def _api_metrics_reset(request):
    metrics.reset()
    return JSONResponse({"ok": True})


async def _api_connect_prompt(request):
    origin = _public_base_url()
    return JSONResponse(
        {
            "prompt": _connect_prompt_text(),
            "agent_card": f"{origin}/.well-known/agent-card.json",
            "a2a": f"{origin}/a2a",
            "authentication_key": "student-demo",
        }
    )


async def _api_ask(request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    message = (body.get("message") or "").strip()
    authentication_key = body.get("authentication_key") or ""
    llm_api_key = body.get("llm_api_key") or ""
    if not message:
        return JSONResponse({"error": "message is required"}, status_code=400)

    async with _request_semaphore:
        try:
            if _is_connection_handshake(message):
                result = await asyncio.to_thread(
                    _handshake_reply,
                    authentication_key,
                )
                rec = None
            else:
                result, rec = await asyncio.to_thread(
                    _run_authenticated_request,
                    message,
                    authentication_key,
                    llm_api_key,
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
    Route("/connect", _gui_index),
    Route("/gui", _gui_index),
    Route("/ask", _gui_ask),
    Route("/gui/ask", _gui_ask),
    Route("/activity", _gui_activity),
    Route("/gui/activity", _gui_activity),
    Route("/commands", _gui_commands),
    Route("/gui/commands", _gui_commands),
    Route("/users", _gui_users),
    Route("/gui/users", _gui_users),
    Route("/api/users", _api_users),
    Route("/api/metrics", _api_metrics),
    Route("/api/metrics/reset", _api_metrics_reset, methods=["POST"]),
    Route("/api/connect-prompt", _api_connect_prompt),
    Route("/api/ask", _api_ask, methods=["POST"]),
]

routes.extend(
    create_agent_card_routes(agent_card)
)

routes.extend(
    create_jsonrpc_routes(
        request_handler,
        rpc_url="/a2a",
        enable_v0_3_compat=True,
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


app = FastAPI(routes=routes, lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8002,
    )
