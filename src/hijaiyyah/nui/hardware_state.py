"""Layer 6.4: what an answer about hardware means.

    PYTHONPATH=src python3 -m hijaiyyah.nui.hardware_state --write
    PYTHONPATH=src python3 -m hijaiyyah.nui.hardware_state --verify

The owner's step 6.4, 27 September 2026. Not new telemetry: the meaning of
NUI's answer when someone asks about the hardware --

    QUERY -> HARDWARE CLAIM -> CLASSIFICATION -> STATE SEMANTICS -> PROVENANCE

Every claim 6.3 walked back to its evidence is filed under one of four kinds
of state, and a query names the kind it asks for:

    IDENTITY     what the device is                              MEASURED, SIMULATED
    CAPABILITY   what the design or build says it can do        SIMULATED
    OBSERVED     what was ever really measured                  MEASURED, UNKNOWN
    CURRENT      what the device is doing now                   LIVE, UNKNOWN

The fence the owner put first: historical board evidence is not the current
hardware state. The newest board run answers "what did that run measure",
never "what is happening now". So a CURRENT query is answered only by a live
source that 6.2's access() finds registered -- today none -- and otherwise
UNKNOWN, "no live hardware telemetry source", whatever history there is.

The answer's state follows one precedence, LIVE > MEASURED > SIMULATED >
UNKNOWN, over the claims allowed to answer that kind of query, so it is the
same every time. Each claim keeps its 6.3 provenance, and a claim whose chain
6.3 left incomplete still answers a historical question as MEASURED -- with
its incomplete provenance named in the answer, never polished into verified.

OBSERVED also takes the opcodes the board ran: the per-opcode hardware column
of P3, frozen with Layer 4, one claim per opcode, each built and checked by
6.3's own machinery against the P2 record it was counted from.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from . import hardware, hardware_provenance, telemetry_sources
from .repository_index import ROOT

SPEC = ROOT / "NUI" / "spec" / "hardware_state.json"
MODEL = ROOT / "NUI" / "hardware_state.json"
PAGE = ROOT / "NUI" / "HARDWARE_STATE.md"
CATEGORIES = ("IDENTITY", "CAPABILITY", "OBSERVED", "CURRENT")
Context = dict[str, Any]


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SPEC.read_text(encoding="utf-8"))
    return data


def _json(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


# -- the observed opcodes, P3's column as claims ------------------------------------------


def _opcode_origins(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """One claim per opcode of the frozen hardware column: MEASURED when a
    program sent to the board ran it, UNKNOWN when none did."""
    rule = spec["observed_opcodes"]
    model = _json(rule["model"])
    stamp = hardware_provenance._key(model, rule["stamp"])
    if not Path(rule["record"]).stem.startswith(stamp):
        raise LookupError(f"the column was counted from {stamp}, not {rule['record']}")
    out = {}
    for op, row in hardware_provenance._key(model, rule["key"]).items():
        measured = row["programs"] > 0
        out[f"P3:{op}"] = {
            "name": op, "layer": "P3", "class": "MEASURED" if measured else "UNKNOWN",
            "hardware": "opcode",
            "claim": (f"{op} di papan = kolom {row['board']}; {row['parity']} PARITY, "
                      f"{row['mismatch']} MISMATCH, {row['unknown']} UNKNOWN dari "
                      f"{row['programs']} program yang dikirim") if measured
            else f"{op} di papan = UNKNOWN",
            "source": {"path": rule["model"], "key": f"{rule['key']}.{op}"},
            "evidence_kind": "board" if measured else "none",
            "evidence": [{"path": rule["record"]}], "board_run": None,
            "reason": row.get("reason")}
    return out


def context(provenance: dict[str, Any] | None = None, spec: dict[str, Any] | None = None,
            base: hardware_provenance.Context | None = None) -> Context:
    """6.3's context, with P3's opcode claims carried by the run they were
    counted from, and 6.3's committed model to answer from."""
    spec = spec if spec is not None else load()
    ctx = base if base is not None else hardware_provenance.context()
    opcodes = _opcode_origins(spec)
    run = next(r for r in ctx["runs"] if spec["observed_opcodes"]["record"] in r["files"])
    measured = [cid for cid, o in opcodes.items() if o["class"] == "MEASURED"]
    run["claims"] = [*run["claims"], *measured]
    ctx["origins"].update(opcodes)
    ctx["carried"].update({cid: run for cid in measured})
    provenance = provenance if provenance is not None else json.loads(
        hardware_provenance.MODEL.read_text(encoding="utf-8"))
    return {"spec": spec, "provenance_ctx": ctx, "provenance": provenance,
            "opcodes": list(opcodes)}


