"""The HCPU as one function over the parts that have an oracle.

The owner's form of 29 September 2026, on the audit f590bac: one system-level
transition over a partial predictive state. The functions already held to
their own oracles -- the pipeline, the memory map with its receiver, the data
RAM, the transmitter -- are composed as they are; the codex ALU and the
multiplier are the interpreter's own handlers; the ROM, the guard, HISAB, the
trap unit, the print state machine and the card controller hand in what the
trace shows; the rest is opaque. The oracle is rtl/tb/tb_hcpu_top.v, edge by
edge. What is held here:

    the function is the RTL at every edge: one step, the outputs, the open
    loop from reset, the RAM word for word, and the bench's terminal reads;
    the run now is the committed one;
    it fires exactly what the two audits counted, and declines only what
    they name;
    each composed part is the function it names, not a copy -- broken, the
    HCPU is red;
    what has no oracle is not predicted: a wider ALU result, an op the case
    does not name, the transmitter past idle, and every opaque register;
    HISAB is an outside result, and its known discrepancy is measured, not
    quoted;
    and each check, broken, is red.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import rtl_function as rf  # noqa: E402

MODEL = json.loads(rf.MODEL.read_text(encoding="utf-8"))
SPEC = rf.load()
M = next(m for m in SPEC["modules"] if m["name"] == "hcpu")
R = next(m for m in MODEL["modules"] if m["name"] == "hcpu")


@pytest.fixture(scope="module")
def runs() -> list[dict[str, Any]]:
    return rf.hcpu_runs(M)


@pytest.fixture(scope="module")
def x() -> dict[str, Any]:
    return rf.hcpu_context()


def _with(result: dict[str, Any]) -> dict[str, Any]:
    return {**MODEL, "modules": [({**m, **result} if m["name"] == "hcpu" else m)
                                 for m in MODEL["modules"]]}


def _hcpu(model: dict[str, Any]) -> list[str]:
    return [b for b in rf.check(model) if " hcpu" in b.split(":")[0]]


def test_the_function_is_the_rtl_at_every_edge() -> None:
    assert (R["steps"], R["cycles"], R["outputs_compared"]) == (231, 232, 57)
    assert R["sampling"] == {"compared": 231, "mismatched": {}}
    assert R["one_step_mismatches"] == R["output_mismatches"] == R["open_loop_mismatches"] == []
    assert R["open_loop_reached"] == 231 and R["not_covered_steps"] == {}
    assert R["not_covered_outputs"] == {"ctrl_halted_stall": 11}
    assert R["unpredicted"] == {"stack_rd": 10} and R["operands_moved"] == 0
    assert R["ram"]["mismatches"] == [] and R["ram"]["checked"] == 115
    assert R["ram"]["final"] == {"function": 2, "rtl": 2, "differ": []}
    assert len(R["terminal"]) == 32 and R["terminal_mismatches"] == []
    assert R["bench_pass"] and _hcpu(MODEL) == []


def test_the_run_now_is_the_committed_one(runs: list[dict[str, Any]]) -> None:
    got = json.loads(json.dumps(rf.hcpu_compare(M, runs)))
    assert {k: R[k] for k in got} == got
    assert rf._hcpu_trace_sha(runs) == R["trace_sha256"]


def test_it_fires_exactly_what_the_two_audits_counted() -> None:
    counted = {t["id"]: t["fired"] for key in ("pipeline_audit", "hcpu_audit")
               for t in MODEL[key]["transitions"]}
    assert R["rules_fired"] == {k: counted[k] for k in R["rules_fired"]}
    assert (len(R["rules"]), sum(1 for r in R["rules"] if r["fired"])) == (149, 71)
    named = set(SPEC["pipeline_audit"]["not_covered"]) | set(rf.hcpu_declared(SPEC["hcpu_audit"]))
    assert set(R["not_covered"]) == named & set(R["rules_fired"])
    assert {r["id"].split(".")[0] for r in R["rules"] if "." in r["id"]} == set(M["composed"])


def test_the_alu_reads_its_ops_and_outputs_from_the_rtl() -> None:
    got = rf._calu_ops(ROOT)
    assert got["ops"] == {0: "HCADD", 1: "HNRM2", 2: "HDIST", 3: "CGET", 4: "CSET", 5: "CMOD4"}
    assert got["drives"] == {"HCADD": "vec", "HNRM2": "scl", "HDIST": "scl", "CSET": "vec",
                             "CMOD4": "scl", "CGET": "scl"}
    alu = (ROOT / "rtl/hcpu_codex_alu.v").read_text(encoding="utf-8").splitlines()
    u = M["units"]["calu"]
    for op, want in (("HCADD", "[7:0] add_result"), ("HNRM2", "[15:0] norm2_sum"),
                     ("HDIST", "[15:0] dist2_sum")):
        assert want in alu[u["width_lines"][op] - 1]
        assert u["width"][op] == int(want[1:].split(":")[0]) + 1
    assert all("12'd17" in alu[n - 1] for n in u["indexed_lines"])
    decode = (ROOT / "rtl/hcpu_decode.v").read_text(encoding="utf-8").splitlines()
    assert "OP_CSET) ? dst" in decode[153 - 1]


def test_a_result_wider_than_the_rtl_is_not_covered(x: dict[str, Any]) -> None:
    big = sum(200 << (8 * i) for i in range(18))
    with pytest.raises(rf.NotCovered, match=r"calu\.width"):
        rf.codex_alu(0, 0, big, big, 0, x["calu"])
    with pytest.raises(rf.NotCovered, match=r"calu\.width"):
        rf.codex_alu(1, 0, big, 0, 0, x["calu"])
    assert rf.codex_alu(0, 0, 1, 2, 0, x["calu"]) == (3, 0)


def test_an_op_the_case_does_not_name_is_not_covered(x: dict[str, Any]) -> None:
    for op in (6, 7):
        with pytest.raises(rf.NotCovered, match=r"calu\.default"):
            rf.codex_alu(op, 0, 0, 0, 0, x["calu"])


def test_the_transmitter_past_idle_is_not_covered(runs: list[dict[str, Any]],
                                                  x: dict[str, Any]) -> None:
    rows = runs[0]["rows"]
    t = next(i for i, r in enumerate(rows) if r["rst_n"] == 1 and rows[i + 1]["rst_n"] == 1)
    inp = {**rf._hcpu_inputs(rows[t], rows[t + 1], x), "tx_start": 1}
    with pytest.raises(rf.NotCovered, match=r"uart_tx\.idle_start"):
        rf.hcpu_step(rf._hcpu_row_state(rows[t], x), inp, x)


def test_nothing_opaque_is_predicted(x: dict[str, Any]) -> None:
    """The predictive state is four parts, each exactly the state its own
    function declares -- a register is named by its file, so nothing of the
    trap unit, the print state machine or the card controller can be among
    them -- and the pipeline's holds no ra_stack."""
    s = rf.hcpu_reset(x)
    mods = {m["name"]: m for m in SPEC["modules"]}
    assert set(s) == {"pipe", "mmio", "ram", "tx"}
    assert list(s["mmio"]) == mods["hcpu_mmio"]["state"]
    assert list(s["tx"]) == mods["hcpu_uart_tx"]["state"]
    assert set(s["ram"]) == {"mem", "rdata"}
    bundles = {k for names in mods["pipeline"]["state"].values() for k in names}
    companion = {"halted", "flags", "stack", "stack_rd"} | {k for k in s["pipe"]
                                                            if k[:3] == "gpr" or k[:4] == "hreg"}
    assert set(s["pipe"]) == bundles | companion
    assert not any("ra_stack" in k for k in s["pipe"])


