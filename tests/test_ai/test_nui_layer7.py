"""Layer 7's first implementation, held to the owner's GREEN criteria of 30 September 2026.

src/hijaiyyah/nui/layer7.py is a read-only evaluator of the contract in
NUI/LAYER7.md: Layer 5 evidence and the Layer 6 state model, through the six
preconditions of 7.6 and the guards of 7.8, to PASS or STOP / REPORT. The
store here is built in a temporary directory by layer5.record itself, with a
runner that stands in for the VM, so no test depends on a VM or on the clock.
What is held:

    old evidence -> STALE -> rejected; fresh evidence -> current -> the
    preconditions pass, at the spec's own limit, inclusive;
    UNKNOWN, NOT_COVERED, KNOWN_DISCREPANCY, invalid provenance, an
    ambiguous target, and an unauthorized action each stop it, each under its
    own name, never folded into a plain false -- with the owner's mapping of
    30 September 2026: AMBIGUOUS TARGET for (vm_name, run_id) alone, opaque
    state and subsystems without a function NOT_COVERED, and the measured HISAB
    discrepancy KNOWN_DISCREPANCY;
    the 7.4 statuses are read from the contract, and anything unlisted is
    denied;
    and the evaluator acts on nothing: it runs no command and writes no file,
    checked in its source and by making every such path raise while it runs.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import layer5  # noqa: E402
from hijaiyyah.nui import layer7 as l7  # noqa: E402

VM = "cosmictera-layer5"
LIMIT = layer5.load()["freshness"]["stale_after_seconds"]
SPEC = json.loads(l7.RTL_SPEC.read_text(encoding="utf-8"))
LABELS = {l7.UNKNOWN, l7.STALE, l7.NOT_COVERED, l7.KNOWN_DISCREPANCY, l7.INVALID,
          l7.AMBIGUOUS, l7.UNAUTHORIZED}


class _Ran:
    """What the VM answered in the P8 runs: journal refused for permissions,
    docker absent, everything else output."""

    def __init__(self, cmd: list[str]) -> None:
        self.returncode, self.stdout, self.stderr = 0, f"out of {' '.join(cmd[4:])}\n", ""
        if cmd[4] == "journalctl":
            self.returncode, self.stdout = 1, ""
            self.stderr = "No journal files were opened due to insufficient permissions.\n"
        if cmd[4] == "docker":
            self.returncode, self.stdout, self.stderr = 127, "", "docker: command not found\n"


@pytest.fixture()
def run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """One run of the main instance, in a store of its own."""
    store = tmp_path / "observations"
    store.mkdir()
    monkeypatch.setattr(layer5, "store", lambda: store)
    monkeypatch.setattr(layer5.shutil, "which", lambda _: "/opt/homebrew/bin/limactl")
    return layer5.record(VM, run=lambda cmd, **_: _Ran(cmd), into=store)


def _at(run: Path, collector: str, seconds: float) -> datetime:
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    entry = next(e for e in manifest["collectors"] if e["collector"] == collector)
    return datetime.fromisoformat(entry["timestamp"]) + timedelta(seconds=seconds)


def _host(run: Path, collector: str = "processes", seconds: float = 10.0,
          action: str = l7.READ, **target: Any) -> dict[str, Any]:
    t = {"kind": "host", "vm_name": VM, "collector": collector, "run_id": run.name, **target}
    return l7.evaluate(t, action, now=_at(run, collector, seconds))


def _stop(report: dict[str, Any], condition: str) -> bool:
    return report["decision"] == l7.STOP and condition in report["conditions"]


def _section(number: str) -> str:
    text = l7.CONTRACT.read_text(encoding="utf-8")
    return text.split(f"\n## {number} ", 1)[1].split("\n## ", 1)[0]


def test_the_labels_are_the_contracts_own() -> None:
    """The conditions 7.6 lists are the labels the evaluator stops with, and
    7.8 carries the owner's KNOWN_DISCREPANCY beside UNKNOWN and NOT_COVERED."""
    listed = _section("7.6").split("```text\n", 1)[1].split("```", 1)[0]
    assert set(listed.split("\n")) - {""} == LABELS
    assert all(f"**{name}**" in _section("7.8") for name in
               (l7.UNKNOWN, l7.NOT_COVERED, l7.KNOWN_DISCREPANCY))


