"""The domain dictionary, and the boundary that keeps it from becoming a copy.

`istilah/` exists because a sweep of this repository found technology terms in
daily use with no definition anywhere — the five Bab II operations worst among
them. VTM, NMV, AGM, ITM and EXM name every module in src/hijaiyyah/algebra/,
are written across cosmictera-build/README.md as one line, and appeared in no
glossary at all. That is not marginal vocabulary; it is the whole of Bab II.

The hazard a second glossary creates is obvious and is exactly what R1
forbids: two pages defining one word, drifting apart. So the split is
mechanical rather than editorial, and these tests enforce it:

    teknologi/ISTILAH.md    system acronyms, used across layers
    istilah/                vocabulary inside one subsystem

A term in both is a defect, not a convenience.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DICT = ROOT / "istilah"
GLOSSARY = ROOT / "teknologi" / "ISTILAH.md"
PAGES = ("README.md", "MATEMATIKA.md", "SILIKON.md", "SISTEM.md",
         "KABAH.md", "CODEX-JIM.md")


def _rows(page: str) -> list[tuple[str, str]]:
    """Every (term, where) pair from the tables of one page.

    A row is `| **term** | ... `path` ... |` — the term in bold, and the file
    that implements it in backticks in ANY cell to its right, not necessarily
    the last. The five Bab II rows end with a chapter number and cite their
    module one column earlier; an earlier version of this test demanded the
    last column and would have forced those rows into a worse shape to satisfy
    it. The rule is "says where it is implemented", not "says it last".
    """
    out: list[tuple[str, str]] = []
    for line in (DICT / page).read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or not cells[0].startswith("**"):
            continue
        term = cells[0].strip("*").strip()
        where = " ".join(cells[1:])
        if term:
            out.append((term, where))
    return out


def test_the_folder_holds_and_indexes_exactly_its_pages() -> None:
    """Same rule the five recipe folders live under: no orphan, no ghost."""
    found = {p.name for p in DICT.glob("*.md")}
    assert found == set(PAGES), f"istilah/ holds {sorted(found)}"
    readme = (DICT / "README.md").read_text(encoding="utf-8")
    for name in PAGES[1:]:
        assert f"({name})" in readme, f"istilah/README does not link {name}"


@pytest.mark.parametrize("page", PAGES[1:])
def test_every_entry_names_where_it_is_implemented(page: str) -> None:
    """A term with no file behind it is not vocabulary, it is a wish.

    Something named but unbuilt belongs in cosmictera-build/OFF.md with a
    blocker, which is where this repository already puts that class of thing.
    """
    bare = [t for t, where in _rows(page) if "`" not in where and "—" not in where]
    assert not bare, (
        f"istilah/{page}: these entries name no file and no reason: {bare}. "
        "Either cite the module that implements the term, or move it to "
        "cosmictera-build/OFF.md as something that does not exist yet."
    )


@pytest.mark.parametrize("page", PAGES[1:])
def test_no_term_is_defined_in_both_glossaries(page: str) -> None:
    """R1, enforced across two files rather than trusted to memory.

    teknologi/ISTILAH.md owns the system acronyms. This folder owns subsystem
    vocabulary. A word in both has two definitions the moment one is edited,
    and nobody reading either page would know which is current.
    """
    gloss = GLOSSARY.read_text(encoding="utf-8")
    # ISTILAH.md marks its own entries in bold, the same way these pages do.
    owned = {m.strip().strip("\\") for m in re.findall(r"\|\s*\*\*([^*|]+)\*\*", gloss)}
    clash = [t for t, _ in _rows(page) if t.strip("\\") in owned]
    assert not clash, (
        f"istilah/{page} redefines {clash}, which teknologi/ISTILAH.md already "
        "owns. One term, one place (R1): either delete it here, or move the "
        "entry out of ISTILAH.md — not both."
    )


def test_the_five_bab_two_operations_are_all_present() -> None:
    """The gap that made this folder necessary, asserted so it cannot reopen.

    Each names a module under src/hijaiyyah/algebra/, and each of those files
    exists — checked here rather than assumed, because a dictionary whose
    pointers rot is worse than no dictionary.
    """
    text = (DICT / "MATEMATIKA.md").read_text(encoding="utf-8")
    for abbr, module in (("VTM", "vektronometry"), ("NMV", "normivektor"),
                         ("AGM", "aggregametric"), ("ITM", "intrametric"),
                         ("EXM", "exometric")):
        assert f"**{abbr}**" in text, f"{abbr} is missing from MATEMATIKA.md"
        path = ROOT / "src" / "hijaiyyah" / "algebra" / f"{module}.py"
        assert path.exists(), f"{abbr} points at {module}.py, which does not exist"
        assert module in text, f"{abbr} does not cite {module}.py"


def test_the_spelling_follows_the_code_not_the_prose() -> None:
    """Normivektor, with the i. The code has it twelve times; AGENTS.md once
    without. Code is the source and prose is what drifted, so the dictionary
    records the code's spelling and says so."""
    text = (DICT / "MATEMATIKA.md").read_text(encoding="utf-8")
    assert "Normivektor" in text
    assert not re.search(r"\bNormvektor\b(?!`)", text.replace("`Normvektor`", "")), (
        "MATEMATIKA.md uses the spelling the code does not"
    )


def test_the_dictionary_does_not_copy_figures_it_cannot_own() -> None:
    """Rule 3 of istilah/README, asserted.

    A glossary that transcribes measurements becomes a second place for them to
    drift -- the failure test_build_list.py was written for after three files
    quoted three different suite totals. Utilisation and Fmax belong to the
    wrapper headers that measured them; this folder may point, not copy.
    """
    for page in PAGES:
        text = (DICT / page).read_text(encoding="utf-8")
        assert not re.search(r"Fmax\s+\d", text), f"{page} transcribes an Fmax"
        assert not re.search(r"\d{2},\d{3}\s*/\s*20,736", text), (
            f"{page} transcribes a utilisation figure")
