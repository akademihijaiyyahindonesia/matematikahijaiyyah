"""Layer 6.5: hardware, program, opcode, execution and board observation, linked.

    PYTHONPATH=src python3 -m hijaiyyah.nui.hardware_correlation --write
    PYTHONPATH=src python3 -m hijaiyyah.nui.hardware_correlation --verify

The owner's step 6.5, 28 September 2026. Not new telemetry -- 6.2 proved
there is none live -- but the links between levels of evidence that already
exist:

    hardware <-> board run <-> program <-> opcode, and what the board printed

Each link is one correlation, and each says how it is known:

    DIRECT    written explicitly in the evidence: a run's record names the
              program and the hash of the payload it sent, holds what the
              board printed, or states a hardware value equal to a claim's;
              or 6.3's chain from a claim to its run
    DERIVED   computed from structure already there: the opcodes the
              interpreter ran for a payload with the same hash, under the
              loader, as frozen before the board was asked; or a verdict on
              the board's output against that frozen expectation
    UNKNOWN   not provable from the evidence -- with the reason, and no value

Nothing is linked because a name looks like it holds an opcode or a program:
a record that names a target and no program has an UNKNOWN program, and a
program with no frozen expectation of its payload has UNKNOWN opcodes.
`executes` is what the interpreter ran, never what the board ran -- P5
measured silicon running a PRINT after HALT that the interpreter never
reaches. And opcode-level hardware evidence is P3's column only, from the
run it was counted from: P4 and P5 are evidence at the level of a program or
an experiment (the owner, 27-28 September 2026), so their `executes`
correlations are shown as such and never counted for an opcode.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from . import hardware, hardware_provenance, hardware_state
from .hardware import _sha
from .repository_index import ROOT

SPEC = ROOT / "NUI" / "spec" / "hardware_correlation.json"
MODEL = ROOT / "NUI" / "hardware_correlation.json"
PAGE = ROOT / "NUI" / "HARDWARE_CORRELATION.md"
CLASSES = ("DIRECT", "DERIVED", "UNKNOWN")
FIELDS = ("id", "relation", "class", "run_id", "observed_at", "from", "to", "payload_sha256",
          "value", "evidence", "evidence_key", "evidence_sha256", "reason")
Context = dict[str, Any]


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SPEC.read_text(encoding="utf-8"))
    return data


def _json(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _file_sha(path: str) -> str:
    return _sha((ROOT / path).read_bytes())


def context(spec: dict[str, Any] | None = None) -> Context:
    """The runs as their records name them now, the claims of 6.3 and 6.4
    with the run each rests on, and the frozen expectations."""
    spec = spec if spec is not None else load()
    runs = []
    for r in spec["runs"]:
        seen = hardware_provenance.read_run({"form": "record", "record": r["record"],
                                             "run_id": r["run_id"],
                                             "observed_at": r["observed_at"], "claims": []})
        runs.append({**r, "id": seen["run_id"], "observed_at_value": seen["observed_at"]})
    provenance = _json("NUI/hardware_provenance.json")
    state = _json("NUI/hardware_state.json")
    inventory = _json("NUI/hardware_inventory.json")
    claims = {c["id"]: ("NUI/hardware_provenance.json", c) for c in provenance["claims"]}
    claims.update({c["id"]: ("NUI/hardware_state.json", c) for c in state["observed_opcodes"]})
    values = {f"6.1:{i['id']}": i["value"] for i in inventory["items"]}
    return {"spec": spec, "runs": runs, "claims": claims, "values": values,
            "expected": _json(spec["expected"]["file"])}


def _edge(relation: str, cls: str, run: dict[str, Any] | None, frm: str | None, to: str | None,
          payload: str | None, value: Any, evidence: str, key: str | None,
          reason: str | None = None) -> dict[str, Any]:
    run_id = run["id"] if run else None
    return {"id": f"{relation}:{frm}->{to}" + (f"@{run_id}" if run_id else ""),
            "relation": relation, "class": cls, "run_id": run_id,
            "observed_at": run["observed_at_value"] if run else None, "from": frm, "to": to,
            "payload_sha256": payload, "value": value, "evidence": evidence, "evidence_key": key,
            "evidence_sha256": _file_sha(evidence), "reason": reason}


def _key(data: Any, parts: list[str]) -> Any:
    for part in parts:
        data = data[part]
    return data


def correlations(ctx: Context) -> list[dict[str, Any]]:
    """Every correlation the spec's runs, 6.3's claims and the frozen
    expectations support -- and the UNKNOWN ones where they do not."""
    spec, out = ctx["spec"], []
    executes: dict[tuple[str, str | None], list[dict[str, Any]]] = {}
    for run in ctx["runs"]:
        record, path = _json(run["record"]), run["record"]
        # supports: 6.3's chain, and P3's column, end on this run
        for cid, (model, c) in ctx["claims"].items():
            if c.get("run_id") == run["id"]:
                out.append(_edge("supports", "DIRECT", run, run["id"], cid, None, run["id"],
                                 model, f"{cid}.run_id"))
        # records: the record states the claim's value under a key
        for key, cid in run.get("records", {}).items():
            if key in record:
                out.append(_edge("records", "DIRECT", run, run["id"], cid, None, record[key],
                                 path, key))
        # ran, printed, judged, and the program's frozen opcodes
        if "programs" in run:
            rule = run["programs"]
            report = _json(run["report"])["programs"]
            frozen = ctx["expected"][run["expected"]]["programs"]
            for name, got in record[rule["key"]].items():
                if rule["text"] not in got:
                    continue
                payload = got[rule["payload"]]
                base = [rule["key"], name]
                out.append(_edge("ran", "DIRECT", run, run["id"], name, payload, payload, path,
                                 ".".join([*base, rule["payload"]])))
                out.append(_edge("printed", "DIRECT", run, run["id"], name, payload,
                                 got[rule["text"]], path, ".".join([*base, rule["text"]])))
                if name in report:
                    out.append(_edge("judged", "DERIVED", run, run["id"], name, payload,
                                     report[name]["status"], run["report"],
                                     f"programs.{name}.status"))
                expected = frozen.get(name, {})
                key = f"{run['expected']}.programs.{name}"
                if expected.get("payload_sha256") == payload:
                    executes[(name, payload)] = [
                        _edge("executes", "DERIVED", None, name, op, payload, op,
                              spec["expected"]["file"], f"{key}.opcodes")
                        for op in expected.get("opcodes", [])]
                else:
                    executes.setdefault((name, payload), [_edge(
                        "executes", "UNKNOWN", None, name, None, payload, None,
                        spec["expected"]["file"], key,
                        "the frozen expectation holds another payload for this name")])
        elif run.get("program"):
            name = record[run["program"]["key"]]
            out.append(_edge("ran", "DIRECT", run, run["id"], name, None, name, path,
                             run["program"]["key"]))
            executes.setdefault((name, None), [_edge(
                "executes", "UNKNOWN", None, name, None, None, None, spec["expected"]["file"],
                None, "no frozen expectation holds this program's payload; its opcodes are "
                      "not read from its name")])
        else:
            out.append(_edge("ran", "UNKNOWN", run, run["id"], None, None, None, path, None,
                             run["program_why"]))
    for edges in executes.values():
        out += edges
    return out


# -- the checks ------------------------------------------------------------------------


def check(e: dict[str, Any], ctx: Context) -> list[dict[str, Any]]:
    """X1-X5 on one correlation, read against its evidence file itself."""
    spec, failed = ctx["spec"], []
    relation = spec["relations"].get(e.get("relation"))
    if list(e) != list(FIELDS):
        failed.append(("X1", f"fields differ from a correlation's: {sorted(set(e) ^ set(FIELDS))}"))
    if relation is None or e.get("class") not in relation["classes"]:
        failed.append(("X1", f"{e.get('relation')} cannot be {e.get('class')}"))
    ev = e.get("evidence")
    if ev is None or not (ROOT / ev).is_file():
        failed.append(("X2", f"{ev} does not exist"))
    elif _file_sha(ev) != e.get("evidence_sha256"):
        failed.append(("X2", f"{ev} is not the file this correlation hashed"))
    if e.get("class") == "UNKNOWN":
        if not e.get("reason") or e.get("value") is not None:
            failed.append(("X5", "an UNKNOWN correlation carries a value or no reason"))
    elif not e.get("evidence_key") or e.get("reason") is not None:
        failed.append(("X5", f"a {e.get('class')} correlation without its evidence key"))
    elif ev is not None and (ROOT / ev).is_file():
        failed += _resolves(e, ctx)
    labels = {k["id"]: k["label"] for k in spec["checks"]}
    return [{"check": n, "label": labels[n], "why": why} for n, why in failed]


def _value(e: dict[str, Any], data: Any) -> Any:
    """What the evidence holds at this correlation's key. Program names hold
    dots, so a program's entry is found by the name the correlation carries,
    never by splitting the key."""
    relation, key = e["relation"], e["evidence_key"]
    if relation == "supports" or key in ("program",) or relation == "records":
        return data[key] if relation != "supports" else None
    if relation == "executes":
        entry = data[key.split(".", 1)[0]]["programs"][e["from"]]
        return entry
    head, field = key.split(".", 1)[0], key.rsplit(".", 1)[1]
    return data[head][e["to"]][field]


def _resolves(e: dict[str, Any], ctx: Context) -> list[tuple[str, str]]:
    """X3 and X4: the key names this correlation's own value, in the record
    of this correlation's own run."""
    failed = []
    relation, data = e["relation"], _json(e["evidence"])
    run = next((r for r in ctx["runs"] if r["id"] == e["run_id"]), None)
    if relation != "executes":
        if run is None or e["observed_at"] != run["observed_at_value"]:
            failed.append(("X4", f"{e['run_id']} is no correlated run, or not when it ran"))
        elif relation in ("ran", "printed", "records") and (
                e["evidence"] != run["record"] or e["from"] != run["id"]):
            failed.append(("X4", f"{e['evidence']} is not the record of run {e['run_id']}"))
        elif relation == "judged" and e["evidence"] != run.get("report"):
            failed.append(("X4", f"{e['evidence']} is not the report of run {e['run_id']}"))
    try:
        if relation == "supports":
            model, claim = ctx["claims"].get(e["to"], (None, {}))
            ok = (e["evidence"] == model and claim.get("run_id") == e["from"] == e["value"])
        elif relation == "records":
            ok = _value(e, data) == e["value"] == ctx["values"].get(e["to"])
        elif relation == "executes":
            entry = _value(e, data)
            ok = (entry.get("payload_sha256") == e["payload_sha256"]
                  and e["to"] in entry.get("opcodes", []) and e["value"] == e["to"])
        else:
            ok = _value(e, data) == e["value"]
            if ok and relation in ("printed", "judged") and run is not None and "programs" in run:
                sent = _json(run["record"])[run["programs"]["key"]].get(e["to"], {})
                ok = sent.get(run["programs"]["payload"]) == e["payload_sha256"]
    except (KeyError, TypeError, IndexError, AttributeError):
        ok = False
    if not ok:
        failed.append(("X3", f"{e['evidence_key']} in {e['evidence']} does not give "
                             f"{e['relation']} {e['from']} -> {e['to']}"))
    return failed


