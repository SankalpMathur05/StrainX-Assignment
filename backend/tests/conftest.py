"""Shared fixtures for the API and AI tests. Fully offline and deterministic.

- Real keys in .env.local are never read: dotenv loading is switched off for the whole
  run, and every config variable is removed from the environment for each test.
- Storage is a LocalJsonRepo in tmp_path; the LLM is either the real wrapper with no key
  (the "AI off" path) or FakeLLM. Nothing reaches Groq or Supabase.
"""

from __future__ import annotations

import os

os.environ["STRAINX_SKIP_DOTENV"] = "1"  # before anything can load settings

from collections.abc import Iterator  # noqa: E402
from datetime import date  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app import engine  # noqa: E402
from backend.app import repo as repo_package  # noqa: E402
from backend.app.ai import groq_client  # noqa: E402
from backend.app.config import Settings, get_settings  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models import (  # noqa: E402
    CompareRequest,
    CompareResult,
    CostBreakdown,
    CostScenario,
    DeliveryEstimate,
    Flag,
    QuoteAnalysis,
    QuoteCosting,
    Recommendation,
    ScoreBreakdown,
    Severity,
)
from backend.app.repo import LocalJsonRepo, get_repo  # noqa: E402
from backend.app.seed import seed_quotes, seed_requisition  # noqa: E402

CONFIG_ENV_VARS = [
    "GROQ_API_KEY",
    "GROQ_EXTRACTION_MODEL",
    "GROQ_EXTRACTION_FALLBACK_MODEL",
    "GROQ_INSIGHT_MODEL",
    "GROQ_INSIGHT_FALLBACK_MODEL",
    "GROQ_CHAT_MODEL",
    "GROQ_CHAT_FALLBACK_MODEL",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "REFERENCE_DATE",
    "VERCEL",
]


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """No real keys or config in the environment, and no settings/clients cached from elsewhere."""
    monkeypatch.setenv("STRAINX_SKIP_DOTENV", "1")
    for name in CONFIG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    caches = [get_settings, repo_package._repo_for, groq_client._llm_for]
    for cached in caches:
        cached.cache_clear()
    yield
    for cached in caches:
        cached.cache_clear()
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class FakeLLM:
    """Stands in for GroqLLM: returns canned replies (or raises `error`) and records calls."""

    model = "fake-model"

    def __init__(self) -> None:
        self.json_reply: dict[str, Any] = {}
        self.text_reply = ""
        self.error: Exception | None = None
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    def complete_json(self, task: str, messages: list[dict[str, str]]) -> tuple[dict[str, Any], str]:
        self.calls.append((task, messages))
        if self.error:
            raise self.error
        return self.json_reply, self.model

    def complete_text(self, task: str, messages: list[dict[str, str]]) -> tuple[str, str]:
        self.calls.append((task, messages))
        if self.error:
            raise self.error
        return self.text_reply, self.model


def fake_compare(request: CompareRequest, default_reference_date: date = date(2026, 11, 24)) -> CompareResult:
    """A small but valid CompareResult: quotes ranked in input order, first landed total 2,27,150."""
    req = request.requisition
    analyses = []
    for rank, quote in enumerate(request.quotes, start=1):
        landed = 227150.0 + 10000 * (rank - 1)
        breakdown = CostBreakdown(
            quantity=req.required_quantity,
            goods_pre_tax_inr=192500.0,
            recoverable_tax_inr=34650.0,
            total_landed_inr=landed,
            unit_cost_pre_tax=7700.0,
            unit_cost_landed=landed / req.required_quantity,
            unit_cost_landed_per_ordered=landed / req.required_quantity,
        )
        scenario = CostScenario(
            name="primary",
            description="GST exclusive @ 18%",
            tax_treatment=quote.tax_treatment,
            gst_rate_pct=quote.gst_rate_pct,
            commitment=breakdown,
            required_only=breakdown,
        )
        analyses.append(
            QuoteAnalysis(
                quote_id=quote.id,
                label=quote.label,
                supplier_name=quote.supplier_name,
                rank=rank,
                costing=QuoteCosting(
                    required_quantity=req.required_quantity,
                    order_quantity=req.required_quantity,
                    scenarios=[scenario],
                    worst_case_landed_inr=landed,
                    budget_variance_inr=landed - req.approved_budget,
                ),
                delivery=DeliveryEstimate(),
                flags=[Flag(code="OVER_BUDGET", severity=Severity.WARNING, message="Over budget.")],
                critical_count=0,
                warning_count=1,
                facts=[f"Rate {quote.price} {quote.currency}"],
                assumptions=["PO placed on the reference date."],
                questions=[f"Can {quote.supplier_name} confirm the final landed price?"],
                score=ScoreBreakdown(
                    price=90, delivery=80, payment=70, quality=60, weighted=75, penalty=5, final=70, display=70
                ),
            )
        )
    top = analyses[0] if analyses else None
    return CompareResult(
        reference_date=request.reference_date or default_reference_date,
        requisition=req,
        weights=request.weights,
        analyses=analyses,
        recommendation=Recommendation(
            quote_id=top.quote_id if top else None,
            quote_label=top.label if top else None,
            supplier_name=top.supplier_name if top else None,
            rationale=f"Quote {top.label} is the best overall value." if top else "No quotes to compare.",
        ),
        summary_text="Fake summary.",
        global_assumptions=["Fake engine used in tests."],
    )


def seed_compare_payload() -> dict[str, Any]:
    """JSON body of a CompareRequest for the seed requisition and Quotes A-D."""
    return CompareRequest(requisition=seed_requisition(), quotes=seed_quotes()).model_dump(mode="json")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def settings(tmp_path: Any) -> Settings:
    """Defaults with no Groq or Supabase keys, storing data in tmp_path."""
    return Settings(local_db_path=tmp_path / "local_db.json")


@pytest.fixture
def repo(settings: Settings) -> LocalJsonRepo:
    return LocalJsonRepo(settings.local_db_path)


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def client(settings: Settings, repo: LocalJsonRepo) -> TestClient:
    """API client: tmp JSON store, no keys, and the real Groq wrapper (which has no key, so AI is off)."""
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[groq_client.get_llm] = lambda: groq_client.GroqLLM(settings)
    return TestClient(app)


@pytest.fixture
def ai_client(client: TestClient, fake_llm: FakeLLM) -> TestClient:
    """Like `client`, but the LLM is FakeLLM."""
    app.dependency_overrides[groq_client.get_llm] = lambda: fake_llm
    return client


@pytest.fixture
def fake_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "compare", fake_compare)
