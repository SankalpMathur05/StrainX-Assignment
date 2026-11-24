"""Unit conversion and whole-pack rounding.

Mass (g, kg) converts within mass and volume (mL, L) within volume. Count units
(pack, drum, unit) only "convert" to themselves: a pack has no mass until a quote
tells us its pack size, and that lookup happens in costing, not here.
"""

from __future__ import annotations

import math

from backend.app.models import Unit

# Factor to each family's base unit (grams for mass, millilitres for volume).
_MASS = {Unit.G: 1.0, Unit.KG: 1000.0}
_VOLUME = {Unit.ML: 1.0, Unit.L: 1000.0}


def is_mass(unit: Unit) -> bool:
    return unit in _MASS


def convert(qty: float, from_unit: Unit, to_unit: Unit) -> float | None:
    """Convert `qty` between units; None when the units are incompatible (e.g. kg -> L)."""
    if from_unit == to_unit:
        return qty
    for family in (_MASS, _VOLUME):
        if from_unit in family and to_unit in family:
            return qty * family[from_unit] / family[to_unit]
    return None


def whole_packs(qty: float, pack_size: float) -> int:
    """Smallest whole number of packs covering `qty` (both in the same unit)."""
    if pack_size <= 0:
        raise ValueError("pack_size must be positive")
    # round() first so float noise (50.000000001) does not become an extra pack.
    return math.ceil(round(qty / pack_size, 9))


def packs_needed(qty: float, unit: Unit, pack_size: float, pack_unit: Unit) -> int | None:
    """Whole packs of `pack_size` `pack_unit` needed for `qty` `unit`; None if incompatible."""
    in_pack_unit = convert(qty, unit, pack_unit)
    if in_pack_unit is None:
        return None
    return whole_packs(in_pack_unit, pack_size)


def round_up_to_packs(
    qty: float, unit: Unit, pack_size: float, pack_unit: Unit
) -> tuple[float, int] | None:
    """Round `qty` up to whole packs. Returns (rounded qty in `unit`, packs) or None."""
    packs = packs_needed(qty, unit, pack_size, pack_unit)
    if packs is None:
        return None
    rounded = convert(packs * pack_size, pack_unit, unit)
    assert rounded is not None  # same unit pair as packs_needed, so always convertible
    return rounded, packs
