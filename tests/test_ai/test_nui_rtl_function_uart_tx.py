"""hcpu_uart_tx as a function, held to the top-level bench the owner named.

The third module of the Layer 6 item, on the owner's order of 28 September
2026: rtl/hcpu_uart_tx.v, with rtl/tb/tb_hcpu_top.v as its oracle -- and only
what that bench makes the transmitter do may be claimed proven. Measured, that
is its reset and its idle: the bench runs no PRINT and no EMITS, and reads
nothing of the transmitter. What is held here:

    every register, the busy flag and the pin agree with the RTL at every cycle
    of the bench, and from reset the whole trajectory does;
    the bench passes, and the spec claims no observation it does not make;
    what the trace shows of the owner's list -- idle, start bit, data bits,
    stop bit, bit timing, busy and ready -- is counted from the RTL itself;
    the rules the bench never runs are exactly the ones the spec names;
    each covered rule, broken, turns the comparison red (R3);
    and each uncovered rule, broken, stays unseen -- which is what "not
    covered" means, and why none of them is claimed.
"""
from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import rtl_function as rf  # noqa: E402

MODEL = json.loads(rf.MODEL.read_text(encoding="utf-8"))
SPEC = next(m for m in rf.load()["modules"] if m["name"] == "hcpu_uart_tx")
M = next(m for m in MODEL["modules"] if m["name"] == "hcpu_uart_tx")
COVERED = ("reset", "idle_wait")


@pytest.fixture(scope="module")
def trace() -> dict[str, Any]:
    return rf.rtl_trace(SPEC)


def test_every_register_and_output_is_the_rtls_at_every_cycle() -> None:
    assert M["cycles"] == 233
    assert M["one_step_mismatches"] == [] and M["output_mismatches"] == []
    assert M["open_loop_mismatches"] == []
    assert [b for b in rf.check(MODEL) if "hcpu_uart_tx" in b] == []


def test_the_function_as_written_now_agrees_with_the_rtl(trace: dict[str, Any]) -> None:
    """Not only the committed model: the function in the code today, run
    against the trace the RTL gives today."""
    got = rf.compare(SPEC, trace)
    assert got["one_step_mismatches"] == got["output_mismatches"] == []
    assert got["open_loop_mismatches"] == [] and got["seen"] == M["seen"]


def test_the_parameters_are_the_benchs() -> None:
    assert M["parameters"] == {"CLKS_PER_BIT": 10, "CNT_W": 4, "CLK_HZ": 50_000_000,
                               "BAUD": 5_000_000}


def test_the_bench_passes_and_reads_nothing_of_the_transmitter() -> None:
    """The verdict is the bench's own, and no line of it looks at the pin, the
    busy flag or a register of u_uart: it declares the pin and wires it, and
    that is all."""
    assert M["bench_pass"] and M["bench_said"] == "Total: 15 PASS, 0 FAIL"
    assert SPEC["bench_expects"] == {} and M["tx_started"] == []
    bench = (ROOT / SPEC["bench"]).read_text(encoding="utf-8").splitlines()
    touching = [n for n, ln in enumerate(bench, 1) if re.search(r"uart_tx|uart_busy|u_uart", ln)]
    assert touching == [12, 40]


def test_what_the_trace_shows_of_the_owners_list_is_idle_only() -> None:
    assert list(M["seen"]) == list(SPEC["seen"])
    assert M["seen"] == {"reset": 54, "idle": 179, "start_bit": 0, "data_bits": 0,
                         "stop_bit": 0, "counter_moving": 0, "busy": 0, "ready": 233,
                         "tx_start": 0, "line_low": 0}


def test_what_the_bench_never_exercises_is_named_not_claimed() -> None:
    fired = {r["id"]: r["fired"] for r in M["rules"]}
    assert [r["id"] for r in M["rules"]] == [r["id"] for r in SPEC["rules"]]
    assert M["not_covered"] == list(SPEC["not_covered"])
    assert [r for r, n in fired.items() if n] == list(COVERED)
    assert fired["reset"] + fired["idle_wait"] == M["cycles"] - 1


def test_the_limits_of_what_is_covered_are_named_on_covered_things_only() -> None:
    assert set(SPEC["covered_limits"]) <= {*COVERED, *SPEC["outputs"]}


def test_the_input_timing_is_declared_and_not_measurable_here() -> None:
    """tx_start never changes under this bench, so which row the transmitter
    reads it from cannot be measured: the rule is stated from the RTL, and the
    count says so."""
    assert M["input_timing"] == {"line_changes": 0, "captured_new": 0, "captured_old": 0}
    assert SPEC["input_timing"]["takes"] == "old"


# -- R3: each covered rule, broken, is red --------------------------------------------------

Step = Callable[[rf.State, dict[str, Any], dict[str, int]], tuple[rf.State, list[str]]]


def _bend(change: Callable[[rf.State, rf.State, list[str], dict[str, Any]], None]) -> Step:
    def step(s: rf.State, inp: dict[str, Any], p: dict[str, int]) -> tuple[rf.State, list[str]]:
        n, fired = rf.uart_tx_step(s, inp, p)
        change(s, n, fired, inp)
        return n, fired
    return step


def _set(n: rf.State, **kw: int) -> None:
    n.update(kw)


