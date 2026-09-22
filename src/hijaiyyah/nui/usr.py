"""The semantic layer's specifications, read and held -- no command is run.

Three specifications the owner asked for on 22 September 2026, while the
burn-in holds the board, each a JSON file under NUI/spec/ that this module
reads rather than restates:

    usr.json            the Universal Semantic Representation -- five fields,
                        ACTION OBJECT TARGET CONTEXT STATE -- and the phrases
                        in three languages that reach it
    layer5_catalog.json USR -> the argv of a command on the Ubuntu host
    hc_kamus.json       HC's Arabic and Indonesian keywords, read per concept
                        in the owner's shape, and the token rules a parser for
                        them must follow

The owner's second message that day added three things this module now
measures rather than states: the example's HISA, compiled by HC's own compiler
and run on the interpreter; which dictionary entries reach HISA at all; and
the Hijaiyyah Registry (nui/registry.py), drawn onto the same page. HC stays
one language with three surfaces -- HCL is HC extended, not a second compiler.

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
HOST = "Ubuntu"     # the one CONTEXT with a command catalog behind it
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
    if usr.get("ACTION") and usr["ACTION"] not in actions:
        problems.append(f"unknown action: {usr['ACTION']}")
    obj = objects.get(usr.get("OBJECT", ""))
    if usr.get("OBJECT") and obj is None:
        problems.append(f"unknown object: {usr['OBJECT']}")
    target = usr.get("TARGET")
    if obj is not None:
        rule = obj["target"]
        if rule["required"] and not target:
            problems.append(f"{obj['name']} needs a target ({rule['kind']})")
        if rule["kind"] == "none" and target:
            problems.append(f"{obj['name']} takes no target")
    if target is not None and not isinstance(target, str):
        problems.append("target is not a string")
    elif target is not None and usr.get("CONTEXT", HOST) == HOST:
        # the argv rules: a host command reads the target, so they hold where
        # one would. In CONTEXT HC the target is an HC expression instead.
        if target.startswith("-"):
            problems.append("target starts with '-': a command would read it as an option")
        elif "\n" in target or "\x00" in target:
            problems.append("target holds a newline or NUL")
    contexts = {c["name"] for c in spec["contexts"]}
    if usr.get("CONTEXT") and usr["CONTEXT"] not in contexts:
        problems.append(f"unknown context: {usr['CONTEXT']}")
    states = {s["name"] for s in spec["states"]}
    if usr.get("STATE") and usr["STATE"] not in states:
        problems.append(f"unknown state: {usr['STATE']}")
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
    usr: dict[str, Any] = {"ACTION": verbs[words[0]], "OBJECT": objects[words[1]]}
    if len(words) > 2:
        usr["TARGET"] = " ".join(words[2:])
    return usr, ""


def to_argv(usr: dict[str, Any]) -> tuple[list[str] | None, str]:
    """USR -> the argv the host would run, or why not. Returns; never runs."""
    problems = validate(usr)
    if problems:
        return None, "; ".join(problems)
    if usr.get("CONTEXT", HOST) != HOST:
        return None, f"CONTEXT {usr['CONTEXT']} is not a host: no command is formed for it"
    action = next(a for a in load("usr")["actions"] if a["name"] == usr["ACTION"])
    if action["stage"] != 1:
        return None, f"{usr['ACTION']} is not allowed in layer 5's read-only first stage"
    entry = next((e for e in load("layer5_catalog")["entries"]
                  if (e["action"], e["object"]) == (usr["ACTION"], usr["OBJECT"])), None)
    if entry is None:
        return None, f"no catalog entry for {usr['ACTION']} {usr['OBJECT']}"
    allowed, forbidden = allowlist()
    if _command(entry["argv"], forbidden):
        return None, f"{entry['argv'][0]} is on the not-yet-allowed list"
    if not _command(entry["argv"], allowed):
        return None, f"{' '.join(entry['argv'])} is not on the read-only allowlist"
    argv = []
    # a catalog row may carry a second form for a target -- READ JOURNAL of
    # one unit, K-4 -- so the target never leaves a dangling option behind
    form = entry["argv_target"] if usr.get("TARGET") and "argv_target" in entry else entry["argv"]
    for part in form:
        if part == "{target}":
            if usr.get("TARGET"):
                argv.append(usr["TARGET"])
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
        "indonesian_keywords_used_as_names": sorted(names & {e["indonesia"] for e in kamus}),
        "keywords_outside_the_28": sorted(e["arabic"] for e in kamus
                                          if any(ch not in H28_SINGLE_CHARS for ch in e["arabic"])),
        "hc_names_missing": sorted(e["hc"] for e in kamus
                                   if e["hc"] not in KEYWORDS and e["hc"] not in builtins),
    }


def kamus() -> dict[str, dict[str, str]]:
    """The dictionary in the owner's shape, {CONCEPT: {hc, arabic, indonesia}} --
    a view of hc_kamus.json, which stays the one place it is written."""
    return {e["concept"]: {"hc": e["hc"], "arabic": e["arabic"], "indonesia": e["indonesia"]}
            for e in load("hc_kamus")["entries"]}


# -- HC -> HISA, measured with HC's own compiler ---------------------------------------

#: The smallest HC that uses each keyword -- probes of mine, used only to ask the
#: compiler whether the construct reaches HISA. None is part of the dictionary.
PROBES = {"let": "let x = 1;", "println": "println(1);",
          "if": "let x = 1;\nif x { println(x); }", "fn": "fn f(a) { return a; }"}


def lower(source: str) -> tuple[list[str], str]:
    """HC -> the instructions HC's compiler emits, or its error. The one
    compiler there is; nothing here translates."""
    from ..compiler import HCCompiler

    compiler = HCCompiler()
    result = compiler.compile_source(source)
    if not result.success:
        return [], "; ".join(result.errors)
    return [" ".join(line.split(";")[0].split()) for line in
            compiler._last_codegen.text.splitlines()
            if line.startswith(" ") and line.split(";")[0].strip()], ""


def _canonical(instructions: list[str]) -> list[str]:
    """`MOVI R1, #10` and `MOVI R1,10` are the same instruction."""
    return [re.sub(r"\s+", " ", i.replace("#", "").replace(",", ", ")).replace(" ,", ",").strip()
            for i in instructions if i.strip()]


def interpret(instructions: list[str]) -> list[int]:
    """What the HISA interpreter prints for them, in this process -- the
    second engine, not the compiler, says what the program does. No host
    command is involved."""
    from ..core.master_table import MASTER_TABLE
    from ..hisa.assembler import assemble
    from ..hisa.machine import HISAMachine

    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(assemble("\n".join(instructions)))
    machine.run()
    return list(machine.output)


def lowering() -> list[dict[str, Any]]:
    """Per dictionary entry: does HC's compiler take it to HISA today?"""
    out = []
    for e in load("hc_kamus")["entries"]:
        instructions, error = lower(PROBES[e["hc"]])
        # the generator closes every program with HALT (codegen.generate); it
        # belongs to no keyword, so it is not counted as one's
        body = instructions[:-1] if instructions[-1:] == ["HALT"] else instructions
        out.append({"hc": e["hc"], "concept": e["concept"], "probe": PROBES[e["hc"]],
                    "reaches_hisa": not error,
                    "opcodes": sorted({i.split()[0] for i in body}),
                    "error": error})
    return out


