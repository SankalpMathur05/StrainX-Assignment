"""Criterion scores (0-100), weighted score with flag penalties, ranking and the recommendation.

final = sum(w_i * s_i) / sum(w_i) - 30 per CRITICAL flag - 5 per WARNING flag.
Ranking uses `final`; `display` clamps it to 0..100 for the UI.
"""

from __future__ import annotations

from backend.app.flags import brand_missing, paid_before_delivery_pct
from backend.app.models import (
    BrandStatus,
    CoaStatus,
    DeliveryEstimate,
    Flag,
    Quote,
    QuoteAnalysis,
    QuoteCosting,
    Recommendation,
    Requisition,
    ScoreBreakdown,
    Severity,
    SourceChannel,
    TaxTreatment,
    Weights,
)
from backend.app.summary import arrival_text, buffer_phrase, format_inr, format_pct, format_qty_unit

CRITICAL_PENALTY = 30.0
WARNING_PENALTY = 5.0

_BRAND_POINTS = {BrandStatus.VERIFIED: 40.0, BrandStatus.NAMED_UNVERIFIED: 25.0, BrandStatus.MISSING: 0.0}
_COA_POINTS = {
    CoaStatus.EVERY_BATCH: 40.0,
    CoaStatus.WITH_MATERIAL: 15.0,
    CoaStatus.ON_REQUEST_OR_CONDITIONAL: 15.0,
    CoaStatus.MISSING_OR_UNCLEAR: 0.0,
}
WRITTEN_SOURCE_POINTS = 20.0  # anything except a phone call


# ---------------------------------------------------------------------------
# Criterion scores
# ---------------------------------------------------------------------------
def cheapest_landed(costings: list[QuoteCosting]) -> float | None:
    """Lowest worst-case landed total among comparable quotes (the price benchmark)."""
    totals = [c.worst_case_landed_inr for c in costings if c.comparable and c.worst_case_landed_inr is not None]
    return min(totals) if totals else None


def price_score(costing: QuoteCosting, cheapest: float | None) -> float:
    own = costing.worst_case_landed_inr
    if not costing.comparable or own is None or cheapest is None:
        return 0.0
    if own <= 0:
        return 100.0  # free: cannot be beaten
    return 100 * cheapest / own


def delivery_score(delivery: DeliveryEstimate) -> float:
    """0 if late or unknown; otherwise 40 for on-the-day, +15 per day of buffer, capped at 100."""
    if delivery.buffer_days is None or delivery.buffer_days < 0:
        return 0.0
    return min(100.0, 40 + 15 * delivery.buffer_days)


def payment_score(quote: Quote) -> float:
    """70 points for nothing paid up front, plus up to 30 for 30+ days of credit."""
    credit = min(max(quote.credit_days, 0), 30)
    return 0.7 * (100 - paid_before_delivery_pct(quote)) + 30 * credit / 30


def quality_score(quote: Quote) -> float:
    brand = 0.0 if brand_missing(quote) else _BRAND_POINTS[quote.brand_status]
    written = WRITTEN_SOURCE_POINTS if quote.source_channel != SourceChannel.PHONE else 0.0
    return brand + _COA_POINTS[quote.coa_status] + written


def weighted_score(scores: dict[str, float], weights: Weights) -> float:
    """Weighted mean of the criterion scores; all-zero weights fall back to equal weights."""
    w = {"price": weights.price, "delivery": weights.delivery, "payment": weights.payment, "quality": weights.quality}
    total = sum(w.values())
    if total == 0:
        return sum(scores.values()) / len(scores)
    return sum(w[k] * scores[k] for k in w) / total


def score_quote(
    quote: Quote,
    costing: QuoteCosting,
    delivery: DeliveryEstimate,
    flags: list[Flag],
    cheapest: float | None,
    weights: Weights,
) -> ScoreBreakdown:
    scores = {
        "price": price_score(costing, cheapest),
        "delivery": delivery_score(delivery),
        "payment": payment_score(quote),
        "quality": quality_score(quote),
    }
    weighted = weighted_score(scores, weights)
    criticals = sum(f.severity == Severity.CRITICAL for f in flags)
    warnings = sum(f.severity == Severity.WARNING for f in flags)
    penalty = CRITICAL_PENALTY * criticals + WARNING_PENALTY * warnings
    final = round(weighted - penalty, 2)  # computed from the unrounded weighted score
    return ScoreBreakdown(
        **{k: round(v, 2) for k, v in scores.items()},
        weighted=round(weighted, 2),
        penalty=penalty,
        final=final,
        display=min(100.0, max(0.0, final)),
    )


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------
def _rank_key(analysis: QuoteAnalysis) -> tuple[float, float, str]:
    landed = analysis.costing.worst_case_landed_inr
    return (-analysis.score.final, landed if landed is not None else float("inf"), analysis.label)


