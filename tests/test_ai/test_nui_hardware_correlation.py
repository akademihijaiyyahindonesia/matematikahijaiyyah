"""Layer 6.5's hardware correlation, held to the evidence each link stands on.

The owner's step 6.5, 28 September 2026: link hardware, board runs, programs,
opcodes and what the board printed, each link DIRECT, DERIVED or UNKNOWN,
none drawn from a name, and P4 and P5 never made opcode-level evidence. What
is held here, on the committed model and on what the spec builds today:

    every correlation holds against its own evidence file, key and hash;
    a relation carries only the classes it may -- executes is never DIRECT;
    opcode-level evidence is exactly P3's column;
    the owner's example chain walks from HCPU to test_hisab.hasm to PRINT to
    the board's recording and its output, with a run and a hash at each step;
    and every guard turns red when what it guards is broken (R3).
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import hardware_correlation as hc  # noqa: E402
from hijaiyyah.nui import knowledge  # noqa: E402

MODEL = json.loads(hc.MODEL.read_text(encoding="utf-8"))
BOTH = pytest.mark.parametrize("model", [MODEL, json.loads(json.dumps(hc.build()))],
                               ids=["committed", "built"])
P2 = "20260924T105400Z-parity"
HISAB = "rtl/programs/test_hisab.hasm"


def _edge(model: dict[str, Any], relation: str, frm: str | None, to: str | None,
          run: str | None = None) -> dict[str, Any]:
    return copy.deepcopy(next(e for e in model["correlations"] if e["relation"] == relation
                              and e["from"] == frm and e["to"] == to
                              and (run is None or e["run_id"] == run)))


def test_the_correlation_reads_back_exactly() -> None:
    assert hc.verify() == []


def test_the_page_is_drawn_from_the_model() -> None:
    assert hc.PAGE.read_text(encoding="utf-8") == hc.page(MODEL)


@BOTH
def test_every_correlation_holds_against_its_own_evidence(model: dict[str, Any]) -> None:
    ctx = hc.context()
    ids = [e["id"] for e in model["correlations"]]
    assert len(ids) == len(set(ids)) == 1180
    for e in model["correlations"]:
        assert hc.check(e, ctx) == [], e["id"]


@BOTH
def test_a_relation_carries_only_the_classes_it_may(model: dict[str, Any]) -> None:
    allowed = {k: v["classes"] for k, v in hc.load()["relations"].items()}
    for e in model["correlations"]:
        assert e["class"] in allowed[e["relation"]], e["id"]
    assert not [e for e in model["correlations"]
                if e["relation"] == "executes" and e["class"] == "DIRECT"]
    assert model["counts"]["executes"] == {"DIRECT": 0, "DERIVED": 795, "UNKNOWN": 1}
    assert model["counts"]["ran"] == {"DIRECT": 91, "DERIVED": 0, "UNKNOWN": 2}


@BOTH
def test_nothing_is_linked_by_a_name(model: dict[str, Any]) -> None:
    """A program is one its run's record names; an opcode is one the frozen
    expectation lists for the same payload; a record naming only a target has
    no program."""
    spec = hc.load()
    runs = {r["record"]: r for r in spec["runs"]}
    expected = json.loads((ROOT / "NUI/board_expected.json").read_text(encoding="utf-8"))
    for e in model["correlations"]:
        if e["relation"] in ("ran", "printed") and e["class"] == "DIRECT":
            record = json.loads((ROOT / e["evidence"]).read_text(encoding="utf-8"))
            rule = runs[e["evidence"]]
            named = (set(record["programs"]) if "programs" in rule
                     else {record[rule["program"]["key"]]})
            assert e["to"] in named, e["id"]
        if e["relation"] == "executes" and e["class"] == "DERIVED":
            section = e["evidence_key"].split(".", 1)[0]
            entry = expected[section]["programs"][e["from"]]
            assert entry["payload_sha256"] == e["payload_sha256"]
            assert e["to"] in entry["opcodes"], e["id"]
    unknown = {e["run_id"] for e in model["correlations"]
               if e["relation"] == "ran" and e["class"] == "UNKNOWN"}
    assert unknown == {"20260925T191528Z-loader", "20260920T000027Z-jamrah"}


@BOTH
def test_opcode_evidence_is_p3s_column_and_p4_p5_are_not(model: dict[str, Any]) -> None:
    ctx = hc.context()
    assert hc.check_opcode_evidence(model["opcode_evidence"], ctx) == []
    ran = [(e["run_id"], e["to"]) for e in model["correlations"]
           if e["relation"] == "ran" and e["class"] == "DIRECT"]
    elsewhere = {p for r, p in ran if r != P2} - {p for r, p in ran if r == P2}
    assert "print-silicon" in elsewhere
    for op, row in model["opcode_evidence"].items():
        assert not set(row["evidence"]) & elsewhere, op
    assert model["opcode_evidence"]["PRINT"]["experiment"] == [
        "print-silicon", "stop-probe:ret-then-print-sentinel"]
    assert len(model["opcode_evidence"]["PRINT"]["evidence"]) == 79


def test_the_owners_example_chain_walks_to_the_boards_output() -> None:
    """HCPU -> test_hisab.hasm -> execution -> PRINT -> board recording ->
    observed output -> provenance: a run and a hash at each step."""
    record = ROOT / "cosmictera-build/parity-board/20260924T105400Z-parity.json"
    sha = hashlib.sha256(record.read_bytes()).hexdigest()
    freeze = json.loads((ROOT / "NUI/layer4_freeze.json").read_text(encoding="utf-8"))
    assert sha == next(e["sha256"] for e in freeze["evidence"]
                       if e["path"] == record.relative_to(ROOT).as_posix())
    hcpu = _edge(MODEL, "supports", P2, "6.1:cpu")
    ran = _edge(MODEL, "ran", P2, HISAB, P2)
    printed = _edge(MODEL, "printed", P2, HISAB, P2)
    judged = _edge(MODEL, "judged", P2, HISAB, P2)
    runs_print = _edge(MODEL, "executes", HISAB, "PRINT")
    assert (hcpu["class"], ran["class"], printed["class"]) == ("DIRECT",) * 3
    assert (judged["class"], runs_print["class"]) == ("DERIVED", "DERIVED")
    assert ran["evidence_sha256"] == printed["evidence_sha256"] == sha
    assert ran["payload_sha256"] == runs_print["payload_sha256"]
    assert printed["value"] == "65824\n2586908910\n" and judged["value"] == "MISMATCH"
    a = hc.answer("program", HISAB, MODEL, hc.context())
    assert {hcpu["id"], ran["id"], printed["id"], judged["id"], runs_print["id"]} <= set(
        a["correlations"])


def test_what_the_interpreter_ran_is_not_what_the_board_ran() -> None:
    """P5: the interpreter stops before the PRINT, the board prints -- the
    reason executes is never read as the board's own execution."""
    probe = "stop-probe:halt-then-print"
    ops = {e["to"] for e in MODEL["correlations"]
           if e["relation"] == "executes" and e["from"] == probe}
    printed = _edge(MODEL, "printed", "20260925T163903Z-stop", probe)
    assert "PRINT" not in ops and printed["value"].strip() == "5"


