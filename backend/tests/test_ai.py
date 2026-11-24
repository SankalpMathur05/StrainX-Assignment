"""AI routes with a fake LLM, the Groq wrapper with a fake SDK client, and number grounding."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import groq
import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.ai import prompts
from backend.app.ai.groq_client import GroqLLM, LLMError, LLMUnavailable
from backend.app.ai.grounding import extract_numbers, ungrounded_numbers
from backend.app.config import Settings
from backend.app.models import Quote, Requisition
from backend.app.repo import LocalJsonRepo
from backend.app.seed import SEED_REQUISITION_ID, seed_requisition
from backend.tests.conftest import FakeLLM, seed_compare_payload

API = "/api/py"
AI_OFF = (
    "AI features are off: add GROQ_API_KEY to .env.local (see .env.example) and restart. "
    "All calculations, flags and recommendations still work without it."
)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
def test_extract_quote_keeps_only_known_valid_fields(ai_client: TestClient, fake_llm: FakeLLM) -> None:
    fake_llm.json_reply = {
        "fields": {
            "supplier_name": "Narmada Lab Supplies",
            "price": 3850,
            "pricing_unit": "per_pack",
            "pack_size_value": 500,
            "pack_size_unit": "g",
            "valid_until": "2026-11-30",
            "freight_cost": None,  # nullable: "at actual"
            "transit_days": None,  # not nullable: just "not stated"
            "tax_treatment": "GST_EXTRA",  # not an allowed value
            "advance_pct": 150,  # outside 0-100
            "favourite_colour": "blue",  # not a Quote field
            "id": "made-up",  # server-managed
        },
        "missing_fields": ["moq_quantity", "not_a_field"],
        "ambiguities": ["Freight below Rs 50,000 is not stated."],
    }
    text = "Rate: Rs 3,850 per 500 g pack ..."
    body = ai_client.post(f"{API}/extract/quote", json={"text": text}).json()

    assert body["available"] is True and body["model_used"] == "fake-model"
    assert body["fields"] == {
        "supplier_name": "Narmada Lab Supplies",
        "price": 3850.0,
        "pricing_unit": "per_pack",
        "pack_size_value": 500.0,
        "pack_size_unit": "g",
        "valid_until": "2026-11-30",
        "freight_cost": None,
        "raw_text": text,  # provenance is added by the server
    }
    assert body["missing_fields"] == ["moq_quantity"]
    assert body["ambiguities"][0] == "Freight below Rs 50,000 is not stated."
    assert any(a.startswith("tax_treatment: ignored 'GST_EXTRA'") for a in body["ambiguities"])
    assert any(a.startswith("advance_pct: ignored 150") for a in body["ambiguities"])
    assert len(body["ambiguities"]) == 3


def test_extract_requisition_lists_missing_required_fields(ai_client: TestClient, fake_llm: FakeLLM) -> None:
    fake_llm.json_reply = {"fields": {"item_name": "Yeast Extract Powder", "need_by_date": "2026-12-05"}}
    body = ai_client.post(f"{API}/extract/requisition", json={"text": "Need yeast extract by 5/12/2026"}).json()
    assert body["fields"] == {"item_name": "Yeast Extract Powder", "need_by_date": "2026-12-05"}
    assert body["missing_fields"] == ["pr_number", "required_quantity"]
    assert body["ambiguities"] == []


def test_extract_quote_in_foreign_currency_asks_for_fx_rate(ai_client: TestClient, fake_llm: FakeLLM) -> None:
    fake_llm.json_reply = {"fields": {"supplier_name": "Pacific", "price": 78, "currency": "USD"}}
    body = ai_client.post(f"{API}/extract/quote", json={"text": "USD 78.00 per kg"}).json()
    assert "fx_rate_to_inr" in body["missing_fields"]


def test_extraction_prompt_lists_fields_enums_rules_and_context(ai_client: TestClient, fake_llm: FakeLLM) -> None:
    fake_llm.json_reply = {"fields": {}}
    requisition = seed_requisition().model_dump(mode="json")
    ai_client.post(f"{API}/extract/quote", json={"text": "rate 7200/kg incl GST", "requisition": requisition})
    task, messages = fake_llm.calls[0]
    system, user = messages[0]["content"], messages[1]["content"]
    assert task == "extraction"
    assert "- tax_treatment: one of EXCLUSIVE_GST | INCLUSIVE_GST | IMPORT_DUTY_IGST" in system
    assert "- valid_until: date YYYY-MM-DD or null" in system
    assert "15/11/2026 means 2026-11-15" in system and "2026-11-24" in system
    assert "Never calculate totals" in system and "against shipping documents" in system
    assert "- id:" not in system and "- raw_text:" not in system and "- label:" not in system
    assert "rate 7200/kg incl GST" in user and "Yeast Extract Powder" in user


def test_field_hints_refer_to_real_fields() -> None:
    known = set(Requisition.model_fields) | set(Quote.model_fields)
    assert set(prompts.FIELD_HINTS) <= known


def test_extract_without_key_says_ai_is_off(client: TestClient) -> None:
    for kind in ("requisition", "quote"):
        body = client.post(f"{API}/extract/{kind}", json={"text": "anything"}).json()
        assert body["available"] is False
        assert body["message"] == AI_OFF
        assert body["fields"] == {}


def test_extract_provider_failure_returns_200_unavailable(ai_client: TestClient, fake_llm: FakeLLM) -> None:
    fake_llm.error = LLMError("both models failed")
    response = ai_client.post(f"{API}/extract/quote", json={"text": "anything"})
    assert response.status_code == 200
    assert response.json()["available"] is False and response.json()["message"]


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
def test_insights_flag_invented_numbers_only(ai_client: TestClient, fake_llm: FakeLLM, fake_engine: None) -> None:
    fake_llm.json_reply = {
        "headline": "Quote A at Rs 2,27,150 is the best pick and saves Rs 9,99,999.",
        "tradeoffs": ["Quote B costs Rs 2,37,150 but needs 100% advance."],
        "supplier_questions": {"A": ["Is delivery free for orders above Rs 50,000?"]},
    }
    body = ai_client.post(f"{API}/insights", json={"compare": seed_compare_payload()}).json()
    assert body["available"] is True and body["model_used"] == "fake-model"
    assert body["headline"].startswith("Quote A")
    assert body["supplier_questions"] == {"A": ["Is delivery free for orders above Rs 50,000?"]}
    # 2,27,150 and 2,37,150 are engine totals; 50,000 is quote A's free-freight threshold.
    assert body["ungrounded_numbers"] == ["9,99,999"]


def test_insights_context_is_compact_engine_output(ai_client: TestClient, fake_llm: FakeLLM, fake_engine: None) -> None:
    fake_llm.json_reply = {"headline": "Quote A."}
    ai_client.post(f"{API}/insights", json={"compare": seed_compare_payload()})
    task, messages = fake_llm.calls[0]
    assert task == "insight"
    assert "ONLY numbers that appear in the data" in messages[0]["content"]
    data = messages[1]["content"]
    assert "227150" in data and "Narmada Lab Supplies" in data
    assert "Dear Sir" not in data and "raw_text" not in data  # raw quote text is dropped


def test_insights_without_key_use_engine_content(client: TestClient, fake_engine: None) -> None:
    response = client.post(f"{API}/insights", json={"compare": seed_compare_payload()})
    body = response.json()
    assert response.status_code == 200
    assert body["available"] is False
    assert body["message"] == AI_OFF
    assert body["headline"] == "Quote A is the best overall value."  # the engine's rationale
    assert list(body["supplier_questions"]) == ["A", "B", "C", "D"]
    assert body["supplier_questions"]["A"] == ["Can Narmada Lab Supplies confirm the final landed price?"]


def test_insights_unusable_reply_falls_back(ai_client: TestClient, fake_llm: FakeLLM, fake_engine: None) -> None:
    fake_llm.json_reply = {"headline": "", "tradeoffs": "not a list"}
    body = ai_client.post(f"{API}/insights", json={"compare": seed_compare_payload()}).json()
    assert body["available"] is False and body["message"]
    assert body["headline"] == "Quote A is the best overall value."


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
def test_chat_persists_user_and_assistant_messages(
    ai_client: TestClient, fake_llm: FakeLLM, fake_engine: None
) -> None:
    fake_llm.text_reply = "Quote A lands at Rs 2,27,150; a 2,50,000 budget leaves 22,850 spare."
    request = {
        "requisition_id": SEED_REQUISITION_ID,
        "message": "What if the budget were 2,50,000?",
        "compare": seed_compare_payload(),
        "history": [{"role": "assistant", "content": "Earlier I said 22,850."}],
    }
    body = ai_client.post(f"{API}/chat", json=request).json()
    assert body["available"] is True and body["model_used"] == "fake-model"
    # 2,50,000 was typed by the user; 22,850 is the AI's own arithmetic (an earlier AI reply is not a source).
    assert body["ungrounded_numbers"] == ["22,850"]

    history = ai_client.get(f"{API}/requisitions/{SEED_REQUISITION_ID}/chat").json()
    assert [(m["role"], m["content"]) for m in history] == [
        ("user", "What if the budget were 2,50,000?"),
        ("assistant", fake_llm.text_reply),
    ]
    assert history[1]["model"] == "fake-model"

    task, messages = fake_llm.calls[0]
    assert task == "chat"
    assert [m["role"] for m in messages] == ["system", "assistant", "user"]
    system = messages[0]["content"]
    assert "conversational" in system and "Never do arithmetic" in system  # friendly, but no maths


def test_chat_without_requisition_id_is_not_persisted(
    ai_client: TestClient, fake_llm: FakeLLM, repo: LocalJsonRepo, fake_engine: None
) -> None:
    fake_llm.text_reply = "Quote A."
    body = ai_client.post(f"{API}/chat", json={"message": "Best?", "compare": seed_compare_payload()}).json()
    assert body["reply"] == "Quote A."
    assert repo.list_chat(SEED_REQUISITION_ID) == []


def test_chat_without_key(client: TestClient, repo: LocalJsonRepo, fake_engine: None) -> None:
    request = {"requisition_id": SEED_REQUISITION_ID, "message": "Best?", "compare": seed_compare_payload()}
    body = client.post(f"{API}/chat", json=request).json()
    assert body == {"available": False, "message": AI_OFF, "reply": "", "ungrounded_numbers": [], "model_used": None}
    assert repo.list_chat(SEED_REQUISITION_ID) == []
    missing = {**request, "requisition_id": "nope"}
    assert client.post(f"{API}/chat", json=missing).status_code == 404


# ---------------------------------------------------------------------------
# Groq wrapper (fake SDK client; no network)
# ---------------------------------------------------------------------------
class FakeCompletions:
    def __init__(self, failing: set[str], content: str = '{"ok": true}') -> None:
        self.failing = failing
        self.content = content
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if kwargs["model"] in self.failing:
            raise groq.APIConnectionError(request=httpx.Request("POST", "https://api.groq.com"))
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _llm(completions: FakeCompletions) -> GroqLLM:
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return GroqLLM(Settings(), client=client)


def test_groq_primary_model_and_json_mode() -> None:
    completions = FakeCompletions(failing=set())
    assert _llm(completions).complete_json("insight", [{"role": "user", "content": "JSON"}]) == (
        {"ok": True},
        "openai/gpt-oss-120b",
    )
    call = completions.calls[0]
    assert call["response_format"] == {"type": "json_object"} and call["temperature"] == 0


def test_groq_falls_back_when_primary_raises() -> None:
    completions = FakeCompletions(failing={"openai/gpt-oss-20b"})
    data, model_used = _llm(completions).complete_json("extraction", [{"role": "user", "content": "JSON"}])
    assert data == {"ok": True}
    assert model_used == "openai/gpt-oss-120b"
    assert [c["model"] for c in completions.calls] == ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]


def test_groq_falls_back_on_invalid_json() -> None:
    completions = FakeCompletions(failing=set(), content="not json")
    with pytest.raises(LLMError):
        _llm(completions).complete_json("insight", [{"role": "user", "content": "JSON"}])
    assert len(completions.calls) == 2


def test_groq_chat_text_and_both_models_failing() -> None:
    completions = FakeCompletions(failing=set(), content="Quote A.")
    assert _llm(completions).complete_text("chat", []) == ("Quote A.", "openai/gpt-oss-120b")
    assert completions.calls[0]["temperature"] == 0.5 and "response_format" not in completions.calls[0]

    failing = FakeCompletions(failing={"openai/gpt-oss-120b", "openai/gpt-oss-20b"})
    with pytest.raises(LLMError):
        _llm(failing).complete_text("chat", [])


def test_chat_context_is_compact_and_keeps_engine_numbers() -> None:
    from backend.app import engine
    from backend.app.models import CompareRequest
    from backend.app.seed import seed_quotes

    request = CompareRequest(requisition=seed_requisition(), quotes=seed_quotes())
    result = engine.compare(request)
    digest = prompts.chat_context(request, result)
    # Much smaller than the JSON context (Groq free tier: 8,000 tokens per minute per model)...
    assert len(digest) < 0.6 * len(prompts._json(prompts.ai_context(request, result)))
    # ...but still carries the figures a director asks about, so replies stay grounded.
    for figure in ["Rs 2,27,150", "Rs 4,47,456.16", "Rs 2,30,978.08", "Rs 1,79,950", "Rs 34,650"]:
        assert figure in digest
    assert ungrounded_numbers("A lands at Rs 2,27,150, C at Rs 4,47,456.16.", digest) == []


def test_chat_uses_low_reasoning_effort_on_gpt_oss() -> None:
    completions = FakeCompletions(failing=set(), content="Hi!")
    _llm(completions).complete_text("chat", [])
    assert completions.calls[0]["reasoning_effort"] == "low"


class RateLimitedCompletions(FakeCompletions):
    """Every model answers 429, like Groq's free tier after a burst of calls."""

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        request = httpx.Request("POST", "https://api.groq.com")
        raise groq.RateLimitError("rate limited", response=httpx.Response(429, request=request), body=None)


