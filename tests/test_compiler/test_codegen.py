"""
The language, compiled onto its own processor.

Stage 5 of HCC was `return ""`. `hc run` walked the AST in Python, the HCPU
executed hand-written .hasm, and the two never met — so nothing could hold
them to the same answer, which is the entire premise of the toolchain.

The gate that matters here is differential. For every program in the corpus,
the HC evaluator computes an answer in Python and the compiled instructions
compute one on the H-ISA machine. They must agree. Testing that the generator
emits particular mnemonics would only pin my choices; testing that both ends
produce the same number pins the thing the project is actually built on.

The generator refuses far more than it accepts, and that is deliberate: wrong
instructions on a processor have no second check behind them. The refusals are
pinned too, because a refusal that quietly becomes an approximation is the
failure mode worth guarding against.
"""

from __future__ import annotations

import itertools
from typing import Any, List

import pytest

from hijaiyyah.compiler.codegen import CodegenError, Emitted, generate
from hijaiyyah.compiler.psi import inject
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import HISAMachine
from hijaiyyah.language.evaluator import HCEvaluator
from hijaiyyah.language.lexer import Lexer
from hijaiyyah.language.parser import Parser

LETTERS = [e.char for e in MASTER_TABLE.all_entries()]


def parse(source: str) -> Any:
    return Parser(Lexer(source).tokenize()).parse()


def compile_hc(source: str) -> Emitted:
    ast = parse(source)
    return generate(ast, inject(ast))


def run_evaluator(source: str) -> List[Any]:
    printed: List[Any] = []
    HCEvaluator(print_func=lambda *a: printed.extend(a)).evaluate(parse(source))
    return printed


def run_machine(source: str) -> List[int]:
    """Compile, assemble, execute, and return whatever PRINT wrote."""
    emitted = compile_hc(source)
    words = assemble(emitted.text)

    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(words)
    machine.run()

    # Read what PRINT actually emitted. This used to re-read the register
    # named in each emitted PRINT line instead, because the interpreter had no
    # output sink at all -- its PRINT printed an H-Reg, which is PRINTH's job.
    # Re-deriving the answer from the source cannot catch a PRINT that emits
    # the wrong thing, since the source is what it was derived from.
    return list(machine.output)


# ══════════════════════════════════════════════════════════════════
#  The differential gate
# ══════════════════════════════════════════════════════════════════

_PAIRS = list(itertools.islice(itertools.combinations(LETTERS, 2), 30))

_PROGRAMS = (
    [f"let h = '{c}';\nprintln(h.norm2());\n" for c in LETTERS]
    + [
        f"let a = '{x}';\nlet b = '{y}';\nlet w = a + b;\nprintln(w.norm2());\n"
        for x, y in _PAIRS
    ]
    + [
        f"let a = '{x}';\nlet b = '{y}';\nprintln(a.dist2(b));\n"
        for x, y in _PAIRS
    ]
    + [
        "let a = 'ب';\nlet b = 'س';\nlet c = 'م';\n"
        "let w = a + b + c;\nprintln(w.norm2());\n",
        "let x = 6;\nlet y = 7;\nprintln(x * y);\n",
        "let x = 40;\nlet y = 2;\nprintln(x + y);\n",
        "let x = 50;\nlet y = 8;\nprintln(x - y);\n",
    ]
    # load_id is the one hybit source that is proven without a known value,
    # so the closure property below is vacuous without it in the corpus.
    + [f"let h = load_id({i});\nprintln(h.norm2());\n" for i in (1, 2, 14, 27, 28)]
    + [f"let h = load_id({i});\nprintln(h.theta());\n" for i in (1, 20, 27)]
)


def test_the_corpus_is_not_empty() -> None:
    assert len(_PROGRAMS) >= 90


@pytest.mark.parametrize("source", _PROGRAMS, ids=range(len(_PROGRAMS)))
def test_evaluator_and_machine_agree(source: str) -> None:
    """
    The same program, computed twice by unrelated machinery: a tree-walking
    interpreter in Python, and compiled instructions on the H-ISA machine.
    """
    expected = [int(v) for v in run_evaluator(source)]
    assert run_machine(source) == expected


# ══════════════════════════════════════════════════════════════════
#  Ψ feeds codegen
# ══════════════════════════════════════════════════════════════════

def test_a_proven_guard_emits_no_instruction() -> None:
    """
    The payoff of the Ψ work: closure makes the check unnecessary, so O(1)
    validation becomes no instruction at all.
    """
    emitted = compile_hc("let w = 'ب' + 'س';\nw.guard();\n")
    assert emitted.guards_elided == 1
    assert emitted.guards_emitted == 0
    assert "HGRD" not in assemble_text(emitted)


def test_load_id_is_proven_and_needs_no_guard() -> None:
    """load_id returns a sealed letter or raises, so the check is redundant."""
    emitted = compile_hc("let h = load_id(3);\nh.guard();\n")
    assert emitted.guards_elided == 1
    assert emitted.guards_emitted == 0


