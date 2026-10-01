"""Layer 6.2: where telemetry really comes from -- and whether it is flowing now.

    PYTHONPATH=src python3 -m hijaiyyah.nui.telemetry_sources --write
    PYTHONPATH=src python3 -m hijaiyyah.nui.telemetry_sources --verify

The owner's step 6.2, 27 September 2026: an inventory of the sources that
already exist, not a hardware project. No debug port, no change to hcpu_top,
no new telemetry, no bitstream built to fill a field that has no source. And
the distinction everything else rests on:

    a source exists  is not  a source is streaming now

Three things are built from what is already committed:

    registry   each of the 27 fields of the owner's telemetry contract v1 --
               read from cosmictera/TELEMETRY.md, not copied -- with its
               source, source kind, live or historical, board run, evidence
               and SHA-256, and a status
    missing    the fields with no source, which stay UNKNOWN: nothing is filled
               in from an RTL signal's name or from a guess
    boundary   whether a name is historical board evidence, a live board
               source, simulated RTL telemetry, or unknown -- access()

NUI/spec/telemetry_sources.json maps each field to its kind and its board run;
the contract says whether the field has a source at all, and the two must
agree or nothing is built. No field is live today: the spec registers no live
source, because no board run is being observed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from . import layer6_addendum
from .hardware import _matching, _sha
from .repository_index import ROOT

SPEC = ROOT / "NUI" / "spec" / "telemetry_sources.json"
MODEL = ROOT / "NUI" / "telemetry_sources.json"
PAGE = ROOT / "NUI" / "TELEMETRY_SOURCES.md"
HISTORICAL, LIVE, SIMULATED, UNKNOWN = ("historical board evidence", "live board source",
                                        "simulated RTL telemetry", "unknown")


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SPEC.read_text(encoding="utf-8"))
    return data


def contract() -> list[dict[str, Any]]:
    """The contract's rows: field, what it says today, where from, and line."""
    c = load()["contract"]
    rows = []
    for n, line, m in _matching(c["file"], c["row"], c["section"]):
        rows.append({"field": m.group("field"), "today": m.group("today").strip(),
                     "origin": m.group("origin").strip(), "line": n,
                     "sha256": _sha(line.encode("utf-8"))})
    return rows


def _hash(path: str, cite: dict[str, str]) -> dict[str, Any]:
    """A file's hash, whole -- or for a Markdown page, only the lines cited."""
    if not path.endswith(".md"):
        return {"path": path, "sha256": _sha((ROOT / path).read_bytes())}
    if path not in cite:
        raise LookupError(f"{path} is cited without the lines it cites")
    hits = _matching(path, cite[path])
    if not hits:
        raise LookupError(f"{path} has no line matching {cite[path]!r}")
    return {"path": path, "lines": [n for n, _, _ in hits],
            "sha256": _sha("\n".join(line for _, line, _ in hits).encode("utf-8"))}


def _has_source(today: str) -> bool:
    return today.startswith("**ada")


def build() -> dict[str, Any]:
    spec = load()
    live = set(spec["live_sources"])
    rows = contract()
    missing_in_spec = [r["field"] for r in rows if r["field"] not in spec["fields"]]
    extra_in_spec = sorted(set(spec["fields"]) - {r["field"] for r in rows})
    if missing_in_spec or extra_in_spec:
        raise LookupError(f"the spec and the contract list different fields: "
                          f"{missing_in_spec} {extra_in_spec}")
    registry = []
    for row in rows:
        s = spec["fields"][row["field"]]
        sourced = s["source_kind"] != "none"
        if sourced != _has_source(row["today"]):
            raise LookupError(f"{row['field']}: the contract says {row['today'][:40]!r} "
                              f"but the spec says {s['source_kind']}")
        cite = s.get("cite", {})
        evidence = [{"path": spec["contract"]["file"], "lines": [row["line"]],
                     "sha256": row["sha256"]}] + [_hash(p, cite) for p in s["evidence"]]
        board = next((e for e in evidence if e["path"] == s["board_run"]), None)
        if sourced and board is None:
            raise LookupError(f"{row['field']}: its board run is not among its evidence")
        registry.append({
            "field": row["field"],
            "source": row["origin"],
            "source_kind": s["source_kind"],
            "live_or_historical": LIVE if row["field"] in live else
            (HISTORICAL if sourced else UNKNOWN),
            "board_run": s["board_run"],
            "evidence": evidence,
            "sha256": board["sha256"] if board else None,
            "status": "MEASURED" if sourced else "UNKNOWN",
            "note": s["note"]})
    rule = spec["rtl_signals"]
    signals = [{"name": m.group(1), "line": n, "boundary": SIMULATED, "status": "SIMULATED"}
               for n, _, m in _matching(rule["file"], rule["pattern"])]
    rtl = {"file": rule["file"], "sha256": _sha((ROOT / rule["file"]).read_bytes()),
           "signals": signals}
    measured = [r for r in registry if r["status"] == "MEASURED"]
    unknown = [r["field"] for r in registry if r["status"] == "UNKNOWN"]
    runs = sorted({r["board_run"] for r in measured})
    matrix = [
        {"source": "UART/Tang Nano board runs", "status": "MEASURED source",
         "coverage": f"{len(measured)}/{len(registry)} medan kontrak"},
        {"source": "historical board recordings", "status": "MEASURED evidence",
         "coverage": f"{len(runs)} lari papan atau halamannya, semuanya di-commit"},
        {"source": "live hardware telemetry sekarang", "status": "UNKNOWN / tidak mengalir",
         "coverage": f"{len(live)} sumber hidup terdaftar -- belum ada stream aktif"},
        {"source": f"{len(unknown)} medan tanpa sumber", "status": "UNKNOWN",
         "coverage": ", ".join(unknown)},
        {"source": "RTL telemetry signals tele_*", "status": "SIMULATED / available in design",
         "coverage": f"{len(signals)} sinyal -- bukan aliran papan yang hidup"},
    ]
    return {"generated_by": "src/hijaiyyah/nui/telemetry_sources.py",
            "spec": "NUI/spec/telemetry_sources.json",
            "contract": spec["contract"]["file"], "matrix": matrix, "registry": registry,
            "missing": [{"field": r["field"], "status": r["status"], "note": r["note"]}
                        for r in registry if r["status"] == "UNKNOWN"],
            "live_sources": sorted(live), "live_sources_why": spec["live_sources_why"],
            "rtl_signals": rtl, "boundary": spec["boundary"]}


