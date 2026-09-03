"""
Bab I read against the code — what it states, and one sentence that overstates.

The book is the reference and the code is measured against it, so a place
where they disagree is worth pinning precisely rather than smoothing over.
Two of the three findings here confirm the book. The third does not, and the
distinction it turns on is real: LINEAR INDEPENDENCE IS NOT INJECTIVITY.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from hijaiyyah.core.constants import V14_SLOTS
from hijaiyyah.core.guards import _to_vec, compute_U
from hijaiyyah.core.master_table import MASTER_TABLE

ROOT = Path(__file__).resolve().parents[2]
ENTRIES = MASTER_TABLE.all_entries()
VECTORS = [list(_to_vec(e)) for e in ENTRIES]
V14 = [v[:14] for v in VECTORS]


def _find_page(number: int) -> Path | None:
    for parent in ROOT.glob("*Matematika Hijaiyyah*"):
        for pdf in parent.rglob(f"{number}.pdf"):
            return pdf
    return None


def _page(number: int) -> str:
    pymupdf = pytest.importorskip("pymupdf")
    path = _find_page(number)
    if path is None:
        pytest.skip("the book PDFs are not in this checkout")
    with pymupdf.open(path) as doc:
        return " ".join(" ".join(p.get_text() for p in doc).split())


def _rank(rows: list[list[int]]) -> int:
    a = [[Fraction(x) for x in r] for r in rows]
    r = 0
    if not a or not a[0]:
        return 0
    for c in range(len(a[0])):
        p = next((i for i in range(r, len(a)) if a[i][c]), None)
        if p is None:
            continue
        a[r], a[p] = a[p], a[r]
        for i in range(len(a)):
            if i != r and a[i][c]:
                f = a[i][c] / a[r][c]
                a[i] = [x - f * y for x, y in zip(a[i], a[r], strict=True)]
        r += 1
    return r


# ══════════════════════════════════════════════════════════════════
#  ID.1.3 — H* is a definition, not a measurement
# ══════════════════════════════════════════════════════════════════

def test_H_star_is_the_hamzah_marker_and_is_defined_not_measured() -> None:
    """
    ID.1.3, page 74:  H* : H_28 -> {0,1},  H*(kaf) = 1,  H*(h) = 0 otherwise.

    That settles a question three earlier commits circled. H* was described
    here as "a gap in the guard" -- the one component at 0% detection with no
    honest law to bind it. It is not a gap. It is an INDICATOR FUNCTION for a
    NON-GEOMETRIC feature, labelled [DP], and no geometric constraint can bind
    it because it is not geometry. Being outside the guard's domain is not the
    same as being a hole in it.

    It also explains the `H* = Ka` relation the null space returned: Kaf is
    simply the only letter with Ka > 0, so the two indicator columns coincide.
    """
    marked = [i for i, v in enumerate(VECTORS) if v[17]]
    assert len(marked) == 1
    assert ENTRIES[marked[0]].name == "Kaf"
    assert set(v[17] for v in VECTORS) == {0, 1}

    text = _page(74)
    assert "Marker Hamzah" in text
    assert "[DP]" in text or "DP]" in text


def test_the_three_aggregates_carry_no_new_information() -> None:
    """
    ID.1.2: "turunan deterministik dari komponen inti (N,K,Q), tidak membawa
    informasi baru". Measured: they add nothing to the rank.
    """
    assert _rank(VECTORS) == _rank(V14) == 14
    assert list(V14_SLOTS) == [
        "Θ̂", "Na", "Nb", "Nd", "Kp", "Kx", "Ks", "Ka", "Kc",
        "Qp", "Qx", "Qs", "Qa", "Qc"]

    for v in VECTORS:
        assert v[14] == sum(v[1:4])
        assert v[15] == sum(v[4:9])
        assert v[16] == sum(v[9:14])


# ══════════════════════════════════════════════════════════════════
#  ID.1.1 — the rank holds; the sentence after it does not
# ══════════════════════════════════════════════════════════════════

def test_rank_of_the_fourteen_is_fourteen_as_the_book_says() -> None:
    assert _rank(V14) == 14
    text = _page(74)
    assert "rank" in text.lower() and "14" in text


def test_dropping_one_dimension_does_not_always_collide() -> None:
    """
    ID.1.1 says: "rank(M14)=14 -- seluruh 14 dimensi diperlukan secara
    aljabar. Penghapusan satu dimensi menyebabkan collision."

    The first half is exact and verified above. The second half overstates,
    and the reason is that it treats two different properties as one:

      LINEAR INDEPENDENCE  no column is a combination of the others.
                           True of all fourteen, which is what rank 14 means.

      INJECTIVITY          no two letters agree on the rest.
                           True of only FOUR: Theta-hat, Na, Nb, Nd.

    Dropping any of the ten K and Q components leaves all 28 letters
    distinguishable. Full rank does not imply that -- a column can be
    linearly independent and still carry nothing that separates any pair.

    The four that do matter are the turning and the three dot zones, which is
    consistent with them carrying the most entropy of the eighteen.
    """
    assert len({tuple(v) for v in V14}) == 28, "v14 is not injective to begin with"

    collides = [k for k in range(14)
                if len({tuple(x for j, x in enumerate(v) if j != k)
                        for v in V14}) < 28]
    assert collides == [0, 1, 2, 3], [V14_SLOTS[k] for k in collides]
    assert len(collides) == 4

    # And rank stays full without any single column, which is the point:
    # independence survives the drop, injectivity mostly does too.
    for k in (0, 4, 13):
        assert _rank([[x for j, x in enumerate(v) if j != k] for v in V14]) == 13


# ══════════════════════════════════════════════════════════════════
#  IC.1.27 — the Mod-4 theorem
# ══════════════════════════════════════════════════════════════════

def test_the_mod_four_gate_holds_on_all_28() -> None:
    """
    IC.1.27, from Umlaufsatz: a closed MainPath turns a whole number of full
    turns, so under Q90 its Theta-hat is 0 mod 4. Contrapositive, IC.1.28:
    Theta-hat mod 4 != 0 means the MainPath is certainly open -- an O(1)
    topological test that never touches the skeleton.
    """
    text = _page(72) + " " + _page(73)
    assert "Mod-4" in text
    assert "Umlaufsatz" in text

    closed_possible = [e.char for e, v in zip(ENTRIES, VECTORS, strict=True)
                       if v[0] % 4 == 0]
    assert set(closed_possible) == set("ا س ش ط ظ م هـ".split())

    # Every letter whose whole turning comes from closed loops is 0 mod 4,
    # because U counts each loop as exactly four quarters.
    for v in VECTORS:
        if v[0] == 4 * v[13] and v[13] > 0:
            assert v[0] % 4 == 0


def test_a_loop_does_not_make_the_mainpath_closed() -> None:
    """
    IC.1.29, flagged in the book as a non-obvious finding: Fa and Waw both
    have Qc = 1 and Theta-hat = 5, so 5 mod 4 = 1 and the MainPath is open.
    The loop exists; the path passes through it and leaves.
    """
    by_char = {e.char: v for e, v in zip(ENTRIES, VECTORS, strict=True)}
    for char in ("ف", "و"):
        v = by_char[char]
        assert v[13] == 1, char           # has a closed loop
        assert v[0] == 5, char            # yet turns five quarters
        assert v[0] % 4 != 0, char        # so the path is open

    looped_but_open = [e.char for e, v in zip(ENTRIES, VECTORS, strict=True)
                       if v[13] > 0 and v[0] % 4 != 0]
    assert set(looped_but_open) == set("ص ض ف ق و".split())
    assert compute_U(by_char["ف"]) == 4    # the loop's own four quarters
