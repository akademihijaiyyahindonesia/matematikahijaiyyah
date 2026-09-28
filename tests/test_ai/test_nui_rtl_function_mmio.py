"""hcpu_mmio as a function, held to its own bench, cycle by cycle.

The second module of the Layer 6 item, on the owner's order of 28 September
2026: rtl/hcpu_mmio.v and rtl/tb/tb_hcpu_mmio.v, with its receiver run
through the function already held to its own bench and its timer modelled
beside it. The card controller, the data RAM and the trap unit stay outside:
what they hand in is an input, never predicted. What is held here:

    every register, and every combinational output, agrees with the RTL at
    every cycle of the bench, and from reset the whole trajectory does;
    the word each bus read returns is the one the bench checks, and no RAM
    write goes out while the address is in the peripheral window;
    the rules the bench never exercises are exactly the ones the spec names;
    the input timing is the one the simulator resolves;
    and each rule, broken, turns the comparison red (R3).
"""
from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import rtl_function as rf  # noqa: E402

MODEL = json.loads(rf.MODEL.read_text(encoding="utf-8"))
SPEC = next(m for m in rf.load()["modules"] if m["name"] == "hcpu_mmio")
M = next(m for m in MODEL["modules"] if m["name"] == "hcpu_mmio")


@pytest.fixture(scope="module")
def trace() -> dict[str, Any]:
    return rf.rtl_trace(SPEC)


def test_every_register_and_output_is_the_rtls_at_every_cycle() -> None:
    assert M["cycles"] == 7758
    assert M["one_step_mismatches"] == [] and M["output_mismatches"] == []
    assert M["open_loop_mismatches"] == []
    assert [b for b in rf.check(MODEL) if "hcpu_mmio" in b] == []


def test_the_function_as_written_now_agrees_with_the_rtl(trace: dict[str, Any]) -> None:
    """Not only the committed model: the function in the code today, run
    against the trace the RTL gives today."""
    got = rf.compare(SPEC, trace)
    assert got["one_step_mismatches"] == got["output_mismatches"] == []
    assert got["open_loop_mismatches"] == [] and got["reads"] == M["reads"]


def test_each_read_returns_what_the_bench_checks() -> None:
    assert M["reads"] == [[0x010, 0xDEADBEEF], [0x010, 0xDEADBEEF], [0xFF5, 0x1234],
                          [0xFF4, 13], [0xFF4, 26], [0xFF1, 1], [0xFF0, 0x41], [0xFF1, 0],
                          [0xFF1, 5]]
    assert M["ram_writes_in_window"] == 0
    assert M["bench_pass"] and M["bench_said"].startswith("PASS: RAM, peripherals")


def test_what_the_bench_never_exercises_is_named_not_claimed() -> None:
    fired = {r["id"]: r["fired"] for r in M["rules"]}
    assert M["not_covered"] == list(SPEC["not_covered"])
    assert all(fired[r] == 0 for r in SPEC["not_covered"])
    for proven in ("decode", "rx_hold", "rx_overrun_set", "rx_read_clear", "timer_count",
                   "timer_compare_write", "timer_clear", "timer_expire", "read_rx_data",
                   "read_rx_status", "read_counter", "read_compare"):
        assert fired[proven] > 0, proven


def test_only_what_comes_from_outside_the_model_is_ever_x_or_z(
        trace: dict[str, Any]) -> None:
    unknown = {k for row in trace["rows"] for k, v in row.items() if isinstance(v, str)}
    assert unknown <= {"sd_buf_rdata", "trap_reg_rdata", "ram_rdata", "rdata"}
    assert not unknown & set(SPEC["state"])


def test_the_input_timing_is_what_the_simulator_resolves(trace: dict[str, Any]) -> None:
    assert M["input_timing"] == {"line_changes": 18, "captured_new": 18, "captured_old": 0}


