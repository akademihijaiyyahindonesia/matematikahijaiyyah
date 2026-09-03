"""
The degree as a function, and where the curvature it does not account for goes.

Theta-hat counts quarter turns. U predicts them from the curve inventory:

    U = Qx + Qs + Qa + 4*Qc

Note what is absent. Qp -- the PRIMARY curve -- is not in U, and Qc carries a
factor of four. The four is Umlaufsatz: a closed curve turns a full 360
degrees, so each closed loop is worth four quarters exactly. Haa has two loops,
U = 8, Theta-hat = 8, and residue zero: 720 degrees of turning and not one
quarter of it from anything but its loops.

rho = Theta-hat - U is therefore the turning the inventory does NOT explain,
and where it comes from is measurable.
"""
from __future__ import annotations

import itertools

from hijaiyyah.core.guards import _to_vec, compute_U, guard_check
from hijaiyyah.core.master_table import MASTER_TABLE

ENTRIES = MASTER_TABLE.all_entries()
VECTORS = [list(_to_vec(e)) for e in ENTRIES]


def _rho(v: list[int]) -> int:
    return v[0] - compute_U(v)


def test_a_closed_loop_is_worth_exactly_four_quarters() -> None:
    """Umlaufsatz, and it is why the 4 sits in front of Qc."""
    haa = next(v for v, e in zip(VECTORS, ENTRIES, strict=True) if e.name == "Haa")
    assert haa[13] == 2                    # two closed loops
    assert haa[0] == 8 == 2 * 4            # 720 degrees
    assert _rho(haa) == 0                  # all of it from the loops

    # And no letter's U can be reached without counting loops fourfold.
    for v in VECTORS:
        assert compute_U(v) == v[10] + v[11] + v[12] + 4 * v[13]


def test_ten_letters_turn_only_because_they_curve() -> None:
    """rho = 0 means the inventory explains the whole turning."""
    zero = [e.char for v, e in zip(VECTORS, ENTRIES, strict=True) if _rho(v) == 0]
    assert len(zero) == 10
    assert set(zero) == set("ا د ذ ر ز ط ظ م و هـ".split())
    assert all(0 <= _rho(v) <= 3 for v in VECTORS)


def test_unexplained_turning_comes_from_a_primary_curve_or_a_corner() -> None:
    """
    rho > 0 <=> Qp > 0 or Ka > 0, on all 28. Traceable rather than mysterious:
    U deliberately omits Qp, so a primary curve's own turning has nowhere to go
    but the residue. Kaf is the exception that completes it -- no primary curve,
    but Ka = 1, an angular corner, and rho = 2.

    [EH], NOT a guard. Unlike G1-G3, which are definitional -- the classifier
    puts each component in exactly one bucket, so the buckets sum -- this is a
    claim about which shapes the alphabet happens to contain. It is supported
    by a real partition, 18 letters against 10, and not by one data point the
    way `H* = Ka` was. It is still empirical, and it stays out of the guard.
    """
    for v, e in zip(VECTORS, ENTRIES, strict=True):
        assert (_rho(v) > 0) == (v[9] > 0 or v[7] > 0), e.char

    assert sum(1 for v in VECTORS if _rho(v) > 0) == 18
    assert sum(1 for v in VECTORS if v[9] > 0) == 17     # Qp
    assert sum(1 for v in VECTORS if v[7] > 0) == 1      # Ka, Kaf alone

    # It happens to survive addition, which a bound on rho does not.
    for a, b in itertools.product(range(28), repeat=2):
        s = [x + y for x, y in zip(VECTORS[a], VECTORS[b], strict=True)]
        assert (_rho(s) > 0) == (s[9] > 0 or s[7] > 0)

    # And Qp is genuinely absent from U -- that is the mechanism.
    probe = [0] * 18
    probe[9] = 5
    assert compute_U(probe) == 0


def test_630_degrees_is_absent_from_the_alphabet_but_not_impossible() -> None:
    """
    The degrees run 0, 90, 180, 270, 360, 450, 540, 720. Seven quarters -- 630
    -- occurs in no letter. That is a fact about these 28 shapes, not a
    constraint: a valid vector with Theta-hat = 7 is constructible, and one is
    built here so the gap cannot be mistaken for a law.
    """
    degrees = sorted({v[0] for v in VECTORS})
    assert degrees == [0, 1, 2, 3, 4, 5, 6, 8]
    assert 7 not in degrees

    built = [0] * 18
    built[0] = 7                                  # Theta-hat
    built[11], built[12] = 1, 3                   # Qs, Qa
    built[16] = built[9] + built[10] + built[11] + built[12] + built[13]
    assert guard_check(built)
    assert built[0] == 7 and _rho(built) == 3
