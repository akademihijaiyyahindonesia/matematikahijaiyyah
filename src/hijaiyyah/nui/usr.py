"""The semantic layer's specifications, read and held -- nothing is executed.

Three specifications the owner asked for on 22 September 2026, while the
burn-in holds the board, each a JSON file under NUI/spec/ that this module
reads rather than restates:

    usr.json            the Universal Semantic Representation -- five fields,
                        ACTION OBJECT TARGET CONTEXT STATE -- and the phrases
                        in three languages that reach it
    layer5_catalog.json USR -> the argv of a command on the Ubuntu host
    hc_kamus.json       HC's Arabic and Indonesian keywords, and the token
                        rules a parser for them must follow

Every entry carries a status and a source. "ditetapkan" is the owner's;
"usulan" is a proposal of mine awaiting the owner, and never passes for a
decision; "dinyatakan, belum diizinkan" is named by the owner but forbidden in
layer 5's read-only first stage.

-- nothing here runs a command ------------------------------------------------
to_argv() returns a list and stops. There is no host yet, layer 5 has not
started, and a module that could execute would be one mistake away from
running on this Mac. A test holds that no process-spawning module is
imported here. The target goes into argv as ONE element and never through a
shell, so `;`, `|` and `$(...)` mean nothing in it.

-- what is read, not copied ---------------------------------------------------
The read-only allowlist is the owner's table in NUI/LAYERS.md, layer 5, and
is parsed from there (R1). The facts about HC -- its keywords, its 28
letters, the programs in the repository -- are measured from the language
package at call time, so a page generated today says what HC is today.
"""
from __future__ import annotations

import json
import re
from itertools import pairwise
from typing import Any

from .repository_index import ROOT, tracked

SPEC = ROOT / "NUI" / "spec"
PAGE = ROOT / "NUI" / "SEMANTIK.md"
LAYERS = ROOT / "NUI" / "LAYERS.md"
Spec = dict[str, Any]


def load(name: str) -> Spec:
    data: Spec = json.loads((SPEC / f"{name}.json").read_text(encoding="utf-8"))
    return data


# -- the allowlist, from the owner's table --------------------------------------


def allowlist() -> tuple[list[str], list[str]]:
    """(allowed, not yet allowed) commands, from NUI/LAYERS.md's table."""
    lines = LAYERS.read_text(encoding="utf-8").splitlines()
    head = next(i for i, line in enumerate(lines)
                if line.startswith("| diizinkan | belum diizinkan"))
    row = lines[head + 2]
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    return (re.findall(r"`([^`]+)`", cells[0]), re.findall(r"`([^`]+)`", cells[1]))


def _command(argv: list[str], names: list[str]) -> str | None:
    """The longest listed command that argv starts with."""
    for name in sorted(names, key=len, reverse=True):
        words = name.split()
        if argv[:len(words)] == words:
            return name
    return None


# -- USR --------------------------------------------------------------------------


def validate(usr: dict[str, Any], spec: Spec | None = None) -> list[str]:
    """Every way `usr` breaks the specification, by name; empty if none."""
    spec = spec or load("usr")
    problems = []
    fields = {f["name"]: f for f in spec["fields"]}
    for key in usr:
        if key not in fields:
            problems.append(f"unknown field: {key}")
    for name, field in fields.items():
        if field["required"] and not usr.get(name):
            problems.append(f"missing field: {name}")
    actions = {a["name"] for a in spec["actions"]}
    objects = {o["name"]: o for o in spec["objects"]}
    if usr.get("action") and usr["action"] not in actions:
        problems.append(f"unknown action: {usr['action']}")
    obj = objects.get(usr.get("object", ""))
    if usr.get("object") and obj is None:
        problems.append(f"unknown object: {usr['object']}")
    target = usr.get("target")
    if obj is not None:
        rule = obj["target"]
        if rule["required"] and not target:
            problems.append(f"{obj['name']} needs a target ({rule['kind']})")
        if rule["kind"] == "none" and target:
            problems.append(f"{obj['name']} takes no target")
    if target is not None:
        if not isinstance(target, str):
            problems.append("target is not a string")
        elif target.startswith("-"):
            problems.append("target starts with '-': a command would read it as an option")
        elif "\n" in target or "\x00" in target:
            problems.append("target holds a newline or NUL")
    contexts = {c["name"] for c in spec["contexts"]}
    if usr.get("context") and usr["context"] not in contexts:
        problems.append(f"unknown context: {usr['context']}")
    states = {s["name"] for s in spec["states"]}
    if usr.get("state") and usr["state"] not in states:
        problems.append(f"unknown state: {usr['state']}")
    return problems