# -- classification ----------------------------------------------------------------------


def categories(spec: dict[str, Any], provenance: dict[str, Any],
               registry: dict[str, Any], opcodes: list[str]) -> dict[str, str]:
    """Each claim's kind of state, exactly one. A claim filed twice, or not
    at all, is refused."""
    rules, out = spec["claims"], dict[str, str]()

    def put(cid: str, category: str) -> None:
        if category not in CATEGORIES:
            raise LookupError(f"{cid}: {category} is not one of the four")
        if cid in out:
            raise LookupError(f"{cid} is filed under both {out[cid]} and {category}")
        out[cid] = category

    for category, ids in rules["6.1"].items():
        for i in ids:
            put(f"6.1:{i}", category)
    signals = {s["name"] for s in registry["rtl_signals"]["signals"]}
    status = {c["id"]: c["status"] for c in provenance["claims"]}
    for r in registry["registry"]:
        cid = f"6.2:{r['field']}"
        put(cid, rules["6.2"]["fields_live" if status.get(cid) == "LIVE" else "fields"])
    for name in sorted(signals):
        put(f"6.2:{name}", rules["6.2"]["rtl_signals"])
    for name, category in rules["6.3"].items():
        put(f"6.3:{name}", category)
    for cid in opcodes:
        put(cid, rules["P3"])
    missing = [c["id"] for c in provenance["claims"] if c["id"] not in out]
    extra = sorted(set(out) - {c["id"] for c in provenance["claims"]} - set(opcodes))
    if missing or extra:
        raise LookupError(f"claims without a kind of state: {missing}; not claims: {extra}")
    return out


def _entry(obj: dict[str, Any], category: str) -> dict[str, Any]:
    return {"id": obj["id"], "category": category, "status": obj["status"],
            "source_kind": obj["source_kind"], "verification": obj["verification"]}


def check_entry(entry: dict[str, Any], obj: dict[str, Any] | None,
                ctx: Context) -> list[dict[str, Any]]:
    """E1-E5 on one classified claim, against its provenance object."""
    spec, failed = ctx["spec"], []
    category, status = entry.get("category"), entry.get("status")
    if category not in CATEGORIES:
        failed.append(("E1", f"{category!r} is not one of the four"))
    elif status not in spec["categories"][category]["status"]:
        failed.append(("E2", f"a {category} claim cannot be {status}"))
    if obj is None or (status, entry.get("source_kind")) != (obj["status"],
                                                             obj["source_kind"]):
        failed.append(("E3", f"{status}/{entry.get('source_kind')} is not its provenance's "
                             f"{obj and obj['status']}/{obj and obj['source_kind']}"))
    if obj is None or entry.get("verification") != obj["verification"]:
        failed.append(("E4", f"{entry.get('verification')} is not its provenance's "
                             f"{obj and obj['verification']}"))
    if status == "LIVE" or entry.get("source_kind") == "live":
        name = entry["id"].split(":", 1)[1]
        registry = ctx["provenance_ctx"]["registry"]
        found = (registry["live_sources"] if entry["id"] == "6.3:current-state"
                 else [name] if telemetry_sources.access(name, registry) == telemetry_sources.LIVE
                 else [])
        if not found:
            failed.append(("E5", "access() finds no registered live source for it"))
    labels = {k["id"]: k["label"] for k in spec["checks"]}
    return [{"check": n, "label": labels[n], "why": why} for n, why in failed]


# -- answers ---------------------------------------------------------------------------------


def select(subject: str, ctx: Context) -> list[str] | None:
    """The claim ids a subject names: the owner's alias, an opcode, or a 6.3
    subject. None when it names nothing."""
    spec = ctx["spec"]
    alias = next((v for k, v in spec["subjects"].items() if k.lower() == subject.lower()), None)
    subject = alias or subject
    if subject.lower().startswith("opcode "):
        cid = f"P3:{subject.split(None, 1)[1].strip().upper()}"
        return [cid] if cid in ctx["opcodes"] else None
    found = hardware_provenance.claims_for(subject, ctx["provenance"])
    return None if found is None else [c["id"] for c in found]