def access(name: str, model: dict[str, Any] | None = None) -> str:
    """Which side of the live-access boundary a name is on: historical board
    evidence, a live board source, simulated RTL telemetry, or unknown."""
    model = model or json.loads(MODEL.read_text(encoding="utf-8"))
    for row in model["registry"]:
        if row["field"] == name:
            return str(row["live_or_historical"])
    if any(s["name"] == name for s in model["rtl_signals"]["signals"]):
        return SIMULATED
    return UNKNOWN


def verify(committed: dict[str, Any] | None = None) -> list[str]:
    """The registry as frozen, with its post-freeze addendum beside it,
    against what the contract and the evidence build today."""
    committed = committed if committed is not None else json.loads(
        MODEL.read_text(encoding="utf-8"))
    try:
        fresh = json.loads(json.dumps(build()))
    except (LookupError, OSError, KeyError) as why:
        return [f"the telemetry sources no longer read back: {why}"]
    return layer6_addendum.verify("telemetry_sources", fresh, committed)


def _diff(a: Any, b: Any, path: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in sorted(set(a) | set(b)) for d in _diff(a.get(k), b.get(k),
                                                                 f"{path}/{k}")]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b, strict=True))
                for d in _diff(x, y, f"{path}/{i}")]
    return [] if a == b else [path]


def page(model: dict[str, Any]) -> str:
    out = ["# Sumber telemetri — Lapis 6.2", "",
           f"Dihasilkan `{model['generated_by']}` dari `{model['spec']}` dan kontrak "
           f"`{model['contract']}`. Inventaris sumber, bukan modifikasi hardware: tidak ada "
           "port debug, perubahan `hcpu_top`, telemetri baru, atau bitstream yang dibuat "
           "untuknya. **Sumber yang ada tidak sama dengan sumber yang sedang mengalir.**", "",
           "## Matriks sumber", "", "| sumber | status | cakupan |", "|---|---|---|"]
    out += [f"| {m['source']} | **{m['status']}** | {m['coverage']} |" for m in model["matrix"]]
    out += ["", "## Registry — 27 medan kontrak", "",
            "| medan | status | batas akses | jenis sumber | sumber | lari papan | sha256 |",
            "|---|---|---|---|---|---|---|"]
    for r in model["registry"]:
        sha = f"`{r['sha256'][:12]}…`" if r["sha256"] else "—"
        run = f"`{r['board_run']}`" if r["board_run"] else "—"
        out.append(f"| `{r['field']}` | {r['status']} | {r['live_or_historical']} | "
                   f"{r['source_kind']} | {r['source']} | {run} | {sha} |")
    out += ["", "## Medan tanpa sumber — tetap UNKNOWN", "",
            "Tidak diisi dari nama sinyal RTL atau dari dugaan.", "",
            "| medan | status | kenapa |", "|---|---|---|"]
    out += [f"| `{m['field']}` | {m['status']} | {m['note']} |" for m in model["missing"]]
    rtl = model["rtl_signals"]
    out += ["", "## Sinyal telemetri RTL — tersedia di desain, bukan aliran hidup", "",
            f"`{rtl['file']}` `{rtl['sha256'][:12]}…`: "
            + ", ".join(f"`{s['name']}`" for s in rtl["signals"])
            + ". Tidak dipetakan ke medan kontrak mana pun.", "",
            "## Batas akses", ""]
    out += [f"- **{k}** — {v}." for k, v in model["boundary"].items()]
    out += ["", f"Sumber hidup yang terdaftar: {len(model['live_sources'])}. "
            f"{model['live_sources_why'][0].upper()}{model['live_sources_why'][1:]}.", "",
            "## Mengulang", "", "```bash",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.telemetry_sources --verify", "```"]
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
          f"telemetry sources reproduced exactly: the frozen record, and "
          f"{len(layer6_addendum.changes('telemetry_sources'))} changes of the post-freeze "
          "addendum")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
