"""The three sample requisitions in backend/app/seed.py, run through the real engine.

Every worst-case landed total below was worked out by hand from the quote terms first (arithmetic
in the comments) and only then checked against the engine. Rules used: cost the commitment
max(required, MOQ) rounded up to whole packs; "GST extra" adds rate x goods, "GST inclusive" backs it
out of the price (the total is the price); imports = CIF x FX, + customs duty % of CIF, + IGST % of
(CIF + duty), + clearance (default 8,000) + inland transport (default 6,500); unknown freight is left
out; with two tax readings the higher total is the worst case. Reference date 2026-11-24, default weights.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.app import engine
from backend.app.models import CompareRequest, CompareResult, Quote, QuoteAnalysis, Requisition, Severity
from backend.app.repo import LocalJsonRepo
from backend.app.seed import (
    ETHANOL_QUOTES,
    ETHANOL_REQUISITION,
    GLOVES_QUOTES,
    GLOVES_REQUISITION,
    PEPTONE_QUOTES,
    PEPTONE_REQUISITION,
    SEED_QUOTES,
    SEED_REQUISITION,
    SEED_SETS,
    all_seed_quotes,
    all_seed_requisitions,
)
from backend.scripts.gen_seed_sql import build_seed_sql


def approx(x: float):
    return pytest.approx(x, abs=0.01)


def run(requisition: Requisition, quotes: list[Quote]) -> tuple[CompareResult, dict[str, QuoteAnalysis]]:
    result = engine.compare(CompareRequest(requisition=requisition, quotes=quotes))
    return result, {a.label: a for a in result.analyses}


def flag_codes(by_label: dict[str, QuoteAnalysis]) -> dict[str, set[str]]:
    return {label: {f.code for f in a.flags} for label, a in by_label.items()}


def severity(analysis: QuoteAnalysis, code: str) -> Severity:
    return next(f.severity for f in analysis.flags if f.code == code)


def assert_worst_case_totals(by_label: dict[str, QuoteAnalysis], expected: dict[str, float]) -> None:
    assert set(by_label) == set(expected)
    for label, total in expected.items():
        costing = by_label[label].costing
        assert costing.comparable, label
        assert costing.worst_case_landed_inr == approx(total), label


# ---------------------------------------------------------------------------
# Shape of the seed
# ---------------------------------------------------------------------------
def test_pr_usp_1147_leads_and_is_unchanged() -> None:
    requisition, quotes = SEED_SETS[0]
    assert quotes is SEED_QUOTES
    # Identical to SEED_REQUISITION apart from the created_at that orders the dashboard list.
    assert SEED_REQUISITION.created_at is None
    assert requisition.model_dump(exclude={"created_at"}) == SEED_REQUISITION.model_dump(exclude={"created_at"})


def test_pr_usp_1147_is_the_newest_seed_requisition() -> None:
    requisitions = all_seed_requisitions()
    assert [r.pr_number for r in requisitions] == ["PR-USP-1147", "PR-MB-1143", "PR-USP-1138", "PR-QC-1132"]
    created = [r.created_at for r in requisitions]
    assert all(created) and created == sorted(created, reverse=True)  # type: ignore[type-var]
    for r in requisitions:
        assert r.created_at is not None and r.created_at.date() == r.date  # raised on the day it is dated


def test_seed_ids_are_fixed_unique_and_linked() -> None:
    ids = [r.id for r in all_seed_requisitions()] + [q.id for q in all_seed_quotes()]
    assert len(ids) == len(set(ids)) == 4 + 15
    for requisition, quotes in SEED_SETS:
        prefix = requisition.pr_number[-4:] + "0000"  # PR-QC-1132 -> 11320000-...
        assert requisition.id == f"{prefix}-0000-4000-8000-000000000000"
        assert [q.label for q in quotes] == list("ABCD"[: len(quotes)])
        for q in quotes:
            assert q.requisition_id == requisition.id
            assert q.id == f"{prefix}-0000-4000-8000-00000000000{q.label.lower()}"


def test_seed_helpers_return_copies() -> None:
    all_seed_requisitions()[0].item_name = "changed"
    all_seed_quotes()[1].contradictions.append("changed")  # PR-USP-1147 Quote B
    assert SEED_SETS[0][0].item_name == "Yeast Extract Powder"
    assert len(SEED_QUOTES[1].contradictions) == 1


# Well-known real manufacturers / brands that must not appear in the fictional sample sets.
REAL_NAMES = [
    "Merck", "Sigma", "Aldrich", "Millipore", "HiMedia", "Thermo", "Fisher", "Oxoid", "Difco", "Bacto", "BD",
    "Becton", "Kimberly", "Ansell", "Loba", "Qualigens", "Finar", "Rankem", "Spectrochem", "SRL", "Avantor", "VWR",
]


def test_sample_sets_use_no_real_brand_or_company_names() -> None:
    pattern = re.compile(r"\b(" + "|".join(REAL_NAMES) + r")\b", re.IGNORECASE)
    for requisition, quotes in SEED_SETS[1:]:
        for record in [requisition, *quotes]:
            text = " ".join(str(value) for value in record.model_dump().values())
            assert not pattern.search(text), f"{record}: {pattern.search(text)}"


def test_fresh_local_store_and_seed_sql_hold_every_set(tmp_path: Path) -> None:
    repo = LocalJsonRepo(tmp_path / "db.json")
    assert [r.id for r in repo.list_requisitions()] == [r.id for r, _ in SEED_SETS]  # newest first
    timestamps = {"created_at", "updated_at"}
    for requisition, quotes in SEED_SETS:
        stored = repo.get_requisition(str(requisition.id))
        assert stored is not None and stored.created_at == requisition.created_at
        stored_quotes = [q.model_dump(exclude=timestamps) for q in repo.list_quotes(str(requisition.id))]
        assert stored_quotes == [q.model_dump(exclude=timestamps) for q in quotes]  # every field round-trips

    sql = build_seed_sql()
    for requisition in all_seed_requisitions():
        assert requisition.created_at is not None
        assert f"'{requisition.id}'" in sql and f"'{requisition.created_at.isoformat()}'" in sql
    assert all(f"'{q.id}'" in sql for q in all_seed_quotes())
    assert sql.count("on conflict (id) do nothing") == 2


# ---------------------------------------------------------------------------
# PR-QC-1132: Ethanol absolute AR, 200 L, need-by 8 Dec 2026, budget Rs 1,80,000
# ---------------------------------------------------------------------------
def test_ethanol_pr_qc_1132() -> None:
    result, by_label = run(ETHANOL_REQUISITION, ETHANOL_QUOTES)

    # A: 200 L / 2.5 L = 80 bottles x Rs 1,795 = 1,43,600. That is below the Rs 1,50,000 free-delivery
    #    threshold, so freight 1,200 is charged. GST 18% x 1,43,600 = 25,848.
    #    1,43,600 + 25,848 + 1,200 = 1,70,648
    # B: full 30 L carboys only: 200 / 30 = 6.67 -> 7 carboys = 210 L x Rs 845 (GST inclusive) = 1,77,450
    #    (= 1,50,381.36 goods + 27,068.64 GST already inside); + transport 2,000 = 1,79,450
    # C: MOQ 100 bottles x 2.5 L = 250 L > 200 L, so commit to 100 bottles x Rs 1,560 = 1,56,000;
    #    GST 18% = 28,080; freight "at actual" left out. 1,56,000 + 28,080 = 1,84,080
    # D: 200 / 5 = 40 cans x Rs 3,450 = 1,38,000. GST-inclusive reading: 1,38,000.
    #    GST-extra reading: 1,38,000 + 18% (24,840) = 1,62,840 -> the worst case
    assert_worst_case_totals(by_label, {"A": 170648, "B": 179450, "C": 184080, "D": 162840})

    a, b, c, d = (by_label[label] for label in "ABCD")
    assert a.costing.scenarios[0].commitment.packs == 80
    assert a.costing.scenarios[0].commitment.freight_inr == 1200  # threshold not met
    assert b.costing.order_quantity == 210 and b.costing.scenarios[0].commitment.packs == 7
    assert b.costing.scenarios[0].commitment.goods_pre_tax_inr == approx(150381.36)
    assert c.costing.moq_applies and c.costing.order_quantity == 250 and c.costing.incomplete
    # If the MOQ were waived: 80 x 1,560 = 1,24,800 + 18% (22,464) = 1,47,264
    assert c.costing.scenarios[0].required_only.total_landed_inr == approx(147264)
    assert d.costing.worst_case_index == 1
    assert d.costing.scenarios[0].commitment.total_landed_inr == approx(138000)

    assert flag_codes(by_label) == {
        "A": set(),
        "B": {"COA_CONDITIONAL", "HEAVY_ADVANCE", "BRAND_MISSING", "VALIDITY_SOON"},
        "C": {"MOQ_ABOVE_REQUIRED", "FREIGHT_UNKNOWN", "HEAVY_ADVANCE", "OVER_BUDGET"},
        "D": {"TAX_UNCONFIRMED", "VERBAL_ONLY", "COA_CONDITIONAL", "VALIDITY_MISSING", "BRAND_MISSING"},
    }
    assert severity(d, "BRAND_MISSING") == Severity.INFO  # a named brand is not required for ethanol

    # A wins on terms and CoA although D is cheaper on paper.
    assert result.recommendation.quote_label == "A"
    assert [x.label for x in result.analyses] == ["A", "B", "C", "D"]


# ---------------------------------------------------------------------------
# PR-USP-1138: Nitrile gloves, 100 boxes, need-by 4 Dec 2026, budget Rs 35,000
# ---------------------------------------------------------------------------
def test_gloves_pr_usp_1138() -> None:
    result, by_label = run(GLOVES_REQUISITION, GLOVES_QUOTES)

    # A: 100 boxes x Rs 312 = 31,200; GST 5% = 1,560; free delivery. 31,200 + 1,560 = 32,760
    # B: Rs 2,690 per carton / 10 = Rs 269 per box x 100 = 26,900.
    #    Chat (GST 5%): 26,900 + 1,345 + transport 450 = 28,695.
    #    Proforma (GST 12%): 26,900 + 3,228 + 450 = 30,578 -> the worst case (and the PI's own total)
    # C: MOQ 15 cartons = 150 boxes > 100, so 150 x Rs 248 = 37,200; GST 5% = 1,860; F.O.R. 37,200 + 1,860 = 39,060
    # D: Rs 2.75 per glove x 100 = Rs 275 per box x 100 = 27,500; GST 5% = 1,375; vehicle 300.
    #    27,500 + 1,375 + 300 = 29,175
    assert_worst_case_totals(by_label, {"A": 32760, "B": 30578, "C": 39060, "D": 29175})

    b, c = by_label["B"], by_label["C"]
    assert b.costing.worst_case_index == 1  # the 12% proforma reading
    assert c.costing.moq_applies and c.costing.order_quantity == 150
    # If the MOQ were waived: 100 x 248 = 24,800 + 5% (1,240) = 26,040
    assert c.costing.scenarios[0].required_only.total_landed_inr == approx(26040)

    assert flag_codes(by_label) == {
        "A": set(),
        "B": {"EXPIRED", "CONTRADICTORY_TERMS", "HEAVY_ADVANCE", "BRAND_UNVERIFIED"},
        "C": {"MOQ_ABOVE_REQUIRED", "OVER_BUDGET", "BRAND_UNVERIFIED"},
        "D": {"BRAND_MISSING", "VERBAL_ONLY", "VALIDITY_MISSING"},
    }
    assert severity(b, "EXPIRED") == Severity.CRITICAL
    assert severity(by_label["D"], "BRAND_MISSING") == Severity.CRITICAL  # a named brand is required for gloves

    # The clean emailed quote wins although B and D are cheaper.
    assert result.recommendation.quote_label == "A"
    assert [x.label for x in result.analyses] == ["A", "C", "B", "D"]


# ---------------------------------------------------------------------------
# PR-MB-1143: Bacteriological peptone, 10 kg, need-by 15 Jan 2027, budget Rs 75,000
# ---------------------------------------------------------------------------
def test_peptone_pr_mb_1143() -> None:
    result, by_label = run(PEPTONE_REQUISITION, PEPTONE_QUOTES)

    # A (import): CIF 10 kg x EUR 44 x Rs 92 = 40,480. Customs duty 12% of CIF = 4,857.60.
    #    IGST 18% of (40,480 + 4,857.60 = 45,337.60) = 8,160.768. Clearance 8,000 and inland transport
    #    6,500 (engine defaults, not quoted). 40,480 + 4,857.60 + 8,160.768 + 8,000 + 6,500 = 67,998.368
    # B: 10 kg / 500 g = 20 packs x Rs 1,980 = 39,600; GST 18% = 7,128; free delivery. 39,600 + 7,128 = 46,728
    # C: 10 kg x Rs 4,200 = 42,000; GST 18% = 7,560; courier 650. 42,000 + 7,560 + 650 = 50,210
    assert_worst_case_totals(by_label, {"A": 67998.368, "B": 46728, "C": 50210})

    a, b = by_label["A"], by_label["B"]
    imported = a.costing.scenarios[0].commitment
    assert imported.goods_pre_tax_inr == approx(40480)
    assert imported.customs_duty_inr == approx(4857.60)
    assert imported.recoverable_tax_inr == approx(8160.77)
    assert (imported.clearance_inr, imported.inland_transport_inr) == (8000, 6500)
    assert a.delivery.on_time  # 4-6 weeks after payment -> by Tue 5 Jan 2027, ahead of 15 Jan
    assert b.costing.scenarios[0].commitment.packs == 20

    assert flag_codes(by_label) == {
        "A": {"IMPORT", "HEAVY_ADVANCE", "BRAND_UNVERIFIED"},
        "B": set(),
        "C": {"BRAND_MISSING", "COA_CONDITIONAL", "HEAVY_ADVANCE", "VALIDITY_SOON"},
    }

    # Clean cheapest-wins: B is the cheapest, verified brand, CoA every batch, credit, no flags.
    totals = {label: x.costing.worst_case_landed_inr for label, x in by_label.items()}
    assert min(totals, key=lambda label: totals[label] or 0.0) == "B"
    assert result.recommendation.quote_label == "B"
    assert [x.label for x in result.analyses] == ["B", "A", "C"]
