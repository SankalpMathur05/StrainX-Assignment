from datetime import date, timedelta

import pytest

from backend.app.costing import cost_quote
from backend.app.dates import estimate_delivery
from backend.app.flags import build_assumptions, build_facts, build_flags, build_questions
from backend.app.models import (
    BrandStatus,
    CoaStatus,
    Flag,
    PricingUnit,
    Quote,
    Requisition,
    Severity,
    SourceChannel,
    TaxTreatment,
    Unit,
)
from backend.app.seed import QUOTE_A, QUOTE_B, QUOTE_C, QUOTE_D, seed_requisition

REF = date(2026, 11, 24)
CRIT, WARN, INFO = Severity.CRITICAL, Severity.WARNING, Severity.INFO


def req(**kw) -> Requisition:
    base = dict(pr_number="PR-T", item_name="Item", required_quantity=10, unit=Unit.KG,
                need_by_date=REF + timedelta(days=10), approved_budget=1_000_000,
                coa_mandatory=True, require_named_brand=True)
    return Requisition(**(base | kw))


def clean_quote(**kw) -> Quote:
    """A quote that raises no flags against req()."""
    base = dict(supplier_name="Clean Co", price=100, pricing_unit=PricingUnit.PER_KG,
                tax_treatment=TaxTreatment.EXCLUSIVE_GST, gst_rate_pct=18, freight_cost=0,
                brand_name="Acme", brand_status=BrandStatus.VERIFIED, coa_status=CoaStatus.EVERY_BATCH,
                source_channel=SourceChannel.EMAIL, lead_time_min_days=2, lead_time_max_days=2,
                credit_days=30, valid_until=REF + timedelta(days=30))
    return Quote(**(base | kw))


def flags_for(q: Quote, r: Requisition | None = None) -> list[Flag]:
    r = r or req()
    return build_flags(r, q, cost_quote(r, q), estimate_delivery(q, r.need_by_date, REF), REF)


def codes(q: Quote, r: Requisition | None = None) -> dict[str, Severity]:
    return {f.code: f.severity for f in flags_for(q, r)}


# ---------------------------------------------------------------------------
# Seed quotes
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("q", "expected"),
    [
        (QUOTE_A, {"BRAND_UNVERIFIED": WARN, "OVER_BUDGET": WARN, "VALIDITY_SOON": INFO}),
        (QUOTE_B, {"EXPIRED": CRIT, "BRAND_MISSING": CRIT, "TIGHT_DELIVERY": WARN, "HEAVY_ADVANCE": WARN,
                   "COA_CONDITIONAL": WARN, "CONTRADICTORY_TERMS": WARN, "OVER_BUDGET": WARN}),
        (QUOTE_C, {"LATE_DELIVERY": CRIT, "BRAND_MISSING": CRIT, "MOQ_ABOVE_REQUIRED": WARN,
                   "HEAVY_ADVANCE": WARN, "OVER_BUDGET": WARN, "IMPORT": INFO}),
        (QUOTE_D, {"BRAND_MISSING": CRIT, "COA_CONDITIONAL": WARN, "VALIDITY_MISSING": WARN, "VERBAL_ONLY": WARN,
                   "FREIGHT_UNKNOWN": WARN, "HEAVY_ADVANCE": WARN, "TAX_UNCONFIRMED": WARN}),
    ],
    ids=["A", "B", "C", "D"],
)
def test_seed_flags(q, expected):
    flags = flags_for(q, seed_requisition())
    assert {f.code: f.severity for f in flags} == expected
    assert len(flags) == len(expected)  # no duplicate codes
    assert [f.severity for f in flags] == sorted((f.severity for f in flags), key=[CRIT, WARN, INFO].index)