def answer(group: str, subject: str, model: dict[str, Any], ctx: Context) -> dict[str, Any]:
    """What `hardware <group> <subject>` means: the claims of the asked kind,
    ranked by precedence, and the answer's state -- the first state in the
    precedence that a claim allowed to answer this kind of query holds, and
    otherwise UNKNOWN. A CURRENT query is answered only by LIVE."""
    spec = ctx["spec"]
    if group not in spec["groups"]:
        raise LookupError(f"`{group}` is not one of {', '.join(spec['groups'])}")
    category = spec["groups"][group]
    precedence = spec["precedence"]
    eligible = (spec["categories"][category]["answers_with"] if category
                else precedence[:-1])
    ids = select(subject, ctx)
    entries = {e["id"]: e for e in model["claims"]}
    chosen = [entries[i] for i in ids or [] if category is None
              or entries[i]["category"] == category]
    order = {e["id"]: n for n, e in enumerate(model["claims"])}
    chosen.sort(key=lambda e: (precedence.index(e["status"]), order[e["id"]]))
    state = next((s for s in precedence if s in eligible
                  and any(e["status"] == s for e in chosen)), "UNKNOWN")
    basis = [e["id"] for e in chosen if e["status"] == state] if state != "UNKNOWN" else []
    reason = None
    live = ctx["provenance_ctx"]["registry"]["live_sources"]
    if state == "UNKNOWN":
        reason = (ctx["provenance_ctx"]["spec"]["current_state"]["reason"]
                  if category == "CURRENT" and not live else
                  f"no live source for `{subject}`" if category == "CURRENT" else
                  f"`{subject}` names no hardware claim" if ids is None else
                  f"no {category or 'hardware'} claim of `{subject}` is "
                  f"{' or '.join(eligible)}")
    kinds = {v["status"]: k for k, v in
             ctx["provenance_ctx"]["spec"]["source_kinds"].items()}
    objects = {o["id"]: o for o in [*ctx["provenance"]["claims"], *model["observed_opcodes"]]}
    return {"query": f"hardware {group} {subject}", "group": group, "category": category,
            "subject": subject, "state": state, "source_kind": kinds[state],
            "evidence_kinds": sorted({objects[i]["evidence_kind"] for i in basis}),
            "basis": basis, "claims": [e["id"] for e in chosen],
            "incomplete_provenance": [e["id"] for e in chosen
                                      if e["verification"] == "incomplete"],
            "reason": reason}


def check_answer(a: dict[str, Any], model: dict[str, Any], ctx: Context) -> list[dict[str, Any]]:
    """A1-A4 on one answer, recomputed from the classified claims."""
    spec, failed = ctx["spec"], []
    entries = {e["id"]: e for e in model["claims"]}
    got = [entries[i] for i in a["claims"] if i in entries]
    live = ctx["provenance_ctx"]["registry"]["live_sources"]
    if a["category"] == "CURRENT":
        historical = [i for i in a["basis"] if entries.get(i, {}).get("status") != "LIVE"]
        if a["state"] not in ("LIVE", "UNKNOWN") or historical:
            failed.append(("A1", f"answered {a['state']} from {historical or a['basis']}"))
        if a["state"] == "UNKNOWN" and not live and a["reason"] != (
                ctx["provenance_ctx"]["spec"]["current_state"]["reason"]):
            failed.append(("A1", f"UNKNOWN for another reason: {a['reason']}"))
    if a["category"] is not None:
        off = [e["id"] for e in got if e["category"] != a["category"]]
        if off or len(got) != len(a["claims"]):
            failed.append(("A2", f"claims of another kind: {off}"))
    precedence = spec["precedence"]
    eligible = (spec["categories"][a["category"]]["answers_with"] if a["category"]
                else precedence[:-1])
    state = next((s for s in precedence if s in eligible
                  and any(e["status"] == s for e in got)), "UNKNOWN")
    basis = [e["id"] for e in got if e["status"] == state] if state != "UNKNOWN" else []
    if (a["state"], sorted(a["basis"])) != (state, sorted(basis)):
        failed.append(("A3", f"{a['state']} on {a['basis']}, precedence gives {state} "
                             f"on {basis}"))
    incomplete = [e["id"] for e in got if e["verification"] == "incomplete"]
    if sorted(a["incomplete_provenance"]) != sorted(incomplete):
        failed.append(("A4", f"incomplete provenance {incomplete} not named"))
    labels = {k["id"]: k["label"] for k in spec["checks"]}
    return [{"check": n, "label": labels[n], "why": why} for n, why in failed]


# -- the model --------------------------------------------------------------------------------


