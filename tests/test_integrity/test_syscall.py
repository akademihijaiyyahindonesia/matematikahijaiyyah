"""
Syscall: the sixth and last H-Kernel prerequisite.

Supervisor mode refuses user code the peripheral window; memory protection
refuses it everything outside its own window. Together they make a wall. A
wall is not a kernel -- a user program that can compute and never ask for
anything is not a process, it is an expression.

SYSCALL is the door. It raises a trap deliberately, and epc points AT the SYSCALL
rather than past it, so the handler decides whether to serve the call or
refuse it: serving means advancing epc by one, refusing means not.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import HISAMachine
from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, OpCode

ROOT = Path(__file__).resolve().parents[2]
PKG = (ROOT / "rtl" / "hcpu_pkg.vh").read_text(encoding="utf-8")
DECODE = (ROOT / "rtl" / "hcpu_decode.v").read_text(encoding="utf-8")
EXECUTE = (ROOT / "rtl" / "hcpu_execute.v").read_text(encoding="utf-8")
TRAP = (ROOT / "rtl" / "hcpu_trap.v").read_text(encoding="utf-8")


def _machine(source: str) -> HISAMachine:
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(source)
    return m


def test_syscall_is_encoded_and_carries_no_operands() -> None:
    assert OpCode.SYSCALL.value == 0x09
    assert OpCode.SYSCALL in RTL_IMPLEMENTED
    assert re.search(r"`define\s+OP_SYSCALL\s+8'h09", PKG)
    word = assemble("        SYSCALL\n")[0]
    assert word >> 24 == 0x09
    assert word & 0x00FFFFFF == 0, "SYSCALL grew an operand field"


def test_decode_recognises_it_or_it_would_halt_the_machine() -> None:
    """
    decode's `default` is HALT_ERR. OP_ERET fell into it for several commits
    and stopped the pipeline while appearing to work; SYSCALL would do the same.
    """
    assert "`OP_SYSCALL:" in DECODE
    assert "assign is_syscall = (id_opcode == `OP_SYSCALL);" in EXECUTE


def test_a_syscall_names_its_own_instruction() -> None:
    """
    epc points AT the SYSCALL. Pointing past it would remove the handler's only
    chance to refuse the call -- it could no longer decline by leaving epc
    alone, because control would already have moved on.
    """
    m = _machine("        SYSCALL\n        HALT\n")
    m.trap_vector = 1
    m.step()
    assert m._maybe_trap() is not None
    assert m.trap_cause == m.TRAP_SYSCALL
    assert m.trap_epc == 0, "epc should point at the SYSCALL, not past it"
    assert "(which >= `TRAP_PRIV) ? pc_fault : pc_now" in TRAP


def test_a_syscall_fires_with_every_enable_bit_clear() -> None:
    """
    Non-maskable, and for a sharper reason than the two faults beside it. A
    maskable privilege violation is a hole; a maskable syscall does not fault
    at all -- user code calls, gets no answer, and continues on a return value
    that was never written. Silence is worse than refusal.
    """
    m = _machine("        SYSCALL\n        HALT\n")
    m.trap_enable = 0
    m.trap_vector = 1
    m.step()
    assert m._maybe_trap() is not None
    assert m.trap_cause == m.TRAP_SYSCALL

    assert m.NONMASKABLE == (1 << m.TRAP_PRIV) | (1 << m.TRAP_MEM) | (1 << m.TRAP_SYSCALL)
    assert "(1 << `TRAP_PRIV) | (1 << `TRAP_MEM) | (1 << `TRAP_SYSCALL)" in TRAP


def test_ecall_is_allowed_in_user_mode_and_is_not_a_privilege_fault() -> None:
    """
    The point of it. Every other crossing is refused; this one is refused and
    then served, which is a different thing.
    """
    m = _machine("        SYSCALL\n        HALT\n")
    m.mode = m.MODE_USER
    m.step()
    assert m._syscall
    assert not m._priv_fault, "SYSCALL was treated as a privilege violation"

    # And Execute does not gate it on in_user, so a supervisor may call itself.
    assert "in_user" not in EXECUTE.split("assign is_syscall")[1].split("\n")[0]
    m = _machine("        SYSCALL\n        HALT\n")
    m.step()
    assert m._syscall


def test_the_causes_are_ordered_interrupts_below_exceptions() -> None:
    m = HISAMachine(MASTER_TABLE)
    assert (m.TRAP_TIMER, m.TRAP_UART_RX) == (0, 1)          # interrupts
    assert (m.TRAP_PRIV, m.TRAP_MEM, m.TRAP_SYSCALL) == (3, 4, 5)   # exceptions
    assert m.TRAP_CAUSES == 6

    hit = re.search(r"^`define\s+TRAP_CAUSES\s+(\d+)", PKG, re.M)
    assert hit and int(hit.group(1)) == 6
    # Everything at or above TRAP_PRIV names its own instruction.
    for cause in (m.TRAP_PRIV, m.TRAP_MEM, m.TRAP_SYSCALL):
        assert cause >= m.TRAP_PRIV


def test_the_whole_crossing_works_and_the_answer_comes_back() -> None:
    source = (ROOT / "rtl" / "programs" / "syscall.hasm").read_text(encoding="utf-8")
    m = _machine(source)
    for _ in range(400):
        if m.step() is None:
            break

    assert m._halted, "the program never finished"
    g = m.regs.gpr
    assert g[10] == m.TRAP_SYSCALL, "the handler saw the wrong cause"
    assert g[9] == 1, "the handler never served the call"
    assert g[1] == 42, f"wrong result: {g[1]}"          # 35 + 7
    assert g[8] == 1, "execution did not resume past the SYSCALL"

    traps = [t.description for t in m.trace if "TRAP" in t.description]
    assert len(traps) == 1, f"expected one crossing, got {len(traps)}"


def test_a_handler_that_does_not_advance_epc_re_enters_the_call() -> None:
    """
    The behaviour a handler author has to know, and the reason epc points at
    the instruction. Not advancing it is how a handler REFUSES -- the call is
    simply retried -- so it must be visible rather than silently skipped.
    """
    source = (ROOT / "rtl" / "programs" / "syscall.hasm").read_text(encoding="utf-8")
    broken = source.replace("        ADDI  R11, R11, 1", "        ADDI  R11, R11, 0")
    assert broken != source

    m = _machine(broken)
    for _ in range(400):
        if m.step() is None:
            break
    assert not m._halted
    assert len([t for t in m.trace if "TRAP" in t.description]) > 5


def test_the_handler_must_use_cmpi_because_sub_sets_no_flags() -> None:
    """
    Kept because the first version of the demonstration used SUB and then JNE,
    and the handler silently took its refuse path on every call. SUB does not
    set the flags; CMPI does.
    """
    source = (ROOT / "rtl" / "programs" / "syscall.hasm").read_text(encoding="utf-8")
    assert "CMPI  R10, 5" in source
    assert "SUB   R4, R10" not in source

    # R1 - R1 is zero, so a SUB that set the flags would clear JNE's branch
    # and fall through to MOVI R3, 1. It does not: Z stays clear from reset,
    # JNE takes the jump, and R3 is never written. That is exactly how the
    # handler took its refuse path on every call.
    m = _machine("        MOVI R1, 5\n        SUB R2, R1, R1\n        JNE done\n"
                 "        MOVI R3, 1\ndone:   HALT\n")
    while m.step() is not None:
        pass
    assert m.regs.gpr[2] == 0, "the SUB itself did not compute zero"
    assert m.regs.gpr[3] == 0, "SUB started setting the zero flag"

    # CMPI does set it, which is why the handler uses that.
    m = _machine("        MOVI R1, 5\n        CMPI R1, 5\n        JNE done\n"
                 "        MOVI R3, 1\ndone:   HALT\n")
    while m.step() is not None:
        pass
    assert m.regs.gpr[3] == 1, "CMPI stopped setting the zero flag"


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_whole_cpu_elaborates_with_the_syscall_path() -> None:
    files = sorted(str(p) for p in (ROOT / "rtl").glob("hcpu_*.v"))
    res = subprocess.run(["iverilog", "-g2012", "-I", "rtl", "-o", "/tmp/hcpu_sys",
                          *files], cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
