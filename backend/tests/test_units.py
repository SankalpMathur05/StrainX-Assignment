import pytest

from backend.app.models import Unit
from backend.app.units import convert, is_mass, packs_needed, round_up_to_packs, whole_packs


@pytest.mark.parametrize(
    ("qty", "src", "dst", "expected"),
    [
        (1, Unit.KG, Unit.G, 1000),
        (500, Unit.G, Unit.KG, 0.5),
        (2, Unit.L, Unit.ML, 2000),
        (250, Unit.ML, Unit.L, 0.25),
        (7, Unit.KG, Unit.KG, 7),
        (3, Unit.DRUM, Unit.DRUM, 3),
    ],
)
def test_convert_within_family(qty, src, dst, expected):
    assert convert(qty, src, dst) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("src", "dst"),
    [(Unit.KG, Unit.L), (Unit.ML, Unit.G), (Unit.PACK, Unit.KG), (Unit.DRUM, Unit.PACK), (Unit.UNIT, Unit.G)],
)
def test_convert_incompatible_returns_none(src, dst):
    assert convert(1, src, dst) is None


def test_is_mass():
    assert is_mass(Unit.KG) and is_mass(Unit.G)
    assert not is_mass(Unit.L) and not is_mass(Unit.PACK)


def test_whole_packs_rounds_up_and_ignores_float_noise():
    assert whole_packs(25000, 500) == 50
    assert whole_packs(25001, 500) == 51
    assert whole_packs(0.3, 0.1) == 3  # 0.3 / 0.1 = 2.9999999999999996 in floats
    with pytest.raises(ValueError):
        whole_packs(1, 0)


def test_round_up_to_packs_25_2_kg_in_500_g_packs():
    assert round_up_to_packs(25.2, Unit.KG, 500, Unit.G) == (pytest.approx(25.5), 51)
    assert packs_needed(25, Unit.KG, 500, Unit.G) == 50


def test_round_up_to_packs_incompatible():
    assert round_up_to_packs(10, Unit.L, 500, Unit.G) is None
    assert packs_needed(10, Unit.L, 25, Unit.KG) is None
