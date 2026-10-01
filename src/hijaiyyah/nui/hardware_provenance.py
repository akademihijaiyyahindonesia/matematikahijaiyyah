"""Layer 6.3: every hardware claim, walked back to the evidence it stands on.

    PYTHONPATH=src python3 -m hijaiyyah.nui.hardware_provenance --write
    PYTHONPATH=src python3 -m hijaiyyah.nui.hardware_provenance --verify

The owner's step 6.3, 27 September 2026. Not new telemetry: 6.2 proved there
is no live source, so NUI may not claim what the hardware is doing now. What
it may do is say where each thing it does claim comes from, as one chain:

    hardware claim -> source -> source kind -> board run -> evidence file
                   -> observed_at -> sha256 -> verification status

The claims are not written again here. They are the 6.1 inventory's items,
the 6.2 registry's fields and RTL signals, and one question the owner named --
what the hardware is doing now -- read from the committed models. Each becomes
one canonical object in Layer 5's words: `observed_at` and `evidence_sha256`,
never a second `timestamp` or `sha256`. Its source kind is one of the four 6.2
proved, and no other:

    historical_board_evidence   measured on the board and recorded; not flowing
    live                        only when access() finds a registered live source
    simulated                   a design, build or simulation artefact
    unknown                     no valid source

NUI/spec/hardware_provenance.json names which board run carries each MEASURED
claim, and where that run says who it is and when it ran: a record's own id
key or the file name its tool gave it, and its start time; or, for a run only
a page records, the heading of the section that records it and the date the
page gives. Nothing is dated that the evidence does not date, and nothing
without a run is given one: such a claim stays MEASURED, as 6.1 and 6.2 class
it, and its verification says which check it fails and why. Where a run_id
came from is said beside it (the owner, after 6.3 was GREEN): `instrumented`
when a tool wrote it, `non-instrumented/inferred-from-record` when it is a
page's section heading kept exactly as written -- never passed off as a
tool's run id.

Every object is checked against the files themselves -- the owner's ten
checks, plus that the object is canonical and that UNKNOWN stays UNKNOWN --
and a claim that fails a check says which. "What is the hardware doing now"
is answered UNKNOWN, "no live hardware telemetry source", and never by the
newest historical run.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from . import hardware, layer6_addendum, telemetry_sources
from .hardware import _sha
from .repository_index import ROOT

SPEC = ROOT / "NUI" / "spec" / "hardware_provenance.json"
MODEL = ROOT / "NUI" / "hardware_provenance.json"
PAGE = ROOT / "NUI" / "HARDWARE_PROVENANCE.md"
SOURCE_KINDS = ("historical_board_evidence", "live", "simulated", "unknown")
STATUSES = ("MEASURED", "SIMULATED", "UNKNOWN", "LIVE")
STAMP = re.compile(r"^(\d{8}T\d{6}Z)")
#: A Layer 5 run -- evidence from the VM, whose identity is (vm_name, run_id).
VM_RUN = re.compile(r"\d{8}T\d{6}Z-collectors")
BOARD = "cosmictera-build/"
Context = dict[str, Any]


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SPEC.read_text(encoding="utf-8"))
    return data


def _json(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _key(data: Any, dotted: str) -> Any:
    for part in dotted.split("."):
        data = data[part]
    return data


def _day(text: str) -> str:
    """'15 September 2026', as a page writes it, as an ISO date."""
    from .knowledge import MONTHS
    d, month, y = text.split()
    return date(int(y), MONTHS[month], int(d)).isoformat()


def _lines(path: str) -> list[str]:
    return (ROOT / path).read_text(encoding="utf-8").splitlines()


def _section(path: str, heading: str) -> tuple[int, int, str] | None:
    """A Markdown section: its first and last line, 1-based, and its heading
    without the #s -- from the heading to the next of its level or higher,
    lines inside code fences not taken for headings."""
    lines, fenced, heads = _lines(path), False, []
    for n, line in enumerate(lines, 1):
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("#"):
            heads.append((n, len(line) - len(line.lstrip("#")), line))
    rx = re.compile(heading)
    start = next(((n, lv, ln) for n, lv, ln in heads if rx.search(ln)), None)
    if start is None:
        return None
    n, level, line = start
    end = next((m - 1 for m, lv, _ in heads if m > n and lv <= level), len(lines))
    return n, end, line.lstrip("#").strip()


def _hashed(path: str, lines: list[int] | None) -> tuple[int, str]:
    """What an evidence file weighs and hashes to: the whole file, or for a
    page only the lines named -- joined as 6.1 and 6.2 join them."""
    if lines is None:
        data = (ROOT / path).read_bytes()
    else:
        text = _lines(path)
        data = "\n".join(text[n - 1] for n in lines).encode("utf-8")
    return len(data), _sha(data)


def read_run(run: dict[str, Any]) -> dict[str, Any]:
    """A run's identity and time, read from its own record or page now."""
    if run["form"] == "record":
        record = _json(run["record"])
        rule = run["run_id"]
        run_id = record[rule["key"]] if "key" in rule else Path(run["record"]).stem
        value = _key(record, run["observed_at"]["key"])
        if run["observed_at"].get("format") == "stamp":
            value = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(
                tzinfo=timezone.utc).isoformat()
        return {"form": "record", "run_id": run_id, "observed_at": value,
                "files": [run["record"], *[d["file"] for d in run.get("derived", [])]],
                "claims": run["claims"]}
    found = _section(run["page"], run["section"])
    if found is None:
        raise LookupError(f"{run['page']} has no section {run['section']!r}")
    first, last, heading = found
    observed, date_line = None, None
    rule = run["observed_at"]
    if rule is not None:
        if rule.get("in") == "heading":
            m, date_line = re.search(rule["pattern"], heading), first
        else:
            text = _lines(run["page"])
            hit = next(((n, mm) for n in range(first, last + 1)
                        if (mm := re.search(rule["pattern"], text[n - 1]))), None)
            m, date_line = (hit[1], hit[0]) if hit else (None, None)
        if m is None:
            raise LookupError(f"{run['page']} section {heading!r} has no date "
                              f"matching {rule['pattern']!r}")
        observed = _day(m.group(1))
    return {"form": "page", "run_id": heading, "observed_at": observed,
            "files": [run["page"]], "section": [first, last], "date_line": date_line,
            "observed_at_why": run.get("observed_at_why"), "claims": run["claims"]}