def parse_phrase(text: str, spec: Spec | None = None) -> tuple[dict[str, Any] | None, str]:
    """A phrase in Arabic, Indonesian or English -> USR, with only the
    vocabulary the specification holds. Nothing is guessed: an unknown word
    is refused and named."""
    spec = spec or load("usr")
    words = text.split()
    if len(words) < 2:
        return None, "a phrase needs a verb and an object"
    verbs = {w: v["action"] for v in spec["phrases"]["verbs"]
             for w in (v["ar"], v["id"], v["en"])}
    objects = {w: o["object"] for o in spec["phrases"]["objects"]
               for w in (o["ar"], o["id"], o["en"])}
    if words[0] not in verbs:
        return None, f"unknown verb: {words[0]}"
    if words[1] not in objects:
        return None, f"unknown object: {words[1]}"
    usr: dict[str, Any] = {"action": verbs[words[0]], "object": objects[words[1]]}
    if len(words) > 2:
        usr["target"] = " ".join(words[2:])
    return usr, ""


def to_argv(usr: dict[str, Any]) -> tuple[list[str] | None, str]:
    """USR -> the argv the host would run, or why not. Returns; never runs."""
    problems = validate(usr)
    if problems:
        return None, "; ".join(problems)
    action = next(a for a in load("usr")["actions"] if a["name"] == usr["action"])
    if action["stage"] != 1:
        return None, f"{usr['action']} is not allowed in layer 5's read-only first stage"
    entry = next((e for e in load("layer5_catalog")["entries"]
                  if (e["action"], e["object"]) == (usr["action"], usr["object"])), None)
    if entry is None:
        return None, f"no catalog entry for {usr['action']} {usr['object']}"
    allowed, forbidden = allowlist()
    if _command(entry["argv"], forbidden):
        return None, f"{entry['argv'][0]} is on the not-yet-allowed list"
    if not _command(entry["argv"], allowed):
        return None, f"{' '.join(entry['argv'])} is not on the read-only allowlist"
    argv = []
    for part in entry["argv"]:
        if part == "{target}":
            if usr.get("target"):
                argv.append(usr["target"])
        else:
            argv.append(part)
    return argv, entry["status"]


def unmapped_allowlist() -> list[str]:
    """Allowed commands no catalog entry uses yet."""
    allowed, _ = allowlist()
    used = {_command(e["argv"], allowed) for e in load("layer5_catalog")["entries"]}
    return [c for c in allowed if c not in used]


# -- HC, measured -------------------------------------------------------------------


def measure_hc() -> dict[str, Any]:
    """What the parser rules rest on, recounted from the repository."""
    from ..language import EXAMPLES, KEYWORDS, tokenize
    from ..language.evaluator import HCEvaluator
    from ..language.lexer import H28_SINGLE_CHARS
    from ..language.tokens import TokenType

    sources = [(ROOT / f).read_text(encoding="utf-8") for f in tracked("*.hc")]
    sources += [src for _name, _desc, src in EXAMPLES]
    bare = adjacent = 0
    names: set[str] = set()
    for src in sources:
        toks = tokenize(src)
        bare += sum(t.type == TokenType.HIJAIYYAH for t in toks)
        names |= {t.value for t in toks if t.type == TokenType.IDENTIFIER}
        adjacent += sum(1 for a, b in pairwise(toks)
                        if a.type == b.type == TokenType.HIJAIYYAH and a.line == b.line
                        and b.col == a.col + len(a.value))
    kamus = load("hc_kamus")["entries"]
    builtins = set(HCEvaluator().globals._values)
    return {
        "hc_sources": len(sources),
        "bare_letters": bare,
        "adjacent_letter_pairs": adjacent,
        "letters": len(H28_SINGLE_CHARS) + 1,          # the 27 single characters and هـ
        "indonesian_keywords_used_as_names": sorted(names & {e["id"] for e in kamus}),
        "keywords_outside_the_28": sorted(e["ar"] for e in kamus
                                          if any(ch not in H28_SINGLE_CHARS for ch in e["ar"])),
        "hc_names_missing": sorted(e["hc"] for e in kamus
                                   if e["hc"] not in KEYWORDS and e["hc"] not in builtins),
    }


# -- the page ---------------------------------------------------------------------


def _rows(items: list[dict[str, Any]], cols: list[str]) -> list[str]:
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for item in items:
        cells = []
        for c in cols:
            value = item.get(c, "")
            cells.append(f"`{value}`" if c in ("name", "hc", "ar", "id", "en", "action", "object")
                         and value else str(value if value is not None else "--"))
        out.append("| " + " | ".join(cells) + " |")
    return out


