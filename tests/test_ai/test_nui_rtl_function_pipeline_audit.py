"""The pipeline's oracle, audited before any model of it is written.

The owner's order of 28 September 2026: rtl/tb/tb_hcpu_top.v is the system
oracle for the pipeline, and there is no bench per stage -- so first map what
the bench shows: the state that can be observed, the sampling point, what
passes through each stage, and which RTL transitions never run. No bench is
added, no RTL changes, and no internal state is claimed that the trace does
not show. What is held here:

    the measurement is sound: what each edge took is what the edge before
    left, and the identity carried past decode agrees with every stage
    register that names an instruction;
    the map is today's: the audit run now is the committed one;
    what the bench never runs is named, with its reason, and neither side
    can claim more than the other;
    the global stall is never taken by a live edge, and two transitions are
    unreachable by the wiring the spec cites;
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
AUDIT = rf.load()["pipeline_audit"]
R = MODEL["pipeline_audit"]


@pytest.fixture(scope="module")
def trace() -> dict[str, Any]:
    return rf.pipeline_trace(AUDIT)


def _checked(model: dict[str, Any]) -> list[str]:
    return [b for b in rf.check(model) if b.startswith("A")]


def test_the_measurement_is_sound() -> None:
    assert R["sampling"]["compared"] == R["live_edges"] == 178
    assert R["sampling"]["mismatched"] == {}
    assert R["sampling"]["release_edges"] == {"stepped": 11, "held_in_reset": 0}
    assert R["identity"] == {"id_checked": 178, "id_mismatches": 0, "ex_checked": 178,
                             "ex_mismatches": 0}
    assert _checked(MODEL) == []


def test_the_audit_run_now_is_the_committed_one(trace: dict[str, Any]) -> None:
    assert rf.pipeline_audit(AUDIT, trace) == R


def test_the_programs_are_the_benchs_eleven() -> None:
    bench = (ROOT / AUDIT["bench"]).read_text(encoding="utf-8").splitlines()
    for p in AUDIT["programs"]:
        assert f"Program {p['n']}" in bench[p["line"] - 1]
        assert all(bench[n - 1].lstrip().startswith("if (") for n in p["checks"])
    assert [p["n"] for p in R["programs"]] == list(range(1, 12))
    assert R["bench_pass"] and R["bench_said"] == "Total: 15 PASS, 0 FAIL"


def test_what_the_bench_never_runs_is_named_with_its_reason() -> None:
    ids = [t["id"] for t in AUDIT["transitions"]]
    assert R["not_covered"] == list(AUDIT["not_covered"])
    assert (len(ids), len(ids) - len(R["not_covered"])) == (78, 45)
    fired = {t["id"]: t["fired"] for t in R["transitions"]}
    assert all(fired[i] == 0 for i in R["not_covered"])
    assert all(fired[i] > 0 for i in ids if i not in AUDIT["not_covered"])


def test_the_opcode_arms_are_read_from_the_decoder() -> None:
    decode = (ROOT / AUDIT["opcodes"]["decode"]).read_text(encoding="utf-8").splitlines()
    for name, o in R["opcodes"].items():
        assert f"`OP_{name}" in decode[o["line"] - 1], name
    assert len(R["opcodes"]) == 55
    assert R["opcodes_not_covered"] == AUDIT["opcodes"]["not_covered"]
    assert len(R["opcodes_not_covered"]) == 29


def test_the_global_stall_is_never_taken_by_a_live_edge() -> None:
    """The finding the model's form has to answer to: halted rises and the
    bench resets on the next edge, so no live edge ever holds a stage."""
    fired = {t["id"]: t["fired"] for t in R["transitions"]}
    for rid in ("ctrl_halted_stall", "decode_stall", "ex_stall", "mem_stall",
                "ctrl_print_stall"):
        assert fired[rid] == 0, rid
    assert fired["ctrl_halt_latch"] == fired["wb_halt"] == 11


def test_two_transitions_are_unreachable_by_the_wiring_cited() -> None:
    top = (ROOT / "rtl/hcpu_top.v").read_text(encoding="utf-8").splitlines()
    ctrl = (ROOT / "rtl/hcpu_controller.v").read_text(encoding="utf-8").splitlines()
    assert "(1'b0)" in top[510 - 1] and ".flush" in top[510 - 1]
    assert "(redirect_taken)" in top[882 - 1] and ".branch_taken" in top[882 - 1]
    assert "if_flush = branch_taken && !global_stall" in ctrl[98 - 1]


# -- R3: each part of the audit, broken, is red ---------------------------------------------


def _with(audit: dict[str, Any]) -> dict[str, Any]:
    return {**MODEL, "pipeline_audit": audit}


def test_a_transition_predicate_broken_is_red(trace: dict[str, Any]) -> None:
    p = rf._pkg(ROOT)
    ops = {v: k[3:] for k, v in p.items() if k.startswith("OP_")}
    rules = rf._pipe_rules(p, rf._usage(ROOT), ops, rf._decode_arms(AUDIT, ROOT))
    rules["hazard_load_use"] = lambda r: False
    got = rf.pipeline_audit(AUDIT, trace, rules_=rules)
    assert "hazard_load_use" in got["not_covered"]
    assert any(b.startswith("A3") for b in _checked(_with(got)))


def test_sampling_one_edge_off_is_red(trace: dict[str, Any]) -> None:
    shifted = {**trace, "active": trace["after"][1:] + trace["after"][-1:]}
    got = rf.pipeline_audit(AUDIT, shifted)
    assert got["sampling"]["mismatched"]
    assert any(b.startswith("A1") for b in _checked(_with(got)))


def test_an_identity_the_stage_register_does_not_carry_is_red(trace: dict[str, Any]) -> None:
    after = [dict(r) for r in trace["after"]]
    k = next(i for i, r in enumerate(after) if r["id_opcode"] == 0x40 and r["rst_n"] == 1)
    after[k]["id_pc"] += 1
    got = rf.pipeline_audit(AUDIT, {**trace, "after": after})
    assert got["identity"]["id_mismatches"]
    assert any(b.startswith("A2") for b in _checked(_with(got)))


def test_a_coverage_claim_the_spec_does_not_make_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    spec["pipeline_audit"]["not_covered"].pop("hazard_store_load")
    monkeypatch.setattr(rf, "load", lambda: spec)
    assert any(b.startswith("A3") for b in _checked(MODEL))


def test_an_opcode_arm_claimed_covered_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    spec["pipeline_audit"]["opcodes"]["not_covered"].remove("JMP")
    monkeypatch.setattr(rf, "load", lambda: spec)
    assert any(b.startswith("A3") for b in _checked(MODEL))


def test_a_bench_that_did_not_pass_is_red() -> None:
    assert any(b.startswith("A4") for b in _checked(_with({**R, "bench_pass": False})))
