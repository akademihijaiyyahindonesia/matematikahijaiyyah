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
    FIELDS,
    FIRST,
    HEARTBEAT_CYCLES,
    OSC_HZ,
    PROGRAM,
    WRAP_S,
    Feed,
    Run,
    expected_first_cycle,
    uptime_s,
)
from burn_in_report import (  # noqa: E402
    baseline,
    classify_gaps,
    compare,
    percentile,
    read,
    spread,
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


# -- the baseline ---------------------------------------------------------


def _log(tmp_path: Path, beats: list[tuple[float, float, int]]) -> Path:
    """A synthetic run: (host_s, gap, cycles) per sampled beat."""
    tmp_path.mkdir(parents=True, exist_ok=True)
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


# -- the parser, which a day-long run cannot afford to get wrong ----------


def _feed(tmp_path: Path) -> Feed:
    from datetime import datetime, timezone
    run = Run(tmp_path / "parse.jsonl", datetime.now(timezone.utc), "none")
    return Feed(run, EXPECT, gap_threshold=5.0)


def _beat(values: list[int]) -> bytes:
    return b"H\n" + b"".join(f"{v}\n".encode() for v in values)


def test_the_first_cycle_and_the_beats_after_it_are_read_apart(
        tmp_path: Path) -> None:
    feed = _feed(tmp_path)
    feed.take(b"".join(f"{v}\n".encode() for v in
                       (28, 3072, 178, 18502, 21297, 1, 1)))
    assert feed.run.first["card_word"] == 0x48465331
    assert feed.run.first["init_attempts"] == 1
    feed.take(_beat([1, 0, 0, 0, 123, 10]) + _beat([2, 0, 0, 0, 456, 10]))
    assert feed.run.heartbeats == 2
    assert feed.run.errors == 0
    assert feed.run.cycles == 2 * HEARTBEAT_CYCLES


def test_a_mangled_number_is_dropped_whole_and_counted(tmp_path: Path) -> None:
    """PRINT emits characters above '9' for large values. Squeezing the digits
    out of "335544;<" would turn a known defect into a plausible number."""
    feed = _feed(tmp_path)
    feed.run.first = {"done": 1}
    feed.take(b"H\n1\n0\n0\n0\n335544;<\n10\n")
    assert feed.run.unparsed == 1
    assert feed.run.heartbeats == 0        # the group never completed
    feed.take(_beat([2, 0, 0, 0, 456, 10]))
    assert feed.run.heartbeats == 1        # and the next H starts clean


def test_a_split_arrival_is_still_one_line(tmp_path: Path) -> None:
    """The board's bytes arrive in whatever pieces the port hands over."""
    feed = _feed(tmp_path)
    feed.run.first = {"done": 1}
    for piece in (b"H\n12", b"3\n0\n", b"0\n0\n7", b"89\n10\n"):
        feed.take(piece)
    assert feed.run.heartbeats == 1
    assert feed.run.cycles == 123 * HEARTBEAT_CYCLES


def test_the_two_group_shapes_cannot_be_confused(tmp_path: Path) -> None:
    """Six fields in a heartbeat, seven in the first cycle -- and the first
    cycle has no H in front of it. That is the whole of the rule."""
    assert len(FIELDS) == 6
    assert len(FIRST) == 7
    feed = _feed(tmp_path)
    feed.take(_beat([1, 0, 0, 0, 123, 10]))
    assert feed.run.heartbeats == 1
    assert feed.run.first == {}, "a heartbeat must never be read as a first cycle"


# -- whose silence was it -------------------------------------------------


def _carrying(t: float, host_s: float, board_s: float, beats: int,
              kind: str = "sample", gap: float = 2.0) -> dict:
    """A logged beat, with the board's clock expressed the way the log does."""
    wraps, rest = divmod(board_s, WRAP_S)
    return {"t": t, "kind": kind, "gap": gap, "host_s": host_s, "board_s": board_s,
            "heartbeats": beats, "errors": 0, "sd_fails": 0, "wraps": int(wraps),
            "counter_hi": int(rest * OSC_HZ) >> COUNTER_SHIFT, "sd_status": 10,
            "cycles": beats * HEARTBEAT_CYCLES}


def test_a_host_that_stopped_reading_is_not_a_board_that_stopped() -> None:
    """Measured on the 24-hour run: 140 seconds of silence where the board had
    never stopped. Reporting that as a hang would be wrong in the one
    direction that matters."""
    lines = [_carrying(100.0, 100.0, 100.0, 60),
             _carrying(300.0, 300.0, 160.0, 96, kind="gap", gap=140.0)]
    (g,) = classify_gaps(lines)
    assert g["whose"] == "the host"
    assert g["board_advance_s"] < g["host_advance_s"] / 2


def test_a_board_that_stopped_is_named_as_the_board() -> None:
    """The other side of the same test: the beat after the gap is CURRENT and
    the count barely moved."""
    lines = [_carrying(100.0, 100.0, 100.0, 60),
             _carrying(240.0, 240.0, 240.0, 61, kind="gap", gap=140.0)]
    (g,) = classify_gaps(lines)
    assert g["whose"] == "the board"
    assert g["beats_advanced"] == 1


def test_a_stall_does_not_bend_the_work_rate(tmp_path: Path) -> None:
    """The stall and the minute after it produce a rate four times too low and
    four times too high. Neither belongs in a baseline."""
    rate, beats = 650.0, []
    for i in range(1, 11):
        beats.append((60.0 * i, 1.5, int(60.0 * i * rate)))
    path = _log(tmp_path, beats)
    lines = [json.loads(ln) for ln in path.read_text().splitlines()]
    # bend one sample's board clock away from the host's, as a stall does
    lines[5]["board_s"] -= 100.0
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    b = baseline(*read(path))
    assert b["intervals_set_aside_for_silence"] == 2
    assert b["cycles_per_second"]["min"] == pytest.approx(rate, rel=1e-6)
    assert b["cycles_per_second"]["max"] == pytest.approx(rate, rel=1e-6)


def test_a_board_that_stopped_unseen_shows_up_in_the_work(tmp_path: Path) -> None:
    """Ten silences totalling two hours leave a blind spot: nothing in the log
    would show the machine stopping and starting inside one. The work the
    board reports, against the board's own clock, is what closes it."""
    rate = 650.0
    honest = [(60.0 * i, 1.5, int(60.0 * i * rate)) for i in range(1, 11)]
    b = baseline(*read(_log(tmp_path, honest)))
    assert b["work_accounted"] == pytest.approx(1.0, abs=0.01)
    assert b["beats_emitted_by_board"] == honest[-1][2] // HEARTBEAT_CYCLES

    # the same run with one minute where the board did no work at all while
    # its clock kept running -- a stall nobody watched. The rate everywhere
    # else is untouched, so the median still says 650, and the shortfall lands
    # in the ratio.
    stalled = []
    cycles = 0
    for i in range(1, 11):
        if i != 6:
            cycles += int(60.0 * rate)
        stalled.append((60.0 * i, 1.5, cycles))
    b = baseline(*read(_log(tmp_path / "stalled", stalled)))
    assert b["cycles_per_second"]["p50"] == pytest.approx(rate, rel=1e-6)
    assert b["work_accounted"] < 0.95, b["work_accounted"]


def test_the_two_beat_counts_are_reported_apart(tmp_path: Path) -> None:
    """The board says how many beats it emitted; the host says how many it
    managed to parse. On a run with long silences these differ by thousands,
    and only the first means anything about the machine."""
    beats = [(60.0 * i, 1.5, int(60.0 * i * 650)) for i in range(1, 11)]
    path = _log(tmp_path, beats)
    summary = json.loads(path.with_suffix(".json").read_text())
    summary["heartbeats"] = 100           # the host parsed far fewer
    path.with_suffix(".json").write_text(json.dumps(summary))
    b = baseline(*read(path))
    assert b["beats_parsed_by_host"] == 100
    assert b["beats_emitted_by_board"] > 100
    # and the work must be measured against the board's count, not the host's:
    # a host that parsed a tenth of the beats did not make the machine idle.
    assert b["work_accounted"] == pytest.approx(1.0, abs=0.01)


# -- holding a run against a frozen baseline ------------------------------


def _baseline_of(tmp_path: Path, rate: float, name: str) -> dict:
    beats = [(60.0 * i, 1.5, int(60.0 * i * rate)) for i in range(1, 11)]
    return baseline(*read(_log(tmp_path / name, beats)))


def test_a_slower_run_shows_up_as_a_difference(tmp_path: Path) -> None:
    frozen = _baseline_of(tmp_path, 650.0, "frozen")
    now = _baseline_of(tmp_path, 600.0, "now")
    moved = {row["field"]: row for row in compare(now, frozen)}
    assert moved["cycles_per_second.p50"]["delta"] == pytest.approx(-50, abs=1)
    assert moved["cycles_per_second.p50"]["percent"] == pytest.approx(-7.7, abs=0.2)
    assert moved["cycle_ms"]["delta"] > 0          # slower work, longer cycle
    for field in ("work_accounted", "errors", "sd_read_failures",
                  "board_beat_period_s"):
        assert field in moved, field


def test_the_difference_view_passes_no_judgement(tmp_path: Path) -> None:
    """The bands are the owner's and cannot be drawn before a baseline exists.
    A tool that scored this would be the anomaly engine, which is priority 7."""
    frozen = _baseline_of(tmp_path, 650.0, "frozen2")
    now = _baseline_of(tmp_path, 300.0, "half")
    for row in compare(now, frozen):
        assert set(row) == {"field", "now", "frozen", "delta", "percent"}
        assert not any(k in str(row).lower()
                       for k in ("verdict", "warning", "critical", "anomaly"))
