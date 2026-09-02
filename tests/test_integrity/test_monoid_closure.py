"""
Closure, tested the way `Hybit.__add__` relies on it.

`__add__` returns `Hybit(result, _skip_check=True)`. Nothing validates the sum;
the object invariant rests entirely on Proposition 3.2.1 being true. That is a
defensible optimisation and an undefended one: if closure ever broke, addition
would hand back an invalid hybit and no check anywhere would notice.

What stood before this file: three assertions over ONE pair (ب, س), covering
G1-G4 and never T1 or T2 -- and re-deriving the guard arithmetic inline instead
of calling the guard, so a change to the guard could not reach them.

And a second thing this pins. `guard_check` is NOT a membership test for V.
The book defines V as a subset of N_0^18, so non-negativity is part of the
domain and the guards are what is checked ON that domain. `guard_check` omits
it, which means -h passes for every letter whose rho is 0 -- ten of the
twenty-eight. The domain check lives in Hybit.__init__ and that is what keeps
the object invariant; the free function alone does not.
"""
from __future__ import annotations

import itertools
import random

from hijaiyyah.core.guards import _to_vec, compute_U, full_guard_check, guard_check
from hijaiyyah.core.hybit import Hybit
from hijaiyyah.core.master_table import MASTER_TABLE

VECTORS = [list(_to_vec(entry)) for entry in MASTER_TABLE.all_entries()]


def _add(a: list[int], b: list[int]) -> list[int]:
    return [x + y for x, y in zip(a, b, strict=True)]


def test_every_letter_is_in_the_valid_set_to_begin_with() -> None:
    assert len(VECTORS) == 28
    for i, v in enumerate(VECTORS):
        assert guard_check(v), (i, full_guard_check(v))
        assert all(x >= 0 for x in v), i


def test_closure_holds_for_every_ordered_pair_not_for_one() -> None:
    """
    784 pairs, through the guard itself rather than a copy of its arithmetic.
    The old test checked one pair and inlined the formulas, so it could pass
    while the guard it was supposed to be about had changed underneath it.
    """
    failures = [
        (a, b, full_guard_check(_add(VECTORS[a], VECTORS[b])))
        for a, b in itertools.product(range(28), repeat=2)
        if not guard_check(_add(VECTORS[a], VECTORS[b]))
    ]
    assert not failures, failures[:3]


def test_closure_covers_the_topological_guards_too() -> None:
    """
    T1 and T2 were never in the closure test. They are implications, so they
    are the ones that could fail without any sum-check noticing: Ks > 0 must
    imply Qc >= 1, and addition can raise Ks.
    """
    seen_ks = False
    for a, b in itertools.product(range(28), repeat=2):
        s = _add(VECTORS[a], VECTORS[b])
        status = full_guard_check(s)
        assert status["T1"] and status["T2"], (a, b, status)
        if s[6] > 0:                      # Ks in the sum
            seen_ks = True
            assert s[13] >= 1, (a, b)     # so Qc must be too
    assert seen_ks, "no sum ever raised Ks — the T1 check was vacuous"


def test_the_topological_guards_actually_reject_what_they_are_for() -> None:
    """
    The closure test above verifies the PROPERTY directly, so it stays green
    even if T1 is replaced by `True` -- correct for closure, and no evidence
    that the guard detects anything. Sabotage caught exactly that. This is the
    other half: a vector that violates T1 must be rejected by the guard.
    """
    # Ks > 0 with Qc == 0: an S-curve claimed with no loop to sit in.
    v = [0] * 18
    v[6] = 1                      # Ks
    v[15] = 1                     # A_K, so G2 still balances
    assert full_guard_check(v)["T1"] is False, "T1 does not reject Ks>0, Qc=0"
    assert not guard_check(v)

    # And T2 likewise, through Kc.
    w = [0] * 18
    w[8] = 1                      # Kc
    w[15] = 1
    assert full_guard_check(w)["T2"] is False, "T2 does not reject Kc>0, Qc=0"
    assert not guard_check(w)

    # With the loop present, both pass — so the rejection was about T1/T2 and
    # not about some other guard failing first.
    for bad in (v, w):
        ok = list(bad)
        ok[13] = 1                # Qc
        ok[16] = 1                # A_Q balances G3
        ok[0] = 4                 # Theta-hat >= U = 4*Qc, so G4 holds
        status = full_guard_check(ok)
        assert status["T1"] and status["T2"], status
        assert guard_check(ok), status


def test_closure_survives_depth_not_just_one_addition() -> None:
    """A monoid claim is about arbitrary sums, not pairs."""
    random.seed(7)
    for _ in range(2000):
        terms = [random.choice(VECTORS) for _ in range(5)]
        total = [sum(col) for col in zip(*terms, strict=True)]
        assert guard_check(total), terms


def test_zero_is_the_identity_and_addition_commutes() -> None:
    zero = [0] * 18
    assert guard_check(zero)
    for v in VECTORS:
        assert _add(v, zero) == v
    for a, b in itertools.product(range(28), repeat=2):
        assert _add(VECTORS[a], VECTORS[b]) == _add(VECTORS[b], VECTORS[a])


def test_the_guard_alone_is_not_a_membership_test_for_V() -> None:
    """
    This is what makes it a monoid rather than a group -- and the reason is the
    N_0 domain, NOT the guards. Negating a hybit keeps every sum-check (they
    are linear), flips rho to -rho (which still passes when rho is 0), and
    makes T1/T2 vacuous (Ks < 0 is not > 0). So -h passes the guards for every
    letter with rho == 0.
    """
    passing = [i for i, v in enumerate(VECTORS) if guard_check([-x for x in v])]
    zero_rho = [i for i, v in enumerate(VECTORS) if v[0] - compute_U(v) == 0]
    assert passing == zero_rho, (passing, zero_rho)
    assert len(passing) == 10, f"{len(passing)} of 28 — the count moved"

    # The domain check is in the constructor, and that is what holds the line.
    for i in passing:
        negated = [-x for x in VECTORS[i]]
        try:
            Hybit(negated)
        except ValueError as exc:
            assert "non-negative" in str(exc)
        else:
            raise AssertionError(f"letter {i}: Hybit accepted a negated vector")


def test_addition_skips_validation_so_the_theorem_is_the_only_guard() -> None:
    """
    Pinning the dependency itself. If __add__ ever starts validating, this
    test should be deleted rather than worked around -- but while it does not,
    the closure tests above are the only thing standing between the theorem
    and an invalid hybit handed back to a caller.
    """
    import inspect

    source = inspect.getsource(Hybit.cadd)
    assert "_skip_check=True" in source
    for a, b in itertools.product(range(0, 28, 3), repeat=2):
        total = Hybit(VECTORS[a]) + Hybit(VECTORS[b])
        assert total.is_valid()
        assert all(x >= 0 for x in total.to_list())