def test_seed_messages_are_concrete():
    by_code = {f.code: f for f in flags_for(QUOTE_C, seed_requisition())}
    assert "Rs 2,16,478.08" in by_code["MOQ_ABOVE_REQUIRED"].message  # 4,47,456.16 - 2,30,978.08
    assert "25 kg surplus" in by_code["MOQ_ABOVE_REQUIRED"].message
    assert "Rs 2,47,456.16 over" in by_code["OVER_BUDGET"].message
    assert "Tue 29 Dec 2026" in by_code["LATE_DELIVERY"].message
    a = {f.code: f for f in flags_for(QUOTE_A, seed_requisition())}
    assert "Mon 30 Nov 2026 (6 days left)" in a["VALIDITY_SOON"].message


def test_clean_quote_has_no_flags():
    assert flags_for(clean_quote()) == []


# ---------------------------------------------------------------------------
# Each rule
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("valid_until", "expected"),
    [(REF - timedelta(days=1), {"EXPIRED": CRIT}), (None, {"VALIDITY_MISSING": WARN}),
     (REF, {"VALIDITY_SOON": INFO}), (REF + timedelta(days=7), {"VALIDITY_SOON": INFO}),
     (REF + timedelta(days=8), {})],
)
def test_validity(valid_until, expected):
    assert codes(clean_quote(valid_until=valid_until)) == expected


@pytest.mark.parametrize(
    ("low", "high", "expected"),
    [(None, None, {"LEAD_TIME_MISSING": WARN}),
     (11, 11, {"LATE_DELIVERY": CRIT}),  # earliest after need-by
     (5, 15, {"DELIVERY_RANGE_RISK": WARN}),  # earliest on time, latest late
     (9, 9, {"TIGHT_DELIVERY": WARN}),  # 1 day buffer
     (10, 10, {"TIGHT_DELIVERY": WARN}),  # arrives on the need-by date
     (8, 8, {})],  # 2 days buffer
)
def test_delivery(low, high, expected):
    assert codes(clean_quote(lead_time_min_days=low, lead_time_max_days=high)) == expected


def test_moq_above_required_message_has_surplus_and_extra_cost():
    flags = flags_for(clean_quote(moq_quantity=20, moq_unit=Unit.KG))
    assert [f.code for f in flags] == ["MOQ_ABOVE_REQUIRED"]
    assert "10 kg surplus" in flags[0].message
    assert "Rs 1,180" in flags[0].message  # 10 kg x Rs 100 x 1.18
    assert flags[0].question == "Can you waive the MOQ and supply 10 kg?"


@pytest.mark.parametrize(
    ("status", "mandatory", "expected"),
    [(CoaStatus.MISSING_OR_UNCLEAR, True, {"COA_MISSING": CRIT}),
     (CoaStatus.WITH_MATERIAL, True, {"COA_CONDITIONAL": WARN}),
     (CoaStatus.ON_REQUEST_OR_CONDITIONAL, True, {"COA_CONDITIONAL": WARN}),
     (CoaStatus.MISSING_OR_UNCLEAR, False, {})],
)
def test_coa(status, mandatory, expected):
    assert codes(clean_quote(coa_status=status), req(coa_mandatory=mandatory)) == expected


@pytest.mark.parametrize(
    ("advance", "pre_delivery", "expected"),
    [(50, 0, {"HEAVY_ADVANCE": WARN}), (30, 100, {"HEAVY_ADVANCE": WARN}),
     (30, 0, {"PARTIAL_ADVANCE": INFO}), (0, 0, {})],
)
def test_payment(advance, pre_delivery, expected):
    assert codes(clean_quote(advance_pct=advance, pre_delivery_pct=pre_delivery)) == expected


def test_contradictions_take_precedence_over_tax_unconfirmed():
    q = clean_quote(alt_tax_treatment=TaxTreatment.INCLUSIVE_GST, contradictions=["Chat says incl GST; PDF says extra."])
    flags = flags_for(q)
    assert {f.code for f in flags} == {"CONTRADICTORY_TERMS"}
    assert "Rs 1,180" in flags[0].message and "Rs 1,000" in flags[0].message  # both readings shown


@pytest.mark.parametrize(
    "kw",
    [{"alt_gst_rate_pct": 5}, {"alt_tax_treatment": TaxTreatment.INCLUSIVE_GST},
     {"tax_treatment": TaxTreatment.UNSPECIFIED}],
)
def test_tax_unconfirmed(kw):
    assert codes(clean_quote(**kw)) == {"TAX_UNCONFIRMED": WARN}