def rank_analyses(pairs: list[tuple[QuoteAnalysis, Quote]]) -> list[tuple[QuoteAnalysis, Quote]]:
    """Sort (analysis, quote) pairs best-first and set rank 1..n.

    Higher final score wins; ties go to the lower worst-case landed cost, then the label.
    """
    ordered = sorted(pairs, key=lambda pair: _rank_key(pair[0]))
    return [(a.model_copy(update={"rank": i}), q) for i, (a, q) in enumerate(ordered, start=1)]


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------
def _cost_phrase(analysis: QuoteAnalysis, requisition: Requisition) -> str:
    costing = analysis.costing
    if not costing.comparable or not costing.scenarios:
        return "cost could not be computed (units do not match the requisition)"
    worst = costing.scenarios[costing.worst_case_index]
    b = worst.commitment
    variance = costing.budget_variance_inr or 0.0
    details = [
        f"{format_inr(variance)} over budget" if variance > 0
        else f"{format_inr(-variance)} under budget" if variance < 0
        else "exactly on budget"
    ]
    if b.recoverable_tax_inr > 0:
        tax = "IGST" if worst.tax_treatment == TaxTreatment.IMPORT_DUTY_IGST else "GST"
        details.append(f"includes {format_inr(b.recoverable_tax_inr)} {tax} that may be claimable as input tax credit")
    if costing.incomplete:
        details.append("freight not yet quantified")
    return (f"{format_inr(b.total_landed_inr)} landed for {format_qty_unit(b.quantity, requisition.unit)} "
            f"({'; '.join(details)})")


def _arrival_phrase(analysis: QuoteAnalysis) -> str:
    d = analysis.delivery
    if d.buffer_days is None:
        return "delivery date not stated"
    return f"arrives {arrival_text(d)} — {buffer_phrase(d.buffer_days)}"


def _payment_phrase(quote: Quote) -> str:
    paid = paid_before_delivery_pct(quote)
    if paid == 0:
        return f"{quote.credit_days} days credit" if quote.credit_days > 0 else "payment on delivery"
    credit = f", then {quote.credit_days} days credit" if quote.credit_days > 0 else ""
    return f"{format_pct(paid)} paid before delivery{credit}"


_COA_PHRASE = {
    CoaStatus.EVERY_BATCH: "CoA with every batch",
    CoaStatus.WITH_MATERIAL: "CoA only 'with material'",
    CoaStatus.ON_REQUEST_OR_CONDITIONAL: "CoA only on request",
    CoaStatus.MISSING_OR_UNCLEAR: "no CoA commitment",
}


def build_recommendation(requisition: Requisition, ranked: list[tuple[QuoteAnalysis, Quote]]) -> Recommendation:
    """Plain-English, template-based pick of the top-ranked quote."""
    if not ranked:
        return Recommendation(rationale="No quotes to compare yet.")
    top, quote = ranked[0]
    parts = [_cost_phrase(top, requisition), _arrival_phrase(top), _payment_phrase(quote), _COA_PHRASE[quote.coa_status]]
    rationale = (f"{top.supplier_name} (Quote {top.label}) ranks first "
                 f"(score {top.score.display:.1f}/100): {', '.join(parts)}.")

    if top.critical_count:
        clean = [a for a, _ in ranked[1:] if a.critical_count == 0]
        if clean:
            # Possible when weights favour it despite the penalty: say so rather than hide it.
            rationale += (f" It still has {top.critical_count} critical issue(s); Quote {clean[0].label} has none "
                          "but ranks lower on the current weights.")
        else:
            rationale += (f" No quote is free of critical issues: Quote {top.label} is the least-risk option, "
                          "and its critical issues must be resolved before ordering.")

    return Recommendation(
        quote_id=top.quote_id,
        quote_label=top.label,
        supplier_name=top.supplier_name,
        rationale=rationale,
        caveats=[f.message for f in top.flags if f.severity in (Severity.CRITICAL, Severity.WARNING)],
        runner_up_label=ranked[1][0].label if len(ranked) > 1 else None,
    )