def test_a_line_read_from_the_row_before_is_red(trace: dict[str, Any],
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    """The sampling first tried -- a row 7 ns after the edge -- saw two line
    changes one edge early. Reading the line from the earlier row is that
    mistake again, and it must not agree with the RTL."""
    own = rf.DRIVERS["hcpu_mmio"]["inputs"]

    def early(rows: list[dict[str, Any]], t: int) -> tuple[Any, ...]:
        inp, = own(rows, t)
        return ({**inp, "uart_rx_in": rows[t]["line"]},)

    monkeypatch.setitem(rf.DRIVERS["hcpu_mmio"], "inputs", early)
    got = rf.compare(SPEC, trace)
    assert got["one_step_mismatches"] and got["open_loop_mismatches"]


# -- R3: each rule, broken, is red ----------------------------------------------------------

Step = Callable[[rf.State, dict[str, Any], dict[str, int]], tuple[rf.State, list[str]]]


def _bend(change: Callable[[rf.State, rf.State, list[str], dict[str, Any]], None]) -> Step:
    def step(s: rf.State, inp: dict[str, Any], p: dict[str, int]) -> tuple[rf.State, list[str]]:
        n, fired = rf.mmio_step(s, inp, p)
        change(s, n, fired, inp)
        return n, fired
    return step


def _keep(n: rf.State, s: rf.State, *keys: str) -> None:
    n.update({k: s[k] for k in keys})


STEP_SABOTAGES: dict[str, Step] = {
    "a read that does not clear ready": _bend(
        lambda s, n, f, i: _keep(n, s, "rx_ready") if "rx_read_clear" in f else None),
    "an overrun dropped silently": _bend(
        lambda s, n, f, i: _keep(n, s, "rx_overrun") if "rx_overrun_set" in f else None),
    "a compare write ignored": _bend(
        lambda s, n, f, i: _keep(n, s, "u_timer.compare") if "timer_compare_write" in f
        else None),
    "a counter that stands still": _bend(lambda s, n, f, i: _keep(n, s, "u_timer.counter")),
    "the read path held except under re": _bend(
        lambda s, n, f, i: _keep(n, s, "periph_rdata") if not i["re"] else None),
}


@pytest.mark.parametrize("name", STEP_SABOTAGES)
def test_each_broken_transition_rule_is_red(name: str, trace: dict[str, Any]) -> None:
    got = rf.compare(SPEC, trace, step=STEP_SABOTAGES[name])
    assert got["one_step_mismatches"] or got["output_mismatches"], name
    assert got["open_loop_mismatches"] or got["output_mismatches"], name


def _ungated(s: rf.State, inp: dict[str, Any], p: dict[str, int]) -> dict[str, Any]:
    return {**rf.mmio_outputs(s, inp, p), "ram_we": inp["we"]}


def _unregistered(s: rf.State, inp: dict[str, Any], p: dict[str, int]) -> dict[str, Any]:
    out = rf.mmio_outputs(s, inp, p)
    return {**out, "rdata": s["periph_rdata"] if inp["re"] else inp["ram_rdata"]}


OUTPUT_SABOTAGES = {"a peripheral write reaching RAM": _ungated,
                    "a read answered in the cycle it asks": _unregistered}


@pytest.mark.parametrize("name", OUTPUT_SABOTAGES)
def test_each_broken_output_rule_is_red(name: str, trace: dict[str, Any],
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(rf.DRIVERS["hcpu_mmio"], "outputs", OUTPUT_SABOTAGES[name])
    assert rf.compare(SPEC, trace)["output_mismatches"], name


def test_a_read_the_bench_does_not_make_is_red() -> None:
    bent = json.loads(json.dumps(MODEL))
    mmio = next(m for m in bent["modules"] if m["name"] == "hcpu_mmio")
    mmio["reads"][6][1] = 0x42
    assert any(b.startswith("F3 hcpu_mmio") for b in rf.check(bent))


def test_a_coverage_claim_the_spec_does_not_make_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    next(m for m in spec["modules"] if m["name"] == "hcpu_mmio")["not_covered"].pop("read_trap")
    monkeypatch.setattr(rf, "load", lambda: spec)
    assert any(b.startswith("F4 hcpu_mmio") for b in rf.check(MODEL))
