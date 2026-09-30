"""Layer 7, first implementation: a read-only evaluator of the autonomous-operation contract.

    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7 host <vm_name> <collector> [<run_id>]
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7 hardware <subject>
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7 rtl <module> <name>
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7 expect <vm_name>
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7 confirm <expected.json>

The owner's order of 30 September 2026, on the contract NUI/LAYER7.md: test
the read/verify/evidence contract against real Layer 5 observations and the
Layer 6 state model before any mutating action is opened. This module is that
test's instrument, and nothing more:

    Layer 5 evidence  +  Layer 6 hardware state
          -> 7.6 preconditions
          -> 7.8 UNKNOWN / NOT_COVERED / STALE guards
          -> PASS or STOP / REPORT
          -> an evidence report

It acts on nothing. It runs no command, starts no collector, writes no file,
and touches no host, board, program, repository or configuration: it reads
the evidence store, the committed models and the contract, and returns a
report. Recording new evidence is layer5.record's, run outside this module
under 7.5's sixth permission. PASS means the preconditions for using an
observation hold -- never that anything was done.

7.7, by the owner's order of 30 September 2026, is validated on that one
AUTHORIZED action and on no other. expect() evaluates its preconditions and
fixes the outcome it must produce before it runs; the caller runs it only on
PASS; confirm() holds the post-action evidence against that outcome:

    PRECONDITION -> expected outcome -> AUTHORIZATION = ALLOWED -> layer5.record
          -> POST-ACTION OBSERVATION -> compare -> SUCCESS or STOP / REPORT

Neither runs the action, and an exit code is one field of the evidence, never
the verdict.

Each of the six preconditions of 7.6 is answered by a mechanism that already
exists, and a failure keeps its own name as a reason to stop -- UNKNOWN,
STALE, NOT_COVERED and KNOWN_DISCREPANCY are never folded into a plain false:

    target identity         known      (vm_name, run_id) K-16, the only identity
                                       AMBIGUOUS TARGET names; hardware_state.select;
                                       the names NUI/spec/rtl_function.json gives
    observation provenance  valid      the manifest check in layer5 (size, SHA-256);
                                       6.3's incomplete provenance; the RTL model's hashes
    evidence freshness      current    layer5.freshness and the spec's limit; LIVE only
                                       for hardware; for the RTL, files unchanged
    required state          known      the collector's outcome class; hardware_state's
                                       answer; the function agreeing with its RTL
    required rule coverage  covered    the collector's contract locked in the spec; the
                                       RTL rule not among those the model does not cover;
                                       opaque state and external results NOT_COVERED, a
                                       measured known discrepancy KNOWN_DISCREPANCY
    authorization           allowed    the 7.4 status table in NUI/LAYER7.md, read, not
                                       copied; anything unlisted is denied (fail-closed)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import hardware_state, layer5
from .repository_index import ROOT

CONTRACT = ROOT / "NUI" / "LAYER7.md"
RTL_MODEL = ROOT / "NUI" / "rtl_function.json"
RTL_SPEC = ROOT / "NUI" / "spec" / "rtl_function.json"
PRECONDITIONS = ("target identity", "observation provenance", "evidence freshness",
                 "required state", "required rule coverage", "authorization")
#: The owner's names for the conditions that force no action (7.6, 7.8).
UNKNOWN, STALE, NOT_COVERED = "UNKNOWN", "STALE", "NOT_COVERED"
KNOWN_DISCREPANCY = "KNOWN_DISCREPANCY"
INVALID, AMBIGUOUS, UNAUTHORIZED = "INVALID PROVENANCE", "AMBIGUOUS TARGET", "UNAUTHORIZED ACTION"
PASS, STOP, SUCCESS = "PASS", "STOP / REPORT", "SUCCESS"
#: The one read the tests of this stage ask for: the 7.4 category, by its name.
READ = "Observasi / read-only"
#: The 7.4 category that 7.5's sixth permission, new evidence written by
#: layer5.record to the store outside the repository (K-11), falls under.
RECORD = "Evidence, provenance, freshness, delta"
#: What no recording of evidence may change: the contract, and the Layer 5
#: spec, VM configuration and code that the action runs on (7.5); the VM's own
#: lima.yaml is added by name. This module is held with them.
PROTECTED = (ROOT / "NUI" / "LAYER7.md", ROOT / "NUI" / "spec" / "layer5_collectors.json",
             ROOT / "NUI" / "spec" / "layer5_lima.yaml",
             ROOT / "src" / "hijaiyyah" / "nui" / "layer5.py",
             ROOT / "src" / "hijaiyyah" / "nui" / "layer7.py")


def authorizations(contract: Path | None = None) -> dict[str, str]:
    """The 7.4 table of NUI/LAYER7.md: each category and its status, read
    from the contract itself (R1), as Layer 5's guard reads its allowlist
    from NUI/LAYERS.md."""
    text = (contract or CONTRACT).read_text(encoding="utf-8")
    section = text.split("## 7.4 Action Contract", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| (.+?) \| .*? \| \*\*(AUTHORIZED|DENIED)\*\* \|$", section, flags=re.M)
    return dict(rows)


def _cond(value: str, mechanism: str, stop: str | None = None, **detail: Any) -> dict[str, Any]:
    return {"value": value, "mechanism": mechanism, **({"stop": stop} if stop else {}), **detail}


def _authorization(action: str, table: dict[str, str]) -> dict[str, Any]:
    status = table.get(action)
    mechanism = "the 7.4 status table of NUI/LAYER7.md"
    if status == "AUTHORIZED":
        return _cond("allowed", mechanism, category=action)
    return _cond("denied" if status == "DENIED" else "unlisted", mechanism, UNAUTHORIZED,
                 category=action,
                 why=f"`{action}` is {status or 'not in the table'}: fail-closed")


def _host(vm_name: Any, collector: Any, run_id: Any, now: datetime | None) -> dict[str, Any]:
    """The five evidence preconditions for one Layer 5 observation."""
    spec = layer5.load()
    names = {c["name"]: c for c in spec["collectors"]}
    vms = {spec["host"]["instance"], spec["host"]["test_instance"]}
    k16 = "(vm_name, run_id), K-16"
    if vm_name not in vms or collector not in names:
        why = (f"`{vm_name}` is not a VM the Layer 5 spec names" if vm_name not in vms
               else f"`{collector}` is not a collector of the Layer 5 spec")
        return {"target identity": _cond("unknown", k16, AMBIGUOUS, why=why)}
    seen = layer5.observations(collector, vm_name)
    if run_id is not None:
        seen = [s for s in seen if s["run_id"] == run_id]
        if len(seen) != 1:
            return {"target identity": _cond("unknown", k16, AMBIGUOUS,
                                             why=f"{len(seen)} observations are run {run_id}")}
    out = {"target identity": _cond("known", k16, vm_name=vm_name, collector=collector)}
    if not seen:
        why = f"no observation of {collector} on {vm_name} (K-14)"
        for p in ("observation provenance", "evidence freshness", "required state"):
            out[p] = _cond("unknown", "layer5.observations", UNKNOWN, why=why)
    else:
        obs = seen[0]
        out["target identity"]["run_id"] = obs["run_id"]
        manifest = "the manifest check of layer5: VM, run, size and SHA-256"
        if "rejected" in obs:
            out["observation provenance"] = _cond("invalid", manifest, INVALID,
                                                  why=obs["rejected"])
            for p in ("evidence freshness", "required state"):
                out[p] = _cond("unknown", "layer5.observations", UNKNOWN,
                               why="an observation whose provenance failed says nothing")
        else:
            out["observation provenance"] = _cond(
                "valid", manifest, manifest_path=obs["manifest"],
                **{s: obs[s] for s in ("stdout", "stderr") if s in obs})
            fresh = layer5.freshness(obs["observed_at"], now)
            out["evidence freshness"] = _cond(
                "current" if fresh["freshness"] == "current" else "stale",
                "layer5.freshness and stale_after_seconds in NUI/spec/layer5_collectors.json",
                None if fresh["freshness"] == "current" else STALE,
                observed_at=obs["observed_at"], **fresh)
            status = obs["status"]
            out["required state"] = _cond(
                "known" if status == "PASS" else "unknown",
                "the outcome classes of NUI/spec/layer5_collectors.json (K-13)",
                None if status == "PASS" else UNKNOWN, outcome=status,
                **({} if status == "PASS" else {"why": obs.get("failure") or status}))
    locked = names[collector]["status"] == "ditetapkan"
    out["required rule coverage"] = _cond(
        "covered" if locked else "not covered",
        "the collector's contract status in NUI/spec/layer5_collectors.json",
        None if locked else NOT_COVERED, contract_status=names[collector]["status"])
    return out


def _hardware(subject: str) -> dict[str, Any]:
    """The five evidence preconditions for the hardware now: Layer 6's
    CURRENT answer, which only a LIVE source gives."""
    ctx = hardware_state.context()
    model = json.loads(hardware_state.MODEL.read_text(encoding="utf-8"))
    mechanism = "hardware_state.answer, CURRENT"
    if hardware_state.select(subject, ctx) is None:
        return {"target identity": _cond("unknown", "hardware_state.select", UNKNOWN,
                                         why=f"`{subject}` names no hardware claim")}
    a = hardware_state.answer("current", subject, model, ctx)
    out = {"target identity": _cond("known", "hardware_state.select", subject=subject)}
    bad = [c for c in a["basis"] if c in a["incomplete_provenance"]]
    out["observation provenance"] = (
        _cond("invalid", "6.3 provenance verification", INVALID,
              why=f"incomplete provenance under the answer: {bad}") if bad else
        _cond("unknown", mechanism, UNKNOWN, why=a["reason"]) if a["state"] == "UNKNOWN" else
        _cond("valid", "6.3 provenance verification", basis=a["basis"]))
    live = a["state"] == "LIVE"
    out["evidence freshness"] = (_cond("current", mechanism, state=a["state"]) if live else
                                 _cond("unknown", mechanism, UNKNOWN, state=a["state"],
                                       why=a["reason"] or "only a LIVE source is current"))
    out["required state"] = (_cond("known", mechanism, state=a["state"]) if live else
                             _cond("unknown", mechanism, UNKNOWN, state=a["state"],
                                   why=a["reason"] or "only a LIVE source is current"))
    out["required rule coverage"] = _cond("covered", mechanism, claims=a["claims"])
    return out


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unmodelled(name: str, entry: dict[str, Any],
                spec: dict[str, Any]) -> tuple[str, str, dict[str, Any]] | None:
    """What NUI/spec/rtl_function.json says of a name its function does not
    model: a measured known discrepancy of any function, or opaque state or an
    external result of this one. None when it names none of them."""
    low = name.casefold()
    for mod in spec["modules"]:
        for key, what in mod.get("known_discrepancy", {}).items():
            if low == key.casefold():
                return (KNOWN_DISCREPANCY, f"known_discrepancy.{key} of {mod['name']}",
                        {"why": what["status"], "measured": what["measured"]})
    for key, why in entry.get("opaque", {}).items():
        if low == key.casefold():
            return NOT_COVERED, f"opaque of {entry['name']}", {"why": why}
    for key in entry.get("externals", {}):
        if low == key.casefold():
            return NOT_COVERED, f"externals of {entry['name']}", {"why": entry["externals_why"]}
    return None


def _rtl(module: str, rule: str) -> dict[str, Any]:
    """The five evidence preconditions for one name of one Layer 6 RTL
    function, from the committed model and its spec: a rule and its coverage,
    or the opaque state, external result or known discrepancy the spec names;
    and whether the files it was measured on are still the files."""
    model = json.loads(RTL_MODEL.read_text(encoding="utf-8"))
    spec = json.loads(RTL_SPEC.read_text(encoding="utf-8"))
    m = next((x for x in model["modules"] if x["name"] == module), None)
    entry: dict[str, Any] = next((x for x in spec["modules"] if x["name"] == module), {})
    rules = {r["id"]: r for r in m["rules"]} if m else {}
    unmodelled = None if m is None or rule in rules else _unmodelled(rule, entry, spec)
    if m is None or (rule not in rules and unmodelled is None):
        why = f"`{module}` is not a function of NUI/rtl_function.json" if m is None else \
              (f"`{rule}` names no rule, opaque state, external result or known "
               f"discrepancy of {module}")
        return {"target identity": _cond("unknown", "NUI/rtl_function.json", UNKNOWN, why=why)}
    out = {"target identity": _cond("known", "NUI/rtl_function.json", module=module, rule=rule)}
    held = {m["rtl"]: m["rtl_sha256"], m["bench"]: m["bench_sha256"],
            **m.get("modelled_sha256", {}), **m.get("pinned_sha256", {})}
    moved = sorted(f for f, h in held.items() if _sha(ROOT / f) != h)
    out["observation provenance"] = _cond("valid", "the hashes the model holds (F5)",
                                          files=len(held))
    out["evidence freshness"] = (
        _cond("current", "the hashes the model holds (F5)") if not moved else
        _cond("stale", "the hashes the model holds (F5)", STALE,
              why=f"measured on files that have since changed: {moved}"))
    if unmodelled is not None:
        label, where, detail = unmodelled
        mechanism = f"NUI/spec/rtl_function.json, {where}"
        out["required state"] = _cond("not predicted", mechanism, label, **detail)
        out["required rule coverage"] = _cond(
            "known discrepancy" if label == KNOWN_DISCREPANCY else "not covered",
            mechanism, label, **detail)
        return out
    agrees = not m["one_step_mismatches"] and not m["open_loop_mismatches"]
    out["required state"] = _cond(
        "known" if agrees else "unknown", "the function against its RTL (F1, F2)",
        None if agrees else UNKNOWN,
        **({} if agrees else {"why": "the function differs from its RTL"}))
    covered = rule not in m["not_covered"]
    out["required rule coverage"] = _cond(
        "covered" if covered else "not covered", "the model's not_covered rules",
        None if covered else NOT_COVERED, fired=rules[rule]["fired"],
        **({} if covered else {"why": f"{rule} never ran under {m['bench']}: no oracle"}))
    return out


def evaluate(target: dict[str, Any], action: str = READ, now: datetime | None = None,
             contract: Path | None = None) -> dict[str, Any]:
    """One request against the contract. Every precondition is evaluated and
    reported, and each one that fails names its condition; the decision is
    PASS only when none does. Nothing is acted on either way."""
    kind = target.get("kind")
    if kind == "host":
        found = _host(target.get("vm_name"), target.get("collector"), target.get("run_id"), now)
    elif kind == "hardware":
        found = _hardware(str(target.get("subject", "")))
    elif kind == "rtl":
        found = _rtl(str(target.get("module", "")), str(target.get("rule", "")))
    else:
        found = {"target identity": _cond("unknown", "the kinds this evaluator reads",
                                          UNKNOWN, why=f"no target kind `{kind}`")}
    for p in PRECONDITIONS[1:-1]:
        found.setdefault(p, _cond("unknown", "not evaluated: the target is not identified",
                                  UNKNOWN))
    found["authorization"] = _authorization(action, authorizations(contract))
    found = {p: found[p] for p in PRECONDITIONS}
    stops = _stops(found, "precondition")
    return {"action": action, "target": target, "preconditions": found,
            "stops": stops, "conditions": sorted({s["condition"] for s in stops}),
            "decision": STOP if stops else PASS,
            "acted": False}


def _stops(found: dict[str, dict[str, Any]], key: str) -> list[dict[str, Any]]:
    return [{"condition": c["stop"], key: p, "why": c.get("why", c["value"])}
            for p, c in found.items() if "stop" in c]


def _store_files() -> dict[str, str]:
    """Every file of the K-11 evidence store, by SHA-256."""
    base = layer5.store()
    return {str(f.relative_to(base)): _sha(f) for f in sorted(base.rglob("*"))
            if f.is_file()} if base.is_dir() else {}


def _store_runs() -> list[str]:
    """Every collector run in the store: <vm_name>/<run_id> (K-16), or
    <run_id> for the runs frozen before K-16."""
    base = layer5.store()
    runs: list[str] = []
    for d in sorted(base.iterdir()) if base.is_dir() else []:
        if d.is_dir() and layer5.RUN.fullmatch(d.name):
            runs.append(d.name)
        elif d.is_dir():
            runs += [f"{d.name}/{r.name}" for r in sorted(d.iterdir())
                     if r.is_dir() and layer5.RUN.fullmatch(r.name)]
    return runs


def _protected(vm_name: str) -> dict[str, str | None]:
    paths = [*PROTECTED, Path(layer5.host()["lima_home"]) / vm_name / "lima.yaml"]
    return {str(f): _sha(f) if f.is_file() else None for f in paths}


def expect(vm_name: str, action: str = RECORD, now: datetime | None = None,
           contract: Path | None = None) -> dict[str, Any]:
    """7.6 and 7.7 before an action that records evidence of one VM: its six
    preconditions, and the outcome it must produce, fixed before it runs. The
    baseline is the newest observation of each collector on this VM (K-16);
    the expected outcome is that observation's outcome class, so the
    collectors that succeeded must stay PASS and the others keep theirs. Reads
    only: the action is the caller's, and only on PASS."""
    decided_at = now or datetime.now(timezone.utc)
    spec = layer5.load()
    k16 = "(vm_name, run_id), K-16"
    found: dict[str, dict[str, Any]] = {}
    outcomes: dict[str, str] = {}
    if vm_name not in {spec["host"]["instance"], spec["host"]["test_instance"]}:
        found["target identity"] = _cond("unknown", k16, AMBIGUOUS,
                                         why=f"`{vm_name}` is not a VM the Layer 5 spec names")
    else:
        found["target identity"] = _cond("known", k16, vm_name=vm_name)
        base = {c["name"]: layer5.latest(c["name"], vm_name) for c in spec["collectors"]}
        missing = sorted(c for c, o in base.items() if o is None)
        rejected = {c: o["rejected"] for c, o in base.items() if o and "rejected" in o}
        manifest = "the manifest check of layer5: VM, run, size and SHA-256"
        if missing or rejected:
            found["observation provenance"] = (
                _cond("unknown", "layer5.latest", UNKNOWN,
                      why=f"no baseline observation of {missing} on {vm_name} (K-14)")
                if missing else
                _cond("invalid", manifest, INVALID, why=f"baseline rejected: {rejected}"))
        else:
            seen = {c: o for c, o in base.items() if o is not None}
            found["observation provenance"] = _cond(
                "valid", manifest, baseline_runs=sorted({o["run_id"] for o in seen.values()}))
            ages = {c: layer5.freshness(o["observed_at"], decided_at) for c, o in seen.items()}
            stale = sorted(c for c, f in ages.items() if f["freshness"] != "current")
            found["evidence freshness"] = _cond(
                "stale" if stale else "current",
                "layer5.freshness and stale_after_seconds in NUI/spec/layer5_collectors.json",
                STALE if stale else None,
                age_seconds=max(f["age_seconds"] for f in ages.values()),
                **({"why": f"baseline not current: {stale}"} if stale else {}))
            classes = {r["status"] for r in spec["outcomes"]["classes"]}
            loose = {c: o["status"] for c, o in seen.items() if o["status"] not in classes}
            outcomes = {c: o["status"] for c, o in seen.items()}
            found["required state"] = _cond(
                "unknown" if loose else "known",
                "the outcome classes of NUI/spec/layer5_collectors.json (K-13)",
                UNKNOWN if loose else None,
                **({"why": f"no outcome class to expect: {loose}"} if loose else {}))
        unlocked = sorted(c["name"] for c in spec["collectors"] if c["status"] != "ditetapkan")
        found["required rule coverage"] = _cond(
            "not covered" if unlocked else "covered",
            "the collectors' contract status in NUI/spec/layer5_collectors.json",
            NOT_COVERED if unlocked else None,
            **({"why": f"contract not locked: {unlocked}"} if unlocked else {}))
    for p in PRECONDITIONS[1:-1]:
        found.setdefault(p, _cond("unknown", "not evaluated: the target is not identified",
                                  UNKNOWN))
    found["authorization"] = _authorization(action, authorizations(contract))
    found = {p: found[p] for p in PRECONDITIONS}
    stops = _stops(found, "precondition")
    known = found["target identity"]["value"] == "known"
    return {"action": action, "target": {"kind": "host", "vm_name": vm_name},
            "decided_at": decided_at.isoformat(), "preconditions": found,
            "stops": stops, "conditions": sorted({s["condition"] for s in stops}),
            "decision": STOP if stops else PASS,
            "expected": {"new_runs": 1, "outcomes": outcomes,
                         "runs_before": _store_runs(),
                         "store_before": _store_files(),
                         "protected_before": _protected(vm_name) if known else {}},
            "acted": False}


