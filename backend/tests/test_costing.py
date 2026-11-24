import pytest

from backend.app.costing import cost_quote, describe_tax
from backend.app.models import PricingUnit, Quote, Requisition, TaxTreatment, Unit
from backend.app.seed import QUOTE_A, QUOTE_B, QUOTE_C, QUOTE_D, seed_requisition


def approx(x):
    return pytest.approx(x, abs=0.01)


def req(**kw) -> Requisition:
    base = dict(pr_number="PR-T", item_name="Test item", required_quantity=10, unit=Unit.KG, approved_budget=1_000_000)
    return Requisition(**(base | kw))


def quote(**kw) -> Quote:
    base = dict(supplier_name="Test supplier", price=100, pricing_unit=PricingUnit.PER_KG,
                tax_treatment=TaxTreatment.EXEMPT, freight_cost=0)
    return Quote(**(base | kw))


# ---------------------------------------------------------------------------
# Seed quotes (PR-USP-1147)
# ---------------------------------------------------------------------------
def test_seed_quote_a():
    c = cost_quote(seed_requisition(), QUOTE_A)
    assert c.comparable and not c.moq_applies and not c.incomplete
    assert len(c.scenarios) == 1
    b = c.scenarios[0].commitment
    assert b.quantity == 25 and b.packs == 50
    assert b.goods_pre_tax_inr == approx(192500)
    assert b.recoverable_tax_inr == approx(34650)
    assert b.freight_inr == 0 and not b.freight_unknown  # free-delivery threshold met
    assert b.total_landed_inr == approx(227150)
    assert b.cost_per_kg_landed == approx(9086)
    assert b.cost_per_kg_pre_tax == approx(7700)
    assert c.worst_case_landed_inr == approx(227150)
    assert c.budget_variance_inr == approx(27150)
    assert c.scenarios[0].description == "GST extra @ 18%"


def test_seed_quote_b_two_tax_readings():
    c = cost_quote(seed_requisition(), QUOTE_B)
    primary, alternate = c.scenarios
    assert primary.description == "GST inclusive @ 18%"
    assert primary.commitment.packs == 1
    assert primary.commitment.goods_pre_tax_inr == approx(152542.37)
    assert primary.commitment.recoverable_tax_inr == approx(27457.63)
    assert primary.commitment.freight_inr == approx(2500)
    assert primary.commitment.total_landed_inr == approx(182500)
    assert alternate.description == "GST extra @ 18%"
    assert alternate.commitment.goods_pre_tax_inr == approx(180000)
    assert alternate.commitment.recoverable_tax_inr == approx(32400)
    assert alternate.commitment.total_landed_inr == approx(214900)
    assert c.worst_case_index == 1
    assert c.worst_case_landed_inr == approx(214900)
    assert c.budget_variance_inr == approx(14900)


def test_seed_quote_c_import_with_moq():
    c = cost_quote(seed_requisition(), QUOTE_C)
    assert c.moq_applies and c.order_quantity == 50 and c.required_quantity == 25
    s = c.scenarios[0]
    assert s.description == "Import: customs 12% + IGST 18%"
    b = s.commitment
    assert b.quantity == 50 and b.packs == 2
    assert b.goods_pre_tax_inr == approx(327600)  # CIF: 50 kg x USD 78 x 84
    assert b.customs_duty_inr == approx(39312)
    assert b.recoverable_tax_inr == approx(66044.16)
    assert b.clearance_inr == approx(8000)
    assert b.inland_transport_inr == approx(6500)
    assert b.total_landed_inr == approx(447456.16)
    assert b.unit_cost_landed == approx(17898.25)  # per required kg
    assert b.cost_per_kg_landed == approx(17898.25)
    assert b.unit_cost_landed_per_ordered == approx(8949.12)  # per ordered kg
    assert s.required_only.quantity == 25
    assert s.required_only.total_landed_inr == approx(230978.08)
    assert c.budget_variance_inr == approx(247456.16)


