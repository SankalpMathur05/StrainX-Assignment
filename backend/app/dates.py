"""Delivery date estimates.

Working days are Monday to Saturday (only Sundays are skipped; public holidays are
ignored). The PO or payment is assumed to happen on the reference date ("today").
Transit days after dispatch are calendar days.
"""

from __future__ import annotations

from datetime import date, timedelta

from backend.app.models import DeliveryEstimate, LeadTimeBasis, Quote

SUNDAY = 6  # date.weekday(): Monday = 0 ... Sunday = 6


def add_working_days(start: date, days: int) -> date:
    """`days` Mon-Sat working days after `start` (start itself is not counted)."""
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() != SUNDAY:
            remaining -= 1
    return current


def _arrival(start: date, lead_days: int, basis: LeadTimeBasis, transit_days: int) -> date:
    dispatch = (
        add_working_days(start, lead_days)
        if basis == LeadTimeBasis.WORKING
        else start + timedelta(days=lead_days)
    )
    return dispatch + timedelta(days=transit_days)


def estimate_delivery(quote: Quote, need_by: date, reference_date: date) -> DeliveryEstimate:
    low, high = quote.lead_time_min_days, quote.lead_time_max_days
    if low is None and high is None:
        return DeliveryEstimate()  # no lead time stated: nothing can be estimated
    # Only one end given -> use it for both; guard against min/max entered the wrong way round.
    low = low if low is not None else high
    high = high if high is not None else low
    assert low is not None and high is not None
    low, high = min(low, high), max(low, high)

    start = reference_date  # PO placed / payment made "today"
    earliest = _arrival(start, low, quote.lead_time_basis, quote.transit_days)
    latest = _arrival(start, high, quote.lead_time_basis, quote.transit_days)
    return DeliveryEstimate(
        start_date=start,
        earliest_arrival=earliest,
        latest_arrival=latest,
        buffer_days=(need_by - latest).days,  # negative = late
        on_time=latest <= need_by,
    )
