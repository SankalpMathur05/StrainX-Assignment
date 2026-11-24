from datetime import date

import pytest

from backend.app.dates import add_working_days, estimate_delivery
from backend.app.models import LeadTimeBasis, Quote
from backend.app.seed import QUOTE_A, QUOTE_B, QUOTE_C, QUOTE_D

REF = date(2026, 11, 24)  # Tuesday
NEED_BY = date(2026, 12, 5)  # Saturday


def quote(**kw) -> Quote:
    return Quote(**({"supplier_name": "Test", "price": 1} | kw))


@pytest.mark.parametrize(
    ("start", "days", "expected"),
    [
        (date(2026, 11, 28), 3, date(2026, 12, 2)),  # Sat -> (skip Sun) Mon, Tue, Wed
        (date(2026, 11, 24), 3, date(2026, 11, 27)),  # Tue -> Fri
        (date(2026, 11, 27), 2, date(2026, 11, 30)),  # Fri -> Sat, (skip Sun) Mon
        (date(2026, 11, 28), 1, date(2026, 11, 30)),  # Sat -> Mon
        (date(2026, 11, 24), 0, date(2026, 11, 24)),
    ],
)
def test_add_working_days_skips_only_sundays(start, days, expected):
    assert add_working_days(start, days) == expected


@pytest.mark.parametrize(
    ("q", "earliest", "latest", "buffer", "on_time"),
    [
        (QUOTE_A, date(2026, 11, 27), date(2026, 11, 27), 8, True),  # 3 working days from PO
        (QUOTE_B, date(2026, 12, 5), date(2026, 12, 5), 0, True),  # 10 days from payment + 1 transit
        (QUOTE_C, date(2026, 12, 22), date(2026, 12, 29), -24, False),  # 28-35 calendar days
        (QUOTE_D, date(2026, 12, 1), date(2026, 12, 1), 4, True),  # one week
    ],
    ids=["A", "B", "C", "D"],
)
def test_seed_deliveries(q, earliest, latest, buffer, on_time):
    d = estimate_delivery(q, NEED_BY, REF)
    assert d.start_date == REF
    assert (d.earliest_arrival, d.latest_arrival, d.buffer_days, d.on_time) == (earliest, latest, buffer, on_time)


def test_only_one_end_of_range_is_used_for_both():
    for q in (quote(lead_time_min_days=5), quote(lead_time_max_days=5)):
        d = estimate_delivery(q, NEED_BY, REF)
        assert d.earliest_arrival == d.latest_arrival == date(2026, 11, 29)


def test_no_lead_time_gives_empty_estimate():
    d = estimate_delivery(quote(), NEED_BY, REF)
    assert d.start_date is None and d.earliest_arrival is None and d.latest_arrival is None
    assert d.buffer_days is None and d.on_time is None


def test_transit_days_are_calendar_days_after_working_lead_time():
    q = quote(lead_time_min_days=3, lead_time_max_days=3, lead_time_basis=LeadTimeBasis.WORKING, transit_days=2)
    # Sat 28 Nov + 3 working days = Wed 2 Dec, + 2 calendar days = Fri 4 Dec
    d = estimate_delivery(q, NEED_BY, date(2026, 11, 28))
    assert d.latest_arrival == date(2026, 12, 4) and d.buffer_days == 1


def test_late_arrival_has_negative_buffer():
    d = estimate_delivery(quote(lead_time_min_days=20), NEED_BY, REF)
    assert d.latest_arrival == date(2026, 12, 14) and d.buffer_days == -9 and d.on_time is False