def test_without_a_psi_report_every_guard_is_emitted() -> None:
    """The elision is an optimisation, not a semantic change."""
    ast = parse("let w = 'ب' + 'س';\nw.guard();\n")
    emitted = generate(ast, None)
    assert emitted.guards_emitted == 1
    assert emitted.guards_elided == 0
    assert "HGRD" in assemble_text(emitted)


def assemble_text(emitted: Emitted) -> str:
    return "\n".join(
        line for line in emitted.lines if not line.strip().startswith(";")
    )


# ══════════════════════════════════════════════════════════════════
#  Everything the generator refuses
# ══════════════════════════════════════════════════════════════════

def test_component_reads_compile_to_cget() -> None:
    """
    These were uncompilable until CGET existed: H-ISA had no AND, no shift,
    no DIV and no projection, and HPACK could not be unpacked. The book's own
    example in §IIIF.3.1.2 uses PROJ THETA and hit the same wall.
    """
    for method, index in (("theta", 0), ("Na", 1), ("Qc", 13), ("AQ", 16)):
        words = assemble(compile_hc(f"let h = 'ب';\nprintln(h.{method}());\n").text)
        projection = next(w for w in words if w >> 24 == 0x44)
        assert projection & 0xFFF == index


def test_derived_quantities_compile_to_cu_and_crho() -> None:
    """
    Owner Decision 2: .U() lowers to hardware opcode CU (0x4D) and .rho()
    lowers to hardware opcode CRHO (0x4C), both reading from hcpu_guard.v.
    """
    words_u = assemble(compile_hc("let h = 'هـ';\nprintln(h.U());\n").text)
    assert any((w >> 24) == 0x4D for w in words_u), "expected CU (0x4D) for .U()"

    words_rho = assemble(compile_hc("let h = 'هـ';\nprintln(h.rho());\n").text)
    assert any((w >> 24) == 0x4C for w in words_rho), "expected CRHO (0x4C) for .rho()"


def test_gpr_bound_never_allocates_above_r15_and_reuses_temporaries() -> None:
    """
    Owner Decision 2: R16 and R17 cannot be encoded in the 4-bit register field
    (MAX_GPR = 15). Temporary scalar registers are reused across statements, and
    16 simultaneously live scalar `let` bindings fail cleanly at R1–R15.
    """
    many_prints = "let b = 'ب';\n" + "println(b.U());\nprintln(b.rho());\n" * 12
    words = assemble(compile_hc(many_prints).text)
    assert words[-1] >> 24 == 0x01

    sixteen_live_scalars = "".join(f"let r{i} = {i};\n" for i in range(1, 17))
    with pytest.raises(CodegenError, match="R1–R15"):
        compile_hc(sixteen_live_scalars)


def test_native_letter_opcodes_emitted_for_literal_letter_chains() -> None:
    """
    Owner Decision 2: A literal letter sum ('ب' + 'س' + 'م') with static Ψ
    safety proof and H0 free lowers to CZERO H0 + native letter opcodes
    (0xE1, 0xEB, 0xF7).
    """
    src = (
        "let bsm = 'ب' + 'س' + 'م';\n"
        "println(bsm.theta());\nprintln(bsm.U());\nprintln(bsm.rho());\n"
    )
    words = assemble(compile_hc(src).text)
    opcodes = [w >> 24 for w in words]
    assert 0x47 in opcodes  # CZERO
    assert [0xE1, 0xEB, 0xF7] == [op for op in opcodes if 0xE0 <= op <= 0xFB]
    assert run_machine(src) == [10, 6, 4]


def test_a_result_with_nowhere_to_go_is_still_refused() -> None:
    """A vector, a matrix or a float cannot land in a 32-bit GPR."""
    for method in ("array", "norm", "exomatrix"):
        with pytest.raises(CodegenError, match="32-bit integer"):
            compile_hc(f"let h = 'ب';\nprintln(h.{method}());\n")


def test_hybit_subtraction_is_refused() -> None:
    with pytest.raises(CodegenError, match="monoid"):
        compile_hc("let d = 'ب' - 'س';\n")


def test_mixing_a_hybit_and_a_scalar_is_refused() -> None:
    with pytest.raises(CodegenError, match="cannot combine"):
        compile_hc("let x = 'ب' + 3;\n")


def test_printing_a_hybit_is_refused() -> None:
    with pytest.raises(CodegenError, match="scalar register"):
        compile_hc("let h = 'ب';\nprintln(h);\n")


def test_an_unbound_name_is_refused() -> None:
    with pytest.raises(CodegenError, match="not bound"):
        compile_hc("println(nowhere);\n")


def test_running_out_of_hybit_registers_is_an_error_not_a_wrap() -> None:
    """H0–H15 is sixteen; a seventeenth must fail loudly."""
    source = "".join(f"let h{i} = 'ب';\n" for i in range(17))
    with pytest.raises(CodegenError, match="out of hybit registers"):
        compile_hc(source)


