"""NUI's knowledge base: what the repository already knows about one thing,
grouped by where that knowledge lives, with where each piece comes from.

    python3 -m hijaiyyah.nui.knowledge opcode PRINT
    python3 -m hijaiyyah.nui.knowledge program rtl/programs/loader.hasm
    python3 -m hijaiyyah.nui.knowledge off OFF-PRINT-SILICON
    python3 -m hijaiyyah.nui.knowledge letter ج
    python3 -m hijaiyyah.nui.knowledge hc متغير
    python3 -m hijaiyyah.nui.knowledge term HCPU
    python3 -m hijaiyyah.nui.knowledge file NUI/board_expected.json
    python3 -m hijaiyyah.nui.knowledge rtl hcpu_top
    python3 -m hijaiyyah.nui.knowledge board latest
    python3 -m hijaiyyah.nui.knowledge host services
    python3 -m hijaiyyah.nui.knowledge host delta processes
    python3 -m hijaiyyah.nui.knowledge hardware current-state
    python3 -m hijaiyyah.nui.knowledge hardware current program
    python3 -m hijaiyyah.nui.knowledge hardware correlation opcode PRINT

The owner's two shapes, both of 22 September 2026. The first is an answer:

    {"query": "opcode PRINT", "facts": [...], "tests": [...], "board_findings": [...]}

The second, later the same day, is how the knowledge is organised:

    Knowledge
    ├── HC       the language: keywords, built-ins, the three-language
    │            dictionary, and what HC's compiler takes to HISA
    ├── HISA     the instruction set: each opcode's definition, and what the
    │            interpreter did with it (layer 3)
    ├── RTL      the Verilog, and whether it agrees with the interpreter (layer 4)
    ├── OFF      what is blocked or not there yet (cosmictera-build/OFF.md)
    ├── PAPAN    what ran on the physical board and what came back
    ├── NUI      NUI's own inventory: the facts of layer 0, the Hijaiyyah
    │            Registry, and the USR specification
    └── HOST     the host and OS being observed: processes, services,
                 network, filesystem, runtime -- added by the owner's K-6

OFF stays what does not depend on an active host. The owner's K-6 also says
no HOST fact goes in before a collector has measured it. So HOST reads one
place only, the observations layer 5's collectors wrote to the K-11 store on
the host, outside this repository -- never facts/, which NUI reads -- and of
those only the main instance's own: an observation is (vm_name, run_id),
K-16, 27 September 2026. The two
are the two classes of provenance the owner named on 26 September 2026 (P8.5):
facts/ sealed engineering facts, observations/ runtime HOST evidence, and the
test that files every item by its source keeps them apart. A HOST item is one
observation that passed its checks -- run, collector, evidence file, time and
SHA-256 -- and a HOST question no observation supports stays `unknown`,
because the evidence is not enough, not because the host is missing (K-14).

The latest applies, so an answer carries the seven domains as its keys; the
first shape's `facts` now sit under NUI, where the facts inventory lives, and
its `board_findings` under PAPAN. `tests` stays beside the domains -- a test is
how an item is verified, not a place it is held -- and `unknown` holds what no
domain can say, never filled in.

The owner's seven questions of 22 September 2026 -- what is HCPU, what does
this opcode do, which program does this file come from, what does this
program call, what does this RTL module instantiate, what did the board last
measure, which services does this Ubuntu run -- are mapped to query kinds in
NUI/spec/query_contract.json, the contract a test holds this module to. An
answer walks back the owner's chain: the fact is the item, its `source` the
place it was read, `evidence` the line or relation where one applies, and the
verification the test the contract names.

A hardware question (layer 6.3, 27 September 2026) is answered from the
provenance model alone: each item is one canonical provenance object -- claim,
source kind, board run, evidence, observed_at, SHA-256, status -- filed where
its evidence lives, and what the hardware is doing now is `unknown`, because
no live source is registered, never the newest historical run. Asked by a
kind of state (layer 6.4) -- `hardware identity|capability|observed|current|
provenance <subject>` -- the answer carries one headline state by the owner's
precedence over the claims of that kind, and a current question is answered by
a live source or not at all. And `hardware correlation <hardware|program|
opcode|run> <subject>` (layer 6.5) walks the links between them -- each one
DIRECT, DERIVED or UNKNOWN, none drawn from a name.

Nothing is inferred and nothing is scored. Every item is a lookup in something
the repository already holds, and every item carries `source` -- a file and
line, or a model and key -- so an answer walks back to its evidence. DOMAINS
names what each domain reads, and a test holds every item to it.
"""
from __future__ import annotations

import json
import re
from typing import Any

from . import off_db, registry, usr
from .facts import load as load_facts
from .repository_index import ROOT, tracked

KINDS = ("opcode", "program", "off", "letter", "hc", "term", "file", "rtl", "board", "host",
         "hardware")
EXECUTION = ROOT / "NUI" / "execution_model.json"
PARITY = ROOT / "NUI" / "parity_model.json"
OPCODES = "src/hijaiyyah/hisa/opcodes.py"
Answer = dict[str, Any]

