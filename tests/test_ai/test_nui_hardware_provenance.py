"""Layer 6.3's hardware provenance, held to the evidence it points at.

The owner's step 6.3, 27 September 2026: every hardware claim walks back to
its source, source kind, board run, evidence file, observed_at and SHA-256,
and says whether that chain holds. What is held here, on the committed model
and on what the spec builds today:

    each claim is one canonical object, in Layer 5's words -- observed_at and
    evidence_sha256, never a second timestamp or sha256;
    the claims are 6.1's and 6.2's, with the class they gave them;
    the source kind is one of the four 6.2 proved, and nothing is live;
    MEASURED ends on a board run the evidence names, SIMULATED on a design
    or build artefact, UNKNOWN on nothing;
    what the hardware is doing now is UNKNOWN, never the newest run;
    and every check turns red when what it guards is broken (R3).
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import hardware, knowledge  # noqa: E402
from hijaiyyah.nui import hardware_provenance as hp  # noqa: E402
from hijaiyyah.nui import telemetry_sources as ts  # noqa: E402

MODEL = json.loads(hp.MODEL.read_text(encoding="utf-8"))
BOTH = pytest.mark.parametrize("model", [MODEL, json.loads(json.dumps(hp.build()))],
                               ids=["committed", "built"])
INCOMPLETE = {"6.1:hdmi": [6], "6.1:reset_button": [6], "6.2:boot_duration": [1, 6]}


def _claim(model: dict[str, Any], cid: str) -> dict[str, Any]:
    return next(c for c in model["claims"] if c["id"] == cid)


def test_the_provenance_reads_back_exactly() -> None:
    assert hp.verify() == []


def test_the_page_is_drawn_from_the_model() -> None:
    assert hp.PAGE.read_text(encoding="utf-8") == hp.page(MODEL)


@BOTH
def test_every_claim_is_one_canonical_object_in_layer_5s_words(model: dict[str, Any]) -> None:
    fields = hp.load()["fields"]
    owners = ["hardware", "claim", "source_kind", "run_id", "observed_at", "evidence",
              "evidence_sha256", "status"]
    assert all(f in fields for f in owners)
    assert "timestamp" not in fields and "sha256" not in fields and "vm_name" not in fields
    for c in model["claims"]:
        assert list(c) == fields, c["id"]


@BOTH
def test_the_claims_are_6_1s_and_6_2s_with_the_class_they_gave(model: dict[str, Any]) -> None:
    inventory = json.loads(hardware.MODEL.read_text(encoding="utf-8"))
    registry = json.loads(ts.MODEL.read_text(encoding="utf-8"))
    want = {f"6.1:{i['id']}": i["class"] for i in inventory["items"]}
    want |= {f"6.2:{r['field']}": r["status"] for r in registry["registry"]}
    want |= {f"6.2:{s['name']}": s["status"] for s in registry["rtl_signals"]["signals"]}
    want["6.3:current-state"] = "UNKNOWN"
    assert {c["id"]: c["status"] for c in model["claims"]} == want
    assert model["counts"]["claims"] == 68 == 34 + 27 + 6 + 1


@BOTH
def test_the_source_kinds_are_the_four_and_nothing_is_live(model: dict[str, Any]) -> None:
    kinds = {"MEASURED": "historical_board_evidence", "SIMULATED": "simulated",
             "UNKNOWN": "unknown"}
    assert list(hp.load()["source_kinds"]) == list(hp.SOURCE_KINDS)
    for c in model["claims"]:
        assert c["source_kind"] == kinds[c["status"]], c["id"]
    assert model["counts"]["LIVE"] == model["counts"]["live"] == 0
    assert (model["counts"]["MEASURED"], model["counts"]["SIMULATED"],
            model["counts"]["UNKNOWN"]) == (42, 17, 9)


@BOTH
def test_every_check_holds_but_the_three_the_evidence_cannot_date(model: dict[str, Any]) -> None:
    """The three stay MEASURED, as 6.1 and 6.2 class them; their chain is
    reported short, with the evidence's own reason, and not filled."""
    spec, ctx = hp.load(), hp.context()
    whys = {*spec["no_run"].values(), *(r.get("observed_at_why") for r in spec["runs"])}
    for c in model["claims"]:
        failed = hp.check(c, ctx)
        assert failed == c["failed_checks"], c["id"]
        assert [f["check"] for f in failed] == INCOMPLETE.get(c["id"], []), c["id"]
        assert all(f["why"] in whys for f in failed), failed
        assert c["verification"] == ("incomplete" if failed else "verified")
    assert model["counts"]["verified"] == 65 and model["counts"]["incomplete"] == 3


