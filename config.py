import os
from dotenv import load_dotenv

load_dotenv()

# --- Database connection (non-secret defaults; secrets via environment) ---
DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "5432"))
DB_USER = os.getenv("PGUSER", "postgres")
# Never hardcode the password. Set PGPASSWORD in your environment / .env file.
DB_PASSWORD = os.getenv("PGPASSWORD", "")

AUTH_DB_NAME = os.getenv("AUTH_DB_NAME", "campus_agent")
MESS_DB_NAME = os.getenv("MESS_DB_NAME", "mess_menu")
ROOM_DB_NAME = os.getenv("ROOM_DB_NAME", "room_booking")
BUS_DB_NAME = os.getenv("BUS_DB_NAME", "bus_schedule")
COMPLAINTS_DB_NAME = os.getenv("COMPLAINTS_DB_NAME", "complaints")
ATTENDANCE_DB_NAME = os.getenv("ATTENDANCE_DB_NAME", "organization_agent")
NOTICE_DB_NAME = os.getenv("NOTICE_DB_NAME", "notice_board")
TIMETABLE_DB_NAME = os.getenv("TIMETABLE_DB_NAME", "timetable")

# --- LLM (secret via environment; the GUI can also supply LLM_API_KEY per request) ---
# Never hardcode the API key. Set LLM_API_KEY in your environment / .env file,
# or paste it in the campus console header.
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://awesome.kado.so/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "kado")
# Classification/dispatch tier. Unset → same model as LLM_MODEL, so existing
# deployments keep identical behavior until someone opts into a cheaper model.
LLM_FAST_MODEL = os.getenv("LLM_FAST_MODEL", LLM_MODEL)
