"""hcpu_uart_rx as a function, held to its own bench, cycle by cycle.

The Layer 6 item the roadmap names -- the next state predicted for a named
module agrees with its bench -- begun, on the owner's choice of 28 September
2026, with rtl/hcpu_uart_rx.v and rtl/tb/tb_hcpu_uart_rx.v. What is held here:

    the function gives the RTL's next state at every cycle of the bench, and
    from reset its whole trajectory;
    it predicts the frames, data, glitch and framing error the bench checks,
    and the bench itself passes;
    every transition rule is exercised;
    the input timing it assumes is the one the simulator resolves;
    and each transition rule, broken, turns the comparison red (R3).
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
SPEC = next(m for m in rf.load()["modules"] if m["name"] == "hcpu_uart_rx")


def _module(name: str) -> dict[str, Any]:
    return next(m for m in MODEL["modules"] if m["name"] == name)


@pytest.fixture(scope="module")
def trace() -> dict[str, Any]:
    return rf.rtl_trace(SPEC)


def test_the_model_reads_back_exactly() -> None:
    assert rf.verify() == []


def test_the_page_is_drawn_from_the_model() -> None:
    assert rf.PAGE.read_text(encoding="utf-8") == rf.page(MODEL)


def test_the_function_is_the_rtl_at_every_cycle_of_its_bench() -> None:
    m = _module("hcpu_uart_rx")
    assert m["cycles"] == 15916
    assert m["one_step_mismatches"] == [] and m["open_loop_mismatches"] == []
    assert rf.check(MODEL) == []


def test_it_predicts_what_the_bench_checks_and_the_bench_passes() -> None:
    m = _module("hcpu_uart_rx")
    assert m["frames"] == [0x41, 0x00, 0xFF, 0x5A, 0x3C]
    assert m["frame_errors"] == [False, False, False, False, True]
    assert m["bench_pass"] and m["bench_said"].startswith("PASS: 5 frames")


def test_every_transition_rule_is_exercised() -> None:
    m = _module("hcpu_uart_rx")
    assert [r["id"] for r in m["rules"]] == [r["id"] for r in SPEC["rules"]]
    assert m["not_covered"] == [] and all(r["fired"] > 0 for r in m["rules"])
    glitches = next(r["fired"] for r in m["rules"] if r["id"] == "start_glitch")
    assert glitches == 2   # the bench's glitch, and the line held low by a bad stop bit


def test_the_parameters_are_the_benchs() -> None:
    m = _module("hcpu_uart_rx")
    assert m["parameters"] == {"CLK_HZ": 27_000_000, "BAUD": 115_200, "DIVISOR": 234,
                               "HALF": 117, "CNT_W": 8}


def test_the_input_timing_is_what_the_simulator_resolves(trace: dict[str, Any]) -> None:
    """Measured, not assumed: at every edge where the bench changed the line,
    the first synchroniser flop took the new value."""
    rows = trace["rows"]
    changed = [t for t in range(len(rows) - 1)
               if rows[t + 1]["rst_n"] and rows[t + 1]["rx_in"] != rows[t]["rx_in"]]
    assert len(changed) == 24
    assert all(rows[t + 1]["rx_meta"] == rows[t + 1]["rx_in"] for t in changed)
    m = _module("hcpu_uart_rx")
    assert m["input_timing"] == {"line_changes": 24, "captured_new": 24, "captured_old": 0}


# -- R3: each transition rule, broken, is red ---------------------------------------------

Step = Callable[[rf.State, int, int, dict[str, int]], tuple[rf.State, list[str]]]


def _bend(change: Callable[[rf.State, rf.State, list[str], int], None]) -> Step:
    def step(s: rf.State, rx_in: int, rst_n: int,
             p: dict[str, int]) -> tuple[rf.State, list[str]]:
        n, fired = rf.uart_rx_step(s, rx_in, rst_n, p)
        change(s, n, fired, rx_in)
        return n, fired
    return step


def _early(s: rf.State, rx_in: int, rst_n: int,
           p: dict[str, int]) -> tuple[rf.State, list[str]]:
    return rf.uart_rx_step(s, rx_in, rst_n, {**p, "HALF": p["HALF"] - 1})


def _set(n: rf.State, **kw: int) -> None:
    n.update(kw)


SABOTAGES: dict[str, Step] = {
    "the start bit sampled one clock early": _early,
    "bits shifted MSB first": _bend(lambda s, n, f, _: _set(
        n, shifter=((s["shifter"] << 1) | s["rx_sync"]) & 0xFF)
        if {"data_sample", "data_last"} & set(f) else None),
    "a glitch taken for a frame": _bend(lambda s, n, f, _: _set(
        n, state=rf.DATA, count=0, index=0) if "start_glitch" in f else None),
    "the framing error inverted": _bend(lambda s, n, f, _: _set(
        n, rx_frame_err=s["rx_sync"]) if "stop_deliver" in f else None),
    "rx_valid held past its cycle": _bend(lambda s, n, f, _: _set(
        n, rx_valid=n["rx_valid"] | s["rx_valid"])),
    "one synchroniser flop, not two": _bend(lambda s, n, f, rx: _set(n, rx_sync=rx)),
}


@pytest.mark.parametrize("name", SABOTAGES)
def test_each_broken_rule_is_red(name: str, trace: dict[str, Any]) -> None:
    assert rf.compare(SPEC, trace)["one_step_mismatches"] == []
    got = rf.compare(SPEC, trace, step=SABOTAGES[name])
    assert got["one_step_mismatches"] and got["open_loop_mismatches"], name


def test_a_prediction_the_bench_does_not_make_is_red() -> None:
    bent = json.loads(json.dumps(MODEL))
    next(m for m in bent["modules"] if m["name"] == "hcpu_uart_rx")["frames"][0] = 0x42
    assert any(b.startswith("F3") for b in rf.check(bent))


def test_another_rtl_than_the_one_held_is_red() -> None:
    bent = json.loads(json.dumps(MODEL))
    next(m for m in bent["modules"] if m["name"] == "hcpu_uart_rx")["rtl_sha256"] = "0" * 64
    assert any(b.startswith("F5") for b in rf.check(bent))


def test_a_rule_citing_no_line_of_the_rtl_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    spec["modules"][0]["rules"][0]["lines"].append(9999)
    monkeypatch.setattr(rf, "load", lambda: spec)
    with pytest.raises(LookupError, match="9999"):
        rf.build()


def test_a_pin_holds_whichever_line_ending_the_checkout_wrote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pin is taken over LF line endings, the form git holds: the same file written CRLF reads
    back to the same pin in both rtl_function and Layer 7's F5 check, while a content change is
    caught as STALE and Layer 7's byte-exact _sha stays byte-exact."""
    from hijaiyyah.nui import layer7 as l7

    pinned = _module("hcpu")["pinned_sha256"]
    for path in ("src/hijaiyyah/hisa/registers.py", "src/hijaiyyah/hisab/protocol.py"):
        lf = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
        crlf = lf.replace(b"\n", b"\r\n")
        for name, body in (("lf.py", lf), ("crlf.py", crlf)):
            (tmp_path / name).write_bytes(body)
            assert rf._file_sha(tmp_path / name) == pinned[path], (path, name)
        assert l7._sha(tmp_path / "lf.py") != l7._sha(tmp_path / "crlf.py")
        (tmp_path / "changed.py").write_bytes(lf.replace(b"class", b"klass", 1))
        assert rf._file_sha(tmp_path / "changed.py") != pinned[path]

    real_file_sha = rf._file_sha
    override: dict[Path, Path] = {}
    monkeypatch.setattr(rf, "_file_sha", lambda p: real_file_sha(override.get(p, p)))
    target = {"kind": "rtl", "module": "hcpu", "rule": "fetch_latch"}
    reg = ROOT / "src/hijaiyyah/hisa/registers.py"
    reg_lf = reg.read_bytes().replace(b"\r\n", b"\n")
    for name, body in (("reg_lf.py", reg_lf), ("reg_crlf.py", reg_lf.replace(b"\n", b"\r\n"))):
        p = tmp_path / name
        p.write_bytes(body)
        override[reg] = p
        res = l7.evaluate(target)
        assert res["decision"] == l7.PASS, (name, res["stops"])
        assert res["preconditions"]["evidence freshness"]["value"] == "current"
    bad = tmp_path / "reg_changed.py"
    bad.write_bytes(reg_lf.replace(b"class", b"klass", 1))
    override[reg] = bad
    res = l7.evaluate(target)
    assert res["decision"] == l7.STOP and l7.STALE in res["conditions"]
