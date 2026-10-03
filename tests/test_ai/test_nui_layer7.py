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

7.7, by the owner's order of 30 September 2026, on the one AUTHORIZED action
layer5.record: expect() fixes the outcome before it, the test runs it, and
confirm() gives SUCCESS only when the post-action evidence matches -- and
STOP / REPORT for a wrong manifest hash, broken provenance, a different
outcome, stale evidence, a changed or ambiguous target, and a result not
found.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

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
        "Observasi / read-only", "Evidence, provenance, freshness, delta",
        # opened by the owner, 3 October 2026: neither changes the board
        "Pembacaan identitas papan lewat JTAG (`openFPGALoader --detect`)",
        "Isolasi kesalahan slot Portal 8888 (`ISOLATE_FAULT`)",
        # opened by the owner's second decision of 3 October 2026: these four
        # do change the board, within the Portal slot and nowhere else
        "Konfigurasi ulang papan ke SRAM dengan bitstream Portal 8888 yang "
        "SHA-256-nya tercatat",
        "Penulisan UART protokol Portal 8888 sesudah muat ulang pada lari yang sama",
        "Mulai ulang slot Portal 8888 (`RESTART_PORTAL`)",
        "Pemulihan slot Portal 8888 (`RECOVER_PORTAL`)"}
    for general in ("Konfigurasi ulang papan (`openFPGALoader`)", "Restart / recovery",
                    "Isolasi kesalahan", "Mengirim program ke papan"):
        assert table[general] == "DENIED", general
    assert sum(1 for v in table.values() if v == "DENIED") == 7
    text = l7.CONTRACT.read_text(encoding="utf-8")
    assert all(f"| {k} |" in text for k in table)
    # The SEND_PROGRAM proposal (owner, 1 October 2026) sits in 7.4 and grants
    # nothing: it is a hard stop, and sending a program stays DENIED.
    assert table["Mengirim program ke papan"] == "DENIED"
    head = "STATUS: HARD STOP — STOP / REPORT (pemilik, 1 Oktober 2026)\nAuthorization: DENIED"
    assert head in _section("7.4")
    assert "STATUS: PROPOSED" not in _section("7.4")


def test_the_readiness_discovery_rests_on_a_silent_loader() -> None:
    """The readiness discovery (owner, 1 October 2026) found loader readiness
    not observable: the loader has no output instruction, the MMIO map has no
    TX data register, and the wrapper speaks only after halted. If any of that
    changes, the discovery has to be measured again."""
    loader = (ROOT / "rtl/programs/loader.hasm").read_text(encoding="utf-8")
    code = [line.split(";", 1)[0] for line in loader.splitlines()]
    assert not any(re.search(r"\b(PRINT|EMITS)\b", line) for line in code)
    mmio = (ROOT / "rtl/hcpu_mmio.v").read_text(encoding="utf-8")
    assert "0xFF2  R   UART TX status" in mmio and "TX data" not in mmio
    wrapper = (ROOT / "rtl/fpga/gowin/hcpu_gowin_top.v").read_text(encoding="utf-8")
    assert "assign uart_txd = report_armed ? report_txd : core_txd;" in wrapper
    assert "end else if (halted_out && !report_armed) begin" in wrapper
    assert "STATUS: HARD STOP" in _section("7.4")


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
    {"kind": "host", "vm_name": VM, "collector": "no_such_collector"},
    {"kind": "nothing we read"},
])
def test_a_name_that_names_nothing_stops_unknown_never_ambiguous(target: dict[str, Any]) -> None:
    """The owner's fourth row of 7.8: a name that maps to no known object.
    hcpu_sdio is an RTL file the spec does not map to a subsystem, and the
    evaluator does not invent the link from the name. A collector the Layer 5
    spec does not name is one too (the owner, 3 October 2026); an unknown VM
    or run_id stays AMBIGUOUS TARGET."""
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


# -- 7.7: the post-action success of layer5.record ----------------------------------------------

T0 = datetime(2026, 9, 30, 6, 0, tzinfo=timezone.utc)
SEC = timedelta(seconds=1)
OUTCOMES = {"journal": "unavailable_due_to_permissions",
            "containers": "unavailable_command_absent"}