def surfaces() -> list[dict[str, Any]]:
    """How HC's lexer reads each Arabic and Indonesian keyword today -- the
    measure of what the design still needs, not a claim that it works."""
    from ..language import tokenize

    out = []
    for e in load("hc_kamus")["entries"]:
        row: dict[str, Any] = {"hc": e["hc"]}
        for lang in ("arabic", "indonesia"):
            toks = [t for t in tokenize(e[lang]) if t.type.name not in ("EOF", "NEWLINE")]
            row[lang] = [f"{t.type.name} {t.value}" for t in toks]
        out.append(row)
    return out


def example_chain() -> dict[str, Any]:
    """The owner's example, carried as far as the repository can carry it:
    the owner's HC through HC's compiler, held against the owner's HISA, and
    run. The Arabic -> HC step is the owner's own, not executed."""
    ex = load("hc_kamus")["examples"][0]
    instructions, error = lower(ex["hc"])
    owner = [line for line in ex["hisa"].splitlines() if line.strip()]
    return {"arabic": ex["source"], "hc": ex["hc"], "owner_hisa": owner,
            "compiled": instructions, "error": error,
            "same": _canonical(instructions) == _canonical(owner),
            "output": interpret(instructions) if not error else None}


# -- the page ---------------------------------------------------------------------


def _rows(items: list[dict[str, Any]], cols: list[str]) -> list[str]:
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for item in items:
        cells = []
        for c in cols:
            value = item.get(c, "")
            cells.append(f"`{value}`" if c in ("name", "hc", "ar", "id", "en", "action", "object",
                                              "arabic", "indonesia")
                         and value else str(value if value is not None else "--"))
        out.append("| " + " | ".join(cells) + " |")
    return out


