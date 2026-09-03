"""
Bab II read against the code — four confirmations and one discrepancy.

Five metric operations, and the book states identities for each. Most hold
exactly. One thing does not match: the code builds the TRANSPOSE of the
exomatrix the book defines, which turns out to change nothing that has been
measured but would confuse anyone comparing the two side by side.
"""
from __future__ import annotations

import itertools
import random
from pathlib import Path

import pytest

from hijaiyyah.core.exomatrix import build_exomatrix
from hijaiyyah.core.guards import _to_vec, compute_U
from hijaiyyah.core.master_table import MASTER_TABLE

ROOT = Path(__file__).resolve().parents[2]
ENTRIES = MASTER_TABLE.all_entries()
VECTORS = [list(_to_vec(e)) for e in ENTRIES]

SUBSPACES = {"theta": [0], "N": [1, 2, 3],
             "K": [4, 5, 6, 7, 8], "Q": [9, 10, 11, 12, 13]}


def _book_exomatrix(v: list[int]) -> list[list[int]]:
    """IIE.2.1 as printed on page 105."""
    u = compute_U(v)
    rho = v[0] - u
    return [[v[0], v[1], v[4], v[9], v[17]],
            [u, v[2], v[5], v[10], 0],
            [rho, v[3], v[6], v[11], 0],
            [0, 0, v[7], v[12], v[15]],
            [0, v[14], v[8], v[13], v[16]]]


def _page(number: int) -> str:
    pymupdf = pytest.importorskip("pymupdf")
    for parent in ROOT.glob("*Matematika Hijaiyyah*"):
        for pdf in parent.rglob(f"{number}.pdf"):
            with pymupdf.open(pdf) as doc:
                return " ".join(" ".join(p.get_text() for p in doc).split())
    pytest.skip("the book PDFs are not in this checkout")


# ══════════════════════════════════════════════════════════════════
#  The discrepancy
# ══════════════════════════════════════════════════════════════════

def test_the_code_builds_the_transpose_of_the_books_exomatrix() -> None:
    """
    IIE.2.1 prints E(h) with Theta-hat, Na, Kp, Qp, H* along the FIRST ROW.
    build_exomatrix puts them down the first COLUMN. It is an exact transpose,
    on all 28 letters.

    It changes nothing that has been measured, and that is worth stating
    precisely rather than waving at: a matrix and its transpose share a
    characteristic polynomial, so the periods, the primitivity of Jim and Kha,
    and the maximal order in GF(2) are all identical either way. The zero
    count is identical too, so sparsity is unaffected. Measured, the emitted
    sequences also come out identical on all 28 -- which is not implied by the
    transpose alone and is simply what the numbers do.

    Pinned so nobody reading the book beside the code concludes one of them
    is wrong about the layout.
    """
    for entry, v in zip(ENTRIES, VECTORS, strict=True):
        code = build_exomatrix(entry)
        book = _book_exomatrix(v)
        assert code == [list(row) for row in zip(*book, strict=True)], entry.char
        assert code != book or all(x == 0 for r in book for x in r)


def test_the_transpose_leaves_every_measured_property_alone() -> None:
    def mul(a: tuple, b: tuple) -> tuple:
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(5)) & 1
                           for j in range(5)) for i in range(5))

    def period(m: list[list[int]]) -> int:
        base = tuple(tuple(x & 1 for x in row) for row in m)
        seen, x, k = {}, base, 1
        while k <= 400:
            if x in seen:
                return k - seen[x]
            seen[x] = k
            x = mul(x, base)
            k += 1
        return -1

    def emit(m: list[list[int]]) -> list[int]:
        mm = [[x & 1 for x in row] for row in m]
        s, out = [1, 0, 0, 0, 0], []
        for _ in range(31):
            out.append(s[0])
            s = [sum(mm[i][j] * s[j] for j in range(5)) & 1 for i in range(5)]
        return out

    for entry, v in zip(ENTRIES, VECTORS, strict=True):
        code, book = build_exomatrix(entry), _book_exomatrix(v)
        assert period(code) == period(book), entry.char
        assert emit(code) == emit(book), entry.char
        assert (sum(1 for r in code for x in r if x)
                == sum(1 for r in book for x in r if x))

    maximal = [e.char for e, v in zip(ENTRIES, VECTORS, strict=True)
               if period(_book_exomatrix(v)) == 31]
    assert maximal == ["ج", "خ"]


