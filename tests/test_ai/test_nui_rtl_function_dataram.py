"""hcpu_dataram as a function, held to tb_parity.v over the Lapis 4 corpus.

The fourth module of the Layer 6 item, on the owner's order of 28 September
2026. There is no bench of the data RAM's own, and none is made: the owner
named rtl/tb/tb_parity.v over the Lapis 4 corpus its oracle -- the same
hcpu_top.u_dataram path that becomes BSRAM on the board. The harness, the
corpus and the frozen parity model are read, never changed. What is held here:

    at every edge of every run, the function gives the RTL's rdata and the
    word at the address, from the RTL's own state and from reset alike, and
    at the end of each run its whole memory is the RTL's;
    what the harness observes -- the write side -- is exactly what the
    function takes in, and the frozen Lapis 4 verdicts are quoted, not
    re-judged;
    the rule the corpus never runs is named, not claimed;
    sram_mock.py is a model of another device, and where it agrees and
    differs is shown, not assumed;
    each covered rule, broken, turns the comparison red (R3), and the
    uncovered one, broken, stays unseen.
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

from hijaiyyah.nui import parity_model as pm  # noqa: E402
from hijaiyyah.nui import rtl_function as rf  # noqa: E402
from hijaiyyah.nui.sram_mock import TwinPortSRAM  # noqa: E402

MODEL = json.loads(rf.MODEL.read_text(encoding="utf-8"))
SPEC = next(m for m in rf.load()["modules"] if m["name"] == "hcpu_dataram")
M = next(m for m in MODEL["modules"] if m["name"] == "hcpu_dataram")
COVERED = ("write", "read", "hold", "initial_zero")


@pytest.fixture(scope="module")
def runs() -> list[dict[str, Any]]:
    return rf.dataram_runs(SPEC)


def test_every_edge_of_every_run_is_the_rtls() -> None:
    assert (M["runs"], M["cycles"], len(M["ram_programs"])) == (107, 826078, 22)
    assert M["one_step_mismatches"] == M["open_loop_mismatches"] == []
    assert M["output_mismatches"] == []
    assert [b for b in rf.check(MODEL) if "hcpu_dataram" in b] == []


def test_the_function_as_written_now_agrees_with_the_rtl(runs: list[dict[str, Any]]) -> None:
    """Not only the committed model: the function in the code today, run
    against every run the harness gives today."""
    got = rf.dataram_compare(SPEC, runs)
    assert got["one_step_mismatches"] == got["open_loop_mismatches"] == []
    assert got["output_mismatches"] == got["harness_trace_mismatches"] == []
    assert got["rules_fired"] == M["rules_fired"]


def test_the_oracle_is_the_lapis4_corpus_read_not_copied(runs: list[dict[str, Any]]) -> None:
    assert [r["program"] for r in runs] == [p.name for p in pm.corpus()]
    assert M["bench_pass"] and M["bench_said"].startswith("107 of 107 runs")
    assert SPEC["bench"] == "rtl/tb/tb_parity.v" and SPEC["instance"] == "u_dut.u_dataram"


def test_what_the_harness_observes_is_what_the_function_takes() -> None:
    fired = {r["id"]: r["fired"] for r in M["rules"]}
    assert M["harness_trace_mismatches"] == []
    assert M["harness_ram_writes"] == fired["write"] == 26580


def test_the_frozen_lapis4_verdicts_are_quoted_not_rejudged() -> None:
    frozen = json.loads(pm.MODEL.read_text(encoding="utf-8"))
    for name, verdict in M["lapis4"].items():
        assert verdict["status"] == frozen["programs"][name]["status"], name
    ram = [n for n, v in M["lapis4"].items() if v["first_divergence"] == "RAM"]
    assert ram == SPEC["bench_expects"]["lapis4_ram_divergences"] == [
        "stop-probe:halt-then-store"]
    parity_page = (ROOT / "NUI" / "PARITY.md").read_text(encoding="utf-8")
    assert "the RTL then commits RAM[0x100]=5" in parity_page


def test_the_board_rows_are_the_p3_column() -> None:
    frozen = json.loads(pm.MODEL.read_text(encoding="utf-8"))["board_corpus"]["opcodes"]
    for op in ("LOAD", "STORE"):
        assert M["board"][op] == {k: frozen[op][k] for k in M["board"][op]}
        assert M["board"][op]["board"] == "PARITY" and M["board"][op]["mismatch"] == 0


def test_what_the_oracle_never_exercises_is_named_not_claimed() -> None:
    fired = {r["id"]: r["fired"] for r in M["rules"]}
    assert M["not_covered"] == list(SPEC["not_covered"]) == ["read_first"]
    assert all(fired[r] > 0 for r in COVERED) and fired["read_first"] == 0


def test_one_port_one_address() -> None:
    """A read and a write in the same edge are always the same word: the RTL
    has one addr. A rule for a read beside a write elsewhere would be
    invented, and none is written."""
    rtl = (ROOT / SPEC["rtl"]).read_text(encoding="utf-8")
    assert len(re.findall(r"^\s*input\s+wire\s+\[[^\]]+\]\s+addr\b", rtl, re.M)) == 1
    assert {r["id"] for r in SPEC["rules"]} == {*COVERED, "read_first"}


def test_the_initial_zero_is_a_simulation_claim() -> None:
    rtl = (ROOT / SPEC["rtl"]).read_text(encoding="utf-8").splitlines()
    lines = next(r["lines"] for r in SPEC["rules"] if r["id"] == "initial_zero")
    assert "translate_off" in rtl[lines[0] - 1] and "translate_on" in rtl[lines[-1] - 1]
    assert set(SPEC["covered_limits"]) == {"initial_zero", "rdata"}


def test_the_input_timing_is_measured() -> None:
    timing = M["input_timing"]
    assert timing["captured_old"] == timing["line_changes"] > 0 == timing["captured_new"]
    assert SPEC["input_timing"]["takes"] == "old"


def test_sram_mock_agrees_on_latency_and_differs_on_read_during_write() -> None:
    """The software model is another device. Where it and the RAM function
    agree -- a written word read back one edge after its address -- and
    where they do not -- a read and a write in one edge -- is run, not
    assumed; neither makes it this module's oracle."""
    mock = TwinPortSRAM(depth=16)
    s = rf.dataram_reset()
    for addr, word in ((3, 0xAB), (5, 0x11)):
        mock.tick(csb0=0, web0=0, addr0=addr, din0=word)
        s, _ = rf.dataram_step(s, {"re": 0, "we": 1, "addr": addr, "wdata": word}, {})
    mock.tick(csb0=0, web0=1, addr0=3)
    s, _ = rf.dataram_step(s, {"re": 1, "we": 0, "addr": 3, "wdata": 0}, {})
    assert mock.dout0 == s["rdata"] == 0xAB

    # One edge that reads and writes word 5. The RAM function returns the old
    # word, 0x11 (read-first, lines 40-42 -- never run by the oracle); the
    # mock's port 0 cannot read while it writes, and dout0 keeps 0xAB.
    mock.tick(csb0=0, web0=0, addr0=5, din0=0xCD)
    s, fired = rf.dataram_step(s, {"re": 1, "we": 1, "addr": 5, "wdata": 0xCD}, {})
    assert fired == ["write", "read_first"] and s["rdata"] == 0x11 != mock.dout0 == 0xAB
    assert mock.mem[5] == s["mem"][5] == 0xCD
    assert "sram_mock.py" in SPEC["levels"]["software_model"]
    assert "sram_mock" not in SPEC["bench"] + SPEC["oracle"]


