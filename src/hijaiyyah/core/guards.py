"""
Guard check and audit detail for hybit/codex vectors.

Structural Guards (on raw v18) — Definition 3.3.1, Bab III:
  G1: A_N = Na + Nb + Nd       (Sum-check zona — konsistensi distribusi titik)
  G2: A_K = Kp + Kx + Ks + Ka + Kc  (Sum-check garis — konsistensi count garis)
  G3: A_Q = Qp + Qx + Qs + Qa + Qc  (Sum-check lengkung — konsistensi count lengkung)
  G4: ρ = Θ̂ − U ≥ 0           (Cross-constraint — kekekalan turning)

Topological Guards — Definition 3.3.1, Bab III:
  T1: Ks > 0 ⇒ Qc ≥ 1         (S-curve implies loop presence)
  T2: Kc > 0 ⇒ Qc ≥ 1         (Closed curve implies loop presence)

WHY THERE IS NO G5, AND WHY THE NULL SPACE IS NOT THE ANSWER.

Computing the null space of the 28x18 alphabet returns exactly four column
relations, and three of them are the guards, recovered without being sought:

    A_N = Na + Nb + Nd              G1
    A_K = Kp + Kx + Ks + Ka + Kc    G2
    A_Q = Qp + Qx + Qs + Qa + Qc    G3
    H*  = Ka                        <- nothing checks this

The fourth is exact on all 28 letters, closed under addition, and rejects no
canonical letter. It looks like a missing guard, and adding it takes the
system's corruption detection from 88.1% to 93.1% by closing the one component
that is currently at 0%.

It was added here and then removed, because the first three are DEFINITIONAL
-- A_N *is* the sum, by construction -- while `H* = Ka` is EMPIRICAL WITH ONE
DATA POINT. Twenty-seven letters have both components zero; one letter, Kaf,
has both equal to one. That is the entire evidence. A relation supported by a
single non-trivial sample is a coincidence of the alphabet, not a law about
hybits, and the null space cannot tell the two apart: it returns whatever holds
on the rows it was given.

So H* stays unguarded, and crypto/guarded_record.py is right to exclude it from
payload rather than assume it harmless -- see UNCONSTRAINED there. The honest
position is that one of eighteen components carries no checkable structure, not
that a fitted rule can be dressed up as a seventh guard.


Audit relations R1–R5 (Identity 33.1.1):
  R1: Θ̂ = U + ρ               (Proposition 11.3.1)
  R2: A_N = Na + Nb + Nd       (Definition 12.2.1)
  R3: A_K = ΣK_j               (Definition 12.2.1)
  R4: A_Q = ΣQ_j               (Definition 12.2.1)
  R5: U = Qx + Qs + Qa + 4Qc  (Definition 11.1.1)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _to_vec(v: Any) -> List[int]:
    """
    Normalize input to a list of 18 integers.
    Accepts: CodexEntry (has .vector), list, or tuple.
    """
    if hasattr(v, "vector"):
        return list(v.vector)
    if isinstance(v, (list, tuple)):
        return list(v)
    raise TypeError(f"Expected vector-like, got {type(v).__name__}")


def compute_U(v: Any) -> int:
    """U(h) = Qx + Qs + Qa + 4·Qc  (Definition 11.1.1)."""
    vec = _to_vec(v)
    return vec[10] + vec[11] + vec[12] + 4 * vec[13]


def compute_rho(v: Any) -> int:
    """ρ(h) = Θ̂ − U  (Definition 11.2.1)."""
    vec = _to_vec(v)
    return vec[0] - compute_U(vec)


def guard_check(v: Any) -> bool:
    """
    Check all 6 guards (4 structural + 2 topological).
    Returns True if all pass.
    Complexity: O(1) — fixed number of additions + comparisons.

    Structural:
      G1: A_N = Na + Nb + Nd
      G2: A_K = Kp + Kx + Ks + Ka + Kc
      G3: A_Q = Qp + Qx + Qs + Qa + Qc
      G4: ρ = Θ̂ − (Qx + Qs + Qa + 4·Qc) ≥ 0

    Topological:
      T1: Ks > 0 ⇒ Qc ≥ 1
      T2: Kc > 0 ⇒ Qc ≥ 1
    """
    vec = _to_vec(v)

    # Structural guards
    U = compute_U(vec)
    rho = vec[0] - U

    g1 = vec[14] == vec[1] + vec[2] + vec[3]
    g2 = vec[15] == vec[4] + vec[5] + vec[6] + vec[7] + vec[8]
    g3 = vec[16] == vec[9] + vec[10] + vec[11] + vec[12] + vec[13]
    g4 = rho >= 0

    # Topological guards (Definition 3.3.1)
    # T1: v[6]=Ks > 0 ⇒ v[13]=Qc ≥ 1
    t1 = vec[13] >= 1 if vec[6] > 0 else True
    # T2: v[8]=Kc > 0 ⇒ v[13]=Qc ≥ 1
    t2 = vec[13] >= 1 if vec[8] > 0 else True

    return g1 and g2 and g3 and g4 and t1 and t2


def full_guard_check(v: Any) -> Dict[str, bool]:
    """
    Check all 6 guards with per-guard results.
    Returns dict with G1–G4, T1, T2, and overall status.
    Complexity: O(1).
    """
    vec = _to_vec(v)

    U = compute_U(vec)
    rho = vec[0] - U

    g1 = vec[14] == vec[1] + vec[2] + vec[3]
    g2 = vec[15] == vec[4] + vec[5] + vec[6] + vec[7] + vec[8]
    g3 = vec[16] == vec[9] + vec[10] + vec[11] + vec[12] + vec[13]
    g4 = rho >= 0
    t1 = vec[13] >= 1 if vec[6] > 0 else True
    t2 = vec[13] >= 1 if vec[8] > 0 else True

    return {
        "G1": g1,
        "G2": g2,
        "G3": g3,
        "G4": g4,
        "T1": t1,
        "T2": t2,
        "all_pass": g1 and g2 and g3 and g4 and t1 and t2,
    }


def guard_detail(v: Any, carried_rho: Optional[int] = None) -> Dict[str, Any]:
    """The audit relations, with detailed output — and one of them used to be
    a tautology.

    **R5 could not fail.** It read ``U == compute_U(vec)`` two lines after
    ``U = compute_U(vec)``, so it compared a value with itself. Measured over
    every letter, every component, every value in the nibble domain and twenty
    thousand random vectors — 28,064 in all — R1 failed 21,490 times, R2
    21,386, R3 22,503, R4 22,499, T1 1,497, T2 1,505, and **R5 zero**. A check
    that never fails is not a check, and the count advertised seven where six
    were doing work.

    R1 carried a smaller version of the same fault: ``vec[0] == U + rho`` with
    ``rho = vec[0] - U`` is an identity, so only its second conjunct
    (``rho >= 0``, which is G4) was ever load-bearing. It now says that.

    **The real seventh is the carried residue.** §IC.1.24's identity
    Θ̂ = U + ρ only tests anything when ρ arrives from outside — off a wire, out
    of a record — rather than being recomputed from the vector it is meant to
    check. That is the gap :mod:`hijaiyyah.crypto.guarded_record` documents:
    G4 is an inequality, so raising Θ̂ never violates it, and only a carried ρ
    closes it. Supply ``carried_rho`` and R7 becomes a check; omit it and R7
    reports ``None``, because reporting ``True`` for a test that did not run
    is how R5 survived this long.

    Args:
        v: The codex vector.
        carried_rho: The residue as received, not as recomputed.
    """
    vec = _to_vec(v)

    U = compute_U(vec)
    rho = vec[0] - U

    R1 = rho >= 0                                    # G4: Θ̂ ≥ U
    R2 = vec[14] == vec[1] + vec[2] + vec[3]
    R3 = vec[15] == vec[4] + vec[5] + vec[6] + vec[7] + vec[8]
    R4 = vec[16] == vec[9] + vec[10] + vec[11] + vec[12] + vec[13]

    # Topological guards
    T1 = vec[13] >= 1 if vec[6] > 0 else True
    T2 = vec[13] >= 1 if vec[8] > 0 else True

    # The seventh throw: the identity, against a residue from outside.
    R7 = None if carried_rho is None else (vec[0] == U + carried_rho)

    checks = [R1, R2, R3, R4, T1, T2]
    if R7 is not None:
        checks.append(R7)

    return {
        "R1": R1,
        "R2": R2,
        "R3": R3,
        "R4": R4,
        "R7": R7,
        "T1": T1,
        "T2": T2,
        "U": U,
        "rho": rho,
        "all_pass": all(checks),
    }
