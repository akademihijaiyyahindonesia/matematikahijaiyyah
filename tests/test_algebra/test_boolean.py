"""The lattice on hybits, and the operation that was wrong before it.

`min` is closed over the sealed table and `max` is not, so the counts here
are the result rather than a coverage detail. They are pinned because a
change to the guards, the table or the operations must not quietly move how
often a lattice result is still a hybit.

One test exists only to keep a mistake from returning. Bitwise `&` on
components reported 782/784 with one exception, and the exception was an
artifact of applying a bit operator to a counting number -- `Qc(Mim) = 1`,
`Qc(Haa) = 2`, `1 & 2 = 0`. The right operation has no exception at all, and
the wrong one is checked here so the difference stays visible.
"""
from __future__ import annotations

import itertools

import pytest

from hijaiyyah.algebra.boolean import (
    hybit_join,
    hybit_meet,
    recompute_aggregates,
)
from hijaiyyah.core.guards import guard_check
from hijaiyyah.core.master_table import MASTER_TABLE

ENTRIES = MASTER_TABLE.all_entries()
VECTORS = [list(e.vector) for e in ENTRIES]
PAIRS = list(itertools.product(range(28), repeat=2))


def _closed(op) -> int:
    return sum(1 for i, j in PAIRS if op(VECTORS[i], VECTORS[j]).valid)


# ── the measured lattice ─────────────────────────────────────────

def test_meet_is_closed_over_the_whole_sealed_table() -> None:
    """Every pair, no exception. `min` cannot raise a component, so `U` never
    outruns Theta-hat and G4 has no way to fail."""
    assert _closed(hybit_meet) == len(PAIRS)


def test_join_is_not_closed_and_g4_is_what_fails() -> None:
    """`max` raises components, `U` grows past Theta-hat, rho goes negative.

    The guard is named, not just counted: a run where join failed the same
    number of times on a different guard would be a different algebra.
    """
    failures = [hybit_join(VECTORS[i], VECTORS[j]) for i, j in PAIRS]
    bad = [r for r in failures if not r.valid]
    assert len(bad) == 100, f"{len(bad)} failures, not 100"
    assert all(r.failed == ("G4",) for r in bad), (
        "join stopped failing exclusively on the cross-constraint")
    assert _closed(hybit_join) == 684


def test_addition_stays_closed_and_meet_matches_it() -> None:
    """The monoid is the reference both are measured against."""
    added = sum(1 for i, j in PAIRS
                if guard_check([x + y for x, y in zip(VECTORS[i], VECTORS[j])]))
    assert added == len(PAIRS), f"(V, +) is no longer closed: {added}/{len(PAIRS)}"
    assert _closed(hybit_meet) == added


# ── why the aggregates are rebuilt ───────────────────────────────

def test_without_rebuilding_aggregates_the_sum_checks_fail() -> None:
    """G1-G3 are sums, so the slot cannot carry op() of the old sums."""
    naive = sum(1 for i, j in PAIRS
                if guard_check([min(x, y) for x, y in zip(VECTORS[i], VECTORS[j])]))
    assert naive < len(PAIRS), "the sum-checks stopped noticing a stale aggregate"
    assert _closed(hybit_meet) > naive


def test_recompute_only_touches_the_three_aggregate_slots() -> None:
    v = [7] * 18
    out = recompute_aggregates(v)
    assert out[14] == sum(v[1:4]) and out[15] == sum(v[4:9]) and out[16] == sum(v[9:14])
    assert out[:14] == v[:14], "an informational component was rewritten"
    assert out[17] == v[17], "H* was rewritten, and nothing may decide its value"


# ── the mistake, kept visible ────────────────────────────────────

def test_bitwise_and_is_not_intersection_and_the_numbers_show_it() -> None:
    """Kept so the wrong operation cannot come back looking like a finding.

    Bitwise AND on counts is meaningless -- Mim has one loop, Haa has two, and
    1 & 2 = 0 says nothing whatever about the two sharing a loop. It produced
    a lone failure that was then read as topological. The right operation
    gives min(1, 2) = 1 and no failure anywhere.
    """
    mim = next(list(e.vector) for e in ENTRIES if e.name == "Mim")
    haa = next(list(e.vector) for e in ENTRIES if e.name == "Haa")
    assert {mim[13], haa[13]} == {1, 2}, (
        f"loop counts are now {mim[13]} and {haa[13]}; the example is stale")
    assert min(mim[13], haa[13]) == 1, "the intersection of one loop and two is one"
    assert (mim[13] & haa[13]) == 0, (
        "1 & 2 no longer collides, so the artifact this test remembers is gone")

    bitwise_closed = sum(
        1 for i, j in PAIRS
        if guard_check(recompute_aggregates(
            [x & y for x, y in zip(VECTORS[i], VECTORS[j])])))
    assert bitwise_closed < _closed(hybit_meet), (
        "the bit operator is now as closed as the lattice meet, which would "
        "mean the counts have stopped being counts")


# ── the result type refuses to hide the verdict ──────────────────

def test_an_invalid_result_names_the_guards_that_rejected_it() -> None:
    bad = next(r for r in (hybit_join(VECTORS[i], VECTORS[j]) for i, j in PAIRS)
               if not r.valid)
    assert bad.valid is False and bad.failed
    good = hybit_meet(VECTORS[0], VECTORS[0])
    assert good.valid is True and good.failed == ()


def test_meet_with_itself_returns_the_letter() -> None:
    """Idempotence, which a lattice owes and a bit operator also happened to
    satisfy -- so it proves less than it looks and is checked anyway."""
    for i, entry in enumerate(ENTRIES):
        assert hybit_meet(VECTORS[i], VECTORS[i]).vector == VECTORS[i], entry.char


def test_a_wrong_width_is_refused_rather_than_padded() -> None:
    with pytest.raises(ValueError, match="18 components"):
        hybit_meet([1, 2, 3], VECTORS[0])
