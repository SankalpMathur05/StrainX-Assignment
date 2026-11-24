"""Persistence: Supabase when configured, otherwise a local JSON file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from backend.app.config import Settings, get_settings
from backend.app.repo.base import Repo
from backend.app.repo.local_json import LocalJsonRepo
from backend.app.repo.supabase_repo import SupabaseRepo

__all__ = ["LocalJsonRepo", "Repo", "SupabaseRepo", "get_repo"]


@lru_cache
def _repo_for(supabase_url: str | None, supabase_key: str | None, local_db_path: Path) -> Repo:
    """One shared repo per configuration (the JSON store's lock must be shared across requests)."""
    if supabase_url and supabase_key:
        return SupabaseRepo(supabase_url, supabase_key)
    return LocalJsonRepo(local_db_path)


def get_repo(settings: Annotated[Settings, Depends(get_settings)]) -> Repo:
    """FastAPI dependency (tests override it with a LocalJsonRepo on tmp_path)."""
    return _repo_for(settings.supabase_url, settings.supabase_service_role_key, settings.local_db_path)
