"""The HCPU's integration oracle, audited before any model of the HCPU is written.

The owner's order of 28 September 2026, when the pipeline function was
accepted: the next model is the HCPU as a system, with rtl/tb/tb_hcpu_top.v
as its integration oracle -- but first an audit of its coverage, on the
pipeline audit's principles, so that no HCPU model is written before the
oracle map and the state boundary are measured. No bench is added, no RTL
changes, no interpreter stands in for the oracle. What is held here:

    the measurement is sound: what each edge took is what the edge before
    left, for every signal the audit probes;
    the map is today's: the audit run now is the committed one;
    only rst_n and imem_data move among the HCPU's inputs, and the ports the
    spec names are hcpu_top.v's own;
    the state boundary is the RTL's own non-blocking assignments, and for a
    subsystem that already has a function it agrees with that function's
    declared state, except what is named outside it;
    what the bench never runs is named, with its reason, and each reason is
    a fact the trace shows;
    and each part of the audit, broken, is red.
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
H, A = SPEC["hcpu_audit"], SPEC["pipeline_audit"]
R = MODEL["hcpu_audit"]
MODS = {m["name"]: m for m in SPEC["modules"]}


@pytest.fixture(scope="module")
def trace() -> dict[str, Any]:
    return rf.hcpu_trace(H, A)


def _checked(model: dict[str, Any]) -> list[str]:
    return [b for b in rf.check(model) if b.startswith("A")]


def _live(trace: dict[str, Any]) -> list[dict[str, Any]]:
    """The rows the live edges take."""
    after = trace["after"]
    return [after[t - 1] for t, _, resetting, _ in
            rf._edges(after, "u_fetch.pc", "u_fetch.fetch_valid", len(A["programs"]))
            if not resetting]


def test_the_measurement_is_sound() -> None:
    assert R["sampling"]["compared"] == R["live_edges"] == 178
    assert R["sampling"]["mismatched"] == {}
    assert R["sampling"]["release_edges"] == {"stepped": 11, "held_in_reset": 0}
    assert R["bench_pass"] and R["bench_said"] == "Total: 15 PASS, 0 FAIL"
    assert _checked(MODEL) == []


def test_the_audit_run_now_is_the_committed_one(trace: dict[str, Any]) -> None:
    assert json.loads(json.dumps(rf.hcpu_audit(H, A, trace))) == R


def test_the_run_is_the_pipeline_audits() -> None:
    """One bench, one list of programs: the audit names the pipeline audit's
    run rather than a second copy of it."""
    assert H["run"] == "pipeline_audit"
    for key in ("bench", "top", "instance", "clock", "compile", "programs", "bench_verdict"):
        assert key not in H, key
    assert R["edges"] == MODEL["pipeline_audit"]["edges"]


def test_only_rst_n_and_imem_data_move() -> None:
    moving = {k for k, v in R["inputs"].items() if v["changes"]}
    assert moving == {"rst_n", "imem_data"} == set(H["inputs_change"])
    for k in ("uart_rx", "sd_cmd_in", "sd_dat_in"):
        assert R["inputs"][k]["values"] == ["z"], k
    assert R["inputs"]["dbg_gpr_raddr"]["values"] == ["0"]
    ports = rf._ports(ROOT)
    assert list(H["inputs"]) == ports["input"] and list(H["outputs"]) == ports["output"]
    assert R["outputs"]["uart_tx"]["values"] == ["1"]
    assert R["outputs"]["imem_we"]["values"] == ["0"]


def test_the_state_boundary_is_the_rtls_own() -> None:
    b = R["boundary"]
    assert (b["files"], b["registers"], b["undeclared"], b["missing"]) == (21, 171, [], [])
    for sub in H["subsystems"]:
        for f, names in sub["files"].items():
            parsed = set(rf._nb_targets(ROOT / f))
            hidden = set(sub.get("not_elaborated", {}).get("names", {}).get(f, []))
            assert set(names) == parsed - hidden, f


def test_a_functions_state_is_the_boundarys_less_what_is_named_outside() -> None:
    subs = {s["id"]: s for s in H["subsystems"]}
    pipe = subs["pipeline"]["files"]
    bundles = [n for names in MODS["pipeline"]["state"].values() for n in names]
    stages = (pipe["rtl/hcpu_fetch.v"] + pipe["rtl/hcpu_decode.v"]
              + pipe["rtl/hcpu_execute.v"] + pipe["rtl/hcpu_memory.v"])
    assert sorted(set(stages) - {"ra_stack[]", "stack[]"}) == sorted(bundles)
    assert "halted" in MODS["pipeline"]["state_also"]
    assert "larik tumpukan" in MODS["pipeline"]["state_also"]
    assert list(subs["pipeline"]["outside_function"]) == ["rtl/hcpu_execute.v:ra_stack[]"]
    mmio = subs["mmio"]["files"]
    own = [k for k in MODS["hcpu_mmio"]["state"] if "." not in k]
    assert own == mmio["rtl/hcpu_mmio.v"]
    for f, prefix in (("rtl/hcpu_uart_rx.v", "u_rx."), ("rtl/hcpu_timer.v", "u_timer.")):
        assert ([k[len(prefix):] for k in MODS["hcpu_mmio"]["state"] if k.startswith(prefix)]
                == mmio[f]), f
    assert MODS["hcpu_uart_tx"]["state"] == subs["uart_tx"]["files"]["rtl/hcpu_uart_tx.v"]


def test_what_is_named_outside_a_function_is_as_the_rtl_says() -> None:
    top = (ROOT / "rtl/hcpu_top.v").read_text(encoding="utf-8").splitlines()
    execute = (ROOT / "rtl/hcpu_execute.v").read_text(encoding="utf-8").splitlines()
    assert ".pc_we" in top[645 - 1] and "1'b0" in top[645 - 1]
    assert "PIPELINE_GUARD(0)" in top[662 - 1]
    assert "ra_stack" in execute[331 - 1]
    assert "priv_fault = in_user" in execute[310 - 1]
    assert "mem_fault = in_user" in execute[317 - 1]
    assert rf._nb_targets(ROOT / "rtl/hcpu_execute.v")["ra_stack[]"] > 331
    assert "branch_call" in MODEL["pipeline_audit"]["not_covered"]
    assert "branch_ret" in MODEL["pipeline_audit"]["not_covered"]


def test_the_x_registers_have_no_reset_and_no_writer_that_ran() -> None:
    x = R["state"]["sdio"]["x"]
    assert len(x) == 17 and all(k.startswith("u_mmio.u_sdio.") for k in x)
    assert all(not st["x"] for sid, st in R["state"].items() if sid != "sdio")


def test_what_the_bench_never_runs_is_named_with_its_reason() -> None:
    ids = [t["id"] for t in rf.hcpu_transitions(H)]
    assert [t["id"] for t in R["transitions"]] == ids
    assert R["not_covered"] == list(rf.hcpu_declared(H))
    assert (len(ids), len(ids) - len(R["not_covered"])) == (162, 47)
    fired = {t["id"]: t["fired"] for t in R["transitions"]}
    assert all(fired[i] == 0 for i in R["not_covered"])
    assert all(fired[i] > 0 for i in ids if i not in R["not_covered"])


def test_a_functions_transitions_are_its_own_rules() -> None:
    by_sub: dict[str, list[str]] = {}
    for t in rf.hcpu_transitions(H):
        by_sub.setdefault(t["subsystem"], []).append(t.get("rule", t["id"]))
    for sub, fn in (("mmio", "hcpu_mmio"), ("uart_tx", "hcpu_uart_tx"),
                    ("dataram", "hcpu_dataram")):
        assert by_sub[sub] == [r["id"] for r in rf.rules(MODS[fn])], sub
    assert "pipeline" not in by_sub and "register file" not in by_sub


def test_the_transmitter_agrees_with_its_own_function_on_this_bench() -> None:
    """Same bench, two derivations: the audit's predicates over the RTL and
    the function's own run name the same rules covered."""
    tx = next(m for m in MODEL["modules"] if m["name"] == "hcpu_uart_tx")
    audit = [t["id"].split(".", 1)[1] for t in R["transitions"]
             if t["id"].startswith("uart_tx.") and t["fired"]]
    assert audit == [r["id"] for r in tx["rules"] if r["fired"]] == ["reset", "idle_wait"]


