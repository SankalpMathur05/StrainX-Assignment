"""API routes against a temporary LocalJsonRepo (see conftest.py). No network."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import engine
from backend.app import repo as repo_package
from backend.app.config import PROJECT_ROOT, Settings, load_settings
from backend.app.main import next_label
from backend.app.models import (
    BrandStatus,
    ChatMessage,
    CoaStatus,
    CompareRequest,
    LeadTimeBasis,
    LeadTimeStart,
    PricingBasis,
    PricingUnit,
    Quote,
    Requisition,
    SourceChannel,
    TaxTreatment,
    Unit,
)
from backend.app.repo import LocalJsonRepo, get_repo
from backend.app.seed import SEED_QUOTE_IDS, SEED_REQUISITION_ID, seed_quotes, seed_requisition
from backend.scripts.gen_seed_sql import SEED_SQL_PATH, build_seed_sql

API = "/api/py"

NEW_REQUISITION = {
    "pr_number": "PR-TEST-1",
    "item_name": "Agar Powder",
    "required_quantity": 10,
    "unit": "kg",
    "need_by_date": "2026-12-20",
    "approved_budget": 50000,
}
NEW_QUOTE = {"supplier_name": "Test Supplier", "price": 1200, "pricing_unit": "per_kg"}


def _create_requisition(client: TestClient) -> str:
    response = client.post(f"{API}/requisitions", json=NEW_REQUISITION)
    assert response.status_code == 200
    return response.json()["id"]


# ---------------------------------------------------------------------------
# Health and seed
# ---------------------------------------------------------------------------
def test_health_reports_local_storage_and_no_ai(client: TestClient) -> None:
    body = client.get(f"{API}/health").json()
    assert body == {
        "status": "ok",
        "groq_configured": False,
        "supabase_configured": False,
        "storage": "local",
        "reference_date": "2026-11-24",
    }


def test_fresh_store_has_seed_requisition_and_quotes(client: TestClient) -> None:
    requisitions = client.get(f"{API}/requisitions").json()
    assert [r["pr_number"] for r in requisitions] == ["PR-USP-1147"]
    assert requisitions[0]["id"] == SEED_REQUISITION_ID

    quotes = client.get(f"{API}/requisitions/{SEED_REQUISITION_ID}/quotes").json()
    assert [q["label"] for q in quotes] == ["A", "B", "C", "D"]
    assert [q["id"] for q in quotes] == [SEED_QUOTE_IDS[label] for label in "ABCD"]
    assert quotes[1]["contradictions"]  # B's incl/extra GST contradiction survives the round trip


# ---------------------------------------------------------------------------
# Requisitions
# ---------------------------------------------------------------------------
def test_requisition_crud(client: TestClient) -> None:
    req_id = _create_requisition(client)
    created = client.get(f"{API}/requisitions/{req_id}").json()
    assert created["item_name"] == "Agar Powder"
    assert created["created_at"] and created["updated_at"]

    # newest first: the new requisition is listed before the seed
    assert [r["id"] for r in client.get(f"{API}/requisitions").json()] == [req_id, SEED_REQUISITION_ID]

    updated = client.put(f"{API}/requisitions/{req_id}", json={**NEW_REQUISITION, "approved_budget": 60000})
    assert updated.status_code == 200
    assert updated.json()["approved_budget"] == 60000
    assert updated.json()["id"] == req_id
    assert updated.json()["created_at"] == created["created_at"]

    assert client.delete(f"{API}/requisitions/{req_id}").json() == {"deleted": True}
    assert client.get(f"{API}/requisitions/{req_id}").status_code == 404


def test_requisition_not_found_and_validation(client: TestClient) -> None:
    missing = "00000000-0000-4000-8000-000000000999"
    assert client.get(f"{API}/requisitions/{missing}").status_code == 404
    assert client.get(f"{API}/requisitions/{missing}").json() == {"detail": "Requisition not found"}
    assert client.put(f"{API}/requisitions/{missing}", json=NEW_REQUISITION).status_code == 404
    assert client.delete(f"{API}/requisitions/{missing}").status_code == 404
    assert client.get(f"{API}/requisitions/{missing}/quotes").status_code == 404
    bad = client.post(f"{API}/requisitions", json={**NEW_REQUISITION, "required_quantity": 0})
    assert bad.status_code == 422


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------
def test_next_label() -> None:
    assert next_label([]) == "A"
    assert next_label(["A", "B"]) == "C"
    assert next_label(["A", "C"]) == "D"
    assert next_label(["Z"]) == "AA"
    assert next_label(["Quote 1", ""]) == "A"


def test_quote_crud_with_auto_labels(client: TestClient) -> None:
    req_id = _create_requisition(client)
    first = client.post(f"{API}/requisitions/{req_id}/quotes", json=NEW_QUOTE).json()
    second = client.post(f"{API}/requisitions/{req_id}/quotes", json={**NEW_QUOTE, "label": "  "}).json()
    assert (first["label"], second["label"]) == ("A", "B")
    assert first["requisition_id"] == req_id

    # requisition_id comes from the path, whatever the body says
    other = client.post(
        f"{API}/requisitions/{req_id}/quotes", json={**NEW_QUOTE, "requisition_id": SEED_REQUISITION_ID}
    ).json()
    assert other["requisition_id"] == req_id and other["label"] == "C"

    # the seed already has A-D, so the next one is E
    seed_extra = client.post(f"{API}/requisitions/{SEED_REQUISITION_ID}/quotes", json=NEW_QUOTE).json()
    assert seed_extra["label"] == "E"

    updated = client.put(f"{API}/quotes/{first['id']}", json={**NEW_QUOTE, "price": 1100}).json()
    assert updated["price"] == 1100
    assert updated["label"] == "A"  # blank label keeps the existing one
    assert updated["requisition_id"] == req_id

    assert client.delete(f"{API}/quotes/{second['id']}").json() == {"deleted": True}
    labels = [q["label"] for q in client.get(f"{API}/requisitions/{req_id}/quotes").json()]
    assert labels == ["A", "C"]

    assert client.put(f"{API}/quotes/{second['id']}", json=NEW_QUOTE).status_code == 404
    assert client.delete(f"{API}/quotes/{second['id']}").status_code == 404
    assert client.post(f"{API}/requisitions/nope/quotes", json=NEW_QUOTE).status_code == 404


def test_delete_requisition_cascades(client: TestClient, repo: LocalJsonRepo, fake_engine: None) -> None:
    req_id = _create_requisition(client)
    quote = client.post(f"{API}/requisitions/{req_id}/quotes", json=NEW_QUOTE).json()
    client.post(f"{API}/comparisons", json={"requisition_id": req_id})
    repo.add_chat(ChatMessage(requisition_id=req_id, role="user", content="hello"))
    assert repo.list_runs(req_id) and repo.list_chat(req_id)

    client.delete(f"{API}/requisitions/{req_id}")
    assert repo.get_quote(quote["id"]) is None
    assert repo.list_quotes(req_id) == []
    assert repo.list_runs(req_id) == []
    assert repo.list_chat(req_id) == []
    assert len(repo.list_quotes(SEED_REQUISITION_ID)) == 4  # other requisitions untouched


def test_local_repo_persists_to_disk(tmp_path: Path) -> None:
    path = tmp_path / "db.json"
    LocalJsonRepo(path).create_requisition(Requisition(**NEW_REQUISITION))
    reopened = LocalJsonRepo(path)  # a new instance reads the same file
    assert [r.pr_number for r in reopened.list_requisitions()] == ["PR-TEST-1", "PR-USP-1147"]
    assert not list(tmp_path.glob("*.tmp"))  # atomic write leaves no temp files behind


# ---------------------------------------------------------------------------
# Comparison (fake engine)
# ---------------------------------------------------------------------------
def test_stateless_compare(client: TestClient, fake_engine: None) -> None:
    payload = CompareRequest(requisition=seed_requisition(), quotes=seed_quotes()).model_dump(mode="json")
    body = client.post(f"{API}/compare", json=payload).json()
    assert body["recommendation"]["quote_label"] == "A"
    assert body["reference_date"] == "2026-11-24"  # settings default


def test_stored_compare(client: TestClient, fake_engine: None) -> None:
    url = f"{API}/requisitions/{SEED_REQUISITION_ID}/compare"
    assert client.post(url).json()["recommendation"]["quote_label"] == "A"  # body optional
    body = client.post(url, json={"weights": {"price": 100}, "reference_date": "2026-11-26"}).json()
    assert body["weights"]["price"] == 100
    assert body["reference_date"] == "2026-11-26"
    assert [a["label"] for a in body["analyses"]] == ["A", "B", "C", "D"]
    assert client.post(f"{API}/requisitions/nope/compare", json={}).status_code == 404


def test_comparison_runs(client: TestClient, fake_engine: None) -> None:
    first = client.post(f"{API}/comparisons", json={"requisition_id": SEED_REQUISITION_ID, "label": "Default"})
    assert first.status_code == 200
    run = first.json()
    assert run["id"] and run["label"] == "Default"
    assert (run["top_pick_label"], run["top_pick_supplier"]) == ("A", "Narmada Lab Supplies")
    assert run["reference_date"] == "2026-11-24"
    assert run["result"]["analyses"][0]["costing"]["worst_case_landed_inr"] == 227150

    second = client.post(
        f"{API}/comparisons", json={"requisition_id": SEED_REQUISITION_ID, "weights": {"price": 90}}
    ).json()
    listed = client.get(f"{API}/comparisons", params={"requisition_id": SEED_REQUISITION_ID}).json()
    assert [r["id"] for r in listed] == [second["id"], run["id"]]  # newest first
    assert len(client.get(f"{API}/comparisons").json()) == 2
    assert client.get(f"{API}/comparisons", params={"requisition_id": "other"}).json() == []

    assert client.get(f"{API}/comparisons/{run['id']}").json() == run
    assert client.get(f"{API}/comparisons/nope").status_code == 404
    assert client.post(f"{API}/comparisons", json={"requisition_id": "nope"}).status_code == 404


def test_chat_history_route(client: TestClient, repo: LocalJsonRepo) -> None:
    url = f"{API}/requisitions/{SEED_REQUISITION_ID}/chat"
    assert client.get(url).json() == []
    repo.add_chat(ChatMessage(requisition_id=SEED_REQUISITION_ID, role="user", content="first"))
    repo.add_chat(ChatMessage(requisition_id=SEED_REQUISITION_ID, role="assistant", content="second"))
    assert [m["content"] for m in client.get(url).json()] == ["first", "second"]  # oldest first
    assert client.get(f"{API}/requisitions/nope/chat").status_code == 404


def test_compare_seed_real_engine(client: TestClient) -> None:
    try:
        engine.compare(CompareRequest(requisition=seed_requisition(), quotes=seed_quotes()))
    except NotImplementedError:
        pytest.skip("engine.compare is not implemented yet")
    body = client.post(f"{API}/requisitions/{SEED_REQUISITION_ID}/compare", json={}).json()
    assert body["recommendation"]["quote_label"] == "A"
    quote_a = next(a for a in body["analyses"] if a["label"] == "A")
    assert quote_a["costing"]["worst_case_landed_inr"] == pytest.approx(227150, abs=0.01)


# ---------------------------------------------------------------------------
# Storage selection and SQL files
# ---------------------------------------------------------------------------
def test_suite_never_reads_real_keys() -> None:
    settings = load_settings()  # .env.local may hold real keys; conftest switches dotenv loading off
    assert not settings.groq_configured
    assert not settings.supabase_configured


def test_get_repo_uses_supabase_only_when_both_vars_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSupabaseRepo:  # never construct a real client in tests
        def __init__(self, url: str, key: str) -> None:
            self.url = url

    monkeypatch.setattr(repo_package, "SupabaseRepo", FakeSupabaseRepo)
    path = tmp_path / "db.json"
    url, key = "https://example.supabase.co", "test-key"  # dummies; nothing is contacted
    url_only = Settings(supabase_url=url, local_db_path=path)
    key_only = Settings(supabase_service_role_key=key, local_db_path=path)
    both = Settings(supabase_url=url, supabase_service_role_key=key, local_db_path=path)
    assert isinstance(get_repo(Settings(local_db_path=path)), LocalJsonRepo)
    assert isinstance(get_repo(url_only), LocalJsonRepo)
    assert isinstance(get_repo(key_only), LocalJsonRepo)
    assert isinstance(get_repo(both), FakeSupabaseRepo)


def test_schema_sql_covers_every_model_field_and_enum_value() -> None:
    schema = (PROJECT_ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
    for model in (Requisition, Quote):
        for field in model.model_fields:
            assert re.search(rf'^\s+"?{field}"?\s', schema, re.MULTILINE), f"schema.sql lacks column {field}"
    enums = (Unit, PricingUnit, PricingBasis, TaxTreatment, CoaStatus, BrandStatus, SourceChannel)
    for enum in (*enums, LeadTimeBasis, LeadTimeStart):
        for member in enum:
            assert f"'{member.value}'" in schema, f"schema.sql lacks {enum.__name__}.{member.name}"


def test_seed_sql_is_up_to_date() -> None:
    expected = build_seed_sql()
    actual = SEED_SQL_PATH.read_text(encoding="utf-8")
    assert actual == expected, "supabase/seed.sql is stale: run `uv run python backend/scripts/gen_seed_sql.py`"
