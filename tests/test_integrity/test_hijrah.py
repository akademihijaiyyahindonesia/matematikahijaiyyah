"""
HIJRAH — Hijaiyyah Injection Raw Hertz.

A bit stream carries one bit per pulse. The claim under test is that a letter
stream carries much more, because a letter is not a pulse: it is a value, a
function, a relation and a rate at once. Counting letters is therefore not
counting bits.

Measured as operators. Take each letter's 5x5 face as a linear map, multiply
words of them, and count the distinct maps a word of length n can reach. The
logarithm of that count, divided by n, is what one letter carries.

    length   mod 2      mod 4      mod 5
         1   4.58       4.81       4.81      bits per letter
         3   3.76       4.45       4.67
         5   3.22       4.06       4.56

A bit stream is 1.00 at every length. log2(28) = 4.81 is the ceiling, since a
letter cannot carry more than its own identity.

AND THE FIELD IS THE WHOLE POINT. Over GF(2) four pairs of letters collapse
onto the same face, because their vectors differ by exactly 2 and 2 vanishes
mod 2 -- Ha with Lam, Syin with Nun, Shad with Qaf, Ain with Ya. Reading a
letter mod 2 IS reading it as bits, and it costs four letters and about a
third of the density. mod 4 is the smallest modulus that separates all 28.
"""
from __future__ import annotations

import math

from hijaiyyah.core.exomatrix import build_exomatrix
from hijaiyyah.core.guards import _to_vec
from hijaiyyah.core.master_table import MASTER_TABLE

ENTRIES = MASTER_TABLE.all_entries()
FACES = [build_exomatrix(e) for e in ENTRIES]


def _face(m: list[list[int]], p: int) -> tuple:
    return tuple(tuple(x % p for x in row) for row in m)


def _mul(a: tuple, b: tuple, p: int) -> tuple:
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(5)) % p
                       for j in range(5)) for i in range(5))


def _reachable(p: int, depth: int) -> list[int]:
    """Distinct maps reachable by words of length 1..depth."""
    gens = [_face(m, p) for m in FACES]
    seen, frontier, sizes = set(gens), set(gens), [len(set(gens))]
    for _ in range(depth - 1):
        nxt = set()
        for a in frontier:
            for b in gens:
                q = _mul(a, b, p)
                if q not in seen:
                    seen.add(q)
                    nxt.add(q)
        frontier = nxt
        sizes.append(len(seen))
        if not nxt:
            break
    return sizes


def test_mod_two_collapses_four_pairs_of_letters() -> None:
    """
    The collisions are not arbitrary: every differing component differs by
    exactly 2. Reading a letter mod 2 throws away exactly the information that
    makes it more than a bit.
    """
    groups: dict[tuple, list[int]] = {}
    for i in range(28):
        groups.setdefault(_face(FACES[i], 2), []).append(i)
    collided = [g for g in groups.values() if len(g) > 1]

    assert len(groups) == 24
    assert len(collided) == 4
    for a, b in collided:
        va, vb = list(_to_vec(ENTRIES[a])), list(_to_vec(ENTRIES[b]))
        diffs = [abs(va[k] - vb[k]) for k in range(18) if va[k] != vb[k]]
        assert diffs and all(d == 2 for d in diffs), (ENTRIES[a].char, diffs)

    pairs = {frozenset((ENTRIES[a].char, ENTRIES[b].char)) for a, b in collided}
    assert pairs == {frozenset(p) for p in
                     (("ح", "ل"), ("ش", "ن"), ("ص", "ق"), ("ع", "ي"))}


def test_four_is_the_smallest_modulus_that_separates_the_alphabet() -> None:
    """Two bits per component, not one. That is the arithmetic of the claim."""
    assert len({_face(m, 2) for m in FACES}) == 24
    assert len({_face(m, 3) for m in FACES}) == 27
    assert len({_face(m, 4) for m in FACES}) == 28
    for p in (5, 7, 8, 16, 256):
        assert len({_face(m, p) for m in FACES}) == 28


def test_a_letter_carries_more_than_four_bits_as_an_operator() -> None:
    """
    Not identity alone -- that would be a lookup. As a MAP, composed into
    words, each letter still adds better than four bits over GF(4) and GF(5),
    against a bit stream's one.
    """
    ceiling = math.log2(28)
    assert 4.80 < ceiling < 4.82

    # Depth 3 in the suite; depth 5 enumerates 7.2M maps and belongs in a
    # measurement run, not a test. Recorded from one: at length 5 the figures
    # are 3.22 (mod 2), 4.06 (mod 4) and 4.56 (mod 5).
    for p, floor in ((4, 4.4), (5, 4.6)):
        sizes = _reachable(p, 3)
        per_letter = [math.log2(s) / (i + 1) for i, s in enumerate(sizes)]
        assert per_letter[0] == ceiling, "length 1 must be pure identity"
        assert per_letter[-1] > floor, f"mod {p} fell to {per_letter[-1]:.2f}"
        assert all(x <= ceiling + 1e-9 for x in per_letter), "above the ceiling"


def test_reading_letters_as_bits_costs_about_a_third_of_the_density() -> None:
    """The measured price of mod 2, which is the price of calling them bits."""
    two = [math.log2(s) / (i + 1) for i, s in enumerate(_reachable(2, 3))]
    five = [math.log2(s) / (i + 1) for i, s in enumerate(_reachable(5, 3))]

    assert two[0] < five[0], "mod 2 already loses at length 1"
    assert two[-1] < 3.9 and five[-1] > 4.6
    # The gap widens with length: 19% here, 29% at length 5 in the deeper run.
    assert (five[-1] - two[-1]) / five[-1] > 0.15


def test_the_letter_stream_beats_the_bit_stream_at_every_length() -> None:
    """
    The whole comparison, stated plainly. One pulse of a bit stream is one bit
    at every length; one pulse of a letter stream is four and a half.
    """
    for p in (2, 4, 5):
        for i, s in enumerate(_reachable(p, 3)):
            assert math.log2(s) / (i + 1) > 1.0
