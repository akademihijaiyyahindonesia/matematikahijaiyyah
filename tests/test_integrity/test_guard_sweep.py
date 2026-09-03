"""
rtl/programs/test_guard.hasm: every canonical letter passes its own guard.

The program's own header comment claimed this since it was written --
"Tests HLOAD + HGRD for every letter in the Master Table" -- and nothing had
ever run it and looked at the answer. `HLOAD H0, R2` used to assemble without
complaint (the operand parser had a register fallback, "immreg", meant for
exactly this), but hcpu_execute.v's `rom_addr` never reads S1 for HLOAD, only
IMM -- so the register vanished silently and the loop spent its whole life
loading ROM index 0 twenty-eight times over. R0 never moved past 0.

The RTL/VM parity suite (test_execution_parity.py) would not have caught this
either: it checks that the interpreter and the pipeline agree with EACH OTHER,
and they did -- both silently computed the same wrong answer, because both
read the same immediate field the same way. Agreement is not correctness;
this file is the test that checks the actual number.
"""

from __future__ import annotations

from pathlib import Path

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import HISAMachine

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = (ROOT / "rtl" / "programs" / "test_guard.hasm").read_text(encoding="utf-8")


def test_all_twenty_eight_letters_pass_their_own_guard() -> None:
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(PROGRAM)
    n = 0
    while n < 2000 and m.step() is not None:
        n += 1
    assert m.regs.gpr[0] == 28, f"only {m.regs.gpr[0]} of 28 letters passed"
    assert m.output == [28], "PRINT did not report the pass count"


def test_the_program_names_no_register_operand_for_hload() -> None:
    """The defect in one line: `HLOAD H0, Rn` assembles, but hardware only
    ever reads the immediate field. Twenty-eight separate immediates is the
    only correct form -- the same shape the guard daemon in kernel.hasm and
    the HAR lookup in hos.hasm both use for the same reason."""
    body = [ln for ln in PROGRAM.splitlines() if ln.strip().startswith("HLOAD")]
    assert len(body) == 28
    for ln in body:
        operand = ln.split(",", 1)[1].strip()
        assert operand.isdigit(), f"HLOAD with a non-immediate operand: {ln!r}"
