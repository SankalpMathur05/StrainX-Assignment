from datetime import date, timedelta

import pytest

from backend.app.engine import compare
from backend.app.models import (
    BrandStatus,
    CoaStatus,
    CompareRequest,
    DeliveryEstimate,
    PricingUnit,
    Quote,
    Requisition,
    SourceChannel,
    TaxTreatment,
    Unit,
    Weights,
)
from backend.app.scoring import delivery_score, payment_score, quality_score, weighted_score
from backend.app.seed import QUOTE_B, QUOTE_C, seed_quotes, seed_requisition

REF = date(2026, 11, 24)


def approx(x):
    return pytest.approx(x, abs=0.01)


def req(**kw) -> Requisition:
    base = dict(pr_number="PR-T", item_name="Item", required_quantity=10, unit=Unit.KG,
                need_by_date=REF + timedelta(days=12), approved_budget=1_000_000,
                coa_mandatory=True, require_named_brand=False)
    return Requisition(**(base | kw))


def quote(label: str, **kw) -> Quote:
    base = dict(label=label, supplier_name=f"Supplier {label}", price=100, pricing_unit=PricingUnit.PER_KG,
                tax_treatment=TaxTreatment.EXEMPT, freight_cost=0, brand_name="Acme",
                brand_status=BrandStatus.VERIFIED, coa_status=CoaStatus.EVERY_BATCH,
                source_channel=SourceChannel.EMAIL, lead_time_min_days=2, lead_time_max_days=2,
                credit_days=30, valid_until=REF + timedelta(days=30))
    return Quote(**(base | kw))


def run(quotes: list[Quote], r: Requisition | None = None, weights: Weights | None = None):
    return compare(CompareRequest(requisition=r or req(), quotes=quotes, weights=weights or Weights()), REF)


@pytest.fixture(scope="module")
def seed_result():
    return compare(CompareRequest(requisition=seed_requisition(), quotes=seed_quotes()))


# ---------------------------------------------------------------------------
# Seed: PR-USP-1147 at default weights 30/25/10/35
# ---------------------------------------------------------------------------
def test_seed_ranking_and_scores(seed_result):
    by_label = {a.label: a for a in seed_result.analyses}
    assert [a.label for a in seed_result.analyses] == ["A", "D", "B", "C"]
    assert [a.rank for a in seed_result.analyses] == [1, 2, 3, 4]
    assert seed_result.reference_date == REF
    expected = {
        # label: (price, delivery, payment, quality, penalty, final, criticals, warnings)
        "A": (79.22, 100, 100, 85, 10, 78.52, 0, 2),
        "B": (83.74, 40, 0, 35, 85, -37.63, 2, 5),
        "C": (40.22, 0, 0, 60, 75, -41.94, 2, 3),
        "D": (100, 100, 35, 15, 60, 3.75, 1, 6),
    }
    for label, (price, delivery, payment, quality, penalty, final, crit, warn) in expected.items():
        a = by_label[label]
        s = a.score
        assert (s.price, s.delivery, s.payment, s.quality) == (approx(price), approx(delivery), approx(payment), approx(quality))
        assert s.penalty == penalty and s.final == approx(final)
        assert s.display == approx(min(100, max(0, final)))
        assert (a.critical_count, a.warning_count) == (crit, warn)


def test_seed_recommendation(seed_result):
    rec = seed_result.recommendation
    assert (rec.quote_label, rec.supplier_name, rec.runner_up_label) == ("A", "Narmada Lab Supplies", "D")
    assert rec.rationale == (
        "Narmada Lab Supplies (Quote A) ranks first (score 78.5/100): Rs 2,27,150 landed for 25 kg "
        "(Rs 27,150 over budget; includes Rs 34,650 GST that may be claimable as input tax credit), "
        "arrives Fri 27 Nov — 8 days before the need-by date, 30 days credit, CoA with every batch."
    )
    assert len(rec.caveats) == 2  # A's two warnings, no criticals
    assert any("Mon" in g and "Sat" in g for g in seed_result.global_assumptions)


def test_reference_date_on_request_overrides_default():
    request = CompareRequest(requisition=seed_requisition(), quotes=seed_quotes(), reference_date=date(2026, 11, 10))
    result = compare(request)
    assert result.reference_date == date(2026, 11, 10)
    b = next(a for a in result.analyses if a.label == "B")
    assert "EXPIRED" not in {f.code for f in b.flags}  # valid until 15 Nov


# ---------------------------------------------------------------------------
# Criterion formulas
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(("buffer", "expected"), [(None, 0), (-1, 0), (0, 40), (2, 70), (4, 100), (10, 100)])
def test_delivery_score(buffer, expected):
    assert delivery_score(DeliveryEstimate(buffer_days=buffer)) == expected


