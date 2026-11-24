"""Storage interface shared by the local JSON store and Supabase.

Repos assign ids and timestamps on create (any id on the incoming model is ignored),
and return None / False when a record does not exist — the API turns that into a 404.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Protocol

from backend.app.models import ChatMessage, ComparisonRun, Quote, Requisition


class Repo(Protocol):
    # Requisitions (listed newest first)
    def list_requisitions(self) -> list[Requisition]: ...
    def get_requisition(self, req_id: str) -> Requisition | None: ...
    def create_requisition(self, requisition: Requisition) -> Requisition: ...
    def update_requisition(self, req_id: str, requisition: Requisition) -> Requisition | None: ...
    def delete_requisition(self, req_id: str) -> bool: ...  # cascades quotes, runs and chat

    # Quotes (listed by label)
    def list_quotes(self, req_id: str) -> list[Quote]: ...
    def get_quote(self, quote_id: str) -> Quote | None: ...
    def create_quote(self, quote: Quote) -> Quote: ...
    def update_quote(self, quote_id: str, quote: Quote) -> Quote | None: ...
    def delete_quote(self, quote_id: str) -> bool: ...

    # Saved comparison runs (listed newest first)
    def list_runs(self, req_id: str | None = None) -> list[ComparisonRun]: ...
    def get_run(self, run_id: str) -> ComparisonRun | None: ...
    def create_run(self, run: ComparisonRun) -> ComparisonRun: ...

    # Chat history (listed oldest first)
    def list_chat(self, req_id: str) -> list[ChatMessage]: ...
    def add_chat(self, message: ChatMessage) -> ChatMessage: ...


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def label_sort_key(quote: Quote) -> tuple[int, str]:
    """A, B, ..., Z, AA, AB — shorter labels first, then alphabetical."""
    return (len(quote.label), quote.label)