CHECKS = ("new run_id", "manifest hash", "evidence read back", "provenance", "outcome",
          "freshness", "no change outside the evidence store")


def confirm(expected: dict[str, Any], now: datetime | None = None,
            contract: Path | None = None) -> dict[str, Any]:
    """7.7 after the action: the post-action evidence held against the outcome
    expect() fixed before it. SUCCESS only when every item is found: one new
    run_id of this VM, its manifest and hashes, every collector read back with
    valid provenance and its expected outcome, evidence timed after the
    decision and still current, and no change outside the evidence store but
    the new run. Anything else is STOP / REPORT, each under its own name."""
    now = now or datetime.now(timezone.utc)
    vm, want = expected["target"]["vm_name"], expected["expected"]
    new = sorted(set(_store_runs()) - set(want["runs_before"]))
    base = {"action": expected["action"], "target": dict(expected["target"]),
            "decided_at": expected["decided_at"], "confirmed_at": now.isoformat()}
    found: dict[str, dict[str, Any]] = {}
    if expected["decision"] != PASS:
        found["new run_id"] = _cond(
            "no action expected", "the preconditions expect() evaluated",
            UNAUTHORIZED if new else UNKNOWN,
            why=f"the preconditions stopped the action {expected['conditions']}"
                + (f", yet {new} appeared" if new else ": there is nothing to confirm"))
    authorized = _authorization(expected["action"], authorizations(contract))
    if "stop" in authorized:
        found["authorization"] = authorized
    mine, others = [r for r in new if r.startswith(f"{vm}/")], [r for r in new
                                                                if not r.startswith(f"{vm}/")]
    if not found:
        found["new run_id"] = (
            _cond("another target", "the store's runs before and after", AMBIGUOUS,
                  why=f"new runs outside {vm}: {others}") if others else
            _cond("not found", "the store's runs before and after", UNKNOWN,
                  why=f"no new run of {vm}: the expected result is not there") if not mine else
            _cond("ambiguous", "the store's runs before and after", AMBIGUOUS,
                  why=f"{len(mine)} new runs of {vm}: {mine}") if len(mine) > 1 else
            _cond("new", "the store's runs before and after", run=mine[0]))
    if "stop" not in found["new run_id"] and "authorization" not in found:
        run_id = mine[0].split("/", 1)[1]
        base["target"]["run_id"] = run_id
        found.update(_post_action(vm, run_id, want, expected["decided_at"], now))
    found["no change outside the evidence store"] = _outside(vm, new, want)
    for c in CHECKS:
        found.setdefault(c, _cond("unknown", "not evaluated: no single new run to read", UNKNOWN))
    stops = _stops(found, "check")
    return {**base, "checks": found, "stops": stops,
            "conditions": sorted({s["condition"] for s in stops}),
            "decision": STOP if stops else SUCCESS, "acted": False}


