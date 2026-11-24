"""Engine entry point: CompareRequest -> CompareResult.

Pure and deterministic — no I/O, no LLM. Composes units, costing, dates, flags,
scoring and summary. (Stub — implemented by the engine milestone.)
"""

from __future__ import annotations

from datetime import date

from backend.app.models import CompareRequest, CompareResult, DEFAULT_REFERENCE_DATE


def compare(request: CompareRequest, default_reference_date: date = DEFAULT_REFERENCE_DATE) -> CompareResult:
    """Cost, flag, score and rank every quote for the requisition.

    `request.reference_date` (if set) overrides `default_reference_date` ("today").
    """
    raise NotImplementedError("engine.compare is not implemented yet")
