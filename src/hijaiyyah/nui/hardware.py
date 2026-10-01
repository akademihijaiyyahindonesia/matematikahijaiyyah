"""Layer 6.1: the hardware inventory, built from evidence that already exists.

    PYTHONPATH=src python3 -m hijaiyyah.nui.hardware --write
    PYTHONPATH=src python3 -m hijaiyyah.nui.hardware --verify

The owner opened Layer 6, Hardware Intelligence, on 27 September 2026, and its
first step touches neither the RTL nor the board: take stock of what the
hardware is, from what is already recorded, and keep three classes apart --

    MEASURED   proven physically: a committed board record, a board-measured
               fact, or a section of PAPAN.md or OFF.md that records a board run
    SIMULATED  derived from the design: RTL, pin constraints, parameters, facts
               recomputed from the repository -- and nextpnr's synthesis and
               place-and-route results, marked PNR/build-derived: not a
               behavioural simulation and not a physical measurement (K-18)
    UNKNOWN    no path observes it -- and so no value

NUI/spec/hardware_inventory.json says where each item is read, never what it
is: a line of a file by pattern, a JSON key, a sealed fact, or a count of
lines. This module reads it and writes, for every item, the chain the owner
asked for -- hardware, evidence, source, measurement or run, hash:

    value     what the source says, read now
    source    the file and line it was read from
    evidence  every file it rests on, with its SHA-256 -- the whole file for
              records, code and facts, and only the lines cited for a Markdown
              page, so an unrelated edit of a page does not move the hash; the
              source is hashed the same way
    run       the board run or measurement it comes from, when there is one

Nothing is added to find a value: no sensor, no debug port, no new telemetry.
What has no evidence stays UNKNOWN.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from . import layer6_addendum
from .repository_index import ROOT

SPEC = ROOT / "NUI" / "spec" / "hardware_inventory.json"
MODEL = ROOT / "NUI" / "hardware_inventory.json"
PAGE = ROOT / "NUI" / "HARDWARE.md"
CLASSES = ("MEASURED", "SIMULATED", "UNKNOWN")


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SPEC.read_text(encoding="utf-8"))
    return data


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fact_path(fact_id: str) -> str:
    domain, name = fact_id.split(".", 1)
    return f"facts/{domain}/{name}.json"


def _lines(path: str) -> list[str]:
    return (ROOT / path).read_text(encoding="utf-8").splitlines()


def _matching(path: str, pattern: str,
              section: str | None = None) -> list[tuple[int, str, re.Match[str]]]:
    """Lines of a file matching a pattern -- within one Markdown section when
    `section` names its heading, from that heading to the next of its level."""
    rx = re.compile(pattern)
    lines = list(enumerate(_lines(path), 1))
    if section is not None:
        head = re.compile(section)
        start = next((i for i, (_, ln) in enumerate(lines) if head.search(ln)), None)
        if start is None:
            return []
        level = len(lines[start][1]) - len(lines[start][1].lstrip("#"))
        end = next((i for i, (_, ln) in enumerate(lines[start + 1:], start + 1)
                    if ln.startswith("#") and len(ln) - len(ln.lstrip("#")) <= level),
                   len(lines))
        lines = lines[start:end]
    return [(n, line, m) for n, line in lines if (m := rx.search(line)) is not None]


def read(rule: dict[str, Any] | None) -> tuple[Any, dict[str, Any] | None]:
    """One item's value and where it was read, by its rule."""
    if rule is None:
        return None, None
    if "file" in rule:
        hits = _matching(rule["file"], rule["pattern"])
        if not hits:
            raise LookupError(f"{rule['file']}: nothing matches {rule['pattern']!r}")
        n, _, m = hits[0]
        return (m.group(1) if m.groups() else m.group(0)), {"path": rule["file"], "line": n}
    if "count" in rule:
        hits = _matching(rule["count"], rule["pattern"], rule.get("section"))
        if not hits:
            raise LookupError(f"{rule['count']}: nothing matches {rule['pattern']!r}")
        return len(hits), {"path": rule["count"], "line": hits[0][0]}
    if "json" in rule:
        value: Any = json.loads((ROOT / rule["json"]).read_text(encoding="utf-8"))
        for part in rule["key"].split("."):
            value = value[part]
        return value, {"path": rule["json"], "key": rule["key"]}
    if "fact" in rule:
        path = fact_path(rule["fact"])
        return json.loads((ROOT / path).read_text(encoding="utf-8"))["value"], {"path": path,
                                                                                "key": "value"}
    raise ValueError(f"no way to read {rule}")


