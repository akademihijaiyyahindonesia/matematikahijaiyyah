"""
Exomatrix: 5×5 structured display matrix (Definition 32.1.1).

NOTE ON ORIENTATION. This builds the TRANSPOSE of the matrix Bab II prints.
IIE.2.1 on page 105 puts Theta-hat, Na, Kp, Qp and H* along the first ROW;
the layout below puts them down the first COLUMN. Verified as an exact
transpose on all 28 letters by tests/test_integrity/test_bab_dua.py.

It changes nothing that has been measured. A matrix and its transpose share a
characteristic polynomial, so the GF(2) periods, the primitivity of Jim and
Kha, and the maximal order 31 are identical either way; the zero count is
identical, so sparsity is too; and the emitted sequences come out identical on
all 28, which the transpose alone does not imply and is simply what the
numbers do. Left as it is rather than flipped, because flipping it would
change every downstream measurement's provenance for no gain -- but recorded,
so nobody reading the book beside the code concludes one of them is wrong.


  Row 0: [Θ̂,  U,    ρ,   0,   0  ]
  Row 1: [Na,  Nb,   Nd,  0,   A_N]
  Row 2: [Kp,  Kx,   Ks,  Ka,  Kc ]
  Row 3: [Qp,  Qx,   Qs,  Qa,  Qc ]
  Row 4: [H*,  0,    0,   A_K, A_Q]
"""

from __future__ import annotations

from typing import Any, List

from .guards import compute_U


def build_exomatrix(v: Any) -> List[List[int]]:
    """Build 5×5 Exomatrix from v18 vector or CodexEntry."""
    if hasattr(v, "vector"):
        vec: List[int] = list(v.vector)
    elif isinstance(v, (list, tuple)):
        vec = list(v)
    else:
        raise TypeError(f"Expected vector-like, got {type(v).__name__}")

    theta = vec[0]
    U = compute_U(vec)
    rho = theta - U
    # A_N/A_K/A_Q are read from v₁₈, not recomputed from the components they
    # summarise. Recomputing them makes audit() tautological: R2–R4 compare a
    # matrix cell against the very sum that produced it, so a vector whose
    # stored checksum disagrees with its components would still audit clean.
    # For canonical letters the two are equal — guards G1–G3 enforce that — so
    # this only changes behaviour on the corrupt input the audit exists to catch.
    a_n = vec[14]
    a_k = vec[15]
    a_q = vec[16]

    return [
        [theta, U, rho, 0, 0],
        [vec[1], vec[2], vec[3], 0, a_n],
        [vec[4], vec[5], vec[6], vec[7], vec[8]],
        [vec[9], vec[10], vec[11], vec[12], vec[13]],
        [vec[17], 0, 0, a_k, a_q],
    ]
