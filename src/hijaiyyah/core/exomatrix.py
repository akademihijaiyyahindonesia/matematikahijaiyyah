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

from typing import Any, List, Optional, Tuple

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


def _matmul_mod(a: Tuple[Tuple[int, ...], ...], b: Tuple[Tuple[int, ...], ...],
                 p: int) -> Tuple[Tuple[int, ...], ...]:
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(5)) % p
                       for j in range(5)) for i in range(5))


def compose_step(state: Tuple[Tuple[int, ...], ...], next_vector: Any,
                  p: int) -> Tuple[Tuple[int, ...], ...]:
    """One clock tick of compose_mod's own composition: `state` (already a
    reduced matrix) times `next_vector`'s own exomatrix, mod p. compose_mod
    is exactly this, called once per element after seeding `state` with the
    first vector's exomatrix -- exposed separately so a caller can observe
    the running state after EVERY element of a sequence, not only after the
    last one (see nui/clockwork.py)."""
    next_matrix = tuple(tuple(x % p for x in row) for row in build_exomatrix(next_vector))
    return _matmul_mod(state, next_matrix, p)


def compose_mod(vectors: List[Any], p: int) -> Tuple[Tuple[int, ...], ...]:
    """The ORDER-SENSITIVE composition matrix_order's own M, M^2, M^3, ...
    is not: M1 x M2 x M3 x ... in sequence, each `v` in `vectors` built into
    its own exomatrix first. Matrix multiplication does not commute in
    general, so unlike v18 addition (which is what dataset.py's accumulation
    uses, and which is provably order-independent -- see its own docstring)
    THIS composition can depend on the order `vectors` is given in. That is
    the whole reason it exists: it is the one operation in this codebase
    where "which letter first" is not thrown away by the mathematics before
    a test can even ask about it.

    Raises ValueError on an empty list rather than returning an identity
    matrix silently -- a caller that meant to compose something and passed
    nothing should see that, not a quietly-neutral result.
    """
    if not vectors:
        raise ValueError("compose_mod needs at least one vector")
    state = tuple(tuple(x % p for x in row) for row in build_exomatrix(vectors[0]))
    for v in vectors[1:]:
        state = compose_step(state, v, p)
    return state


def gf2_rank(matrix: Tuple[Tuple[int, ...], ...]) -> int:
    """Rank of a 5x5 matrix over GF(2), by Gaussian elimination -- a real,
    order-sensitive property of a composed matrix (rank(A@B) is not in
    general rank(B@A)), used to test whether the ORDER letters are composed
    in has any measurable effect. 0 <= rank <= 5; rank 5 means invertible,
    which over GF(2) is exactly `tail == 1` in matrix_order's own reading.
    """
    rows = [list(row) for row in matrix]
    n = len(rows)
    rank = 0
    for col in range(n):
        pivot = next((r for r in range(rank, n) if rows[r][col] == 1), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for r in range(n):
            if r != rank and rows[r][col] == 1:
                rows[r] = [(a ^ b) for a, b in zip(rows[r], rows[rank], strict=True)]
        rank += 1
    return rank


def matrix_order(v: Any, p: int, cap: int = 20000) -> Tuple[Optional[int], Optional[int]]:
    """(tail, period) of M, M^2, M^3, ... over Z/p, where M is `v`'s exomatrix.

    cosmic-codex-jim/'s own numbers (Jim: period 31 over GF(2), 3124 over
    GF(5), the only letter maximal in two fields) came from exactly this
    computation -- it lived only as a private helper duplicated in
    tests/test_integrity/test_cosmic_codex_jim.py, unusable by anything that
    was not that test file. Read `tail == 1` as "M is already inside its own
    cycle" -- invertible, not merely eventually periodic -- the same reading
    MACHINE.md gives it for Jim.

    `v` need not be a canonical letter or even guard-valid: any 18-component
    vector build_exomatrix accepts works, including the sum of several
    letters accumulated the way a real HASM program does it (see
    rtl/programs/letters.hasm's L_<letter> chain) -- that generality is the
    point of lifting this out of the test file.
    """
    base = tuple(tuple(x % p for x in row) for row in build_exomatrix(v))
    return matrix_order_of(base, p, cap)


def matrix_order_of(matrix: Tuple[Tuple[int, ...], ...], p: int,
                     cap: int = 20000) -> Tuple[Optional[int], Optional[int]]:
    """(tail, period) of matrix, matrix^2, matrix^3, ... over Z/p -- the same
    cycle-detection matrix_order runs, but over any matrix already in hand
    rather than one build_exomatrix constructs from a v18 vector first.
    matrix_order(v, p, cap) is exactly matrix_order_of(build_exomatrix(v)
    reduced mod p, p, cap); this exists separately for a caller whose
    matrix came from somewhere else -- compose_step's running state in
    nui/clockwork.py, for one, where "order of the matrix multiplied out
    SO FAR" is a genuinely different question from "order of one letter's
    own exomatrix" that matrix_order alone cannot answer."""
    seen: dict = {}
    x, k = matrix, 1
    while k <= cap:
        if x in seen:
            return seen[x], k - seen[x]
        seen[x] = k
        x = _matmul_mod(x, matrix, p)
        k += 1
    return None, None
