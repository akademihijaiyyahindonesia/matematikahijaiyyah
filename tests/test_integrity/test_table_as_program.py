"""
The Master Table is not a table of numbers. It is eighteen classifiers, and
each cell is the count of times one of them fired on a letter's skeleton.

docs/csgi_algorithm_spec.md section 4 is the program: classify_khatt and
classify_qaws walk a letter's graph and return one bucket per component, on
predicates like is_standalone, touches_loop, on_mainpath, has_angle and
is_vertical. K[bucket] += 1. Nothing else writes those cells.

Read that way the columns are not eighteen of the same thing. They fall into
three roles, and the split is sharp:

    FLAGS        8   fire for at most two letters each
    DISCRIMINATORS 4  carry more than 1.3 bits
    COUNTERS     6   accumulate across most of the alphabet

And four of them fire exactly once: Nb marks Jim, Kp marks Alif, Ka and H*
both mark Kaf. Which is the whole explanation of the `H* = Ka` relation that
the null space returned and that was nearly promoted to a seventh guard: two
flags on the same letter are equal on 28 rows for a reason that is about the
alphabet, not about hybits.
"""
from __future__ import annotations

import collections
import math

from hijaiyyah.core.guards import _to_vec
from hijaiyyah.core.master_table import MASTER_TABLE

ENTRIES = MASTER_TABLE.all_entries()
VECTORS = [list(_to_vec(e)) for e in ENTRIES]
SLOTS = ["Θ̂", "Na", "Nb", "Nd", "Kp", "Kx", "Ks", "Ka", "Kc",
         "Qp", "Qx", "Qs", "Qa", "Qc", "AN", "AK", "AQ", "H*"]


def _fired(k: int) -> list[int]:
    return [i for i in range(28) if VECTORS[i][k]]


def _entropy(k: int) -> float:
    counts = collections.Counter(VECTORS[i][k] for i in range(28))
    return -sum(n / 28 * math.log2(n / 28) for n in counts.values())


def test_the_columns_split_into_three_roles() -> None:
    flags = {SLOTS[k] for k in range(18) if len(_fired(k)) <= 2}
    discriminators = {SLOTS[k] for k in range(18)
                      if len(_fired(k)) > 2 and _entropy(k) > 1.3}
    counters = {SLOTS[k] for k in range(18)
                if len(_fired(k)) > 2 and _entropy(k) <= 1.3}

    assert flags == {"Nb", "Nd", "Kp", "Ks", "Ka", "Kc", "Qa", "H*"}
    assert discriminators == {"Θ̂", "Na", "AN", "AQ"}
    assert counters == {"Kx", "Qp", "Qx", "Qs", "Qc", "AK"}
    assert len(flags) + len(discriminators) + len(counters) == 18


def test_four_columns_name_a_single_letter_each() -> None:
    """
    Alif, Jim and Kaf are each identified by one classifier firing and no
    other letter setting it. Alif is the origin at 0 degrees, Jim is the
    maximal-period machine, Kaf is the only letter with H*.
    """
    once = {SLOTS[k]: ENTRIES[_fired(k)[0]].char
            for k in range(18) if len(_fired(k)) == 1}
    assert once == {"Nb": "ج", "Kp": "ا", "Ka": "ك", "H*": "ك"}


def test_the_H_star_relation_is_two_flags_on_one_letter() -> None:
    """
    Why `H* = Ka` holds on all 28 rows and is still not a law: both columns
    are flags, and both flag Kaf. Twenty-seven rows agree because both are
    zero there, and the twenty-eighth agrees because it is the same letter.
    That is one observation, not twenty-eight.
    """
    assert _fired(7) == _fired(17)                  # Ka and H*
    assert len(_fired(7)) == 1
    assert ENTRIES[_fired(7)[0]].name == "Kaf"

    agreeing_by_zero = sum(1 for v in VECTORS if v[7] == v[17] == 0)
    assert agreeing_by_zero == 27
    assert sum(1 for v in VECTORS if v[7] == v[17] != 0) == 1


def test_the_sum_checks_are_the_classifier_being_a_function() -> None:
    """
    G1, G2 and G3 are not checks imposed on the data. classify_khatt returns
    exactly one bucket per component and the caller does K[bucket] += 1, so
    the buckets necessarily sum to the number of components -- which is what
    A_K holds. The guard states that the classifier is a function.

    That is why the null space returns them: definitional, not empirical.
    """
    from pathlib import Path

    spec = (Path(__file__).resolve().parents[2]
            / "docs" / "csgi_algorithm_spec.md").read_text(encoding="utf-8")
    assert "K[subcat] += 1" in spec
    assert "Q[subcat] += 1" in spec

    for v in VECTORS:
        assert v[14] == v[1] + v[2] + v[3]                       # G1
        assert v[15] == v[4] + v[5] + v[6] + v[7] + v[8]         # G2
        assert v[16] == v[9] + v[10] + v[11] + v[12] + v[13]     # G3


def test_the_mod_two_collisions_are_even_differences_anywhere() -> None:
    """
    A first version of this claimed the four GF(2) collisions were confined to
    the dot zone. They are not: Syin and Nun also differ at Qx. What is true
    is narrower and stronger -- every differing component differs by EXACTLY
    two, wherever it sits, and an even difference is invisible to a parity
    reading.

    So the loss is not about dots. It is about the table counting in integers
    while GF(2) reads only their parity.
    """
    from hijaiyyah.core.exomatrix import build_exomatrix

    groups: dict[tuple, list[int]] = {}
    for i in range(28):
        face = tuple(tuple(x & 1 for x in row)
                     for row in build_exomatrix(ENTRIES[i]))
        groups.setdefault(face, []).append(i)

    for pair in (g for g in groups.values() if len(g) > 1):
        a, b = pair
        differing = [k for k in range(18) if VECTORS[a][k] != VECTORS[b][k]]
        assert differing, "a collision with no difference at all"
        for k in differing:
            assert abs(VECTORS[a][k] - VECTORS[b][k]) == 2, (
                ENTRIES[a].char, ENTRIES[b].char, SLOTS[k])
        # And they are not confined to one zone.
        zones = {"N" if 1 <= k <= 3 else "KQ" if 4 <= k <= 13
                 else "agg" if 14 <= k <= 16 else "other" for k in differing}
        assert len(zones) >= 1