def _evidence(path: str, item: dict[str, Any]) -> dict[str, Any]:
    """One evidence file and its hash: the whole file, or for a Markdown page
    only the lines the item cites -- its value's lines, or the lines its
    `cite` pattern names."""
    if not path.endswith(".md"):
        return {"path": path, "sha256": _sha((ROOT / path).read_bytes())}
    rule = item.get("value") or {}
    pattern = (rule.get("pattern") if path in (rule.get("file"), rule.get("count"))
               else item.get("cite", {}).get(path))
    if pattern is None and rule.get("json") == path:
        return {"path": path, "sha256": _sha((ROOT / path).read_bytes())}
    if pattern is None:
        raise LookupError(f"{item['id']}: {path} is cited without the lines it cites")
    section = rule.get("section") if path == rule.get("count") else None
    hits = _matching(path, pattern, section)
    if not hits:
        raise LookupError(f"{item['id']}: {path} has no line matching {pattern!r}")
    return {"path": path, "lines": [n for n, _, _ in hits],
            "sha256": _sha("\n".join(line for _, line, _ in hits).encode("utf-8"))}


def build() -> dict[str, Any]:
    spec = load()
    items = []
    for item in spec["items"]:
        value, source = read(item["value"])
        if source is not None:
            source["sha256"] = _evidence(source["path"], item)["sha256"]
        items.append({"id": item["id"], "hardware": item["hardware"],
                      "answers": item["answers"], "class": item["class"],
                      "evidence_kind": item["evidence_kind"], "value": value,
                      "source": source,
                      "evidence": [_evidence(p, item) for p in item["evidence"]],
                      "run": item["run"], "why": item["why"]})
    counts = {c: sum(1 for i in items if i["class"] == c) for c in CLASSES}
    return {"generated_by": "src/hijaiyyah/nui/hardware.py",
            "spec": "NUI/spec/hardware_inventory.json",
            "questions": spec["questions"], "counts": counts, "items": items}


def verify(committed: dict[str, Any] | None = None) -> list[str]:
    """What the evidence says today against what the inventory wrote down:
    the frozen record and, beside it, the post-freeze addendum (the owner,
    1 October 2026). Paths that differ, and whatever keeps the addendum from
    standing, are returned."""
    committed = committed if committed is not None else json.loads(
        MODEL.read_text(encoding="utf-8"))
    try:
        fresh = json.loads(json.dumps(build()))
    except (LookupError, OSError, KeyError) as why:
        return [f"the inventory no longer reads back: {why}"]
    return layer6_addendum.verify("hardware", fresh, committed)


def _diff(a: Any, b: Any, path: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in sorted(set(a) | set(b)) for d in _diff(a.get(k), b.get(k),
                                                                 f"{path}/{k}")]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b, strict=True))
                for d in _diff(x, y, f"{path}/{i}")]
    return [] if a == b else [path]


def _where(source: dict[str, Any] | None) -> str:
    if source is None:
        return "—"
    return f"`{source['path']}:{source['line']}`" if "line" in source else \
        f"`{source['path']}#{source['key']}`"


def page(model: dict[str, Any]) -> str:
    """NUI/HARDWARE.md, drawn from the model only; the headings and the fixed
    sentences are the only words not taken from it."""
    c = model["counts"]
    out = ["# Inventaris hardware — Lapis 6.1", "",
           f"Dihasilkan `{model['generated_by']}` dari `{model['spec']}`. Tidak ada RTL, "
           "papan, sensor, port debug, atau telemetri baru yang disentuh untuknya: tiap "
           "nilai dibaca dari bukti yang sudah ada.", "",
           f"**{c['MEASURED']} MEASURED** (dibuktikan secara fisik), **{c['SIMULATED']} "
           "SIMULATED** (RTL atau interpreter — dan hasil synthesis, place-and-route, dan "
           "analisis build yang ditandai `PNR/build-derived`: **bukan simulasi perilaku "
           "dan bukan pengukuran fisik**, K-18), "
           f"**{c['UNKNOWN']} UNKNOWN** (belum ada jalur observasi, jadi tanpa nilai).", ""]
    for key, question in model["questions"].items():
        out += [f"## {question}", "",
                "| hardware | nilai | kelas | jenis bukti | sumber | run | bukti |",
                "|---|---|---|---|---|---|---|"]
        for i in model["items"]:
            if key not in i["answers"]:
                continue
            value = "—" if i["value"] is None else f"`{i['value']}`"
            proof = "<br>".join(f"`{e['path']}` `{e['sha256'][:12]}…`" for e in i["evidence"])
            out.append(f"| {i['hardware']} | {value} | {i['class']} | {i['evidence_kind']} | "
                       f"{_where(i['source'])} | {i['run'] or '—'} | {proof} |")
        out.append("")
    out += ["## Kenapa", ""]
    out += [f"- `{i['id']}` — {i['why']}." for i in model["items"]]
    out += ["", "## Mengulang", "", "```bash",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.hardware --verify", "```"]
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
          f"hardware inventory reproduced exactly: the frozen record, and "
          f"{len(layer6_addendum.changes('hardware'))} changes of the post-freeze "
          "addendum")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
