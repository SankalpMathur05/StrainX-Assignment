"""Local JSON-file storage — used when Supabase is not configured.

One small JSON document holds every table as {table: {id: record}}. A lock serialises
access between request threads, and every write goes to a temp file that atomically
replaces the original, so a crash never leaves half-written JSON. A missing file is
created and seeded with PR-USP-1147 + Quotes A-D (fixed seed ids).
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from backend.app.models import ChatMessage, ComparisonRun, Quote, Requisition
from backend.app.repo.base import label_sort_key, new_id, utc_now
from backend.app.seed import seed_quotes, seed_requisition

M = TypeVar("M", bound=BaseModel)
# table -> id -> record (JSON-safe dict). Dicts keep insertion order (also through JSON), and updates
# keep a record's position, so each table is always in creation order: no timestamp sorting needed.
Data = dict[str, dict[str, dict[str, Any]]]


def _stamped(model: M, record_id: str, created_at: Any) -> M:
    """Copy of `model` with id and timestamps set, re-validated so every field has its proper type."""
    values = {**model.model_dump(), "id": record_id, "created_at": created_at, "updated_at": utc_now()}
    return type(model).model_validate(values)  # extra keys (updated_at on runs/chat) are ignored


def _seed_data() -> Data:
    now = utc_now()
    requisition = seed_requisition().model_copy(update={"created_at": now, "updated_at": now})
    quotes = [q.model_copy(update={"created_at": now, "updated_at": now}) for q in seed_quotes()]
    return {
        "requisitions": {str(requisition.id): requisition.model_dump(mode="json")},
        "quotes": {str(q.id): q.model_dump(mode="json") for q in quotes},
        "runs": {},
        "chat": {},
    }


class LocalJsonRepo:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()

    # -- file I/O -----------------------------------------------------------
    def _load(self) -> Data:
        if not self.path.exists():
            data = _seed_data()
            self._save(data)
            return data
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: Data) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        for attempt in range(5):  # Windows (e.g. OneDrive sync) can lock the target for a moment
            try:
                os.replace(tmp, self.path)
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05)

    # -- generic table operations ------------------------------------------
    def _all(self, table: str, cls: type[M]) -> list[M]:
        with self._lock:
            records = list(self._load()[table].values())
        return [cls.model_validate(r) for r in records]

    def _get(self, table: str, record_id: str, cls: type[M]) -> M | None:
        with self._lock:
            record = self._load()[table].get(record_id)
        return cls.model_validate(record) if record else None

    def _create(self, table: str, model: M) -> M:
        record_id = new_id()
        with self._lock:
            data = self._load()  # load first: a missing file is seeded before we stamp, so seed rows stay oldest
            record = _stamped(model, record_id, created_at=utc_now())
            data[table][record_id] = record.model_dump(mode="json")
            self._save(data)
        return record

    def _update(self, table: str, record_id: str, model: M) -> M | None:
        with self._lock:
            data = self._load()
            existing = data[table].get(record_id)
            if existing is None:
                return None
            record = _stamped(model, record_id, created_at=existing["created_at"])
            data[table][record_id] = record.model_dump(mode="json")
            self._save(data)
        return record

    def _delete(self, table: str, record_id: str) -> bool:
        with self._lock:
            data = self._load()
            if data[table].pop(record_id, None) is None:
                return False
            self._save(data)
            return True

    # -- requisitions --------------------------------------------------------
    def list_requisitions(self) -> list[Requisition]:
        return self._all("requisitions", Requisition)[::-1]  # newest first

    def get_requisition(self, req_id: str) -> Requisition | None:
        return self._get("requisitions", req_id, Requisition)

    def create_requisition(self, requisition: Requisition) -> Requisition:
        return self._create("requisitions", requisition)

    def update_requisition(self, req_id: str, requisition: Requisition) -> Requisition | None:
        return self._update("requisitions", req_id, requisition)

    def delete_requisition(self, req_id: str) -> bool:
        with self._lock:
            data = self._load()
            if data["requisitions"].pop(req_id, None) is None:
                return False
            for table in ("quotes", "runs", "chat"):  # cascade, like ON DELETE CASCADE in Postgres
                data[table] = {k: r for k, r in data[table].items() if r.get("requisition_id") != req_id}
            self._save(data)
            return True

    # -- quotes --------------------------------------------------------------
    def list_quotes(self, req_id: str) -> list[Quote]:
        quotes = [q for q in self._all("quotes", Quote) if q.requisition_id == req_id]
        return sorted(quotes, key=label_sort_key)

    def get_quote(self, quote_id: str) -> Quote | None:
        return self._get("quotes", quote_id, Quote)

    def create_quote(self, quote: Quote) -> Quote:
        return self._create("quotes", quote)

    def update_quote(self, quote_id: str, quote: Quote) -> Quote | None:
        return self._update("quotes", quote_id, quote)

    def delete_quote(self, quote_id: str) -> bool:
        return self._delete("quotes", quote_id)

    # -- comparison runs ----------------------------------------------------
    def list_runs(self, req_id: str | None = None) -> list[ComparisonRun]:
        runs = [r for r in self._all("runs", ComparisonRun) if req_id is None or r.requisition_id == req_id]
        return runs[::-1]  # newest first

    def get_run(self, run_id: str) -> ComparisonRun | None:
        return self._get("runs", run_id, ComparisonRun)

    def create_run(self, run: ComparisonRun) -> ComparisonRun:
        return self._create("runs", run)

    # -- chat ----------------------------------------------------------------
    def list_chat(self, req_id: str) -> list[ChatMessage]:
        return [m for m in self._all("chat", ChatMessage) if m.requisition_id == req_id]  # oldest first

    def add_chat(self, message: ChatMessage) -> ChatMessage:
        return self._create("chat", message)