def opcode_evidence(model: dict[str, Any], ctx: Context) -> dict[str, dict[str, Any]]:
    """Per opcode: the programs that are opcode-level evidence -- those P3's
    run ran -- and those that are only experiment-level."""
    rule = ctx["spec"]["opcode_evidence"]
    ran = {(e["run_id"], e["to"], e["payload_sha256"]) for e in model["correlations"]
           if e["relation"] == "ran" and e["class"] == "DIRECT"}
    out: dict[str, dict[str, Any]] = {}
    for e in model["correlations"]:
        if e["relation"] != "executes" or e["class"] != "DERIVED":
            continue
        row = out.setdefault(e["to"], {"evidence": [], "experiment": []})
        level = ("evidence" if (rule["run"], e["from"], e["payload_sha256"]) in ran
                 else "experiment")
        row[level].append(e["from"])
    return {op: {k: sorted(set(v)) for k, v in row.items()} for op, row in sorted(out.items())}


def check_opcode_evidence(evidence: dict[str, dict[str, Any]], ctx: Context) -> list[str]:
    """X6: the opcode-level evidence is exactly P3's column for every opcode."""
    rule = ctx["spec"]["opcode_evidence"]["column"]
    column = hardware_provenance._key(_json(rule["model"]), rule["key"])
    bad = []
    for op, row in column.items():
        want = sorted({*row["agreeing_programs"], *row["differing_programs"],
                       *row["undecided_programs"]})
        if evidence.get(op, {}).get("evidence", []) != want:
            bad.append(op)
    return bad