#: The owner's seven domains, and the places each one reads -- regular
#: expressions over an item's source. HASM programs are HISA; everything else
#: under rtl/ is RTL. The parity model is read by three: its interpreter column
#: is HISA, its RTL column RTL, its board column PAPAN. HOST reads only the
#: observations in the K-11 store, `observations/<run_id>/...` (K-6, K-11),
#: which no other domain reads; facts/ is NUI's, and never HOST's (P8.5).
DOMAINS: dict[str, tuple[str, ...]] = {
    "HC": (r"src/hijaiyyah/language/", r"src/hijaiyyah/compiler/", r"NUI/spec/hc_kamus\.json"),
    "HISA": (r"src/hijaiyyah/hisa/", r"docs/HISA_SPEC\.md", r"NUI/execution_model\.json",
             r"NUI/parity_model\.json", r"rtl/programs/", r"<"),
    "RTL": (r"rtl/(?!programs/)", r"NUI/parity_model\.json"),
    "OFF": (r"cosmictera-build/OFF\.md",),
    "PAPAN": (r"cosmictera-build/", r"NUI/parity_model\.json"),
    "NUI": (r"facts/", r"NUI/", r"src/hijaiyyah/nui/", r"teknologi/ISTILAH\.md"),
    "HOST": (r"observations/",),
}
CONTRACT = ROOT / "NUI" / "spec" / "query_contract.json"


