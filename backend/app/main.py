"""FastAPI app. Every route lives under /api/py — see docs/API_CONTRACT.md.

The engine (backend/app/engine.py) does all calculations; this layer loads and saves
records, and wraps the optional Groq features so they degrade to HTTP 200 with
`available: false` instead of failing.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from backend.app import engine
from backend.app.ai import grounding, prompts
from backend.app.ai.groq_client import GroqLLM, LLMError, LLMUnavailable, get_llm
from backend.app.config import Settings, get_settings
from backend.app.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CompareRequest,
    CompareResult,
    ComparisonRun,
    ComparisonRunCreate,
    ExtractRequest,
    ExtractResponse,
    Health,
    InsightsRequest,
    InsightsResponse,
    Quote,
    Requisition,
    Weights,
)
from backend.app.repo import Repo, get_repo

AI_OFF_MESSAGE = (
    "AI features are off: add GROQ_API_KEY to .env.local (see .env.example) and restart. "
    "All calculations, flags and recommendations still work without it."
)
AI_FAILED_MESSAGE = "The AI service did not respond. Calculations are unaffected — please try again shortly."
AI_RATE_LIMITED_MESSAGE = (
    "Groq's per-minute usage limit was reached. Wait about a minute and try again — "
    "calculations, flags and the recommendation are unaffected."
)


def _ai_failed_message(exc: Exception) -> str:
    return AI_RATE_LIMITED_MESSAGE if getattr(exc, "rate_limited", False) else AI_FAILED_MESSAGE

SettingsDep = Annotated[Settings, Depends(get_settings)]
RepoDep = Annotated[Repo, Depends(get_repo)]
LLMDep = Annotated[GroqLLM, Depends(get_llm)]

app = FastAPI(
    title="StrainX Quote Comparison API",
    docs_url="/api/py/docs",
    openapi_url="/api/py/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
router = APIRouter(prefix="/api/py")


class StoredCompareOptions(BaseModel):
    """Body of POST /requisitions/{id}/compare."""

    weights: Weights = Field(default_factory=Weights)
    reference_date: date | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _not_found(what: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{what} not found")


def _require_requisition(repo: Repo, req_id: str) -> Requisition:
    requisition = repo.get_requisition(req_id)
    if requisition is None:
        raise _not_found("Requisition")
    return requisition


def _label_index(label: str) -> int:
    """Spreadsheet-style column number: A -> 1, Z -> 26, AA -> 27; 0 for non-letter labels."""
    if not (label.isascii() and label.isalpha()):
        return 0
    index = 0
    for char in label.upper():
        index = index * 26 + ord(char) - ord("A") + 1
    return index


def _index_label(index: int) -> str:
    """Inverse of _label_index: 1 -> A, 27 -> AA."""
    label = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        label = chr(ord("A") + remainder) + label
    return label


def next_label(existing: list[str]) -> str:
    """The letter after the highest existing letter label: [] -> A, [A, B] -> C, [A, C] -> D."""
    return _index_label(max((_label_index(label) for label in existing), default=0) + 1)


def _compare_stored(
    repo: Repo, settings: Settings, req_id: str, weights: Weights, reference_date: date | None
) -> CompareResult:
    request = CompareRequest(
        requisition=_require_requisition(repo, req_id),
        quotes=repo.list_quotes(req_id),
        weights=weights,
        reference_date=reference_date,
    )
    return engine.compare(request, settings.reference_date)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@router.get("/health")
def health(settings: SettingsDep) -> Health:
    return Health(
        groq_configured=settings.groq_configured,
        supabase_configured=settings.supabase_configured,
        storage="supabase" if settings.supabase_configured else "local",
        reference_date=settings.reference_date,
    )


# ---------------------------------------------------------------------------
# Requisitions
# ---------------------------------------------------------------------------
@router.get("/requisitions")
def list_requisitions(repo: RepoDep) -> list[Requisition]:
    return repo.list_requisitions()


@router.post("/requisitions")
def create_requisition(body: Requisition, repo: RepoDep) -> Requisition:
    return repo.create_requisition(body)


@router.get("/requisitions/{req_id}")
def get_requisition(req_id: str, repo: RepoDep) -> Requisition:
    return _require_requisition(repo, req_id)


@router.put("/requisitions/{req_id}")
def update_requisition(req_id: str, body: Requisition, repo: RepoDep) -> Requisition:
    updated = repo.update_requisition(req_id, body)
    if updated is None:
        raise _not_found("Requisition")
    return updated


@router.delete("/requisitions/{req_id}")
def delete_requisition(req_id: str, repo: RepoDep) -> dict[str, bool]:
    if not repo.delete_requisition(req_id):
        raise _not_found("Requisition")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------
@router.get("/requisitions/{req_id}/quotes")
def list_quotes(req_id: str, repo: RepoDep) -> list[Quote]:
    _require_requisition(repo, req_id)
    return repo.list_quotes(req_id)


@router.post("/requisitions/{req_id}/quotes")
def create_quote(req_id: str, body: Quote, repo: RepoDep) -> Quote:
    _require_requisition(repo, req_id)
    label = body.label.strip() or next_label([q.label for q in repo.list_quotes(req_id)])
    return repo.create_quote(body.model_copy(update={"requisition_id": req_id, "label": label}))


@router.put("/quotes/{quote_id}")
def update_quote(quote_id: str, body: Quote, repo: RepoDep) -> Quote:
    existing = repo.get_quote(quote_id)
    if existing is None:
        raise _not_found("Quote")
    # A quote stays with its requisition; a blank label keeps the current one.
    changes = {"requisition_id": existing.requisition_id, "label": body.label.strip() or existing.label}
    updated = repo.update_quote(quote_id, body.model_copy(update=changes))
    if updated is None:
        raise _not_found("Quote")
    return updated


@router.delete("/quotes/{quote_id}")
def delete_quote(quote_id: str, repo: RepoDep) -> dict[str, bool]:
    if not repo.delete_quote(quote_id):
        raise _not_found("Quote")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------
@router.post("/compare")
def compare(body: CompareRequest, settings: SettingsDep) -> CompareResult:
    return engine.compare(body, settings.reference_date)


@router.post("/requisitions/{req_id}/compare")
def compare_stored(
    req_id: str, repo: RepoDep, settings: SettingsDep, body: StoredCompareOptions | None = None
) -> CompareResult:
    options = body or StoredCompareOptions()
    return _compare_stored(repo, settings, req_id, options.weights, options.reference_date)


@router.get("/comparisons")
def list_comparisons(repo: RepoDep, requisition_id: str | None = None) -> list[ComparisonRun]:
    return repo.list_runs(requisition_id)


@router.post("/comparisons")
def create_comparison(body: ComparisonRunCreate, repo: RepoDep, settings: SettingsDep) -> ComparisonRun:
    result = _compare_stored(repo, settings, body.requisition_id, body.weights, body.reference_date)
    run = ComparisonRun(
        id="",  # assigned by the repo
        requisition_id=body.requisition_id,
        label=body.label,
        weights=result.weights,
        reference_date=result.reference_date,
        top_pick_label=result.recommendation.quote_label,
        top_pick_supplier=result.recommendation.supplier_name,
        result=result.model_dump(mode="json"),
    )
    return repo.create_run(run)


@router.get("/comparisons/{run_id}")
def get_comparison(run_id: str, repo: RepoDep) -> ComparisonRun:
    run = repo.get_run(run_id)
    if run is None:
        raise _not_found("Comparison run")
    return run


@router.get("/requisitions/{req_id}/chat")
def list_chat(req_id: str, repo: RepoDep) -> list[ChatMessage]:
    _require_requisition(repo, req_id)
    return repo.list_chat(req_id)


# ---------------------------------------------------------------------------
# AI (Groq) — always HTTP 200; `available: false` when off or failing
# ---------------------------------------------------------------------------
def _extract(llm: GroqLLM, messages: list[prompts.Message], model: type[Requisition] | type[Quote]) -> ExtractResponse:
    try:
        raw, model_used = llm.complete_json("extraction", messages)
    except LLMUnavailable:
        return ExtractResponse(available=False, message=AI_OFF_MESSAGE)
    except LLMError as exc:
        return ExtractResponse(available=False, message=_ai_failed_message(exc))
    fields, missing, ambiguities = prompts.parse_extraction(raw, model)
    return ExtractResponse(
        available=True, fields=fields, missing_fields=missing, ambiguities=ambiguities, model_used=model_used
    )


@router.post("/extract/requisition")
def extract_requisition(body: ExtractRequest, settings: SettingsDep, llm: LLMDep) -> ExtractResponse:
    messages = prompts.requisition_extraction_messages(body.text, settings.reference_date)
    return _extract(llm, messages, Requisition)


@router.post("/extract/quote")
def extract_quote(body: ExtractRequest, settings: SettingsDep, llm: LLMDep) -> ExtractResponse:
    messages = prompts.quote_extraction_messages(body.text, body.requisition, settings.reference_date)
    response = _extract(llm, messages, Quote)
    if response.available:
        response.fields["raw_text"] = body.text  # provenance: keep what was pasted
        foreign = response.fields.get("currency", "INR") != "INR"
        if foreign and "fx_rate_to_inr" not in response.fields and "fx_rate_to_inr" not in response.missing_fields:
            response.missing_fields.append("fx_rate_to_inr")  # otherwise the default 1.0 would be used
    return response


@router.post("/insights")
def insights(body: InsightsRequest, settings: SettingsDep, llm: LLMDep) -> InsightsResponse:
    result = engine.compare(body.compare, settings.reference_date)
    # Deterministic content for when the AI is off or fails, so the UI is never empty.
    fallback = InsightsResponse(
        available=False,
        headline=result.recommendation.rationale,
        supplier_questions={a.label: a.questions for a in result.analyses},
    )
    context = prompts.ai_context(body.compare, result)
    try:
        raw, model_used = llm.complete_json("insight", prompts.insight_messages(context))
        draft = prompts.InsightsDraft.model_validate(raw)
    except LLMUnavailable:
        return fallback.model_copy(update={"message": AI_OFF_MESSAGE})
    except (LLMError, ValidationError) as exc:
        return fallback.model_copy(update={"message": _ai_failed_message(exc)})
    return InsightsResponse(
        available=True,
        headline=draft.headline,
        tradeoffs=draft.tradeoffs,
        supplier_questions=draft.supplier_questions,
        ungrounded_numbers=grounding.ungrounded_numbers(draft.all_text(), context),
        model_used=model_used,
    )


@router.post("/chat")
def chat(body: ChatRequest, settings: SettingsDep, repo: RepoDep, llm: LLMDep) -> ChatResponse:
    if body.requisition_id:
        _require_requisition(repo, body.requisition_id)
    result = engine.compare(body.compare, settings.reference_date)
    context = prompts.ai_context(body.compare, result)
    try:
        reply, model_used = llm.complete_text("chat", prompts.chat_messages(context, body.history, body.message))
    except LLMUnavailable:
        return ChatResponse(available=False, message=AI_OFF_MESSAGE)
    except LLMError as exc:
        return ChatResponse(available=False, message=_ai_failed_message(exc))
    if body.requisition_id:
        repo.add_chat(ChatMessage(requisition_id=body.requisition_id, role="user", content=body.message))
        repo.add_chat(
            ChatMessage(requisition_id=body.requisition_id, role="assistant", content=reply, model=model_used)
        )
    # Numbers the user typed may be repeated back; earlier AI replies are not a trusted source.
    user_text = [body.message, *(turn.content for turn in body.history if turn.role == "user")]
    return ChatResponse(
        available=True,
        reply=reply,
        ungrounded_numbers=grounding.ungrounded_numbers(reply, [context, user_text]),
        model_used=model_used,
    )


app.include_router(router)