def test_the_7_4_statuses_are_read_from_the_contract() -> None:
    table = l7.authorizations()
    assert {k for k, v in table.items() if v == "AUTHORIZED"} == {
        "Observasi / read-only", "Evidence, provenance, freshness, delta"}
    assert sum(1 for v in table.values() if v == "DENIED") == 7
    text = l7.CONTRACT.read_text(encoding="utf-8")
    assert all(f"| {k} |" in text for k in table)


def test_old_evidence_is_stale_and_rejected(run: Path) -> None:
    r = _host(run, seconds=LIMIT + 1)
    assert r["conditions"] == [l7.STALE] and r["decision"] == l7.STOP
    assert r["preconditions"]["evidence freshness"]["value"] == "stale"
    assert r["preconditions"]["authorization"]["value"] == "allowed"
    assert r["acted"] is False


def test_fresh_evidence_is_current_and_the_preconditions_pass(run: Path) -> None:
    r = _host(run, seconds=10)
    assert r["decision"] == l7.PASS and r["stops"] == [] and r["acted"] is False
    assert {p: c["value"] for p, c in r["preconditions"].items()} == {
        "target identity": "known", "observation provenance": "valid",
        "evidence freshness": "current", "required state": "known",
        "required rule coverage": "covered", "authorization": "allowed"}


def test_the_limit_is_the_specs_own_and_inclusive(run: Path) -> None:
    assert LIMIT == 300
    assert _host(run, seconds=LIMIT)["decision"] == l7.PASS
    assert _stop(_host(run, seconds=LIMIT + 0.001), l7.STALE)
    assert _stop(_host(run, seconds=-1), l7.STALE)      # a clock that went back