def test_the_reasons_hold_on_the_trace(trace: dict[str, Any]) -> None:
    rows, live = trace["after"], _live(trace)
    for k in ("ex_is_print", "ex_is_emits", "u_trap.pending", "u_trap.armed", "trap_reg_we_w",
              "trap_is_eret_w", "uart_busy", "u_mmio.u_rx.rx_valid", "u_mmio.sd_soft_rst",
              "u_mmio.u_sdio.start", "u_mmio.u_sdio.busy", "u_mmio.u_sdio.wr_en"):
        assert {r[k] for r in rows} == {0}, k
    assert {r["u_trap.mode"] for r in rows} == {1}
    assert {r["u_mmio.u_rx.rx_sync"] for r in rows} == {1}
    assert {r["u_mmio.u_sdio.state"] for r in rows} == {0}
    assert {r["u_mmio.u_timer.compare"] for r in rows} == {0xFFFF_FFFF}
    access = [(r["dram_re"], r["dram_we"], r["dram_addr"]) for r in live
              if r["dram_re"] == 1 or r["dram_we"] == 1]
    assert access == [(0, 1, 0), (1, 0, 0), (0, 1, 10), (1, 0, 10)]
    nibbles = {r["dram_addr"] & 0xF for r in live}
    assert not nibbles & {0x4, 0x7, 0xE}
    assert not [r for r in live if 0xFE0 <= r["dram_addr"] <= 0xFEF]
    loads = {r["rom_addr"] for r in live if r["id_opcode"] == 0x40 and r["ex_stall"] != 1}
    assert loads & set(range(31, 37)) == {31}
    assert not [r for r in rows if isinstance(r["id_opcode"], int) and r["id_opcode"] >= 0xE0]
    assert {r["calu_op"] for r in rows} <= set(range(6))


