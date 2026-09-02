"""
Each letter contains its own machine, and two of them are maximal.

The exomatrix is 5x5, the sponge state is 25 lanes, so a letter is one face of
the cube. Read that face as a linear map over GF(2) and iterate it: every
letter settles into a definite period. Most settle immediately. Two do not.

    period  1   16 letters      idempotent or nilpotent -- they stop
    period  2    2
    period  3    7
    period  4    1
    period 31    2              Jim and Kha

31 is 2^5 - 1, the largest order any element of GL(5,2) can have -- the Singer
cycle. A matrix that reaches it has a primitive characteristic polynomial, and
a matrix with a primitive characteristic polynomial over GF(2) is exactly a
maximal-length linear feedback shift register written as a matrix. That is the
standard construction for a counter and for a stream generator.

So "each letter contains its own computing system" is not a metaphor here. It
is measurable, and it separates the alphabet sharply: two letters carry a
maximal-period machine and twenty-six do not.
"""
from __future__ import annotations

import itertools

from hijaiyyah.core.exomatrix import build_exomatrix
from hijaiyyah.core.master_table import MASTER_TABLE

ENTRIES = MASTER_TABLE.all_entries()
JIM, KHA = 4, 6


def _mul(a: list[list[int]], b: list[list[int]]) -> list[list[int]]:
    return [[sum(a[i][k] * b[k][j] for k in range(5)) & 1 for j in range(5)]
            for i in range(5)]


def _orbit(m: list[list[int]], cap: int = 200) -> tuple[int, int]:
    """(tail, period) of M, M^2, M^3, ... over GF(2)."""
    base = [[x & 1 for x in row] for row in m]
    seen: dict[tuple, int] = {}
    x, k = [row[:] for row in base], 1
    while k <= cap:
        key = tuple(map(tuple, x))
        if key in seen:
            return seen[key], k - seen[key]
        seen[key] = k
        x = _mul(x, base)
        k += 1
    raise AssertionError("no cycle within the cap")


def _charpoly(m: list[list[int]]) -> list[int]:
    """Coefficients of det(xI - M) over GF(2), index i is the x^i term."""
    def principal_minor_is_nonsingular(idx: list[int]) -> int:
        n = len(idx)
        if n == 0:
            return 1
        a = [[m[i][j] & 1 for j in idx] for i in idx]
        r = 0
        for c in range(n):
            p = next((i for i in range(r, n) if a[i][c]), None)
            if p is None:
                return 0
            a[r], a[p] = a[p], a[r]
            for i in range(r + 1, n):
                if a[i][c]:
                    a[i] = [u ^ v for u, v in zip(a[i], a[r], strict=True)]
            r += 1
        return 1

    co = [0] * 6
    co[5] = 1
    for k in range(1, 6):
        s = 0
        for idx in itertools.combinations(range(5), k):
            s ^= principal_minor_is_nonsingular(list(idx))
        co[5 - k] = s
    return co


def _is_primitive(co: list[int]) -> bool:
    """x has order exactly 31 in GF(2)[x]/(p)."""
    if co[0] == 0:
        return False
    modulus = sum(c << j for j, c in enumerate(co[:5])) | (1 << 5)

    def mulmod(u: int, v: int) -> int:
        r = 0
        for i in range(5):
            if (v >> i) & 1:
                r ^= u << i
        for i in range(9, 4, -1):
            if (r >> i) & 1:
                r ^= modulus << (i - 5)
        return r & 31

    e = 2
    for k in range(1, 32):
        if e == 1:
            return k == 31
        e = mulmod(e, 2)
    return False


def test_every_letter_settles_into_a_definite_period() -> None:
    """A machine, not a number: iterate the face and it cycles."""
    periods = [_orbit(build_exomatrix(e))[1] for e in ENTRIES]
    assert len(periods) == 28
    assert all(p >= 1 for p in periods)
    assert sorted(set(periods)) == [1, 2, 3, 4, 31]


def test_only_jim_and_kha_reach_the_maximal_period() -> None:
    """
    31 = 2^5 - 1 is the largest order in GL(5,2). Two letters of twenty-eight
    reach it, and both are 270 degrees.
    """
    maximal = [i for i, e in enumerate(ENTRIES)
               if _orbit(build_exomatrix(e))[1] == 31]
    assert maximal == [JIM, KHA], [ENTRIES[i].char for i in maximal]
    assert ENTRIES[JIM].name.lower().startswith("jim")

    for i in maximal:
        m = build_exomatrix(ENTRIES[i])
        assert m[0][0] == 3, "a maximal letter is not 270 degrees any more"
        # Tail 1 means the matrix is already inside its own cycle: invertible.
        assert _orbit(m)[0] == 1


