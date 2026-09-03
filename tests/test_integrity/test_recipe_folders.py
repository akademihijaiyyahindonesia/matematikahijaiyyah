"""
Four folders, one per named recipe, and the numbers in them bound to the code.

    cosmictera/            the folding, the rotation, the seal
    cosmic-codex-jim/      one letter's machine, in two fields
    hijrah/                the letter as the unit of counting
    matematika-hijaiyyah/  the table read as a program

Prose drifts and code does not, so every figure a folder prints is checked
against what produces it. The failure mode this guards against is specific and
has happened four times in this repository: a number quoted in a document
after the thing it measured had changed.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FOLDERS = {
    "cosmictera": ("README.md", "RULES.md", "SYSTEM.md", "CONCRETE.md"),
    "cosmic-codex-jim": ("README.md", "MACHINE.md", "WAVE.md", "LIMITS.md"),
    "hijrah": ("README.md", "UNIT.md", "INSTRUCTION.md", "JUMP.md"),
    "matematika-hijaiyyah": ("README.md", "GUARD.md", "ALGEBRA.md", "LINEAGE.md"),
}


def _text(folder: str, name: str) -> str:
    return (ROOT / folder / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("folder", sorted(FOLDERS))
def test_each_folder_holds_and_indexes_exactly_its_documents(folder: str) -> None:
    found = {p.name for p in (ROOT / folder).glob("*.md")}
    assert found == set(FOLDERS[folder]), (folder, found)
    readme = _text(folder, "README.md")
    for name in FOLDERS[folder][1:]:
        assert f"({name})" in readme, f"{folder}/README does not link {name}"


@pytest.mark.parametrize("folder", sorted(FOLDERS))
def test_each_folder_names_the_tests_that_anchor_it(folder: str) -> None:
    """A folder that cites no test is a story."""
    readme = _text(folder, "README.md")
    cited = set(re.findall(r"(test_[a-z_]+\.py)", readme))
    assert cited, f"{folder}/README cites no test file"
    for name in cited:
        assert (ROOT / "tests" / "test_integrity" / name).is_file(), name


def test_hijrah_prints_the_density_that_was_measured() -> None:
    """
    The whole claim of the folder: a letter carries more than four bits as an
    operator where a bit carries one. Parsed from the table, not searched for
    in the file -- every one of those figures also appears in the prose.
    """
    table = _text("hijrah", "README.md")
    rows = {int(m.group(1)): [float(x.replace(",", ".")) for x in m.groups()[1:]]
            for m in re.finditer(
                r"^\s+(\d)\s+(\d,\d\d)\s+(\d,\d\d)\s+(\d,\d\d)\s+(\d,\d\d)$",
                table, re.M)}
    assert set(rows) == {1, 3, 5}
    for n, (two, four, five, bits) in rows.items():
        assert bits == 1.00, n
        # The field matters, in that order. At length 1 both GF(4) and GF(5)
        # sit on the ceiling, so the inequality is only strict beyond it.
        assert two < four <= five, n
        if n > 1:
            assert four < five, n
        # Bounded on BOTH sides. A one-sided check let a sabotage that
        # raised the figure to 9,99 pass -- above the ceiling is as wrong as
        # below it, and log2(28) is the ceiling.
        assert 4.5 < five <= 4.81, n
        assert two <= 4.81 and four <= 4.81, n
    assert rows[1][2] == 4.81                  # log2(28), the ceiling itself


def test_hijrah_records_the_four_letters_gf2_loses() -> None:
    from hijaiyyah.core.exomatrix import build_exomatrix
    from hijaiyyah.core.master_table import MASTER_TABLE

    groups: dict[tuple, list[str]] = {}
    for e in MASTER_TABLE.all_entries():
        face = tuple(tuple(x & 1 for x in r) for r in build_exomatrix(e))
        groups.setdefault(face, []).append(e.char)
    collided = {frozenset(g) for g in groups.values() if len(g) > 1}

    assert len(collided) == 4
    text = _text("hijrah", "README.md")
    for pair in collided:
        for char in pair:
            assert char in text, char


def test_matematika_hijaiyyah_prints_the_column_roles_it_measured() -> None:
    import collections
    import math

    from hijaiyyah.core.guards import _to_vec
    from hijaiyyah.core.master_table import MASTER_TABLE

    vectors = [list(_to_vec(e)) for e in MASTER_TABLE.all_entries()]
    slots = ["Θ̂", "Na", "Nb", "Nd", "Kp", "Kx", "Ks", "Ka", "Kc",
             "Qp", "Qx", "Qs", "Qa", "Qc", "AN", "AK", "AQ", "H*"]

    def fired(k: int) -> int:
        return sum(1 for v in vectors if v[k])

    def entropy(k: int) -> float:
        c = collections.Counter(v[k] for v in vectors)
        return -sum(n / 28 * math.log2(n / 28) for n in c.values())

    flags = {slots[k] for k in range(18) if fired(k) <= 2}
    disc = {slots[k] for k in range(18) if fired(k) > 2 and entropy(k) > 1.3}
    counters = {slots[k] for k in range(18) if fired(k) > 2 and entropy(k) <= 1.3}

    readme = _text("matematika-hijaiyyah", "README.md")
    row = next(ln for ln in readme.splitlines() if "PENANDA" in ln)
    assert f"| {len(flags)} |" in row, row
    for name, group in (("PEMBEDA", disc), ("PENCACAH", counters)):
        line = next(ln for ln in readme.splitlines() if name in ln and "|" in ln)
        assert f"| {len(group)} |" in line, line


def test_the_guard_page_keeps_the_ceiling_honest() -> None:
    """
    93.1% is the ceiling and the page says so. If either locked component ever
    became detectable, the page would be wrong -- so both are re-measured.
    """
    from hijaiyyah.core.guards import _to_vec, compute_U, guard_check
    from hijaiyyah.core.master_table import MASTER_TABLE

    vectors = [list(_to_vec(e)) for e in MASTER_TABLE.all_entries()]

    def detection(indices: list[int]) -> tuple[int, int]:
        tried = caught = 0
        for v in vectors:
            for i in indices:
                for d in (1, -1, 2, -2, 7):
                    w = list(v)
                    w[i] += d
                    if any(x < 0 for x in w):
                        continue
                    tried += 1
                    caught += not guard_check(w)
        return tried, caught

    assert detection([17]) == (85, 0)          # H*, unguarded
    assert detection([0]) == (133, 15)         # Theta-hat, one-sided

    # rho is additive, which is why no finite upper bound survives.
    rho = [v[0] - compute_U(v) for v in vectors]
    assert max(rho) > 0
    a, b = vectors[0], vectors[13]
    total = [x + y for x, y in zip(a, b, strict=True)]
    assert total[0] - compute_U(total) == rho[0] + rho[13]

    page = _text("matematika-hijaiyyah", "GUARD.md")
    assert "93,1%" in page and "88,1%" in page
    # The retraction, checked by its consequence rather than by a word: if G5
    # had been kept, H* would be detectable, and it is not.
    assert "dicabut" in page, "the G5 retraction was removed"
    assert "empiris dengan satu titik data" in page
    assert detection([17]) == (85, 0), "H* became detectable — G5 is back"
