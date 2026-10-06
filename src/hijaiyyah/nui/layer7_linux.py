"""Layer 7 on one Linux service: read cron.service, class it, and start it if it is inactive.

    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7_linux            # read, class, print
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7_linux --record   # and keep the evidence
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7_linux --restart  # RESTART_SERVICE

The owner's decisions of 6 October 2026 (NUI/LAYER7.md, end of 7.4). The
first system Layer 7 looks after outside CosmicTera is a Linux VM: the test
instance cosmictera-layer5-uji, made again for this, and one unit on it,
cron.service. ISOLATE_SERVICE is the first action there and it only reads:

    limactl shell <test instance> -- systemctl status cron.service

-- the one argv, passed by Layer 5's guard before it runs, never a shell, never
sudo. Layer 5 is frozen and is not changed: it classes a unit that is not
active as `collector_error`, because `systemctl status` exits non-zero. The
classes below are Layer 7's own, mapped here and nowhere else.

WHAT IT CLASSES, AND FROM WHAT. Every form was measured on the test VM on
6 October 2026 before a line of this was written, and only a measured form
is given a name:

    Active: active (running)                 exit 0   NO FAULT
    Active: inactive (dead)                  exit 3   UNIT_INACTIVE
    Active: failed (Result: exit-code)       exit 3   UNIT_FAILED
    limactl: instance `<vm>` is stopped      exit 1   VM_UNREACHABLE
    limactl: instance `<vm>` does not exist  exit 1   VM_UNREACHABLE

Inactive and failed both exit 3, so the exit code cannot tell them apart;
the `Active:` line does, and the exit code must agree with it. The `Main PID`
line is not read: after `reset-failed` an inactive unit still shows the
FAILURE of the process that last ran.

WHAT IT DOES NOT SAY. UNIT_FAILED is the one failure that was made and
measured -- ExecStart exiting non-zero with Restart=no. A unit failed by a
start timeout or a signal, a unit activating or deactivating, an `Active:`
line with any other words, an exit code that disagrees with the line, a
stderr that is not empty, a status of another unit: each of these is UNKNOWN
and stops, with what was seen. It is not guessed from how systemd usually
behaves.

ISOLATE_SERVICE ACTS ON NOTHING. `may_act` is false in every one of its
reports. The faults it was measured on were made by the owner's own hand.
The main instance, cosmictera-layer5, is not a target of anything here.

RESTART_SERVICE (owner, 6 October 2026) is the one action, and it is narrow:

    limactl shell <test instance> -- sudo systemctl start cron.service

-- that argv whole, built here and taken from no input. It runs only for a
unit ISOLATE_SERVICE has just read as UNIT_INACTIVE. UNIT_FAILED is classed
and recorded and NOT restarted: the failure that was measured is a unit whose
start fails, and starting it again mends nothing. VM_UNREACHABLE and UNKNOWN
stop likewise. After each start the unit is read again; success is that
reading -- `Active: active (running)` -- and never the start's exit code. One
fault gets at most the owner's number of starts in all, read from 7.4 and
counted from the records kept, across runs; a fault is one inactive spell,
named by its `since`. If a reading after a start is neither inactive nor
active, it stops there. `systemctl stop`, kill, reboot and every other change
to the VM stay outside what NUI may do.

The evidence of a run -- the report, stdout and stderr -- goes to
~/cosmictera-layer5/linux-service/<time>-isolate/ or <time>-restart/ (the
owner's namespace for it, 6 October 2026), outside the repository and apart
from Layer 5's store. A restart keeps the reading before, each start and the
reading after it, and writes its record after every step. Nothing is started
without a place outside the repository to keep that.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import layer5, layer7
from .repository_index import ROOT

#: The 7.4 row this action stands on, by its name in the contract.
ISOLATE = "Penggolongan gangguan `cron.service` di VM uji Linux (`ISOLATE_SERVICE`)"
#: The one unit the owner named, and the one argv that reads it.
UNIT = "cron.service"
STATUS_ARGV = ("systemctl", "status", UNIT)
#: The owner's three classes of fault, in the order they are looked for.
VM_UNREACHABLE, UNIT_INACTIVE, UNIT_FAILED = "VM_UNREACHABLE", "UNIT_INACTIVE", "UNIT_FAILED"
FAULTS = (VM_UNREACHABLE, UNIT_INACTIVE, UNIT_FAILED)
ISOLATED, NO_FAULT = "FAULT ISOLATED", "NO FAULT"
#: `Active: <state> (<detail>)`, as systemctl status prints it.
ACTIVE_LINE = re.compile(r"^ +Active: (\S+) \(([^)]*)\)", re.M)
#: The measured forms: the state, its detail and the exit code together.
MEASURED = {("active", "running", 0): NO_FAULT,
            ("inactive", "dead", 3): UNIT_INACTIVE,
            ("failed", "Result: exit-code", 3): UNIT_FAILED}
#: limactl's own refusal when the VM is not running or is not there.
UNREACHABLE = re.compile(r'level=fatal msg="instance `([^`]+)` (is stopped|does not exist), run ')
UNREACHABLE_EXIT = 1
#: Where a run's evidence is kept (the owner's namespace, 6 October 2026).
EVIDENCE = "~/cosmictera-layer5/linux-service/"
TIMEOUT_S = 120

Runner = Callable[..., Any]


def instance() -> str:
    """The test VM, by the name Layer 5's spec gives it (R1, K-9)."""
    return str(layer5.load()["host"]["test_instance"])


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read(vm: str, run: Runner = subprocess.run) -> dict[str, Any]:
    """`systemctl status cron.service` on one VM, through Layer 5's guard and
    limactl, and what came back. Nothing is parsed here."""
    argv = list(STATUS_ARGV)
    allowed_by = layer5.guard(argv)
    if not layer5.SAFE_ARG.fullmatch(vm):
        raise layer5.Refused(f"instance name {vm!r} holds a space or a shell character")
    if run is subprocess.run and shutil.which("limactl") is None:
        raise layer5.Refused("limactl is not installed")
    where = layer5.host()
    started = datetime.now(timezone.utc)
    proc = run(["limactl", "shell", vm, "--", *argv], capture_output=True, text=True,
               timeout=TIMEOUT_S, stdin=subprocess.DEVNULL,
               env={**os.environ, "LIMA_HOME": where["lima_home"]})
    return {"vm_name": vm, "argv": argv, "allowed_by": allowed_by,
            "started_utc": started.isoformat(), "exit_code": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr,
            "stdout_sha256": _sha(proc.stdout), "stderr_sha256": _sha(proc.stderr),
            "layer5_outcome": layer5.outcome(proc.returncode, proc.stderr)}


