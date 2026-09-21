"""
CALL and RET: the piece everything above them was written straight without.

The spec reserved 0x2E and 0x2F and marked them "perangkat lunak saja". That is
why kernel.hasm, loader.hasm and every other program in rtl/programs/ is one
long straight line -- a kernel with no subroutines cannot factor anything, and
HFS on top of it would have been worse.

They are branches. The one design decision is where the return address lives,
and it is not the PUSH/POP stack: in hardware that array is read synchronously,
so a pop's value arrives a stage after RET needs it, and making the read
combinational would turn the array into flip-flops (hcpu_memory.v records the
number: 8,392) on a board already over its LUT budget.

So a small array of its own, read combinationally, and RET resolves in Execute
exactly like a branch. The visible cost is that CALL and PUSH do not share a
stack. The visible gain is the mirror of it, and it is tested below: an
unbalanced PUSH inside a subroutine cannot corrupt the return path.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import HISAMachine
from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, OpCode

ROOT = Path(__file__).resolve().parents[2]
PKG = (ROOT / "rtl" / "hcpu_pkg.vh").read_text(encoding="utf-8")
EXECUTE = (ROOT / "rtl" / "hcpu_execute.v").read_text(encoding="utf-8")
PROGRAM = (ROOT / "rtl" / "programs" / "subroutine.hasm").read_text(encoding="utf-8")


def _run(source: str, steps: int = 2000) -> HISAMachine:
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(source)
    n = 0
    while n < steps and m.step() is not None:
        n += 1
    return m


def _at(m: HISAMachine, addr: int) -> int:
    return int(m.data_mem.get(addr, 0))


# ── encoded where the spec put them ─────────────────────────────


def test_call_and_ret_are_where_the_spec_reserved_them() -> None:
    assert OpCode.CALL.value == 0x2E
    assert OpCode.RET.value == 0x2F
    assert OpCode.CALL in RTL_IMPLEMENTED and OpCode.RET in RTL_IMPLEMENTED
    assert re.search(r"`define\s+OP_CALL\s+8'h2E", PKG)
    assert re.search(r"`define\s+OP_RET\s+8'h2F", PKG)
    assert assemble("        CALL 5\n")[0] >> 24 == 0x2E
    assert assemble("        RET\n")[0] >> 24 == 0x2F


def test_the_spec_no_longer_calls_them_software_only() -> None:
    spec = (ROOT / "docs" / "HISA_SPEC.md").read_text(encoding="utf-8")
    rows = [ln for ln in spec.splitlines() if "`CALL`" in ln or "`RET`" in ln]
    assert rows
    for row in rows:
        assert "perangkat lunak saja" not in row, row


# ── they work ───────────────────────────────────────────────────


def test_a_flat_call_returns_to_the_instruction_after_it() -> None:
    m = _run("""        MOVI  R1, 0
        CALL  add7
        CALL  add7
        MOVI  R5, 0
        STORE R1, R5, 0x100
        HALT
add7:   ADDI  R1, R1, 7
        RET
""")
    assert _at(m, 0x100) == 14
    assert m.return_stack == [], "the return stack did not come back balanced"


def test_calls_nest() -> None:
    m = _run("""        MOVI  R1, 0
        CALL  outer
        MOVI  R5, 0
        STORE R1, R5, 0x100
        HALT
outer:  ADDI  R1, R1, 1
        CALL  inner
        ADDI  R1, R1, 100
        RET
inner:  ADDI  R1, R1, 10
        RET
""")
    assert _at(m, 0x100) == 111, "the inner return did not land after its CALL"


def test_an_unbalanced_push_cannot_corrupt_the_return() -> None:
    """The property the separate stack buys. With one shared stack this RET
    would return to 5."""
    m = _run("""        MOVI  R1, 0
        CALL  messy
        MOVI  R5, 0
        STORE R1, R5, 0x100
        HALT
messy:  MOVI  R2, 5
        PUSH  R2
        ADDI  R1, R1, 3
        RET
""")
    assert _at(m, 0x100) == 3


# ── and they fault rather than inventing a target ───────────────


def test_ret_with_nothing_to_return_to_halts() -> None:
    """HC-05. A RET on an empty stack has no correct target; jumping to
    whatever the array happens to hold is how a fault becomes a wild branch.

    The work after the RET is the point. This test once put HALT straight
    after it and asserted `m.halted` -- an attribute the fault path set and
    nothing read -- so it passed while the machine reported HC-05 and ran on:
    this program printed 5. Found by NUI layer 3."""
    m = _run("        RET\n        MOVI  R1, 5\n        PRINT R1\n        HALT\n")
    assert m.output == [], "the machine ran past HC-05"
    assert m.trace[-1].description == "RET → HC-05 return stack underflow"
    assert m.step() is None
    assert m.return_stack == []


def test_the_depth_is_the_same_number_in_both_implementations() -> None:
    depth = int(re.search(r"`define\s+RA_DEPTH\s+(\d+)", PKG).group(1))
    assert HISAMachine.RA_DEPTH == depth == 32


def test_overflow_halts_rather_than_wrapping() -> None:
    """HC-04. Recursion one level past the stack must stop, not wrap onto its
    own oldest frame."""
    m = _run("        CALL loop\n        HALT\nloop:   CALL loop\n        MOVI  R1, 5\n"
             "        PRINT R1\n        RET\n")
    assert m.output == [], "the machine ran past HC-04"
    assert m.trace[-1].description == "CALL → HC-04 return stack overflow"
    assert m.step() is None
    assert len(m.return_stack) == HISAMachine.RA_DEPTH


# ── the RTL agrees, and its bench says so ───────────────────────


def test_the_return_stack_is_read_combinationally_in_execute() -> None:
    """If this becomes a registered read, RET loses its target in the stage
    that redirects and the whole design has to change shape."""
    assert re.search(r"wire\s+\[`CODE_ADDR_W-1:0\]\s+ra_top\s*=\s*ra_stack", EXECUTE)
    assert "ra_stack [0:`RA_DEPTH-1]" in EXECUTE


def test_a_faulting_call_or_ret_does_not_also_branch() -> None:
    body = EXECUTE.split("Branch resolution")[1].split("endcase")[0]
    assert "id_is_call && !ra_overflow" in body
    assert "id_is_ret && !ra_underflow" in body


def test_the_program_and_its_bench_agree_with_the_interpreter() -> None:
    m = _run(PROGRAM)
    expected = {0x100: 21, 0x101: 111, 0x102: 8, 0x103: 3}
    for addr, want in expected.items():
        assert _at(m, addr) == want, f"0x{addr:X} = {_at(m, addr)}, wanted {want}"
    bench = (ROOT / "rtl" / "tb" / "tb_hcpu_subroutine.v").read_text(encoding="utf-8")
    for want in expected.values():
        assert f"== {want}," in bench, f"the bench stopped checking {want}"


@pytest.mark.parametrize("victim", ["id_is_call", "id_is_ret"])
def test_decode_clears_them_on_every_bubble(victim: str) -> None:
    """A stale call bit in a flushed slot would push a return address for an
    instruction that never ran."""
    decode = (ROOT / "rtl" / "hcpu_decode.v").read_text(encoding="utf-8")
    assert decode.count(f"{victim}   <= 1'b0;") >= 3 or \
           decode.count(f"{victim}    <= 1'b0;") >= 3