def _post_action(vm: str, run_id: str, want: dict[str, Any], decided_at: str,
                 now: datetime) -> dict[str, dict[str, Any]]:
    """The one new run, item by item, through layer5's own verification."""
    out: dict[str, dict[str, Any]] = {}
    path = layer5.store() / vm / run_id / "manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        hashed = all(e.get("failure") or all(e.get("evidence", {}).get(s, {}).get("sha256")
                                             for s in ("stdout", "stderr"))
                     for e in manifest.get("collectors", []))
        out["manifest hash"] = (
            _cond("present", "manifest.json of the new run", sha256=_sha(path)) if hashed else
            _cond("missing", "manifest.json of the new run", INVALID,
                  why="an entry carries no SHA-256 for its evidence"))
    except (OSError, ValueError) as why:
        out["manifest hash"] = _cond("unreadable", "manifest.json of the new run", INVALID,
                                     why=f"{type(why).__name__}: {why}")
    seen = {c: [o for o in layer5.observations(c, vm) if o["run_id"] == run_id]
            for c in want["outcomes"]}
    missing = sorted(c for c, o in seen.items() if len(o) != 1)
    got = {c: o[0] for c, o in seen.items() if len(o) == 1}
    rejected = {c: o["rejected"] for c, o in got.items() if "rejected" in o}
    valid = {c: o for c, o in got.items() if "rejected" not in o}
    differs = {c: {"expected": want["outcomes"][c], "observed": o["status"]}
               for c, o in valid.items() if o["status"] != want["outcomes"][c]}
    early = sorted(c for c, o in valid.items()
                   if datetime.fromisoformat(o["observed_at"]) < datetime.fromisoformat(decided_at))
    stale = sorted(c for c, o in valid.items()
                   if layer5.freshness(o["observed_at"], now)["freshness"] != "current")
    mech = "layer5.observations, (vm_name, run_id)"
    out["evidence read back"] = (
        _cond("missing", mech, UNKNOWN, why=f"not read back from {run_id}: {missing}")
        if missing else _cond("read", mech, collectors=len(got)))
    out["provenance"] = (
        _cond("invalid", "the manifest check of layer5: VM, run, size and SHA-256", INVALID,
              why=f"rejected: {rejected}") if rejected else
        _cond("valid", "the manifest check of layer5: VM, run, size and SHA-256"))
    out["outcome"] = (
        _cond("differs", "the outcome fixed before the action", KNOWN_DISCREPANCY,
              why=f"post-action outcome differs from the one fixed before: {differs}")
        if differs else _cond("as expected", "the outcome fixed before the action",
                              outcomes={c: o["status"] for c, o in valid.items()}))
    out["freshness"] = (
        _cond("inconsistent", "decided_at, and layer5.freshness at confirmation", STALE,
              why=(f"observed before the decision: {early}. " if early else "")
                  + (f"not current: {stale}" if stale else ""))
        if early or stale else
        _cond("consistent", "decided_at, and layer5.freshness at confirmation"))
    return out