def test_the_read_path_runs_and_is_never_selected() -> None:
    reads = [t["id"] for t in R["transitions"]
             if t["id"].startswith("mmio.read_") and t["fired"]]
    assert len(reads) == 8
    assert H["covered_limits"]["mmio.read_*"].startswith("delapan aturan baca")
    assert R["state"]["mmio"]["held"]["u_mmio.periph_sel"] == "0"
    assert "u_mmio.periph_rdata" in R["state"]["mmio"]["moved"]


def test_the_unreachable_are_unreachable_by_the_lines_cited() -> None:
    top = (ROOT / "rtl/hcpu_top.v").read_text(encoding="utf-8").splitlines()
    execute = (ROOT / "rtl/hcpu_execute.v").read_text(encoding="utf-8").splitlines()
    assert ".src_illegal" in top[798 - 1] and "1'b0" in top[798 - 1]
    assert "reg [2:0] print_state" in top[247 - 1]
    assert [ln.split("=")[1].strip(" ;") for ln in top[261:266] + top[278:281]] == [
        f"3'd{i}" for i in range(8)]
    arms = "\n".join(execute[202 - 1:207])
    assert "calu_op" in arms and all(f"3'd{i}" in arms for i in range(6))
    assert "3'd6" not in arms and "3'd7" not in arms


def test_every_line_the_spec_cites_says_what_it_names() -> None:
    sdio = (ROOT / "rtl/hcpu_sdio.v").read_text(encoding="utf-8").splitlines()
    for t in H["transitions"]:
        if t["id"].startswith("sdio.s_"):
            assert f"{t['id'][5:].upper()}:" in sdio[t["lines"][0] - 1], t["id"]
        if t["subsystem"] == "print":
            assert all(286 <= n <= 390 for n in t["lines"]), t["id"]


# -- R3: each part of the audit, broken, is red ---------------------------------------------


def _with(audit: dict[str, Any]) -> dict[str, Any]:
    return {**MODEL, "hcpu_audit": audit}