def classify(seen: dict[str, Any]) -> tuple[str, str]:
    """One reading, classed: NO FAULT, one of the three faults, or UNKNOWN --
    and why. Only a form that was measured is given a name."""
    out, err, code, vm = seen["stdout"], seen["stderr"], seen["exit_code"], seen["vm_name"]
    lines = ACTIVE_LINE.findall(out)
    if not lines:
        refused = UNREACHABLE.search(err)
        if refused and refused.group(1) == vm and not out and code == UNREACHABLE_EXIT:
            return VM_UNREACHABLE, f"limactl: instance `{vm}` {refused.group(2)}"
        return layer7.UNKNOWN, (f"no `Active:` line, exit {code}: not a measured form of an "
                                "unreachable VM")
    if len(lines) != 1:
        return layer7.UNKNOWN, f"{len(lines)} `Active:` lines: one unit was asked"
    if f" {UNIT} - " not in out.splitlines()[0]:
        return layer7.UNKNOWN, f"the status is not headed by {UNIT}"
    state, detail = lines[0]
    shown = f"`Active: {state} ({detail})`"
    verdict = MEASURED.get((state, detail, code))
    if verdict is None:
        known = sorted(c for s, d, c in MEASURED if (s, d) == (state, detail))
        if known:
            return layer7.UNKNOWN, f"{shown} with exit {code}, not {known[0]}: they disagree"
        return layer7.UNKNOWN, f"{shown} with exit {code} is not a form that was measured"
    if err:
        return layer7.UNKNOWN, f"{shown} with a stderr that is not empty: not as measured"
    return verdict, f"{shown}, exit {code}"


