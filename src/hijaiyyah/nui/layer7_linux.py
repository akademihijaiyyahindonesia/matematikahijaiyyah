"""Layer 7 on one Linux service: ISOLATE_SERVICE reads cron.service and classes what it shows.

    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7_linux            # read, class, print
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7_linux --record   # and keep the evidence

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

IT ACTS ON NOTHING. `may_act` is false in every report. Restarting the unit
(RESTART_SERVICE, `sudo systemctl start cron.service`) is not in 7.4 and is
not written here; `systemctl stop`, sudo and every change to the VM stay
outside what NUI may do. The faults this was measured on were made by the
owner's own hand. The main instance, cosmictera-layer5, is not a target of
this action.

The evidence of a run -- the report, stdout and stderr -- goes to
~/cosmictera-layer5/linux-service/<time>-isolate/ (the owner's namespace for
it, 6 October 2026), outside the repository and apart from Layer 5's store.
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


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
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