def test_the_opaque_counts_are_the_audits() -> None:
    subs = {s["id"]: s for s in SPEC["hcpu_audit"]["subsystems"]}
    audit = MODEL["hcpu_audit"]["state"]
    scalars = [n for n in subs["print"]["files"]["rtl/hcpu_top.v"] if not n.endswith("[]")]
    assert len(scalars) == 9 and M["opaque"]["mesin keadaan cetak"].startswith("sembilan")
    assert len(subs["trap"]["files"]["rtl/hcpu_trap.v"]) == 7
    assert len(subs["sdio"]["files"]["rtl/hcpu_sdio.v"]) == 41 and len(audit["sdio"]["x"]) == 17
    names = subs["guard"]["not_elaborated"]["names"]["rtl/hcpu_guard.v"]
    assert len(names) == 7


def test_hisab_is_an_outside_result(monkeypatch: pytest.MonkeyPatch,
                                    runs: list[dict[str, Any]], x: dict[str, Any]) -> None:
    """The function never asks the Python serializer: with it broken, every
    step and every output still runs."""
    def refuse(*a: Any, **k: Any) -> Any:
        raise AssertionError("the serializer was asked")

    for name in ("_nibble_pack", "_compute_guard_status", "serialize_letter"):
        monkeypatch.setattr(rf, name, refuse)
    rows = runs[0]["rows"]
    for t in range(len(rows) - 1):
        try:
            rf.hcpu_step(rf._hcpu_row_state(rows[t], x), rf._hcpu_inputs(rows[t], rows[t + 1], x),
                         x)
        except rf.NotCovered:
            pytest.fail(f"edge {t + 1} stopped")


