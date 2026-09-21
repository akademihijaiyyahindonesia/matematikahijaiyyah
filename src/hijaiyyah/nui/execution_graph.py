"""Layer 3: the execution model -- every program run, every edge with its step.

execution_trace records one run. This module runs all 62 HASM programs, plus
the loader carrying a program on its wire, and joins what they did into one
graph whose edges are the owner's nine kinds:

    EXECUTES  program -> opcode          an instruction ran
    READS     program -> mmio | memory   a read that changed state (RX_DATA
                                          pops its byte) or a memory read
    OBSERVES  program -> mmio            a register read that changed nothing
    WRITES    program -> mmio | memory
    MODIFIES  program -> register        a value moved
    CALLS / RETURNS / RESUMES            CALL, RET, ERET -> where they landed:
                                          `label:name@addr` when the assembler
                                          bound a label there, `pc:addr` if not
    TRAPS     program -> trap cause      with the epc it left and the vector
                                          it reached

READS and OBSERVES are told apart by MEASUREMENT: the recorder notes whether
the UART queue shrank during the read. Nothing is classified by its name.

-- re-testable from the same repository ----------------------------------
The model is written to NUI/execution_model.json, and `verify()` rebuilds it
from scratch and compares. Each run's full ENTRY/STEP/CHANGE/EXIT trace is
too long to keep -- tens of thousands of steps for a program that polls -- so
the model keeps its SHA-256, and `--trace <program>` prints the text that
digest covers. An edge the rebuild does not produce -- a false
execution edge, a register that never moved, a register-mapped address that
was never touched -- is reported by name. Those are the three sabotages the
owner requires to turn red, and they turn red here.

-- the UNKNOWN inventory ---------------------------------------------------
What execution in this interpreter cannot establish is listed, never filled
in: branches seen going one way only, programs that did not halt within the
budget, programs that ran off their code, stops by the interpreter's own
periodic HCHECK, the SD card the interpreter does not have, a timer that
counts instructions rather than clocks, integer state that appeared on the
machine without being declared at construction, and everything RTL -- which
runs in the benches, not here.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .execution_trace import HARDWARE_GPRS, Trace, trace_loader, trace_program
from .program_index import programs
from .repository_index import ROOT

MODEL = ROOT / "NUI" / "execution_model.json"
PAGE = ROOT / "NUI" / "EXECUTION.md"
#: The model as JSON gives it back: plain dicts and lists, read by key.
Model = dict[str, Any]
KINDS = ("EXECUTES", "READS", "OBSERVES", "WRITES", "MODIFIES",
         "CALLS", "RETURNS", "RESUMES", "TRAPS")
MAX_STEPS = 20_000
#: The loader needs something on its wire to show its handover. Three words,
#: the smallest program that proves the payload ran: it prints what it set.
LOADER_PAYLOAD = "        MOVI  R1, 7\n        PRINT R1\n        HALT\n"
LOADER_SCENARIO = "rtl/programs/loader.hasm#with-payload"


def _digest() -> tuple[Any, Callable[[str], None]]:
    digest = hashlib.sha256()
    return digest, lambda line: digest.update(line.encode("utf-8") + b"\n")


def _traces() -> tuple[dict[str, Trace], dict[str, str]]:
    """Every run, and the SHA-256 of its rendered ENTRY/STEP/CHANGE/EXIT
    trace -- the whole trace, not the part a summary keeps."""
    out: dict[str, Trace] = {}
    sums: dict[str, str] = {}
    for path in sorted(programs().hasm):
        digest, sink = _digest()
        out[path] = trace_program(path, max_steps=MAX_STEPS, keep=0, sink=sink)
        sums[path] = digest.hexdigest()
    digest, sink = _digest()
    out[LOADER_SCENARIO] = trace_loader(LOADER_PAYLOAD, max_steps=MAX_STEPS, keep=0,
                                        sink=sink)
    sums[LOADER_SCENARIO] = digest.hexdigest()
    return out, sums


def print_trace(program: str) -> Trace:
    """The full trace of one run, to stdout: what the model's digest covers."""
    if program == LOADER_SCENARIO:
        return trace_loader(LOADER_PAYLOAD, max_steps=MAX_STEPS, keep=0, sink=print)
    return trace_program(program, max_steps=MAX_STEPS, keep=0, sink=print)