def test_unknown_stops_under_its_own_name(run: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journal = _host(run, collector="journal")
    assert journal["conditions"] == [l7.UNKNOWN]
    assert journal["preconditions"]["required state"]["outcome"] == \
        "unavailable_due_to_permissions"
    assert _host(run, collector="containers")["conditions"] == [l7.UNKNOWN]
    hardware = l7.evaluate({"kind": "hardware", "subject": "board clock"})
    assert hardware["conditions"] == [l7.UNKNOWN]
    assert hardware["preconditions"]["required state"]["why"] == "no live hardware telemetry source"
    assert hardware["preconditions"]["observation provenance"]["value"] == "unknown"
    monkeypatch.setattr(layer5, "observations", lambda c, v: [])
    none = l7.evaluate({"kind": "host", "vm_name": VM, "collector": "processes"})
    assert none["conditions"] == [l7.UNKNOWN]


def test_not_covered_stops_under_its_own_name(run: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    rtl = l7.evaluate({"kind": "rtl", "module": "hcpu", "rule": "fetch_redirect_trap"})
    assert rtl["conditions"] == [l7.NOT_COVERED]
    assert l7.evaluate({"kind": "rtl", "module": "hcpu", "rule": "fetch_latch"})["decision"] \
        == l7.PASS
    spec = json.loads(json.dumps(layer5.load()))
    next(c for c in spec["collectors"] if c["name"] == "processes")["status"] = "usulan"
    monkeypatch.setattr(layer5, "load", lambda: spec)
    assert _host(run)["conditions"] == [l7.NOT_COVERED]


def test_invalid_provenance_stops(run: Path) -> None:
    (run / "raw" / "processes.stdout").write_text("tampered\n", encoding="utf-8")
    r = _host(run)
    assert l7.INVALID in r["conditions"] and r["decision"] == l7.STOP
    assert "SHA-256" in r["preconditions"]["observation provenance"]["why"]


@pytest.mark.parametrize("target", [
    {"kind": "host", "vm_name": "another-vm", "collector": "processes"},
    {"kind": "host", "vm_name": None, "collector": "processes"},
    {"kind": "host", "vm_name": VM, "collector": "no_such_collector"},
    {"kind": "host", "vm_name": VM, "collector": "processes", "run_id": "19700101T000000Z-x"},
])
def test_an_ambiguous_identity_stops(run: Path, target: dict[str, Any]) -> None:
    """(vm_name, run_id) that points at no single piece of evidence. What
    rests on the identity is not evaluated, and says so."""
    r = l7.evaluate(target)
    assert r["decision"] == l7.STOP
    assert r["preconditions"]["target identity"]["stop"] == l7.AMBIGUOUS
    rest = [x for x in r["stops"] if x["precondition"] != "target identity"]
    assert rest and all(x["condition"] == l7.UNKNOWN for x in rest)
    assert all(r["preconditions"][x["precondition"]]["mechanism"].startswith("not evaluated")
               for x in rest)


@pytest.mark.parametrize("target", [
    {"kind": "hardware", "subject": "no such subject"},
    {"kind": "rtl", "module": "hcpu", "rule": "no_such_rule"},
    {"kind": "rtl", "module": "no_such_module", "rule": "reset"},
    {"kind": "rtl", "module": "hcpu_sdio", "rule": "sd_busy"},
    {"kind": "nothing we read"},
])
def test_a_name_that_names_nothing_stops_unknown_never_ambiguous(target: dict[str, Any]) -> None:
    """The owner's fourth row of 7.8: a name that maps to no known object.
    hcpu_sdio is an RTL file the spec does not map to a subsystem, and the
    evaluator does not invent the link from the name."""
    r = l7.evaluate(target)
    assert r["conditions"] == [l7.UNKNOWN] and r["decision"] == l7.STOP
    assert r["preconditions"]["target identity"]["value"] == "unknown"


def _unmodelled_names() -> list[tuple[str, str]]:
    return [(m["name"], name) for m in SPEC["modules"]
            for part in ("opaque", "externals") for name in m.get(part, {})]


def test_opaque_state_and_subsystems_without_a_function_are_not_covered() -> None:
    """Every opaque and external name the spec gives: the target is known,
    its behaviour has no coverage. The HISAB discrepancy is the one exception."""
    discrepant = {k.casefold() for m in SPEC["modules"] for k in m.get("known_discrepancy", {})}
    names = _unmodelled_names()
    assert {n for _, n in names} >= {"ra_stack[]", "register pc di register file",
                                     "guard berregister", "pengendali kartu", "unit trap"}
    for module, name in names:
        r = l7.evaluate({"kind": "rtl", "module": module, "rule": name})
        want = l7.KNOWN_DISCREPANCY if name.casefold() in discrepant else l7.NOT_COVERED
        assert r["conditions"] == [want], (module, name)
        assert all(x["condition"] == want for x in r["stops"]) and len(r["stops"]) == 2
        assert r["preconditions"]["target identity"]["value"] == "known"
        assert r["preconditions"]["required state"]["value"] == "not predicted"


def test_the_hisab_discrepancy_is_known_not_merely_not_covered() -> None:
    hcpu = next(m for m in SPEC["modules"] if m["name"] == "hcpu")
    measured = hcpu["known_discrepancy"]["hisab"]["measured"]
    for module in ("hcpu", "pipeline"):
        r = l7.evaluate({"kind": "rtl", "module": module, "rule": "HISAB"})
        assert r["conditions"] == [l7.KNOWN_DISCREPANCY], module
        coverage = r["preconditions"]["required rule coverage"]
        assert coverage["value"] == "known discrepancy" and coverage["measured"] == measured
        assert {x["precondition"] for x in r["stops"]} == {"required state",
                                                           "required rule coverage"}
    assert measured["edges"] == 13
    authorized = [k for k, v in l7.authorizations().items() if v == "AUTHORIZED"]
    for action in authorized:
        assert l7.evaluate({"kind": "rtl", "module": "hcpu", "rule": "hisab"}, action)[
            "decision"] == l7.STOP


def test_ambiguous_target_comes_from_host_identity_alone() -> None:
    targets = [{"kind": "rtl", "module": m, "rule": n} for m, n in _unmodelled_names()]
    targets += [{"kind": "rtl", "module": "hcpu", "rule": "fetch_redirect_trap"},
                {"kind": "hardware", "subject": "board clock"},
                {"kind": "hardware", "subject": "no such subject"}, {"kind": None}]
    assert all(l7.AMBIGUOUS not in l7.evaluate(t)["conditions"] for t in targets)


def test_an_unauthorized_action_stops_even_on_fresh_evidence(run: Path) -> None:
    denied = [k for k, v in l7.authorizations().items() if v == "DENIED"]
    for action in [*denied, "reconfigure the board", ""]:
        r = _host(run, action=action)
        assert r["conditions"] == [l7.UNAUTHORIZED], action
        assert r["preconditions"]["authorization"]["value"] in ("denied", "unlisted")


def test_every_stop_keeps_its_name_and_its_reason(run: Path) -> None:
    r = _host(run, collector="journal", seconds=LIMIT + 1, action="Restart / recovery")
    assert r["conditions"] == sorted([l7.STALE, l7.UNKNOWN, l7.UNAUTHORIZED])
    for s in r["stops"]:
        assert s["precondition"] in l7.PRECONDITIONS and s["why"]


# -- nothing is acted on ---------------------------------------------------------------------


def test_the_source_calls_no_mutating_mechanism() -> None:
    source = (ROOT / "src/hijaiyyah/nui/layer7.py").read_text(encoding="utf-8")
    code = ast.unparse(ast.parse(source))
    for name in ("subprocess", "os.system", "Popen", "openFPGALoader", "send_program",
                 "caffeinate", "limactl", "record(", "observe(", "write_text", "write_bytes",
                 "mkdir", "unlink", "rmtree", "open("):
        assert name not in code, name
    imported = {n.module or "" for n in ast.walk(ast.parse(source))
                if isinstance(n, ast.ImportFrom)} | {a.name for n in ast.walk(ast.parse(source))
                                                     if isinstance(n, ast.Import)
                                                     for a in n.names}
    assert imported <= {"__future__", "hashlib", "json", "re", "sys", "datetime", "pathlib",
                        "typing", "", "repository_index"}


def _tree(path: Path) -> dict[str, str]:
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob("*")) if p.is_file()}