@pytest.fixture()
def act(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """A store of its own, a stand-in VM, and a clock the test moves. The
    baseline run is recorded at T0; the action is whatever the test records
    after expect() has fixed its outcome."""
    store = tmp_path / "observations"
    store.mkdir()
    clock = [T0]

    class Fixed(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
            return clock[0]

    monkeypatch.setattr(layer5, "store", lambda: store)
    monkeypatch.setattr(layer5.shutil, "which", lambda _: "/opt/homebrew/bin/limactl")
    monkeypatch.setattr(layer5, "datetime", Fixed)

    def record(at: datetime, vm: str = VM,
               runner: Callable[[list[str]], Any] = _Ran) -> Path:
        clock[0] = at
        return layer5.record(vm, run=lambda cmd, **_: runner(cmd), into=store)

    record(T0)
    return SimpleNamespace(store=store, record=record, clock=clock, Fixed=Fixed)


def _check(report: dict[str, Any], condition: str) -> bool:
    return report["decision"] == l7.STOP and condition in report["conditions"]


def _run_stop(report: dict[str, Any], condition: str) -> bool:
    """The new run_id check stops under `condition`, and every other stop is a
    check that rests on that run and says it was not evaluated."""
    rest = [x for x in report["stops"] if x["check"] != "new run_id"]
    return (report["checks"]["new run_id"].get("stop") == condition
            and all(x["condition"] == l7.UNKNOWN and report["checks"][x["check"]][
                "mechanism"].startswith("not evaluated") for x in rest))


def test_7_7_success_is_the_outcome_fixed_before_the_action(act: SimpleNamespace) -> None:
    e = l7.expect(VM, now=T0 + 5 * SEC)
    assert e["decision"] == l7.PASS and e["action"] == l7.RECORD and e["acted"] is False
    assert e["preconditions"]["authorization"]["value"] == "allowed"
    want = {c["name"]: OUTCOMES.get(c["name"], "PASS") for c in layer5.load()["collectors"]}
    assert e["expected"]["outcomes"] == want and e["expected"]["new_runs"] == 1
    run = act.record(T0 + 10 * SEC)
    r = l7.confirm(e, now=T0 + 20 * SEC)
    assert r["decision"] == l7.SUCCESS and r["stops"] == [] and r["acted"] is False
    assert r["target"]["run_id"] == run.name
    assert list(r["checks"]) == list(l7.CHECKS)
    assert r["checks"]["manifest hash"]["sha256"] == hashlib.sha256(
        (run / "manifest.json").read_bytes()).hexdigest()
    assert r["checks"]["outcome"]["outcomes"] == want


def test_an_exit_code_of_zero_is_not_the_verdict(act: SimpleNamespace) -> None:
    """Every collector exits 0, and the journal, fixed as refused, comes back
    PASS: the outcome differs from the one fixed, so STOP."""
    class AllZero(_Ran):
        def __init__(self, cmd: list[str]) -> None:
            super().__init__(cmd)
            self.returncode, self.stderr = 0, ""

    e = l7.expect(VM, now=T0 + 5 * SEC)
    act.record(T0 + 10 * SEC, runner=AllZero)
    r = l7.confirm(e, now=T0 + 20 * SEC)
    assert r["conditions"] == [l7.KNOWN_DISCREPANCY]
    assert "journal" in r["checks"]["outcome"]["why"]


def test_a_wrong_manifest_hash_stops(act: SimpleNamespace) -> None:
    e = l7.expect(VM, now=T0 + 5 * SEC)
    run = act.record(T0 + 10 * SEC)
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    manifest["collectors"][1]["evidence"]["stdout"]["sha256"] = "0" * 64
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    r = l7.confirm(e, now=T0 + 20 * SEC)
    assert _check(r, l7.INVALID) and r["checks"]["provenance"]["value"] == "invalid"


def test_broken_provenance_stops(act: SimpleNamespace) -> None:
    e = l7.expect(VM, now=T0 + 5 * SEC)
    run = act.record(T0 + 10 * SEC)
    (run / "raw" / "routes.stdout").write_text("tampered\n", encoding="utf-8")
    assert _check(l7.confirm(e, now=T0 + 20 * SEC), l7.INVALID)
    (run / "raw" / "routes.stdout").unlink()
    assert _check(l7.confirm(e, now=T0 + 20 * SEC), l7.INVALID)


def test_an_outcome_that_does_not_match_stops(act: SimpleNamespace) -> None:
    class Broken(_Ran):
        def __init__(self, cmd: list[str]) -> None:
            super().__init__(cmd)
            if cmd[4] == "ps":
                self.returncode, self.stdout, self.stderr = 1, "", "ps: broken\n"

    e = l7.expect(VM, now=T0 + 5 * SEC)
    act.record(T0 + 10 * SEC, runner=Broken)
    r = l7.confirm(e, now=T0 + 20 * SEC)
    assert r["conditions"] == [l7.KNOWN_DISCREPANCY]
    assert "processes" in r["checks"]["outcome"]["why"]


def test_stale_post_action_evidence_stops(act: SimpleNamespace) -> None:
    e = l7.expect(VM, now=T0 + 5 * SEC)
    act.record(T0 + 10 * SEC)
    assert l7.confirm(e, now=T0 + 10 * SEC + LIMIT * SEC)["decision"] == l7.SUCCESS
    assert l7.confirm(e, now=T0 + 11 * SEC + LIMIT * SEC)["conditions"] == [l7.STALE]


def test_evidence_timed_before_the_decision_is_not_post_action(act: SimpleNamespace) -> None:
    e = l7.expect(VM, now=T0 + 15 * SEC)
    act.record(T0 + 10 * SEC)
    r = l7.confirm(e, now=T0 + 20 * SEC)
    assert r["conditions"] == [l7.STALE]
    assert "before the decision" in r["checks"]["freshness"]["why"]


def test_a_changed_or_ambiguous_target_stops(act: SimpleNamespace) -> None:
    e = l7.expect(VM, now=T0 + 5 * SEC)
    other = layer5.load()["host"]["test_instance"]
    act.record(T0 + 10 * SEC, vm=other)
    r = l7.confirm(e, now=T0 + 20 * SEC)
    assert _run_stop(r, l7.AMBIGUOUS) and other in r["checks"]["new run_id"]["why"]
    e = l7.expect(VM, now=T0 + 25 * SEC)
    act.record(T0 + 30 * SEC)
    act.record(T0 + 31 * SEC)
    r = l7.confirm(e, now=T0 + 40 * SEC)
    assert _run_stop(r, l7.AMBIGUOUS) and "2 new runs" in r["checks"]["new run_id"]["why"]


def test_an_expected_result_not_found_stops(act: SimpleNamespace) -> None:
    e = l7.expect(VM, now=T0 + 5 * SEC)
    r = l7.confirm(e, now=T0 + 20 * SEC)
    assert _run_stop(r, l7.UNKNOWN) and "not there" in r["checks"]["new run_id"]["why"]


def test_a_change_outside_the_evidence_store_stops(act: SimpleNamespace, tmp_path: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    e = l7.expect(VM, now=T0 + 5 * SEC)
    act.record(T0 + 10 * SEC)
    old = next((act.store / VM).iterdir()) / "raw" / "mounts.stdout"
    assert old.parent.parent.name != l7.confirm(e, now=T0 + 20 * SEC)["target"]["run_id"]
    old.write_text("an older run, rewritten\n", encoding="utf-8")
    r = l7.confirm(e, now=T0 + 20 * SEC)
    assert r["conditions"] == [l7.UNAUTHORIZED]
    # A boundary violation, not a functional failure of the action (owner, 30 September 2026):
    # the action's own checks still read as met beside it.
    assert all(r["checks"][c].get("stop") is None for c in l7.CHECKS[:-1])
    assert r["checks"]["outcome"]["value"] == "as expected"
    guarded = tmp_path / "guarded.txt"
    guarded.write_text("before\n", encoding="utf-8")
    monkeypatch.setattr(l7, "PROTECTED", (*l7.PROTECTED, guarded))
    e = l7.expect(VM, now=T0 + 25 * SEC)
    act.record(T0 + 30 * SEC)
    guarded.write_text("after\n", encoding="utf-8")
    r = l7.confirm(e, now=T0 + 40 * SEC)
    assert r["conditions"] == [l7.UNAUTHORIZED] and "guarded.txt" in r["checks"][
        "no change outside the evidence store"]["why"]


def test_what_the_guard_and_decide_read_is_protected() -> None:
    """The owner's ruling of 3 October 2026: close the PROTECTED gap. What the
    Layer 5 guard reads before any command runs -- the allowlist and the
    collector catalog, through usr.py -- and the DECIDE module are held, each
    path taken from the code that reads it, not written here a second time."""
    from hijaiyyah.nui import layer7_decision, usr
    source = (ROOT / "src" / "hijaiyyah" / "nui" / "layer5.py").read_text(encoding="utf-8")
    assert 'usr.load("layer5_catalog")' in source and "usr.allowlist()" in source
    read = {usr.LAYERS, usr.SPEC / "layer5_catalog.json"}
    code = {Path(m.__file__) for m in (layer5, usr, l7, layer7_decision)}
    held = set(l7.PROTECTED)
    assert read | code <= held, sorted(map(str, (read | code) - held))
    assert all(p.is_file() for p in held)
    assert set(l7._protected(VM)) >= {str(p) for p in read | code}


def test_the_preconditions_hold_the_action_back(act: SimpleNamespace) -> None:
    """Before layer5.record may run: a DENIED category, an unknown VM, a
    baseline gone stale, and no baseline at all each stop it."""
    for action in [k for k, v in l7.authorizations().items() if v == "DENIED"]:
        assert l7.expect(VM, action, now=T0 + 5 * SEC)["conditions"] == [l7.UNAUTHORIZED]
    assert l7.AMBIGUOUS in l7.expect("another-vm", now=T0 + 5 * SEC)["conditions"]
    assert l7.expect(VM, now=T0 + (LIMIT + 1) * SEC)["conditions"] == [l7.STALE]
    assert l7.UNKNOWN in l7.expect(layer5.load()["host"]["test_instance"],
                                   now=T0 + 5 * SEC)["conditions"]


def test_a_stopped_expectation_confirms_nothing(act: SimpleNamespace) -> None:
    e = l7.expect(VM, "Restart / recovery", now=T0 + 5 * SEC)
    assert l7.confirm(e, now=T0 + 20 * SEC)["conditions"] == [l7.UNAUTHORIZED, l7.UNKNOWN]
    act.record(T0 + 10 * SEC)
    r = l7.confirm(e, now=T0 + 20 * SEC)
    assert r["decision"] == l7.STOP and "yet" in r["checks"]["new run_id"]["why"]


def test_expect_and_confirm_act_on_nothing(act: SimpleNamespace,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_: Any, **__: Any) -> Any:
        raise AssertionError("a side effect was attempted")

    e = l7.expect(VM, now=T0 + 5 * SEC)
    act.record(T0 + 10 * SEC)
    before = _tree(act.store)
    with monkeypatch.context() as m:
        for obj, name in ((subprocess, "run"), (subprocess, "Popen"), (os, "system"),
                          (shutil, "rmtree"), (layer5, "record"), (layer5, "observe"),
                          (Path, "write_text"), (Path, "write_bytes"), (Path, "mkdir"),
                          (Path, "unlink"), (Path, "rename")):
            m.setattr(obj, name, refuse)
        assert l7.expect(VM, now=T0 + 15 * SEC)["decision"] == l7.PASS
        assert l7.confirm(e, now=T0 + 20 * SEC)["decision"] == l7.SUCCESS
    assert _tree(act.store) == before


def test_the_command_line_expects_and_confirms(act: SimpleNamespace, tmp_path: Path,
                                               monkeypatch: pytest.MonkeyPatch,
                                               capsys: pytest.CaptureFixture[str]) -> None:
    """The real run's path: expect prints the outcome, the caller keeps it
    and runs layer5.record, and confirm reads it back."""
    monkeypatch.setattr(l7, "datetime", act.Fixed)
    assert l7.main(["expect", "another-vm"]) == 1
    capsys.readouterr()
    act.clock[0] = T0 + 5 * SEC
    assert l7.main(["expect", VM]) == 0
    kept = tmp_path / "expected.json"
    kept.write_text(capsys.readouterr().out, encoding="utf-8")
    act.record(T0 + 10 * SEC)
    act.clock[0] = T0 + 20 * SEC
    assert l7.main(["confirm", str(kept)]) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == l7.SUCCESS
    act.clock[0] = T0 + 11 * SEC + LIMIT * SEC
    assert l7.main(["confirm", str(kept)]) == 1