def page() -> str:
    usr, catalog, kamus = load("usr"), load("layer5_catalog"), load("hc_kamus")
    allowed, forbidden = allowlist()
    hc = measure_hc()
    out = ["# Lapisan semantik -- USR, katalog Lapis 5, kamus HC", "",
           "Ditarik dari `NUI/spec/*.json` dan dari pengukuran oleh "
           "`src/hijaiyyah/nui/usr.py`. Status `ditetapkan` milik pemilik; `usulan` "
           "menunggu pengesahan pemilik. Tidak ada perintah yang dijalankan.", "",
           "## USR", "",
           *_rows([{**f, "required": f"{f['required']} ({f['required_status']})"}
                   for f in usr["fields"]], ["name", "required", "status", "source"]), "",
           f"Huruf: {usr['case']['rule']} ({usr['case']['status']}; {usr['case']['source']}).",
           "", "### ACTION", "", *_rows(usr["actions"], ["name", "stage", "status", "source"]),
           "", "### OBJECT", "",
           *_rows([{**o, "target": f"{o['target']['kind']}"
                    + (", wajib" if o["target"]["required"] else "")
                    + f" ({o['target']['status']})"}
                   for o in usr["objects"]], ["name", "target", "status", "source"]),
           "", "### TARGET", "", *_rows(usr["target_rules"], ["rule", "status", "source"]),
           "", "### CONTEXT dan STATE", "",
           *_rows(usr["contexts"] + usr["states"], ["name", "status", "source"]),
           "", "### Kalimat -> USR", "",
           f"Tata kalimat: {usr['phrases']['grammar']} ({usr['phrases']['grammar_status']}).", "",
           *_rows(usr["phrases"]["verbs"], ["action", "ar", "id", "en", "status"]), "",
           *_rows(usr["phrases"]["objects"], ["object", "ar", "id", "en", "status"]), "",
           "## Katalog Lapis 5", "",
           f"Daftar izin dibaca dari {catalog['allowlist']}: diizinkan "
           + ", ".join(f"`{c}`" for c in allowed) + "; belum diizinkan "
           + ", ".join(f"`{c}`" for c in forbidden) + ".", "",
           "| USR | argv | di daftar izin | status | sumber |", "|---|---|---|---|---|"]
    for e in catalog["entries"]:
        ok = _command(e["argv"], allowed) is not None
        out.append(f"| `{e['action']} {e['object']}` | `{' '.join(e['argv'])}` | "
                   f"{'ya' if ok else '**tidak**'} | {e['status']} | {e['source']} |")
    out += ["", "Perintah di daftar izin yang belum punya baris katalog: "
            + (", ".join(f"`{c}`" for c in unmapped_allowlist()) or "tidak ada") + ".", "",
            "## Kamus HC", "",
            *_rows(kamus["entries"], ["hc", "kind", "ar", "id", "status", "source"]),
            "", "Bukan HC:", "", *_rows(kamus["not_hc"], ["name", "ar", "id", "reason"]), "",
            "### Aturan token", "", *_rows(kamus["token_rules"], ["rule", "status", "source"]), "",
            "### Contoh", ""]
    for ex in kamus["examples"]:
        shown = "`" + ex["hc"].strip().replace("\n", " ") + "`" if ex["hc"] else "tidak sah"
        out += ["```", ex["source"].rstrip("\n"), "```",
                f"-> {shown} ({ex['status']}; {ex['source_note']})", ""]
    out += ["### Diukur dari repositori", "", "| | |", "|---|---:|",
            f"| sumber HC (berkas `.hc` dan contoh bawaan) | {hc['hc_sources']} |",
            f"| huruf telanjang di dalamnya | {hc['bare_letters']} |",
            f"| huruf telanjang yang berdampingan | {hc['adjacent_letter_pairs']} |",
            f"| huruf yang lexer HC kenal | {hc['letters']} |",
            "| kata kunci Arab yang memuat huruf di luar 28 | "
            + (", ".join(f"`{w}`" for w in hc["keywords_outside_the_28"]) or "tidak ada") + " |",
            "| kata kunci Indonesia yang sudah dipakai sebagai nama | "
            + (", ".join(hc["indonesian_keywords_used_as_names"]) or "tidak ada") + " |",
            "", "## Yang belum ditetapkan", ""]
    for source, spec in (("USR", usr), ("katalog", catalog), ("kamus", kamus)):
        out += [f"- {source}: {q}" for q in spec["open"]]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    import sys
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--write":
        PAGE.write_text(page(), encoding="utf-8")
        print(f"page: {PAGE.relative_to(ROOT)}")
        return 0
    phrase = " ".join(args) or "baca file nginx.log"
    usr, why = parse_phrase(phrase)
    print(f"{phrase!r} -> {usr or why}")
    if usr:
        print(f"argv (not run): {to_argv(usr)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
