"""The four theorem modules, which the suite reached 0% of.

`theorems/` states as theorems what `algebra/` and `core/` compute. The
modules were never broken -- they were never called. Coverage read
pythagorean.py and energy_norm.py at 0%, and the Pythagorean identity on the
codex is a Chapter II invention named in the patent certificate: a claim with
an implementation and no test underneath it.

Asserting `verify_all() is True` would close the coverage gap and prove
almost nothing, because it stays true if the implementation collapses into
something trivially true. So each theorem is checked three ways: that it
holds on the sealed table, that the structure it rests on is what it claims,
and that it fails when that STRUCTURE is broken rather than when the values
move. Writing these turned up why the distinction matters: perturbing a
component does not falsify the Pythagorean identity, because the identity is
structural and holds for any vector at all. Dropping an index from a block
does falsify it. The first test written here had the wrong falsification and
a name that claimed the opposite of its own assertion.
"""
from __future__ import annotations

import pytest

from hijaiyyah.algebra.vektronometry import norm2, pythagorean_check
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.theorems import decomposition, energy_norm, mod4_gate, pythagorean

ENTRIES = MASTER_TABLE.all_entries()

#: The four orthogonal blocks the identity decomposes v14 into.
BLOCKS = {"theta": [0], "N": [1, 2, 3], "K": [4, 5, 6, 7, 8], "Q": [9, 10, 11, 12, 13]}


# ── Theorem 20.2.1 — the Pythagorean identity on the codex ───────

def test_the_four_blocks_are_exactly_the_fourteen_dimensions() -> None:
    """1 + 3 + 5 + 5, disjoint, and stopping at 14 rather than 18.

    This is why the norm is written ||.||^2_14: components 14..17 are the
    aggregates A_N, A_K, A_Q and the free tag H*, which are sums of the
    blocks and a slot no guard constrains -- counting them would count the
    same information twice and add one unconstrained number.
    """
    indices = [i for block in BLOCKS.values() for i in block]
    assert sorted(indices) == list(range(14))
    assert len(indices) == len(set(indices)), "the blocks overlap"
    assert sum(len(b) for b in BLOCKS.values()) == 14


@pytest.mark.parametrize("entry", ENTRIES, ids=[e.char for e in ENTRIES])
def test_the_identity_holds_for_every_sealed_letter(entry) -> None:
    result = pythagorean_check(entry)
    assert result["pass"], (entry.char, result)
    assert result["lhs"] == result["rhs"]
    assert result["rhs"] == result["theta"] + result["N"] + result["K"] + result["Q"]


def test_the_identity_is_the_squared_norm_and_not_a_restatement() -> None:
    """Both sides computed independently, then compared.

    pythagorean_check builds the right side from the blocks; norm2 is the
    left side. If the two ever came from one expression the test would be
    comparing a value with itself.
    """
    for entry in ENTRIES:
        blocks = sum(sum(list(entry.vector)[k] ** 2 for k in idx) for idx in BLOCKS.values())
        assert blocks == norm2(entry), entry.char


def test_the_identity_is_structural_not_a_property_of_the_table() -> None:
    """Named for what it establishes, after the first name said the opposite.

    It was written as "breaks when a block moves", expecting perturbation to
    falsify the identity. Perturbation does not: both sides move together,
    for any vector, sealed or not. That is the stronger result and the reason
    it is a theorem rather than an observation about 28 rows -- so the name
    says so. The falsification lives in the test below, which breaks the
    block STRUCTURE instead of the values.
    """
    survivors = []
    for entry in ENTRIES:
        for k in range(14):
            broken = list(entry.vector)
            broken[k] += 1
            r = pythagorean_check(broken)
            # Both sides move, but the left side is the norm of the whole
            # vector -- so they move together only if the identity is real.
            if not r["pass"]:
                continue
            survivors.append((entry.char, k))
    # Perturbing inside the 14 keeps the identity true, because the identity
    # is structural: it holds for ANY vector, not only sealed ones. That is
    # what makes it a theorem rather than a property of the table -- and the
    # test says so instead of pretending to falsify something unfalsifiable.
    assert len(survivors) == len(ENTRIES) * 14, (
        "the identity stopped being structural; it now depends on which "
        "vector it is applied to, which contradicts Theorem 20.2.1")


def test_a_vector_outside_the_block_structure_breaks_it() -> None:
    """What DOES falsify it: a right side built from the wrong blocks."""
    v = list(ENTRIES[1].vector)
    wrong = sum(sum(v[k] ** 2 for k in idx)
                for idx in ([0], [1, 2], [4, 5, 6, 7, 8], [9, 10, 11, 12, 13]))
    assert wrong != norm2(v), (
        "dropping index 3 from block N left the sum unchanged, so the blocks "
        "are not carrying the information the identity says they carry")


def test_the_module_level_verifier_agrees() -> None:
    assert pythagorean.verify_all() is True


# ── Theorem 34.3.1 — the energy-norm inequality ──────────────────

def test_phi_strictly_exceeds_the_squared_norm() -> None:
    """Strict, not >=. An equality anywhere would make Phi no stronger."""
    from hijaiyyah.algebra.exometric import build, phi

    for entry in ENTRIES:
        assert phi(build(entry)) > norm2(entry), entry.char


def test_the_energy_verifier_agrees() -> None:
    assert energy_norm.verify_all() is True


# ── Proposition 11.3.1 — theta = U + rho ─────────────────────────

@pytest.mark.parametrize("entry", ENTRIES, ids=[e.char for e in ENTRIES])
def test_the_quadrant_identity_is_exact_for_every_letter(entry) -> None:
    d = decomposition.QuadrantDecomposer().decompose(entry)
    assert d["identity_holds"], (entry.char, d)
    assert d["theta"] == d["U"] + d["rho"]
    assert d["valid"], "rho < 0 means G4 fails, and no sealed letter may"


def test_rho_is_what_g4_tests() -> None:
    """The decomposition and the guard must not drift apart.

    G4 is rho >= 0. If decompose() ever computed a different rho than the
    guard does, a vector could pass one and fail the other -- and the
    certificate's rho row would describe neither.
    """
    from hijaiyyah.core.guards import compute_rho

    dec = decomposition.QuadrantDecomposer()
    for entry in ENTRIES:
        assert dec.decompose(entry)["rho"] == compute_rho(list(entry.vector))


# ── Theorem 11.4.1 — the mod-4 gate ──────────────────────────────

def test_the_gate_is_one_sided_and_says_so() -> None:
    """`possibly_closed` and `definitely_open` are not opposites by accident.

    theta % 4 == 0 is necessary for closure, not sufficient -- so the naming
    carries the asymmetry, and this checks the code keeps it: every letter is
    exactly one of the two, and the closed side never claims certainty.
    """
    rows = mod4_gate.Mod4Gate().check_all()
    assert len(rows) == len(ENTRIES)
    for row in rows:
        assert row["possibly_closed"] != row["definitely_open"]
        assert row["possibly_closed"] == (row["mod4"] == 0)
        assert row["theta"] % 4 == row["mod4"]


def test_the_gate_actually_separates_the_table() -> None:
    """A gate that lets everything through, or nothing, is not a gate."""
    rows = mod4_gate.Mod4Gate().check_all()
    closed = [r for r in rows if r["possibly_closed"]]
    assert 0 < len(closed) < len(rows), (
        f"{len(closed)} of {len(rows)} pass the gate; it is not discriminating")
    assert len(closed) == 7, f"the sealed table gives 7, this run gives {len(closed)}"
