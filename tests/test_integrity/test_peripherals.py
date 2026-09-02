"""
The two prerequisites after bitwise: a way in, and a clock.

The design could talk and not listen. That is enough to print a result and not
enough for anything to *ask* for one — without input there is nothing for an
operating system to mediate, no command to dispatch, no event to schedule
against. And without a timer a program can only respond to what it is handed;
it cannot wait, time out, or be preempted.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
needs_iverilog = pytest.mark.skipif(
    shutil.which("iverilog") is None, reason="iverilog not installed")


def _run(top: str, sources: list[str], expect: str) -> None:
    # `-I rtl` because hcpu_mmio.v includes hcpu_pkg.vh. Without it iverilog
    # fails in the preprocessor, which reads as a test failure rather than a
    # missing flag.
    build = subprocess.run(
        ["iverilog", "-g2012", "-I", "rtl", "-s", top, "-o", f"/tmp/{top}",
         *sources],
        cwd=ROOT, capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([f"/tmp/{top}"], cwd=ROOT, capture_output=True, text=True)
    assert expect in run.stdout, run.stdout


@needs_iverilog
def test_the_receiver_reads_bytes_off_a_real_bit_period() -> None:
    """
    The stimulus holds each bit for a full divisor of clocks, as a wire would,
    so the mid-bit sampling is tested rather than assumed. Three sabotages
    were induced first and all three caught: dropping the mid-bit re-check of
    the start bit, shifting MSB-first instead of LSB-first, and ignoring the
    stop bit.
    """
    _run("tb_hcpu_uart_rx",
         ["rtl/hcpu_uart_rx.v", "rtl/tb/tb_hcpu_uart_rx.v"],
         "PASS: 5 frames, glitch rejected, framing error caught")


@needs_iverilog
def test_the_timer_counts_expires_stays_up_and_clears_on_write() -> None:
    """
    A flag cleared by *reading* cannot be polled by two pieces of code: the
    first read consumes the event and the second sees nothing. Clearing on
    write makes the consumer say so.

    The stale-expiry sabotage passed the first version of this testbench,
    because it set a new compare *after* an explicit clear — checking a zero
    that was already zero. It sets one while the flag is still up now.
    """
    _run("tb_hcpu_timer",
         ["rtl/hcpu_timer.v", "rtl/tb/tb_hcpu_timer.v"],
         "PASS: counts, expires, stays up, and clears on write")


def test_the_receiver_samples_at_bit_centres_and_says_why() -> None:
    """
    Sampling on edges works in simulation with a perfect clock and fails on a
    desk. The half-period wait is the whole correctness argument and has to
    stay documented where it lives.
    """
    raw = (ROOT / "rtl" / "hcpu_uart_rx.v").read_text(encoding="utf-8")
    source = " ".join(raw.replace("//", " ").split())
    assert "SAMPLING AT BIT CENTRES" in source
    assert "works in simulation with a perfect clock and fails on a desk" in source
    assert "HALF" in raw and "rx_meta" in raw


def test_the_receiver_synchronises_the_line_before_using_it() -> None:
    """
    The line is asynchronous to this clock. Sampling it directly puts a
    metastable value into the state machine — a fault that appears once an
    hour on a desk and never in simulation, so no testbench here can catch
    its absence. The two flops are checked structurally instead.
    """
    text = (ROOT / "rtl" / "hcpu_uart_rx.v").read_text(encoding="utf-8")
    assert "{rx_meta, rx_sync} <= {rx_in, rx_meta}" in text
    body = text[text.index("case (state)"):]
    assert "rx_in" not in body, "the state machine reads the raw line"


# ══════════════════════════════════════════════════════════════════
#  Reachable: memory-mapped I/O
# ══════════════════════════════════════════════════════════════════

@needs_iverilog
def test_the_bus_routes_ram_and_peripherals_apart() -> None:
    """
    A receiver and a timer nothing can call are two modules, not two
    capabilities. Six properties, each a way MMIO goes quietly wrong.

    Four sabotages caught: ungating the RAM write-enable, returning peripheral
    data combinationally instead of registered, dropping the overrun flag, and
    never clearing `ready` on read.

    The write-gating sabotage passed the first version of this testbench,
    which wrote to a peripheral address and then read a *different* RAM
    address to prove nothing landed — proving nothing, since the write would
    have gone to the peripheral's own address in RAM. `ram_we` is watched
    directly now.
    """
    _run("tb_hcpu_mmio",
         ["rtl/hcpu_mmio.v", "rtl/hcpu_uart_rx.v", "rtl/hcpu_timer.v",
          "rtl/hcpu_dataram.v", "rtl/tb/tb_hcpu_mmio.v"],
         "PASS: RAM, peripherals, latency, hold, and overrun")


def test_peripheral_reads_have_the_same_latency_as_ram() -> None:
    """
    The RAM's read is registered. Returning a peripheral value combinationally
    would make LOAD mean something different depending on which address it
    read, and every program that mixed the two would be subtly wrong.
    """
    raw = (ROOT / "rtl" / "hcpu_mmio.v").read_text(encoding="utf-8")
    source = " ".join(raw.replace("//", " ").split())
    assert "LATENCY MATCHES THE RAM" in source
    assert "periph_sel <= re & is_periph" in raw
    assert "assign rdata = periph_sel ? periph_rdata : ram_rdata;" in raw


def test_an_unread_byte_followed_by_another_is_an_overrun_not_a_drop() -> None:
    """
    Losing a byte quietly is the failure that looks like a protocol bug for a
    week. The flag says it happened.
    """
    text = (ROOT / "rtl" / "hcpu_mmio.v").read_text(encoding="utf-8")
    assert "if (rx_ready) rx_overrun <= 1'b1;" in text


def test_the_interpreter_models_the_same_map() -> None:
    """
    Without it a LOAD from 0xFF4 reads RAM in the interpreter and the timer in
    the pipeline, and the two engines quietly disagree about what a program
    does.
    """
    from hijaiyyah.core.master_table import MASTER_TABLE
    from hijaiyyah.hisa.assembler import assemble
    from hijaiyyah.hisa.machine import HISAMachine

    machine = HISAMachine(MASTER_TABLE)
    machine.rx_queue = [0x41, 0x42]
    machine.load_program(assemble("""
        MOVI R5, 0
        LOAD R1, R5, 0xFF1
        LOAD R2, R5, 0xFF0
        LOAD R3, R5, 0xFF0
        LOAD R4, R5, 0xFF1
        HALT
    """))
    machine.run()

    assert machine.regs.gpr[1] == 1          # ready
    assert machine.regs.gpr[2] == 0x41
    assert machine.regs.gpr[3] == 0x42
    assert machine.regs.gpr[4] == 0          # drained


def test_the_counter_is_not_claimed_to_be_parity_testable() -> None:
    """
    It counts real clock cycles and the interpreter does not model the
    pipeline's timing. Reporting a counter that "agrees" between the two would
    mean one of them was lying about what it measures — so the parity suite
    covers the compare and the status words and says why it stops there.
    """
    from hijaiyyah.hisa import machine as vm

    source = (ROOT / "src" / "hijaiyyah" / "hisa" / "machine.py").read_text(
        encoding="utf-8")
    assert "The free-running" in source and "counter is not" in source
    assert hasattr(vm.HISAMachine, "PERIPH_BASE")
