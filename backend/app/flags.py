"""Deterministic risk / ambiguity flags, plus each quote's facts, assumptions and questions.

Facts = what the quote itself states. Assumptions = what the engine had to assume.
Questions = what to ask the supplier, one per flag that needs an answer (deduplicated).
"""

from __future__ import annotations

from datetime import date

from backend.app.costing import (
    DEFAULT_CLEARANCE_INR,
    DEFAULT_INLAND_TRANSPORT_INR,
    describe_tax,
    pricing_label,
)
from backend.app.models import (
    BrandStatus,
    CoaStatus,
    DeliveryEstimate,
    Flag,
    LeadTimeBasis,
    LeadTimeStart,
    PricingBasis,
    Quote,
    QuoteCosting,
    Requisition,
    Severity,
    SourceChannel,
    TaxTreatment,
)
from backend.app.summary import (
    arrival_text,
    buffer_phrase,
    format_date,
    format_inr,
    format_pct,
    format_qty,
    format_qty_unit,
)

CRIT, WARN, INFO = Severity.CRITICAL, Severity.WARNING, Severity.INFO
_SEVERITY_ORDER = {CRIT: 0, WARN: 1, INFO: 2}

COA_TEXT = {
    CoaStatus.EVERY_BATCH: "with every batch",
    CoaStatus.WITH_MATERIAL: "'comes with the material' (not confirmed batch-specific)",
    CoaStatus.ON_REQUEST_OR_CONDITIONAL: "only on request / if needed",
    CoaStatus.MISSING_OR_UNCLEAR: "not mentioned",
}
_SOURCE_TEXT = {
    SourceChannel.EMAIL: "email",
    SourceChannel.WHATSAPP: "WhatsApp",
    SourceChannel.PDF: "PDF quotation",
    SourceChannel.PHONE: "phone call (verbal only)",
    SourceChannel.OTHER: "other",
}
_BASIS_TEXT = {
    PricingBasis.EX_WORKS: "ex-works",
    PricingBasis.CIF: "CIF",
    PricingBasis.DELIVERED: "delivered",
    PricingBasis.PICKUP: "pickup",
}


def brand_missing(quote: Quote) -> bool:
    return quote.brand_status == BrandStatus.MISSING or not (quote.brand_name or "").strip()


def paid_before_delivery_pct(quote: Quote) -> float:
    """Share of the order value paid before the goods arrive (advance + against documents)."""
    return max(quote.advance_pct, quote.pre_delivery_pct)


def _has_alternate_tax(quote: Quote) -> bool:
    return quote.alt_tax_treatment is not None or quote.alt_gst_rate_pct is not None


