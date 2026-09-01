"""
The Ψ-Injector, and the one thing it must never do.

Stage 4 of HCC was `return ast` — a named pipeline stage that did nothing, so
the property Bab III §IIIG.3.1.2 calls "data carries its own proof" had no
implementation behind it.

What makes the pass worth having is that closure is a theorem, not a hope: all
28 sealed letters satisfy G1–G4/T1–T2, and ℋ is closed under + (Proposisi
IIIA.3.2.1, holding because U is linear — Lemma IIIA.3.2.2). So an expression
built from letters and + is provably valid without running a guard.

That also makes the pass dangerous in exactly one direction. Claiming a guard
can be elided when the value would actually fail it turns a safety property
into a silent lie, and on the HCPU there is no second check behind it. So the
central test here is differential: whatever the analysis claims is provable,
the evaluator is made to actually compute, and the real guard must agree.
"""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any, Tuple

import pytest

from hijaiyyah.compiler.psi import (
    HREG_COMPONENT_MAX,
    SEALED_COMPONENT_MAX,
    HybitFacts,
    inject,
)
from hijaiyyah.core.exceptions import EBNFSemanticError
from hijaiyyah.core.guards import compute_rho, compute_U, guard_check
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.language.evaluator import HCEvaluator
from hijaiyyah.language.lexer import Lexer
from hijaiyyah.language.parser import Parser

ROOT = Path(__file__).resolve().parents[2]
LETTERS = [e.char for e in MASTER_TABLE.all_entries()]


def analyse(source: str):
    return inject(Parser(Lexer(source).tokenize()).parse())


def evaluate_bindings(source: str, *names: str) -> Tuple[Any, ...]:
    """Run an HC program and read raw values back out of its environment.

    Going through println would compare against stringified output; the
    bindings hold the real objects, which is what a differential check needs.
    """
    evaluator = HCEvaluator(print_func=lambda *a: None)
    evaluator.evaluate(Parser(Lexer(source).tokenize()).parse())
    return tuple(evaluator.current_env.get(name) for name in names)


def only_binding(source: str) -> HybitFacts:
    report = analyse(source)
    assert len(report.bindings) == 1, report.bindings
    return next(iter(report.bindings.values()))


# ══════════════════════════════════════════════════════════════════
#  Soundness — the property that matters
# ══════════════════════════════════════════════════════════════════

_SUMS = [
    " + ".join(f"'{c}'" for c in combo)
    for size in (1, 2, 3)
    for combo in itertools.islice(itertools.combinations_with_replacement(LETTERS, size), 40)
]


@pytest.mark.parametrize("expr", _SUMS, ids=range(len(_SUMS)))
def test_a_discharged_guard_would_really_have_passed(expr: str) -> None:
    """
    For every expression the pass is willing to elide a guard on, run the
    program and make the guard actually execute. If the analysis says the
    check is unnecessary, the check must be one that passes.

    This is the test that stands between a compile-time optimisation and a
    silently wrong one.
    """
    source = f"let w = {expr};\nprintln(w.guard());"
    report = analyse(source)
    assert report.guards_total == 1

    site = report.guard_sites[0]
    if not site.discharged:
        pytest.skip("not claimed provable — nothing to check")

    (actual,) = evaluate_bindings(
        f"let w = {expr};\nlet g = w.guard();", "g"
    )
    assert actual is True, f"{expr}: guard elided but would have failed"


@pytest.mark.parametrize("expr", _SUMS, ids=range(len(_SUMS)))
def test_the_folded_vector_is_the_vector_the_program_computes(expr: str) -> None:
    """Constant folding must agree with evaluation, component for component."""
    facts = only_binding(f"let w = {expr};")
    if facts.vector is None:
        pytest.skip("no folded value")

    (value,) = evaluate_bindings(f"let w = {expr};", "w")
    # A single letter evaluates to a CodexEntry; a sum evaluates to a list.
    computed = list(getattr(value, "vector", value))
    assert list(facts.vector) == computed, expr


@pytest.mark.parametrize("char", LETTERS, ids=LETTERS)
def test_every_sealed_letter_is_proven_on_sight(char: str) -> None:
    facts = only_binding(f"let h = '{char}';")
    assert facts.proven_valid
    assert facts.can_discharge_guard()
    entry = MASTER_TABLE.get_by_char(char)
    assert entry is not None
    assert facts.vector == tuple(entry.vector)
    assert facts.har_ref == f"HM-28:{entry.index:02d}"
    assert guard_check(list(entry.vector)), "the premise of the whole pass"