# -- answers ---------------------------------------------------------------------------


def answer(kind: str, subject: str, model: dict[str, Any], ctx: Context) -> dict[str, Any]:
    """`hardware correlation <kind> <subject>`: the correlations that leave
    or reach it, in the owner's directions."""
    edges = model["correlations"]
    unknown: list[str] = []
    if kind == "hardware":
        state_ctx = hardware_state.context()
        ids = hardware_state.select(subject, state_ctx) or []
        linked = [e for e in edges if e["relation"] in ("supports", "records") and e["to"] in ids]
        runs = {e["run_id"] for e in linked}
        chosen = linked + [e for e in edges if e["relation"] == "ran" and e["run_id"] in runs]
        unknown += [f"{i}: no board run supports or records it" for i in ids
                    if not any(e["to"] == i for e in linked)]
        if not ids:
            unknown.append(f"`{subject}` names no hardware claim")
    elif kind == "program":
        own = [e for e in edges if subject in (e["from"], e["to"])
               and e["relation"] in ("ran", "printed", "judged", "executes")]
        runs = {e["run_id"] for e in own if e["relation"] == "ran"}
        chosen = own + [e for e in edges if e["relation"] in ("supports", "records")
                        and e["run_id"] in runs]
        if not own:
            unknown.append(f"`{subject}` is no program a correlated run names")
    elif kind == "opcode":
        chosen = [e for e in edges if e["relation"] == "executes" and e["to"] == subject]
        if not chosen:
            unknown.append(f"no correlated program executes {subject}")
    elif kind == "run":
        chosen = [e for e in edges if e["run_id"] == subject]
        if not chosen:
            unknown.append(f"`{subject}` is no correlated run")
    else:
        raise LookupError(f"`{kind}` is not hardware, program, opcode or run")
    unknown += [f"{e['id']}: {e['reason']}" for e in chosen if e["class"] == "UNKNOWN"]
    out: dict[str, Any] = {"query": f"hardware correlation {kind} {subject}", "kind": kind,
                           "subject": subject,
           "correlations": [e["id"] for e in chosen], "unknown": unknown}
    if kind == "opcode":
        row = model["opcode_evidence"].get(subject, {"evidence": [], "experiment": []})
        out["opcode_evidence"] = {"programs": len(row["evidence"]),
                                  "experiment": row["experiment"]}
    return out