def test_the_hisab_discrepancy_is_measured_not_quoted() -> None:
    known = M["known_discrepancy"]["hisab"]
    assert R["hisab_discrepancy"] == known["measured"] == {"edges": 13, "consumed": 0,
                                                             "programs": [5, 10]}
    top = (ROOT / "rtl/hcpu_hisab.v").read_text(encoding="utf-8").splitlines()
    assert "{2'b00, t2, t1, g4, g3, g2, g1}" in top[76 - 1]
    assert "is_kaf" in top[72 - 1] and "is_kaf" in top[74 - 1]


# -- R3: each composed part, and each check, broken, is red ---------------------------------


def test_the_memory_map_is_the_composed_function(monkeypatch: pytest.MonkeyPatch,
                                                 runs: list[dict[str, Any]]) -> None:
    real = rf.mmio_step

    def slow(s: Any, inp: Any, p: Any) -> Any:
        n, fired = real(s, inp, p)
        n["u_timer.counter"] = s["u_timer.counter"]
        return n, fired

    monkeypatch.setattr(rf, "mmio_step", slow)
    got = rf.hcpu_compare(M, runs)
    assert got["one_step_mismatches"] and got["open_loop_mismatches"]
    assert any(b.startswith(("F1 hcpu", "F2 hcpu")) for b in _hcpu(_with(got)))


def test_the_alu_is_the_interpreters_handler(monkeypatch: pytest.MonkeyPatch,
                                             runs: list[dict[str, Any]]) -> None:
    real = rf._SCRATCH._execute

    def off_by_one(iw: Any) -> Any:
        out = real(iw)
        if iw.opcode == int(rf.OpCode.HNRM2):
            rf._SCRATCH.regs.gpr[3] += 1
        return out

    monkeypatch.setattr(rf._SCRATCH, "_execute", off_by_one)
    got = rf.hcpu_compare(M, runs)
    assert got["output_mismatches"] and got["one_step_mismatches"]


def test_the_ram_is_the_composed_function(monkeypatch: pytest.MonkeyPatch,
                                          runs: list[dict[str, Any]]) -> None:
    real = rf.dataram_step

    def wrong(s: Any, inp: Any, p: Any) -> Any:
        return real(s, {**inp, "wdata": inp["wdata"] ^ 1}, p)

    monkeypatch.setattr(rf, "dataram_step", wrong)
    got = rf.hcpu_compare(M, runs)
    assert got["ram"]["final"]["differ"] == [0, 10]
    assert any(b.startswith("F2 hcpu") for b in _hcpu(_with(got)))


def test_the_transmitter_is_the_composed_function(monkeypatch: pytest.MonkeyPatch,
                                                  runs: list[dict[str, Any]]) -> None:
    monkeypatch.setattr(rf, "uart_tx_outputs",
                        lambda s, inp, p: {"tx_busy": 1, "uart_tx": s["tx_out"]})
    got = rf.hcpu_compare(M, runs)
    assert got["output_mismatches"]


def test_a_rule_the_audit_does_not_cover_stops_the_step(monkeypatch: pytest.MonkeyPatch,
                                                        runs: list[dict[str, Any]]) -> None:
    spec = rf.load()
    spec["hcpu_audit"]["not_covered"]["dataram.write"] = "sabotage"
    monkeypatch.setattr(rf, "load", lambda: spec)
    got = rf.hcpu_compare(M, runs)
    assert "dataram.write" in got["not_covered_steps"]


def test_a_count_the_audits_do_not_hold_is_red() -> None:
    bent = {**R, "rules_fired": {**R["rules_fired"], "calu.cget": 8}}
    assert any(b.startswith("F4 hcpu") for b in _hcpu(_with(bent)))


def test_a_terminal_read_that_differs_is_red() -> None:
    first = {**R["terminal"][0], "function": -1}
    bent = {**R, "terminal_mismatches": [first]}
    assert any(b.startswith("F3 hcpu") for b in _hcpu(_with(bent)))


def test_a_hisab_discrepancy_the_spec_does_not_record_is_red() -> None:
    bent = {**R, "hisab_discrepancy": {**R["hisab_discrepancy"], "edges": 12}}
    assert any(b.startswith("F3 hcpu") for b in _hcpu(_with(bent)))


def test_operands_that_move_with_the_alu_are_red() -> None:
    assert any(b.startswith("F1 hcpu") for b in _hcpu(_with({**R, "operands_moved": 1})))


def test_a_sampling_the_trace_does_not_hold_is_red(runs: list[dict[str, Any]]) -> None:
    shifted = [{**runs[0], "active": runs[0]["rows"][1:] + runs[0]["rows"][-1:]}]
    got = rf.hcpu_compare(M, shifted)
    assert got["sampling"]["mismatched"]
    assert any(b.startswith("F1 hcpu") for b in _hcpu(_with(got)))