@BOTH
def test_measured_ends_on_a_board_run_the_evidence_names(model: dict[str, Any]) -> None:
    tracked = set(subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                                 text=True, check=True).stdout.split("\n"))
    runs = {r["run_id"]: r for r in model["runs"]}
    for c in model["claims"]:
        if c["status"] != "MEASURED":
            continue
        assert c["evidence"] in tracked and c["evidence"].startswith("cosmictera-build/")
        if c["id"] in INCOMPLETE:
            continue
        run = runs[c["run_id"]]
        assert c["evidence"] in run["evidence"] and c["id"] in run["claims"]
        assert c["observed_at"] == run["observed_at"]


def test_a_record_run_is_named_by_its_own_record() -> None:
    """The board run identity that already exists -- the tool's own id or
    file name -- and never a vm_name; the raw capture is the file its
    manifest hashed."""
    for run in hp.load()["runs"]:
        if run["form"] != "record":
            continue
        record = json.loads((ROOT / run["record"]).read_text(encoding="utf-8"))
        seen = hp.read_run(run)
        rule = run["run_id"]
        assert seen["run_id"] == (record[rule["key"]] if "key" in rule
                                  else Path(run["record"]).stem)
        assert Path(run["record"]).name.startswith(seen["run_id"])
        assert "vm_name" not in record
        assert not hp.VM_RUN.fullmatch(seen["run_id"])
    capture = _claim(MODEL, "6.1:uart")
    manifest = json.loads((ROOT / "cosmictera-build/burn-in/"
                           "20260924T073655Z-burn-in-capture.json").read_text(encoding="utf-8"))
    assert (capture["evidence_sha256"], capture["evidence_bytes"]) == (
        manifest["raw_sha256"], manifest["bytes"])


@BOTH
def test_simulated_ends_on_a_design_or_build_artefact(model: dict[str, Any]) -> None:
    for c in model["claims"]:
        if c["status"] != "SIMULATED":
            continue
        assert c["run_id"] is None and c["observed_at"] is None, c["id"]
        assert c["evidence"].startswith(("rtl/", "facts/")), c["id"]
        assert c["evidence_kind"] in ("rtl", "PNR/build-derived"), c["id"]
    resources = [c for c in model["claims"] if c["evidence_kind"] == "PNR/build-derived"]
    assert [c["id"] for c in resources] == ["6.1:fpga_lut4", "6.1:fpga_dff", "6.1:fpga_bsram",
                                            "6.1:fpga_fmax"]


@BOTH
def test_unknown_stays_unknown_with_nothing_behind_it(model: dict[str, Any]) -> None:
    four = ["anomaly_score", "corruption_score", "state_hash", "last_relocation"]
    for c in model["claims"]:
        if c["status"] == "UNKNOWN":
            assert all(c[f] is None for f in ("run_id", "observed_at", "evidence",
                                               "evidence_lines", "evidence_bytes",
                                               "evidence_sha256")), c["id"]
            assert c["reason"], c["id"]
    assert all(_claim(model, f"6.2:{f}")["status"] == "UNKNOWN" for f in four)