def _summary(t: Trace, trace_sha256: str) -> Model:
    return {
        "entry": t.entry,
        "exit": t.exit,
        "exit_detail": t.exit_detail,
        "steps": t.total_steps,
        "trace_sha256": trace_sha256,
        "branches_both_ways": sum(1 for o in t.branches.values() if len(o) == 2),
        "branches_one_way": sum(1 for o in t.branches.values() if len(o) == 1),
        "lines_executed": len(t.lines_executed),
        "gprs_modified": sorted(t.gprs_modified),
        "hregs_modified": sorted(t.hregs_modified),
        "traps": [{"step": s, "cause": c, "epc": e, "vector": v} for s, c, e, v in t.traps],
        "printed": len(t.printed),
    }


def _unknowns(traces: dict[str, Trace]) -> dict[str, list[str]]:
    """What running here could not establish. Listed, never filled in."""
    included = {f"rtl/programs/{name}" for unit in programs().hasm.values()
                for name in unit.includes}
    out: dict[str, list[str]] = {
        "branch_seen_one_way": [], "did_not_halt_within_budget": [],
        "ran_off_its_code": [], "stopped_by_interpreter_hcheck": [],
        "sd_card_absent_in_interpreter": [], "timer_counts_instructions": [],
        "registers_the_hardware_lacks": [],
        "trap_to_an_uninstalled_vector": [],
        "state_the_machine_never_declared": [],
    }
    for name, t in sorted(traces.items()):
        one_way = sum(1 for outcomes in t.branches.values() if len(outcomes) == 1)
        if one_way:
            out["branch_seen_one_way"].append(f"{name}: {one_way} branch(es)")
        if t.exit == "step_cap":
            waiting = ", ".join(sorted(t.final_window_mmio)) or "no register read"
            out["did_not_halt_within_budget"].append(
                f"{name}: {t.total_steps} steps; last 200 read {waiting}")
        if t.exit == "end_of_code":
            role = "included by another program" if name in included else "standalone"
            out["ran_off_its_code"].append(f"{name}: {role}")
        if t.exit == "hcheck":
            out["stopped_by_interpreter_hcheck"].append(f"{name}: {t.exit_detail}")
        touched = {m for (_, m, _) in t.mmio}
        if any(m.startswith("SD_") for m in touched):
            out["sd_card_absent_in_interpreter"].append(name)
        if touched & {"COUNTER", "COMPARE", "TIMER_STATUS"}:
            out["timer_counts_instructions"].append(name)
        # A trap to vector 0 means no handler was installed: the program
        # expects another to set it up. Run alone, the trap lands on its own
        # first word and it starts over -- which is why the three rtl/tb
        # probes, written to be injected into the shell, never halt here.
        unset = sorted({cause for _, cause, _, vector in t.traps if vector == 0})
        if unset:
            out["trap_to_an_uninstalled_vector"].append(f"{name}: cause {unset}")
        for attribute, (step, where) in sorted(t.undeclared.items()):
            out["state_the_machine_never_declared"].append(
                f"{name}: {attribute} first set at step {step}, {where}")
        high = sorted(r for r in t.gprs_modified if r >= HARDWARE_GPRS)
        if high:
            out["registers_the_hardware_lacks"].append(f"{name}: R{high}")
    out["scope"] = [
        "RTL execution is not traced here -- Verilog runs in rtl/tb/, and "
        "joining the two is layer 4",
        "Python execution is not traced -- function-to-function calls stay "
        "unresolved, as layers 1 and 2 left them",
        "each program runs alone at address 0 with nothing on its UART, except "
        f"{LOADER_SCENARIO}, which carries a three-word payload",
    ]
    return out


