"""The burn-in harness, checked before it is trusted for a day.

A run that takes 24 hours cannot be debugged by repeating it, so what can be
checked in a second is checked here: that the work the board repeats is the
work this repository defines, that the numbers it reports mean what the host
thinks they mean, and that a corrupted word really does raise the error count.

The two constants the host multiplies by -- 1024 cycles per heartbeat and a
counter shifted right 12 -- live in the program, and a silent change to either
would make every reported uptime wrong. So they are read back out of the
program rather than trusted.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from burn_in import (  # noqa: E402
    COUNTER_SHIFT,
    EXPECT,
    HEARTBEAT_CYCLES,
    OSC_HZ,
    PROGRAM,
    WRAP_S,
    expected_first_cycle,
    uptime_s,
)
from jamrah_board import GATE, gate_body  # noqa: E402

from hijaiyyah.core.master_table import MASTER_TABLE  # noqa: E402
from hijaiyyah.hisa.assembler import assemble  # noqa: E402
from hijaiyyah.hisa.machine import HISAMachine  # noqa: E402

SOURCE = PROGRAM.read_text(encoding="utf-8")


def _machine() -> HISAMachine:
    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(assemble(SOURCE, base_dir=PROGRAM.parent))
    return machine


def _run_to_cycle(machine: HISAMachine, cycle: int, cap: int = 6_000_000) -> int:
    steps = 0
    while steps < cap and machine.data_mem.get(0x200, 0) < cycle:
        machine.step()
        steps += 1
    return steps


def test_the_gate_the_board_repeats_is_the_gate_this_repo_defines() -> None:
    """Copied, not retyped -- and this is what keeps the copy honest."""
    body = gate_body(GATE.read_text(encoding="utf-8"))
    marked = SOURCE.split("; >>> jamrah_gate.hasm body begins\n")[1]
    marked = marked.split("\n; <<< jamrah_gate.hasm body ends")[0]
    assert [ln for ln in marked.splitlines() if ln.strip()] == [
        ln for ln in body if ln.strip()]


def test_the_first_cycle_prints_what_python_says_it_should() -> None:
    """28 from the letters, 3072 from the tree, 178 from the Master Table --
    three sources, none of them this program."""
    machine = _machine()
    _run_to_cycle(machine, 1)
    printed = list(machine.output)[:3]
    assert printed == [EXPECT["pulse_sum"], EXPECT["node_sum"], EXPECT["codex_sum"]]
    assert expected_first_cycle() == EXPECT
    assert EXPECT["codex_sum"] == sum(e.theta_hat + e.U + e.rho
                                      for e in MASTER_TABLE.all_entries())


def test_a_corrupted_word_raises_the_error_count() -> None:
    """The memory check, tested by breaking what it guards (R3). Without this
    the check could be counting nothing and a clean run would say so anyway."""
    machine = _machine()
    _run_to_cycle(machine, 2)
    assert machine.data_mem.get(0x201, 0) == 0
    machine.data_mem[0x213] ^= 1          # one bit, in one of the sixteen words
    _run_to_cycle(machine, 4)
    assert machine.data_mem.get(0x201, 0) >= 1


def test_a_drifting_sum_raises_the_error_count() -> None:
    """The same for the reference the gate and the codex are held against."""
    machine = _machine()
    _run_to_cycle(machine, 2)
    machine.data_mem[0x204] += 1          # the stored pulse sum, not the live one
    _run_to_cycle(machine, 4)
    assert machine.data_mem.get(0x201, 0) >= 1


def test_the_host_multiplies_by_what_the_program_divides_by() -> None:
    """Both numbers are in the program; a change to either would leave every
    uptime in the log wrong and nothing would say so."""
    assert f"ANDI  R4, R1, {HEARTBEAT_CYCLES - 1}" in SOURCE
    assert f"SHRI  R2, R2, {COUNTER_SHIFT}" in SOURCE
    assert WRAP_S == 2 ** 32 / OSC_HZ
    assert uptime_s(0, 0) == 0.0
    assert uptime_s(1, 0) == WRAP_S
    assert uptime_s(0, 1 << 20) == (1 << 32) / OSC_HZ


def test_the_program_reads_the_card_and_never_writes_it() -> None:
    """A week of writes would wear the card out and measure the wrong thing.
    hal_sd_run takes 1 to initialise and 2 to read; 3 is a write."""
    calls = re.findall(r"MOVI\s+R1,\s*(\d+)\s*\n\s*CALL\s+hal_sd_run", SOURCE)
    assert set(calls) <= {"1", "2"}, calls
    assert "3" not in calls
