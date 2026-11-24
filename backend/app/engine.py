"""Engine entry point: CompareRequest -> CompareResult.

Pure and deterministic: no I/O, no LLM. Pipeline per quote:
cost -> delivery -> flags -> score, then rank -> recommendation -> summary text.
"""

from __future__ import annotations

from datetime import date

from backend.app.costing import cost_quote
from backend.app.dates import estimate_delivery
from backend.app.flags import build_assumptions, build_facts, build_flags, build_questions
from backend.app.models import (
    DEFAULT_REFERENCE_DATE,
    CompareRequest,
    CompareResult,
    Quote,
    QuoteAnalysis,
    Severity,
    Weights,
)
from backend.app.scoring import (
    CRITICAL_PENALTY,
    WARNING_PENALTY,
    build_recommendation,
    cheapest_landed,
    rank_analyses,
    score_quote,
)
from backend.app.summary import build_summary_text, format_date, format_qty


def _global_assumptions(reference_date: date, weights: Weights) -> list[str]:
    w = [weights.price, weights.delivery, weights.payment, weights.quality]
    weight_text = (
        "equal weights (all sliders are 0)" if sum(w) == 0
        else "weights price {}, delivery {}, payment {}, quality {}".format(*(format_qty(x) for x in w))
    )
    return [
        f"{format_date(reference_date)} is treated as today; every PO or payment is assumed to be placed that day.",
        "Working days are Monday to Saturday (only Sundays skipped; holidays ignored); transit days are calendar days.",
        "Budget is compared with the worst-case landed cash outflow including GST/IGST; recoverable GST/IGST is "
        "shown separately as potential input tax credit and never deducted.",
        "Unclear or contradictory tax terms are costed both ways; ranking, budget and flags use the higher total.",
        "Ranking uses the cost of the quantity you must commit to (MOQ, rounded up to whole packs); the "
        "required-quantity cost is shown as 'if MOQ waived'.",
        "Unknown costs (e.g. freight 'at actual') are excluded from totals and flagged.",
        f"Score = weighted average of price, delivery, payment and quality scores ({weight_text}) minus "
        f"{format_qty(CRITICAL_PENALTY)} per critical and {format_qty(WARNING_PENALTY)} per warning flag; "
        "the displayed score is clamped to 0-100.",
    ]


def compare(request: CompareRequest, default_reference_date: date = DEFAULT_REFERENCE_DATE) -> CompareResult:
    """Cost, flag, score and rank every quote for the requisition.

    `request.reference_date` (if set) overrides `default_reference_date` ("today").
    """
    reference_date = request.reference_date or default_reference_date
    requisition = request.requisition
    weights = request.weights

    # Cost everything first: the price score needs the cheapest comparable quote.
    costings = [cost_quote(requisition, q) for q in request.quotes]
    cheapest = cheapest_landed(costings)

    pairs: list[tuple[QuoteAnalysis, Quote]] = []
    for i, (quote, costing) in enumerate(zip(request.quotes, costings)):
        label = quote.label.strip() or str(i + 1)  # unlabelled quotes are numbered
        delivery = estimate_delivery(quote, requisition.need_by_date, reference_date)
        flags = build_flags(requisition, quote, costing, delivery, reference_date)
        analysis = QuoteAnalysis(
            quote_id=quote.id,
            label=label,
            supplier_name=quote.supplier_name,
            rank=0,  # set by rank_analyses
            costing=costing,
            delivery=delivery,
            flags=flags,
            critical_count=sum(f.severity == Severity.CRITICAL for f in flags),
            warning_count=sum(f.severity == Severity.WARNING for f in flags),
            facts=build_facts(requisition, quote),
            assumptions=build_assumptions(quote, costing, delivery),
            questions=build_questions(flags),
            score=score_quote(quote, costing, delivery, flags, cheapest, weights),
        )
        pairs.append((analysis, quote))

    ranked = rank_analyses(pairs)  # the quote travels with its analysis (labels may repeat)
    result = CompareResult(
        reference_date=reference_date,
        requisition=requisition,
        weights=weights,
        analyses=[analysis for analysis, _ in ranked],
        recommendation=build_recommendation(requisition, ranked),
        summary_text="",
        global_assumptions=_global_assumptions(reference_date, weights),
    )
    result.summary_text = build_summary_text(result)
    return result