@BOTH
def test_the_contract_answers_as_written(model: dict[str, Any]) -> None:
    edges = {e["id"]: e for e in model["correlations"]}
    for want, got in zip(hc.load()["contract"], model["contract"], strict=True):
        assert got["query"] == want["query"]
        seen = {(edges[i]["relation"], edges[i]["from"] if edges[i]["relation"] == "executes"
                 else edges[i]["run_id"], edges[i]["to"], edges[i]["class"])
                for i in got["correlations"]}
        for relation, frm, to, cls in want["includes"]:
            assert (relation, frm, to, cls) in seen, (want["query"], relation, frm, to)
        if "evidence_programs" in want:
            assert got["opcode_evidence"]["programs"] == want["evidence_programs"]


def test_the_first_p2_run_is_named_and_not_correlated() -> None:
    first = "cosmictera-build/parity-board/20260924T104300Z-parity.json"
    assert [n["record"] for n in MODEL["not_correlated"]] == [first]
    assert all(r["record"] != first for r in MODEL["runs"])
    assert not [e for e in MODEL["correlations"] if e["evidence"] == first]


def test_the_owners_directions_through_the_knowledge_base() -> None:
    chain = knowledge.query(f"hardware correlation program {HISAB}")
    relations = {i["relation"] for d in knowledge.DOMAINS for i in chain[d]
                 if i["what"] == "correlation"}
    assert relations == {"ran", "printed", "judged", "executes", "supports", "records"}
    loader = knowledge.query("hardware correlation run 20260925T191528Z-loader")
    assert any("target `loader`" in u for u in loader["unknown"])
    printed = knowledge.query("hardware correlation opcode PRINT")
    head, = [i for i in printed["NUI"] if i["what"] == "hardware correlation"]
    assert head["opcode_evidence"]["programs"] == 79