def test_groq_rate_limit_is_reported_as_such() -> None:
    with pytest.raises(LLMError) as caught:
        _llm(RateLimitedCompletions(failing=set())).complete_text("chat", [])
    assert caught.value.rate_limited is True


def test_groq_without_key_is_unavailable() -> None:
    with pytest.raises(LLMUnavailable):
        GroqLLM(Settings(groq_api_key=None)).complete_text("chat", [])


# ---------------------------------------------------------------------------
# Grounding
# ---------------------------------------------------------------------------
def test_extract_numbers_handles_grouping_currency_and_percent() -> None:
    text = "Rs 2,27,150 vs ₹4,47,456.16, USD 1,000,000 or 227,150 at 18% and 17898.25"
    assert extract_numbers(text) == [227150, 447456.16, 1000000, 227150, 18, 17898.25]
    assert extract_numbers("Rs3,850 per pack, -20,050 variance") == [3850, 20050]


def test_ungrounded_numbers_rules() -> None:
    context = {"costing": {"landed": 227150.0, "variance": -20050.0, "tax": 17898.25}, "terms": ["70% against docs"]}
    assert ungrounded_numbers("Rs 2,27,150 lands, 20,050 under budget", context) == []
    assert ungrounded_numbers("Tax of 17,898 (rounded)", context) == []  # rounding tolerance
    assert ungrounded_numbers("Pay 70% against documents", context) == []  # number inside a string
    assert ungrounded_numbers("By 2026, in 5 days, 18% GST", context) == []  # years and small ints ignored
    assert ungrounded_numbers("Saves Rs 9,99,999 and 9,99,999 again, or 45.5", context) == ["9,99,999", "45.5"]
    assert ungrounded_numbers("Rs 2,026 extra", context) == ["2,026"]  # an amount, not a year
