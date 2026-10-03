"""Layer 7 DECIDE, held to the owner's order of 30 September 2026.

src/hijaiyyah/nui/layer7_decision.py turns one contract result -- what
layer7.evaluate() or layer7.expect() returns -- into one decision record,
and runs nothing. The owner's table is held row by row:

    fresh + authorized read       -> ALLOW
    fresh + mutative action       -> DENY
    STALE, UNKNOWN, NOT_COVERED, KNOWN_DISCREPANCY, AMBIGUOUS TARGET,
    UNAUTHORIZED ACTION           -> STOP / REPORT

and with it: the same evidence gives the same record; a record changed in its
authorization, reason, target, outcome or decision does not pass verify()
silently; a result that claims more than 7.4 gives is refused; and ALLOW is
never execution -- the module is read with every way to act made to raise.
"""
from __future__ import annotations

import ast
import copy
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
from hijaiyyah.nui import layer7_decision as d  # noqa: E402

VM = "cosmictera-layer5"
LIMIT = layer5.load()["freshness"]["stale_after_seconds"]
DENIED = [k for k, v in l7.authorizations().items() if v == "DENIED"]


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


def _at(run: Path, seconds: float, collector: str = "processes") -> datetime:
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    entry = next(e for e in manifest["collectors"] if e["collector"] == collector)
    return datetime.fromisoformat(entry["timestamp"]) + timedelta(seconds=seconds)


def _host(run: Path, action: str = l7.READ, seconds: float = 10.0,
          collector: str = "processes") -> dict[str, Any]:
    target = {"kind": "host", "vm_name": VM, "collector": collector, "run_id": run.name}
    return l7.evaluate(target, action, now=_at(run, seconds, collector))


def _conditions(record: dict[str, Any]) -> set[str]:
    return {r["condition"] for r in record["reason"]}


# -- the owner's table ---------------------------------------------------------------------------


def test_fresh_and_authorized_read_is_allow(run: Path) -> None:
    r = d.decide(_host(run))
    assert r["decision"] == d.ALLOW and r["reason"] == []
    assert r["authorization"] == {"category": l7.READ, "status_in_7_4": "AUTHORIZED",
                                  "result_says": "allowed"}
    assert r["run_identity"] == {"vm_name": VM, "run_id": [run.name]}
    assert r["expected_outcome"] is None


def test_fresh_evidence_recording_is_allow_with_its_outcome(run: Path) -> None:
    r = d.decide(l7.expect(VM, now=_at(run, 10)))
    assert r["decision"] == d.ALLOW and r["required_action"] == l7.RECORD
    assert r["expected_outcome"]["new_runs"] == 1
    assert r["expected_outcome"]["outcomes"]["journal"] == "unavailable_due_to_permissions"
    assert r["run_identity"] == {"vm_name": VM, "run_id": [run.name]}


@pytest.mark.parametrize("action", DENIED)
def test_fresh_and_mutative_is_deny(run: Path, action: str) -> None:
    r = d.decide(_host(run, action))
    assert r["decision"] == d.DENY
    assert r["authorization"]["status_in_7_4"] == "DENIED"
    assert _conditions(r) == {l7.UNAUTHORIZED}


@pytest.mark.parametrize("result, condition", [
    (lambda run: _host(run, seconds=LIMIT + 1), l7.STALE),
    (lambda run: _host(run, collector="journal"), l7.UNKNOWN),
    (lambda run: l7.evaluate({"kind": "hardware", "subject": "board clock"}), l7.UNKNOWN),
    (lambda run: l7.evaluate({"kind": "rtl", "module": "hcpu",
                              "rule": "fetch_redirect_trap"}), l7.NOT_COVERED),
    (lambda run: l7.evaluate({"kind": "rtl", "module": "hcpu", "rule": "HISAB"}),
     l7.KNOWN_DISCREPANCY),
    (lambda run: l7.evaluate({"kind": "host", "vm_name": "another-vm",
                              "collector": "processes"}), l7.AMBIGUOUS),
    (lambda run: _host(run, "reconfigure the board by another name"), l7.UNAUTHORIZED),
])
def test_every_stop_condition_is_stop_and_report(run: Path, result: Any, condition: str) -> None:
    r = d.decide(result(run))
    assert r["decision"] == d.STOP and condition in _conditions(r)


