"""
Memory protection: the fifth OS prerequisite, and the fifth of six.

Supervisor mode drew a boundary around the PERIPHERAL WINDOW. That stops a
user program touching the timer or the trap unit, and stops nothing else --
all 4 KB of data RAM stayed open to it, including whatever the supervisor was
keeping there. A kernel cannot hold its own tables in memory a user program
can read.

base and limit close that. The window is [base, limit), the check sits beside
the privilege check in Execute because that is the last stage that knows the
PC, and the access is SUPPRESSED rather than performed and undone.
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


def _user(base: int = 0x100, limit: int = 0x200) -> HISAMachine:
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble("        MOVI R1, 0\n")
    m.mem_base, m.mem_limit = base, limit
    m.mode = m.MODE_USER
    return m


def test_the_constants_match_the_package() -> None:
    m = HISAMachine(MASTER_TABLE)
    for attr, define in (("REG_MEM_BASE", "REG_MEM_BASE"),
                         ("REG_MEM_LIMIT", "REG_MEM_LIMIT"),
                         ("TRAP_MEM", "TRAP_MEM"),
                         ("TRAP_CAUSES", "TRAP_CAUSES")):
        hit = re.search(rf"^`define\s+{define}\s+(?:\d*'[hd])?([0-9A-Fa-f]+)",
                        PKG, re.M)
        assert hit, define
        base = 16 if "'h" in hit.group(0) else 10
        assert getattr(m, attr) == int(hit.group(1), base), attr


def test_the_limit_starts_wide_open() -> None:
    """
    A machine that never sets the window must behave exactly as it did before
    protection existed. Reset leaves base at 0 and limit at the top.
    """
    m = HISAMachine(MASTER_TABLE)
    assert m.mem_base == 0 and m.mem_limit == 0xFFF
    m.mem_base, m.mem_limit = 5, 9
    m.reset()
    assert m.mem_base == 0 and m.mem_limit == 0xFFF
    assert "mem_limit <= {`DATA_ADDR_W{1'b1}};" in (
        ROOT / "rtl" / "hcpu_mmio.v").read_text(encoding="utf-8")


@pytest.mark.parametrize("addr", [0x100, 0x101, 0x1FF])
def test_inside_the_window_is_allowed(addr: int) -> None:
    m = _user()
    m._mem_write(addr, 0xABC)
    assert not m._mem_fault
    assert m._mem_read(addr) == 0xABC
    assert not m._mem_fault


@pytest.mark.parametrize("addr", [0x000, 0x0FF, 0x200, 0x800])
def test_outside_the_window_faults_and_is_suppressed(addr: int) -> None:
    """Suppressed, not performed and undone: nothing is written at all."""
    m = _user()
    m._mem_write(addr, 0xDEAD)
    assert m._mem_fault
    assert addr not in m.data_mem, "the write landed anyway"

    # The read must be suppressed, and proving that needs something THERE to
    # read. A first version checked the value was 0 at an address nothing had
    # written, so it passed whether the read was refused or performed --
    # checking a zero that was already zero.
    m.mode = m.MODE_SUPER
    m._mem_write(addr, 0x5A5A)
    m.mode = m.MODE_USER
    m._mem_fault = False
    assert m._mem_read(addr) == 0, "the refused read returned the stored value"
    assert m._mem_fault


def test_supervisor_is_not_bounded() -> None:
    """The window is the user's, not the machine's."""
    m = _user()
    m.mode = m.MODE_SUPER
    for addr in (0x000, 0x800):
        m._mem_write(addr, 7)
        assert not m._mem_fault
        assert m.data_mem[addr] == 7


def test_a_memory_fault_fires_with_every_enable_bit_clear() -> None:
    """
    It is an EXCEPTION, like the privilege fault and unlike the timer. A
    boundary software can switch off is not a boundary.
    """
    m = _user()
    m.trap_enable = 0
    m.trap_vector = 2
    m._mem_write(0x000, 1)
    assert m._mem_fault
    assert m._maybe_trap() is not None
    assert m.trap_cause == m.TRAP_MEM

    assert "(1 << `TRAP_PRIV) | (1 << `TRAP_MEM)" in TRAP
    assert m.NONMASKABLE == (1 << m.TRAP_PRIV) | (1 << m.TRAP_MEM)


def test_the_fault_names_its_own_instruction() -> None:
    """Exceptions save the faulting PC; interrupts save the next one."""
    m = _user()
    m.trap_vector = 2
    m.regs.pc = 7
    m._mem_write(0x000, 1)
    m._maybe_trap()
    assert m.trap_epc == 6, "the exception did not name its instruction"

    assert "(which >= `TRAP_PRIV) ? pc_fault : pc_now" in TRAP
    assert "mem_base" in EXECUTE and "mem_limit" in EXECUTE
    assert "output wire                    mem_fault," in EXECUTE


def test_the_window_registers_are_supervisor_only() -> None:
    """
    They sit in the peripheral window, which is why supervisor mode had to be
    drawn there first: a user program that could move its own boundary has
    none. Checked through the memory path, not the register helper.
    """
    m = _user()
    m._mem_write(0xFFE, 0)          # REG_MEM_BASE
    m._mem_write(0xFFF, 0xFFF)      # REG_MEM_LIMIT
    assert m._priv_fault
    assert (m.mem_base, m.mem_limit) == (0x100, 0x200), "the window moved"


def test_peripheral_addresses_report_privilege_not_bounds() -> None:
    """
    A peripheral address is already refused by the privilege check, so it must
    not be reported twice. Two causes for one act would let a handler dispatch
    on the wrong one.
    """
    m = _user()
    m._mem_write(0xFF4, 1)
    assert m._priv_fault and not m._mem_fault
    assert "&& !touches_window" in EXECUTE


def test_a_user_program_is_held_inside_its_window() -> None:
    source = (ROOT / "rtl" / "programs" / "mem_protect.hasm").read_text(encoding="utf-8")
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(source)
    for _ in range(300):
        if m.step() is None:
            break

    assert m._halted, "the program never finished"
    g = m.regs.gpr
    assert g[7] == 42 and m.data_mem.get(0x150) == 42   # inside: written
    assert g[8] == 0 and 0x050 not in m.data_mem        # outside: refused
    assert g[9] == 1, "the handler never ran"
    assert g[10] == m.TRAP_MEM

    traps = [t.description for t in m.trace if "TRAP" in t.description]
    assert len(traps) == 1 and "TRAP 4" in traps[0]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_whole_cpu_elaborates_with_the_window_wired_in() -> None:
    files = sorted(str(p) for p in (ROOT / "rtl").glob("hcpu_*.v"))
    res = subprocess.run(["iverilog", "-g2012", "-I", "rtl", "-o", "/tmp/hcpu_mem",
                          *files], cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