def _scenario_totals(costing: QuoteCosting) -> str:
    """"GST inclusive @ 18%: Rs 1,82,500; GST extra @ 18%: Rs 2,14,900"."""
    return "; ".join(f"{s.description}: {format_inr(s.commitment.total_landed_inr)}" for s in costing.scenarios)


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------
def build_flags(
    requisition: Requisition,
    quote: Quote,
    costing: QuoteCosting,
    delivery: DeliveryEstimate,
    reference_date: date,
) -> list[Flag]:
    """All flags for one quote, CRITICAL first, then WARNING, then INFO."""
    flags: list[Flag] = []

    def add(code: str, severity: Severity, message: str, question: str | None = None) -> None:
        flags.append(Flag(code=code, severity=severity, message=message, question=question))

    need_by = format_date(requisition.need_by_date)

    # --- Cost comparability -------------------------------------------------
    if not costing.comparable:
        add("UNIT_MISMATCH", CRIT, f"Cannot be costed against the requisition: {' '.join(costing.notes)}",
            f"Please restate the price per {requisition.unit.value} (or give the pack size) so it can be compared.")

    # --- Validity -------------------------------------------------------------
    if quote.valid_until is None:
        add("VALIDITY_MISSING", WARN, "The quote does not say how long the price is valid.",
            "How long is this price valid? Please confirm the validity date in writing.")
    else:
        days_left = (quote.valid_until - reference_date).days
        valid = format_date(quote.valid_until)
        if days_left < 0:
            add("EXPIRED", CRIT, f"Quote expired on {valid}, {-days_left} days before {format_date(reference_date)}.",
                "The quote has expired. Please re-confirm the price and terms in a fresh written quote.")
        elif days_left <= 7:
            add("VALIDITY_SOON", INFO, f"Price valid only until {valid} ({days_left} days left).",
                f"Can you hold this price beyond {valid} while we complete approval?")

    # --- Delivery -------------------------------------------------------------
    if quote.lead_time_min_days is None and quote.lead_time_max_days is None:
        add("LEAD_TIME_MISSING", WARN, "No delivery lead time stated, so arrival cannot be estimated.",
            f"What is the delivery lead time to {requisition.site} from PO?")
    elif delivery.earliest_arrival and delivery.latest_arrival and delivery.buffer_days is not None:
        arrives = arrival_text(delivery, year=True)
        if delivery.earliest_arrival > requisition.need_by_date:
            days_late = (delivery.earliest_arrival - requisition.need_by_date).days
            add("LATE_DELIVERY", CRIT,
                f"Arrives {arrives}: at least {buffer_phrase(-days_late)} ({need_by}).",
                f"Can you deliver by {need_by}? Our estimate from your lead time is {arrives}.")
        elif delivery.latest_arrival > requisition.need_by_date:
            add("DELIVERY_RANGE_RISK", WARN,
                f"Arrival window {arrives} straddles the need-by date {need_by}: on time only at the early end.",
                f"Can you commit to delivery by {need_by}?")
        elif delivery.buffer_days <= 1:
            add("TIGHT_DELIVERY", WARN,
                f"Arrives {arrives}, {buffer_phrase(delivery.buffer_days)} ({need_by}): no slack for any delay.",
                f"Can you confirm a firm dispatch date so the goods arrive before {need_by}?")

    # --- Quantity -------------------------------------------------------------
    if costing.moq_applies and costing.scenarios:
        primary = costing.scenarios[0]
        unit = requisition.unit
        surplus = costing.order_quantity - costing.required_quantity
        extra = primary.commitment.total_landed_inr - primary.required_only.total_landed_inr
        moq = format_qty_unit(quote.moq_quantity or 0, quote.moq_unit or unit)
        add("MOQ_ABOVE_REQUIRED", WARN,
            f"MOQ {moq} forces an order of {format_qty_unit(costing.order_quantity, unit)} against "
            f"{format_qty_unit(costing.required_quantity, unit)} required: {format_qty_unit(surplus, unit)} surplus "
            f"costing {format_inr(extra)} more than buying only what is needed.",
            f"Can you waive the MOQ and supply {format_qty_unit(costing.required_quantity, unit)}?")

    # --- CoA ------------------------------------------------------------------
    if requisition.coa_mandatory:
        if quote.coa_status == CoaStatus.MISSING_OR_UNCLEAR:
            add("COA_MISSING", CRIT, "A CoA is mandatory but the quote does not commit to one.",
                "Will you supply a batch-specific Certificate of Analysis with every batch?")
        elif quote.coa_status in (CoaStatus.WITH_MATERIAL, CoaStatus.ON_REQUEST_OR_CONDITIONAL):
            offer = ("only says it 'comes with the material' (not confirmed batch-specific)"
                     if quote.coa_status == CoaStatus.WITH_MATERIAL else "offers it only on request / if needed")
            add("COA_CONDITIONAL", WARN, f"A CoA is mandatory but the quote {offer}.",
                "Please confirm a batch-specific CoA will accompany every batch at no extra cost.")

    # --- Payment --------------------------------------------------------------
    paid_pct = paid_before_delivery_pct(quote)
    if paid_pct > 0:
        amount = ""
        if costing.worst_case_landed_inr is not None:
            amount = f" ({format_inr(costing.worst_case_landed_inr * paid_pct / 100)})"
        terms = f" [{quote.payment_terms}]" if quote.payment_terms else ""
        message = f"{format_pct(paid_pct)} of the value{amount} is paid before the goods arrive{terms}."
        if paid_pct >= 50:
            add("HEAVY_ADVANCE", WARN, message,
                "Can you accept a lower advance, payment against delivery, or credit terms?")
        else:
            add("PARTIAL_ADVANCE", INFO, message)

    # --- Terms and tax (one flag per cause: contradictions win over tax doubt) -
    if quote.contradictions:
        message = "Conflicting terms: " + " ".join(quote.contradictions)
        if len(costing.scenarios) == 2:
            message += f" Both readings costed ({_scenario_totals(costing)}); ranked on the higher."
        add("CONTRADICTORY_TERMS", WARN, message,
            "Please confirm in writing which terms apply: " + " ".join(quote.contradictions))
    elif _has_alternate_tax(quote) or quote.tax_treatment == TaxTreatment.UNSPECIFIED:
        if len(costing.scenarios) == 2:
            message = f"Tax not confirmed. {_scenario_totals(costing)}; ranked on the higher."
        else:
            message = "The quote does not state its GST treatment; no tax is included in the total."
        if quote.tax_treatment == TaxTreatment.UNSPECIFIED:
            question = "Is GST included in the price, and at what rate (with HSN code)?"
        elif quote.alt_gst_rate_pct is not None and quote.alt_gst_rate_pct != quote.gst_rate_pct:
            question = (f"Please confirm the GST rate in writing ({format_pct(quote.gst_rate_pct)} quoted; "
                        f"{format_pct(quote.alt_gst_rate_pct)} may apply) with the HSN code.")
        else:
            question = "Please confirm in writing whether the price is inclusive or exclusive of GST."
        add("TAX_UNCONFIRMED", WARN, message, question)

    # --- Brand ----------------------------------------------------------------
    if brand_missing(quote):
        if requisition.require_named_brand:
            add("BRAND_MISSING", CRIT, "A named brand is required but the quote names none.",
                "Which brand / manufacturer is this? Please share its spec sheet and a sample CoA.")
        else:
            add("BRAND_MISSING", INFO, "No brand or manufacturer named.", "Which brand / manufacturer is this?")
    elif requisition.require_named_brand and quote.brand_status == BrandStatus.NAMED_UNVERIFIED:
        add("BRAND_UNVERIFIED", WARN, f"Brand '{quote.brand_name}' is named but not yet confirmed as approved by the lab.",
            f"Please share the {quote.brand_name} spec sheet and a sample CoA so the lab can approve the brand.")

    # --- Budget, source, freight, import --------------------------------------
    variance = costing.budget_variance_inr
    if variance is not None and variance > 0 and costing.worst_case_landed_inr is not None:
        add("OVER_BUDGET", WARN,
            f"Worst-case landed cost {format_inr(costing.worst_case_landed_inr)} is {format_inr(variance)} "
            f"over the approved budget of {format_inr(requisition.approved_budget)}.",
            f"Is there any flexibility on price to bring the total within {format_inr(requisition.approved_budget)}?")

    if quote.source_channel == SourceChannel.PHONE:
        add("VERBAL_ONLY", WARN, "Verbal quote over the phone: nothing in writing yet.",
            "Please send this quote in writing (email/PDF) with price, GST, validity and delivery terms.")

    if costing.incomplete:
        add("FREIGHT_UNKNOWN", WARN, "Freight is not quantified ('at actual' / not stated); landed totals exclude it.",
            f"What is the fixed transport cost to {requisition.site}?")

    if quote.tax_treatment == TaxTreatment.IMPORT_DUTY_IGST:
        message = f"Import priced in {quote.currency} at Rs {format_qty(quote.fx_rate_to_inr)}/{quote.currency}."
        if costing.scenarios:
            b = costing.scenarios[costing.worst_case_index].commitment
            message += (f" Customs duty {format_inr(b.customs_duty_inr)}, IGST {format_inr(b.recoverable_tax_inr)}, "
                        f"clearance {format_inr(b.clearance_inr)} and inland transport "
                        f"{format_inr(b.inland_transport_inr)} added.")
        add("IMPORT", INFO, message + " FX and duty rates can move before clearance.")

    return sorted(flags, key=lambda f: _SEVERITY_ORDER[f.severity])  # stable sort keeps rule order


