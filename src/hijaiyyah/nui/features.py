"""The 3-component-plus-turning geometric feature, per letter.

The user's framing -- garis lurus (straight line), lengkung (curve), titik
(point/node) as three universal primitives -- names exactly the three
sum-checked families the Master Table already carries: Khat (K, line
strokes, guard G2), Qaws (Q, curve strokes, guard G3), and Nuqthah (N,
points, guard G1). Theta-hat and rho are the fourth piece: total turning and
the part of it NOT explained by curve classification (guard G4, Definition
11.2.1 in Bab III). All five numbers here are read straight off the sealed
Master Table and guards.py -- nothing here is fit or estimated.

One precision note, because cosmic-codex-jim/LIMITS.md exists specifically
to correct readings like this: Theta-hat is the letter's TOTAL turning, not
"the curve component's value". Jim's Theta-hat is 270 degrees, but Jim's own
`rho` is also 3 (all of it) -- its curve component U is 0, so none of that
270 degrees is actually explained by Qaws. Treat (titik, garis, lengkung) as
three independent counts and (theta, rho) as a separate turning summary;
do not read lengkung=270 for Jim specifically, that identity does not hold.
"""

from __future__ import annotations

from typing import Any, Dict, List, NamedTuple

from ..core.guards import _to_vec, compute_rho
from ..core.master_table import MASTER_TABLE

FEATURE_NAMES = ("titik", "garis", "lengkung", "theta", "rho")


class LetterFeatures(NamedTuple):
    """One letter's (or one accumulated vector's) 5-number decomposition."""

    titik: int     #: A_N = Na + Nb + Nd -- point/node count (guard G1)
    garis: int     #: A_K = sum(K) -- straight-line stroke count (guard G2)
    lengkung: int  #: A_Q = sum(Q) -- curve stroke count (guard G3)
    theta: int     #: Theta-hat -- total turning, in units of 90 degrees
    rho: int       #: rho = Theta-hat - U -- turning NOT explained by curves

    def as_tuple(self) -> tuple:
        return (self.titik, self.garis, self.lengkung, self.theta, self.rho)


def vector_features(v: Any) -> LetterFeatures:
    """Decompose any v18-like vector -- a canonical letter, a corrupt one, or
    the running sum of several letters accumulated the way a real HASM
    program does it (rtl/programs/letters.hasm's L_<letter> chain) -- into
    the five geometric numbers. G1-G3 are linear sums, so this is well
    defined and consistent whether `v` is a single canonical letter or a sum
    of several; it does not require the result to still be guard-valid.
    """
    vec = _to_vec(v)
    Na, Nb, Nd = vec[1], vec[2], vec[3]
    Kp, Kx, Ks, Ka, Kc = vec[4], vec[5], vec[6], vec[7], vec[8]
    Qp, Qx, Qs, Qa, Qc = vec[9], vec[10], vec[11], vec[12], vec[13]
    return LetterFeatures(
        titik=Na + Nb + Nd,
        garis=Kp + Kx + Ks + Ka + Kc,
        lengkung=Qp + Qx + Qs + Qa + Qc,
        theta=vec[0],
        rho=compute_rho(vec),
    )


def letter_order() -> List[str]:
    """The 28 canonical characters, index 0..27, Master Table order."""
    return [e.char for e in MASTER_TABLE.all_entries()]


def all_letter_features() -> Dict[str, LetterFeatures]:
    """The 5-number decomposition for all 28 canonical letters."""
    return {e.char: vector_features(e.vector) for e in MASTER_TABLE.all_entries()}


def feature_matrix() -> List[List[int]]:
    """28x5 table, Master Table order -- the embedding NUI's frozen physics
    variant is initialised from (see model.py)."""
    return [list(vector_features(e.vector).as_tuple()) for e in MASTER_TABLE.all_entries()]
