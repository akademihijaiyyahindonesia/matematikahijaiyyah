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
no HOST fact goes in before a collector has measured it, so HOST reads
nowhere yet: the test that files every item by its source refuses anything
placed there.

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

KINDS = ("opcode", "program", "off", "letter", "hc", "term", "file", "rtl", "board", "host")
EXECUTION = ROOT / "NUI" / "execution_model.json"
PARITY = ROOT / "NUI" / "parity_model.json"
OPCODES = "src/hijaiyyah/hisa/opcodes.py"
Answer = dict[str, Any]

#: The owner's seven domains, and the places each one reads -- regular
#: expressions over an item's source. HASM programs are HISA; everything else
#: under rtl/ is RTL. The parity model is read by three: its interpreter column
#: is HISA, its RTL column RTL, its board column PAPAN. HOST reads nothing:
#: no collector has measured a host, and where its records will be kept is
#: not decided (K-6).
DOMAINS: dict[str, tuple[str, ...]] = {
    "HC": (r"src/hijaiyyah/language/", r"src/hijaiyyah/compiler/", r"NUI/spec/hc_kamus\.json"),
    "HISA": (r"src/hijaiyyah/hisa/", r"docs/HISA_SPEC\.md", r"NUI/execution_model\.json",
             r"NUI/parity_model\.json", r"rtl/programs/", r"<"),
    "RTL": (r"rtl/(?!programs/)", r"NUI/parity_model\.json"),
    "OFF": (r"cosmictera-build/OFF\.md",),
    "PAPAN": (r"cosmictera-build/", r"NUI/parity_model\.json"),
    "NUI": (r"facts/", r"NUI/", r"src/hijaiyyah/nui/", r"teknologi/ISTILAH\.md"),
    "HOST": (),
}


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
    answer["PAPAN"] = [{"what": "board record", **line}
                       for line in _lines("cosmictera-build/PAPAN.md", rf"`{stem}(?:\.hasm)?`")]
    answer["PAPAN"] += [{"what": "board run", "board": r["board"], "status": r["status"],
                         "date": r["date"], "source": r["record"]}
                        for r in parity["board"] if r["program"] == path]
    answer["NUI"] = _facts([base, path])
    answer["OFF"] = _off([base])
    answer["tests"] = _tests(rf"\b{re.escape(base)}\b")
    if not answer["PAPAN"]:
        answer["unknown"].append("cosmictera-build/PAPAN.md records no board run of it")
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
    """What the Ubuntu host runs: nothing is known, because there is no host.
    HOST stays empty; the collectors that would answer are NUI's own plan."""
    from . import layer5
    answer = _empty()
    answer["unknown"].append("no Ubuntu host exists yet: layer 5 has not started, so nothing "
                             "has been observed (NUI/LAYERS.md)")
    area = {"services": "service"}.get(subject)
    for row in layer5.plan():
        if area is None or row["area"] == area:
            answer["NUI"].append({"what": "planned collector", "name": row["name"],
                                  "argv": row.get("argv"), "status": row["status"],
                                  "source": "NUI/spec/layer5_collectors.json"})
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
               "host": lambda: _host(subject)}[kind]
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