def build() -> Model:
    traces, sums = _traces()
    edges = []
    for name, t in sorted(traces.items()):
        for (kind, target), (step, pc, where, times) in sorted(t.edges.items()):
            edges.append({"source": name, "kind": kind, "target": target,
                          "step": step, "pc": pc, "where": where, "times": times})
    return {
        "generated_by": "src/hijaiyyah/nui/execution_graph.py",
        "interpreter": "src/hijaiyyah/hisa/machine.py",
        "max_steps": MAX_STEPS,
        "programs": {name: _summary(t, sums[name]) for name, t in sorted(traces.items())},
        "edges": edges,
        "unknown": _unknowns(traces),
    }


def write(model: Model | None = None) -> Path:
    MODEL.write_text(json.dumps(model or build(), indent=1, sort_keys=True) + "\n")
    return MODEL


def verify(claimed: Model,
           fresh: Model | None = None) -> list[str]:
    """Rebuild from the repository and name every claim the rebuild denies.
    `fresh` lets a caller that already rebuilt pass it in; the default is to
    rebuild, because a verifier that trusted a cached answer would verify
    nothing."""
    fresh = fresh if fresh is not None else build()
    key = lambda e: (e["source"], e["kind"], e["target"])  # noqa: E731
    real = {key(e): e for e in fresh["edges"]}
    problems = []
    for edge in claimed["edges"]:
        found = real.get(key(edge))
        if found is None:
            problems.append(f"not reproduced: {edge['source']} {edge['kind']} {edge['target']}")
        elif (found["step"], found["where"]) != (edge["step"], edge["where"]):
            problems.append(f"evidence moved: {edge['source']} {edge['kind']} "
                            f"{edge['target']} claims step {edge['step']} "
                            f"{edge['where']}, runs at step {found['step']} {found['where']}")
        elif found["times"] != edge["times"]:
            # Found by the HCHECK fix: two EXECUTES counts moved by one and
            # the first version of this check, comparing step and line only,
            # passed the stale model.
            problems.append(f"count differs: {edge['source']} {edge['kind']} "
                            f"{edge['target']} claims {edge['times']} times, "
                            f"runs {found['times']}")
    claimed_keys = {key(e) for e in claimed["edges"]}
    for k in real:
        if k not in claimed_keys:
            problems.append(f"missing from the model: {k[0]} {k[1]} {k[2]}")
    ours, theirs = claimed["programs"], fresh["programs"]
    for name in sorted(set(ours) | set(theirs)):
        if name not in theirs:
            problems.append(f"not reproduced: program {name}")
            continue
        if name not in ours:
            problems.append(f"missing from the model: program {name}")
            continue
        a, b = ours[name], theirs[name]
        for field in sorted(set(a) | set(b)):
            if a.get(field) != b.get(field):
                problems.append(f"summary differs: {name} {field} claims "
                                f"{a.get(field)!r}, runs {b.get(field)!r}")
    for category in sorted(set(claimed["unknown"]) | set(fresh["unknown"])):
        if claimed["unknown"].get(category) != fresh["unknown"].get(category):
            problems.append(f"unknown inventory differs: {category}")
    return problems


def control_transfer(model: Model, program: str) -> list[Model]:
    """How a program hands control on -- the writes that set it up and the
    transfers that take it -- read from the model, not from the code."""
    wanted = {"CALLS", "RETURNS", "RESUMES", "TRAPS"}
    setup = ("mmio:TRAP_EPC", "mmio:TRAP_MODE", "mmio:TRAP_VECTOR")
    rows = [e for e in model["edges"]
            if e["source"] == program and (e["kind"] in wanted
                                           or (e["kind"] == "WRITES"
                                               and str(e["target"]).startswith(setup)))]
    return sorted(rows, key=lambda e: int(e["step"]))