def _outside(vm: str, new: list[str], want: dict[str, Any]) -> dict[str, Any]:
    """Only new runs may have come into the store -- whether they are the one
    expected is the new run_id check's -- and nothing the action runs on may
    have changed."""
    after, before = _store_files(), want["store_before"]
    runs = tuple(f"{r}/" for r in new)
    changed = sorted(f for f in before if after.get(f) != before[f])
    added = sorted(f for f in after if f not in before and not (runs and f.startswith(runs)))
    moved = sorted(f for f, h in want["protected_before"].items()
                   if _protected(vm).get(f) != h)
    if changed or added or moved:
        return _cond("changed", "the store and the protected files, before and after",
                     UNAUTHORIZED, why=f"changed or removed {changed}; added outside the "
                                       f"new run {added}; protected files changed {moved}")
    return _cond("unchanged", "the store and the protected files, before and after")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    action: str | None = None
    if "--action" in args:
        i = args.index("--action")
        action, args = args[i + 1], args[:i] + args[i + 2:]
    if args[:1] == ["host"] and len(args) in (3, 4):
        target: dict[str, Any] = {"kind": "host", "vm_name": args[1], "collector": args[2],
                                  "run_id": args[3] if len(args) == 4 else None}
    elif args[:1] == ["hardware"] and len(args) >= 2:
        target = {"kind": "hardware", "subject": " ".join(args[1:])}
    elif args[:1] == ["rtl"] and len(args) >= 3:
        target = {"kind": "rtl", "module": args[1], "rule": " ".join(args[2:])}
    elif args[:1] == ["expect"] and len(args) == 2:
        report = expect(args[1], action or RECORD)
        print(json.dumps(report, indent=1, ensure_ascii=False, default=str))
        return 0 if report["decision"] == PASS else 1
    elif args[:1] == ["confirm"] and len(args) == 2:
        report = confirm(json.loads(Path(args[1]).read_text(encoding="utf-8")))
        print(json.dumps(report, indent=1, ensure_ascii=False, default=str))
        return 0 if report["decision"] == SUCCESS else 1
    else:
        print(__doc__.split("\n\n")[1])
        return 2
    report = evaluate(target, action or READ)
    print(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    return 0 if report["decision"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
