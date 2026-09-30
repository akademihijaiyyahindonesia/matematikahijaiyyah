"""Layer 7, DECIDE: one contract result becomes one operational decision, and nothing runs.

    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7_decision <result.json> [...]

The owner's order of 30 September 2026, after 7.7 was accepted GREEN
(b7fa5e8): before any mutative action is opened, NUI moves from

    READ -> EVALUATE -> GATE -> DECIDE -> EVIDENCE / REPORT

with DECIDE giving an explicit operational decision and gaining no authority
to execute it. Every candidate action of 7.4 decides one of

    ALLOW            the contract passes the action: read/evidence actions
    DENY             a mutative action, DENIED in 7.4
    STOP / REPORT    UNKNOWN, STALE, NOT_COVERED, KNOWN_DISCREPANCY,
                     UNAUTHORIZED ACTION, AMBIGUOUS TARGET

ALLOW means "passes the contract for the action", never that this module ran
it: running stays with the caller and inside 7.5's authorization boundary.

This module only takes contract results -- what layer7.evaluate() and
layer7.expect() return -- and gives a deterministic decision record:

    target, run_identity, required_action, authorization, preconditions,
    reason, decision, expected_outcome, and record_sha256 over the rest

It runs no command, writes no file, sends no program, touches no board,
restarts nothing, and authorizes nothing: the 7.4 status of the action is
read again from NUI/LAYER7.md, and a result that claims more than 7.4 gives
stops as UNAUTHORIZED ACTION. The decision is derived from the result's own
six preconditions, never from the verdict it carries, and a result whose
verdict disagrees with its preconditions stops as UNKNOWN.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from . import layer7

ALLOW, DENY, STOP = "ALLOW", "DENY", layer7.STOP
#: The fields of a decision record, in order; record_sha256 is over the rest.
FIELDS = ("target", "run_identity", "required_action", "authorization", "preconditions",
          "reason", "decision", "expected_outcome")


def candidates(contract: Path | None = None) -> list[str]:
    """The candidate actions of 7.4, by category, as the contract lists them."""
    return list(layer7.authorizations(contract))


def _run_identity(result: dict[str, Any]) -> dict[str, Any] | None:
    """(vm_name, run_id) for host evidence (K-16): the run the evaluation
    read, or the baseline runs expect() fixed its outcome on. None for a
    target that is no host."""
    target = result.get("target") or {}
    if target.get("kind") != "host":
        return None
    pre = result["preconditions"]
    runs = pre["target identity"].get("run_id") or \
        pre["observation provenance"].get("baseline_runs") or []
    return {"vm_name": target.get("vm_name"),
            "run_id": sorted([runs] if isinstance(runs, str) else runs)}


def _digest(record: dict[str, Any]) -> str:
    """SHA-256 over the record's fields in canonical JSON: sorted keys, no
    spaces, UTF-8."""
    body = {k: record.get(k) for k in FIELDS}
    canon = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _sealed(record: dict[str, Any]) -> dict[str, Any]:
    return {**{k: record[k] for k in FIELDS}, "record_sha256": _digest(record)}


def _unreadable(result: Any, why: str) -> dict[str, Any]:
    target = result.get("target") if isinstance(result, dict) else None
    action = result.get("action") if isinstance(result, dict) else None
    return _sealed({"target": target, "run_identity": None, "required_action": action,
                    "authorization": None, "preconditions": None,
                    "reason": [{"condition": layer7.UNKNOWN, "why": why}],
                    "decision": STOP, "expected_outcome": None})


def decide(result: Any, contract: Path | None = None) -> dict[str, Any]:
    """One contract result -> one decision record. The input is read, never
    changed."""
    pre = result.get("preconditions") if isinstance(result, dict) else None
    if not isinstance(pre, dict) or set(pre) != set(layer7.PRECONDITIONS) \
            or not all(isinstance(c, dict) for c in pre.values()) \
            or "action" not in result or "target" not in result:
        return _unreadable(result, "not a contract result the decision reads: it needs the "
                                   "action, the target and the six preconditions of 7.6")
    action = result["action"]
    status = layer7.authorizations(contract).get(action)
    claimed = pre["authorization"].get("value")
    authorization = {"category": action, "status_in_7_4": status, "result_says": claimed}
    reason = [{"condition": c["stop"], "precondition": p, "why": c.get("why", c.get("value"))}
              for p in layer7.PRECONDITIONS for c in [pre[p]] if "stop" in c]
    held = {"AUTHORIZED": "allowed", "DENIED": "denied"}.get(status or "", "unlisted")
    if claimed != held:
        reason.append({"condition": layer7.UNAUTHORIZED, "precondition": "authorization",
                       "why": f"the result says `{claimed}`, 7.4 holds `{held}`: "
                              "no result authorizes itself"})
    verdict = layer7.STOP if any(c.get("stop") for c in pre.values()) else layer7.PASS
    if result.get("decision") != verdict:
        reason.append({"condition": layer7.UNKNOWN, "precondition": None,
                       "why": f"the result's verdict `{result.get('decision')}` disagrees "
                              f"with its own preconditions, which give `{verdict}`"})
    if status == "DENIED" and claimed == held:
        decision = DENY
    elif reason or status != "AUTHORIZED":
        decision = STOP
    else:
        decision = ALLOW
    expected = result.get("expected")
    return _sealed({
        "target": result["target"], "run_identity": _run_identity(result),
        "required_action": action, "authorization": authorization,
        "preconditions": {p: pre[p].get("value") for p in layer7.PRECONDITIONS},
        "reason": reason, "decision": decision,
        "expected_outcome": ({"new_runs": expected["new_runs"],
                              "outcomes": expected["outcomes"]}
                             if isinstance(expected, dict) and "outcomes" in expected
                             else None)})


def verify(record: dict[str, Any], result: Any,
           contract: Path | None = None) -> list[str]:
    """The fields in which a decision record differs from the one its
    contract result gives, and `record_sha256` when the record no longer
    matches its own digest. Empty when the record is faithful."""
    again = decide(result, contract)
    moved = [k for k in FIELDS if record.get(k) != again[k]]
    if record.get("record_sha256") != _digest(record):
        moved.append("record_sha256")
    return moved


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print(__doc__.split("\n\n")[1])
        return 2
    records = []
    for name in args:
        loaded = json.loads(Path(name).read_text(encoding="utf-8"))
        records += [decide(r) for r in (loaded if isinstance(loaded, list) else [loaded])]
    print(json.dumps(records, indent=1, ensure_ascii=False))
    return 0 if all(r["decision"] == ALLOW for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