# -- the model -------------------------------------------------------------------------------


def build(ctx: Context | None = None) -> dict[str, Any]:
    ctx = ctx if ctx is not None else context()
    spec = ctx["spec"]
    edges = correlations(ctx)
    ids = [e["id"] for e in edges]
    if len(ids) != len(set(ids)):
        twice = sorted(i for i in set(ids) if ids.count(i) > 1)
        raise LookupError(f"two correlations share an id: {twice}")
    failed = {e["id"]: f for e in edges if (f := check(e, ctx))}
    if failed:
        raise LookupError(f"correlations that do not hold: {failed}")
    counts: dict[str, dict[str, int]] = {}
    for e in edges:
        row = counts.setdefault(e["relation"], {c: 0 for c in CLASSES})
        row[e["class"]] += 1
    model: dict[str, Any] = {
        "generated_by": "src/hijaiyyah/nui/hardware_correlation.py",
        "spec": "NUI/spec/hardware_correlation.json",
        "reads": ["NUI/hardware_provenance.json", "NUI/hardware_state.json",
                  spec["expected"]["file"]],
        "runs": [{"run_id": r["id"], "observed_at": r["observed_at_value"],
                  "record": r["record"], "sha256": _file_sha(r["record"]),
                  "sent": (sum(1 for v in _json(r["record"])[r["programs"]["key"]].values()
                               if r["programs"]["text"] in v) if "programs" in r else None),
                  "not_sent": (sum(1 for v in _json(r["record"])[r["programs"]["key"]].values()
                                   if r["programs"]["text"] not in v)
                               if "programs" in r else None)} for r in ctx["runs"]],
        "not_correlated": spec["not_correlated"], "counts": counts, "correlations": edges}
    model["opcode_evidence"] = opcode_evidence(model, ctx)
    bad = check_opcode_evidence(model["opcode_evidence"], ctx)
    if bad:
        raise LookupError(f"opcode evidence that is not P3's column: {bad}")
    model["contract"] = []
    for row in spec["contract"]:
        _, _, kind, subject = row["query"].split(" ", 3)
        model["contract"].append(answer(kind, subject, model, ctx))
    return model