# -- R3: each covered rule, broken, is red ---------------------------------------------------

Step = Callable[[dict[str, Any], dict[str, Any], dict[str, int]],
                tuple[dict[str, Any], list[str]]]


def _bend(change: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], None]) -> Step:
    def step(s: dict[str, Any], inp: dict[str, Any],
             p: dict[str, int]) -> tuple[dict[str, Any], list[str]]:
        n, fired = rf.dataram_step(s, inp, p)
        change(s, n, inp)
        return n, fired
    return step


def _set(n: dict[str, Any], **kw: Any) -> None:
    n.update(kw)


def _dropped(s: dict[str, Any], inp: dict[str, Any],
             p: dict[str, int]) -> tuple[dict[str, Any], list[str]]:
    return rf.dataram_step(s, {**inp, "we": 0}, p)


def _off_by_one(s: dict[str, Any], inp: dict[str, Any],
                p: dict[str, int]) -> tuple[dict[str, Any], list[str]]:
    if inp["we"] == 1 and inp["re"] != 1:
        return rf.dataram_step(s, {**inp, "addr": inp["addr"] + 1}, p)
    return rf.dataram_step(s, inp, p)


RED: dict[str, Step] = {
    "a write dropped": _dropped,
    "a write landing one word off": _off_by_one,
    "a read that does not latch": _bend(
        lambda s, n, i: _set(n, rdata=s["rdata"]) if i["re"] == 1 else None),
    "a hold that follows the address": _bend(
        lambda s, n, i: _set(n, rdata=s["mem"].get(i["addr"], 0)) if i["re"] != 1 else None),
    "memory that does not start at zero": _bend(
        lambda s, n, i: _set(n, rdata=0xFFFFFFFF)
        if i["re"] == 1 and i["addr"] not in s["mem"] else None),
}