def test_seed_quote_d_unknown_freight_and_alternate_rate():
    c = cost_quote(seed_requisition(), QUOTE_D)
    primary, alternate = c.scenarios
    assert primary.commitment.goods_pre_tax_inr == approx(152500)
    assert primary.commitment.recoverable_tax_inr == approx(7625)
    assert primary.commitment.total_landed_inr == approx(160125)
    assert primary.commitment.freight_unknown
    assert alternate.description == "GST extra @ 18%"
    assert alternate.commitment.recoverable_tax_inr == approx(27450)
    assert alternate.commitment.total_landed_inr == approx(179950)
    assert c.worst_case_index == 1
    assert c.incomplete
    assert c.budget_variance_inr == approx(-20050)


# ---------------------------------------------------------------------------
# Quantities: packs, drums, MOQ
# ---------------------------------------------------------------------------
def test_pack_rounding_25_2_kg_in_500_g_packs():
    q = quote(price=3850, pricing_unit=PricingUnit.PER_PACK, pack_size_value=500, pack_size_unit=Unit.G)
    c = cost_quote(req(required_quantity=25.2), q)
    b = c.scenarios[0].commitment
    assert b.packs == 51 and b.quantity == approx(25.5)
    assert b.goods_pre_tax_inr == approx(51 * 3850)
    assert b.unit_cost_landed_per_ordered == approx(51 * 3850 / 25.5)
    assert b.unit_cost_landed == approx(51 * 3850 / 25.2)  # per required kg
    assert c.scenarios[0].required_only.packs == 51


def test_per_drum_pricing():
    q = quote(price=10000, pricing_unit=PricingUnit.PER_DRUM, drum_size_kg=25)
    b = cost_quote(req(required_quantity=60), q).scenarios[0].commitment
    assert b.packs == 3 and b.quantity == 75
    assert b.goods_pre_tax_inr == approx(30000)


def test_per_drum_when_requisition_counts_drums():
    q = quote(price=10000, pricing_unit=PricingUnit.PER_DRUM, drum_size_kg=25)
    b = cost_quote(req(required_quantity=2, unit=Unit.DRUM), q).scenarios[0].commitment
    assert b.packs == 2 and b.goods_pre_tax_inr == approx(20000)
    assert b.cost_per_kg_landed is None  # requisition is not mass-based


def test_moq_in_grams_against_kg_requisition():
    c = cost_quote(req(required_quantity=2), quote(moq_quantity=5000, moq_unit=Unit.G))
    assert c.moq_applies and c.order_quantity == approx(5)
    assert c.scenarios[0].commitment.goods_pre_tax_inr == approx(500)
    assert c.scenarios[0].required_only.goods_pre_tax_inr == approx(200)

    below = cost_quote(req(required_quantity=2), quote(moq_quantity=500, moq_unit=Unit.G))
    assert not below.moq_applies and below.order_quantity == approx(2)


def test_moq_in_packs_converts_via_pack_size():
    q = quote(pricing_unit=PricingUnit.PER_PACK, pack_size_value=500, pack_size_unit=Unit.G,
              moq_quantity=30, moq_unit=Unit.PACK)
    c = cost_quote(req(required_quantity=10), q)
    assert c.moq_applies and c.order_quantity == approx(15)
    assert c.scenarios[0].commitment.packs == 30


# ---------------------------------------------------------------------------
# Money: FX, tax treatments, freight
# ---------------------------------------------------------------------------
def test_usd_price_converted_with_fx():
    q = quote(price=10, currency="USD", fx_rate_to_inr=84)
    b = cost_quote(req(required_quantity=5), q).scenarios[0].commitment
    assert b.goods_pre_tax_inr == approx(4200)
    assert b.total_landed_inr == approx(4200)  # exempt, no freight


def test_inclusive_gst_back_calculation():
    q = quote(price=118000, pricing_unit=PricingUnit.PER_UNIT, tax_treatment=TaxTreatment.INCLUSIVE_GST, gst_rate_pct=18)
    b = cost_quote(req(required_quantity=1, unit=Unit.UNIT), q).scenarios[0].commitment
    assert b.goods_pre_tax_inr == approx(100000)
    assert b.recoverable_tax_inr == approx(18000)
    assert b.total_landed_inr == approx(118000)


@pytest.mark.parametrize("treatment", [TaxTreatment.EXEMPT, TaxTreatment.UNSPECIFIED])
def test_exempt_and_unspecified_add_no_tax(treatment):
    s = cost_quote(req(), quote(tax_treatment=treatment)).scenarios[0]
    assert s.commitment.recoverable_tax_inr == 0
    assert s.commitment.total_landed_inr == approx(1000)
    assert s.gst_rate_pct is None


