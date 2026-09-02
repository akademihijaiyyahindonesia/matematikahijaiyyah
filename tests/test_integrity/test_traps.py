"""
Traps: the third OS prerequisite, after bitwise and after UART receive plus
the timer. A timer that cannot preempt is a counter, and a UART that cannot
interrupt has to be polled, which costs the whole CPU. Neither is an OS.

The hard part is not entry. It is that the sources are LEVEL-sensitive: UART
rx_ready stays high until the byte is read and the timer's flag is sticky
until written, so without a latch saying "a trap is already running" the very
next cycle traps again, from inside the handler, and the handler's first
instruction never retires. `in_trap` is that latch and ERET is what clears it.
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

needs_iverilog = pytest.mark.skipif(
    shutil.which("iverilog") is None, reason="iverilog not installed")


def _machine(source: str) -> HISAMachine:
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(source)
    return m


def _define(name: str) -> int:
    """One `define from hcpu_pkg.vh, as an int. The package is the source."""
    hit = re.search(rf"^`define\s+{name}\s+(\d*'[hd])?([0-9A-Fa-f_]+)", PKG, re.M)
    assert hit, f"{name} not defined in hcpu_pkg.vh"
    text = hit.group(2).replace("_", "")
    return int(text, 16 if (hit.group(1) or "").endswith("'h") else 10)


# ══════════════════════════════════════════════════════════════════
#  One truth: the package, and the machine that mirrors it
# ══════════════════════════════════════════════════════════════════

def test_the_register_map_and_causes_match_the_package() -> None:
    """
    These numbers exist in three places -- the package, hcpu_mmio's decoder,
    and the machine model. The package is the one that defines them; the other
    two must read the same values or a handler correct on the interpreter
    writes to the wrong register on silicon.
    """
    m = HISAMachine(MASTER_TABLE)
    for attr, define in (
        ("REG_RX_DATA", "REG_RX_DATA"), ("REG_RX_STATUS", "REG_RX_STATUS"),
        ("REG_TX_STATUS", "REG_TX_STATUS"), ("REG_COUNTER", "REG_COUNTER"),
        ("REG_COMPARE", "REG_COMPARE"), ("REG_TIMER_STATUS", "REG_TIMER_ST"),
        ("REG_TRAP_VECTOR", "REG_TRAP_VECTOR"), ("REG_TRAP_EPC", "REG_TRAP_EPC"),
        ("REG_TRAP_CAUSE", "REG_TRAP_CAUSE"),
        ("REG_TRAP_ENABLE", "REG_TRAP_ENABLE"),
        ("REG_TRAP_PENDING", "REG_TRAP_PENDING"),
        ("TRAP_TIMER", "TRAP_TIMER"), ("TRAP_UART_RX", "TRAP_UART_RX"),
        ("TRAP_ILLEGAL", "TRAP_ILLEGAL"), ("TRAP_CAUSES", "TRAP_CAUSES"),
        ("TRAP_MASK_W", "TRAP_MASK_W"),
    ):
        assert getattr(m, attr) == _define(define), attr

    assert m.PERIPH_BASE == _define("PERIPH_BASE")


def test_mmio_reads_the_map_from_the_package_not_its_own_copy() -> None:
    """The decoder used to hold localparam copies. One truth, one place."""
    mmio = (ROOT / "rtl" / "hcpu_mmio.v").read_text(encoding="utf-8")
    for name in ("PERIPH_BASE", "REG_RX_DATA", "REG_COMPARE", "REG_TIMER_ST"):
        assert f"`{name}" in mmio, f"{name} is not taken from the package"
    assert not re.search(r"localparam\s+\[3:0\]\s+REG_\w+\s*=\s*4'h", mmio), (
        "a hard-coded register number is back in the decoder")


def test_eret_is_the_only_instruction_the_traps_needed() -> None:
    """
    Vector, epc, cause, enable and pending are all memory. Only the return had
    to be an instruction, because clearing the latch and redirecting the fetch
    must be indivisible: a trap arriving between a load and a jump would be
    taken with the old epc still in place.
    """
    assert OpCode.ERET in RTL_IMPLEMENTED
    assert OpCode.ERET.value == _define("OP_ERET") == 0x08


# ══════════════════════════════════════════════════════════════════
#  The unit, on hardware
# ══════════════════════════════════════════════════════════════════

@needs_iverilog
def test_the_trap_unit_enters_holds_and_returns() -> None:
    out = ROOT / "rtl" / "tb" / "tb_hcpu_trap.v"
    subprocess.run(
        ["iverilog", "-g2012", "-I", "rtl", "-o", "/tmp/tb_hcpu_trap",
         "rtl/hcpu_trap.v", str(out)], cwd=ROOT, check=True, capture_output=True)
    res = subprocess.run(["vvp", "/tmp/tb_hcpu_trap"], cwd=ROOT,
                         capture_output=True, text=True)
    assert "PASS" in res.stdout, res.stdout


@needs_iverilog
def test_the_whole_cpu_still_elaborates_with_the_trap_unit_in_it() -> None:
    files = sorted(str(p) for p in (ROOT / "rtl").glob("hcpu_*.v"))
    res = subprocess.run(["iverilog", "-g2012", "-I", "rtl", "-o", "/tmp/hcpu_all",
                          *files], cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_the_illegal_cause_is_defined_but_tied_off() -> None:
    """
    TRAP_ILLEGAL reserves its encoding so adding it later renumbers nothing.
    Nothing raises it yet, and that has to be pinned rather than assumed: the
    only illegal-instruction path is HALT_ERR on a bad ROM index, and turning
    a halt into a trap is a semantic change, not part of adding traps.
    """
    top = (ROOT / "rtl" / "hcpu_top.v").read_text(encoding="utf-8")
    assert re.search(r"\.src_illegal\s*\(\s*1'b0\s*\)", top), (
        "src_illegal is wired to something -- update this test and the comment")
    m = HISAMachine(MASTER_TABLE)
    m.trap_enable = 0xFF
    assert not (m._trap_pending() >> m.TRAP_ILLEGAL) & 1


# ══════════════════════════════════════════════════════════════════
#  The model
# ══════════════════════════════════════════════════════════════════

BARE = "        MOVI  R5, 0\n        HALT\n"


def _armed(enable: int) -> HISAMachine:
    m = _machine(BARE)
    m.trap_vector = 0x40
    m.trap_enable = enable
    return m


def test_a_source_with_no_enable_does_not_trap() -> None:
    m = _armed(0)
    m.timer_expired = True
    assert m._maybe_trap() is None
    assert not m.trap_active
    # ...but it is still visible as pending, masked or not.
    assert m._trap_pending() & (1 << m.TRAP_TIMER)


def test_entry_saves_the_pc_and_records_the_cause_as_an_index() -> None:
    m = _armed(1 << HISAMachine(MASTER_TABLE).TRAP_TIMER)
    m.timer_expired = True
    m.regs.pc = 7
    assert m._maybe_trap() is not None
    assert m.regs.pc == 0x40          # the vector
    assert m.trap_epc == 7            # where it will return
    assert m.trap_cause == m.TRAP_TIMER
    assert m.trap_active


def test_a_running_trap_does_not_re_enter_on_its_own_still_high_source() -> None:
    """Without the latch this is an infinite loop, not a slow handler."""
    m = _armed(1)
    m.timer_expired = True
    m.regs.pc = 7
    m._maybe_trap()
    for _ in range(10):
        assert m._maybe_trap() is None, "re-entered while a trap was running"
    assert m.trap_epc == 7, "epc was overwritten from inside the handler"


def test_the_lowest_index_wins_and_wins_every_time() -> None:
    """
    Two causes in one cycle must resolve the same way always, or the machine
    is not deterministic and nothing above it can be sealed.
    """
    for _ in range(4):
        m = _armed(0b111)
        m.rx_queue = [0x41]        # cause 1
        m.timer_expired = True     # cause 0
        m._maybe_trap()
        assert m.trap_cause == m.TRAP_TIMER

    m = _armed(0b111)
    m.rx_queue = [0x41]            # only cause 1 armed
    m._maybe_trap()
    assert m.trap_cause == m.TRAP_UART_RX


def test_cause_and_pending_refuse_writes() -> None:
    m = _armed(0)
    m.trap_cause = 2
    m._periph_write(m.REG_TRAP_CAUSE, 7)
    assert m.trap_cause == 2
    m.timer_expired = True
    m._periph_write(m.REG_TRAP_PENDING, 0)
    assert m._periph_read(m.REG_TRAP_PENDING) & 1, "PENDING must mirror sources"


def test_the_timer_expires_on_a_match_not_on_a_level() -> None:
    """
    hcpu_timer.v fires on `counter == compare`. Modelling it as `>=` would make
    the interpreter re-expire forever past the deadline while the silicon fired
    once -- so a handler that is correct on one would spin on the other.
    """
    rtl = (ROOT / "rtl" / "hcpu_timer.v").read_text(encoding="utf-8")
    assert "counter == compare" in rtl
    assert ">=" not in rtl.split("expired <= 1'b1")[0].split("counter ==")[-1]

    m = _machine("        MOVI R1, 0\n" * 8 + "        HALT\n")
    m.timer_compare = 3
    while m.step() is not None:
        pass
    assert m.timer_expired
    m._periph_write(m.REG_TIMER_STATUS, 0)
    assert not m.timer_expired, "clearing must work past the deadline"


# ══════════════════════════════════════════════════════════════════
#  A whole program: preempted, handled, resumed, finished
# ══════════════════════════════════════════════════════════════════

def test_a_timer_interrupt_breaks_a_loop_that_would_not_end_by_itself() -> None:
    source = (ROOT / "rtl" / "programs" / "trap_timer.hasm").read_text(encoding="utf-8")
    m = _machine(source)
    for _ in range(500):
        if m.step() is None:
            break

    assert m._halted, "the program never finished: the trap did not return"
    g = m.regs.gpr
    assert g[8] == 1, "the handler never ran"
    assert g[9] == m.TRAP_TIMER, "the handler read the wrong cause"
    assert g[7] >= 2, "the loop did not resume after the handler"

    taken = [t.description for t in m.trace if "TRAP" in t.description]
    returned = [t.description for t in m.trace if "ERET" in t.description]
    assert len(taken) == 1, f"expected exactly one trap, got {taken}"
    assert len(returned) == 1

    # epc must point INTO the loop, not at the handler and not at the setup.
    assert g[10] == m.trap_epc
    assert source.splitlines()[0].startswith(";")
    assert not m.trap_active, "ERET did not clear the latch"


def test_without_the_handler_clearing_its_source_the_program_spins() -> None:
    """
    The behaviour a handler author has to know, pinned so it cannot change
    silently. Dropping the STORE that clears the timer status must NOT be
    quietly absorbed -- a lost interrupt is worse than a visible spin.
    """
    source = (ROOT / "rtl" / "programs" / "trap_timer.hasm").read_text(encoding="utf-8")
    broken = source.replace("        STORE R1, R5, 0xFF6", "        MOVI  R11, 0")
    assert broken != source

    m = _machine(broken)
    for _ in range(500):
        if m.step() is None:
            break
    assert not m._halted, "a handler that never clears its source must not finish"
    taken = [t for t in m.trace if "TRAP" in t.description]
    assert len(taken) > 5, "the source stayed high; it must keep re-trapping"
