"""Vercel Python entry point: exposes the FastAPI app as `app`.

vercel.json rewrites /api/py/* here; the request keeps its original path, which the
app's /api/py routes match.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))  # so `backend` is importable

from backend.app.main import app  # noqa: E402

__all__ = ["app"]