def page(model: Model) -> str:
    """NUI/EXECUTION.md, drawn from the model and nothing else. The headings
    are the only words not taken from it; a test holds the committed page to
    this function, so the page cannot drift from the model it describes."""
    programs_: dict[str, Model] = model["programs"]
    edges: list[Model] = model["edges"]
    unknown: dict[str, list[str]] = model["unknown"]
    exits: dict[str, int] = {}
    for summary in programs_.values():
        exits[str(summary["exit"])] = exits.get(str(summary["exit"]), 0) + 1
    kinds = {k: sum(1 for e in edges if e["kind"] == k) for k in KINDS}
    nodes: dict[str, set[str]] = {}
    for e in edges:
        target = str(e["target"])
        nodes.setdefault(target.split(":")[0], set()).add(target)
    both = sum(int(s["branches_both_ways"]) for s in programs_.values())
    one = sum(int(s["branches_one_way"]) for s in programs_.values())
    out = [
        "# Model eksekusi — Lapis 3 NUI", "",
        f"Dihasilkan `{model['generated_by']}` dari eksekusi di `{model['interpreter']}`, "
        "dan ditarik dari `NUI/execution_model.json` oleh `page()`. Yang ditulis tangan "
        "hanya judulnya.", "",
        "## Lari", "", "| | |", "|---|---:|",
        f"| lari | {len(programs_)} |",
        f"| batas langkah per lari | {model['max_steps']} |",
    ]
    out += [f"| keluar `{k}` | {v} |" for k, v in sorted(exits.items())]
    out += [f"| cabang terlihat dua arah | {both} |", f"| cabang terlihat satu arah | {one} |"]
    out += ["", "## Edge", "", "| jenis | jumlah |", "|---|---:|"]
    out += [f"| `{k}` | {v} |" for k, v in kinds.items()]
    out += [f"| **total** | **{len(edges)}** |", "",
            "## Node tujuan edge", "", "| jenis | jumlah |", "|---|---:|"]
    out += [f"| `{k}:` | {len(v)} |" for k, v in sorted(nodes.items())]
    out += ["", "## Bagaimana `loader.hasm` memindahkan kendali", "",
            "| langkah | edge | target | sumber |", "|---:|---|---|---|"]
    out += [f"| {e['step']} | `{e['kind']}` | `{e['target']}` | `{e['where']}` |"
            for e in control_transfer(model, LOADER_SCENARIO)]
    out += ["", "## Inventaris UNKNOWN", ""]
    # Sorted: the JSON is written with sorted keys, so the model read back
    # from disk and the one just built must give the same page.
    for category, entries in sorted(unknown.items()):
        if category == "scope":
            continue
        out += [f"### `{category}` — {len(entries)}", ""]
        out += [f"- `{entry}`" for entry in entries] or ["- (kosong)"]
        out.append("")
    out += ["### `scope`", ""] + [f"- {entry}" for entry in unknown["scope"]]
    out += ["", "## Mengulang", "", "```bash",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.execution_graph --verify",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.execution_graph "
            f"--trace {LOADER_SCENARIO}",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.execution_graph --write",
            "```"]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    import sys
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--write":
        model = build()
        path = write(model)
        PAGE.write_text(page(model), encoding="utf-8")
        print(f"model: {path.relative_to(ROOT)}, page: {PAGE.relative_to(ROOT)}")
        return 0
    if len(args) == 2 and args[0] == "--trace":
        print_trace(args[1])
        return 0
    if args and args[0] == "--verify":
        problems = verify(json.loads(MODEL.read_text()))
        print("\n".join(problems) if problems else "model reproduced exactly")
        return 1 if problems else 0
    model = build()
    exits: dict[str, int] = {}
    for summary in model["programs"].values():
        exits[str(summary["exit"])] = exits.get(str(summary["exit"]), 0) + 1
    print(f"{len(model['programs'])} runs, {len(model['edges'])} edges, exits {exits}")
    target = args[0] if args else LOADER_SCENARIO
    for e in control_transfer(model, target):
        print(f"  step {e['step']:>5}  {e['kind']:<8} {e['target']:<26} {e['where']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
