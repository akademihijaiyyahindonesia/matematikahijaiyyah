"""Layer 6.4's hardware state model, held to what an answer may mean.

The owner's step 6.4, 27 September 2026: a hardware answer names the kind of
state it gives -- IDENTITY, CAPABILITY, OBSERVED, CURRENT -- and keeps each
claim's 6.3 provenance. What is held here, on the committed model and on what
the spec builds today:

    every claim has exactly one kind, and its status is one that kind allows;
    capability is never an observation, and history is never the present;
    a CURRENT question is answered only by a registered live source -- today
    none -- and never falls back to the newest run;
    the answer's state follows one precedence, LIVE > MEASURED > SIMULATED >
    UNKNOWN, so it is the same every time;
    the three claims 6.3 left incomplete stay MEASURED and are named as
    incomplete wherever they answer;
    and every check turns red when what it guards is broken (R3).
"""
from __future__ import annotations

import copy
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import hardware_provenance as hp  # noqa: E402
from hijaiyyah.nui import hardware_state as hs  # noqa: E402
from hijaiyyah.nui import knowledge  # noqa: E402
from hijaiyyah.nui import telemetry_sources as ts  # noqa: E402

MODEL = json.loads(hs.MODEL.read_text(encoding="utf-8"))
BOTH = pytest.mark.parametrize("model", [MODEL, json.loads(json.dumps(hs.build()))],
                               ids=["committed", "built"])
INCOMPLETE = ["6.1:hdmi", "6.1:reset_button", "6.2:boot_duration"]
REASON = "no live hardware telemetry source"