# -- where each claim came from ------------------------------------------------------


def _source(where: dict[str, Any] | None) -> dict[str, Any] | None:
    """Where a claim is read -- a file and line, or a file and key. Its hash is
    6.1's and 6.2's to keep; here only the evidence is hashed."""
    if where is None:
        return None
    return {k: where[k] for k in ("path", "line", "key") if k in where}


def _expand(entries: list[dict[str, Any]]) -> list[str]:
    """A claim's evidence paths, and through each sealed fact among them the
    fact's own sources and evidence -- a fact points at what it rests on."""
    out = []
    for e in entries:
        out.append(e["path"])
        if e["path"].startswith("facts/"):
            fact = _json(e["path"])
            out += [p for p in (*fact["source"], *fact["evidence"]) if p not in out]
    return out


def origins(inventory: dict[str, Any], registry: dict[str, Any],
            spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every claim as 6.1 and 6.2 made it -- its class there, its evidence
    there -- keyed by the id the provenance object carries."""
    out: dict[str, dict[str, Any]] = {}
    for item in inventory["items"]:
        value = "UNKNOWN" if item["value"] is None else item["value"]
        out[f"6.1:{item['id']}"] = {
            "name": item["id"], "layer": "6.1", "class": item["class"],
            "hardware": item["hardware"], "claim": f"{item['hardware']} = {value}",
            "source": _source(item["source"]), "evidence_kind": item["evidence_kind"],
            "evidence": item["evidence"], "board_run": None, "reason": item["why"]}
    for row in registry["registry"]:
        out[f"6.2:{row['field']}"] = {
            "name": row["field"], "layer": "6.2", "class": row["status"],
            "hardware": "telemetri",
            "claim": (f"{row['field']}: {row['note']}" if row["status"] == "MEASURED"
                      else f"{row['field']} = UNKNOWN"),
            "source": {"path": row["evidence"][0]["path"], "line": row["evidence"][0]["lines"][0]},
            "evidence_kind": row["source_kind"], "evidence": row["evidence"][1:],
            "board_run": row["board_run"], "reason": row["note"]}
    rtl = registry["rtl_signals"]
    for s in rtl["signals"]:
        out[f"6.2:{s['name']}"] = {
            "name": s["name"], "layer": "6.2", "class": s["status"], "hardware": "telemetri RTL",
            "claim": f"{s['name']} = port {rtl['file']}:{s['line']}",
            "source": {"path": rtl["file"], "line": s["line"]}, "evidence_kind": "rtl",
            "evidence": [{"path": rtl["file"], "sha256": rtl["sha256"]}], "board_run": None,
            "reason": None}
    now = spec["current_state"]
    out["6.3:current-state"] = {
        "name": "current-state", "layer": "6.3", "class": "UNKNOWN", "hardware": now["hardware"],
        "claim": f"{now['hardware']} = UNKNOWN",
        "source": {"path": "NUI/telemetry_sources.json", "key": "live_sources"},
        "evidence_kind": "none", "evidence": [], "board_run": None, "reason": now["reason"]}
    return out


def context(inventory: dict[str, Any] | None = None, registry: dict[str, Any] | None = None,
            spec: dict[str, Any] | None = None) -> Context:
    """What a claim is built and checked against: the spec, the 6.1 and 6.2
    records as they stand -- frozen, with the post-freeze addendum applied --
    and every run as its own evidence names it now."""
    spec = spec if spec is not None else load()
    inventory = inventory if inventory is not None else layer6_addendum.current("hardware")
    registry = registry if registry is not None else layer6_addendum.current(
        "telemetry_sources")
    runs = [{**read_run(r), "spec": r} for r in spec["runs"]]
    carried: dict[str, dict[str, Any]] = {}
    for run in runs:
        for claim in run["claims"]:
            if claim in carried:
                raise LookupError(f"{claim} is carried by two runs")
            carried[claim] = run
    return {"spec": spec, "inventory": inventory, "registry": registry, "runs": runs,
            "carried": carried, "origins": origins(inventory, registry, spec)}


def _boundary(o: dict[str, Any], ctx: Context) -> str:
    """Which side of 6.2's live-access boundary a claim is on."""
    if o["layer"] == "6.2":
        return telemetry_sources.access(o["name"], ctx["registry"])
    if o["layer"] == "6.3" and ctx["registry"]["live_sources"]:
        return telemetry_sources.LIVE
    return {"MEASURED": telemetry_sources.HISTORICAL, "SIMULATED": telemetry_sources.SIMULATED,
            "UNKNOWN": telemetry_sources.UNKNOWN}[o["class"]]


def _kind_of(boundary: str, spec: dict[str, Any]) -> str:
    return str(next(k for k, v in spec["source_kinds"].items() if v["boundary"] == boundary))


def _design(path: str, spec: dict[str, Any]) -> bool:
    rule = spec["design_evidence"]
    if path.startswith(tuple(rule["paths"])):
        return True
    return path.startswith("facts/") and _json(path)["confidence"] in rule["fact_confidence"]


# -- the canonical object ------------------------------------------------------------


def _object(cid: str, ctx: Context) -> dict[str, Any]:
    spec, o = ctx["spec"], ctx["origins"][cid]
    kind = _kind_of(_boundary(o, ctx), spec)
    obj: dict[str, Any] = {
        "id": cid, "hardware": o["hardware"], "claim": o["claim"], "source": o["source"],
        "source_kind": kind, "evidence_kind": o["evidence_kind"], "run_id": None,
        "run_identity": None, "observed_at": None, "evidence": None, "evidence_lines": None,
        "evidence_bytes": None, "evidence_sha256": None,
        "status": spec["source_kinds"][kind]["status"], "reason": None}
    if kind == "live":
        live = ctx["registry"]["live_sources"]
        obj["claim"] = f"{o['hardware']} = live"
        named = live if o["layer"] == "6.3" else [o["name"]]
        obj["reason"] = f"registered live source: {', '.join(named)}"
        return obj
    if kind == "unknown":
        obj["reason"] = o["reason"]
        return obj
    paths = _expand(o["evidence"])
    if kind == "simulated":
        path = next((p for p in paths if _design(p, spec)), None)
        if path is None:
            raise LookupError(f"{cid} is SIMULATED but none of its evidence is a design artefact")
        obj["evidence"] = path
    else:
        run = ctx["carried"].get(cid)
        if run is None and cid not in spec["no_run"]:
            raise LookupError(f"{cid} is MEASURED but no board run carries it")
        if run is None:
            obj["evidence"] = o["board_run"] or next(p for p in paths if p.startswith(BOARD))
        else:
            obj["run_id"], obj["observed_at"] = run["run_id"], run["observed_at"]
            obj["run_identity"] = spec["run_identity"]["labels"][run["form"]]
            obj["evidence"] = next((p for p in paths if p in run["files"]), run["files"][0])
    if obj["evidence"].endswith(".md"):
        lines = set(next((e.get("lines") or [] for e in o["evidence"]
                          if e["path"] == obj["evidence"]), []))
        run = ctx["carried"].get(cid)
        if run is not None and run["form"] == "page":
            lines |= {run["section"][0]} | ({run["date_line"]} if run["date_line"] else set())
        obj["evidence_lines"] = sorted(lines)
    obj["evidence_bytes"], obj["evidence_sha256"] = _hashed(obj["evidence"],
                                                           obj["evidence_lines"])
    return obj


# -- the checks ------------------------------------------------------------------------


def _run_named(run_id: Any, ctx: Context) -> dict[str, Any] | None:
    return next((r for r in ctx["runs"] if r["run_id"] == run_id), None)


def _observed(value: Any) -> str | None:
    """Why an observed_at is not valid, or None: an ISO datetime with its
    offset, or an ISO date where the evidence dates only the day."""
    if not isinstance(value, str):
        return f"{value!r} is not a time"
    try:
        when = datetime.fromisoformat(value)
    except ValueError:
        return f"{value!r} is not ISO 8601"
    if len(value) == 10:
        return None if date.fromisoformat(value).isoformat() == value else f"{value!r}"
    return None if when.tzinfo is not None else f"{value!r} has no UTC offset"


def check(c: dict[str, Any], ctx: Context) -> list[dict[str, Any]]:
    """The owner's ten checks on one provenance object, and the two that
    hold the object canonical and UNKNOWN unknown -- each read from the files
    themselves, not from what the object says. Returns what failed."""
    spec = ctx["spec"]
    failed: list[dict[str, Any]] = []

    def fail(n: int, why: str) -> None:
        failed.append({"check": n, "why": why})

    o = ctx["origins"].get(c.get("id", ""))
    kind, status = c.get("source_kind"), c.get("status")
    historical = kind == "historical_board_evidence"
    # 0 -- canonical: the fields, and no second timestamp or sha256
    fields = spec["fields"]
    if list(c) != fields:
        extra = sorted(set(c) - set(fields))
        missing = [f for f in fields if f not in c]
        fail(0, f"fields differ from the canonical object: extra {extra}, missing {missing}")
    if kind not in SOURCE_KINDS or status not in STATUSES:
        fail(0, f"source_kind {kind!r} or status {status!r} is not one of the four")
    need = {"MEASURED": ("evidence", "evidence_bytes", "evidence_sha256"),
            "SIMULATED": ("evidence", "evidence_bytes", "evidence_sha256"),
            "UNKNOWN": ("reason",), "LIVE": ("reason",)}.get(str(status), ())
    empty = [f for f in need if c.get(f) in (None, "")]
    if empty or not c.get("claim") or not c.get("hardware"):
        fail(0, f"a {status} claim without provenance: {empty or ['claim']}")
    if status in ("UNKNOWN", "LIVE") and any(c.get(f) is not None for f in (
            "run_id", "observed_at", "evidence", "evidence_lines", "evidence_bytes",
            "evidence_sha256")):
        fail(0, f"a {status} claim carries evidence it cannot have")
    # 1 -- run_id exists
    run = _run_named(c.get("run_id"), ctx) if historical else None
    if historical and run is None:
        why = spec["no_run"].get(c.get("id", ""))
        fail(1, why or f"run {c.get('run_id')!r} is no board run the evidence names")
    if not historical and c.get("run_id") is not None:
        fail(1, f"a {kind} claim names a board run")
    label = spec["run_identity"]["labels"][run["form"]] if run is not None else None
    if c.get("run_identity") != label:
        fail(1, f"its run_id is {label or 'no run'}, not {c.get('run_identity')}")
    # 2 -- the run belongs to the right source
    if run is not None:
        ev = c.get("evidence")
        if c.get("id") not in run["claims"]:
            fail(2, f"run {run['run_id']!r} does not carry this claim")
        if ev not in run["files"]:
            fail(2, f"{ev} is not a file of run {run['run_id']!r}")
        if o is not None and ev not in _expand(o["evidence"]):
            fail(2, f"the claim's own evidence does not name {ev}")
        derived = next((d for d in run["spec"].get("derived", []) if d["file"] == ev), None)
        if derived is not None:
            rule, record, file = derived["named_by"], _json(run["spec"]["record"]), str(ev)
            named = (Path(file).stem == run["run_id"] if rule.get("stem") else
                     record.get(rule["key"]) == Path(file).name if "is" not in rule else
                     _json(file).get(rule["key"]) == run["observed_at"])
            if not named:
                fail(2, f"{ev} does not name run {run['run_id']!r}")
        if run["form"] == "page":
            first, last = run["section"]
            outside = [n for n in c.get("evidence_lines") or [] if not first <= n <= last]
            if outside:
                fail(2, f"lines {outside} lie outside the section of {run['run_id']!r}")
    # 3, 4, 5 -- the evidence file, its size, its hash
    ev = c.get("evidence")
    if ev is not None:
        if not (ROOT / ev).is_file():
            fail(3, f"{ev} does not exist")
        else:
            size, sha = _hashed(ev, c.get("evidence_lines"))
            if size != c.get("evidence_bytes"):
                fail(4, f"{ev} weighs {size} bytes, not {c.get('evidence_bytes')}")
            if sha != c.get("evidence_sha256"):
                fail(5, f"{ev} hashes to {sha[:12]}, not {str(c.get('evidence_sha256'))[:12]}")
            derived = next((d for r in ctx["runs"] for d in r["spec"].get("derived", [])
                            if d["file"] == ev), None)
            if derived is not None and "sha256_key" in derived:
                record = _json(next(r["spec"]["record"] for r in ctx["runs"]
                                    if derived in r["spec"].get("derived", [])))
                whole_size, whole_sha = _hashed(ev, None)
                if record[derived["bytes_key"]] != whole_size:
                    fail(4, f"{ev} is not the {record[derived['bytes_key']]} bytes its "
                            "record wrote")
                if record[derived["sha256_key"]] != whole_sha:
                    fail(5, f"{ev} is not the file its record hashed")
    # 6 -- observed_at
    if historical:
        if c.get("observed_at") is None:
            why = (run or {}).get("observed_at_why") or spec["no_run"].get(c.get("id", ""))
            fail(6, why or "no observed_at")
        else:
            bad = _observed(c["observed_at"])
            if bad:
                fail(6, bad)
            elif run is not None and c["observed_at"] != run["observed_at"]:
                fail(6, f"{c['observed_at']} is not {run['observed_at']}, when the run says it ran")
            elif run is not None and run["form"] == "record":
                stamp = STAMP.match(str(c.get("run_id")))
                when = datetime.fromisoformat(c["observed_at"]).astimezone(timezone.utc)
                if stamp and when.strftime("%Y%m%dT%H%M%SZ") != stamp.group(1):
                    fail(6, f"{c['observed_at']} does not fall on the run's own stamp")
    elif c.get("observed_at") is not None:
        fail(6, f"a {kind} claim was not observed on the board")
    # 7 -- source_kind consistent with the source
    if o is not None and kind in SOURCE_KINDS:
        want = _kind_of(_boundary(o, ctx), spec)
        if kind != want:
            fail(7, f"its source is {want}, not {kind}")
        if spec["source_kinds"][kind]["status"] != status:
            fail(7, f"a {kind} claim is {status}")
        if c.get("evidence_kind") not in spec["source_kinds"][kind]["evidence_kinds"]:
            fail(7, f"evidence_kind {c.get('evidence_kind')!r} is not {kind}")
        if kind == "historical_board_evidence" and not str(ev).startswith(BOARD):
            fail(7, f"{ev} is not board evidence")
        if kind == "simulated" and (ev is None or not _design(ev, spec)):
            fail(7, f"{ev} is not a design or build artefact")
    # 8 -- the VM namespace is not mixed in
    if "vm_name" in c or VM_RUN.fullmatch(str(c.get("run_id"))) or str(ev).startswith(
            "observations/"):
        fail(8, "VM evidence is (vm_name, run_id), and this is not a VM claim")
    # 9 -- historical is not promoted to live
    live = o is not None and _boundary(o, ctx) == telemetry_sources.LIVE
    if (kind == "live" or status == "LIVE") and not live:
        fail(9, "access() finds no registered live source for it")
    # 10 -- simulated is not promoted to measured
    if status == "MEASURED" and (o is None or o["class"] != "MEASURED"
                                 or c.get("evidence_kind") in
                                 spec["source_kinds"]["simulated"]["evidence_kinds"]):
        fail(10, f"MEASURED, but its origin is {o['class'] if o else 'nowhere'}")
    if o is not None and o["class"] == "SIMULATED" and status != "SIMULATED":
        fail(10, f"a SIMULATED claim reported {status}")
    # 11 -- UNKNOWN stays UNKNOWN without a live source
    if o is not None and o["class"] == "UNKNOWN" and not live and status != "UNKNOWN":
        fail(11, f"UNKNOWN without a live source, reported {status}")
    labels = {k["id"]: k["label"] for k in spec["checks"]}
    return [{"check": f["check"], "label": labels[f["check"]], "why": f["why"]} for f in failed]


# -- the model -----------------------------------------------------------------------


def _discrepancies(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """What the contract page says against what the committed baselines give --
    recorded, not corrected."""
    out = []
    for d in spec["discrepancies"]:
        hits = hardware._matching(d["says"]["file"], d["says"]["pattern"])
        if not hits:
            raise LookupError(f"{d['says']['file']} no longer says {d['field']}")
        n, _, m = hits[0]
        out.append({"field": d["field"], "says": m.group(1),
                    "where": {"path": d["says"]["file"], "line": n},
                    "measured": [{"path": x["json"], "key": x["key"],
                                  "value": _key(_json(x["json"]), x["key"])}
                                 for x in d["measured"]]})
    return out


def claim(cid: str, ctx: Context) -> dict[str, Any]:
    """One claim's canonical object, checked: `verification` says whether
    every check held, and `failed_checks` which did not."""
    obj = _object(cid, ctx)
    obj["verification"], obj["failed_checks"] = "verified", []
    failed = check(obj, ctx)
    if failed:
        obj["verification"], obj["failed_checks"] = "incomplete", failed
    return obj


def build(ctx: Context | None = None) -> dict[str, Any]:
    ctx = ctx if ctx is not None else context()
    spec = ctx["spec"]
    for cid in [*ctx["carried"], *spec["no_run"]]:
        if cid not in ctx["origins"]:
            raise LookupError(f"the spec names {cid}, which 6.1 and 6.2 do not")
    claims = [claim(cid, ctx) for cid in ctx["origins"]]
    runs = [{"run_id": r["run_id"], "form": r["form"],
             "run_identity": spec["run_identity"]["labels"][r["form"]],
             "observed_at": r["observed_at"], "evidence": r["files"], "claims": r["claims"]}
            for r in ctx["runs"]]
    counts = {**{s: sum(1 for c in claims if c["status"] == s) for s in STATUSES},
              **{k: sum(1 for c in claims if c["source_kind"] == k) for k in SOURCE_KINDS},
              "claims": len(claims),
              "verified": sum(1 for c in claims if c["verification"] == "verified"),
              "incomplete": sum(1 for c in claims if c["verification"] == "incomplete")}
    return {"generated_by": "src/hijaiyyah/nui/hardware_provenance.py",
            "spec": "NUI/spec/hardware_provenance.json",
            "reads": ["NUI/hardware_inventory.json", "NUI/telemetry_sources.json"],
            "counts": counts, "runs": runs, "claims": claims,
            "discrepancies": _discrepancies(spec), "discrepancies_why": spec["discrepancies_why"]}


def claims_for(subject: str, model: dict[str, Any] | None = None) -> list[dict[str, Any]] | None:
    """The claims a hardware query names: one of the owner's subjects, or a
    claim by its name. None when the subject names nothing."""
    model = model if model is not None else json.loads(MODEL.read_text(encoding="utf-8"))
    spec = load()
    inventory = json.loads(hardware.MODEL.read_text(encoding="utf-8"))
    rule = next((v for k, v in spec["queries"].items() if k.lower() == subject.lower()), None)
    by_id = {c["id"]: c for c in model["claims"]}
    if rule is None:
        hits = [c for c in model["claims"] if c["id"].split(":", 1)[1] == subject]
        return hits or None
    if "claims" in rule:
        return [by_id[i] for i in rule["claims"]]
    if "evidence_kind" in rule:
        return [c for c in model["claims"] if c["evidence_kind"] == rule["evidence_kind"]]
    chosen = [by_id[f"6.1:{i['id']}"] for i in inventory["items"]
              if rule["answers"] in i["answers"]]
    if rule.get("layer"):
        chosen += [c for c in model["claims"] if c["id"].startswith(rule["layer"] + ":")]
    return chosen


def verify(committed: dict[str, Any] | None = None) -> list[str]:
    """The provenance as frozen, with its post-freeze addendum beside it,
    against what the evidence builds today."""
    committed = committed if committed is not None else json.loads(
        MODEL.read_text(encoding="utf-8"))
    try:
        fresh = json.loads(json.dumps(build()))
    except (LookupError, OSError, KeyError, ValueError) as why:
        return [f"the hardware provenance no longer reads back: {why}"]
    return layer6_addendum.verify("hardware_provenance", fresh, committed)


def page(model: dict[str, Any]) -> str:
    c = model["counts"]
    out = ["# Provenance hardware — Lapis 6.3", "",
           f"Dihasilkan `{model['generated_by']}` dari `{model['spec']}`, atas klaim "
           f"`{model['reads'][0]}` (6.1) dan `{model['reads'][1]}` (6.2). Tidak ada port "
           "debug, RTL, bitstream, atau telemetri live yang disentuh untuknya.", "",
           f"**{c['claims']} klaim**: {c['MEASURED']} MEASURED, {c['SIMULATED']} SIMULATED, "
           f"{c['UNKNOWN']} UNKNOWN, {c['LIVE']} LIVE. **{c['verified']} terverifikasi, "
           f"{c['incomplete']} belum lengkap.**", ""]
    now = next(x for x in model["claims"] if x["id"] == "6.3:current-state")
    out += ["## Keadaan hardware sekarang", "",
            f"**{now['status']}** — {now['reason']}. Rekaman historis terakhir bukan keadaan "
            "sekarang.", "",
            "## Lari papan", "",
            "Identitas run: `instrumented` bila alat yang menulisnya; "
            "`non-instrumented/inferred-from-record` bila ia judul bagian halaman, dipertahankan "
            "persis seperti sumbernya.", "",
            "| run_id | bentuk | identitas | observed_at | bukti | klaim |",
            "|---|---|---|---|---|---|"]
    for r in model["runs"]:
        ev = "<br>".join(f"`{p}`" for p in r["evidence"])
        out.append(f"| `{r['run_id']}` | {r['form']} | {r['run_identity']} | "
                   f"{r['observed_at'] or '—'} | {ev} | {', '.join(r['claims'])} |")
    out += ["", "## Klaim", "",
            "| id | status | source_kind | jenis bukti | run_id | observed_at | evidence | "
            "sha256 | verifikasi |", "|---|---|---|---|---|---|---|---|---|"]
    for x in model["claims"]:
        ev = "—" if x["evidence"] is None else f"`{x['evidence']}`" + (
            f" baris {', '.join(map(str, x['evidence_lines']))}" if x["evidence_lines"] else "")
        sha = f"`{x['evidence_sha256'][:12]}…`" if x["evidence_sha256"] else "—"
        run = f"`{x['run_id']}`" if x["run_id"] else "—"
        out.append(f"| `{x['id']}` | {x['status']} | {x['source_kind']} | {x['evidence_kind']} | "
                   f"{run} | {x['observed_at'] or '—'} | {ev} | {sha} | {x['verification']} |")
    out += ["", "## Belum lengkap", "",
            "Klaim ini tetap memakai kelas 6.1/6.2-nya; yang belum lengkap adalah rantainya, dan "
            "tidak diisi.", ""]
    for x in model["claims"]:
        for f in x["failed_checks"]:
            out.append(f"- `{x['id']}` — pemeriksaan {f['check']} ({f['label']}): {f['why']}.")
    out += ["", "## Selisih historis — dicatat, tidak disunting", "",
            f"{model['discrepancies_why'][0].upper()}{model['discrepancies_why'][1:]}.", "",
            "| medan | kontrak | baris | garis dasar |", "|---|---|---|---|"]
    for d in model["discrepancies"]:
        measured = "<br>".join(f"`{m['path']}` `{m['key']}` = {m['value']}"
                               for m in d["measured"])
        out.append(f"| `{d['field']}` | {d['says']} | `{d['where']['path']}:{d['where']['line']}` "
                   f"| {measured} |")
    out += ["", "## Mengulang", "", "```bash",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.hardware_provenance --verify", "```"]
    return "\n".join(out) + "\n"


def write() -> Path:
    model = json.loads(json.dumps(build()))
    MODEL.write_text(json.dumps(model, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    PAGE.write_text(page(model), encoding="utf-8")
    return MODEL


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == ["--write"]:
        print(f"model: {write().relative_to(ROOT)}, page: {PAGE.relative_to(ROOT)}")
        return 0
    problems = verify()
    print("\n".join(problems) if problems else
          f"hardware provenance reproduced exactly: the frozen record, and "
          f"{len(layer6_addendum.changes('hardware_provenance'))} changes of the post-freeze "
          "addendum")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
