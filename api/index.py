"""Vercel file-based Python entrypoint. Re-exports the FastAPI/Starlette app."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from main import app  # noqa: E402
