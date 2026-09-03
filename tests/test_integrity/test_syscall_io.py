"""
I/O through the kernel, and the two defects that hid behind its absence.

The claim in the build list was that a user process could not do I/O at all.
That was wrong, and the truth was worse: PRINT is this machine's only output
path and it was not privileged, so user mode wrote to the serial line with
nothing in between. Unmediated I/O, not absent I/O -- two processes interleave
characters and nothing arbitrates.

Making PRINT privileged then exposed something larger. Dropping to user mode is
`STORE ... 0xFFD` followed by `ERET`, which is how every program here writes
it, and the ERET read `prev` before the write to it landed. So the machine
stayed in supervisor -- silently, with no fault and no signal. Every program
that "dropped to user mode" on hardware never left privilege, and the
interpreter, which has no pipeline, dropped correctly; the two agreed on every
result they were asked for and differed only on the thing being tested.

One NOP between the store and the ERET was enough to hide it. The fix is that
one is not needed.
"""

from __future__ import annotations

import re
from pathlib import Path

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import HISAMachine
from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, OpCode

ROOT = Path(__file__).resolve().parents[2]
EXECUTE = (ROOT / "rtl" / "hcpu_execute.v").read_text(encoding="utf-8")
TRAP = (ROOT / "rtl" / "hcpu_trap.v").read_text(encoding="utf-8")
PROGRAM = (ROOT / "rtl" / "programs" / "syscall_io.hasm").read_text(encoding="utf-8")
BENCH = (ROOT / "rtl" / "tb" / "tb_hcpu_syscall_io.v").read_text(encoding="utf-8")


def _run(source: str, steps: int = 2000) -> HISAMachine:
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(source)
    n = 0
    while n < steps and m.step() is not None:
        n += 1
    return m


# ── PRINT is the output path, and it is mediated now ────────────


def test_print_writes_a_gpr_not_an_h_register() -> None:
    """0xA0 is PRINT (GPR) and 0xA1 is PRINTH (H-Reg). The interpreter ran
    PRINT with PRINTH's semantics, so the two implementations disagreed about
    what the opcode does while both were listed as having it."""
    m = _run("        MOVI R3, 42\n        PRINT R3\n        HALT\n")
    assert m.output == [42]
    assert OpCode.PRINT.value == 0xA0 and OpCode.PRINTH.value == 0xA1
    assert OpCode.PRINT in RTL_IMPLEMENTED
    assert OpCode.PRINTH not in RTL_IMPLEMENTED, "PRINTH is software-only"


def test_user_mode_cannot_print_directly() -> None:
    m = _run("""        MOVI  R5, 0
        MOVI  R1, handler
        STORE R1, R5, 0xFF8
        MOVI  R1, usr
        STORE R1, R5, 0xFF9
        MOVI  R1, 0
        STORE R1, R5, 0xFFD
        ERET
usr:    MOVI  R3, 99
        PRINT R3
        HALT
handler:MOVI  R10, 1
        HALT
""")
    assert m.output == [], "user mode reached the serial line unmediated"
    assert m.regs.gpr[10] == 1, "the direct PRINT did not trap"


def test_print_is_privileged_in_the_rtl_too() -> None:
    fault = EXECUTE.split("assign priv_fault")[1].split(";")[0]
    assert "id_is_print" in fault
    assert "ex_is_print <= id_is_print & ~priv_fault;" in EXECUTE, (
        "a refused PRINT must not still reach the UART"
    )


# ── the mode race ───────────────────────────────────────────────


def test_an_eret_sees_a_mode_write_from_the_same_cycle() -> None:
    """This is the whole bug. Without it, `STORE ... 0xFFD` then `ERET` --
    the only way anything drops to user mode, and how every program here is
    written -- returned to supervisor and said nothing."""
    assert "prev_at_eret" in TRAP
    assert re.search(r"wire\s+mode_write\s*=\s*reg_we\s*&&\s*\(reg_sel == `REG_TRAP_MODE\)", TRAP)
    body = TRAP.split("if (eret) begin")[1].split("end else if (fire)")[0]
    assert "mode        <= prev_at_eret;" in body
    assert "mode        <= prev;" not in body


def test_the_program_does_not_pad_around_the_race() -> None:
    """A NOP between the store and the ERET makes the symptom go away without
    the defect going away, and would leave the next program to rediscover it."""
    tail = PROGRAM.split("STORE R1, R5, 0xFFD")[1].split("ERET")[0]
    assert "NOP" not in tail, "the program is working around the race again"


# ── what the program proves ─────────────────────────────────────


def test_the_right_number_reaches_the_wire_and_the_wrong_one_does_not() -> None:
    """Something arriving proves nothing on its own. The user asks for 42 and
    tries to print 99 itself, so the test is which of the two came out."""
    m = _run(PROGRAM)
    assert m.output == [42], f"the wire carried {m.output}"
    assert m.regs.gpr[10] == 1, "the direct PRINT was not refused"
    assert m.regs.gpr[8] == 1, "the handler did not step over the refused PRINT"
    assert m.regs.gpr[7] == 1 and m.regs.gpr[1] == 1, "the syscall was not served"


def test_the_bench_checks_both_sides_too() -> None:
    assert "saw_42" in BENCH and "saw_99" in BENCH
    assert "check(!saw_99," in BENCH, "the bench stopped checking the negative"
    assert "HALF_PERIOD = 18.5" in BENCH, (
        "the bench decodes the wire, so it has to clock the board at 27 MHz"
    )


def test_the_handler_is_written_with_subroutines() -> None:
    """It is the first program here that could be, and factoring `skip` out is
    the point: both causes name their own instruction."""
    assert "CALL  skip" in PROGRAM and "RET" in PROGRAM
    assert PROGRAM.count("CALL  skip") == 2