def test_every_candidate_of_7_4_decides_one_of_three(run: Path) -> None:
    assert d.candidates() == list(l7.authorizations())
    decided = {c: d.decide(_host(run, c))["decision"] for c in d.candidates()}
    assert decided == {c: d.ALLOW if v == "AUTHORIZED" else d.DENY
                       for c, v in l7.authorizations().items()}
    stale = {c: d.decide(_host(run, c, seconds=LIMIT + 1))["decision"] for c in d.candidates()}
    assert stale == {c: d.STOP if v == "AUTHORIZED" else d.DENY
                     for c, v in l7.authorizations().items()}


# -- determinism ---------------------------------------------------------------------------------


def test_the_same_evidence_gives_the_same_record(run: Path) -> None:
    first, second = _host(run), _host(run)
    assert first == second
    a, b = d.decide(first), d.decide(second)
    assert a == b and a["record_sha256"] == b["record_sha256"]
    again = d.decide(json.loads(json.dumps(first, default=str)))
    assert again == a
    assert list(a) == [*d.FIELDS, "record_sha256"]
    canon = json.dumps({k: a[k] for k in d.FIELDS}, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"))
    assert a["record_sha256"] == hashlib.sha256(canon.encode("utf-8")).hexdigest()


def test_deciding_changes_nothing_it_reads(run: Path) -> None:
    result = l7.expect(VM, now=_at(run, 10))
    kept = copy.deepcopy(result)
    d.decide(result)
    assert result == kept


# -- nothing passes silently ---------------------------------------------------------------------


@pytest.mark.parametrize("field, change", [
    ("authorization", lambda r: {**r["authorization"], "status_in_7_4": "AUTHORIZED"}),
    ("reason", lambda r: []),
    ("target", lambda r: {**r["target"], "vm_name": "another-vm"}),
    ("expected_outcome", lambda r: {"new_runs": 1, "outcomes": {"journal": "PASS"}}),
    ("decision", lambda r: d.ALLOW),
    ("run_identity", lambda r: {"vm_name": VM, "run_id": ["19700101T000000Z-collectors"]}),
    ("preconditions", lambda r: {**r["preconditions"], "evidence freshness": "current"}),
])
def test_a_changed_record_does_not_pass_verify(run: Path, field: str, change: Any) -> None:
    result = l7.expect(VM, "Restart / recovery", now=_at(run, LIMIT + 1))
    record = d.decide(result)
    assert d.verify(record, result) == []
    changed = {**record, field: change(record)}
    assert field in d.verify(changed, result)
    assert "record_sha256" in d.verify(changed, result)
    resealed = d._sealed(changed)
    assert d.verify(resealed, result) == [field]


def test_a_result_that_authorizes_itself_is_refused(run: Path) -> None:
    result = copy.deepcopy(_host(run, DENIED[0]))
    auth = result["preconditions"]["authorization"]
    auth.pop("stop")
    auth["value"] = "allowed"
    result["decision"], result["stops"], result["conditions"] = l7.PASS, [], []
    r = d.decide(result)
    assert r["decision"] == d.STOP and _conditions(r) == {l7.UNAUTHORIZED}
    assert "no result authorizes itself" in r["reason"][0]["why"]


def test_a_verdict_that_disagrees_with_its_preconditions_is_refused(run: Path) -> None:
    result = copy.deepcopy(_host(run, seconds=LIMIT + 1))
    result["decision"] = l7.PASS
    r = d.decide(result)
    assert r["decision"] == d.STOP and _conditions(r) == {l7.STALE, l7.UNKNOWN}


@pytest.mark.parametrize("result", [
    None, "PASS", {}, {"action": l7.READ, "target": {}, "preconditions": {}},
    {"action": l7.READ, "target": {}, "preconditions": dict.fromkeys(l7.PRECONDITIONS, "x")},
])
def test_what_is_no_contract_result_is_stop_and_report(result: Any) -> None:
    r = d.decide(result)
    assert r["decision"] == d.STOP and _conditions(r) == {l7.UNKNOWN}


def test_a_post_action_confirmation_is_no_candidate(run: Path) -> None:
    """confirm() judges an action that ran; DECIDE is for one that has not."""
    e = l7.expect(VM, now=_at(run, 10))
    r = d.decide(l7.confirm(e, now=_at(run, 20)))
    assert r["decision"] == d.STOP and _conditions(r) == {l7.UNKNOWN}


# -- ALLOW is not execution ----------------------------------------------------------------------


def test_the_source_calls_no_mutating_mechanism() -> None:
    """No call in the module runs, records, evaluates, writes or removes
    anything -- read from its call nodes, so the docstring may name what it
    reads from -- and no tool of an action is named anywhere in it."""
    source = (ROOT / "src/hijaiyyah/nui/layer7_decision.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {ast.unparse(n.func).rsplit(".", 1)[-1] for n in ast.walk(tree)
              if isinstance(n, ast.Call)}
    assert not called & {"run", "Popen", "system", "record", "observe", "evaluate", "expect",
                         "confirm", "write_text", "write_bytes", "mkdir", "unlink", "rmtree",
                         "rename", "open", "touch"}
    for name in ("subprocess", "openFPGALoader", "send_program", "caffeinate", "limactl"):
        assert name not in source, name
    imported = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
        {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert imported <= {"__future__", "hashlib", "json", "sys", "pathlib", "typing", ""}


def _tree(path: Path) -> dict[str, str]:
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob("*")) if p.is_file()}


