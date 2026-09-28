"""The pipeline as one function over its four bundles, held to tb_hcpu_top.v.

The owner's form of 28 September 2026, after the audit bd8158c was accepted:
one synchronous transition over the four stage bundles the audit mapped,
rst_n and imem_data as inputs, every other subsystem's result taken from the
trace rather than predicted again; compared at every edge, then at the bench's
own reads. Only the audit's covered transitions have behaviour. What is held
here:

    at every edge, from the RTL's own state, from reset, and at every output,
    the function is the RTL's;
    it fires exactly what the audit counted;
    the bench's reads are the constants the bench itself states;
    wherever a transition is uncovered it stops with NotCovered, and the row
    after the last HALT is a terminal snapshot, not a transition;
    no interpreter stands in for the oracle;
    and each covered rule, broken, is red.
"""
from __future__ import annotations

import inspect
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
SPEC = next(m for m in rf.load()["modules"] if m["name"] == "pipeline")
M = next(m for m in MODEL["modules"] if m["name"] == "pipeline")
C = rf.pipeline_context()


@pytest.fixture(scope="module")
def runs() -> list[dict[str, Any]]:
    return rf.pipeline_runs(SPEC)


def _pipeline(bad: list[str]) -> list[str]:
    return [b for b in bad if b.split()[1:2] == ["pipeline:"]]


def test_every_edge_every_output_and_the_open_loop_are_the_rtls() -> None:
    assert (M["cycles"], M["steps"]) == (232, 231)
    assert M["one_step_mismatches"] == M["output_mismatches"] == []
    assert M["open_loop_mismatches"] == [] and M["open_loop_reached"] == 231
    assert _pipeline(rf.check(MODEL)) == []


def test_the_function_as_written_now_agrees_with_the_rtl(runs: list[dict[str, Any]]) -> None:
    got = rf.pipeline_compare(SPEC, runs)
    assert got["one_step_mismatches"] == got["output_mismatches"] == []
    assert got["open_loop_mismatches"] == [] and got["terminal"] == M["terminal"]


def test_it_fires_exactly_what_the_audit_counted() -> None:
    counted = {t["id"]: t["fired"] for t in MODEL["pipeline_audit"]["transitions"]}
    assert M["rules_fired"] == counted
    assert M["not_covered"] == MODEL["pipeline_audit"]["not_covered"]
    assert sum(1 for v in M["rules_fired"].values() if v) == 45


def test_the_bench_reads_are_the_constants_the_bench_states() -> None:
    """Parsed from tb_hcpu_top.v's own checks, program by program -- not from
    the RTL: the function's registers at each halt are the numbers the bench
    was written to expect."""
    bench = (ROOT / SPEC["bench"]).read_text(encoding="utf-8").splitlines()
    programs = MODEL["pipeline_audit"]["programs"]
    starts = [p["line"] for p in rf.load()["pipeline_audit"]["programs"]] + [len(bench) + 1]
    wanted = []
    for i, prog in enumerate(programs):
        text = "\n".join(bench[starts[i] - 1:starts[i + 1] - 1])
        for reg, base, v in re.findall(r"gpr\[(\d+)\] == 32'([dh])([0-9A-Fa-f_]+)", text):
            wanted.append((prog["n"], f"R{reg}", int(v.replace("_", ""),
                                                      10 if base == "d" else 16)))
        for v in re.findall(r"hreg\[2\]\[7:0\] == 8'd(\d+)", text):
            wanted.append((prog["n"], "H2[7:0]", int(v)))
        if "if (guard_led)" in text:
            wanted.append((prog["n"], "guard_led", 1))
    got = {(x["program"], x["read"]): x["function"] for x in M["terminal"]}
    assert len(wanted) == len(got) == 32
    assert all(got[(n, r)] == v for n, r, v in wanted)


def test_the_last_row_is_a_terminal_snapshot_not_a_transition(
        runs: list[dict[str, Any]]) -> None:
    """The owner's decision of 28 September 2026. After program 11's HALT the
    bench calls $finish without a reset; in this probe the row after that
    edge prints, halted up and every probed signal held. It is recorded as a
    terminal snapshot, never compared as a transition -- the function would
    stop on it, ctrl_halted_stall being uncovered -- and the ten resets that
    follow a halt leave stack_rd, gated by the same stall, unpredicted."""
    rows = runs[0]["rows"]
    assert rows[-1] == rows[-2] and rows[-1]["halted"] == 1
    assert M["terminal_snapshot"] == {"row": 232, "halted": 1, "held": True}
    assert M["not_covered_steps"] == {}
    assert M["not_covered_outputs"] == {"ctrl_halted_stall": 11}
    assert M["unpredicted"] == {"stack_rd": 10}
    with pytest.raises(rf.NotCovered) as why:
        rf.pipeline_step(rf._pipe_state(rows[-2], C),
                         rf._pipe_inputs(rows[-2], rows[-1], SPEC), C)
    assert why.value.rule == "ctrl_halted_stall"