def _start_always(s: rf.State, inp: dict[str, Any],
                  p: dict[str, int]) -> tuple[rf.State, list[str]]:
    return rf.uart_tx_step(s, {**inp, "tx_start": 1}, p)


RED: dict[str, Step] = {
    "the idle line driven low": _bend(
        lambda s, n, f, i: _set(n, tx_out=0) if "idle_wait" in f else None),
    "a reset that leaves the line low": _bend(
        lambda s, n, f, i: _set(n, tx_out=0) if "reset" in f else None),
    "a reset that leaves a byte in the shifter": _bend(
        lambda s, n, f, i: _set(n, tx_shift=0x41) if "reset" in f else None),
    "a start taken without tx_start": _start_always,
}


@pytest.mark.parametrize("name", RED)
def test_each_broken_covered_rule_is_red(name: str, trace: dict[str, Any]) -> None:
    got = rf.compare(SPEC, trace, step=RED[name])
    assert got["one_step_mismatches"] and got["open_loop_mismatches"], name


def _busy_while_idle(s: rf.State, inp: dict[str, Any], p: dict[str, int]) -> dict[str, Any]:
    return {**rf.uart_tx_outputs(s, inp, p), "tx_busy": 1}


def _pin_inverted(s: rf.State, inp: dict[str, Any], p: dict[str, int]) -> dict[str, Any]:
    return {**rf.uart_tx_outputs(s, inp, p), "uart_tx": 1 - s["tx_out"]}


@pytest.mark.parametrize("outputs", [_busy_while_idle, _pin_inverted])
def test_each_broken_output_is_red(outputs: Callable[..., dict[str, Any]],
                                   trace: dict[str, Any],
                                   monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(rf.DRIVERS["hcpu_uart_tx"], "outputs", outputs)
    assert rf.compare(SPEC, trace)["output_mismatches"]


# -- what "not covered" means: a broken uncovered rule stays unseen ---------------------------

UNSEEN: dict[str, Step] = {
    "the start bit sent high": _bend(
        lambda s, n, f, i: _set(n, tx_out=1) if {"start_count", "start_end"} & set(f) else None),
    "the data bits sent MSB first": _bend(
        lambda s, n, f, i: _set(n, tx_out=s["tx_shift"] >> (7 - s["bit_idx"]) & 1)
        if {"data_count", "data_next", "data_last"} & set(f) else None),
    "one clock short of a bit": lambda s, i, p: rf.uart_tx_step(
        s, i, {**p, "CLKS_PER_BIT": p["CLKS_PER_BIT"] - 1}),
    "the stop bit sent low": _bend(
        lambda s, n, f, i: _set(n, tx_out=0) if {"stop_count", "stop_end"} & set(f) else None),
    "a reset that leaves the state as it was": lambda s, i, p: (
        (dict(s), ["reset"]) if not i["rst_n"] else rf.uart_tx_step(s, i, p)),
    "an idle that leaves the line as it was": _bend(
        lambda s, n, f, i: _set(n, tx_out=s["tx_out"]) if "idle_wait" in f else None),
}


@pytest.mark.parametrize("name", UNSEEN)
def test_a_broken_rule_the_bench_never_runs_stays_unseen(name: str,
                                                         trace: dict[str, Any]) -> None:
    """Were one of these ever red, the bench would have begun to run it, and
    the spec's not_covered or covered_limits would be stale."""
    got = rf.compare(SPEC, trace, step=UNSEEN[name])
    assert got["one_step_mismatches"] == got["open_loop_mismatches"] == [], name


def test_busy_never_raised_while_sending_stays_unseen(trace: dict[str, Any],
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    def never_busy(s: rf.State, inp: dict[str, Any], p: dict[str, int]) -> dict[str, Any]:
        return {**rf.uart_tx_outputs(s, inp, p), "tx_busy": 0}

    monkeypatch.setitem(rf.DRIVERS["hcpu_uart_tx"], "outputs", never_busy)
    assert rf.compare(SPEC, trace)["output_mismatches"] == []


# -- the spec cannot claim more than the bench shows ------------------------------------------


def test_an_observation_the_bench_does_not_make_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    next(m for m in spec["modules"] if m["name"] == "hcpu_uart_tx")["bench_expects"] = {
        "frames": [0x41]}
    monkeypatch.setattr(rf, "load", lambda: spec)
    assert any(b.startswith("F3 hcpu_uart_tx") for b in rf.check(MODEL))


def test_a_coverage_claim_the_spec_does_not_make_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    next(m for m in spec["modules"] if m["name"] == "hcpu_uart_tx")["not_covered"].pop(
        "data_next")
    monkeypatch.setattr(rf, "load", lambda: spec)
    assert any(b.startswith("F4 hcpu_uart_tx") for b in rf.check(MODEL))


def test_input_timing_read_the_other_way_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """The declared direction is checked, not only printed: were tx_start ever
    taken from the row after, the count would have to say so."""
    bent = json.loads(json.dumps(MODEL))
    tx = next(m for m in bent["modules"] if m["name"] == "hcpu_uart_tx")
    tx["input_timing"] = {"line_changes": 2, "captured_new": 2, "captured_old": 0}
    assert any(b.startswith("F1 hcpu_uart_tx") for b in rf.check(bent))