def verify(committed: dict[str, Any] | None = None) -> list[str]:
    committed = committed if committed is not None else json.loads(
        MODEL.read_text(encoding="utf-8"))
    try:
        fresh = json.loads(json.dumps(build()))
    except (LookupError, OSError, KeyError, ValueError) as why:
        return [f"the hardware correlation no longer reads back: {why}"]
    return hardware._diff(committed, fresh)


def page(model: dict[str, Any]) -> str:
    spec = load()
    out = ["# Korelasi hardware — Lapis 6.5", "",
           f"Dihasilkan `{model['generated_by']}` dari `{model['spec']}`, atas "
           + ", ".join(f"`{p}`" for p in model["reads"]) + ", dan rekaman lari papan yang "
           "di-commit. Tidak ada RTL, port debug, bitstream, lari papan baru, atau telemetri "
           "baru yang disentuh untuknya.", "",
           "**Tidak ada korelasi karena nama.** `executes` adalah yang interpreter jalankan "
           "untuk payload dengan hash yang sama, bukan yang papan jalankan; bukti tingkat opcode "
           "hanya kolom P3.", "", "## Kelas", ""]
    out += [f"- **{k}** — {v}." for k, v in spec["classes"].items()]
    out += ["", "## Relasi", "", "| relasi | dari → ke | arti | DIRECT | DERIVED | UNKNOWN |",
            "|---|---|---|---|---|---|"]
    for name, rel in spec["relations"].items():
        c = model["counts"].get(name, {k: 0 for k in CLASSES})
        out.append(f"| `{name}` | {rel['from']} → {rel['to']} | {rel['means']} | {c['DIRECT']} | "
                   f"{c['DERIVED']} | {c['UNKNOWN']} |")
    out += ["", "## Lari yang dikorelasikan", "",
            "| run_id | observed_at | rekaman | dikirim | tidak dikirim |", "|---|---|---|---|---|"]
    for r in model["runs"]:
        out.append(f"| `{r['run_id']}` | {r['observed_at']} | `{r['record']}` | "
                   f"{'—' if r['sent'] is None else r['sent']} | "
                   f"{'—' if r['not_sent'] is None else r['not_sent']} |")
    out += ["", "Tidak dikorelasikan:", ""]
    out += [f"- `{n['record']}` — {n['why']}." for n in model["not_correlated"]]
    out += ["", "## Kontrak", "", "| kueri | korelasi | UNKNOWN |", "|---|---|---|"]
    for a in model["contract"]:
        extra = (f"; bukti opcode {a['opcode_evidence']['programs']} program, eksperimen "
                 + (", ".join(f"`{p}`" for p in a["opcode_evidence"]["experiment"]) or "—")
                 if "opcode_evidence" in a else "")
        out.append(f"| `{a['query']}` | {len(a['correlations'])}{extra} | "
                   + ("<br>".join(a["unknown"]) or "—") + " |")
    out += ["", "## Yang tetap UNKNOWN", ""]
    out += [f"- `{e['id']}` — {e['reason']}." for e in model["correlations"]
            if e["class"] == "UNKNOWN"]
    out += ["", "## Divergensi yang terukur", "", f"`{spec['divergence']['run']}`: "
            f"{spec['divergence']['why']}.", "", "## Mengulang", "", "```bash",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.hardware_correlation --verify", "```"]
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
    print("\n".join(problems) if problems else "hardware correlation reproduced exactly")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
