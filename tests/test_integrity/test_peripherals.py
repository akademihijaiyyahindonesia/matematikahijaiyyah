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
    build = subprocess.run(
        ["iverilog", "-g2012", "-s", top, "-o", f"/tmp/{top}", *sources],
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