def test_what_the_hardware_is_doing_now_is_unknown_not_the_newest_run() -> None:
    a = knowledge.query("hardware current-state")
    assert a["PAPAN"] == [] and a["RTL"] == []
    item, = a["NUI"]
    assert item["status"] == "UNKNOWN" and item["provenance"]["run_id"] is None
    assert item["provenance"]["reason"] == "no live hardware telemetry source"
    assert a["unknown"] == ["6.3:current-state: no live hardware telemetry source"]


def test_the_owners_hardware_queries() -> None:
    hcpu = knowledge.query("hardware HCPU")
    cpu, = [i for i in hcpu["PAPAN"] if i["id"] == "6.1:cpu"]
    p = cpu["provenance"]
    assert (p["status"], p["source_kind"], p["verification"]) == (
        "MEASURED", "historical_board_evidence", "verified")
    assert p["run_id"] and p["observed_at"] and p["evidence"] and p["evidence_sha256"]
    fpga = knowledge.query("hardware FPGA resources")
    assert fpga["RTL"] and all(i["provenance"]["evidence_kind"] == "PNR/build-derived"
                               and i["status"] == "SIMULATED" for i in fpga["RTL"])
    pc = knowledge.query("hardware tele_pc")
    item, = pc["RTL"]
    assert (item["status"], item["source_kind"], item["boundary"]) == (
        "SIMULATED", "simulated", ts.SIMULATED)
    for subject in ("FPGA", "clock", "memory", "peripheral", "telemetry"):
        a = knowledge.query(f"hardware {subject}")
        items = [i for d in knowledge.DOMAINS for i in a[d]]
        assert items and all(i["status"] == i["provenance"]["status"] for i in items), subject
        assert not any(i["status"] == "LIVE" for i in items), subject
    assert knowledge.query("hardware nothing-here")["unknown"]