def _json(path: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _empty() -> Answer:
    return {**{d: [] for d in DOMAINS}, "tests": [], "unknown": []}


def _lines(path: str, pattern: str, limit: int = 20) -> list[dict[str, Any]]:
    """Lines of a tracked file matching `pattern`, as file:line sources."""
    out = []
    text = (ROOT / path).read_text(encoding="utf-8", errors="replace").splitlines()
    for number, line in enumerate(text, 1):
        if re.search(pattern, line):
            out.append({"text": line.strip()[:160], "source": f"{path}:{number}"})
            if len(out) >= limit:
                break
    return out


def _facts(words: list[str]) -> list[dict[str, Any]]:
    out = []
    for fact in load_facts():
        haystack = " ".join([fact.fact_id, fact.statement, *fact.source])
        if any(re.search(rf"(?<![\w.]){re.escape(w)}(?![\w])", haystack) for w in words):
            out.append({"what": "fact", "fact_id": fact.fact_id, "statement": fact.statement,
                        "status": fact.status, "confidence": fact.confidence,
                        "source": str(fact.path.relative_to(ROOT)) if fact.path else ""})
    return out


def _tests(pattern: str) -> list[dict[str, Any]]:
    out = []
    for path in tracked("tests/*.py"):
        hits = _lines(path, pattern, limit=1000)
        if hits:
            out.append({"file": path, "lines": len(hits), "first": hits[0]["text"],
                        "source": hits[0]["source"]})
    return out


def _off(words: list[str]) -> list[dict[str, Any]]:
    out = []
    for record, body in off_db.entries():
        text = record["title"] + "\n" + body
        if any(re.search(rf"(?<![\w.]){re.escape(w)}(?![\w])", text) for w in words):
            out.append({k: record[k] for k in ("id", "key", "title", "status", "layer",
                                               "source")})
    return out


def _definition(name: str) -> dict[str, Any] | None:
    """The line of src/hijaiyyah/hisa/opcodes.py that defines `name`."""
    hit = _lines(OPCODES, rf"^\s+{re.escape(name)}\s+=\s+0x", limit=1)
    if not hit:
        return None
    value = re.search(r"=\s+(0x[0-9A-Fa-f]+)", hit[0]["text"])
    comment = hit[0]["text"].partition("#")[2].strip()
    return {"what": "definition", "opcode": name, "value": value.group(1) if value else None,
            "does": comment or None, "source": hit[0]["source"]}


# -- opcode ------------------------------------------------------------------------


def _opcode(name: str) -> Answer:
    answer = _empty()
    definition = _definition(name)
    if definition:
        answer["HISA"].append(definition)
    answer["HISA"] += [{"what": "specification", **line}
                       for line in _lines("docs/HISA_SPEC.md", rf"\|\s*`{re.escape(name)}`\s*\|",
                                          limit=5)]
    ran = [e for e in _json(EXECUTION)["edges"]
           if e["kind"] == "EXECUTES" and e["target"] == f"opcode:{name}"]
    answer["HISA"].append({"what": "execution", "programs": len(ran),
                           "first": [{"program": e["source"], "step": e["step"],
                                      "source": e["where"]} for e in ran[:5]],
                           "source": "NUI/execution_model.json"})
    for row in usr.lowering():
        if name in row["opcodes"]:
            entry = usr.kamus()[row["concept"]]
            answer["HC"].append({"what": "dictionary", "concept": row["concept"], **entry,
                                 "probe": row["probe"], "source": "NUI/spec/hc_kamus.json"})
    letter = next((r for r in registry.load()
                   if r["operator"]["instruction"]["mnemonic"] == name), None)
    if letter:
        answer["HC"].append({"what": "letter literal", "literal": letter["char"],
                             "compiles_to": letter["hc"]["compiles_to"],
                             "source": letter["hc"]["source"]})
        answer["NUI"].append({"what": "registry", "index": letter["index"],
                              "char": letter["char"], "name": letter["name"],
                              "source": "NUI/hijaiyyah_registry.json"})
    answer["NUI"] += _facts([name])
    answer["OFF"] = _off([name])
    answer["tests"] = _tests(rf"\bOpCode\.{name}\b")
    if not ran:
        answer["unknown"].append("no program in layer 3's corpus executes it")

    parity = _json(PARITY)
    row = parity["opcodes"].get(name)
    if row is None:
        answer["unknown"].append(f"{name} is not an opcode the parity model knows")
        return answer
    model = f"NUI/parity_model.json#opcodes/{name}"
    answer["HISA"].append({"what": "interpreter", "python": row.get("python"), "source": model})
    answer["RTL"].append({"what": "parity", "in_rtl": row.get("in_rtl"), "rtl": row.get("rtl"),
                          "mismatches": len(row["mismatches"]), "reason": row.get("reason"),
                          "note": row.get("note"), "model": model,
                          "source": row.get("source") or model})
    answer["PAPAN"].append({"what": "board", "board": row.get("board"),
                            "overall": row.get("status"), "source": model})
    for m in row.get("board_mismatches", []):
        answer["PAPAN"].append({"what": "board mismatch", "value": m.get("value"),
                                "board": m["board"], "interpreter": m["interpreter"],
                                "rtl": m["rtl"], "date": m["date"], "source": m["record"]})
    for program in row["board_programs"]:
        rec = next((r for r in parity["board"] if r["program"] == program and "value" not in r),
                   None)
        if rec:
            answer["PAPAN"].append({"what": "board run", "program": program,
                                    "board": rec["board"], "status": rec["status"],
                                    "date": rec["date"], "source": rec["record"]})
    if row["board"] == "UNKNOWN":
        answer["unknown"].append("no board record covers it yet: the board parity run waits "
                                 "for the burn-in")
    return answer


# -- program -----------------------------------------------------------------------


def _resolve(program: str) -> str | None:
    """A path, or a basename that names exactly one program. A program layer 3
    ran in more than one scenario -- loader.hasm alone and with a payload --
    is still one program."""
    paths = {p.split("#")[0] for p in _json(EXECUTION)["programs"]}
    if program in paths:
        return program
    hits = sorted(p for p in paths if p.endswith("/" + program))
    return hits[0] if len(hits) == 1 else None


def _control(edges: list[dict[str, Any]], program: str) -> list[dict[str, Any]]:
    """How a run hands control on: CALLS, RESUMES, TRAPS, and the stores into
    TRAP_EPC and TRAP_MODE that set a resume up."""
    wanted = []
    for e in sorted(edges, key=lambda e: e["step"]):
        if e["source"] != program:
            continue
        setup = e["kind"] == "WRITES" and str(e["target"]).startswith(
            ("mmio:TRAP_EPC", "mmio:TRAP_MODE"))
        if e["kind"] in ("CALLS", "RESUMES", "TRAPS") or setup:
            wanted.append({"step": e["step"], "kind": e["kind"], "target": e["target"],
                           "source": e["where"]})
    return wanted[:12]


def _program(given: str) -> Answer:
    answer = _empty()
    path = _resolve(given)
    if path is None:
        answer["unknown"].append(f"{given} names no program layer 3 ran, or names several")
        return answer
    base = path.split("/")[-1]
    execution = _json(EXECUTION)
    for scenario in (p for p in execution["programs"] if p.split("#")[0] == path):
        answer["HISA"].append({"what": "execution", "scenario": scenario,
                               **execution["programs"][scenario],
                               "control": _control(execution["edges"], scenario),
                               "source": f"NUI/execution_model.json#programs/{scenario}"})
    from .program_graph import hasm_calls
    from .program_index import programs
    if path in programs().hasm:
        calls, missing = hasm_calls(path)
        for link in calls:
            answer["HISA"].append({"what": "calls", "label": link.via.split(" ", 1)[1],
                                   "defined_in": link.target.rsplit(":", 1)[0],
                                   "source": f"{path}:{link.line}"})
        answer["unknown"] += [f"CALL {label} at line {line} lands on no label"
                              for label, line in missing]
    parity = _json(PARITY)
    if path in parity["programs"]:
        row = parity["programs"][path]
        answer["RTL"].append({"what": "parity", "status": row["status"],
                              "first_divergence": row["first_divergence"],
                              "reason": row["reason"],
                              "source": f"NUI/parity_model.json#programs/{path}"})
    stem = re.escape(base.rsplit(".", 1)[0])
    # A board record names a program by its repository path or by its stem, in backticks and
    # nothing else: PAPAN.md writes `rtl/programs/hfs_lifecycle.hasm`, which a pattern taking only
    # the stem missed, and the closing backtick keeps `hal` from matching `hal_sd`.
    answer["PAPAN"] = [{"what": "board record", **line}
                       for line in _lines("cosmictera-build/PAPAN.md",
                                          rf"`(?:{re.escape(path)}|{stem}(?:\.hasm)?)`")]
    answer["PAPAN"] += [{"what": "board run", "board": r["board"], "status": r["status"],
                         "date": r["date"], "source": r["record"]}
                        for r in parity["board"] if r["program"] == path]
    # The board parity run's own report, the record parity_model.json names in board_corpus. Its
    # row is shown when nothing above names the program, and always when it says "not sent": a
    # program can have run on the board in another run and still be absent from this one.
    record = (parity.get("board_corpus") or {}).get("record")
    report = f"cosmictera-build/parity-board/{record}-parity.report.json" if record else None
    board_row = (_json(ROOT / report)["programs"].get(path)
                 if report and (ROOT / report).is_file() else None)
    found = bool(answer["PAPAN"])
    if board_row is not None:
        sent = not str(board_row.get("reason", "")).startswith("not sent")
        if not sent:
            answer["PAPAN"].append({"what": "board parity run: not sent", "record": record,
                                    "reason": board_row.get("reason", ""),
                                    "source": f"{report}#programs/{path}"})
        elif not found:
            answer["PAPAN"].append({"what": "board parity run", "record": record,
                                    "status": board_row["status"],
                                    "reason": board_row.get("reason", ""),
                                    "source": f"{report}#programs/{path}"})
    answer["NUI"] = _facts([base, path])
    answer["OFF"] = _off([base])
    answer["tests"] = _tests(rf"\b{re.escape(base)}\b")
    if not found and not any(i["what"] == "board parity run" for i in answer["PAPAN"]):
        # Neither of these is "never run". What was searched is PAPAN.md (directly, and through the
        # parity model's board rows, which it reads) and the board parity run's report -- and a
        # report row that says "not sent" is a row, so it is not reported as missing.
        if board_row is not None:
            answer["unknown"].append(
                "no board record of it was found in cosmictera-build/PAPAN.md, and the board "
                f"parity run {record} did not send it; neither says whether it ever ran on the "
                "board")
        else:
            answer["unknown"].append(
                "no board record of it was found in cosmictera-build/PAPAN.md or in the board "
                "parity run's report; that does not say it never ran on the board")
    return answer


# -- OFF entry ---------------------------------------------------------------------


def _off_entry(key: str) -> Answer:
    answer = _empty()
    for record, body in off_db.entries():
        if key in (record["id"], record["key"]):
            answer["OFF"] = [record]
            words = [w for w in re.findall(r"`([A-Z_]{3,})`", body) if w.isupper()][:5]
            answer["NUI"] = _facts(words) if words else []
            return answer
    answer["unknown"].append(f"no OFF entry has the id or key {key}")
    return answer


# -- letter, from the Hijaiyyah Registry --------------------------------------------


def _letter(given: str) -> Answer:
    record = next((r for r in registry.load() if given in (r["char"], r["name"])), None)
    if record is None:
        answer = _empty()
        answer["unknown"].append(f"{given} is not one of the registry's "
                                 f"{len(registry.load())} letters")
        return answer
    ins = record["operator"]["instruction"]
    answer = _opcode(ins["mnemonic"])
    answer["NUI"] = [{"what": "registry", **{k: record[k] for k in ("index", "char", "name",
                                                                    "codex")},
                      "face": record["operator"]["face"],
                      "source": "NUI/hijaiyyah_registry.json"},
                     *_facts([record["name"]])]
    answer["HC"] = [{"what": "letter literal", "literal": record["char"],
                     "compiles_to": record["hc"]["compiles_to"],
                     "as_a_name": record["hc"]["as_a_name"], "source": record["hc"]["source"]}]
    answer["HISA"].insert(1, {"what": "letter instruction", "effect": ins["effect"],
                              "word": record["hisa"]["word"], "source": ins["source"]})
    return answer


# -- HC word, from the dictionary ----------------------------------------------------


def _hc(word: str) -> Answer:
    from ..language import KEYWORDS

    answer = _empty()
    spec = usr.load("hc_kamus")
    entry = next((e for e in spec["entries"]
                  if word in (e["hc"], e["arabic"], e["indonesia"], e["concept"])), None)
    if entry is None:
        other = next((x for x in spec["not_hc"]
                      if word in (x["name"], x["arabic"], x["indonesia"])), None)
        if other is None:
            answer["unknown"].append(f"{word} is in neither the dictionary nor its not-HC list")
            return answer
        answer["HC"].append({"what": "not HC", **other, "source": "NUI/spec/hc_kamus.json"})
        answer["NUI"].append({"what": "usr", "ACTION": "READ", "OBJECT": "FILE",
                              "source": "NUI/spec/usr.json"})
        return answer
    hc = entry["hc"]
    answer["HC"].append({"what": "dictionary", **entry, "source": "NUI/spec/hc_kamus.json"})
    where = ("src/hijaiyyah/language/tokens.py" if hc in KEYWORDS
             else "src/hijaiyyah/language/evaluator.py")
    answer["HC"] += [{"what": "defined", **line} for line in _lines(where, rf'"{hc}"', limit=1)]
    row = next(r for r in usr.lowering() if r["hc"] == hc)
    answer["HC"].append({"what": "lowering", "probe": row["probe"],
                         "reaches_hisa": row["reaches_hisa"], "opcodes": row["opcodes"],
                         "error": row["error"], "source": "src/hijaiyyah/compiler/codegen.py"})
    surface = next(s for s in usr.surfaces() if s["hc"] == hc)
    answer["HC"].append({"what": "read by HC's lexer today", "arabic": surface["arabic"],
                         "indonesia": surface["indonesia"],
                         "source": "src/hijaiyyah/language/lexer.py"})
    for op in row["opcodes"]:
        definition = _definition(op)
        if definition:
            answer["HISA"].append(definition)
    if entry["concept"] in {a["name"] for a in usr.load("usr")["actions"]}:
        answer["NUI"].append({"what": "usr", "ACTION": entry["concept"],
                              "source": "NUI/spec/usr.json"})
    answer["tests"] = _tests("|".join(re.escape(w) for w in (entry["arabic"], entry["indonesia"])))
    return answer


# -- the rest of the owner's seven questions ------------------------------------------

TERMS = "teknologi/ISTILAH.md"
GRAPH = "src/hijaiyyah/nui/repository_graph.py"
#: Board records the repository keeps, by family; baselines and reports are
#: derived from a record, not records themselves. A record is taken for a
#: family only when its own `target` says so where it carries one: since P1
#: (24 September 2026) the burn-in folder holds three kinds of file -- a run's
#: summary, a raw capture's manifest, and what the offline parser made of it --
#: and a capture manifest answering "what did the board last measure" would
#: report a run's fields as empty.
FAMILIES = {"burn-in": "cosmictera-build/burn-in/*.json",
            "burn-in-capture": "cosmictera-build/burn-in/*-capture.json",
            "attack-lab": "cosmictera-build/attack-lab/*.json",
            "parity-board": "cosmictera-build/parity-board/*.json"}
TARGETS = {"burn-in": "burn-in", "burn-in-capture": "burn-in-capture"}
HEADLINES = {"burn-in": ("started", "ended", "heartbeats", "errors", "sd_read_failures"),
             "burn-in-capture": ("started", "ended", "bytes", "raw_sha256",
                                 "bitstream_sha256"),
             "attack-lab": ("attack_id", "target", "inputs", "rejected", "findings"),
             "parity-board": ("experiment", "commit", "date")}
MONTHS = {m: i for i, m in enumerate(
    ("Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
     "September", "Oktober", "November", "Desember"), 1)}


def _term(word: str) -> Answer:
    """A row of the system's glossary, read as its table's own columns."""
    answer = _empty()
    header: list[str] = []
    for number, line in enumerate((ROOT / TERMS).read_text(encoding="utf-8").splitlines(), 1):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == "Istilah":
            header = cells
            continue
        name = cells[0].replace("\\", "").strip("*") if cells else ""
        if header and name.lower() == word.lower():
            answer["NUI"].append({"what": "term", **dict(zip(header, cells, strict=False)),
                                  "source": f"{TERMS}:{number}"})
    if not answer["NUI"]:
        answer["unknown"].append(f"{word} is not a term in {TERMS}")
    return answer


def _file(path: str) -> Answer:
    """What the repository graph knows of one file, and what wrote it where the
    file itself says."""
    from .repository_graph import build as graph
    answer = _empty()
    if not tracked(path):
        answer["unknown"].append(f"{path} is not a file git tracks")
        return answer
    generated = None
    if path.endswith(".json"):
        data = json.loads((ROOT / path).read_text(encoding="utf-8"))
        generated = data.get("generated_by") if isinstance(data, dict) else None
    if generated:
        answer["NUI"].append({"what": "generated by", "by": generated, "source": path})
    elif path.endswith(".json"):
        # A generated file here says so in its own `generated_by`; one that
        # does not is not guessed at from who happens to mention it.
        answer["unknown"].append(f"{path} does not say what writes it")
    g = graph()
    if path not in g.nodes:
        answer["unknown"].append(f"{path} is not a node of the repository graph, which "
                                 "indexes Python, tests, Verilog, HASM, facts and documents")
        return answer
    answer["NUI"].append({"what": "node", "path": path, "kind": g.nodes[path].kind,
                          "source": GRAPH})
    for e in g.out(path):
        answer["NUI"].append({"what": f"{e.kind} ->", "other": e.target,
                              "evidence": e.evidence, "source": GRAPH})
    for e in g.into(path):
        answer["NUI"].append({"what": f"<- {e.kind}", "other": e.source,
                              "evidence": e.evidence, "source": GRAPH})
    answer["tests"] = [{"file": t, "source": t} for t in g.verified_by(path)]
    return answer


def _rtl(module: str) -> Answer:
    """What a Verilog module instantiates, and what instantiates it."""
    from .program_graph import verilog_instances
    from .program_index import programs
    answer = _empty()
    keys = [k for k in programs().verilog if k.split("::")[1] == module]
    if not keys:
        answer["unknown"].append(f"{module} is not a Verilog module in the repository")
        return answer
    for key in keys:
        file = key.split("::")[0]
        links, vendor, missing = verilog_instances(key)
        for link in links:
            answer["RTL"].append({"what": "instantiates", "instance": link.via,
                                  "module": link.target.split("::")[1],
                                  "defined_in": link.target.split("::")[0], "source": file})
        answer["RTL"] += [{"what": "vendor primitive", "module": m, "source": file}
                          for m in vendor]
        answer["unknown"] += [f"{file} instantiates {m}, defined nowhere here" for m in missing]
    # A module with two homes is linked once per home (program_graph), so the
    # same instantiation would otherwise be listed twice.
    by: set[tuple[str, str]] = set()
    for key in programs().verilog:
        for link in verilog_instances(key)[0]:
            if link.target.split("::")[1] == module and (key, link.via) not in by:
                by.add((key, link.via))
                answer["RTL"].append({"what": "instantiated by", "module": key.split("::")[1],
                                      "instance": link.via, "source": key.split("::")[0]})
    return answer


def _papan_latest() -> dict[str, Any] | None:
    """The PAPAN.md heading with the latest date written in it."""
    best: tuple[tuple[int, int, int], dict[str, Any]] | None = None
    for line in _lines("cosmictera-build/PAPAN.md", r"^#+ .*\d{1,2} [A-Z][a-z]+ 20\d\d",
                       limit=10_000):
        m = re.search(r"(\d{1,2}) ([A-Z][a-z]+) (20\d\d)", line["text"])
        if m and m.group(2) in MONTHS:
            day = (int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
            if best is None or day > best[0]:
                best = (day, {"what": "latest dated section", "heading": line["text"],
                              "date": f"{day[0]}-{day[1]:02d}-{day[2]:02d}",
                              "source": line["source"]})
    return best[1] if best else None


def _board(subject: str) -> Answer:
    """The newest record the repository keeps from the board, per family."""
    answer = _empty()
    if subject != "latest":
        answer["unknown"].append("the board query takes `latest`")
        return answer
    for family, pattern in FAMILIES.items():
        files = [f for f in tracked(pattern)
                 if re.search(r"\d{8}T\d{6}Z", f) and not f.endswith(("-baseline.json",
                                                                       "-parsed.json",
                                                                       ".report.json"))]
        if family in TARGETS:
            files = [f for f in files
                     if _json(ROOT / f).get("target") == TARGETS[family]]
        if not files:
            answer["unknown"].append(f"no {family} record is tracked yet")
            continue
        newest = max(files, key=lambda f: re.search(r"\d{8}T\d{6}Z", f).group(0))  # type: ignore[union-attr]
        data = json.loads((ROOT / newest).read_text(encoding="utf-8"))
        stamp = re.search(r"\d{8}T\d{6}Z", newest).group(0)  # type: ignore[union-attr]
        answer["PAPAN"].append({"what": "latest record", "family": family, "stamp": stamp,
                                **{k: data.get(k) for k in HEADLINES[family]},
                                "source": newest})
    section = _papan_latest()
    if section:
        answer["PAPAN"].append(section)
    return answer


def _host(subject: str) -> Answer:
    """What the host shows, read only from verified observations (K-6, K-11).

    The host is the main instance the spec names, cosmictera-layer5, and only
    its own observations answer: the canonical identity of an observation is
    (vm_name, run_id), so the test instance's evidence never stands for the
    main one (K-16). The subject is a collector or an area of
    NUI/spec/layer5_collectors.json,
    or `services`, the service area. Each HOST item is the newest observation
    of one collector that passed layer5.latest()'s checks, with its run,
    collector, evidence file, time and SHA-256; a collector that is not PASS
    shows its stderr as the provenance of why. What no observation supports
    stays unknown, with the reason (K-14). For `services` the owner's contract
    names the collectors whose evidence would answer, and none yet does."""
    from . import layer5
    if subject.startswith("delta "):
        return _host_delta(subject[len("delta "):].strip())
    answer = _empty()
    vm = layer5.host()["instance"]
    collectors = layer5.load()["collectors"]
    area = {"services": "service"}.get(subject, subject)
    chosen = [c["name"] for c in collectors if subject == c["name"] or area == c["area"]]
    if not chosen:
        answer["unknown"].append(f"`{subject}` is not a collector or an area of "
                                 "NUI/spec/layer5_collectors.json")
    for row in layer5.plan():
        if not chosen or row["name"] in chosen:
            answer["NUI"].append({"what": "planned collector", "name": row["name"],
                                  "argv": row.get("argv"), "status": row["status"],
                                  "source": "NUI/spec/layer5_collectors.json"})
    passed = set()
    for name in chosen:
        seen = layer5.latest(name, vm)
        if seen is None:
            answer["unknown"].append(f"no supporting HOST observation: {name} has no run for "
                                     f"{vm} in the observation store")
            continue
        if "rejected" in seen:
            answer["unknown"].append(f"no supporting HOST observation: {name} in "
                                     f"{seen['run_id']} was rejected -- {seen['rejected']}")
            continue
        if "failure" in seen:
            answer["unknown"].append(f"no supporting HOST observation: {name} failed in "
                                     f"{seen['run_id']} -- {seen['failure']}")
            continue
        stream = "stdout" if seen["status"] == "PASS" else "stderr"
        fresh = layer5.freshness(seen["observed_at"])
        answer["HOST"].append({
            "what": "observation", "provenance": "observation", "collector": name,
            "status": seen["status"], "run_id": seen["run_id"], "vm_name": seen["vm_name"],
            "observed_at": seen["observed_at"], "command_identity": seen["command_identity"],
            "exit_code": seen["exit_code"], "evidence": seen[stream]["source"],
            "evidence_sha256": seen[stream]["sha256"], "text": seen[f"{stream}_text"],
            **fresh, "source": seen[stream]["source"]})
        if seen["status"] == "PASS":
            passed.add(name)
        else:
            said = seen["stderr_text"].strip().splitlines() or [f"exit {seen['exit_code']}"]
            answer["unknown"].append(f"{name} is {seen['status']} in {seen['run_id']}: "
                                     f"{said[-1]}")
    if subject == "services":
        row = next(q for q in _json(CONTRACT)["questions"] if q["query"] == "host services")
        if not passed & set(row["supported_by"]):
            answer["unknown"].insert(0, row["unknown_reason"])
    return answer


def _host_delta(collector: str) -> Answer:
    """What changed in one collector's output between the main instance's two
    newest runs of it, each item with the provenance of both runs (layer5.delta).
    What the spec's rule sets apart -- kworker, for processes -- comes as one
    item of its own and is never reported as the collector's change. An
    observation of change, never an action on it."""
    from . import layer5
    answer = _empty()
    vm = layer5.host()["instance"]
    if collector not in {c["name"] for c in layer5.load()["collectors"]}:
        answer["unknown"].append(f"`{collector}` is not a collector of "
                                 "NUI/spec/layer5_collectors.json")
        return answer
    d = layer5.delta(collector, vm)
    if "unknown" in d:
        answer["unknown"].append(d["unknown"])
        return answer
    common = {"provenance": "observation", "collector": collector, "vm_name": vm,
              "from_run": d["from"]["run_id"], "to_run": d["to"]["run_id"],
              "between": {"from": d["from"], "to": d["to"]}}
    for key in d["appeared"]:
        answer["HOST"].append({"what": "appeared", "item": key, **common,
                               "source": d["to"]["evidence"]})
    for key in d["disappeared"]:
        answer["HOST"].append({"what": "disappeared", "item": key, **common,
                               "source": d["from"]["evidence"]})
    for change in d["changed"]:
        answer["HOST"].append({"what": "changed", **change, **common,
                               "source": d["to"]["evidence"]})
    if d["from"]["status"] != d["to"]["status"]:
        answer["HOST"].append({"what": "status changed", "from": d["from"]["status"],
                               "to": d["to"]["status"], **common,
                               "source": d["to"]["stderr"]})
    if not answer["HOST"]:
        answer["HOST"].append({"what": "unchanged", **common, "source": d["to"]["evidence"]})
    for name in [k for k in d if k not in ("collector", "vm_name", "from", "to", "appeared",
                                            "disappeared", "changed")]:
        apart = d[name]
        if any(apart.values()):
            answer["HOST"].append({"what": name, **apart, **common,
                                   "source": d["to"]["evidence"]})
    return answer


def _hardware_item(c: dict[str, Any], registry: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """One claim as an answer item, and the domain that reads its evidence --
    a board record or page under PAPAN, RTL under RTL, a fact under NUI; a
    claim with no evidence points at the provenance model."""
    from . import telemetry_sources
    where = c["evidence"]
    source = ("NUI/hardware_provenance.json" if where is None else
              f"{where}:{c['evidence_lines'][0]}" if c["evidence_lines"] else where)
    domain = ("PAPAN" if source.startswith("cosmictera-build/") else
              "RTL" if source.startswith("rtl/") else "NUI")
    item = {"what": "hardware claim", "id": c["id"], "status": c["status"],
            "source_kind": c["source_kind"], "provenance": c, "source": source}
    if c["id"].startswith("6.2:"):
        item["boundary"] = telemetry_sources.access(c["id"][4:], registry)
    return domain, item


def _incomplete(c: dict[str, Any]) -> list[str]:
    return [f"{c['id']}: check {f['check']} ({f['label']}) fails -- {f['why']}"
            for f in c["failed_checks"]]


def _hardware(subject: str) -> Answer:
    """Hardware claims with their provenance (layer 6.3). Each item is filed
    in the domain that reads its evidence. What is UNKNOWN, and every check a
    claim fails, is said in `unknown`; nothing is taken from the newest run to
    stand for the hardware now. A subject that begins with one of layer 6.4's
    groups -- identity, capability, observed, current, provenance -- is asked
    of the state model instead."""
    from . import hardware_provenance, hardware_state, telemetry_sources
    group, _, rest = subject.partition(" ")
    if group == "correlation":
        return _hardware_correlation(rest.strip())
    if group in hardware_state.load()["groups"]:
        return _hardware_state(group, rest.strip())
    answer = _empty()
    claims = hardware_provenance.claims_for(subject)
    if claims is None:
        answer["unknown"].append(f"`{subject}` is not a hardware subject or claim of "
                                 "NUI/hardware_provenance.json")
        return answer
    registry = _json(telemetry_sources.MODEL)
    for c in claims:
        domain, item = _hardware_item(c, registry)
        answer[domain].append(item)
        if c["status"] == "UNKNOWN":
            answer["unknown"].append(f"{c['id']}: {c['reason']}")
        answer["unknown"] += _incomplete(c)
    return answer


def _hardware_state(group: str, subject: str) -> Answer:
    """What a hardware answer means (layer 6.4): the claims of the kind of
    state asked for -- IDENTITY, CAPABILITY, OBSERVED, CURRENT, or all of them
    for provenance -- and one headline state by the owner's precedence. A
    CURRENT question is answered only by a registered live source; with none,
    it is unknown, never the newest historical run. A claim whose provenance
    6.3 left incomplete is named as such in `unknown`, not polished."""
    from . import hardware_state, telemetry_sources
    answer = _empty()
    ctx = hardware_state.context()
    model = _json(hardware_state.MODEL)
    a = hardware_state.answer(group, subject, model, ctx)
    answer["NUI"].append({"what": "hardware answer",
                          **{k: a[k] for k in ("group", "category", "state", "source_kind",
                                               "evidence_kinds", "basis",
                                               "incomplete_provenance", "reason")},
                          "source": "NUI/hardware_state.json"})
    objects = {o["id"]: o for o in [*ctx["provenance"]["claims"], *model["observed_opcodes"]]}
    categories = {e["id"]: e["category"] for e in model["claims"]}
    registry = _json(telemetry_sources.MODEL)
    for cid in a["claims"]:
        domain, item = _hardware_item(objects[cid], registry)
        answer[domain].append({**item, "category": categories[cid]})
        if objects[cid]["status"] == "UNKNOWN":
            answer["unknown"].append(f"{cid}: {objects[cid]['reason']}")
        answer["unknown"] += _incomplete(objects[cid])
    if a["state"] == "UNKNOWN":
        answer["unknown"].insert(0, a["reason"])
    return answer


def _hardware_correlation(text: str) -> Answer:
    """How hardware, board runs, programs and opcodes are linked (layer 6.5):
    `correlation <hardware|program|opcode|run> <subject>`. Each item is one
    correlation -- DIRECT, DERIVED or UNKNOWN -- filed where its evidence
    lives; an UNKNOWN one says why in `unknown`, and nothing is linked by a
    name. For an opcode, what counts as opcode-level evidence is P3's column
    only; programs of other experiments are named apart."""
    from . import hardware_correlation
    answer = _empty()
    kind, _, subject = text.partition(" ")
    model = _json(hardware_correlation.MODEL)
    try:
        a = hardware_correlation.answer(kind, subject.strip(), model,
                                        hardware_correlation.context())
    except LookupError as why:
        answer["unknown"].append(str(why))
        return answer
    edges = {e["id"]: e for e in model["correlations"]}
    head = {"what": "hardware correlation", "kind": a["kind"], "subject": a["subject"],
            "correlations": len(a["correlations"]), "source": "NUI/hardware_correlation.json"}
    if "opcode_evidence" in a:
        head["opcode_evidence"] = a["opcode_evidence"]
    answer["NUI"].append(head)
    for cid in a["correlations"]:
        e = edges[cid]
        domain = "PAPAN" if e["evidence"].startswith("cosmictera-build/") else "NUI"
        answer[domain].append({"what": "correlation", **{k: e[k] for k in (
            "id", "relation", "class", "run_id", "from", "to", "payload_sha256", "value",
            "evidence_key", "evidence_sha256")}, "source": e["evidence"]})
    answer["unknown"] += a["unknown"]
    return answer


def query(text: str) -> Answer:
    kind, _, subject = text.strip().partition(" ")
    if kind not in KINDS or not subject:
        raise ValueError(f"a query is '<kind> <subject>', kind one of {', '.join(KINDS)}")
    subject = subject.strip()
    handler = {"opcode": lambda: _opcode(subject.upper()),
               "program": lambda: _program(subject),
               "off": lambda: _off_entry(subject),
               "letter": lambda: _letter(subject),
               "hc": lambda: _hc(subject),
               "term": lambda: _term(subject),
               "file": lambda: _file(subject),
               "rtl": lambda: _rtl(subject),
               "board": lambda: _board(subject),
               "host": lambda: _host(subject),
               "hardware": lambda: _hardware(subject)}[kind]
    return {"query": text.strip(), "kind": kind, "subject": subject, **handler()}


def sources(answer: Answer) -> list[str]:
    """Every source an answer cites, wherever it sits."""
    out: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                if k in ("source", "model") and isinstance(v, str) and v:
                    # the parity model joins two places with ", " where a
                    # divergence has two (a stop's source is the controller
                    # and the writeback stage)
                    out.extend(part for part in v.split(", ") if part)
                else:
                    walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    walk(answer)
    return out


def main(argv: list[str] | None = None) -> int:
    import sys
    args = sys.argv[1:] if argv is None else argv
    print(json.dumps(query(" ".join(args) or "opcode PRINT"), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