def page() -> str:
    from . import registry

    usr, catalog, kamus_spec = load("usr"), load("layer5_catalog"), load("hc_kamus")
    allowed, forbidden = allowlist()
    hc = measure_hc()
    out = ["# Lapisan semantik -- USR, katalog Lapis 5, kamus HC, registry Hijaiyyah", "",
           "Ditarik dari `NUI/spec/*.json`, `NUI/hijaiyyah_registry.json`, dan dari "
           "pengukuran oleh `src/hijaiyyah/nui/usr.py`. Status `ditetapkan` milik pemilik; "
           "`usulan` menunggu pengesahan pemilik. Tidak ada perintah host yang dijalankan; "
           "contoh HC dijalankan di interpreter HISA, di dalam proses.", "",
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
           "", "### TARGET", "",
           *_rows([{**r, "applies_to": f"{r['applies_to']} ({r['applies_to_status']})"}
                   for r in usr["target_rules"]], ["rule", "applies_to", "status", "source"]),
           "", "### CONTEXT dan STATE", "",
           *_rows(usr["contexts"] + usr["states"], ["name", "status", "source"]),
           "", f"**Arti STATE, {usr['state_definition']['status']}.** "
           f"{usr['state_definition']['text']} Contoh: "
           f"`{json.dumps(usr['state_definition']['example'], ensure_ascii=False)}` "
           f"({usr['state_definition']['source']}).",
           "", "### Contoh pemilik", "",
           "Ketiganya sah menurut `validate()`, dan diperiksa tes.", ""]
    for ex in usr["examples"]:
        argv, why = to_argv(ex["usr"])
        said = f"argv `{' '.join(argv)}`, dikembalikan, tidak dijalankan" if argv else why
        out += ["```json", json.dumps(ex["usr"], ensure_ascii=False), "```",
                f"-> {said} ({ex['status']}; {ex['source']})", ""]
    out += ["### Kalimat -> USR", "",
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
    fmt = kamus_spec["format"]
    out += ["", "Perintah di daftar izin yang belum punya baris katalog: "
            + (", ".join(f"`{c}`" for c in unmapped_allowlist()) or "tidak ada") + ".", "",
            "## Kamus HC", "",
            f"{fmt['rule']} ({fmt['status']}; {fmt['source']}). Dibaca `usr.kamus()` dari "
            "`NUI/spec/hc_kamus.json`, satu-satunya tempat ia ditulis:", "",
            "```json", json.dumps(kamus(), ensure_ascii=False, indent=1), "```", "",
            *_rows([{**e, "concept": f"{e['concept']} ({e['concept_status']})"}
                    for e in kamus_spec["entries"]],
                   ["concept", "hc", "kind", "arabic", "indonesia", "status", "source"]),
            "", "Ditahan, belum kata kunci tiga bahasa:", "",
            *_rows(kamus_spec["withheld"], ["hc", "arabic", "indonesia", "status", "reason",
                                            "source"]),
            "", "Bukan HC:", "",
            *_rows(kamus_spec["not_hc"], ["name", "arabic", "indonesia", "status", "reason"]), "",
            "### Aturan token", "",
            *_rows(kamus_spec["token_rules"], ["rule", "status", "source"]), "",
            "### Contoh", ""]
    for ex in kamus_spec["examples"]:
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
            + (", ".join(hc["indonesian_keywords_used_as_names"]) or "tidak ada") + " |", ""]
    out += _surfaces_section() + _registry_section(registry.load())
    out += ["## Yang belum ditetapkan", ""]
    for source, spec in (("USR", usr), ("katalog", catalog), ("kamus", kamus_spec)):
        out += [f"- {source}: {q}" for q in spec["open"]]
    return "\n".join(out) + "\n"


