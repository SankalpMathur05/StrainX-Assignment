"""Formatting helpers (INR, dates, quantities) and the WhatsApp/email summary text.

Only depends on the models, so every other engine module can import it.
"""

from __future__ import annotations

from datetime import date

from backend.app.models import CompareResult, DeliveryEstimate, QuoteAnalysis, Severity, Unit

_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_COUNT_UNITS = (Unit.PACK, Unit.DRUM, Unit.UNIT)


def format_inr(amount: float, decimals: int | None = None) -> str:
    """Rupees with Indian digit grouping: 227150 -> "Rs 2,27,150", -20050 -> "-Rs 20,050".

    decimals=None shows paise only when the amount is not a whole number of rupees.
    """
    if decimals is None:
        decimals = 0 if round(amount, 2) == round(amount) else 2
    whole, _, paise = f"{abs(amount):.{decimals}f}".partition(".")
    # Indian grouping: the last 3 digits, then groups of 2 (1,00,00,000).
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    text = "Rs " + ",".join(groups + [tail]) + (f".{paise}" if paise else "")
    # Sign from the rounded value so a tiny negative never prints as "-Rs 0".
    return "-" + text if round(amount, decimals) < 0 else text


def format_date(d: date, year: bool = True) -> str:
    """Fri 27 Nov 2026 (locale-independent)."""
    text = f"{_DAYS[d.weekday()]} {d.day} {_MONTHS[d.month - 1]}"
    return f"{text} {d.year}" if year else text


def format_qty(qty: float) -> str:
    """25.0 -> "25", 25.5 -> "25.5" (max 3 decimals)."""
    return f"{qty:.3f}".rstrip("0").rstrip(".")


def format_qty_unit(qty: float, unit: Unit) -> str:
    """"25 kg", "51 packs", "1 drum" — count units take a plural."""
    plural = "s" if unit in _COUNT_UNITS and qty != 1 else ""
    return f"{format_qty(qty)} {unit.value}{plural}"


def format_pct(pct: float) -> str:
    """18.0 -> "18%", 12.5 -> "12.5%"."""
    return f"{format_qty(pct)}%"


def _days(n: int) -> str:
    return f"{n} day" if n == 1 else f"{n} days"


def buffer_phrase(buffer_days: int) -> str:
    """How the (latest) arrival sits against the need-by date."""
    if buffer_days > 0:
        return f"{_days(buffer_days)} before the need-by date"
    if buffer_days == 0:
        return "on the need-by date itself"
    return f"{_days(-buffer_days)} after the need-by date"


def arrival_text(delivery: DeliveryEstimate, year: bool = False) -> str:
    """"Fri 27 Nov", or "Tue 22 Dec to Tue 29 Dec" for a range, or "not stated"."""
    if delivery.earliest_arrival is None or delivery.latest_arrival is None:
        return "not stated"
    earliest = format_date(delivery.earliest_arrival, year)
    if delivery.earliest_arrival == delivery.latest_arrival:
        return earliest
    return f"{earliest} to {format_date(delivery.latest_arrival, year)}"


def _fact(analysis: QuoteAnalysis, label: str) -> str:
    """Value of a labelled fact line ("Payment: 100% advance" -> "100% advance")."""
    prefix = f"{label}: "
    return next((f[len(prefix):] for f in analysis.facts if f.startswith(prefix)), "not stated")


def _ranking_line(analysis: QuoteAnalysis, unit: Unit) -> str:
    costing = analysis.costing
    if not costing.comparable or costing.worst_case_landed_inr is None:
        cost = "cost not comparable (unit mismatch)"
    else:
        worst = costing.scenarios[costing.worst_case_index].commitment
        variance = costing.budget_variance_inr or 0.0
        budget = (
            f"{format_inr(variance)} over budget" if variance > 0
            else f"{format_inr(-variance)} under budget" if variance < 0
            else "exactly on budget"
        )
        freight = " + freight TBC" if costing.incomplete else ""
        cost = f"{format_inr(worst.total_landed_inr)}{freight} for {format_qty_unit(worst.quantity, unit)} ({budget})"
    return (
        f"{analysis.rank}. Quote {analysis.label} {analysis.supplier_name}: {cost}"
        f" | arrives {arrival_text(analysis.delivery)}"
        f" | pay: {_fact(analysis, 'Payment')}"
        f" | {analysis.critical_count} critical, {analysis.warning_count} warning{'' if analysis.warning_count == 1 else 's'}"
        f" | score {analysis.score.display:.1f}"
    )


def build_summary_text(result: CompareResult) -> str:
    """Plain text a buyer can paste into WhatsApp or email. Numbers come from `result` only."""
    req = result.requisition
    w = result.weights
    lines = [
        f"{req.pr_number}: {req.item_name} - quote comparison (as of {format_date(result.reference_date)})",
        f"Need {format_qty_unit(req.required_quantity, req.unit)} by {format_date(req.need_by_date)}"
        f" | Budget {format_inr(req.approved_budget)} | {len(result.analyses)} quotes",
        "",
    ]
    rec = result.recommendation
    if rec.quote_label is not None:
        lines.append(f"RECOMMENDED: Quote {rec.quote_label} - {rec.supplier_name}")
    lines += [rec.rationale, ""]

    if result.analyses:
        lines.append("Ranking (worst-case landed cash outflow incl. GST):")
        lines += [_ranking_line(a, req.unit) for a in result.analyses]
        top = result.analyses[0]
        risks = [f.message for f in top.flags if f.severity != Severity.INFO][:4]
        lines += ["", f"Top risks (Quote {top.label}):"]
        lines += [f"- {r}" for r in risks] or ["- No critical or warning flags."]
        if top.questions:
            lines += ["", f"Questions for {top.supplier_name}:"]
            lines += [f"- {q}" for q in top.questions[:4]]
        lines.append("")

    lines.append(
        "Note: GST/IGST is shown as potential input tax credit (subject to a valid tax invoice) "
        "and is NOT deducted from the landed totals. "
        f"Weights: price {format_qty(w.price)}, delivery {format_qty(w.delivery)}, "
        f"payment {format_qty(w.payment)}, quality {format_qty(w.quality)}."
    )
    return "\n".join(lines)
