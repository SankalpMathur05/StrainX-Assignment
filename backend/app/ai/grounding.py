"""Number grounding: which numbers in AI text do not appear anywhere in the data it was given?

The engine does all arithmetic. The AI may only repeat numbers from its context, so any
other number (e.g. an invented saving) is reported back to the UI as "check these numbers".
"""

from __future__ import annotations

import re
from typing import Any

# One number, optionally with Indian (2,27,150) or western (227,150 / 1,000,000) digit grouping
# and decimals. Western is tried first so "1,000,000" is not cut short at "1,000".
# Prefixes like "Rs", "₹" and suffixes like "%" are simply not part of the match.
_NUMBER = re.compile(
    r"(?<![\d.,])"  # not in the middle of another number
    r"(?:\d{1,3}(?:,\d{3})+"  # western grouping: 227,150
    r"|\d{1,2}(?:,\d{2})*,\d{3}"  # Indian grouping: 2,27,150 / 12,500
    r"|\d+)"  # plain: 227150
    r"(?:\.\d+)?"  # decimals: .16
    r"(?!\d)"
)


def _numbers_with_text(text: str) -> list[tuple[str, float]]:
    return [(m.group(), float(m.group().replace(",", ""))) for m in _NUMBER.finditer(text)]


def extract_numbers(text: str) -> list[float]:
    """All numbers in `text`, in order: "Rs 2,27,150 at 18%" -> [227150.0, 18.0]."""
    return [value for _, value in _numbers_with_text(text)]


def _context_numbers(context: Any) -> list[float]:
    """Absolute values of every number in nested dicts/lists, including numbers inside strings."""
    if isinstance(context, bool) or context is None:
        return []
    if isinstance(context, (int, float)):
        return [abs(float(context))]
    if isinstance(context, str):
        return extract_numbers(context)
    if isinstance(context, dict):
        return [n for value in context.values() for n in _context_numbers(value)]
    if isinstance(context, (list, tuple, set)):
        return [n for item in context for n in _context_numbers(item)]
    return extract_numbers(str(context))  # dates, enums, ...


def _ignored(raw: str, value: float) -> bool:
    """Small integers (days, %, counts) and years are too common to check meaningfully."""
    if not value.is_integer():
        return False
    if 0 <= value <= 31:
        return True
    return 1900 <= value <= 2100 and "," not in raw  # "2026" is a year; "2,026" is an amount


def ungrounded_numbers(ai_text: str, context: Any) -> list[str]:
    """Numbers (as written) in `ai_text` that match no number in `context`.

    A match is equal within 0.01, or equal after rounding to the nearest integer
    (so "17,898" matches 17898.25). Signs are ignored (a -20,050 variance may be
    described as "20,050 under budget").
    """
    known = _context_numbers(context)
    known_rounded = {round(n) for n in known}
    result: list[str] = []
    for raw, value in _numbers_with_text(ai_text):
        if _ignored(raw, value) or raw in result:
            continue
        grounded = round(value) in known_rounded or any(abs(value - n) <= 0.01 for n in known)
        if not grounded:
            result.append(raw)
    return result