def _objects(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    provenance = json.loads(hp.MODEL.read_text(encoding="utf-8"))
    return {o["id"]: o for o in [*provenance["claims"], *model["observed_opcodes"]]}


def test_the_state_model_reads_back_exactly() -> None:
    assert hs.verify() == []


def test_the_page_is_drawn_from_the_model() -> None:
    assert hs.PAGE.read_text(encoding="utf-8") == hs.page(MODEL)


@BOTH
def test_every_claim_has_one_kind_its_status_allows(model: dict[str, Any]) -> None:
    ctx, objects = hs.context(), _objects(model)
    ids = [e["id"] for e in model["claims"]]
    assert len(ids) == len(set(ids)) == 171 == 68 + 103
    assert set(ids) == set(objects)
    for e in model["claims"]:
        assert hs.check_entry(e, objects[e["id"]], ctx) == [], e["id"]
    assert {k: model["counts"][k] for k in hs.CATEGORIES} == {
        "IDENTITY": 4, "CAPABILITY": 19, "OBSERVED": 145, "CURRENT": 3}


@BOTH
def test_capability_is_never_an_observation_and_history_never_the_present(
        model: dict[str, Any]) -> None:
    """The owner, 28 September 2026: a configuration the board proved is a
    capability, not an identity -- the 27 MHz clock and UART 115200 -- and
    stays MEASURED; everything else a capability holds is SIMULATED."""
    for e in model["claims"]:
        if e["category"] == "CAPABILITY":
            assert e["status"] == ("MEASURED" if e["id"] in ("6.1:clock", "6.1:uart")
                                   else "SIMULATED"), e["id"]
        if e["category"] == "OBSERVED":
            assert e["status"] in ("MEASURED", "UNKNOWN"), e["id"]
        if e["category"] == "CURRENT":
            assert e["status"] == "UNKNOWN" and e["source_kind"] == "unknown", e["id"]
        if e["source_kind"] == "historical_board_evidence":
            assert e["category"] != "CURRENT", e["id"]


@BOTH
def test_nothing_is_live(model: dict[str, Any]) -> None:
    assert model["live_sources"] == []
    assert not [e for e in model["claims"] if e["status"] == "LIVE"]


@BOTH
def test_the_three_incomplete_stay_measured_and_incomplete(model: dict[str, Any]) -> None:
    """The owner: claim status MEASURED, provenance INCOMPLETE -- neither
    filled nor lowered."""
    got = {e["id"]: (e["status"], e["verification"]) for e in model["claims"]
           if e["verification"] == "incomplete"}
    assert got == {i: ("MEASURED", "incomplete") for i in INCOMPLETE}
    assert all(e["category"] == "OBSERVED" for e in model["claims"] if e["id"] in got)


@BOTH
def test_the_observed_opcodes_are_p3s_column_from_its_own_record(model: dict[str, Any]) -> None:
    parity = json.loads((ROOT / "NUI/parity_model.json").read_text(encoding="utf-8"))
    column = parity["board_corpus"]["opcodes"]
    freeze = json.loads((ROOT / "NUI/layer4_freeze.json").read_text(encoding="utf-8"))
    record = hs.load()["observed_opcodes"]["record"]
    frozen = next(e for e in freeze["evidence"] if e["path"] == record)
    assert [o["id"] for o in model["observed_opcodes"]] == [f"P3:{op}" for op in column]
    for o in model["observed_opcodes"]:
        row = column[o["id"][3:]]
        assert o["verification"] == "verified", o["id"]
        if row["programs"] > 0:
            assert o["status"] == "MEASURED" and f"kolom {row['board']}" in o["claim"]
            assert (o["evidence"], o["evidence_sha256"], o["run_id"]) == (
                record, frozen["sha256"], Path(record).stem)
            assert o["run_identity"] == "instrumented"
        else:
            assert o["status"] == "UNKNOWN" and o["evidence"] is None and o["reason"]
    assert model["counts"]["observed_opcodes_measured"] == 79
    assert sum(1 for r in column.values() if r["board"] == "PARITY") == 74


@BOTH
def test_the_contract_answers_as_the_owner_said(model: dict[str, Any]) -> None:
    ctx = hs.context()
    for want, got in zip(hs.load()["contract"], model["contract"], strict=True):
        assert got["query"] == want["query"]
        for key, value in want.items():
            assert got[key] == value, (want["query"], key, got[key])
        assert hs.check_answer(got, model, ctx) == [], want["query"]


def test_a_current_question_never_falls_back_to_history() -> None:
    """Every subject the model knows, asked for now, is UNKNOWN for want of a
    live source -- the history behind it notwithstanding."""
    ctx = hs.context()
    subjects = [*hp.load()["queries"], *hs.load()["subjects"],
                *[c["id"].split(":", 1)[1] for c in ctx["provenance"]["claims"]],
                "opcode PRINT"]
    for subject in subjects:
        a = hs.answer("current", subject, MODEL, ctx)
        assert (a["state"], a["basis"], a["reason"]) == ("UNKNOWN", [], REASON), subject
        assert hs.check_answer(a, MODEL, ctx) == [], subject
        for group in ("identity", "capability", "observed", "provenance"):
            b = hs.answer(group, subject, MODEL, ctx)
            assert b["state"] != "LIVE" and hs.check_answer(b, MODEL, ctx) == []


def test_the_owners_queries_through_the_knowledge_base() -> None:
    now = knowledge.query("hardware current program")
    head, = [i for i in now["NUI"] if i["what"] == "hardware answer"]
    assert (head["state"], head["basis"], head["reason"]) == ("UNKNOWN", [], REASON)
    assert now["PAPAN"] == [] and now["unknown"][0] == REASON
    hcpu = knowledge.query("hardware identity HCPU")
    cpu, = hcpu["PAPAN"]
    assert (cpu["id"], cpu["category"], cpu["status"]) == ("6.1:cpu", "IDENTITY", "MEASURED")
    fpga = knowledge.query("hardware capability FPGA resources")
    assert all(i["provenance"]["evidence_kind"] == "PNR/build-derived" for i in fpga["RTL"])
    printed = knowledge.query("hardware observed opcode PRINT")
    item, = printed["PAPAN"]
    assert (item["status"], item["source_kind"]) == ("MEASURED", "historical_board_evidence")
    peripheral = knowledge.query("hardware observed peripheral")
    flagged = [u for u in peripheral["unknown"] if "check 6" in u]
    assert [u.split(":")[0] + ":" + u.split(":")[1] for u in flagged] == [
        "6.1:hdmi", "6.1:reset_button"]


def test_a_registered_live_source_answers_now_and_only_now(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """LIVE only when access() finds it: a live field becomes CURRENT, its
    history is not what answers, and every other subject stays UNKNOWN."""
    spec = ts.load()
    spec["live_sources"] = ["uptime"]
    monkeypatch.setattr(ts, "load", lambda: spec)
    registry = json.loads(json.dumps(ts.build()))
    provenance = json.loads(json.dumps(hp.build(hp.context(registry=registry))))
    ctx = hs.context(provenance=provenance, base=hp.context(registry=registry))
    model = json.loads(json.dumps(hs.build(ctx)))
    uptime = next(e for e in model["claims"] if e["id"] == "6.2:uptime")
    assert (uptime["category"], uptime["status"]) == ("CURRENT", "LIVE")
    now = hs.answer("current", "telemetry", model, ctx)
    assert (now["state"], now["basis"]) == ("LIVE", ["6.2:uptime"])
    other = hs.answer("current", "program", model, ctx)
    assert (other["state"], other["reason"]) == ("UNKNOWN", "no live source for `program`")
    assert "6.2:uptime" not in hs.answer("observed", "telemetry", model, ctx)["claims"]


# -- R3: each check red when what it guards is broken -------------------------------------


def _entry(cid: str) -> dict[str, Any]:
    return copy.deepcopy(next(e for e in MODEL["claims"] if e["id"] == cid))


ENTRY_SABOTAGES: dict[str, tuple[str, Callable[[dict[str, Any]], dict[str, Any]], str]] = {
    "historical -> current": ("6.1:clock_drift", lambda e: {**e, "category": "CURRENT"}, "E2"),
    "simulated -> observed": ("6.1:fpga_lut4", lambda e: {**e, "category": "OBSERVED"}, "E2"),
    "unknown -> measured": ("6.1:isa_board_unknown", lambda e: {
        **e, "status": "MEASURED", "source_kind": "historical_board_evidence"}, "E3"),
    "incomplete provenance -> verified": ("6.1:hdmi", lambda e: {
        **e, "verification": "verified"}, "E4"),
    "live flag without live source": ("6.3:current-state", lambda e: {
        **e, "status": "LIVE", "source_kind": "live"}, "E5"),
    "a fifth kind": ("6.1:board", lambda e: {**e, "category": "HISTORY"}, "E1"),
}


@pytest.mark.parametrize("name", ENTRY_SABOTAGES)
def test_each_entry_sabotage_turns_its_check_red(name: str) -> None:
    cid, sabotage, want = ENTRY_SABOTAGES[name]
    ctx, obj = hs.context(), _objects(MODEL)[cid]
    assert hs.check_entry(_entry(cid), obj, ctx) == []
    failed = [f["check"] for f in hs.check_entry(sabotage(_entry(cid)), obj, ctx)]
    assert want in failed, (name, failed)


def _answer(query: str) -> dict[str, Any]:
    return copy.deepcopy(next(a for a in MODEL["contract"] if a["query"] == query))


ANSWER_SABOTAGES: dict[str, tuple[str, Callable[[dict[str, Any]], dict[str, Any]], str]] = {
    "current query falls back to old run": ("hardware current program", lambda a: {
        **a, "state": "MEASURED", "basis": ["6.1:bitstream_last_measured"],
        "claims": ["6.1:bitstream_last_measured"], "reason": None}, "A1"),
    "capability answered by an observation": ("hardware capability FPGA resources", lambda a: {
        **a, "claims": [*a["claims"], "6.1:isa_board"]}, "A2"),
    "headline against the precedence": ("hardware provenance HCPU", lambda a: {
        **a, "state": "SIMULATED", "basis": ["6.1:cpu_pipeline", "6.1:isa_rtl"]}, "A3"),
    "incomplete provenance not named": ("hardware observed peripheral", lambda a: {
        **a, "incomplete_provenance": []}, "A4"),
}


@pytest.mark.parametrize("name", ANSWER_SABOTAGES)
def test_each_answer_sabotage_turns_its_check_red(name: str) -> None:
    query, sabotage, want = ANSWER_SABOTAGES[name]
    ctx = hs.context()
    assert hs.check_answer(_answer(query), MODEL, ctx) == []
    failed = [f["check"] for f in hs.check_answer(sabotage(_answer(query)), MODEL, ctx)]
    assert want in failed, (name, failed)


def test_a_claim_filed_twice_or_not_at_all_is_refused() -> None:
    spec = hs.load()
    spec["claims"]["6.1"]["OBSERVED"].append("clock")
    with pytest.raises(LookupError, match="both"):
        hs.build(hs.context(spec=spec))
    spec = hs.load()
    spec["claims"]["6.1"]["CURRENT"].remove("program_now")
    with pytest.raises(LookupError, match="program_now"):
        hs.build(hs.context(spec=spec))


def test_a_column_counted_from_another_record_is_refused() -> None:
    spec = hs.load()
    spec["observed_opcodes"]["record"] = ("cosmictera-build/parity-board/"
                                          "20260924T104300Z-parity.json")
    with pytest.raises(LookupError, match="counted from"):
        hs.build(hs.context(spec=spec))
