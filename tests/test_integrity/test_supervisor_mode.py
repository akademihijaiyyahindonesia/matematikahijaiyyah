"""
Supervisor mode: the fourth OS prerequisite, after bitwise, UART+timer, traps.

Two levels, and the peripheral window is the boundary. Everything the trap
unit, the timer and the UART expose lives there, so one rule covers all of
them, and user code reaches them through a syscall -- which is the step after
this one.

Three things here are load-bearing and each is easy to get subtly wrong:

  * TRAP_PRIV IS NOT MASKABLE. A timer or a UART byte is an interrupt: it
    arrives from outside and software may say "not now". A privilege violation
    is an exception -- the instruction stream doing what it may not -- and a
    maskable protection is not a protection, because user code would clear one
    bit and walk through.

  * THE FAULT IS RAISED IN EXECUTE, not in the peripheral decoder, because
    Execute is the last stage that still knows the PC. An exception that
    cannot name where it happened is not much of an exception.

  * A FAULTING ERET MUST NOT ALSO RETURN. Without that, the one instruction
    that changes privilege changes it while reporting it was not allowed to.
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

ROOT = Path(__file__).resolve().parents[2]
PKG = (ROOT / "rtl" / "hcpu_pkg.vh").read_text(encoding="utf-8")
EXECUTE = (ROOT / "rtl" / "hcpu_execute.v").read_text(encoding="utf-8")
TRAP = (ROOT / "rtl" / "hcpu_trap.v").read_text(encoding="utf-8")


def _machine(source: str) -> HISAMachine:
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(source)
    return m


def _user(m: HISAMachine) -> HISAMachine:
    m.mode = m.MODE_USER
    return m


# ══════════════════════════════════════════════════════════════════
#  One truth: the package
# ══════════════════════════════════════════════════════════════════

def test_the_mode_constants_match_the_package() -> None:
    m = HISAMachine(MASTER_TABLE)
    for attr, define in (("TRAP_PRIV", "TRAP_PRIV"), ("TRAP_CAUSES", "TRAP_CAUSES"),
                         ("REG_TRAP_MODE", "REG_TRAP_MODE")):
        hit = re.search(rf"^`define\s+{define}\s+(?:\d*'[hd])?([0-9A-Fa-f]+)", PKG, re.M)
        assert hit, define
        base = 16 if "'h" in hit.group(0) else 10
        assert getattr(m, attr) == int(hit.group(1), base), attr
    assert m.MODE_USER == 0 and m.MODE_SUPER == 1
    assert "`define MODE_USER         1'b0" in PKG


# ══════════════════════════════════════════════════════════════════
#  Reset, and the only way into user mode
# ══════════════════════════════════════════════════════════════════

def test_reset_lands_in_supervisor() -> None:
    """
    A machine that came up in user mode could never configure itself, because
    configuring it means touching the window user mode cannot touch.
    """
    m = HISAMachine(MASTER_TABLE)
    assert m.mode == m.MODE_SUPER
    m.mode = m.MODE_USER
    m.reset()
    assert m.mode == m.MODE_SUPER
    assert "mode        <= `MODE_SUPER;" in TRAP


def test_entering_user_mode_takes_a_write_and_an_eret() -> None:
    m = HISAMachine(MASTER_TABLE)
    m.trap_epc = 40
    m._periph_write(m.REG_TRAP_MODE, 0b00)      # previous := USER
    assert m.trap_prev == m.MODE_USER
    m.code = assemble("        ERET\n")
    m.step()
    assert m.mode == m.MODE_USER
    assert m.regs.pc == 40


def test_the_current_mode_bit_is_read_only() -> None:
    """
    If bit 0 were writable, dropping privilege and raising it again would be
    the same instruction, and the boundary would not exist.
    """
    m = HISAMachine(MASTER_TABLE)
    m.mode = m.MODE_USER
    m._periph_write(m.REG_TRAP_MODE, 0b01)      # try to set mode = SUPER
    assert m.mode == m.MODE_USER
    assert m._periph_read(m.REG_TRAP_MODE) & 1 == m.MODE_USER
    assert "`REG_TRAP_MODE:   prev   <= reg_wdata[1];" in TRAP


# ══════════════════════════════════════════════════════════════════
#  What user mode may not do
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("addr", [0xFF0, 0xFF4, 0xFF8, 0xFFB, 0xFFD, 0xFFF])
def test_user_mode_cannot_touch_the_peripheral_window(addr: int) -> None:
    m = _user(_machine("        MOVI R1, 0\n"))
    m._mem_read(addr)
    assert m._priv_fault, f"read of {addr:#x} was allowed"

    m._priv_fault = False
    m._mem_write(addr, 0xDEAD)
    assert m._priv_fault, f"write to {addr:#x} was allowed"


def test_a_refused_read_does_not_consume_the_byte_it_refused() -> None:
    """
    Suppressed, not performed and undone. Reading RX_DATA consumes a byte, so
    letting it through would destroy state the handler is about to be told did
    not happen.
    """
    m = _user(_machine("        MOVI R1, 0\n"))
    m.rx_queue = [0x41, 0x42]
    assert m._mem_read(0xFF0) == 0
    assert m.rx_queue == [0x41, 0x42], "the byte was consumed by a refused read"


def test_ordinary_memory_stays_open_to_user_mode() -> None:
    """The boundary is the window, not memory. A user program still has RAM."""
    m = _user(_machine("        MOVI R1, 0\n"))
    m._mem_write(0x100, 0x1234)
    assert m._mem_read(0x100) == 0x1234
    assert not m._priv_fault


def test_halt_and_eret_are_privileged_and_do_not_take_effect() -> None:
    m = _user(_machine("        HALT\n"))
    m.step()
    assert m._priv_fault
    assert not m._halted, "user mode halted the machine"

    m = _user(_machine("        ERET\n"))
    m.trap_epc = 99
    m.step()
    assert m._priv_fault
    assert m.mode == m.MODE_USER, "a faulting ERET still changed privilege"
    assert m.regs.pc != 99, "a faulting ERET still returned"
    assert "assign is_eret = eret_decoded && !in_user;" in EXECUTE


# ══════════════════════════════════════════════════════════════════
#  Exception, not interrupt
# ══════════════════════════════════════════════════════════════════

def test_a_privilege_fault_fires_with_every_enable_bit_clear() -> None:
    """The distinction the whole design rests on."""
    m = _user(_machine("        MOVI R1, 0\n" * 4))
    m.trap_enable = 0                       # everything masked
    m.trap_vector = 2
    m._priv_fault = True
    assert m._maybe_trap() is not None, "a maskable protection is not one"
    assert m.trap_cause == m.TRAP_PRIV
    assert "NONMASKABLE" in TRAP


def test_interrupts_still_obey_the_mask() -> None:
    m = _machine("        MOVI R1, 0\n" * 4)
    m.trap_enable = 0
    m.timer_expired = True
    assert m._maybe_trap() is None, "a masked interrupt fired"


def test_the_fault_is_raised_where_the_pc_is_still_known() -> None:
    """
    Detected in Execute rather than in the peripheral decoder. Memory has no
    PC -- the pipeline carries id_pc only as far as Execute -- so a fault
    found there could not name its instruction.
    """
    assert "output wire                    priv_fault," in EXECUTE
    assert "input  wire                    in_user," in EXECUTE
    top = (ROOT / "rtl" / "hcpu_top.v").read_text(encoding="utf-8")
    assert ".pc_fault      (id_pc)," in top
    assert ".src_priv      (trap_priv_fault_w)," in top
    # And the trap unit must choose between the two PCs by cause.
    assert "(which == `TRAP_PRIV) ? pc_fault : pc_now" in TRAP


# ══════════════════════════════════════════════════════════════════
#  The whole program
# ══════════════════════════════════════════════════════════════════

def test_a_user_program_faults_is_rescued_and_finishes() -> None:
    source = (ROOT / "rtl" / "programs" / "user_mode.hasm").read_text(encoding="utf-8")
    m = _machine(source)
    for _ in range(300):
        if m.step() is None:
            break

    assert m._halted, "the program never finished"
    g = m.regs.gpr
    assert g[7] == 1, "user code did not run at all"
    assert g[8] == 0, "the timer read was ALLOWED — the boundary leaked"
    assert g[10] == 1, "the handler never ran"
    assert g[11] == m.TRAP_PRIV, f"wrong cause: {g[11]}"
    assert g[9] == 1, "control never came back after the handler"
    assert m.mode == m.MODE_SUPER

    traps = [t.description for t in m.trace if "TRAP" in t.description]
    assert len(traps) == 1, f"expected one fault, got {traps}"
    # epc points AT the faulting instruction, so the handler had to step past
    # it. If it pointed past, the handler's ADDI would have skipped a good one.
    assert "epc=11" in traps[0], traps[0]


def test_not_stepping_past_the_fault_loops_only_if_privilege_is_not_restored() -> None:
    """
    Two things have to go wrong together, and the first version of this test
    got that wrong: it removed only the step and expected a loop. The shipped
    handler also returns to SUPERVISOR, and a supervisor may read the timer --
    so the same instruction succeeds on the retry and the program finishes.

    The loop needs the handler to return to USER mode as well. Then epc points
    at an instruction that is still forbidden, and it faults forever. Which is
    the right behaviour: a silent skip nobody asked for is harder to find.
    """
    source = (ROOT / "rtl" / "programs" / "user_mode.hasm").read_text(encoding="utf-8")

    # Only the step removed: the retry succeeds, because we came back as
    # supervisor and the window is open to us.
    retried = source.replace("        ADDI  R12, R12, 1", "        ADDI  R12, R12, 0")
    assert retried != source
    m = _machine(retried)
    for _ in range(400):
        if m.step() is None:
            break
    assert m._halted, "the retry should have succeeded in supervisor mode"
    assert m.regs.gpr[8] != 0, "the retried read produced nothing"

    # Step removed AND privilege not restored: forbidden instruction, forever.
    looping = retried.replace("        MOVI  R1, 2             ; bit1 = 1 → return to SUPERVISOR",
                              "        MOVI  R1, 0             ; stay in user mode")
    assert looping != retried
    m = _machine(looping)
    for _ in range(400):
        if m.step() is None:
            break
    assert not m._halted
    assert len([t for t in m.trace if "TRAP" in t.description]) > 5


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_whole_cpu_elaborates_with_privilege_wired_in() -> None:
    files = sorted(str(p) for p in (ROOT / "rtl").glob("hcpu_*.v"))
    res = subprocess.run(["iverilog", "-g2012", "-I", "rtl", "-o", "/tmp/hcpu_priv",
                          *files], cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