def build(ctx: Context | None = None) -> dict[str, Any]:
    ctx = ctx if ctx is not None else context()
    spec, pctx = ctx["spec"], ctx["provenance_ctx"]
    opcodes = [hardware_provenance.claim(cid, pctx) for cid in ctx["opcodes"]]
    kinds = categories(spec, ctx["provenance"], pctx["registry"], ctx["opcodes"])
    objects = {o["id"]: o for o in [*ctx["provenance"]["claims"], *opcodes]}
    claims = [_entry(objects[cid], kinds[cid]) for cid in objects]
    failed = {e["id"]: f for e in claims if (f := check_entry(e, objects[e["id"]], ctx))}
    if failed:
        raise LookupError(f"claims that break the state model: {failed}")
    model: dict[str, Any] = {
        "generated_by": "src/hijaiyyah/nui/hardware_state.py",
        "spec": "NUI/spec/hardware_state.json",
        "reads": ["NUI/hardware_provenance.json", spec["observed_opcodes"]["model"]],
        "live_sources": pctx["registry"]["live_sources"],
        "counts": {**{c: sum(1 for e in claims if e["category"] == c) for c in CATEGORIES},
                   "claims": len(claims), "observed_opcodes": len(opcodes),
                   "observed_opcodes_measured": sum(1 for o in opcodes
                                                    if o["status"] == "MEASURED")},
        "claims": claims, "observed_opcodes": opcodes}
    model["contract"] = []
    for row in spec["contract"]:
        _, group, subject = row["query"].split(" ", 2)
        model["contract"].append(answer(group, subject, model, ctx))
    return model


def verify(committed: dict[str, Any] | None = None) -> list[str]:
    committed = committed if committed is not None else json.loads(
        MODEL.read_text(encoding="utf-8"))
    try:
        fresh = json.loads(json.dumps(build()))
    except (LookupError, OSError, KeyError, ValueError) as why:
        return [f"the hardware state model no longer reads back: {why}"]
    return hardware._diff(committed, fresh)


def page(model: dict[str, Any]) -> str:
    spec = load()
    c = model["counts"]
    out = ["# Model keadaan hardware — Lapis 6.4", "",
           f"Dihasilkan `{model['generated_by']}` dari `{model['spec']}`, atas provenance "
           f"`{model['reads'][0]}` (6.3) dan kolom opcode papan `{model['reads'][1]}` (P3). "
           "Tidak ada RTL, port debug, bitstream, lari papan baru, atau telemetri baru yang "
           "disentuh untuknya.", "",
           "**Rekaman papan historis bukan keadaan hardware sekarang.** Lari papan terakhir "
           "menjawab apa yang terukur pada lari itu, bukan apa yang sedang terjadi. Sumber "
           f"live terdaftar: {len(model['live_sources'])}.", "",
           "## Empat jenis keadaan", "",
           "| kategori | arti | status klaim | menjawab kueri | klaim |", "|---|---|---|---|---|"]
    for name, cat in spec["categories"].items():
        out.append(f"| {name} | {cat['means']} | {', '.join(cat['status'])} | "
                   f"{', '.join(cat['answers_with'])} | {c[name]} |")
    out += ["", f"Precedence: **{' > '.join(spec['precedence'])}**. "
            f"{spec['precedence_why'][0].upper()}{spec['precedence_why'][1:]}.", "",
            "## Kontrak kueri", "",
            "| kueri | keadaan | dasar | provenance belum lengkap | alasan |",
            "|---|---|---|---|---|"]
    for a in model["contract"]:
        basis = ", ".join(f"`{i}`" for i in a["basis"]) or "—"
        inc = ", ".join(f"`{i}`" for i in a["incomplete_provenance"]) or "—"
        out.append(f"| `{a['query']}` | **{a['state']}** ({a['source_kind']}) | {basis} | "
                   f"{inc} | {a['reason'] or '—'} |")
    out += ["", "## Klasifikasi klaim 6.3", "",
            "| id | kategori | status | source_kind | verifikasi |", "|---|---|---|---|---|"]
    out += [f"| `{e['id']}` | {e['category']} | {e['status']} | {e['source_kind']} | "
            f"{e['verification']} |" for e in model["claims"] if not e["id"].startswith("P3:")]
    out += ["", "## Opcode teramati di papan — kolom P3", "",
            f"{c['observed_opcodes']} opcode dari kolom perangkat keras P3: "
            f"{c['observed_opcodes_measured']} dijalankan sekurangnya satu program yang dikirim "
            f"ke papan (MEASURED), {c['observed_opcodes'] - c['observed_opcodes_measured']} "
            "tidak pernah (UNKNOWN). Vonis kolomnya dibawa di klaim.", "",
            "| opcode | status | klaim | run_id |", "|---|---|---|---|"]
    out += [f"| `{o['id']}` | {o['status']} | {o['claim']} | "
            f"{'`' + o['run_id'] + '`' if o['run_id'] else '—'} |"
            for o in model["observed_opcodes"]]
    out += ["", "## Mengulang", "", "```bash",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.hardware_state --verify", "```"]
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
    print("\n".join(problems) if problems else "hardware state model reproduced exactly")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
