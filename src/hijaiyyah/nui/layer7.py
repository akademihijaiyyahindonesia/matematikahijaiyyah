"""Layer 7, first implementation: a read-only evaluator of the autonomous-operation contract.

    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7 host <vm_name> <collector> [<run_id>]
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7 hardware <subject>
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7 rtl <module> <name>

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
from datetime import datetime
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
PASS, STOP = "PASS", "STOP / REPORT"
#: The one read the tests of this stage ask for: the 7.4 category, by its name.
READ = "Observasi / read-only"


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
    stops = [{"condition": c["stop"], "precondition": p, "why": c.get("why", c["value"])}
             for p in PRECONDITIONS for c in [found[p]] if "stop" in c]
    return {"action": action, "target": target,
            "preconditions": {p: found[p] for p in PRECONDITIONS},
            "stops": stops, "conditions": sorted({s["condition"] for s in stops}),
            "decision": STOP if stops else PASS,
            "acted": False}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    action = READ
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
    else:
        print(__doc__.split("\n\n")[1])
        return 2
    report = evaluate(target, action)
    print(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    return 0 if report["decision"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