def test_the_result_does_not_hang_on_whether_the_snapshot_prints(
        runs: list[dict[str, Any]]) -> None:
    """Whether that last row prints depends on $strobe against $finish, and
    it did not in the audit's probe. Without it, nothing else moves."""
    full = rf.pipeline_compare(SPEC, runs)
    cut = rf.pipeline_compare(SPEC, [{**runs[0], "rows": runs[0]["rows"][:-1]}])
    assert cut["terminal_snapshot"] is None
    assert {k: v for k, v in full.items() if k != "terminal_snapshot"} == {
        k: v for k, v in cut.items() if k != "terminal_snapshot"}


def _row(runs: list[dict[str, Any]], t: int) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = runs[0]["rows"]
    return rf._pipe_state(rows[t], C), rf._pipe_inputs(rows[t], rows[t + 1], SPEC)


def _code(name: str) -> int:
    return int(C["p"][f"OP_{name}"])


@pytest.mark.parametrize("bend, rule", [
    (lambda s, i: s.update(id_opcode=_code("JMP")), "opcode:JMP"),
    (lambda s, i: s.update(halted=1), "ctrl_halted_stall"),
    (lambda s, i: i.update(print_active=1), "ctrl_print_stall"),
    (lambda s, i: i.update(trap_redirect_w=1), "fetch_redirect_trap"),
    (lambda s, i: i.update(trap_in_user_w=1), "priv_fault"),
    (lambda s, i: s.update(if_instruction=_code("CALL") << 24, pc_valid=1), "opcode:CALL"),
    (lambda s, i: s.update(id_opcode=_code("HLOAD"), id_is_codex=1)
     or i.update(rom_valid=0), "hc01_invalid_rom"),
])
def test_an_uncovered_transition_stops_the_step(bend: Callable[[dict[str, Any], dict[str, Any]],
                                                              Any], rule: str,
                                                runs: list[dict[str, Any]]) -> None:
    s, inp = _row(runs, 20)
    assert s["halted"] == 0 and inp["rst_n"] == 1
    bend(s, inp)
    with pytest.raises(rf.NotCovered) as why:
        rf.pipeline_step(s, inp, C)
    assert why.value.rule == rule


def test_a_store_then_load_to_one_word_stops_the_step(runs: list[dict[str, Any]]) -> None:
    s, inp = _row(runs, 20)
    s.update(ex_mem_write=1, ex_mem_addr=5, if_instruction=_code("LOAD") << 24 | 5,
             pc_valid=1, mem_gpr_we=0, gpr0=0)
    with pytest.raises(rf.NotCovered) as why:
        rf.pipeline_step(s, inp, C)
    assert why.value.rule == "hazard_store_load"


def test_no_interpreter_stands_in_for_the_oracle() -> None:
    for fn in (rf.pipeline_step, rf._pipe_comb, rf.pipeline_runs, rf.pipeline_compare):
        text = inspect.getsource(fn)
        assert "run_interpreter" not in text and "HISAMachine" not in text
        assert "hisa." not in text and "parity_model" not in text


# -- R3: each covered rule, broken, is red --------------------------------------------------

Step = Callable[[dict[str, Any], dict[str, Any], dict[str, Any]],
                tuple[dict[str, Any], list[str]]]


