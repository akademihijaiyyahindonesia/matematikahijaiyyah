"""
The cosmic-codex-jim/ folder states numbers about one matrix. These bind them
to the code, so the folder cannot become a story about a letter.

What is actually claimed there is narrow: the 5x5 face built from Jim's
18-component vector, read as a linear map, has maximal multiplicative order in
GF(2) and in GF(5), and is the only letter of the twenty-eight that reaches the
maximum in more than one field. Everything else in the folder is either a
consequence of that or a record of a reading that failed.
"""
from __future__ import annotations

import re
from pathlib import Path

from hijaiyyah.core.exomatrix import build_exomatrix
from hijaiyyah.core.guards import _to_vec, compute_U
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "cosmic-codex-jim"
NAMES = ("README.md", "MACHINE.md", "WAVE.md", "LIMITS.md")

ENTRIES = MASTER_TABLE.all_entries()
JIM, KHA = 4, 6


def _text(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def _mul(a: tuple, b: tuple, p: int) -> tuple:
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(5)) % p
                       for j in range(5)) for i in range(5))


def _order(entry, p: int, cap: int = 20000) -> tuple[int, int] | tuple[None, None]:
    """(tail, period) of M, M^2, ... over Z/p."""
    base = tuple(tuple(x % p for x in row) for row in build_exomatrix(entry))
    seen: dict[tuple, int] = {}
    x, k = base, 1
    while k <= cap:
        if x in seen:
            return seen[x], k - seen[x]
        seen[x] = k
        x = _mul(x, base, p)
        k += 1
    return None, None


def test_the_folder_exists_and_indexes_itself() -> None:
    assert DOCS.is_dir()
    assert {p.name for p in DOCS.glob("*.md")} == set(NAMES)
    readme = _text("README.md")
    for name in NAMES[1:]:
        assert f"({name})" in readme, name


def test_jim_is_the_only_letter_maximal_in_two_fields() -> None:
    """
    The one claim the folder rests on. Kha reaches the maximum in GF(2) only,
    Ba in GF(3) only, and nothing reaches it in GF(7) at all.
    """
    reached: dict[int, list[str]] = {}
    for p in (2, 3, 5):
        top = p**5 - 1
        reached[p] = [e.char for e in ENTRIES if _order(e, p)[1] == top]

    assert reached[2] == ["ج", "خ"]
    assert reached[3] == ["ب"]
    assert reached[5] == ["ج"]

    counts = {c: sum(1 for v in reached.values() if c in v) for c in "جخب"}
    assert counts["ج"] == 2
    assert counts["خ"] == counts["ب"] == 1

    # Nothing is primitive over GF(7); the best is exactly half the maximum.
    best = max(_order(e, 7)[1] or 0 for e in ENTRIES)
    assert best == (7**5 - 1) // 2 == 8403


def test_the_periods_the_docs_print_are_the_periods_measured() -> None:
    jim = ENTRIES[JIM]

    # Parse the table row, not the file. Every period also appears in the
    # prose beside it, so a substring search passes while the table lies --
    # the fourth time that hole has turned up in these test files.
    rows = dict(
        (m.group(1), int(m.group(3)))
        for m in re.finditer(
            r"^\s{2}(GF\(\d+\)|mod \d+)\s+(\d+)\s+(\d+)\s",
            _text("MACHINE.md"), re.M))

    for p, period in ((2, 31), (3, 3), (4, 62), (5, 3124),
                      (7, 2400), (8, 124), (16, 248), (256, 3968)):
        assert _order(jim, p)[1] == period, p
        key = f"GF({p})" if p in (2, 3, 5, 7) else f"mod {p}"
        assert rows[key] == period, (key, rows.get(key), period)
    assert len(rows) == 8

    # Tail 1: the matrix is already inside its own cycle, so it is invertible.
    assert _order(jim, 2)[0] == 1
    assert "ekor 1" in _text("MACHINE.md").lower()

    # The powers of two are 31 * 2^k, which the doc claims out loud.
    for k, p in enumerate((2, 4, 8, 16)):
        assert _order(jim, p)[1] == 31 * 2**k


def test_the_facts_on_the_readme_card_are_read_from_the_code() -> None:
    readme = _text("README.md")
    v = list(_to_vec(ENTRIES[JIM]))

    assert v[0] == 3 and v[0] * 90 == 270
    assert v[0] - compute_U(v) == 3 and compute_U(v) == 0
    nonzero = sum(1 for row in build_exomatrix(ENTRIES[JIM]) for x in row if x)
    assert nonzero == 8

    assert assemble("        ج\n")[0] >> 24 == 0xE4
    for token in ("0xE4", "270°", "8 dari 25"):
        assert token in readme, token


def test_the_limits_page_keeps_every_failed_reading() -> None:
    """
    Three readings failed and one claim was retracted. If any of them quietly
    started working, the page would be wrong -- so each is re-measured.
    """
    limits = _text("LIMITS.md")
    vectors = [list(_to_vec(e)) for e in ENTRIES]

    def total(i: int) -> int:
        return sum(sum((x - y) ** 2 for x, y in zip(vectors[i], w, strict=True))
                   for w in vectors)

    ranked = sorted(range(28), key=total)
    assert ranked.index(JIM) == 5, "Jim became more central"
    assert ranked[0] == KHA
    assert "peringkat 6 dari 28" in limits

    zeros = sum(1 for v in vectors for x in v if x == 0)
    assert zeros / (28 * 18) > 0.70
    assert "71%" in limits

    # And the retraction stays retracted -- measured, not phrased, because a
    # phrase can be deleted while the surrounding words still read right.
    def emit(idx: int) -> list[int]:
        m = [[x & 1 for x in row] for row in build_exomatrix(ENTRIES[idx])]
        state, out = [1, 0, 0, 0, 0], []
        for _ in range(31):
            out.append(state[0])
            state = [sum(m[i][j] * state[j] for j in range(5)) & 1
                     for i in range(5)]
        return [1 - 2 * b for b in out]

    j, k = emit(JIM), emit(KHA)
    cross = {sum(j[i] * k[(i + t) % 31] for i in range(31)) for t in range(31)}
    assert len(cross) == 6 and max(abs(c) for c in cross) == 11
    assert cross != {-1, -9, 7}, "it became a preferred pair"

    assert "bukan pasangan pilihan" in limits.lower()
    assert "{−1, −9, 7}" in limits
    assert "tidak bisa dibangun" in limits, "the retraction was softened"


def test_the_folder_states_what_it_does_not_claim() -> None:
    """The paragraph that makes the rest readable."""
    for name in ("README.md", "LIMITS.md"):
        text = _text(name)
        assert "Q₉₀" in text or "kuantisasi" in text
        assert "tidak diklaim" in text.lower() or "tidak diukur" in text.lower()

    # The layout really is load-bearing, which is what that caveat rests on.
    from hijaiyyah.core.exomatrix import build_exomatrix as build

    face = build(ENTRIES[JIM])
    swapped = [face[0], face[1], face[3], face[2], face[4]]

    class _Stub:
        vector = tuple(range(18))

    def order_of(rows: list[list[int]]) -> int:
        base = tuple(tuple(x & 1 for x in r) for r in rows)
        seen, x, k = {}, base, 1
        while k <= 400:
            if x in seen:
                return k - seen[x]
            seen[x] = k
            x = _mul(x, base, 2)
            k += 1
        return -1

    assert order_of(face) == 31
    assert order_of(swapped) != 31, "swapping two rows left the period alone"