@pytest.mark.parametrize("name", RED)
def test_each_broken_covered_rule_is_red(name: str, runs: list[dict[str, Any]]) -> None:
    got = rf.dataram_compare(SPEC, runs, step=RED[name])
    assert got["open_loop_mismatches"], name
    if name != "memory that does not start at zero":     # only the open loop knows history
        assert got["one_step_mismatches"], name


def test_a_port_that_is_not_the_register_is_red(runs: list[dict[str, Any]]) -> None:
    got = rf.dataram_compare(SPEC, runs, outputs=lambda s, i, p: {"rdata": 0})
    assert got["output_mismatches"]


# -- what "not covered" means: the uncovered rule, broken, stays unseen ----------------------


def test_write_first_instead_of_read_first_stays_unseen(runs: list[dict[str, Any]]) -> None:
    """Were this ever red, the corpus would have begun to read and write one
    word in the same edge, and not_covered would be stale."""
    write_first = _bend(lambda s, n, i: _set(n, rdata=i["wdata"])
                        if i["re"] == 1 and i["we"] == 1 else None)
    got = rf.dataram_compare(SPEC, runs, step=write_first)
    assert got["one_step_mismatches"] == got["open_loop_mismatches"] == []


# -- the spec cannot claim more than the oracle shows ------------------------------------------


def test_a_coverage_claim_the_spec_does_not_make_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    next(m for m in spec["modules"] if m["name"] == "hcpu_dataram")["not_covered"].pop(
        "read_first")
    monkeypatch.setattr(rf, "load", lambda: spec)
    assert any(b.startswith("F4 hcpu_dataram") for b in rf.check(MODEL))


def test_a_lapis4_divergence_the_spec_hides_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    next(m for m in spec["modules"] if m["name"] == "hcpu_dataram")["bench_expects"][
        "lapis4_ram_divergences"] = []
    monkeypatch.setattr(rf, "load", lambda: spec)
    assert any(b.startswith("F3 hcpu_dataram") for b in rf.check(MODEL))


def test_a_harness_trace_that_disagrees_is_red() -> None:
    bent = json.loads(json.dumps(MODEL))
    next(m for m in bent["modules"] if m["name"] == "hcpu_dataram")[
        "harness_trace_mismatches"] = ["parity:store_then_load"]
    assert any(b.startswith("F3 hcpu_dataram") for b in rf.check(bent))