def isolate(vm: str | None = None, unit: str = UNIT, contract: Path | None = None,
            run: Runner = subprocess.run) -> dict[str, Any]:
    """ISOLATE_SERVICE: the fault of cron.service on the test VM, or none, or
    STOP / REPORT. It reads once and acts on nothing."""
    vm = instance() if vm is None else vm
    status = layer7.authorizations(contract).get(ISOLATE) or "unlisted"
    report: dict[str, Any] = {
        "action": ISOLATE, "authorization": {ISOLATE: status},
        "target": {"vm_name": vm, "unit": unit}, "observation": None,
        "fault": None, "condition": None,
        "may_act": False,
        "may_act_why": "isolating reads and classes; 7.4 opens no action on the VM"}

    def close(decision: str, why: str, **more: Any) -> dict[str, Any]:
        return {**report, **more, "decision": decision, "why": why}

    if status != "AUTHORIZED":
        return close(layer7.STOP, "7.4 does not authorize this row: fail-closed",
                     condition=layer7.UNAUTHORIZED)
    if unit != UNIT:
        return close(layer7.STOP, f"`{unit}` is not the unit this row names, {UNIT}",
                     condition=layer7.UNAUTHORIZED)
    if vm != instance():
        return close(layer7.STOP, f"`{vm}` is not the test instance this row is opened on, "
                                  f"{instance()}", condition=layer7.UNAUTHORIZED)
    try:
        report["observation"] = seen = read(vm, run)
    except layer5.Refused as refused:
        return close(layer7.STOP, f"not read: {refused}", condition=layer7.UNKNOWN)
    except subprocess.TimeoutExpired:
        return close(layer7.STOP, f"no answer within {TIMEOUT_S} s: not a measured form",
                     condition=layer7.UNKNOWN)
    verdict, why = classify(seen)
    if verdict == NO_FAULT:
        return close(NO_FAULT, why)
    if verdict in FAULTS:
        return close(ISOLATED, why, fault=verdict)
    return close(layer7.STOP, why, condition=verdict)