def _rules() -> dict[str, Any]:
    p = rf._pkg(ROOT)
    ops = {v: k[3:] for k, v in p.items() if k.startswith("OP_")}
    tx = rf._parameters(MODS["hcpu_uart_tx"], ROOT)
    return rf._hcpu_rules(p, ops, tx, rf.uart_rx_parameters(tx["CLK_HZ"], tx["BAUD"]),
                          rf._sdio_states(ROOT))


def test_a_transition_predicate_broken_is_red(trace: dict[str, Any]) -> None:
    rules = _rules()
    rules["dataram.write"] = lambda r: False
    got = rf.hcpu_audit(H, A, trace, rules_=rules)
    assert "dataram.write" in got["not_covered"]
    assert any(b.startswith("A3") for b in _checked(_with(got)))


def test_sampling_one_edge_off_is_red(trace: dict[str, Any]) -> None:
    shifted = {**trace, "active": trace["after"][1:] + trace["after"][-1:]}
    got = rf.hcpu_audit(H, A, shifted)
    assert got["sampling"]["mismatched"]
    assert any(b.startswith("A1") for b in _checked(_with(got)))


def test_a_register_left_out_of_the_boundary_is_red(trace: dict[str, Any]) -> None:
    h = json.loads(json.dumps(H))
    trap = next(s for s in h["subsystems"] if s["id"] == "trap")
    trap["files"]["rtl/hcpu_trap.v"].remove("epc")
    got = rf.hcpu_audit(h, A, trace)
    assert got["boundary"]["undeclared"] == ["rtl/hcpu_trap.v:epc"]
    assert any(b.startswith("A2") for b in _checked(_with(got)))


def test_an_unelaborated_register_not_named_so_is_red(trace: dict[str, Any]) -> None:
    h = json.loads(json.dumps(H))
    guard = next(s for s in h["subsystems"] if s["id"] == "guard")
    guard["not_elaborated"]["names"]["rtl/hcpu_guard.v"].remove("guard_r")
    got = rf.hcpu_audit(h, A, trace)
    assert got["boundary"]["undeclared"] == ["rtl/hcpu_guard.v:guard_r"]
    assert any(b.startswith("A2") for b in _checked(_with(got)))


def test_a_register_the_rtl_does_not_hold_is_red(trace: dict[str, Any]) -> None:
    h = json.loads(json.dumps(H))
    trap = next(s for s in h["subsystems"] if s["id"] == "trap")
    trap["files"]["rtl/hcpu_trap.v"].append("stack[]")
    got = rf.hcpu_audit(h, A, trace)
    assert got["boundary"]["missing"] == ["rtl/hcpu_trap.v:stack[]"]
    assert any(b.startswith("A2") for b in _checked(_with(got)))


def test_a_coverage_claim_the_spec_does_not_make_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    spec["hcpu_audit"]["not_covered"].pop("trap.eret")
    monkeypatch.setattr(rf, "load", lambda: spec)
    assert any(b.startswith("A3") for b in _checked(MODEL))


def test_a_function_rule_the_audit_does_not_hold_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    tx = next(m for m in spec["modules"] if m["name"] == "hcpu_uart_tx")
    tx["rules"] = tx["rules"][:-1]
    monkeypatch.setattr(rf, "load", lambda: spec)
    assert any(b.startswith("A3 hcpu") for b in _checked(MODEL))


def test_an_input_claimed_still_that_moves_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    spec["hcpu_audit"]["inputs_change"] = ["rst_n"]
    monkeypatch.setattr(rf, "load", lambda: spec)
    assert any(b.startswith("A6") for b in _checked(MODEL))


def test_an_x_on_the_bus_is_refused_not_classified(trace: dict[str, Any]) -> None:
    """The bus address was never x on a live edge; had it been, the audit does
    not decide which read arm an x select takes."""
    after = [{**r, "dram_addr": "x"} for r in trace["after"]]
    with pytest.raises(ValueError, match="bus address"):
        rf.hcpu_audit(H, A, {**trace, "after": after})


def test_a_bench_that_did_not_pass_is_red() -> None:
    assert any(b.startswith("A4 hcpu") for b in _checked(_with({**R, "bench_pass": False})))
