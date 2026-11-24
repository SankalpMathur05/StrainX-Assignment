"""Runtime settings, read from the environment.

`.env.local` then `.env` (project root) are loaded first; real environment variables win
(override=False). Every key is optional: without Groq the AI routes say so, without
Supabase data goes to a local JSON file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from backend.app.models import DEFAULT_REFERENCE_DATE

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKIP_DOTENV_FLAG = "STRAINX_SKIP_DOTENV"  # set to 1 to ignore .env files (tests)


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None = None
    # Groq withdrew llama-3.3-70b-versatile and llama-3.1-8b-instant (NotFound on 24 Nov 2026),
    # so every task uses the two gpt-oss models, each falling back to the other.
    groq_extraction_model: str = "openai/gpt-oss-20b"
    groq_extraction_fallback_model: str = "openai/gpt-oss-120b"
    groq_insight_model: str = "openai/gpt-oss-120b"
    groq_insight_fallback_model: str = "openai/gpt-oss-20b"
    groq_chat_model: str = "openai/gpt-oss-120b"
    groq_chat_fallback_model: str = "openai/gpt-oss-20b"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    reference_date: date = DEFAULT_REFERENCE_DATE  # "today" for validity and delivery checks
    local_db_path: Path = PROJECT_ROOT / ".data" / "local_db.json"

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)


def _env(name: str) -> str | None:
    """Environment value, with blank treated as unset."""
    return os.getenv(name, "").strip() or None


def _env_or(name: str, default: str) -> str:
    return _env(name) or default


def load_settings() -> Settings:
    if not os.getenv(SKIP_DOTENV_FLAG):  # the test suite sets this so real keys are never read
        load_dotenv(PROJECT_ROOT / ".env.local", override=False)
        load_dotenv(PROJECT_ROOT / ".env", override=False)
    d = Settings()  # defaults
    reference_date = _env("REFERENCE_DATE")
    return Settings(
        groq_api_key=_env("GROQ_API_KEY"),
        groq_extraction_model=_env_or("GROQ_EXTRACTION_MODEL", d.groq_extraction_model),
        groq_extraction_fallback_model=_env_or("GROQ_EXTRACTION_FALLBACK_MODEL", d.groq_extraction_fallback_model),
        groq_insight_model=_env_or("GROQ_INSIGHT_MODEL", d.groq_insight_model),
        groq_insight_fallback_model=_env_or("GROQ_INSIGHT_FALLBACK_MODEL", d.groq_insight_fallback_model),
        groq_chat_model=_env_or("GROQ_CHAT_MODEL", d.groq_chat_model),
        groq_chat_fallback_model=_env_or("GROQ_CHAT_FALLBACK_MODEL", d.groq_chat_fallback_model),
        supabase_url=_env("SUPABASE_URL"),
        supabase_service_role_key=_env("SUPABASE_SERVICE_ROLE_KEY"),
        reference_date=date.fromisoformat(reference_date) if reference_date else d.reference_date,
        # Vercel's filesystem is read-only except /tmp (ephemeral, per instance).
        local_db_path=Path("/tmp/strainx_local_db.json") if os.getenv("VERCEL") else d.local_db_path,
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings; also the FastAPI dependency (tests override it)."""
    return load_settings()
