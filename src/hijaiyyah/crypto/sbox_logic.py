# -*- coding: utf-8 -*-
"""The substitution as logic instead of memory — the router, not the table.

**The gap this closes.** :mod:`hijaiyyah.crypto.cube` computes the S-box once
and reads it out of a 256-entry table. In software that table is a
data-indexed memory access, which is the exact target of the AES cache-timing
attacks (Bernstein 2005; Osvik, Shamir and Tromer 2006): the pattern of cache
lines touched leaks the index, and the index is the state. GAPS.md §6 listed
that as open.

**Why a table was the wrong shape for this system anyway.** The cube takes a
byte per clock. A lookup is a memory transaction — an address, a latency, a
port that one consumer holds at a time — and twenty-five lanes wanting the
same table is twenty-five serialised accesses or twenty-five copies of the
ROM. Logic has none of those properties: it is a routed path with a
propagation delay, it can be instantiated as many times as there are gates,
and the delay does not depend on the value flowing through it. That last
clause is the security property, and it comes free with the shape.

**How.** GF(2⁸) is too wide to invert directly in gates, but every GF(2⁸) is
isomorphic to GF((2⁴)²), and inversion there is cheap: one norm into the
4-bit subfield, one 4-bit inverse, two 4-bit multiplies. Written out, with
A = a_h·y + a_l over y² + y + ν:

    N     = ν·a_h² + a_h·a_l + a_l²          the norm, in GF(2⁴)
    A⁻¹   = (a_h·N⁻¹)·y + ((a_h ⊕ a_l)·N⁻¹)

so the whole substitution is

    x → T → composite inverse → T⁻¹ → affine

where T is the change of basis into the tower and both T and T⁻¹ are
GF(2)-linear, which is to say XOR trees. This is Canright's structure; what is
derived here rather than borrowed is the isomorphism, because the sealed cube
chooses polynomial 0x12B and Canright's constants are for AES's 0x11B.

**Nothing here is hardcoded from a paper.** ν, β and the basis matrices are
searched at import from :data:`cube.POLYNOMIAL`, so if the seal ever selects a
different field the logic follows it instead of drifting from it. The search
minimises XOR weight across T, T⁻¹ and multiplication by ν.

**What this module is and is not.** It is the reference the Verilog is checked
against, and it is bit-exact with ``cube.SBOX`` — that equality is a test, not
a claim. It is *not* a constant-time implementation in Python: CPython's
integers, its ``&`` and its ``^`` are not constant-time, and the 4-bit inverse
here is still written as a lookup because at four bits the hardware is four
LUT4s and the Python is documentation. The timing property belongs to the
silicon, and ``rtl/hijaiyyah_sbox.v`` is where it is real.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from hijaiyyah.crypto.cube import AFFINE_C, POLYNOMIAL

#: GF(2⁴) as x⁴ + x + 1. The subfield the tower stands on.
P4 = 0b10011

#: Width of the field being decomposed.
BITS = 8


def gf4_mul(a: int, b: int) -> int:
    """Multiply in GF(2⁴). Four ANDs and a reduction, in hardware."""
    result = 0
    while b:
        if b & 1:
            result ^= a
        a <<= 1
        if a & 0x10:
            a ^= P4
        b >>= 1
    return result & 0xF


#: The 4-bit inverse. Written as a table because at this width the synthesised
#: form is four LUT4s — one per output bit, four inputs each — which is logic
#: with a fixed delay, not a memory with an address.
GF4_INVERSE: Tuple[int, ...] = (
    0,
    *(next(b for b in range(1, 16) if gf4_mul(a, b) == 1) for a in range(1, 16)),
)


def gf8_mul(a: int, b: int, poly: int = POLYNOMIAL) -> int:
    """Multiply in the sealed GF(2⁸), for checking the isomorphism."""
    result = 0
    while b:
        if b & 1:
            result ^= a
        a <<= 1
        if a & 0x100:
            a ^= poly
        b >>= 1
    return result & 0xFF


def _composite_mul(nu: int):
    def mul(a: int, b: int) -> int:
        ah, al, bh, bl = a >> 4, a & 0xF, b >> 4, b & 0xF
        hh = gf4_mul(ah, bh)
        high = hh ^ gf4_mul(ah, bl) ^ gf4_mul(al, bh)
        low = gf4_mul(hh, nu) ^ gf4_mul(al, bl)
        return (high << 4) | low

    return mul


def _matrix_from_columns(columns: List[int], n: int = BITS) -> List[int]:
    """Row i holds the input bits that XOR into output bit i."""
    return [sum(((columns[j] >> i) & 1) << j for j in range(n)) for i in range(n)]


def _invert(matrix: List[int], n: int = BITS):
    rows = [[matrix[i], 1 << i] for i in range(n)]
    pivot = 0
    for col in range(n):
        found = next((r for r in range(pivot, n) if (rows[r][0] >> col) & 1), None)
        if found is None:
            return None
        rows[pivot], rows[found] = rows[found], rows[pivot]
        for r in range(n):
            if r != pivot and (rows[r][0] >> col) & 1:
                rows[r][0] ^= rows[pivot][0]
                rows[r][1] ^= rows[pivot][1]
        pivot += 1
    out = [0] * n
    for r in range(n):
        out[rows[r][0].bit_length() - 1] = rows[r][1]
    return out


def apply_matrix(matrix: List[int], x: int, n: int = BITS) -> int:
    """One GF(2)-linear map — an XOR tree with no data-dependent branch."""
    return sum((bin(matrix[i] & x).count("1") & 1) << i for i in range(n))


def xor_cost(matrix: List[int]) -> int:
    """Two-input XOR gates an XOR-tree realisation of this matrix needs."""
    return sum(bin(row).count("1") - 1 for row in matrix if row)


def _derive() -> Tuple[int, int, List[int], List[int]]:
    """Search the tower for the cheapest basis, from the sealed polynomial.

    Eight candidate ν make y² + y + ν irreducible; each admits eight roots β
    of the sealed polynomial, one per conjugate. All sixty-four give a correct
    S-box, so the choice is free and is spent on gate count.
    """
    best = None
    for nu in range(16):
        mul = _composite_mul(nu)
        if any(gf4_mul(r, r) ^ r ^ nu == 0 for r in range(16)):
            continue  # y² + y + ν is reducible; no quadratic extension

        def power(a: int, e: int, mul=mul) -> int:
            result = 1
            while e:
                if e & 1:
                    result = mul(result, a)
                a = mul(a, a)
                e >>= 1
            return result

        # β must satisfy the sealed polynomial, so that x ↦ β generates the
        # same field: 0x12B is x⁸ + x⁵ + x³ + x + 1.
        exponents = [i for i in range(9) if (POLYNOMIAL >> i) & 1]
        roots = [
            b
            for b in range(256)
            if 0 == _xor_all(power(b, e) if e else 1 for e in exponents)
        ]
        nu_columns = [gf4_mul(nu, 1 << j) for j in range(4)]
        nu_matrix = _matrix_from_columns(nu_columns, 4)

        for beta in roots:
            basis = [power(beta, i) for i in range(BITS)]
            forward = _matrix_from_columns(basis)
            back = _invert(forward)
            if back is None:
                continue
            cost = xor_cost(forward) + xor_cost(back) + xor_cost(nu_matrix)
            if best is None or cost < best[0]:
                best = (cost, nu, beta, forward, back)

    if best is None:  # pragma: no cover - unreachable for any GF(2⁸)
        raise RuntimeError(f"no tower found for polynomial {POLYNOMIAL:#x}")
    return best[1], best[2], best[3], best[4]


def _xor_all(values) -> int:
    result = 0
    for value in values:
        result ^= value
    return result


#: The tower, derived from the sealed field rather than copied from a paper.
NU, BETA, TO_TOWER, FROM_TOWER = _derive()


def composite_inverse(a: int) -> int:
    """Invert in GF((2⁴)²): one norm, one 4-bit inverse, two 4-bit multiplies."""
    ah, al = a >> 4, a & 0xF
    norm = gf4_mul(gf4_mul(ah, ah), NU) ^ gf4_mul(ah, al) ^ gf4_mul(al, al)
    scale = GF4_INVERSE[norm]
    return (gf4_mul(ah, scale) << 4) | gf4_mul(ah ^ al, scale)


def affine(byte: int, constant: int = AFFINE_C) -> int:
    """The rotate-and-sum tail, identical to :func:`cube._affine`."""
    result = byte
    for shift in (1, 2, 3, 4):
        result ^= ((byte << shift) | (byte >> (BITS - shift))) & 0xFF
    return result ^ constant


def substitute(x: int) -> int:
    """One S-box evaluation with no 256-entry table anywhere in the path."""
    return affine(apply_matrix(FROM_TOWER, composite_inverse(apply_matrix(TO_TOWER, x))))


def report() -> Dict[str, object]:
    """The constants and costs, for the specification and the Verilog."""
    nu_matrix = _matrix_from_columns([gf4_mul(NU, 1 << j) for j in range(4)], 4)
    return {
        "polynomial": POLYNOMIAL,
        "subfield_polynomial": P4,
        "nu": NU,
        "beta": BETA,
        "to_tower": list(TO_TOWER),
        "from_tower": list(FROM_TOWER),
        "affine_constant": AFFINE_C,
        "xor_to_tower": xor_cost(TO_TOWER),
        "xor_from_tower": xor_cost(FROM_TOWER),
        "xor_nu": xor_cost(nu_matrix),
        "table_entries": 0,
    }
