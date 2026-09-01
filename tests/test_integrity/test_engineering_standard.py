"""
The engineering standard, checked against the repository it describes.

ENGINEERING_STANDARD.md §3 is the official directory layout. Version 1.0 of it
listed thirty files that never existed and omitted ten packages that do —
including compiler/, assembler/, vm/, pipeline/ and hisab/, which is most of
the compilation path. It placed the compiler at hisa/compiler.py, named the
five algebra modules after things they were never called, and pointed at a
repository under a different name.

None of that was caught, because a document nobody executes drifts silently.
That is the same shape as every other divergence in this project: a truth
written in two places, with only one of them under test.

So the standard is now executable. Not every line — prose stays prose — but
the parts that make a factual claim about the repository:

  * every file the §3 tree names must exist;
  * every package under src/hijaiyyah/ must appear in the tree;
  * the entry points §6.2 tabulates must match [project.scripts];
  * the version numbers §5 quotes must match version.py.

A new package with no entry in §3 fails this file. That is the point: the
standard cannot fall behind the repository without someone being told.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Dict, List, Set

import pytest

ROOT = Path(__file__).resolve().parents[2]
STANDARD = ROOT / "ENGINEERING_STANDARD.md"
SRC = ROOT / "src" / "hijaiyyah"

TEXT = STANDARD.read_text(encoding="utf-8")

# Entries that name a shape rather than one file.
GLOBS = {"hcpu_*.v"}


def _tree_block() -> str:
    after = TEXT.split("## 3. STRUKTUR DIREKTORI RESMI", 1)[1]
    return after.split("### Aturan Penempatan", 1)[0]


def _tree_paths() -> List[str]:
    """Reconstruct every path the §3 ASCII tree names."""
    paths: List[str] = []
    stack: List[str] = []
    for line in _tree_block().splitlines():
        marks = [line.find(c) for c in "├└" if line.find(c) != -1]
        if not marks:
            continue
        column = min(marks)
        # Four columns of prefix per level of nesting.
        depth = column // 4
        name = line[column + 4:].strip()
        # Strip the "← what it is" annotations.
        name = re.split(r"\s+←", name)[0].strip()
        if not name:
            continue
        is_dir = name.endswith("/")
        stack = [*stack[:depth], name.rstrip("/")]
        if not is_dir:
            paths.append("/".join(stack))
    return paths


TREE = _tree_paths()


def test_the_tree_was_parsed() -> None:
    """A parser that silently matched nothing would make everything below pass."""
    assert len(TREE) > 80, f"only {len(TREE)} entries parsed — the tree format changed"
    assert "src/hijaiyyah/core/master_table.py" in TREE


@pytest.mark.parametrize("entry", sorted(set(TREE)), ids=lambda p: p)
def test_every_listed_path_exists(entry: str) -> None:
    name = Path(entry).name
    if name in GLOBS:
        parent = ROOT / Path(entry).parent
        assert list(parent.glob(name)), f"§3 lists {entry}, nothing matches"
        return
    assert (ROOT / entry).exists(), (
        f"§3 lists {entry}, which does not exist.\n"
        "Either the file was removed and the standard was not updated, or the "
        "standard describes something that was never built."
    )


def _packages() -> Set[str]:
    """Every package directory under src/hijaiyyah."""
    return {
        p.parent.relative_to(SRC).as_posix()
        for p in SRC.rglob("__init__.py")
        if "__pycache__" not in p.parts and p.parent != SRC
    }


@pytest.mark.parametrize("package", sorted(_packages()), ids=lambda p: p)
def test_every_package_appears_in_the_standard(package: str) -> None:
    """
    The failure that prompted this file. compiler/, assembler/, vm/, pipeline/,
    har/ and hisab/ all shipped without ever reaching §3.
    """
    prefix = f"src/hijaiyyah/{package}/"
    assert any(entry.startswith(prefix) for entry in TREE), (
        f"package src/hijaiyyah/{package} is not listed in §3.\n"
        "Add it to the tree — a package the standard does not know about is a "
        "package nobody reviewing the layout will see."
    )


@pytest.mark.parametrize("module", sorted(SRC.glob("*.py")), ids=lambda p: p.name)
def test_every_top_level_module_appears(module: Path) -> None:
    entry = f"src/hijaiyyah/{module.name}"
    assert entry in TREE, f"§3 does not list {entry}"


# ── §6.2 entry points ────────────────────────────────────────────

def _declared_scripts() -> Dict[str, str]:
    with open(ROOT / "pyproject.toml", "rb") as handle:
        return tomllib.load(handle)["project"].get("scripts", {})


def test_the_entry_point_table_matches_pyproject() -> None:
    """
    §6 used to document one entry point. There are three, and two of them —
    `hc` and `hybit-ai` — are how the language and the AI runtime are actually
    invoked.
    """
    section = TEXT.split("### 6.2", 1)[1].split("### 6.3", 1)[0]
    for command, target in _declared_scripts().items():
        assert f"`{command}`" in section, f"§6.2 does not document `{command}`"
        assert target in section, f"§6.2 does not name the target for `{command}`"


def test_the_type_checker_named_is_the_one_ci_runs() -> None:
    """§6.5 said pyright; the CI gate is mypy. A standard that names the wrong
    tool sends a contributor to a check that is not the one blocking merges."""
    workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    assert "mypy src/hijaiyyah" in workflow
    section = TEXT.split("### 6.5", 1)[1]
    assert "mypy src/hijaiyyah" in section


# ── §5 version block ─────────────────────────────────────────────

def test_the_quoted_version_matches_version_py() -> None:
    source = (SRC / "version.py").read_text(encoding="utf-8")
    for field in ("__version__", "__dataset_release__", "__release__"):
        match = re.search(rf'{field}\s*=\s*"([^"]+)"', source)
        assert match, f"version.py no longer defines {field}"
        quoted = f'{field} = "{match.group(1)}"'
        assert quoted in TEXT, f"§5 does not quote the current {field}"


def test_the_standard_states_its_own_status() -> None:
    """
    The header carries a date and the tree carries a status note saying it
    describes what is, not what is planned. Both were the missing context that
    let version 1.0 read as authoritative long after it stopped being true.
    """
    assert "Versi 1.1" in TEXT
    assert "bukan rencana" in _tree_block()
