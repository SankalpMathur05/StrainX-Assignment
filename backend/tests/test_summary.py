from datetime import date

import pytest

from backend.app.engine import compare
from backend.app.models import CompareRequest, Unit
from backend.app.seed import seed_quotes, seed_requisition
from backend.app.summary import buffer_phrase, format_date, format_inr, format_qty_unit


@pytest.mark.parametrize(
    ("amount", "decimals", "expected"),
    [
        (227150, None, "Rs 2,27,150"),
        (447456.16, None, "Rs 4,47,456.16"),
        (10_000_000, None, "Rs 1,00,00,000"),
        (-20050, None, "-Rs 20,050"),
        (999, None, "Rs 999"),
        (0, None, "Rs 0"),
        (-0.001, None, "Rs 0"),  # rounds to zero: no minus sign
        (2500, 2, "Rs 2,500.00"),
        (152542.372881, 0, "Rs 1,52,542"),
        (123456789.5, None, "Rs 12,34,56,789.50"),
    ],
)
def test_format_inr(amount, decimals, expected):
    assert format_inr(amount, decimals) == expected


def test_format_date():
    assert format_date(date(2026, 11, 27)) == "Fri 27 Nov 2026"
    assert format_date(date(2026, 12, 5), year=False) == "Sat 5 Dec"


def test_format_qty_unit_and_buffer_phrase():
    assert format_qty_unit(25.0, Unit.KG) == "25 kg"
    assert format_qty_unit(25.5, Unit.KG) == "25.5 kg"
    assert format_qty_unit(51, Unit.PACK) == "51 packs"
    assert format_qty_unit(1, Unit.DRUM) == "1 drum"
    assert buffer_phrase(8) == "8 days before the need-by date"
    assert buffer_phrase(1) == "1 day before the need-by date"
    assert buffer_phrase(0) == "on the need-by date itself"
    assert buffer_phrase(-24) == "24 days after the need-by date"


def test_summary_text_for_seed():
    result = compare(CompareRequest(requisition=seed_requisition(), quotes=seed_quotes()))
    text = result.summary_text
    lines = text.splitlines()
    assert lines[0].startswith("PR-USP-1147: Yeast Extract Powder")
    assert "RECOMMENDED: Quote A - Narmada Lab Supplies" in text
    assert result.recommendation.rationale in text
    # One line per ranked quote, best first, with numbers from the engine.
    ranking = [line for line in lines if line[:2] in ("1.", "2.", "3.", "4.")]
    assert [line.split()[2] for line in ranking] == ["A", "D", "B", "C"]
    assert "Rs 2,27,150 for 25 kg (Rs 27,150 over budget)" in ranking[0]
    assert "Rs 1,79,950 + freight TBC for 25 kg (Rs 20,050 under budget)" in ranking[1]
    assert "Rs 4,47,456.16 for 50 kg" in ranking[3]
    assert "1 critical, 6 warnings" in ranking[1]
    assert "Questions for Narmada Lab Supplies:" in text
    assert "NOT deducted" in text
    assert 15 <= len(lines) <= 30


def test_summary_text_with_no_quotes():
    result = compare(CompareRequest(requisition=seed_requisition(), quotes=[]))
    assert "PR-USP-1147" in result.summary_text
    assert result.recommendation.quote_label is None
    assert result.analyses == []