# ══════════════════════════════════════════════════════════════════
#  Pre-computed U and ρ — §IIIG.3.1.2 names both
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("char", LETTERS, ids=LETTERS)
def test_u_and_rho_are_precomputed_and_correct(char: str) -> None:
    facts = only_binding(f"let h = '{char}';")
    v = list(facts.vector or [])
    assert facts.budget_u == compute_U(v)
    assert facts.residue_rho == compute_rho(v)
    assert facts.theta == v[0]
    assert facts.residue_rho is not None and facts.residue_rho >= 0


def test_guard_flags_are_attached() -> None:
    flags = only_binding("let h = 'ب';").guard_flags
    assert flags is not None
    assert flags["all_pass"] is True
    assert set(flags) >= {"G1", "G2", "G3", "G4", "T1", "T2"}


# ══════════════════════════════════════════════════════════════════
#  Where the proof must stop
# ══════════════════════════════════════════════════════════════════

_DIFFERENCES = [
    f"'{a}' - '{b}'"
    for a, b in itertools.islice(itertools.permutations(LETTERS, 2), 40)
]


@pytest.mark.parametrize("expr", _DIFFERENCES, ids=range(len(_DIFFERENCES)))
def test_no_difference_is_ever_claimed_provable(expr: str) -> None:
    """
    The soundness sweep, extended to the operator that can actually leave ℋ.

    Checking this only through the one hand-written subtraction case was a
    hole: making `-` claim closure passed every differential test and failed
    only the dedicated one. A corpus that never builds the dangerous shape
    cannot catch an analysis that mishandles it.

    A difference is a 14D vector in Domain C, so .guard() now refuses it
    outright — which is itself the evidence that it is not a hybit.
    """
    report = analyse(f"let d = {expr};\nprintln(d.guard());")
    assert report.guards_discharged == 0, f"{expr}: claimed provable"

    with pytest.raises(EBNFSemanticError, match="18-component"):
        evaluate_bindings(f"let d = {expr};\nlet g = d.guard();", "g")


def test_subtraction_is_never_a_proof() -> None:
    """
    ℋ is a commutative monoid, not a group (Proposisi IIIA.3.2.2). A
    difference can leave the non-negative cone, so it can leave ℋ.
    """
    report = analyse("let d = 'ب' - 'س';\nprintln(d.guard());")
    assert report.guards_discharged == 0
    assert "monoid, not a group" in report.guard_sites[0].facts.reason


def test_a_value_from_outside_is_not_proven() -> None:
    report = analyse("fn f(x) { return x.guard(); }")
    assert report.guards_discharged == 0


def test_a_reassigned_binding_gives_up_its_proof() -> None:
    """
    The pre-pass is a coarse over-approximation on purpose: a name that is
    ever reassigned is unknown everywhere. Coarse in the safe direction — it
    can only lose a proof, never invent one.
    """
    report = analyse("let mut h = 'ب';\nh = 'س';\nprintln(h.guard());")
    assert report.guards_discharged == 0


def test_a_guard_before_the_reassignment_also_gives_up_its_proof() -> None:
    """
    The case the pre-pass actually exists for, and the one this file first
    missed: the guard is read *before* the assignment in source order, so a
    linear walk sees a sealed letter and discharges. On the second iteration
    the binding holds whatever mystery() returned.

    Deleting the pre-pass left every other test in this file green. A check
    that only exercises the easy order proves nothing about the hard one.
    """
    report = analyse(
        "let mut h = 'ب';\n"
        "for i in 1..=3 {\n"
        "    println(h.guard());\n"
        "    h = mystery();\n"
        "}\n"
    )
    assert report.guards_total == 1
    assert report.guards_discharged == 0
    assert "reassigned" in report.guard_sites[0].facts.reason


def test_an_unknown_call_is_not_proven() -> None:
    report = analyse("let h = mystery();\nprintln(h.guard());")
    assert report.guards_discharged == 0


# ══════════════════════════════════════════════════════════════════
#  The 8-bit boundary — §IIIJ.3.3.2 and §IIIK.3.3
# ══════════════════════════════════════════════════════════════════