def test_import_uses_default_clearance_and_inland_transport():
    q = quote(price=1000, tax_treatment=TaxTreatment.IMPORT_DUTY_IGST, customs_duty_pct=10, igst_rate_pct=18)
    b = cost_quote(req(required_quantity=1), q).scenarios[0].commitment
    assert b.customs_duty_inr == approx(100)
    assert b.recoverable_tax_inr == approx(198)  # 18% of (1000 + 100)
    assert b.clearance_inr == approx(8000) and b.inland_transport_inr == approx(6500)
    assert b.total_landed_inr == approx(1000 + 100 + 198 + 8000 + 6500)


@pytest.mark.parametrize(("price", "freight"), [(49999, 1000), (50000, 0), (50001, 0)])
def test_free_freight_threshold(price, freight):
    q = quote(price=price, pricing_unit=PricingUnit.PER_UNIT, freight_cost=1000, freight_free_above_inr=50000)
    b = cost_quote(req(required_quantity=1, unit=Unit.UNIT), q).scenarios[0].commitment
    assert b.freight_inr == freight and not b.freight_unknown


def test_unknown_freight_is_excluded_and_marks_incomplete():
    c = cost_quote(req(), quote(freight_cost=None))
    b = c.scenarios[0].commitment
    assert b.freight_unknown and b.freight_inr == 0
    assert b.total_landed_inr == approx(1000)
    assert c.incomplete


def test_unknown_freight_below_threshold_is_unknown():
    q = quote(freight_cost=None, freight_free_above_inr=50000)
    assert cost_quote(req(), q).incomplete


# ---------------------------------------------------------------------------
# Scenarios and comparability
# ---------------------------------------------------------------------------
def test_alternate_defaults_to_primary_treatment_and_rate():
    only_rate = cost_quote(req(), quote(tax_treatment=TaxTreatment.EXCLUSIVE_GST, gst_rate_pct=5, alt_gst_rate_pct=18))
    assert [s.tax_treatment for s in only_rate.scenarios] == [TaxTreatment.EXCLUSIVE_GST] * 2
    assert [s.gst_rate_pct for s in only_rate.scenarios] == [5, 18]

    only_treatment = cost_quote(req(), quote(tax_treatment=TaxTreatment.INCLUSIVE_GST, gst_rate_pct=12,
                                             alt_tax_treatment=TaxTreatment.EXCLUSIVE_GST))
    alt = only_treatment.scenarios[1]
    assert alt.tax_treatment == TaxTreatment.EXCLUSIVE_GST and alt.gst_rate_pct == 12
    assert alt.description == "GST extra @ 12%"


def test_worst_case_tie_keeps_primary():
    c = cost_quote(req(), quote(alt_tax_treatment=TaxTreatment.UNSPECIFIED))  # both readings add no tax
    assert c.worst_case_index == 0


def test_unit_mismatch_litres_vs_per_kg():
    c = cost_quote(req(unit=Unit.L), quote(pricing_unit=PricingUnit.PER_KG))
    assert not c.comparable
    assert c.scenarios == []
    assert c.worst_case_landed_inr is None and c.budget_variance_inr is None
    assert "per kg" in c.notes[0] and "L" in c.notes[0]


def test_per_pack_without_pack_size_is_not_comparable():
    c = cost_quote(req(), quote(pricing_unit=PricingUnit.PER_PACK))
    assert not c.comparable and "size is not stated" in c.notes[0]


def test_describe_tax():
    q = quote(customs_duty_pct=12, igst_rate_pct=18)
    assert describe_tax(q, TaxTreatment.EXCLUSIVE_GST, 18) == "GST extra @ 18%"
    assert describe_tax(q, TaxTreatment.INCLUSIVE_GST, 12.5) == "GST inclusive @ 12.5%"
    assert describe_tax(q, TaxTreatment.IMPORT_DUTY_IGST, 18) == "Import: customs 12% + IGST 18%"
    assert describe_tax(q, TaxTreatment.EXEMPT, 18) == "GST exempt"
    assert describe_tax(q, TaxTreatment.UNSPECIFIED, 18) == "Tax not specified"