def test_deciding_has_no_side_effect(run: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    results = [_host(run, c) for c in d.candidates()] + [l7.expect(VM, now=_at(run, 10))]
    store = run.parent.parent
    before = _tree(store)

    def refuse(*_: Any, **__: Any) -> Any:
        raise AssertionError("a side effect was attempted")

    for obj, name in ((subprocess, "run"), (subprocess, "Popen"), (os, "system"),
                      (shutil, "rmtree"), (layer5, "record"), (layer5, "observe"),
                      (l7, "evaluate"), (l7, "expect"), (l7, "confirm"),
                      (Path, "write_text"), (Path, "write_bytes"), (Path, "mkdir"),
                      (Path, "unlink"), (Path, "rename")):
        monkeypatch.setattr(obj, name, refuse)
    records = [d.decide(r) for r in results]
    monkeypatch.undo()
    assert _tree(store) == before
    # every AUTHORIZED category of 7.4 on fresh evidence, and the expectation
    allowed = sum(1 for v in l7.authorizations().values() if v == "AUTHORIZED") + 1
    assert allowed == 5
    assert [r["decision"] for r in records].count(d.ALLOW) == allowed


def test_the_command_line_decides_and_acts_on_nothing(run: Path, tmp_path: Path,
                                                      capsys: pytest.CaptureFixture[str]) -> None:
    kept = tmp_path / "results.json"
    kept.write_text(json.dumps([_host(run), _host(run, DENIED[0])], default=str),
                    encoding="utf-8")
    assert d.main([str(kept)]) == 1
    assert [r["decision"] for r in json.loads(capsys.readouterr().out)] == [d.ALLOW, d.DENY]
    kept.write_text(json.dumps(_host(run), default=str), encoding="utf-8")
    assert d.main([str(kept)]) == 0
    capsys.readouterr()
    assert d.main([]) == 2