@pytest.mark.parametrize(
    ("advance", "pre_delivery", "credit", "expected"),
    [(0, 0, 30, 100), (0, 0, 60, 100), (0, 0, 15, 85), (50, 50, 0, 35), (30, 100, 0, 0), (0, 0, 0, 70)],
)
def test_payment_score(advance, pre_delivery, credit, expected):
    q = quote("X", advance_pct=advance, pre_delivery_pct=pre_delivery, credit_days=credit)
    assert payment_score(q) == approx(expected)


@pytest.mark.parametrize(
    ("brand", "coa", "source", "expected"),
    [(BrandStatus.VERIFIED, CoaStatus.EVERY_BATCH, SourceChannel.EMAIL, 100),
     (BrandStatus.NAMED_UNVERIFIED, CoaStatus.WITH_MATERIAL, SourceChannel.PDF, 60),
     (BrandStatus.MISSING, CoaStatus.ON_REQUEST_OR_CONDITIONAL, SourceChannel.PHONE, 15),
     (BrandStatus.VERIFIED, CoaStatus.MISSING_OR_UNCLEAR, SourceChannel.WHATSAPP, 60)],
)
def test_quality_score(brand, coa, source, expected):
    assert quality_score(quote("X", brand_status=brand, coa_status=coa, source_channel=source)) == expected


def test_all_zero_weights_fall_back_to_equal_weights():
    scores = {"price": 80, "delivery": 40, "payment": 100, "quality": 20}
    assert weighted_score(scores, Weights(price=0, delivery=0, payment=0, quality=0)) == approx(60)
    result = run([quote("A")], weights=Weights(price=0, delivery=0, payment=0, quality=0))
    s = result.analyses[0].score
    assert s.weighted == approx((s.price + s.delivery + s.payment + s.quality) / 4)
    assert "equal weights" in result.global_assumptions[-1]


def test_penalty_is_30_per_critical_and_5_per_warning():
    # One CRITICAL (expired) + one WARNING (verbal only) = 35 points.
    q = quote("A", valid_until=REF - timedelta(days=1), source_channel=SourceChannel.PHONE)
    s = run([q]).analyses[0].score
    assert s.penalty == 35
    assert s.final == approx(s.weighted - 35)


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------
def test_weights_flip_the_winner():
    cheap_slow = quote("C", price=100, lead_time_min_days=9, lead_time_max_days=9)  # buffer 3 -> 85
    fast_pricey = quote("F", price=150, lead_time_min_days=1, lead_time_max_days=1)  # buffer 11 -> 100
    price_only = run([cheap_slow, fast_pricey], weights=Weights(price=100, delivery=0, payment=0, quality=0))
    delivery_only = run([cheap_slow, fast_pricey], weights=Weights(price=0, delivery=100, payment=0, quality=0))
    assert [a.label for a in price_only.analyses] == ["C", "F"]
    assert [a.label for a in delivery_only.analyses] == ["F", "C"]
    assert price_only.analyses[1].score.price == approx(100 * 1000 / 1500)


def test_ties_break_on_lower_landed_cost_then_label():
    # Identical except price; price weight 0 so the weighted scores tie.
    zero_price = Weights(price=0, delivery=50, payment=25, quality=25)
    result = run([quote("A", price=120), quote("B", price=100)], weights=zero_price)
    assert [a.label for a in result.analyses] == ["B", "A"]
    result = run([quote("B"), quote("A")], weights=zero_price)
    assert [a.label for a in result.analyses] == ["A", "B"]


def test_unit_mismatch_quote_scores_zero_on_price_and_ranks_last():
    result = run([quote("A"), quote("M", pricing_unit=PricingUnit.PER_PACK)])  # no pack size
    mismatch = result.analyses[-1]
    assert mismatch.label == "M" and not mismatch.costing.comparable
    assert mismatch.score.price == 0
    assert "UNIT_MISMATCH" in {f.code for f in mismatch.flags}


def test_unlabelled_quotes_are_numbered():
    result = run([quote(""), quote("", price=90)])
    assert sorted(a.label for a in result.analyses) == ["1", "2"]


# ---------------------------------------------------------------------------
# Recommendation when the top pick has critical issues
# ---------------------------------------------------------------------------
def test_all_quotes_critical_says_least_risk_option():
    result = compare(CompareRequest(requisition=seed_requisition(), quotes=[QUOTE_B, QUOTE_C]))
    rec = result.recommendation
    assert rec.quote_label == "B" and rec.runner_up_label == "C"
    assert "No quote is free of critical issues" in rec.rationale
    assert "least-risk option" in rec.rationale
    assert len(rec.caveats) == 7  # B's 2 critical + 5 warning messages


def test_top_pick_with_critical_names_the_clean_alternative():
    expired_cheap = quote("X", price=50, valid_until=REF - timedelta(days=1))
    clean_pricey = quote("Y", price=100)
    result = run([expired_cheap, clean_pricey], weights=Weights(price=100, delivery=0, payment=0, quality=0))
    rec = result.recommendation
    assert rec.quote_label == "X"  # 100 - 30 = 70 beats 50
    assert "Quote Y has none but ranks lower" in rec.rationale
