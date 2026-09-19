"""The hijrah lab, held to hijrah's own definition before a board sees it.

rtl/scripts/hijrah_board.py runs rtl/programs/hijrah_sweep.hasm and compares its
counts with the definition in src/. These tests pin what would let the pair
agree with each other while both answered the wrong question -- which is not
hypothetical: the first version of both counted the 784 products of length 2
ALONE, got 305 / 630 / 605 / 694, and agreed perfectly. hijrah's densities are
cumulative (words of length 1 OR 2), and the right numbers are 321 / 649 / 625 /
714.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))
sys.path.insert(0, str(ROOT / "tests" / "test_integrity"))

from hijrah_board import MODULI, expected, run_interpreter, split  # noqa: E402
from test_hijrah import _reachable  # noqa: E402


def test_the_reference_is_hijrahs_own_cumulative_count() -> None:
    """Tie the tool to test_hijrah.py's _reachable, the definition the README
    densities come from -- not to a count that merely looks like it."""
    want = expected()
    for p in MODULI:
        sizes = _reachable(p, 2)
        entry = want[p]
        assert isinstance(entry, dict)
        assert entry["len1"] == sizes[0], p
        assert entry["len2"] == sizes[1], p


def test_the_four_gf2_collisions_are_the_ones_hijrah_names() -> None:
    entry = expected()[2]
    assert isinstance(entry, dict)
    assert entry["pairs"] == [(6, 23), (13, 25), (14, 21), (18, 28)]


def test_the_program_agrees_in_the_interpreter() -> None:
    """The whole sweep, all four moduli: faces, counts, pairs."""
    got, want = split(run_interpreter()), expected()
    assert got["faces"] == want["faces"]
    for p in MODULI:
        g, w = got[p], want[p]
        assert isinstance(g, dict) and isinstance(w, dict)
        for key in ("len1", "pairs", "len2"):
            assert g[key] == w[key], (p, key, g[key], w[key])


def test_a_wrong_count_is_seen_by_the_split_and_comparison() -> None:
    """R3 on the comparator: a stream with the length-2 count of mod 5 off by
    one must not read as agreement."""
    want = expected()
    stream: list[int] = list(want["faces"])  # type: ignore[arg-type]
    for p in MODULI:
        w = want[p]
        assert isinstance(w, dict)
        flat = [x for pair in w["pairs"] for x in pair]
        len2 = w["len2"] - (1 if p == 5 else 0)
        stream += [p, w["len1"], len(w["pairs"]), *flat, len2, 0, 0]
    got = split(stream)
    g5 = got[5]
    assert isinstance(g5, dict)
    w5 = want[5]
    assert isinstance(w5, dict)
    assert g5["len2"] != w5["len2"]
