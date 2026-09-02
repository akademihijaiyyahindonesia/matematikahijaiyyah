"""
How strong the guard actually is, component by component — and why one of its
gaps cannot be closed.

The guard is the system's strongest property: validity decided from the datum
alone, in O(1), with no stored reference. This file measures that claim per
component rather than asserting it, because "self-validating" is worth nothing
if a third of the vector is unwatched.

Measured: 100% on the thirteen N/K/Q components and the three aggregates.
0% on H*. And 11% on Theta-hat -- which turns out to be forced rather than
overlooked, and that is the finding worth keeping.
"""
from __future__ import annotations

import itertools

from hijaiyyah.core.guards import _to_vec, compute_U, guard_check
from hijaiyyah.core.master_table import MASTER_TABLE

VECTORS = [list(_to_vec(entry)) for entry in MASTER_TABLE.all_entries()]
DELTAS = (1, -1, 2, -2, 7)


def _detection(indices: list[int]) -> tuple[int, int]:
    """(corruptions tried, corruptions the guard rejected)."""
    tried = caught = 0
    for v in VECTORS:
        for i in indices:
            for d in DELTAS:
                w = list(v)
                w[i] += d
                if any(x < 0 for x in w):
                    continue            # outside N_0: a different rejection
                tried += 1
                if not guard_check(w):
                    caught += 1
    return tried, caught


def test_the_guard_catches_every_corruption_of_N_K_and_Q() -> None:
    tried, caught = _detection(list(range(1, 14)))
    assert tried > 1000
    assert caught == tried, f"{tried - caught} of {tried} slipped through"


def test_the_guard_catches_every_corruption_of_the_aggregates() -> None:
    tried, caught = _detection([14, 15, 16])
    assert caught == tried, f"{tried - caught} of {tried} slipped through"


def test_H_star_is_carried_but_never_checked() -> None:
    """
    Index 17 appears in no guard. Every corruption of it passes. This is the
    one gap that is a gap rather than a consequence -- and it is pinned here
    so it stays visible until something closes it.

    H* is 1 for exactly one letter (Kaf) and 0 for the other twenty-seven, so
    any rule tying it to structure would be fitted to a single positive
    example rather than derived. That is why it is still open.
    """
    tried, caught = _detection([17])
    assert tried == 85
    assert caught == 0, "something now checks H* -- update this test"

    from pathlib import Path
    src = (Path(__file__).resolve().parents[2]
           / "src" / "hijaiyyah" / "core" / "guards.py").read_text(encoding="utf-8")
    assert "vec[17]" not in src

    marked = [i for i, v in enumerate(VECTORS) if v[17]]
    assert marked == [21], marked


def test_theta_is_one_sided_and_that_is_forced_by_the_monoid() -> None:
    """
    G4 is `rho = Theta-hat - U >= 0`. It catches Theta-hat too small and never
    catches it too large, so 118 of 133 corruptions pass. That looks like an
    oversight and is not one.

    rho is ADDITIVE: rho(a+b) = rho(a) + rho(b), verified over all 784 pairs.
    So any finite upper bound B > 0 is violated by some sum of two valid
    hybits. The only bounds closed under addition are B = infinity -- no bound
    at all -- and rho identically zero, which it is not.

    Closure and two-sided detection on Theta-hat cannot both be had. The guard
    keeps closure, and this is the price, stated rather than hidden.
    """
    tried, caught = _detection([0])
    assert tried == 133
    assert caught == 15, f"detection on Theta-hat moved: {caught}/{tried}"

    rho = [v[0] - compute_U(v) for v in VECTORS]
    assert min(rho) == 0 and max(rho) > 0, "rho is not identically zero"

    # Additive, over every pair.
    for a, b in itertools.product(range(28), repeat=2):
        total = [x + y for x, y in zip(VECTORS[a], VECTORS[b], strict=True)]
        assert total[0] - compute_U(total) == rho[a] + rho[b]

    # Therefore every finite bound is broken by a sum.
    for bound in range(1, max(rho) * 2):
        broken = [(a, b) for a, b in itertools.product(range(28), repeat=2)
                  if rho[a] + rho[b] > bound]
        assert broken, f"bound {bound} was never exceeded -- rho stopped being additive"


def test_the_guard_survives_arithmetic_and_a_checksum_does_not() -> None:
    """
    The property no checksum has, and the reason it is the side worth
    strengthening: adding two valid hybits yields a valid hybit that is still
    checkable in O(1), without touching either term. Adding two checksummed
    records destroys the checksum -- it has to be recomputed over the result.
    """
    import struct
    import zlib

    def blob(v: list[int]) -> bytes:
        return b"".join(struct.pack("<i", x) for x in v)

    still_valid = derivable = 0
    for a, b in itertools.product(range(28), repeat=2):
        total = [x + y for x, y in zip(VECTORS[a], VECTORS[b], strict=True)]
        if guard_check(total):
            still_valid += 1
        if zlib.crc32(blob(total)) == zlib.crc32(blob(VECTORS[a])) ^ zlib.crc32(blob(VECTORS[b])):
            derivable += 1

    assert still_valid == 784
    assert derivable == 0, "a CRC of the sum became derivable from the terms"