def test_the_maximal_letters_have_primitive_characteristic_polynomials() -> None:
    """
    The exact statement. A matrix over GF(2) whose characteristic polynomial is
    primitive IS a maximal-length LFSR in matrix form -- the standard counter
    and stream-generator construction. There are six primitive polynomials of
    degree 5 over GF(2); two of them turn up here as letters.
    """
    primitive = [i for i, e in enumerate(ENTRIES)
                 if _is_primitive(_charpoly(build_exomatrix(e)))]
    assert primitive == [JIM, KHA]

    # And primitivity is what the period measurement was seeing.
    for i in range(28):
        m = build_exomatrix(ENTRIES[i])
        assert _is_primitive(_charpoly(m)) == (_orbit(m)[1] == 31)


def test_most_letters_stop_rather_than_cycle() -> None:
    """
    Sixteen of twenty-eight have period 1: their face is idempotent or
    nilpotent under iteration. The alphabet is not uniformly a set of
    generators -- the separation is what makes the two maximal ones mean
    something.
    """
    counts: dict[int, int] = {}
    for e in ENTRIES:
        p = _orbit(build_exomatrix(e))[1]
        counts[p] = counts.get(p, 0) + 1
    assert counts[1] == 16
    assert counts[31] == 2
    assert sum(counts.values()) == 28


# ══════════════════════════════════════════════════════════════════
#  The dot is the feedback tap
# ══════════════════════════════════════════════════════════════════

def _period(v: list[int]) -> int:
    return _orbit(build_exomatrix(v))[1]


def test_the_dot_is_what_makes_the_machine_maximal() -> None:
    """
    Jim, Ha and Kha share a skeleton and differ only in dots. Measured, the
    difference between Ha and Jim is ONE component -- Nb goes 0 to 1, and A_N
    follows by G1 -- and the period goes from 2 to 31.

    So the dot is not decoration on the glyph. On the face it is the feedback
    tap, and without it the letter's machine does essentially nothing.
    """
    from hijaiyyah.core.guards import _to_vec

    by_name = {e.name: list(_to_vec(e)) for e in ENTRIES}
    ha, jim, kha = by_name["Ha"], by_name["Jim"], by_name["Kha"]

    assert [i for i in range(18) if jim[i] != ha[i]] == [2, 14]   # Nb and A_N
    assert [i for i in range(18) if kha[i] != ha[i]] == [1, 14]   # Na and A_N

    assert _period(ha) == 2
    assert _period(jim) == 31
    assert _period(kha) == 31


def test_only_two_of_the_three_dot_slots_reach_the_maximum() -> None:
    """
    Take Ha and add a single dot in each slot. Na and Nb -- the slots Kha and
    Jim actually use -- both give 31. The third slot gives 21, high but not
    maximal. The alphabet's two occupied single-dot positions are exactly the
    two that maximise.
    """
    from hijaiyyah.core.guards import _to_vec, guard_check

    ha = next(list(_to_vec(e)) for e in ENTRIES if e.name == "Ha")
    periods = {}
    for slot in (1, 2, 3):
        v = list(ha)
        v[slot] += 1
        v[14] += 1                       # keep G1
        assert guard_check(v)
        periods[slot] = _period(v)

    assert periods[1] == 31              # Na, where Kha puts it
    assert periods[2] == 31              # Nb, where Jim puts it
    assert periods[3] == 21              # unused for a single dot
    assert periods[3] < 31


def test_jim_is_the_only_letter_in_its_slot() -> None:
    """
    Na is used by twelve letters and Nd by two. Nb is used by exactly one:
    Jim. "The single dot in the middle" is not a description of a glyph here,
    it is a slot with one occupant, and that slot is one of the two maximal
    ones.
    """
    from hijaiyyah.core.guards import _to_vec

    vectors = [list(_to_vec(e)) for e in ENTRIES]
    occupancy = {slot: [i for i in range(28) if vectors[i][slot]]
                 for slot in (1, 2, 3)}

    assert occupancy[2] == [JIM], [ENTRIES[i].char for i in occupancy[2]]
    assert len(occupancy[1]) == 12
    assert len(occupancy[3]) == 2


def test_a_second_dot_destroys_what_the_first_one_built() -> None:
    """
    Maximality is fragile in the direction that matters: one tap makes the
    generator, two break it. Doubling a single slot returns the period to Ha's
    own 2 -- the letter stops being a machine again.
    """
    from hijaiyyah.core.guards import _to_vec

    ha = next(list(_to_vec(e)) for e in ENTRIES if e.name == "Ha")

    def with_dots(na: int, nb: int, nd: int) -> int:
        v = list(ha)
        v[1] += na
        v[2] += nb
        v[3] += nd
        v[14] += na + nb + nd
        return _period(v)

    assert with_dots(0, 1, 0) == 31      # Jim
    assert with_dots(1, 0, 0) == 31      # Kha
    for na, nb, nd in ((2, 0, 0), (0, 2, 0)):
        assert with_dots(na, nb, nd) == 2, "a doubled slot should collapse"
    for na, nb, nd in ((1, 1, 0), (1, 0, 1), (0, 1, 1)):
        assert with_dots(na, nb, nd) < 31, "two taps should not stay maximal"