def build_questions(flags: list[Flag]) -> list[str]:
    """Supplier questions from the flags, in flag order, without duplicates."""
    return list(dict.fromkeys(f.question for f in flags if f.question))


# ---------------------------------------------------------------------------
# Facts and assumptions
# ---------------------------------------------------------------------------
def _lead_time_text(quote: Quote) -> str:
    low, high = quote.lead_time_min_days, quote.lead_time_max_days
    if low is None and high is None:
        return "not stated"
    low = low if low is not None else high
    high = high if high is not None else low
    days = str(low) if low == high else f"{low}-{high}"
    basis = "working" if quote.lead_time_basis == LeadTimeBasis.WORKING else "calendar"
    start = "payment" if quote.lead_time_starts == LeadTimeStart.PAYMENT else "PO"
    return f"{days} {basis} days from {start}"


def build_facts(requisition: Requisition, quote: Quote) -> list[str]:
    """What the quote states, each line labelled ("Price: ...", "Payment: ...")."""
    if quote.currency.upper() == "INR":
        price = f"{format_inr(quote.price)} {pricing_label(quote, requisition.unit)}"
    else:
        price = (f"{quote.currency} {quote.price:,.2f} {pricing_label(quote, requisition.unit)} "
                 f"(at Rs {format_qty(quote.fx_rate_to_inr)}/{quote.currency} = {format_inr(quote.price * quote.fx_rate_to_inr)})")
    if quote.pricing_basis in _BASIS_TEXT:
        price += f", {_BASIS_TEXT[quote.pricing_basis]}"

    if quote.freight_free_above_inr is not None:
        below = "amount not stated" if quote.freight_cost is None else format_inr(quote.freight_cost)
        freight = f"free for orders of {format_inr(quote.freight_free_above_inr)} or more (below that: {below})"
    elif quote.freight_cost is None:
        freight = "'at actual' / not stated"
    elif quote.freight_cost == 0:
        freight = "no separate charge"
    else:
        freight = format_inr(quote.freight_cost)

    if quote.payment_terms:
        payment = quote.payment_terms
    else:
        parts = []
        if paid_before_delivery_pct(quote) > 0:
            parts.append(f"{format_pct(paid_before_delivery_pct(quote))} before delivery")
        if quote.credit_days > 0:
            parts.append(f"{quote.credit_days} days credit")
        payment = ", ".join(parts) or "not stated"

    if brand_missing(quote):
        brand = "not named"
    else:
        verified = "verified" if quote.brand_status == BrandStatus.VERIFIED else "named, not verified"
        brand = f"{quote.brand_name} ({verified})"

    facts = [
        f"Price: {price}",
        f"Tax: {describe_tax(quote, quote.tax_treatment, quote.gst_rate_pct)}",
        f"Freight: {freight}",
    ]
    if quote.moq_quantity:
        facts.append(f"MOQ: {format_qty_unit(quote.moq_quantity, quote.moq_unit or requisition.unit)}")
    facts += [
        f"Lead time: {_lead_time_text(quote)}",
        f"Payment: {payment}",
        f"Validity: {'until ' + format_date(quote.valid_until) if quote.valid_until else 'not stated'}",
        f"CoA: {COA_TEXT[quote.coa_status]}",
        f"Brand: {brand}",
        f"Source: {_SOURCE_TEXT[quote.source_channel]}",
    ]
    return facts