def _surfaces_section() -> list[str]:
    chain = example_chain()
    kamus_spec = load("hc_kamus")["entries"]
    words = {lang: " ".join(e[lang] for e in kamus_spec) for lang in ("arabic", "indonesia")}
    out = ["## HC: satu inti, tiga permukaan", "",
           "HCL adalah HC yang diperluas, bukan bahasa baru (pemilik, 21 September 2026). "
           "Satu lexer, satu parser, satu evaluator, satu compiler ke HISA; kata kunci Arab "
           "dan Indonesia adalah lapisan sintaks di atasnya, dan implementasinya menunggu "
           "sesudah Lapis 5 (pemilik, 22 September 2026).", "",
           "```",
           "HC   lexer -> parser -> evaluator, dan compiler -> HISA",
           f"├── English     {' '.join(e['hc'] for e in kamus_spec):<32} berjalan hari ini",
           f"├── Arabic      {words['arabic']:<32} dirancang; lexer belum membacanya",
           f"└── Indonesian  {words['indonesia']:<32} dirancang; lexer belum membacanya",
           "```", "",
           "### Yang dibaca lexer HC hari ini", "",
           "Diukur, bukan diklaim: inilah yang harus diubah rancangannya.", "",
           "| hc | Arab dibaca sebagai | Indonesia dibaca sebagai |", "|---|---|---|"]
    for row in surfaces():
        out.append(f"| `{row['hc']}` | {', '.join(row['arabic'])} | "
                   f"{', '.join(row['indonesia'])} |")
    out += ["", "### Sampai HISA", "",
            "Tiap kata kunci ditanyakan ke compiler HC lewat program HC terkecil yang "
            "memakainya. Programnya milik saya, bukan bagian kamus.", "",
            "| hc | konsep | program uji | sampai HISA | opcode, atau alasan |",
            "|---|---|---|---|---|"]
    for row in lowering():
        what = ", ".join(f"`{o}`" for o in row["opcodes"]) if row["reaches_hisa"] else row["error"]
        out.append(f"| `{row['hc']}` | {row['concept']} | "
                   f"`{row['probe'].replace(chr(10), ' ')}` | "
                   f"{'ya' if row['reaches_hisa'] else '**tidak**'} | {what} |")
    out += ["", "### Contoh pemilik, dari ujung ke ujung", "",
            "Arab -> HC adalah terjemahan pemilik sendiri dan tidak dijalankan. HC -> HISA "
            "dikompilasi compiler HC, dibandingkan dengan HISA yang pemilik tulis, lalu "
            "dijalankan di interpreter.", "",
            "```", chain["arabic"].rstrip("\n"), "```", "",
            "```", chain["hc"].rstrip("\n"), "```", "",
            "| compiler HC | ditulis pemilik |", "|---|---|"]
    for got, owner in zip(chain["compiled"], chain["owner_hisa"], strict=True):
        out.append(f"| `{got}` | `{owner}` |")
    out += ["", f"Sama instruksi demi instruksi: **{'ya' if chain['same'] else 'tidak'}**. "
            f"Interpreter mencetak **{', '.join(map(str, chain['output'] or []))}**. RTL dan "
            "papan tidak dijalankan untuk contoh ini.", ""]
    return out


def _registry_section(records: list[dict[str, Any]]) -> list[str]:
    singular_tail = [r for r in records if r["operator"]["face"]["gf2"]["tail"] == 1
                     and r["operator"]["face"]["rank_gf2"] < 5]
    out = ["## Registry Hijaiyyah", "",
           "Huruf -> operator -> HC -> HISA, dibangun `src/hijaiyyah/nui/registry.py` ke "
           "`NUI/hijaiyyah_registry.json`. Tiap kolom dibaca dari tempatnya: Master Table, "
           "`OpCode.L_*` dan efeknya `H0 <- H0 + v(huruf)`, muka 5x5 lewat "
           "`core.exomatrix.matrix_order` (yang Codex JIM ukur), dan keluaran compiler HC. "
           f"{len(records)} huruf, karena Master Table dan slot 0xE0-0xFB memuat "
           f"{len(records)}; angka 29 di pesan pemilik adalah salah ketik (pemilik, 22 "
           "September 2026, pesan ketiga). Operatornya kedua representasi yang sudah ada, "
           "diterima pemilik pada pesan yang sama.", "",
           "| # | huruf | nama | instruksi | kata | rank GF(2) | periode GF(2) | "
           "periode GF(5) | HC | sebagai nama |",
           "|---:|---|---|---|---|---:|---:|---:|---|---|"]
    for r in records:
        ins, face = r["operator"]["instruction"], r["operator"]["face"]
        out.append(f"| {r['index']} | {r['char']} | {r['name']} | `{ins['mnemonic']}` "
                   f"`{ins['effect']}` | `{r['hisa']['word']}` | {face['rank_gf2']} | "
                   f"{face['gf2']['period']} | {face['gf5']['period']} | "
                   f"`{r['hc']['compiles_to']}` | "
                   f"{'ditolak parser' if r['hc']['as_a_name'] else '**diterima**'} |")
    out += ["", f"**Ekor 1 tidak berarti invertibel**, jadi rank dicatat sendiri: "
            f"{len(singular_tail)} huruf berekor 1 atas GF(2) dengan rank di bawah 5 -- "
            + ", ".join(r["name"] for r in singular_tail) + ". Docstring "
            "`matrix_order` dan `gf2_rank` di `src/hijaiyyah/core/exomatrix.py` membaca "
            "ekor 1 sebagai invertibel; itu benar untuk Jim dan Kha, tidak untuk yang lain. "
            "Selisih ini dicatat sebagai fakta Lapis 0, `nui.tail_one_is_not_invertibility`, "
            "yang dihitung ulang tiap lari tes; matematikanya tidak disunting, dan NUI tidak "
            "memakai \"ekor 1 berarti invertibel\" sebagai aturan sampai definisinya "
            "dibuktikan (pemilik, 22 September 2026, pesan ketiga).", ""]
    return out


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