def test_an_unsupported_statement_is_refused() -> None:
    with pytest.raises(CodegenError, match="not compilable"):
        compile_hc("fn f() { return 1; }\n")


# ══════════════════════════════════════════════════════════════════
#  The emitted assembly is real assembly
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("source", _PROGRAMS[:40], ids=range(40))
def test_everything_emitted_assembles(source: str) -> None:
    """Output that the canonical assembler rejects is not assembly."""
    assert assemble(compile_hc(source).text)


def test_every_program_ends_in_halt() -> None:
    words = assemble(compile_hc("let h = 'ب';\nprintln(h.norm2());\n").text)
    assert words[-1] >> 24 == 0x01, "a program that runs off the end is a hang"


@pytest.mark.parametrize("char", LETTERS, ids=LETTERS)
def test_letters_load_by_their_one_based_index(char: str) -> None:
    """
    HLOAD IMM is 1-based, and this is where an off-by-one would put the wrong
    letter on the processor while the interpreter stayed right.
    """
    entry = MASTER_TABLE.get_by_char(char)
    assert entry is not None
    word = assemble(compile_hc(f"let h = '{char}';\n").text)[0]
    assert word >> 24 == 0x40
    assert word & 0xFFF == entry.index


def test_a_guard_with_no_facts_at_all_is_still_emitted() -> None:
    """
    The elision must be driven by a proof, never by the absence of one.

    Deleting the receiver's entry from the report models a hybit the analysis
    knows nothing about. Today every hybit source codegen accepts — a letter,
    a sum of letters, load_id — happens to be provable, so this path cannot be
    reached by writing a program: changing the check from "facts exist and
    prove it" to "no facts, or they prove it" passed all 172 other tests here.
    It is latent unsoundness that would bite the moment codegen gains an
    unprovable hybit source, so it is pinned directly.
    """
    source = "let w = 'ب' + 'س';\nw.guard();\n"
    ast = parse(source)
    report = inject(ast)

    guard_call = next(
        node
        for node in ast.body
        if isinstance(getattr(node, "expr", None), object)
        and type(node).__name__ == "ExpressedStmt"
    ).expr
    report.facts.pop(id(guard_call.obj), None)

    emitted = generate(ast, report)
    assert emitted.guards_emitted == 1, "an unproven guard must survive"
    assert emitted.guards_elided == 0
    assert "HGRD" in assemble_text(emitted)


# ══════════════════════════════════════════════════════════════════
#  Guard insertion — the other half of Ψ
# ══════════════════════════════════════════════════════════════════

def test_the_compilable_subset_is_closed_under_provability() -> None:
    """
    Every hybit a compilable program can produce is one Ψ can prove.

    That is not a coincidence, it is the shape of the subset: the only hybit
    sources codegen accepts are a sealed letter, load_id — which returns a
    sealed letter or raises — and sums of those, which closure covers
    (Proposisi IIIA.3.2.1). Register pressure keeps sums short enough that
    the 8-bit bound is never reached either: nine letters exhaust H0–H15
    before eight of them can push a component past 255.

    So insertion has nothing to insert today. The property is worth pinning
    rather than assuming: the moment codegen gains a source from outside the
    sealed world — a function parameter, a memory load, decoded input — this
    fails, and whoever adds it has to decide what guards it needs.
    """
    for source in _PROGRAMS:
        ast = parse(source)
        report = inject(ast)
        emitted = generate(ast, report, insert_guards=True)
        assert emitted.guards_inserted == 0, (
            f"an unprovable hybit is now reachable:\n{source}"
        )


def test_insertion_emits_a_guard_for_an_unproven_value() -> None:
    """
    The mechanism itself, exercised directly. Deleting the facts models a
    hybit the analysis knows nothing about — the case the property above says
    cannot yet be written, and the case insertion exists for.
    """
    source = "let h = 'ب';\n"
    ast = parse(source)
    report = inject(ast)
    report.facts.pop(id(ast.body[0].value), None)

    emitted = generate(ast, report, insert_guards=True)
    assert emitted.guards_inserted == 1
    assert "HGRD" in assemble_text(emitted)
    assert "disisipkan" in emitted.text, "the listing must say why"


def test_insertion_leaves_a_proven_value_alone() -> None:
    """Insertion adds a check where closure says nothing, never where it does."""
    ast = parse("let w = 'ب' + 'س';\n")
    emitted = generate(ast, inject(ast), insert_guards=True)
    assert emitted.guards_inserted == 0
    assert "HGRD" not in assemble_text(emitted)


def test_insertion_is_off_by_default() -> None:
    """It changes the instruction stream, so it is opt-in."""
    ast = parse("let h = 'ب';\n")
    report = inject(ast)
    report.facts.pop(id(ast.body[0].value), None)
    assert generate(ast, report).guards_inserted == 0