def build_assumptions(quote: Quote, costing: QuoteCosting, delivery: DeliveryEstimate) -> list[str]:
    """What the engine assumed to cost and date this quote."""
    out: list[str] = []
    if delivery.start_date is not None:
        event = "Payment made" if quote.lead_time_starts == LeadTimeStart.PAYMENT else "PO placed"
        basis = " (Mon-Sat)" if quote.lead_time_basis == LeadTimeBasis.WORKING else ""
        out.append(f"{event} on {format_date(delivery.start_date)}; lead time counted from then{basis}.")
    if quote.transit_days:
        out.append(f"{quote.transit_days} calendar day(s) of transit added after dispatch.")
    low, high = quote.lead_time_min_days, quote.lead_time_max_days
    if low is not None and high is not None and low != high:
        out.append(f"Lead time is a range ({low}-{high} days): delivery is judged on the later date.")
    elif (low is None) != (high is None):
        out.append("Only one lead-time figure given; used as both earliest and latest.")
    for s in costing.scenarios:
        if s.tax_treatment == TaxTreatment.INCLUSIVE_GST:
            out.append(f"{s.name.capitalize()} reading: inclusive price back-calculated at GST {format_pct(s.gst_rate_pct or 0)}.")
    if len(costing.scenarios) == 2:
        out.append("Two tax readings costed; ranking, budget and flags use the higher total.")
    if costing.moq_applies:
        out.append("Ranked at the MOQ commitment; the required-quantity cost is shown as 'if MOQ waived'.")
    if costing.incomplete:
        out.append("Unknown freight is excluded from the landed totals (flagged).")
    if any(s.tax_treatment == TaxTreatment.IMPORT_DUTY_IGST for s in costing.scenarios):
        if quote.clearance_fee_inr is None:
            out.append(f"Customs clearance not quoted: default {format_inr(DEFAULT_CLEARANCE_INR)} used.")
        if quote.inland_transport_inr is None:
            out.append(f"Port-to-site transport not quoted: default {format_inr(DEFAULT_INLAND_TRANSPORT_INR)} used.")
    if quote.notes.strip():
        out.append(quote.notes.strip())
    return out