def test_evaluating_has_no_side_effect(run: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every way of running a command or writing a file raises while the
    evaluator runs over all three kinds of target, and the store is byte for
    byte what it was."""
    def refuse(*_: Any, **__: Any) -> Any:
        raise AssertionError("a side effect was attempted")

    store, contract = run.parent.parent, hashlib.sha256(l7.CONTRACT.read_bytes()).hexdigest()
    before = _tree(store)
    for obj, name in ((subprocess, "run"), (subprocess, "Popen"), (os, "system"),
                      (shutil, "rmtree"), (shutil, "move"), (layer5, "record"),
                      (layer5, "observe"), (Path, "write_text"), (Path, "write_bytes"),
                      (Path, "mkdir"), (Path, "unlink"), (Path, "rename")):
        monkeypatch.setattr(obj, name, refuse)
    reports = [_host(run, collector=c["name"]) for c in layer5.load()["collectors"]]
    reports += [l7.evaluate({"kind": "hardware", "subject": "board clock"}),
                l7.evaluate({"kind": "rtl", "module": "hcpu", "rule": "fetch_latch"}),
                l7.evaluate({"kind": "rtl", "module": "hcpu", "rule": "ra_stack[]"}),
                l7.evaluate({"kind": "rtl", "module": "hcpu", "rule": "HISAB"})]
    monkeypatch.undo()
    assert _tree(store) == before
    assert hashlib.sha256(l7.CONTRACT.read_bytes()).hexdigest() == contract
    assert all(r["acted"] is False for r in reports)


def test_the_command_line_reports_and_acts_on_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    assert l7.main(["rtl", "hcpu", "fetch_latch"]) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == l7.PASS
    assert l7.main(["rtl", "hcpu", "fetch_redirect_trap"]) == 1
    assert json.loads(capsys.readouterr().out)["conditions"] == [l7.NOT_COVERED]
    assert l7.main(["rtl", "hcpu", "register", "pc", "di", "register", "file"]) == 1
    assert json.loads(capsys.readouterr().out)["conditions"] == [l7.NOT_COVERED]
    assert l7.main(["nothing"]) == 2