# -- R3: each guard red when what it guards is broken ------------------------------------


def _to(e: dict[str, Any], **kw: Any) -> dict[str, Any]:
    return {**e, **kw}


SABOTAGES: dict[str, tuple[Callable[[], dict[str, Any]], Callable[[dict[str, Any]],
                                                                  dict[str, Any]], str]] = {
    "a run's program moved to another program": (
        lambda: _edge(MODEL, "ran", P2, HISAB, P2), lambda e: _to(e, to="print-silicon"), "X3"),
    "a program given an opcode it does not execute": (
        lambda: _edge(MODEL, "executes", HISAB, "PRINT"),
        lambda e: _to(e, to="ADD", value="ADD"), "X3"),
    "P4 promoted to opcode evidence": (
        lambda: _edge(MODEL, "executes", "print-silicon", "PRINT"),
        lambda e: _to(e, **{"class": "DIRECT"}), "X1"),
    "an UNKNOWN correlation forced DIRECT": (
        lambda: _edge(MODEL, "ran", "20260925T191528Z-loader", None),
        lambda e: _to(e, **{"class": "DIRECT"}), "X5"),
    "cross-run provenance mixed": (
        lambda: _edge(MODEL, "printed", "20260925T141701Z-print", "print-silicon"),
        lambda e: _to(e, run_id="20260925T141737Z-print"), "X4"),
    "another run's output on this run": (
        lambda: _edge(MODEL, "printed", "20260925T141737Z-print", "print-silicon"),
        lambda e: _to(e, value=_edge(MODEL, "printed", "20260925T141701Z-print",
                                     "print-silicon")["value"]), "X3"),
    "a hash forged": (
        lambda: _edge(MODEL, "ran", P2, HISAB, P2), lambda e: _to(e, evidence_sha256="0" * 64),
        "X2"),
    "a claim moved to a run that does not support it": (
        lambda: _edge(MODEL, "supports", P2, "6.1:cpu"),
        lambda e: _to(e, to="6.1:uart"), "X3"),
}


@pytest.mark.parametrize("name", SABOTAGES)
def test_each_sabotage_turns_its_guard_red(name: str) -> None:
    get, sabotage, want = SABOTAGES[name]
    ctx = hc.context()
    assert hc.check(get(), ctx) == []
    failed = [f["check"] for f in hc.check(sabotage(get()), ctx)]
    assert want in failed, (name, failed)


def test_p4_counted_as_opcode_evidence_is_refused() -> None:
    spec = hc.load()
    spec["opcode_evidence"]["run"] = "20260925T141701Z-print"
    with pytest.raises(LookupError, match="not P3's column"):
        hc.build(hc.context(spec=spec))