@pytest.mark.parametrize(
    ("brand_name", "status", "required", "expected"),
    [(None, BrandStatus.MISSING, True, {"BRAND_MISSING": CRIT}),
     ("   ", BrandStatus.NAMED_UNVERIFIED, True, {"BRAND_MISSING": CRIT}),  # blank name counts as missing
     (None, BrandStatus.MISSING, False, {"BRAND_MISSING": INFO}),
     ("BioPure", BrandStatus.NAMED_UNVERIFIED, True, {"BRAND_UNVERIFIED": WARN}),
     ("BioPure", BrandStatus.NAMED_UNVERIFIED, False, {})],
)
def test_brand(brand_name, status, required, expected):
    q = clean_quote(brand_name=brand_name, brand_status=status)
    assert codes(q, req(require_named_brand=required)) == expected


def test_over_budget():
    flags = flags_for(clean_quote(), req(approved_budget=1000))
    assert [(f.code, f.severity) for f in flags] == [("OVER_BUDGET", WARN)]
    assert "Rs 180 over the approved budget of Rs 1,000" in flags[0].message


def test_verbal_freight_import_and_unit_mismatch():
    assert codes(clean_quote(source_channel=SourceChannel.PHONE)) == {"VERBAL_ONLY": WARN}
    assert codes(clean_quote(freight_cost=None)) == {"FREIGHT_UNKNOWN": WARN}
    assert codes(clean_quote(tax_treatment=TaxTreatment.IMPORT_DUTY_IGST)) == {"IMPORT": INFO}
    assert codes(clean_quote(), req(unit=Unit.L)) == {"UNIT_MISMATCH": CRIT}


def test_questions_are_deduplicated_in_order():
    flags = [Flag(code="X", severity=CRIT, message="m", question="Q1"),
             Flag(code="Y", severity=WARN, message="m", question="Q2"),
             Flag(code="Z", severity=WARN, message="m", question="Q1"),
             Flag(code="I", severity=INFO, message="m")]
    assert build_questions(flags) == ["Q1", "Q2"]


# ---------------------------------------------------------------------------
# Facts and assumptions
# ---------------------------------------------------------------------------
def _assumptions(q: Quote) -> list[str]:
    r = seed_requisition()
    return build_assumptions(q, cost_quote(r, q), estimate_delivery(q, r.need_by_date, REF))


def test_facts_state_what_the_quote_says():
    facts = build_facts(seed_requisition(), QUOTE_A)
    assert "Price: Rs 3,850 per 500 g pack, delivered" in facts
    assert "Tax: GST extra @ 18%" in facts
    assert "Lead time: 3 working days from PO" in facts
    assert "Payment: 30 days credit from date of invoice" in facts
    assert "Validity: until Mon 30 Nov 2026" in facts
    c_facts = build_facts(seed_requisition(), QUOTE_C)
    assert "MOQ: 50 kg" in c_facts and "Lead time: 28-35 calendar days from PO" in c_facts
    assert any(f.startswith("Price: USD 78.00 per kg") for f in c_facts)


def test_assumptions_record_what_the_engine_assumed():
    b = _assumptions(QUOTE_B)
    assert "Payment made on Tue 24 Nov 2026; lead time counted from then." in b
    assert "1 calendar day(s) of transit added after dispatch." in b
    assert "Primary reading: inclusive price back-calculated at GST 18%." in b
    assert QUOTE_B.notes in b
    assert any("judged on the later date" in a for a in _assumptions(QUOTE_C))
    assert "Unknown freight is excluded from the landed totals (flagged)." in _assumptions(QUOTE_D)

    no_defaults = QUOTE_C.model_copy(update={"clearance_fee_inr": None, "inland_transport_inr": None})
    c = _assumptions(no_defaults)
    assert "Customs clearance not quoted: default Rs 8,000 used." in c
    assert "Port-to-site transport not quoted: default Rs 6,500 used." in c
