"""Landed-cost build-up for one quote: quantities, tax scenarios, freight and unit costs.

All arithmetic is done at full precision; money is rounded to 2 dp only on output.
Recoverable tax (GST / import IGST) is added to the cash outflow and reported separately
as potential input tax credit — it is never subtracted from a total.
"""

from __future__ import annotations

from backend.app import units
from backend.app.models import (
    CostBreakdown,
    CostScenario,
    PricingUnit,
    Quote,
    QuoteCosting,
    Requisition,
    TaxTreatment,
    Unit,
)
from backend.app.summary import format_pct, format_qty_unit

DEFAULT_CLEARANCE_INR = 8000.0  # imports: customs clearance / CHA fee when the quote is silent
DEFAULT_INLAND_TRANSPORT_INR = 6500.0  # imports: port -> site transport when the quote is silent

# Pack-priced quotes and the count unit a requisition would use for them.
_COUNT_UNIT = {PricingUnit.PER_PACK: Unit.PACK, PricingUnit.PER_DRUM: Unit.DRUM}


def _money(amount: float) -> float:
    return round(amount, 2)


# ---------------------------------------------------------------------------
# Descriptions
# ---------------------------------------------------------------------------
def pricing_label(quote: Quote, requisition_unit: Unit) -> str:
    """"per kg", "per 500 g pack", "per 25 kg drum"."""
    if quote.pricing_unit == PricingUnit.PER_KG:
        return "per kg"
    if quote.pricing_unit == PricingUnit.PER_PACK:
        if quote.pack_size_value and quote.pack_size_unit:
            return f"per {format_qty_unit(quote.pack_size_value, quote.pack_size_unit)} pack"
        return "per pack"
    if quote.pricing_unit == PricingUnit.PER_DRUM:
        if quote.drum_size_kg:
            return f"per {format_qty_unit(quote.drum_size_kg, Unit.KG)} drum"
        return "per drum"
    return f"per {requisition_unit.value}"


def describe_tax(quote: Quote, treatment: TaxTreatment, gst_rate_pct: float) -> str:
    """Scenario description, e.g. "GST extra @ 18%"."""
    if treatment == TaxTreatment.EXCLUSIVE_GST:
        return f"GST extra @ {format_pct(gst_rate_pct)}"
    if treatment == TaxTreatment.INCLUSIVE_GST:
        return f"GST inclusive @ {format_pct(gst_rate_pct)}"
    if treatment == TaxTreatment.IMPORT_DUTY_IGST:
        return f"Import: customs {format_pct(quote.customs_duty_pct)} + IGST {format_pct(quote.igst_rate_pct)}"
    if treatment == TaxTreatment.EXEMPT:
        return "GST exempt"
    return "Tax not specified"


# ---------------------------------------------------------------------------
# Quantities
# ---------------------------------------------------------------------------
def _pack(quote: Quote) -> tuple[float, Unit] | None:
    """The pack or drum size the supplier sells in, if the quote states one.

    PER_DRUM quotes use drum_size_kg; otherwise (or if that is missing) the pack size.
    """
    drum = quote.drum_size_kg
    if quote.pricing_unit == PricingUnit.PER_DRUM and drum is not None and drum > 0:
        return drum, Unit.KG
    size, size_unit = quote.pack_size_value, quote.pack_size_unit
    if size is not None and size > 0 and size_unit is not None:
        return size, size_unit
    return None


def _round_to_packs(qty: float, unit: Unit, quote: Quote) -> tuple[float, int | None]:
    """Round an order quantity (requisition unit) up to whole packs; packs=None if loose."""
    if unit in (Unit.PACK, Unit.DRUM):  # requisition already counts packs/drums
        n = units.whole_packs(qty, 1)
        return float(n), n
    pack = _pack(quote)
    if pack is not None:
        rounded = units.round_up_to_packs(qty, unit, *pack)
        if rounded is not None:
            return rounded
    return qty, None  # sold loose, or the pack size is in an unrelated unit


def _to_requisition_unit(qty: float, from_unit: Unit, unit: Unit, quote: Quote) -> float | None:
    """Convert e.g. an MOQ into the requisition unit; "10 packs" goes via the pack size."""
    direct = units.convert(qty, from_unit, unit)
    if direct is not None:
        return direct
    pack = _pack(quote)
    if from_unit in (Unit.PACK, Unit.DRUM) and pack is not None:
        return units.convert(qty * pack[0], pack[1], unit)
    return None