# ══════════════════════════════════════════════════════════════════
#  What the book states and the code confirms
# ══════════════════════════════════════════════════════════════════

def test_the_grand_sum_identity_holds() -> None:
    """IIE.2.3 [VF]: sum of E(h) = 2*Theta-hat + 2*A_N + 2*A_K + 2*A_Q + H*."""
    for v in VECTORS:
        total = sum(x for row in _book_exomatrix(v) for x in row)
        assert total == 2 * v[0] + 2 * v[14] + 2 * v[15] + 2 * v[16] + v[17]


def test_the_fifteen_degrees_of_freedom_account_for_all_25_slots() -> None:
    """
    IIE.2.2: 25 slots = 14 core + 5 derived + 1 marker + 5 structural zeros,
    with 14 + 1 = 15 effective. The five zeros are checked as cells that are
    zero on EVERY letter, not merely on some.
    """
    assert 14 + 5 + 1 + 5 == 25

    always_zero = [(i, j) for i in range(5) for j in range(5)
                   if all(_book_exomatrix(v)[i][j] == 0 for v in VECTORS)]
    assert len(always_zero) == 5, always_zero

    text = _page(105)
    assert "15 Derajat Kebebasan" in text or "15 Derajat" in text


def test_the_five_exometric_relations_hold_on_every_letter() -> None:
    """
    IIE.2.2's R1-R5, claimed 140/140. They do hold -- but two of them are
    tautologies as computed here, and that is the same fault this repository
    already found and fixed once in guard_detail: R1 compares Theta-hat with
    U + rho when rho was derived as Theta-hat - U, and R5 compares U with the
    formula that produced it. A check that cannot fail is not a check.
    """
    passes = 0
    for v in VECTORS:
        u = compute_U(v)
        rho = v[0] - u
        passes += (v[0] == u + rho)
        passes += (v[14] == sum(v[1:4]))
        passes += (v[15] == sum(v[4:9]))
        passes += (v[16] == sum(v[9:14]))
        passes += (u == v[10] + v[11] + v[12] + 4 * v[13])
    assert passes == 140

    # The two that cannot fail, demonstrated on a deliberately broken vector.
    broken = [9] + [0] * 17
    u = compute_U(broken)
    assert broken[0] == u + (broken[0] - u), "R1 became falsifiable"
    assert u == broken[10] + broken[11] + broken[12] + 4 * broken[13]


def test_the_four_subspaces_are_orthogonal() -> None:
    """IIA.2.4-2.5: theta (1) + N (3) + K (5) + Q (5) = 14, pairwise orthogonal."""
    assert sum(len(v) for v in SUBSPACES.values()) == 14
    for (a, ia), (b, ib) in itertools.combinations(SUBSPACES.items(), 2):
        assert not set(ia) & set(ib), (a, b)
        for v in VECTORS:
            pa = [v[i] if i in ia else 0 for i in range(14)]
            pb = [v[i] if i in ib else 0 for i in range(14)]
            assert sum(x * y for x, y in zip(pa, pb, strict=True)) == 0


def test_pythagoras_holds_across_the_four_subspaces() -> None:
    """IIA.2.20: the squared norm splits exactly along the decomposition."""
    for v in VECTORS:
        whole = sum(x * x for x in v[:14])
        parts = sum(sum(v[i] * v[i] for i in idx) for idx in SUBSPACES.values())
        assert whole == parts


def test_a_word_and_its_anagram_have_the_same_codex() -> None:
    """
    IIC.2.2. It follows from commutativity of addition, which is why the codex
    of a word says nothing about the order of its letters -- worth knowing
    before anyone treats a codex as an identifier for a string.
    """
    random.seed(9)
    for _ in range(300):
        word = [random.choice(VECTORS) for _ in range(random.randint(2, 6))]
        first = [sum(c) for c in zip(*word, strict=True)]
        random.shuffle(word)
        assert [sum(c) for c in zip(*word, strict=True)] == first