def record(report: dict[str, Any], into: Path | None = None,
           now: datetime | None = None, contract: Path | None = None) -> Path:
    """One report kept as evidence: the report, and the stdout and stderr it
    was classed from, in a directory of its own outside the repository."""
    if layer7.authorizations(contract).get(layer7.RECORD) != "AUTHORIZED":
        raise layer5.Refused("7.4 does not authorize recording evidence")
    base = (into or Path(os.path.expanduser(EVIDENCE))).resolve()
    if base == ROOT.resolve() or ROOT.resolve() in base.parents:
        raise layer5.Refused(f"{base} is inside the repository: evidence is kept outside it")
    at = now or datetime.now(timezone.utc)
    where = base / f"{at.strftime('%Y%m%dT%H%M%SZ')}-isolate"
    where.mkdir(parents=True)
    seen = report.get("observation") or {}
    kept = dict(report)
    if seen:
        (where / "stdout.txt").write_text(seen["stdout"], encoding="utf-8")
        (where / "stderr.txt").write_text(seen["stderr"], encoding="utf-8")
        kept["observation"] = {k: v for k, v in seen.items() if k not in ("stdout", "stderr")}
    (where / "report.json").write_text(
        json.dumps(kept, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return where


#: The 7.4 row the one action stands on (owner, 6 October 2026).
RESTART = "Mulai ulang `cron.service` di VM uji Linux (`RESTART_SERVICE`)"
#: The one argv that acts, whole. Layer 5's guard refuses it and is not asked:
#: it is opened by its own row of 7.4 and by nothing else.
START_ARGV = ("sudo", "systemctl", "start", UNIT)
#: The one fault the owner opened the restart for.
RESTARTABLE = UNIT_INACTIVE
RESTORED, FAILED_RECOVERY = layer7.SUCCESS, "FAILED_RECOVERY"
#: The line that tells one inactive spell from the next: its `since`.
SINCE = re.compile(r"^ +(Active: inactive \(dead\) since [^;\n]+);", re.M)


def attempt_limit(contract: Path | None = None) -> int:
    """How many starts one fault may get, in all: the owner's number, read
    from 7.4 (R1). Not that many retries after a first -- that many attempts."""
    text = (contract or layer7.CONTRACT).read_text(encoding="utf-8")
    found = re.search(r"^Batas percobaan RESTART_SERVICE untuk satu gangguan: (\d+)\b", text,
                      flags=re.M)
    return int(found.group(1)) if found else 0


def fault_id(seen: dict[str, Any]) -> str | None:
    """One inactive spell of the unit on one VM, named by its `since`; None
    when the reading does not carry one."""
    found = SINCE.findall(seen["stdout"])
    return _sha(f"{seen['vm_name']}\n{UNIT}\n{found[0]}") if len(found) == 1 else None


def _brief(report: dict[str, Any]) -> dict[str, Any]:
    """A report without the bytes it was classed from; those are kept as files."""
    seen = report.get("observation")
    return {**report, "observation": None if seen is None else
            {k: v for k, v in seen.items() if k not in ("stdout", "stderr")}}


def _files(base: Path, but: Path | None = None) -> dict[str, str]:
    """Every file already kept under the evidence directory, by its hash."""
    if not base.is_dir():
        return {}
    return {str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(base.rglob("*"))
            if p.is_file() and (but is None or but not in p.parents)}


def spent(base: Path, fault: str) -> int | None:
    """How many starts this fault has already had, counted from the records
    kept; None when a record cannot be read -- then nothing is counted on."""
    total = 0
    for path in sorted(base.glob("*-restart/record.json")):
        try:
            kept = json.loads(path.read_text(encoding="utf-8"))
            if kept["fault_id"] == fault:
                total += len(kept["attempts"])
        except (OSError, ValueError, KeyError, TypeError):
            return None
    return total


def _start(vm: str, run: Runner) -> dict[str, Any]:
    """START_ARGV on the test VM through limactl, once, and what came back.
    The verdict is not here: it is the reading that follows."""
    argv = list(START_ARGV)
    where = layer5.host()
    started = datetime.now(timezone.utc)
    try:
        proc = run(["limactl", "shell", vm, "--", *argv], capture_output=True, text=True,
                   timeout=TIMEOUT_S, stdin=subprocess.DEVNULL,
                   env={**os.environ, "LIMA_HOME": where["lima_home"]})
    except subprocess.TimeoutExpired:
        return {"argv": argv, "started_utc": started.isoformat(), "exit_code": None,
                "stdout": "", "stderr": "", "timed_out_after_s": TIMEOUT_S,
                "stdout_sha256": _sha(""), "stderr_sha256": _sha("")}
    return {"argv": argv, "started_utc": started.isoformat(), "exit_code": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr,
            "stdout_sha256": _sha(proc.stdout), "stderr_sha256": _sha(proc.stderr)}


def _keep(where: Path, name: str, seen: dict[str, Any] | None) -> None:
    if seen is not None:
        (where / f"{name}.stdout.txt").write_text(seen["stdout"], encoding="utf-8")
        (where / f"{name}.stderr.txt").write_text(seen["stderr"], encoding="utf-8")


def restart(vm: str | None = None, unit: str = UNIT, into: Path | None = None,
            contract: Path | None = None, run: Runner = subprocess.run,
            now: datetime | None = None) -> dict[str, Any]:
    """RESTART_SERVICE: for a unit that ISOLATE_SERVICE reads as UNIT_INACTIVE,
    START_ARGV, then the reading again -- at most the owner's number of starts
    for one fault, counted from the records. Success is the reading, never the
    start's exit code. Every other state is classed, recorded and left alone."""
    vm = instance() if vm is None else vm
    table = layer7.authorizations(contract)
    authorization = {name: table.get(name) or "unlisted"
                     for name in (ISOLATE, RESTART, layer7.RECORD)}
    limit = attempt_limit(contract)
    result: dict[str, Any] = {
        "action": RESTART, "authorization": authorization,
        "target": {"vm_name": vm, "unit": unit}, "argv": list(START_ARGV),
        "restartable": RESTARTABLE, "attempt_limit": limit, "before": None,
        "fault": None, "fault_id": None, "attempts_before_this_run": None,
        "attempts": [], "condition": None, "evidence": None}

    def close(decision: str, why: str, **more: Any) -> dict[str, Any]:
        return {**result, **more, "decision": decision, "why": why}

    if set(authorization.values()) != {"AUTHORIZED"}:
        return close(layer7.STOP, "7.4 does not authorize all three rows: fail-closed",
                     condition=layer7.UNAUTHORIZED)
    if limit < 1:
        return close(layer7.STOP, "7.4 names no attempt limit: fail-closed",
                     condition=layer7.UNAUTHORIZED)
    if unit != UNIT:
        return close(layer7.STOP, f"`{unit}` is not the unit this row names, {UNIT}",
                     condition=layer7.UNAUTHORIZED)
    if vm != instance():
        return close(layer7.STOP, f"`{vm}` is not the test instance this row is opened on, "
                                  f"{instance()}", condition=layer7.UNAUTHORIZED)
    base = (into or Path(os.path.expanduser(EVIDENCE))).resolve()
    if base == ROOT.resolve() or ROOT.resolve() in base.parents:
        return close(layer7.STOP, f"{base} is inside the repository: evidence is kept "
                                  "outside it, and nothing runs without a place for it",
                     condition=layer7.UNAUTHORIZED)

    seen = isolate(vm, unit, contract, run)
    result["before"] = _brief(seen)
    if seen["decision"] == layer7.STOP and seen["observation"] is None:
        return close(layer7.STOP, seen["why"], condition=seen["condition"])
    older = _files(base)
    at = now or datetime.now(timezone.utc)
    where = base / f"{at.strftime('%Y%m%dT%H%M%SZ')}-restart"
    where.mkdir(parents=True)
    result["evidence"] = str(where)
    _keep(where, "before", seen["observation"])

    def kept(decision: str, why: str, **more: Any) -> dict[str, Any]:
        done = close(decision, why, **more)
        if _files(base, where) != older:
            done = {**done, "decision": layer7.STOP, "condition": layer7.UNAUTHORIZED,
                    "why": "an older record under the evidence directory changed during the "
                           f"run; before that: {why}"}
        (where / "record.json").write_text(
            json.dumps(done, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return done

    if seen["decision"] == NO_FAULT:
        return kept(NO_FAULT, "the unit is active: nothing to restart")
    if seen["decision"] != ISOLATED:
        return kept(layer7.STOP, seen["why"], condition=seen["condition"])
    result["fault"] = fault = seen["fault"]
    if fault != RESTARTABLE:
        return kept(layer7.STOP, f"{fault}: 7.4 opens the restart for {RESTARTABLE} only; "
                                 "classed and recorded, not restarted",
                    condition=layer7.UNAUTHORIZED)
    result["fault_id"] = this = fault_id(seen["observation"])
    if this is None:
        return kept(layer7.STOP, "the reading names no `since`: this fault cannot be told "
                                 "from another, so its attempts cannot be counted",
                    condition=layer7.UNKNOWN)
    result["attempts_before_this_run"] = had = spent(base, this)
    if had is None:
        return kept(layer7.STOP, "a kept restart record cannot be read: the attempts already "
                                 "made cannot be counted", condition=layer7.UNKNOWN)
    if had >= limit:
        return kept(FAILED_RECOVERY, f"this fault has had its {limit} attempts: no more")

    for n in range(had + 1, limit + 1):
        acted = _start(vm, run)
        after = isolate(vm, unit, contract, run)
        _keep(where, f"attempt-{n}.start", acted)
        _keep(where, f"attempt-{n}.after", after["observation"])
        result["attempts"].append({
            "attempt": n,
            "started": {k: v for k, v in acted.items() if k not in ("stdout", "stderr")},
            "after": _brief(after)})
        if after["decision"] == NO_FAULT:
            return kept(RESTORED, f"after attempt {n} of {limit}: {after['why']}")
        if (after["decision"], after["fault"]) != (ISOLATED, RESTARTABLE):
            return kept(layer7.STOP,
                        f"after attempt {n} the unit is not {RESTARTABLE} and not active "
                        f"({after['fault'] or after['condition']}: {after['why']}): "
                        "not restarted again",
                        condition=after["condition"] or layer7.UNAUTHORIZED)
        kept("IN PROGRESS", f"attempt {n} of {limit}: still {RESTARTABLE}")
    return kept(FAILED_RECOVERY, f"{limit} attempts and the unit is still {RESTARTABLE}")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--restart"]:
        done = restart()
        print(json.dumps(done, indent=1, ensure_ascii=False))
        return 0 if done["decision"] in (RESTORED, NO_FAULT) else 1
    if args not in ([], ["--record"]):
        print((__doc__ or "").split("\n\n")[1])
        return 2
    report = isolate()
    if args:
        report = {**report, "evidence": str(record(report))}
    shown = {**report, "observation": {k: v for k, v in (report["observation"] or {}).items()
                                       if k not in ("stdout", "stderr")} or None}
    print(json.dumps(shown, indent=1, ensure_ascii=False))
    return 0 if report["decision"] == NO_FAULT else 1


if __name__ == "__main__":
    raise SystemExit(main())
