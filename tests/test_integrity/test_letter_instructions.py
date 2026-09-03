"""
One letter is the whole instruction.

Writing a command should not need numbers. A letter already carries a value,
a function and a rate -- measured at roughly 4.6 bits as an operator against a
bit's one -- so spelling it out as an opcode plus a register plus an immediate
discards what it already holds.

    ب            assembles to 0xE1000000
    HREG[0] <- HREG[0] + v(Ba)

No register field, because there is nothing to choose: the accumulator is
implicit. That is safe rather than merely short, and the reason is measured
elsewhere -- the guard is closed under addition over all 784 pairs, so a
program made of letters cannot leave the valid set.

The consequence is that a WORD COMPUTES ITS OWN CODEX BY BEING WRITTEN. Three
letters of source and the accumulator holds what string_integral returns.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from hijaiyyah.algebra.aggregametric import string_integral
from hijaiyyah.core.guards import guard_check
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import HISAMachine
from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, OpCode

ROOT = Path(__file__).resolve().parents[2]
ENTRIES = MASTER_TABLE.all_entries()
FIRST, LAST = 0xE0, 0xFB


def _run(source: str) -> HISAMachine:
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(source)
    while m.step() is not None:
        pass
    return m


def test_twenty_eight_letters_fit_the_range_exactly() -> None:
    assert LAST - FIRST + 1 == 28 == len(ENTRIES)
    for i, e in enumerate(ENTRIES):
        op = OpCode[f"L_{e.name.upper()}"]
        assert int(op) == FIRST + i
        assert op in RTL_IMPLEMENTED
    assert int(OpCode.HALT_ERR) == 0xFF > LAST


def test_the_arabic_letter_is_a_line_of_source() -> None:
    """`ج` and `L_JIM` assemble identically. That is the whole point."""
    for e in ENTRIES:
        assert assemble(f"        {e.char}\n") == assemble(f"        L_{e.name.upper()}\n")
    assert assemble("        ج\n") == [0xE4000000]


def test_a_letter_instruction_carries_no_operands() -> None:
    """No register, no immediate: every field below the opcode byte is zero."""
    for e in ENTRIES:
        word = assemble(f"        {e.char}\n")[0]
        assert word & 0x00FFFFFF == 0, e.char
        assert word >> 24 == int(OpCode[f"L_{e.name.upper()}"])


def test_writing_a_word_computes_its_codex() -> None:
    for word in ("بسم", "جحخ", "الله", "ملك"):
        letters = "".join(c for c in word if MASTER_TABLE.get_by_char(c))
        source = "".join(f"        {c}\n" for c in letters) + "        HALT\n"
        machine = _run(source)
        assert list(machine.regs.hreg[0]) == list(string_integral(letters)["cod18"])


def test_a_program_of_letters_cannot_leave_the_valid_set() -> None:
    """
    What makes the implicit accumulator defensible. Closure is measured
    elsewhere; here it is relied on, so it is checked at every step rather
    than only at the end.
    """
    import itertools

    for combo in itertools.islice(itertools.product(ENTRIES, repeat=3), 0, 400, 7):
        source = "".join(f"        {e.char}\n" for e in combo) + "        HALT\n"
        m = HISAMachine(MASTER_TABLE)
        m.code = assemble(source)
        while m.step() is not None:
            assert guard_check(list(m.regs.hreg[0]))


def test_the_index_base_differs_between_the_two_accessors() -> None:
    """
    get_by_index is 1-BASED and all_entries() is 0-based. The interpreter used
    the 0-based offset against the 1-based accessor and silently accumulated
    the wrong letters; the RTL, which adds one to reach its 1-indexed ROM, was
    right. Pinned because nothing else in the package makes the difference
    visible.
    """
    assert MASTER_TABLE.get_by_index(1).name == "Alif"
    assert ENTRIES[0].name == "Alif"
    assert MASTER_TABLE.get_by_index(2).name == ENTRIES[1].name == "Ba"

    machine = _run("        ب\n        HALT\n")
    assert list(machine.regs.hreg[0]) == list(ENTRIES[1].vector)


@pytest.mark.parametrize("path", ["rtl/hcpu_decode.v", "rtl/hcpu_execute.v"])
def test_the_rtl_recognises_the_range_rather_than_28_cases(path: str) -> None:
    """
    One range check, not twenty-eight cases. decode's `default` is HALT_ERR,
    so the letters must be caught before it -- and Execute needed exactly one
    new path: the ROM's output as the codex ALU's second operand.
    """
    text = (ROOT / path).read_text(encoding="utf-8")
    assert "`LETTER_OP_FIRST" in text and "`LETTER_OP_LAST" in text
    if path.endswith("execute.v"):
        assert "is_letter ? rom_data : id_hreg_s2" in text
        assert re.search(r"letter_index\s*=\s*\n?\s*\(id_opcode - `LETTER_OP_FIRST\) \+ 1", text)


def test_the_range_bounds_are_not_parsed_as_opcodes() -> None:
    """
    LETTER_OP_FIRST, not OP_LETTER_FIRST. The parity test parses every
    `define OP_* as an opcode, and the bounds are not opcodes.
    """
    pkg = (ROOT / "rtl" / "hcpu_pkg.vh").read_text(encoding="utf-8")
    assert "`define LETTER_OP_FIRST" in pkg
    assert "`define OP_LETTER_FIRST" not in pkg
    names = set(re.findall(r"`define\s+OP_([A-Z0-9_]+)\s+8'h", pkg))
    assert "LETTER_FIRST" not in names and "LETTER_LAST" not in names
    assert len({n for n in names if n.startswith("L_")}) == 28
