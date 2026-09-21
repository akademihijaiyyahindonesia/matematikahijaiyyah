"""The OFF database: cosmictera-build/OFF.md read as records -- never written by hand.

The owner asked for OFF's entries in one standard shape:

    {"id": "OFF-PRINT-SILICON", "status": "EH", "layer": 4,
     "evidence": [...], "reproduced": true, "fixed": false}

OFF.md stays the one place they are written (R1). This module reads it and
NUI/off_db.json is what it reads, rebuilt and compared by a test, so the two
cannot drift. Each field comes from the entry's own text, and a field the
text does not state is left empty rather than filled in:

    id          the owner's name for the entry, when it has one. Only
                OFF-PRINT-SILICON has one so far; no name is invented, and
                `key`, a slug of the heading, is what the others are found by
    status      the entry's own `Label:` line -- EH, AT
    layer       the NUI layer the entry says found or tracks it ("Lapis 4
                NUI"), if it says one
    evidence    the commits it cites that exist in git, and the files it
                cites that exist in the tree
    reproduced  null: OFF.md does not state it in a form a reader can check
                without judgement, and a guess here would be a claim
    fixed       false for every entry: OFF.md holds only what is still
                blocked (tests/test_integrity/test_build_list.py), so an
                entry that is here is not fixed
"""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from .repository_index import ROOT

OFF = ROOT / "cosmictera-build" / "OFF.md"
DB = ROOT / "NUI" / "off_db.json"
Record = dict[str, Any]


def _slug(text: str) -> str:
    return re.sub(r"[^0-9a-z]+", "-", text.lower()).strip("-")


def _existing_commits(hashes: list[str]) -> list[str]:
    if not hashes:
        return []
    out = subprocess.run(["git", "cat-file", "--batch-check"], cwd=ROOT, check=True,
                         input="\n".join(f"{h}^{{commit}}" for h in hashes),
                         capture_output=True, text=True).stdout.splitlines()
    return [h for h, line in zip(hashes, out, strict=True) if not line.endswith("missing")]


def entries() -> list[tuple[Record, str]]:
    """(record, the entry's text) for every ### entry of OFF.md."""
    lines = OFF.read_text(encoding="utf-8").splitlines()
    section = ""
    raw: list[tuple[str, int, str, list[str]]] = []
    for number, line in enumerate(lines, 1):
        if line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith("### "):
            raw.append((line[4:].strip(), number, section, []))
        elif raw and not line.startswith("## "):
            raw[-1][3].append(line)
    out = []
    for heading, number, sect, body_lines in raw:
        body = "\n".join(body_lines)
        named = re.match(r"(OFF-[A-Z0-9-]+)\s+—\s+(.*)", heading)
        title = named.group(2) if named else heading
        labels = re.findall(r"Label:\s*(?:\*\*|`)([A-Z]{2})(?:\*\*|`)", body)
        layer = re.search(r"Lapis (\d+) NUI", body)
        commits = sorted(set(re.findall(r"`([0-9a-f]{7})`", body)))
        files = sorted({p for p in re.findall(r"`([\w./-]+\.(?:py|v|vh|hasm|md|json|hex))`", body)
                        if "/" in p and (ROOT / p).exists()})
        out.append(({
            "key": _slug(title),
            "id": named.group(1) if named else None,
            "title": title,
            "section": sect,
            "status": labels[-1] if labels else None,
            "layer": int(layer.group(1)) if layer else None,
            "evidence": {"commits": _existing_commits(commits), "files": files},
            "reproduced": None,
            "fixed": False,
            "source": f"cosmictera-build/OFF.md:{number}",
        }, body))
    return out


def build() -> list[Record]:
    return [record for record, _ in entries()]


def write() -> None:
    DB.write_text(json.dumps(build(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> int:
    import sys
    if sys.argv[1:] == ["--write"]:
        write()
        print(f"database: {DB.relative_to(ROOT)}")
        return 0
    for r in build():
        print(f"{r['id'] or '-':<18} {r['status'] or '-':<3} layer={r['layer']} "
              f"{r['key'][:50]:<50} {r['source']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