def test_a_registered_live_source_makes_its_claim_live_and_nothing_else(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """LIVE only when access() finds a registered live source: a rule, not
    a label -- and it takes the historical run away rather than mixing."""
    spec = ts.load()
    spec["live_sources"] = ["uptime"]
    monkeypatch.setattr(ts, "load", lambda: spec)
    registry = json.loads(json.dumps(ts.build()))
    model = json.loads(json.dumps(hp.build(hp.context(registry=registry))))
    uptime = _claim(model, "6.2:uptime")
    assert (uptime["status"], uptime["source_kind"], uptime["run_id"], uptime["evidence"],
            uptime["verification"]) == ("LIVE", "live", None, None, "verified")
    assert _claim(model, "6.3:current-state")["status"] == "LIVE"
    assert _claim(model, "6.2:cycle_rate")["source_kind"] == "historical_board_evidence"
    assert model["counts"]["LIVE"] == 2


def test_the_stale_contract_numbers_are_recorded_not_corrected() -> None:
    d = {x["field"]: x for x in MODEL["discrepancies"]}
    assert d["cycle_rate"]["says"] == "649,4" and d["drift"]["says"] == "−3,3"
    assert all(abs(m["value"] - 650.42) < 0.01 for m in d["cycle_rate"]["measured"])
    assert [round(m["value"], 1) for m in d["drift"]["measured"]] == [-3.8, -4.3]
    line = (ROOT / "cosmictera/TELEMETRY.md").read_text(encoding="utf-8").splitlines()
    assert "649,4" in line[d["cycle_rate"]["where"]["line"] - 1]


# -- R3: each check red when what it guards is broken -------------------------------------


def _other_run(c: dict[str, Any]) -> dict[str, Any]:
    c["run_id"] = "20260920T000027Z-jamrah"
    return c


def _to_live(c: dict[str, Any]) -> dict[str, Any]:
    c.update(source_kind="live", status="LIVE", run_id=None, observed_at=None, evidence=None,
             evidence_lines=None, evidence_bytes=None, evidence_sha256=None,
             reason="streaming now")
    return c


SABOTAGES: dict[str, tuple[str, Callable[[dict[str, Any]], dict[str, Any]], int]] = {
    "evidence hash forged": ("6.1:loader", lambda c: {**c, "evidence_sha256": "0" * 64}, 5),
    "evidence size forged": ("6.1:loader", lambda c: {**c, "evidence_bytes": 1}, 4),
    "run_id moved to another source": ("6.1:loader", _other_run, 2),
    "historical -> live": ("6.2:uptime", _to_live, 9),
    "simulated -> measured": ("6.1:fpga_lut4", lambda c: {
        **c, "status": "MEASURED", "source_kind": "historical_board_evidence"}, 10),
    "claim without provenance": ("6.1:cpu", lambda c: {
        **c, "evidence": None, "evidence_bytes": None, "evidence_sha256": None}, 0),
    "unknown filled": ("6.2:state_hash", lambda c: {
        **c, "status": "MEASURED", "source_kind": "historical_board_evidence"}, 11),
    "observed_at moved": ("6.1:cpu", lambda c: {
        **c, "observed_at": "2026-09-24T10:55:00+00:00"}, 6),
    "a second timestamp": ("6.1:cpu", lambda c: {**c, "timestamp": c["observed_at"]}, 0),
    "vm namespace mixed in": ("6.1:cpu", lambda c: {
        **c, "run_id": "20260927T083814Z-collectors"}, 8),
    "evidence not the source's kind": ("6.1:cpu_pipeline", lambda c: {
        **c, "evidence": "cosmictera-build/PAPAN.md"}, 7),
    "evidence file missing": ("6.1:cpu", lambda c: {
        **c, "evidence": "cosmictera-build/parity-board/20990101T000000Z-parity.json"}, 3),
}


@pytest.mark.parametrize("name", SABOTAGES)
def test_each_sabotage_turns_its_check_red(name: str) -> None:
    cid, sabotage, want = SABOTAGES[name]
    ctx = hp.context()
    before = copy.deepcopy(_claim(MODEL, cid))
    assert hp.check(before, ctx) == []
    after = sabotage(copy.deepcopy(before))
    assert want in [f["check"] for f in hp.check(after, ctx)], (name, hp.check(after, ctx))


def test_a_run_that_does_not_carry_the_claim_is_red() -> None:
    """The run a claim names must itself carry it: the one part of check 2
    no other part catches, since today no two runs share an evidence file."""
    ctx = hp.context()
    c = _claim(MODEL, "6.1:loader")
    run = next(r for r in ctx["runs"] if r["run_id"] == c["run_id"])
    run["claims"] = [x for x in run["claims"] if x != c["id"]]
    assert [f["check"] for f in hp.check(c, ctx)] == [2]


def test_an_evidence_file_replaced_is_red(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = hp.context()
    c = _claim(MODEL, "6.1:loader")
    fake = tmp_path / c["evidence"]
    fake.parent.mkdir(parents=True)
    shutil.copy(ROOT / c["evidence"], fake)
    monkeypatch.setattr(hp, "ROOT", tmp_path)
    assert hp.check(c, ctx) == []
    fake.write_text(fake.read_text(encoding="utf-8").replace('"findings": 0', '"findings": 1'),
                    encoding="utf-8")
    assert 5 in [f["check"] for f in hp.check(c, ctx)]


def test_a_claim_moved_to_another_run_in_the_spec_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = hp.load()
    loader, jamrah = spec["runs"][0], spec["runs"][1]
    loader["claims"].remove("6.1:loader")
    jamrah["claims"].append("6.1:loader")
    model = json.loads(json.dumps(hp.build(hp.context(spec=spec))))
    c = _claim(model, "6.1:loader")
    assert c["verification"] == "incomplete" and 2 in [f["check"] for f in c["failed_checks"]]


def test_a_measured_claim_no_run_carries_is_refused() -> None:
    spec = hp.load()
    spec["runs"][0]["claims"].remove("6.1:loader")
    with pytest.raises(LookupError, match=r"6\.1:loader"):
        hp.build(hp.context(spec=spec))
