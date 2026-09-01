"""
HISAB, reachable from the language it belongs to — and a whole frame at last.

Two gaps, both of them a component that existed everywhere except where it
was needed.

HPACK and HCRC are in the ISA and in hcpu_hisab.v, and HC had no way to
produce either: two of the twenty-nine opcodes were unreachable from the
language. §IIIC calls HISAB the auditable bridge between systems, and the
bridge could only be crossed by hand-written assembly.

And HPACK itself was a third built. §IIIM.3.1 gives it as
``GPR[DST] ← nibble_pack(H[S1])[S2]``, words 0–2. Only word 0 was ever
selected — pack_word1 and pack_word2 were wired to the top level and never
read, in the RTL and in the Python machine alike. The processor could emit the
first four bytes of a nine-byte frame and no more, so no HISAB frame could be
assembled from the machine at all.

The golden values here are the ones rtl/tb/gen_golden.py feeds the RTL
testbench, so all three implementations are held to one set of numbers.
"""

from __future__ import annotations

import re
from typing import Any, List

import pytest

from hijaiyyah.compiler.codegen import CodegenError, generate
from hijaiyyah.compiler.psi import inject
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import HISAMachine
from hijaiyyah.hisab.serialize import (
    _compute_guard_status,
    _nibble_pack,
    serialize_letter,
)
from hijaiyyah.language.evaluator import HCEvaluator
from hijaiyyah.language.lexer import Lexer
from hijaiyyah.language.parser import Parser

LETTERS = [e.char for e in MASTER_TABLE.all_entries()]

# The RTL testbench's golden values for Ba, from rtl/tb/gen_golden.py.
BA_WORDS = (0x00010120, 0x11000001, 0x00003F10)
BA_CRC = 0x9A3115CC


def expected_words(char: str) -> List[int]:
    entry = MASTER_TABLE.get_by_char(char)
    assert entry is not None
    v = list(entry.vector)
    packed = _nibble_pack(v)
    return [
        int.from_bytes(packed[0:4], "little"),
        int.from_bytes(packed[4:8], "little"),
        (_compute_guard_status(v) << 8) | packed[8],
    ]


def run_hc(source: str) -> List[Any]:
    printed: List[Any] = []
    HCEvaluator(print_func=lambda *a: printed.extend(a)).evaluate(
        Parser(Lexer(source).tokenize()).parse()
    )
    return printed


def run_compiled(source: str) -> int:
    ast = Parser(Lexer(source).tokenize()).parse()
    asm = generate(ast, inject(ast)).text
    register = int(re.search(r"PRINT\s+R(\d+)", asm).group(1))
    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(assemble(asm))
    machine.run()
    return machine.dump_state()["gpr"][register]


# ══════════════════════════════════════════════════════════════════
#  All three words, on all three implementations
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("word", [0, 1, 2])
def test_ba_matches_the_rtl_golden_values(word: int) -> None:
    """The values rtl/tb/gen_golden.py hands the testbench."""
    source = f"let h = 'ب';\nprintln(h.pack({word}));\n"
    assert int(run_hc(source)[0]) == BA_WORDS[word]
    assert run_compiled(source) == BA_WORDS[word]


def test_ba_crc_matches_the_rtl_golden_value() -> None:
    source = "let h = 'ب';\nprintln(h.crc());\n"
    assert int(run_hc(source)[0]) == BA_CRC
    assert run_compiled(source) == BA_CRC


@pytest.mark.parametrize("char", LETTERS, ids=LETTERS)
def test_every_letter_packs_identically_in_all_three(char: str) -> None:
    """
    Interpreter, compiled H-ISA, and the hisab package, on all three words.
    """
    words = expected_words(char)
    for index, want in enumerate(words):
        source = f"let h = '{char}';\nprintln(h.pack({index}));\n"
        assert int(run_hc(source)[0]) == want, f"{char} word {index}: interpreter"
        assert run_compiled(source) == want, f"{char} word {index}: machine"


@pytest.mark.parametrize("char", LETTERS, ids=LETTERS)
def test_every_letter_digests_identically(char: str) -> None:
    entry = MASTER_TABLE.get_by_char(char)
    assert entry is not None
    want = serialize_letter(list(entry.vector)).digest
    source = f"let h = '{char}';\nprintln(h.crc());\n"
    assert int(run_hc(source)[0]) == want
    assert run_compiled(source) == want


# ══════════════════════════════════════════════════════════════════
#  A whole frame, which was impossible before
# ══════════════════════════════════════════════════════════════════

def test_a_complete_nine_byte_frame_can_be_assembled_from_the_machine() -> None:
    """
    Word 0 alone is four of nine bytes. Selecting only word 0 meant the
    processor could not produce a HISAB frame at all.
    """
    words = [
        run_compiled(f"let h = 'ب';\nprintln(h.pack({i}));\n") for i in range(3)
    ]
    assert words == list(BA_WORDS)
    assert len(set(words)) == 3, "three distinct words, not one repeated"


def test_word_zero_alone_is_not_the_frame() -> None:
    """Pins what the old behaviour lost, so a regression cannot look correct."""
    assert BA_WORDS[1] != BA_WORDS[0]
    assert BA_WORDS[2] != BA_WORDS[0]


def test_a_word_past_two_names_nothing() -> None:
    words = assemble("HLOAD H0, #2\nHPACK R1, H0, 5\nHALT\n")
    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(words)
    machine.run()
    assert machine.dump_state()["gpr"][1] == 0


def test_the_compiler_refuses_an_out_of_range_word() -> None:
    ast = Parser(Lexer("let h = 'ب';\nprintln(h.pack(7));\n").tokenize()).parse()
    with pytest.raises(CodegenError, match="words 0–2"):
        generate(ast, inject(ast))


def test_the_interpreter_refuses_an_out_of_range_word() -> None:
    from hijaiyyah.core.exceptions import EBNFSemanticError

    with pytest.raises(EBNFSemanticError, match="words 0–2"):
        run_hc("let h = 'ب';\nprintln(h.pack(7));\n")