def test_a_sum_that_overflows_the_hreg_field_is_not_discharged() -> None:
    """
    H-Reg components are 8-bit unsigned. A sum that is perfectly valid in
    Python can wrap on silicon, and a guard elided on that basis would be
    unsound. Θ̂(هـ) = 8, so 32 of them reach 256 — one past the field.
    """
    report = analyse("let w = " + " + ".join(["'هـ'"] * 32) + ";\nprintln(w.guard());")
    site = report.guard_sites[0]
    assert site.facts.proven_valid, "closure still holds mathematically"
    assert not site.facts.hardware_safe
    assert not site.discharged
    assert "8-bit H-Reg" in site.facts.reason


def test_the_widest_sum_that_still_fits_is_discharged() -> None:
    """31 × Θ̂(هـ) = 248 ≤ 255. The book puts the limit at roughly 30."""
    report = analyse("let w = " + " + ".join(["'هـ'"] * 31) + ";\nprintln(w.guard());")
    assert report.guards_discharged == 1
    assert report.guard_sites[0].facts.max_component == 248


def test_an_unknown_bound_blocks_the_hardware_claim() -> None:
    """
    load_id gives validity without a value. Adding a letter to it keeps
    closure, and the bound stays computable — but stack enough of them and
    the bound alone is what stops the elision.
    """
    facts = only_binding("let w = load_id(1) + 'ب';")
    assert facts.proven_valid
    assert facts.vector is None, "no folded value is available"
    assert facts.max_component == SEALED_COMPONENT_MAX + 2


def test_facts_with_no_bound_are_not_hardware_safe() -> None:
    assert not HybitFacts(proven_valid=True, max_component=None).hardware_safe
    assert not HybitFacts(proven_valid=True, max_component=None).can_discharge_guard()


def test_the_sealed_bound_is_derived_not_written_down() -> None:
    assert SEALED_COMPONENT_MAX == max(
        max(e.vector) for e in MASTER_TABLE.all_entries()
    )
    assert SEALED_COMPONENT_MAX <= HREG_COMPONENT_MAX


# ══════════════════════════════════════════════════════════════════
#  Builtins with a proven contract
# ══════════════════════════════════════════════════════════════════

def test_load_id_returns_a_sealed_letter_or_raises() -> None:
    report = analyse("let h = load_id(7);\nprintln(h.guard());")
    assert report.guards_discharged == 1
    facts = report.guard_sites[0].facts
    assert facts.vector is None, "the index is not tracked, only the contract"
    assert facts.max_component == SEALED_COMPONENT_MAX


@pytest.mark.parametrize("index", range(1, 29))
def test_the_load_id_contract_actually_holds(index: int) -> None:
    """The premise behind discharging load_id, checked against every index."""
    (actual,) = evaluate_bindings(
        f"let g = load_id({index}).guard();", "g"
    )
    assert actual is True


def test_zero_is_the_monoid_identity_and_is_in_the_set() -> None:
    facts = only_binding("let z = zero();")
    assert facts.proven_valid
    assert facts.vector == tuple([0] * 18)
    assert guard_check([0] * 18), "the identity must be in ℋ for ℋ to be a monoid"


# ══════════════════════════════════════════════════════════════════
#  The pass changes nothing it runs over
# ══════════════════════════════════════════════════════════════════

EXAMPLES = sorted(ROOT.joinpath("examples").glob("*.hc"))


@pytest.mark.parametrize("path", EXAMPLES, ids=[p.name for p in EXAMPLES])
def test_every_example_analyses(path: Path) -> None:
    report = analyse(path.read_text(encoding="utf-8"))
    assert report.guards_discharged == report.guards_total, (
        f"{path.name}: {report.summary()}"
    )


def test_the_compiler_attaches_the_report_only_under_psi_mode() -> None:
    from hijaiyyah.compiler import CompileOptions, HCCompiler

    source = "let w = 'ب' + 'س';\nprintln(w.guard());"
    with_psi = HCCompiler(CompileOptions(psi_mode=True)).compile_source(source)
    assert with_psi.psi_report is not None
    assert with_psi.psi_report.guards_discharged == 1

    without = HCCompiler(CompileOptions()).compile_source(source)
    assert without.psi_report is None
