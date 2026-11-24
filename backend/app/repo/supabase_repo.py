"""Supabase (Postgres) storage via supabase-py, server-side only.

Uses the service-role key, which bypasses row-level security; RLS is enabled with no
policies (supabase/schema.sql), so the public anon key can read nothing. Postgres
generates ids and timestamps; the updated_at trigger maintains updated_at.
"""

from __future__ import annotations

import uuid
from typing import Any, TypeVar

from pydantic import BaseModel
from supabase import Client, create_client  # the installed package, not the supabase/ SQL folder

from backend.app.models import ChatMessage, ComparisonRun, Quote, Requisition
from backend.app.repo.base import label_sort_key

M = TypeVar("M", bound=BaseModel)

SERVER_MANAGED = {"id", "created_at", "updated_at"}


def _is_uuid(value: str) -> bool:
    """Postgres rejects malformed uuids with an error; treat them as 'not found' instead."""
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _payload(model: BaseModel) -> dict[str, Any]:
    """JSON-safe column values (dates -> ISO strings, enums -> their values)."""
    return model.model_dump(mode="json", exclude=SERVER_MANAGED)


class SupabaseRepo:
    def __init__(self, url: str, service_role_key: str) -> None:
        self.client: Client = create_client(url, service_role_key)

    # -- generic helpers ------------------------------------------------------
    def _get(self, table: str, record_id: str, cls: type[M]) -> M | None:
        if not _is_uuid(record_id):
            return None
        rows = self.client.table(table).select("*").eq("id", record_id).limit(1).execute().data
        return cls.model_validate(rows[0]) if rows else None

    def _insert(self, table: str, model: M) -> M:
        rows = self.client.table(table).insert(_payload(model)).execute().data
        return type(model).model_validate(rows[0])

    def _update(self, table: str, record_id: str, model: M) -> M | None:
        if not _is_uuid(record_id):
            return None
        rows = self.client.table(table).update(_payload(model)).eq("id", record_id).execute().data
        return type(model).model_validate(rows[0]) if rows else None

    def _delete(self, table: str, record_id: str) -> bool:
        if not _is_uuid(record_id):
            return False
        rows = self.client.table(table).delete().eq("id", record_id).execute().data
        return bool(rows)

    # -- requisitions ---------------------------------------------------------
    def list_requisitions(self) -> list[Requisition]:
        rows = self.client.table("requisitions").select("*").order("created_at", desc=True).execute().data
        return [Requisition.model_validate(r) for r in rows]

    def get_requisition(self, req_id: str) -> Requisition | None:
        return self._get("requisitions", req_id, Requisition)

    def create_requisition(self, requisition: Requisition) -> Requisition:
        return self._insert("requisitions", requisition)

    def update_requisition(self, req_id: str, requisition: Requisition) -> Requisition | None:
        return self._update("requisitions", req_id, requisition)

    def delete_requisition(self, req_id: str) -> bool:
        return self._delete("requisitions", req_id)  # FKs cascade to quotes, runs and chat

    # -- quotes ---------------------------------------------------------------
    def list_quotes(self, req_id: str) -> list[Quote]:
        if not _is_uuid(req_id):
            return []
        rows = self.client.table("quotes").select("*").eq("requisition_id", req_id).execute().data
        return sorted((Quote.model_validate(r) for r in rows), key=label_sort_key)

    def get_quote(self, quote_id: str) -> Quote | None:
        return self._get("quotes", quote_id, Quote)

    def create_quote(self, quote: Quote) -> Quote:
        return self._insert("quotes", quote)

    def update_quote(self, quote_id: str, quote: Quote) -> Quote | None:
        return self._update("quotes", quote_id, quote)

    def delete_quote(self, quote_id: str) -> bool:
        return self._delete("quotes", quote_id)

    # -- comparison runs ------------------------------------------------------
    def list_runs(self, req_id: str | None = None) -> list[ComparisonRun]:
        query = self.client.table("comparison_runs").select("*")
        if req_id is not None:
            if not _is_uuid(req_id):
                return []
            query = query.eq("requisition_id", req_id)
        rows = query.order("created_at", desc=True).execute().data
        return [ComparisonRun.model_validate(r) for r in rows]

    def get_run(self, run_id: str) -> ComparisonRun | None:
        return self._get("comparison_runs", run_id, ComparisonRun)

    def create_run(self, run: ComparisonRun) -> ComparisonRun:
        return self._insert("comparison_runs", run)

    # -- chat -----------------------------------------------------------------
    def list_chat(self, req_id: str) -> list[ChatMessage]:
        if not _is_uuid(req_id):
            return []
        rows = (
            self.client.table("chat_messages").select("*").eq("requisition_id", req_id)
            .order("created_at").execute().data
        )
        return [ChatMessage.model_validate(r) for r in rows]

    def add_chat(self, message: ChatMessage) -> ChatMessage:
        return self._insert("chat_messages", message)
