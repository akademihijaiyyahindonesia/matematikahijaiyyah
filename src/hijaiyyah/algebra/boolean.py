"""The lattice on hybits: meet is closed, join is not.

Components of a hybit are **counts** -- `Kc` is how many closed curves a
letter has, `Qc` how many loops. Intersection of counts is `min`, union is
`max`. That is the whole of it, and getting there took one wrong turn worth
recording, because the wrong turn produced a result that looked like a
finding.

**Bitwise operators do not belong here.** The first version of this module
applied `&`, `|` and `^` component-wise and reported that AND was closed on
782 of 784 sealed pairs, with a single exception -- Mim AND Haa -- described
as a *topological* failure of T2. It was nothing of the kind. Mim has one
loop and Haa has two, and `1 & 2 = 0`: an artifact of binary representation,
not a statement that the two letters share no loop. Applying a bit operator to a
counting number produces a number with no geometric meaning, and the
"exception" was that meaninglessness surfacing where a guard could see it.
T2 never failed. The operation was simply not producing letters.

Measured over all 784 ordered pairs, aggregates recomputed:

    min   (meet, intersection)     784 / 784   closed
    a + b (the monoid)             784 / 784   closed
    max   (join, union)            684 / 784   100 failures, every one G4
    |a-b| (symmetric difference)   434 / 784

So `(V, min)` is closed and `(V, max)` is not, and the asymmetry is
structural rather than incidental: `min` can only lower components, so
`rho = Theta-hat - U` has no way to go negative, while `max` raises them and
`U` outruns Theta-hat a hundred times over the sealed table.
"""
from __future__ import annotations

from typing import Callable, List, NamedTuple, Sequence

from ..core.guards import full_guard_check, guard_check

__all__ = ["LatticeResult", "hybit_meet", "hybit_join", "recompute_aggregates"]

#: The three aggregate slots and the component ranges each one sums.
_AGGREGATES = ((14, slice(1, 4)), (15, slice(4, 9)), (16, slice(9, 14)))

_GUARDS = ("G1", "G2", "G3", "G4", "T1", "T2")


class LatticeResult(NamedTuple):
    """The vector, and whether it is still a hybit.

    `meet` is closed, so its `valid` is always True on sealed input -- but the
    field is not dropped for it, because the operation is defined on any
    18-vector and closure was measured, not proved.
    """

    vector: List[int]
    valid: bool
    failed: tuple


def _vec(h) -> List[int]:
    return list(h.vector) if hasattr(h, "vector") else list(h)


def recompute_aggregates(v: Sequence[int]) -> List[int]:
    """Rebuild A_N, A_K and A_Q from the components they sum.

    Without this, G1-G3 fail for arithmetic reasons alone: the guards demand
    `A_N = Na + Nb + Nd`, and an operation applied component-wise puts
    `op(A_N(a), A_N(b))` in the slot instead, which is a different number.

    H* is untouched. No guard constrains it, so nothing here may decide it.
    """
    out = list(v)
    for slot, span in _AGGREGATES:
        out[slot] = sum(out[span])
    return out


def _apply(op: Callable[[int, int], int], a, b) -> LatticeResult:
    va, vb = _vec(a), _vec(b)
    if len(va) != 18 or len(vb) != 18:
        raise ValueError(f"hybits are 18 components, got {len(va)} and {len(vb)}")
    result = recompute_aggregates([op(x, y) for x, y in zip(va, vb)])
    if guard_check(result):
        return LatticeResult(result, True, ())
    detail = full_guard_check(result)
    return LatticeResult(result, False, tuple(g for g in _GUARDS if not detail[g]))


def hybit_meet(a, b) -> LatticeResult:
    """Intersection, component-wise minimum. Closed on the sealed table."""
    return _apply(min, a, b)


def hybit_join(a, b) -> LatticeResult:
    """Union, component-wise maximum. Not closed -- G4 is what gives way."""
    return _apply(max, a, b)
