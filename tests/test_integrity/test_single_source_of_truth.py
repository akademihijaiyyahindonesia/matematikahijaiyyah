"""
One definition per invariant, in Python.

The recurring failure in this project has never been wrong mathematics — it is
a truth kept in more than one place. The turning budget

    U = Qx + Qs + Qa + 4·Qc

had 31 hand-written copies across 16 files. Every divergence found so far grew
from that shape: the Master Table drifting across six representations, H-ISA
living in three encodings, the clock frequency written twice, the letter index
existing in two conventions.

Python has one definition now, core.guards.compute_U, and everything else calls
it. The JavaScript engine and the RTL keep their own — a browser cannot import
Python and neither can a processor — and those are held by
test_js_engine_parity.py and test_dataset_consistency.py instead.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

import pytest

from hijaiyyah.core.guards import compute_U
from hijaiyyah.core.master_table import MASTER_TABLE

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "src" / "hijaiyyah" / "core" / "guards.py"

PYTHON_ROOTS = [ROOT / "src", ROOT / "tools"]

# Qx + Qs + Qa + 4*Qc, written against any variable name.
_U_FORMULA = re.compile(
    r"\[10\]\s*\+\s*\w*\[11\]\s*\+\s*\w*\[12\]\s*\+\s*4\s*\*\s*\w*\[13\]"
)


def _copies() -> List[Tuple[str, int, str]]:
    found: List[Tuple[str, int, str]] = []
    for root in PYTHON_ROOTS:
        for path in sorted(root.rglob("*.py")):
            for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if _U_FORMULA.search(line):
                    found.append((str(path.relative_to(ROOT)), number, line.strip()))
    return found


COPIES = _copies()


def test_the_scan_finds_the_canonical_definition() -> None:
    """A regex that matched nothing would make the check below vacuous."""
    files = {path for path, _, _ in COPIES}
    assert str(CANONICAL.relative_to(ROOT)) in files, (
        "the scan does not even see compute_U — the pattern must have drifted"
    )


def test_the_formula_is_written_once() -> None:
    extra = [c for c in COPIES if c[0] != str(CANONICAL.relative_to(ROOT))]
    assert not extra, (
        "U is spelled out somewhere other than core.guards.compute_U:\n"
        + "\n".join(f"  {path}:{line}: {text}" for path, line, text in extra)
        + "\n\nCall compute_U instead. Every divergence this project has had "
        "grew from a formula kept in two places."
    )


def test_the_canonical_definition_is_a_single_line() -> None:
    """compute_U itself, and nothing else in that file, may spell it out."""
    inside = [c for c in COPIES if c[0] == str(CANONICAL.relative_to(ROOT))]
    assert len(inside) == 1, (
        f"core/guards.py spells U out {len(inside)} times; only compute_U should"
    )


# ── The definition still has to be right ─────────────────────────

@pytest.mark.parametrize(
    "entry", MASTER_TABLE.all_entries(), ids=[e.char for e in MASTER_TABLE.all_entries()]
)
def test_compute_U_matches_the_definition(entry) -> None:
    """Definition 11.1.1, checked against the letter it describes."""
    v = list(entry.vector)
    assert compute_U(v) == v[10] + v[11] + v[12] + 4 * v[13]


def test_compute_U_is_linear() -> None:
    """
    U(a + b) = U(a) + U(b). This is what makes the codex a monoid and what
    lets a string integral stay auditable; a copy that drifted could break it
    silently.
    """
    entries = MASTER_TABLE.all_entries()
    for a in entries[:6]:
        for b in entries[:6]:
            total = [x + y for x, y in zip(a.vector, b.vector, strict=True)]
            assert compute_U(total) == compute_U(list(a.vector)) + compute_U(
                list(b.vector)
            )


# ── The guard system, likewise defined once ──────────────────────

def test_the_language_guard_is_the_canonical_guard() -> None:
    """
    HC's `.guard()` used to be its own implementation, and it disagreed.

    It checked four constraints where ℋ has six, and numbered them wrongly:
    ρ ≥ 0 was called "G1" and the Nuqṭah sum-check "G2", where Bab III
    §IIIA.3.1.2 has G1–G3 as the sum-checks and G4 as turning conservation.
    T1 and T2 were absent.

    hcpu_guard.v computes all six, so the gap was a real HC↔HCPU divergence:
    a vector with Ks > 0 and Qc = 0 passed .guard() in the language and would
    have failed HGRD on the processor.
    """
    from hijaiyyah.core.guards import full_guard_check
    from hijaiyyah.language.evaluator import _guard_check

    # T1: Ks > 0 ⟹ Qc ≥ 1. Sum-checks all satisfied, so only T1 can fail.
    t1_violation = [4, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0]
    assert full_guard_check(t1_violation)["all_pass"] is False
    assert _guard_check(t1_violation) is False, "the language must see T1 too"

    # T2: Kc > 0 ⟹ Qc ≥ 1.
    t2_violation = [4, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0]
    assert full_guard_check(t2_violation)["all_pass"] is False
    assert _guard_check(t2_violation) is False, "the language must see T2 too"


@pytest.mark.parametrize(
    "entry", MASTER_TABLE.all_entries(), ids=[e.char for e in MASTER_TABLE.all_entries()]
)
def test_language_and_core_guards_agree_on_every_letter(entry) -> None:
    from hijaiyyah.core.guards import full_guard_check
    from hijaiyyah.language.evaluator import _guard_check

    v = list(entry.vector)
    assert _guard_check(v) == full_guard_check(v)["all_pass"] is True


def test_a_difference_vector_is_refused_rather_than_crashing() -> None:
    """
    `a - b` is a 14D vector in Domain C, not a hybit — ℋ is a monoid with no
    additive inverse. Asking it for a guard used to raise IndexError from
    inside the guard code; it now says what is wrong.
    """
    from hijaiyyah.core.exceptions import EBNFSemanticError
    from hijaiyyah.language.evaluator import _guard_check

    with pytest.raises(EBNFSemanticError, match="18-component"):
        _guard_check([0] * 14)