def _billable_units(quote: Quote, qty: float, unit: Unit) -> float | None:
    """How many pricing units the supplier charges for `qty`; None if units don't connect."""
    if quote.pricing_unit == PricingUnit.PER_UNIT:
        return qty  # price is per one requisition unit
    if quote.pricing_unit == PricingUnit.PER_KG:
        return units.convert(qty, unit, Unit.KG)
    # PER_PACK / PER_DRUM: charged per whole pack or drum.
    if unit == _COUNT_UNIT[quote.pricing_unit]:  # requisition already counts packs/drums
        return float(units.whole_packs(qty, 1))
    pack = _pack(quote)
    if pack is None:
        return None
    packs = units.packs_needed(qty, unit, *pack)
    return None if packs is None else float(packs)


def _mismatch_reason(quote: Quote, unit: Unit) -> str:
    if quote.pricing_unit in _COUNT_UNIT and _pack(quote) is None:
        return f"Priced per {_COUNT_UNIT[quote.pricing_unit].value} but its size is not stated."
    return (
        f"Priced {pricing_label(quote, unit)} but the requisition is in {unit.value}; "
        "the quantities cannot be converted."
    )


# ---------------------------------------------------------------------------
# Cost build-up
# ---------------------------------------------------------------------------
def _freight(quote: Quote, pre_tax: float) -> tuple[float, bool]:
    """(freight INR, unknown?). Free above the threshold; None means "at actual" / not stated."""
    if quote.freight_free_above_inr is not None and pre_tax >= quote.freight_free_above_inr:
        return 0.0, False
    if quote.freight_cost is None:
        return 0.0, True  # excluded from totals and flagged
    return quote.freight_cost, False


def _breakdown(
    requisition: Requisition,
    quote: Quote,
    qty: float,
    packs: int | None,
    treatment: TaxTreatment,
    gst_rate_pct: float,
) -> CostBreakdown:
    billable = _billable_units(quote, qty, requisition.unit)
    assert billable is not None  # cost_quote checks comparability first
    value_inr = billable * quote.price * quote.fx_rate_to_inr  # as quoted, before tax treatment

    duty = clearance = inland = 0.0
    rate = gst_rate_pct / 100
    if treatment == TaxTreatment.INCLUSIVE_GST:
        pre_tax = value_inr / (1 + rate)  # back out the GST already inside the price
        tax = value_inr - pre_tax
    elif treatment == TaxTreatment.EXCLUSIVE_GST:
        pre_tax = value_inr
        tax = pre_tax * rate
    elif treatment == TaxTreatment.IMPORT_DUTY_IGST:
        pre_tax = value_inr  # CIF value in INR
        duty = pre_tax * quote.customs_duty_pct / 100  # basic customs duty: not recoverable
        tax = (pre_tax + duty) * quote.igst_rate_pct / 100  # import IGST is levied on CIF + duty
        clearance = quote.clearance_fee_inr if quote.clearance_fee_inr is not None else DEFAULT_CLEARANCE_INR
        inland = quote.inland_transport_inr if quote.inland_transport_inr is not None else DEFAULT_INLAND_TRANSPORT_INR
    else:  # EXEMPT or UNSPECIFIED: no tax added (UNSPECIFIED is flagged)
        pre_tax = value_inr
        tax = 0.0

    freight, freight_unknown = _freight(quote, pre_tax)
    total = pre_tax + duty + tax + freight + clearance + inland

    required = requisition.required_quantity
    required_kg = units.convert(required, requisition.unit, Unit.KG)  # None unless mass-based
    return CostBreakdown(
        quantity=round(qty, 6),
        packs=packs,
        goods_pre_tax_inr=_money(pre_tax),
        customs_duty_inr=_money(duty),
        recoverable_tax_inr=_money(tax),
        freight_inr=_money(freight),
        clearance_inr=_money(clearance),
        inland_transport_inr=_money(inland),
        total_landed_inr=_money(total),
        freight_unknown=freight_unknown,
        unit_cost_pre_tax=_money(pre_tax / required),
        unit_cost_landed=_money(total / required),
        unit_cost_landed_per_ordered=_money(total / qty),
        cost_per_kg_pre_tax=None if required_kg is None else _money(pre_tax / required_kg),
        cost_per_kg_landed=None if required_kg is None else _money(total / required_kg),
    )


