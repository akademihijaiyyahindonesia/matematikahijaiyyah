"""
Five folders, one per named recipe, and the numbers in them bound to the code.

    cosmictera/            the folding, the rotation, the seal
    cosmic-codex-jim/      one letter's machine, in two fields
    hijrah/                the letter as the unit of counting
    matematika-hijaiyyah/  the table read as a program
    teknologi/             what the mathematics actually produced

The last one answers a different question from the other four -- not how the
system works but what exists because of it -- so its figures are a census of
the tree rather than a property of the table, and are recounted as such.

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
    "cosmictera": ("README.md", "RULES.md", "SYSTEM.md", "CONCRETE.md", "COMPUTING.md", "CODEX.md"),
    "cosmic-codex-jim": ("README.md", "MACHINE.md", "WAVE.md", "LIMITS.md"),
    "hijrah": ("README.md", "UNIT.md", "INSTRUCTION.md", "JUMP.md"),
    "matematika-hijaiyyah": ("README.md", "GUARD.md", "ALGEBRA.md", "LINEAGE.md"),
    "teknologi": ("README.md", "ISTILAH.md", "BAHASA.md", "SILIKON.md", "KRIPTO.md", "INDUSTRI.md"),
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
        # Anywhere under tests/, not only test_integrity/. A folder anchored by
        # tests/test_core/test_hybit.py is anchored just as well, and the
        # narrower rule turned a correct citation into a failure.
        assert list((ROOT / "tests").rglob(name)), (
            f"{folder} cites {name}, which does not exist")


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


def test_teknologi_inventory_is_a_census_not_a_claim() -> None:
    """
    An inventory is the easiest document to let drift: adding a module breaks
    nothing when the table that counts modules is not updated, so the table
    quietly becomes false while every other test stays green. Each row is
    therefore recounted from the tree it describes, not compared against a
    constant retyped here -- the same reason the other folders parse their
    figures instead of searching for them.
    """
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from hijaiyyah.core.master_table import MASTER_TABLE

    readme = _text("teknologi", "README.md")

    def row(label: str) -> int:
        m = re.search(rf"^\| {re.escape(label)} \| ([\d.]+) \|", readme, re.M)
        assert m, f"teknologi/README has no counted row for {label!r}"
        return int(m.group(1).replace(".", ""))

    entries = MASTER_TABLE.all_entries()
    pkg = ROOT / "src" / "hijaiyyah"
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    scripts = re.search(r"\[project\.scripts\]\n((?:.+\n)+?)\n", pyproject)
    assert scripts, "pyproject no longer declares [project.scripts]"

    actual = {
        "Nilai tersegel":            len(entries) * len(entries[0].vector),
        "Opcode H-ISA":              len(re.findall(r"^`define OP_", (ROOT / "rtl" / "hcpu_pkg.vh")
                                                    .read_text(encoding="utf-8"), re.M)),
        "Paket Python":              len([d for d in pkg.iterdir()
                                          if d.is_dir() and d.name != "__pycache__"]),
        "Modul RTL HCPU":            len(list((ROOT / "rtl").glob("hcpu_*.v"))),
        "Modul RTL Ka'bah":          len(list((ROOT / "rtl").glob("hijaiyyah_*.v"))),
        "Testbench RTL":             len(list((ROOT / "rtl" / "tb").glob("tb_*.v"))),
        "Program HASM": (
            len(list((ROOT / "rtl" / "programs").glob("*.hasm")))
            + len(list((ROOT / "rtl" / "programs" / "bench").glob("*.hasm")))
        ),
        "Spesifikasi":               len(list((ROOT / "docs").glob("*.md"))),
        "Alat baris perintah":       len([ln for ln in scripts.group(1).splitlines() if "=" in ln]),
    }
    for label, count in actual.items():
        assert row(label) == count, (
            f"teknologi/README says {row(label)} {label}, tree holds {count}"
        )


def test_teknologi_industry_page_separates_capability_from_deployment() -> None:
    """Two failure modes, opposite directions, and the page must avoid both.

    The first draft of this page answered "who uses this" when the question
    was "what is this good for", and opened with "Nol" -- reading a list of
    absent customers as a verdict on the work. Capability and deployment are
    different claims: an O(1) guard in 25 operations is useful whether or not
    anyone has bought it yet.

    The other direction is the brochure, where unbuilt deployment is implied
    by listing sectors without ever saying nobody has installed this.

    So: every capability carries a measured label, and the deployment status
    is stated in its own section rather than inferred either way.
    """
    page = _text("teknologi", "INDUSTRI.md")

    body, status = page.split("## Status penerapan", 1)
    assert "**AT**" in status, (
        "the deployment section no longer labels field installation as unbuilt")
    assert "belum" in status, "the deployment section no longer says what is missing"

    numbered = re.findall(r"^## \d+\. (.+)$", body, re.M)
    assert len(numbered) >= 5, f"only {len(numbered)} capabilities listed"
    assert body.count("**CC**") >= 4, (
        "a capability lost its measured label -- every one has to name what "
        "was measured, or it is a sector list wearing a number")
    # Every capability says what the thing does before naming who wants it.
    assert body.count("**Kemampuannya.**") >= 5, (
        "a capability section stopped stating what the technology can do")
