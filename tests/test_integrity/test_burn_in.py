"""The burn-in harness and its baseline, checked before either is trusted.

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

import json  # noqa: E402

import pytest  # noqa: E402
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
from burn_in_report import baseline, percentile, read, spread  # noqa: E402
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


# -- the baseline ---------------------------------------------------------


def _log(tmp_path: Path, beats: list[tuple[float, float, int]]) -> Path:
    """A synthetic run: (host_s, gap, cycles) per sampled beat."""
    path = tmp_path / "run.jsonl"
    lines = [{"t": 0.0, "kind": "start"}]
    for host_s, gap, cycles in beats:
        lines.append({"t": host_s, "kind": "sample", "gap": gap, "host_s": host_s,
                      "board_s": host_s - 3.0, "heartbeats": cycles // 1024,
                      "errors": 0, "sd_fails": 0, "wraps": 0,
                      "counter_hi": 0, "sd_status": 10, "cycles": cycles})
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    path.with_suffix(".json").write_text(json.dumps({
        "started": "2026-09-20T01:35:38+00:00", "ended": "duration reached",
        "host_seconds": beats[-1][0], "board_seconds": beats[-1][0] - 3.0,
        "heartbeats": beats[-1][2] // 1024, "cycles": beats[-1][2], "errors": 0,
        "sd_read_failures": 0, "unparsed_lines": 0,
        "longest_gap_s": max(b[1] for b in beats), "longest_gap_at_s": 5.7}) + "\n")
    return path


def test_percentiles_are_nearest_rank_and_need_no_numpy() -> None:
    values = [float(i) for i in range(1, 101)]
    assert percentile(values, 50) == 50
    assert percentile(values, 95) == 95
    assert percentile(values, 100) == 100
    assert percentile([7.0], 99) == 7
    assert spread([1.0, 2.0, 3.0])["mean"] == 2


def test_the_baseline_keeps_the_host_s_view_apart_from_the_board_s(
        tmp_path: Path) -> None:
    """Tier 1's intervals piled up at 1.0 and 2.0 seconds because the host
    read with a one-second timeout, while the board was beating every 1.58.
    A baseline that reported the first as the machine's cadence would be
    describing the host."""
    rate = 650.0
    beats = [(60.0 * i, 1.0 if i % 2 else 2.0, int(60.0 * i * rate))
             for i in range(1, 21)]
    b = baseline(*read(_log(tmp_path, beats)))
    assert b["cycles_per_second"]["p50"] == pytest.approx(rate, rel=1e-6)
    assert b["board_beat_period_s"] == pytest.approx(1024 / rate, rel=1e-3)
    assert "as_the_host_saw_it" in "".join(b)
    assert b["cycle_ms"] == pytest.approx(1000 / rate, rel=1e-3)


def test_a_run_that_stalls_cannot_hide_inside_an_average(tmp_path: Path) -> None:
    """The mean of a day is a poor place to keep a stall. The longest silence
    comes from the run's own summary, over every beat, not from the samples."""
    beats = [(60.0 * i, 40.0 if i == 7 else 1.5, int(60.0 * i * 650))
             for i in range(1, 21)]
    b = baseline(*read(_log(tmp_path, beats)))
    assert b["longest_silence_s"] == 40.0
    assert b["heartbeat_interval_s_as_the_host_saw_it"]["max"] == 40.0
    assert b["heartbeat_interval_s_as_the_host_saw_it"]["p50"] == 1.5