def _tax_scenarios(quote: Quote) -> list[tuple[str, TaxTreatment, float]]:
    """Primary reading, plus an alternate when the quote's tax terms are unclear."""
    scenarios = [("primary", quote.tax_treatment, quote.gst_rate_pct)]
    if quote.alt_tax_treatment is not None or quote.alt_gst_rate_pct is not None:
        scenarios.append((
            "alternate",
            quote.alt_tax_treatment or quote.tax_treatment,
            quote.alt_gst_rate_pct if quote.alt_gst_rate_pct is not None else quote.gst_rate_pct,
        ))
    return scenarios


def _scenario_rate(quote: Quote, treatment: TaxTreatment, gst_rate_pct: float) -> float | None:
    """Rate shown on the scenario: GST rate, IGST rate for imports, None when no tax applies."""
    if treatment == TaxTreatment.IMPORT_DUTY_IGST:
        return quote.igst_rate_pct
    if treatment in (TaxTreatment.EXCLUSIVE_GST, TaxTreatment.INCLUSIVE_GST):
        return gst_rate_pct
    return None


def cost_quote(requisition: Requisition, quote: Quote) -> QuoteCosting:
    unit = requisition.unit
    required = requisition.required_quantity

    def not_comparable(reason: str) -> QuoteCosting:
        return QuoteCosting(comparable=False, required_quantity=required, order_quantity=required, notes=[reason])

    # 1. Commitment quantity = max(required, MOQ), in the requisition unit.
    moq: float | None = None
    if quote.moq_quantity is not None and quote.moq_quantity > 0:
        moq_unit = quote.moq_unit or unit
        moq = _to_requisition_unit(quote.moq_quantity, moq_unit, unit, quote)
        if moq is None:
            return not_comparable(f"MOQ is in {moq_unit.value} but the requisition is in {unit.value}; cannot convert.")
    moq_applies = moq is not None and moq > required
    commit_qty = max(required, moq or 0.0)

    # 2. Round both quantities up to whole packs/drums when the quote sells in packs.
    order_qty, order_packs = _round_to_packs(commit_qty, unit, quote)
    req_qty, req_packs = _round_to_packs(required, unit, quote)
    if _billable_units(quote, order_qty, unit) is None:
        return not_comparable(_mismatch_reason(quote, unit))

    # 3. One cost breakdown per tax reading, at commitment and at required quantity.
    scenarios = [
        CostScenario(
            name=name,  # type: ignore[arg-type]
            description=describe_tax(quote, treatment, rate),
            tax_treatment=treatment,
            gst_rate_pct=_scenario_rate(quote, treatment, rate),
            commitment=_breakdown(requisition, quote, order_qty, order_packs, treatment, rate),
            required_only=_breakdown(requisition, quote, req_qty, req_packs, treatment, rate),
        )
        for name, treatment, rate in _tax_scenarios(quote)
    ]
    # max() keeps the first on a tie, so the primary reading wins ties.
    worst_index = max(range(len(scenarios)), key=lambda i: scenarios[i].commitment.total_landed_inr)
    worst = scenarios[worst_index].commitment.total_landed_inr
    incomplete = any(s.commitment.freight_unknown or s.required_only.freight_unknown for s in scenarios)

    notes: list[str] = []
    if moq_applies:
        notes.append(
            f"MOQ is above the {format_qty_unit(required, unit)} required: ranking and budget use the "
            f"{format_qty_unit(order_qty, unit)} commitment; the required-quantity cost is shown as 'if MOQ waived'."
        )
    if order_packs is not None and order_qty != commit_qty:
        notes.append(f"Order rounded up to {order_packs} whole packs ({format_qty_unit(order_qty, unit)}).")
    if len(scenarios) == 2:
        notes.append(f"Two tax readings costed; the {scenarios[worst_index].name} reading is the higher and is used.")
    if incomplete:
        notes.append("Freight is not quantified, so it is excluded from the landed totals.")

    return QuoteCosting(
        comparable=True,
        required_quantity=required,
        order_quantity=round(order_qty, 6),
        moq_applies=moq_applies,
        scenarios=scenarios,
        worst_case_index=worst_index,
        worst_case_landed_inr=worst,
        budget_variance_inr=_money(worst - requisition.approved_budget),
        incomplete=incomplete,
        notes=notes,
    )