def _bend(change: Callable[[dict[str, Any], dict[str, Any], list[str]], None]) -> Step:
    def step(s: dict[str, Any], inp: dict[str, Any],
             c: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        n, fired = rf.pipeline_step(s, inp, c)
        change(s, n, fired)
        return n, fired
    return step


def _unless(rule: str, key: str, value: Callable[[dict[str, Any], dict[str, Any]], Any]
            ) -> Step:
    return _bend(lambda s, n, f: n.update({key: value(s, n)}) if rule in f else None)


RED: dict[str, Step] = {
    "a branch landing one word off": _unless("fetch_redirect_branch", "pc",
                                             lambda s, n: n["pc"] + 1),
    "a fetch that does not advance": _unless("fetch_latch", "pc", lambda s, n: s["pc"]),
    "a warm-up that never warms": _unless("fetch_warmup", "fetch_valid", lambda s, n: 0),
    "a bubble that keeps the instruction": _unless("decode_flush_redirect", "id_opcode",
                                                   lambda s, n: s["if_instruction"] >> 24),
    "CSET reading S2, not DST": _bend(
        lambda s, n, f: n.update(id_s2=s["if_instruction"] >> 12 & 0xF)
        if "decode_latch_instruction" in f and s["if_instruction"] >> 24 == _code("CSET")
        else None),
    "a register write dropped": _bend(
        lambda s, n, f: n.update({f"gpr{s['mem_dst']}": s[f"gpr{s['mem_dst']}"]})
        if "wb_gpr" in f else None),
    "the stack read one word high": _bend(
        lambda s, n, f: n.update(stack_rd=s["stack"].get(s["sp"] & 0xFF, "x"))
        if "mem_latch" in f else None),
    "a halt that never latches": _unless("ctrl_halt_latch", "halted", lambda s, n: 0),
}


@pytest.mark.parametrize("name", RED)
def test_each_broken_covered_rule_is_red(name: str, runs: list[dict[str, Any]]) -> None:
    got = rf.pipeline_compare(SPEC, runs, step=RED[name])
    assert (got["one_step_mismatches"] or got["open_loop_mismatches"]
            or got["terminal_mismatches"]), name


def _comb(change: Callable[[dict[str, Any], dict[str, Any]], None]
          ) -> Callable[..., dict[str, Any]]:
    orig = rf._pipe_comb

    def comb(s: dict[str, Any], inp: dict[str, Any], c: dict[str, Any]) -> dict[str, Any]:
        k = orig(s, inp, c)
        change(s, k)
        return k
    return comb


COMB: dict[str, Callable[[dict[str, Any], dict[str, Any]], None]] = {
    "a load-use hazard not stalled": lambda s, k: k.update(
        load_use=0, id_flush=k["branch_taken"]),
    "forwarding from EX ignored": lambda s, k: k["fwd"].update(
        fwd_gpr_s1=s["id_gpr_s1"]) if s["ex_gpr_we"] == 1 and s["ex_dst"] == s["id_s1"]
    else None,
    "a taken branch not taken": lambda s, k: k.update(branch_taken=0, if_flush=0,
                                                      id_flush=k["load_use"]),
}


@pytest.mark.parametrize("name", COMB)
def test_each_broken_combinational_rule_is_red(name: str, runs: list[dict[str, Any]],
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rf, "_pipe_comb", _comb(COMB[name]))
    got = rf.pipeline_compare(SPEC, runs)
    assert (got["one_step_mismatches"] or got["open_loop_mismatches"]
            or got["terminal_mismatches"]), name


# -- the spec and the model cannot claim more than the trace shows --------------------------


def test_rule_counts_that_are_not_the_audits_are_red() -> None:
    bent = json.loads(json.dumps(MODEL))
    next(m for m in bent["modules"] if m["name"] == "pipeline")["rules_fired"][
        "fetch_latch"] += 1
    assert any(b.startswith("F4 pipeline") for b in rf.check(bent))


def test_a_snapshot_that_did_not_hold_is_red() -> None:
    bent = json.loads(json.dumps(MODEL))
    next(m for m in bent["modules"] if m["name"] == "pipeline")["terminal_snapshot"][
        "held"] = False
    assert any(b.startswith("F1 pipeline") for b in rf.check(bent))


def test_a_stop_on_a_transition_edge_is_red() -> None:
    bent = json.loads(json.dumps(MODEL))
    next(m for m in bent["modules"] if m["name"] == "pipeline")["not_covered_steps"] = {
        "ctrl_halted_stall": [100]}
    assert any(b.startswith("F1 pipeline") for b in rf.check(bent))


def test_a_terminal_read_that_differs_is_red() -> None:
    bent = json.loads(json.dumps(MODEL))
    pipe = next(m for m in bent["modules"] if m["name"] == "pipeline")
    pipe["terminal_mismatches"] = [pipe["terminal"][0]]
    assert any(b.startswith("F3 pipeline") for b in rf.check(bent))


def test_a_register_left_unpredicted_beyond_stack_rd_is_red() -> None:
    bent = json.loads(json.dumps(MODEL))
    next(m for m in bent["modules"] if m["name"] == "pipeline")["unpredicted"] = {
        "stack_rd": 10, "pc": 1}
    assert any(b.startswith("F1 pipeline") for b in rf.check(bent))
