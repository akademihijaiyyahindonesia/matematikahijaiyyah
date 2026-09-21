"""Layer 4: one program on every engine that can run it -- and where two part,
the step, the register, the address and the opcode.

Layer 3 recorded what the interpreter does. This layer runs the same words on
the RTL and holds the two records against each other change by change, then
reads what the board printed against both. Nothing here is a new engine: the
interpreter is HISAMachine through layer 3's recorder, the RTL is hcpu_top.v
under Icarus through rtl/tb/tb_parity.v -- the harness
tests/test_hisa/test_execution_parity.py already drives -- with its +TRACE, and
the board is what cosmictera-build/ recorded.

-- the four engines, and what each one is in this repository ----------------
  python       The book's own functions (src/hijaiyyah/algebra, core) applied
               to the operands the interpreter held at that step. Four opcodes
               have one the interpreter does not call: HLOAD (the Master Table
               entry whose own .index is the immediate), HCADD (add_codex),
               HNRM2 (norm2), HDIST (distance_decomposition). For every other
               opcode the Python implementation IS the interpreter --
               src/hijaiyyah/vm delegates to HISAMachine -- so there is no
               second Python answer, and the model says "same engine" rather
               than inventing one.
  interpreter  HISAMachine.
  rtl          rtl/*.v, simulated.
  board        Recorded output only: the board carries the 72-hour burn-in.
               A record older than the last change to the CPU's RTL describes a
               design that is gone (R4), so only records dated after it count,
               and the board is seen through what it printed -- its registers
               are not visible from the wire.

-- how a divergence is located -----------------------------------------------
Both runs are reduced to streams of state CHANGES, one per kind: GPR, HREG,
FLAGS, RAM, MMIO (every store into the peripheral window) and TX (every byte
handed to the UART). A write that leaves a value as it was is not a change on
either side. The pipeline commits in program order, so the n-th change of a
kind on the RTL is the n-th on the interpreter, or the two disagree; the first
index where they do names the interpreter step, its pc, its source line, its
opcode, and the register or address, with both values. When the step that
diverged read a memory-mapped register, the divergence is charged to that
register, not to the opcode that carried the value: a LOAD of COUNTER that
differs is the timer differing, not LOAD.

PRINT's text is compared as bytes. The interpreter records the value PRINT
printed; the model renders it the way docs/HISA_SPEC.md defines PRINT --
decimal, ended by a newline.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..algebra.aggregametric import add_codex
from ..algebra.intrametric import distance_decomposition
from ..algebra.vektronometry import norm2
from ..core.master_table import MASTER_TABLE
from ..hisa.assembler import assemble
from ..hisa.machine import HISAMachine
from ..hisa.opcodes import RTL_IMPLEMENTED, InstructionWord, OpCode
from ..hisa.parity_programs import PROGRAMS
from .execution_trace import Step, label_map, run, source_map
from .program_index import programs
from .repository_index import ROOT

Model = dict[str, Any]

MODEL = ROOT / "NUI" / "parity_model.json"
PAGE = ROOT / "NUI" / "PARITY.md"
HARNESS = ROOT / "rtl" / "tb" / "tb_parity.v"
KINDS = ("GPR", "HREG", "FLAGS", "RAM", "MMIO", "TX")
#: Steps the interpreter runs per program here. Layer 3 runs 20,000; the RTL
#: simulates about 10,600 cycles a second, so a program that never halts is
#: compared over a prefix instead, and its status says so.
MAX_STEPS = 5_000
#: The last commit that changed the CPU's RTL, and its date. Board records
#: made before it are about a different design. A test holds this to git.
LAST_CPU_RTL_CHANGE = ("e4c251e", "2026-09-17")
HALTED = ("halt", "fault")

# -- corpora ------------------------------------------------------------------

LADDER = "print-ladder"
#: 2^0 .. 2^31, one PRINT each: the values f236499 sent to the board. That
#: program was never committed; its values were, and a register holding 2^k
#: is 2^k however it got there.
LADDER_SOURCE = "        MOVI  R1, 1\n        PRINT R1\n" + (
    "        SHLI  R1, R1, 1\n        PRINT R1\n" * 31) + "        HALT\n"


@dataclass
class Program:
    name: str
    words: list[int]
    sources: dict[int, tuple[str, int]]
    labels: dict[int, str]


def corpus() -> list[Program]:
    out = []
    for name, words in sorted(PROGRAMS.items()):
        out.append(Program(f"parity:{name}", list(words),
                           {pc: (f"<parity:{name}>", pc + 1) for pc in range(len(words))}, {}))
    for path in sorted(programs().hasm):
        source = ROOT / path
        words = assemble(source.read_text(encoding="utf-8"), base_dir=source.parent)
        out.append(Program(path, words, dict(enumerate(source_map(path))), label_map(path)))
    words = assemble(LADDER_SOURCE)
    out.append(Program(LADDER, words, {pc: ("<print-ladder>", pc + 1)
                                       for pc in range(len(words))}, {}))
    return out


# -- the interpreter ----------------------------------------------------------

#: The four opcodes whose meaning the book computes by a function the
#: interpreter does not call.
PY_REFERENCE = {
    "HLOAD": "src/hijaiyyah/core/master_table.py::MasterTable.get_by_index",
    "HCADD": "src/hijaiyyah/algebra/aggregametric.py::add_codex",
    "HNRM2": "src/hijaiyyah/algebra/vektronometry.py::norm2",
    "HDIST": "src/hijaiyyah/algebra/intrametric.py::distance_decomposition",
}


def _reference(name: str, iw: InstructionWord, hreg: list[list[int]]) -> Any:
    """The book's answer for one execution, or None where it has none."""
    if name == "HLOAD":
        entry = MASTER_TABLE.get_by_index(iw.imm)
        return None if entry is None else list(entry.vector)
    if name == "HCADD":
        return add_codex(hreg[iw.src1], hreg[iw.src2])["cod18"]
    if name == "HNRM2":
        return norm2(hreg[iw.src1])
    if name == "HDIST":
        return distance_decomposition(hreg[iw.src1], hreg[iw.src2])["total"]
    raise KeyError(name)


@dataclass
class Event:
    kind: str
    key: int
    value: Any
    step: int | None = None     # interpreter step
    cycle: int | None = None    # RTL cycle


@dataclass
class InterpreterRun:
    exit: str
    exit_detail: str
    steps: list[Step]
    events: dict[str, list[Event]]
    printed: list[int]
    final: dict[str, Any]
    python: list[dict[str, Any]] = field(default_factory=list)
    imem_written: bool = False


def _tx_bytes(value: int) -> list[int]:
    return list(f"{value}\n".encode("ascii"))


def run_interpreter(program: Program, max_steps: int = MAX_STEPS) -> InterpreterRun:
    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(list(program.words))
    flags: list[int] = []
    python: list[dict[str, Any]] = []
    step = machine.step

    def observed_step():  # type: ignore[no-untyped-def]
        pc = machine.regs.pc
        iw = InstructionWord(machine.code[pc]) if pc < len(machine.code) else None
        name = ""
        if iw is not None:
            try:
                name = OpCode(iw.opcode).name
            except ValueError:
                name = ""
        before = [list(h) for h in machine.regs.hreg] if name in PY_REFERENCE else None
        active = machine.trap_active
        entry = step()
        flags.append(machine._pack_flags())
        # Checked only when the instruction ran. A trap or an HCHECK taken in
        # its place returns its own entry -- the rule layer 3 uses. The first
        # version asked whether the cycle count moved, and taking a trap moves
        # it too (machine.py, _maybe_trap), so a trap taken on an HLOAD's word
        # read as an HLOAD that loaded nothing.
        desc = entry.description if entry is not None else ""
        ran = entry is not None and not desc.startswith("HCHECK") and not (
            desc.startswith("TRAP") and machine.trap_active and not active)
        if before is not None and iw is not None and ran:
            want = _reference(name, iw, before)
            got = (list(machine.regs.hreg[iw.dst]) if name in ("HLOAD", "HCADD")
                   else machine.regs.gpr[iw.dst])
            python.append({"opcode": name, "step": len(flags) - 1, "pc": pc,
                           "reference": want, "interpreter": got,
                           "agrees": None if want is None else want == got})
        return entry

    machine.step = observed_step  # type: ignore[method-assign]
    trace = run(machine, program.sources, program.name, max_steps, keep=max_steps,
                labels=program.labels)
    events: dict[str, list[Event]] = {k: [] for k in KINDS}
    shadow = [[0] * 18 for _ in range(16)]
    previous_flags = 0
    window = HISAMachine.PERIPH_WINDOW
    imem_written = False
    for s in trace.steps:
        for r, _, a in s.gpr:
            events["GPR"].append(Event("GPR", r, a, step=s.index))
        touched = sorted({h for h, _, _, _ in s.hreg})
        for h, c, _, a in s.hreg:
            shadow[h][c] = a
        for h in touched:
            events["HREG"].append(Event("HREG", h, tuple(shadow[h]), step=s.index))
        if s.index < len(flags) and flags[s.index] != previous_flags:
            previous_flags = flags[s.index]
            events["FLAGS"].append(Event("FLAGS", 0, previous_flags, step=s.index))
        for acc in s.accesses:
            if acc.kind != "write":
                continue
            if acc.address >= window:
                events["MMIO"].append(Event("MMIO", acc.address, acc.value, step=s.index))
                imem_written |= acc.mmio == "IMEM_DATA"
            elif acc.before != acc.after:
                events["RAM"].append(Event("RAM", acc.address, acc.after, step=s.index))
        text: list[int] = []
        for v in s.printed:
            text += _tx_bytes(v)
        for name, before, after in s.state:
            if name == "len(chars)":
                text += machine.chars[before:after]
        for byte in text:
            events["TX"].append(Event("TX", 0, byte, step=s.index))
    final = {"gpr": list(machine.regs.gpr[:16]),
             "hreg": [list(h) for h in machine.regs.hreg[:16]],
             "flags": machine._pack_flags()}
    return InterpreterRun(trace.exit, trace.exit_detail, trace.steps, events,
                          list(trace.printed), final, python, imem_written)


# -- the RTL ------------------------------------------------------------------


def compile_rtl(workdir: Path) -> Path:
    if shutil.which("iverilog") is None:
        raise RuntimeError("Icarus Verilog is required to run the RTL column")
    out = workdir / "tb_parity.vvp"
    sources = [str(HARNESS), *sorted(str(p) for p in (ROOT / "rtl").glob("*.v"))]
    proc = subprocess.run(["iverilog", "-g2012", "-I", str(ROOT / "rtl"), "-o", str(out),
                           *sources], capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"iverilog failed:\n{proc.stderr}")
    return out


@dataclass
class RtlRun:
    halted: bool
    cycles: int
    budget: int
    events: dict[str, list[Event]]
    final: dict[str, Any]


def _hex(text: str) -> int | str:
    """A value the simulator printed. Icarus prints an undefined bit as x or
    z; such a value is kept as its text, and no integer ever equals it."""
    try:
        return int(text, 16)
    except ValueError:
        return text.lower()


def _hreg_bytes(text: str) -> tuple[int, ...] | str:
    packed = _hex(text)
    if isinstance(packed, str):
        return packed
    return tuple((packed >> (8 * i)) & 0xFF for i in range(18))


def run_rtl(sim: Path, words: list[int], budget: int, workdir: Path) -> RtlRun:
    hexfile = workdir / f"p{os.getpid()}_{id(words)}.hex"
    hexfile.write_text("".join(f"{w:08X}\n" for w in words), encoding="utf-8")
    proc = subprocess.run(["vvp", "-n", str(sim), f"+PROGRAM={hexfile}",
                           f"+CYCLES={budget}", "+TRACE"],
                          capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError(f"vvp failed:\n{proc.stdout[-2000:]}\n{proc.stderr}")
    events: dict[str, list[Event]] = {k: [] for k in KINDS}
    gpr: list[int | str] = [0] * 32
    hreg: list[tuple[int, ...] | str] = [tuple([0] * 18)] * 16
    ram: dict[int, int | str] = {}
    flags: int | str = 0
    final: dict[str, Any] = {"gpr": [0] * 16, "hreg": [[0] * 18 for _ in range(16)],
                             "flags": 0}
    halted, cycles = False, 0
    for line in proc.stdout.splitlines():
        part = line.split()
        if part and part[0] == "T" and len(part) >= 4:
            cycle, kind = int(part[1]), part[2]
            if kind == "GPR":
                r, v = int(part[3]), _hex(part[4])
                if gpr[r] != v:
                    gpr[r] = v
                    events["GPR"].append(Event("GPR", r, v, cycle=cycle))
            elif kind == "HREG":
                h, vec = int(part[3]), _hreg_bytes(part[4])
                if hreg[h] != vec:
                    hreg[h] = vec
                    events["HREG"].append(Event("HREG", h, vec, cycle=cycle))
            elif kind == "FLAGS":
                v = _hex(part[3])
                if v != flags:
                    flags = v
                    events["FLAGS"].append(Event("FLAGS", 0, v, cycle=cycle))
            elif kind == "RAM":
                a, v = int(part[3], 16), _hex(part[4])
                if ram.get(a, 0) != v:
                    ram[a] = v
                    events["RAM"].append(Event("RAM", a, v, cycle=cycle))
            elif kind == "MMIO":
                events["MMIO"].append(Event("MMIO", int(part[3], 16), _hex(part[4]),
                                            cycle=cycle))
            elif kind == "TX":
                events["TX"].append(Event("TX", 0, _hex(part[3]), cycle=cycle))
        elif m := re.fullmatch(r"HALTED=(\d)", line.strip()):
            halted = m.group(1) == "1"
        elif m := re.fullmatch(r"CYCLES=(\d+)", line.strip()):
            cycles = int(m.group(1))
        elif m := re.fullmatch(r"GPR\[(\d+)\]=(\w{8})", line.strip()):
            if int(m.group(1)) < 16:
                final["gpr"][int(m.group(1))] = _hex(m.group(2))
        elif m := re.fullmatch(r"HREG\[(\d+)\]=(\w{36})", line.strip()):
            vec = _hreg_bytes(m.group(2))
            final["hreg"][int(m.group(1))] = vec if isinstance(vec, str) else list(vec)
        elif m := re.fullmatch(r"FLAGS=(\w{2})", line.strip()):
            final["flags"] = _hex(m.group(1))
    hexfile.unlink(missing_ok=True)
    return RtlRun(halted, cycles, budget, events, final)


def cycle_budget(interp: InterpreterRun) -> int:
    """Enough for the RTL to cover what the interpreter did: a few clocks per
    instruction, about a hundred per byte on the wire (tb_parity runs the
    UART at 5 Mbaud from 50 MHz), and slack. Measured against the corpus on
    21 September 2026: the tightest run, print-ladder, halts in 20,375 of
    its 28,400 cycles. A test holds every halted run under 90% of its budget,
    so a program cannot turn UNKNOWN by running out of it unnoticed."""
    return 8 * len(interp.steps) + 120 * len(interp.events["TX"]) + 4_000


# -- the comparison -----------------------------------------------------------


def _where(program: Program, run_: InterpreterRun, step: int | None) -> dict[str, Any]:
    if step is None or step >= len(run_.steps):
        return {"step": step}
    s = run_.steps[step]
    reads = sorted({a.mmio for a in s.accesses if a.mmio and a.kind == "read"})
    where = f"{s.source[0]}:{s.source[1]}" if s.source else "<unmapped>"
    return {"step": s.index, "pc": s.pc, "where": where, "opcode": s.mnemonic,
            "reads_mmio": reads}


def _show(e: Event | None) -> Any:
    if e is None:
        return None
    value = list(e.value) if isinstance(e.value, tuple) else e.value
    return {"key": e.key, "value": value}


def compare(program: Program, interp: InterpreterRun, rtl: RtlRun) -> Model:
    """First divergence between the two change streams, or none."""
    first: Model | None = None
    compared = {}
    matched = {}
    complete = interp.exit in HALTED and rtl.halted
    for kind in KINDS:
        a, b = interp.events[kind], rtl.events[kind]
        n = min(len(a), len(b))
        compared[kind] = n
        index = next((i for i in range(n)
                      if (a[i].key, a[i].value) != (b[i].key, b[i].value)), None)
        matched[kind] = n if index is None else index
        if index is None and complete and len(a) != len(b):
            index = n
        if index is None:
            continue
        ea = a[index] if index < len(a) else None
        eb = b[index] if index < len(b) else None
        # A change the RTL made that the interpreter never did, once both
        # have stopped, came AFTER the interpreter's last step: it is charged
        # to that step -- the instruction that should have stopped the
        # machine -- and ordered after every in-run difference.
        last = len(interp.steps) - 1
        step = ea.step if ea is not None else last
        candidate: Model = {"kind": kind, "index": index,
                     "interpreter": {**_where(program, interp, step), **(_show(ea) or {})},
                     "rtl": {"cycle": eb.cycle if eb else None, **(_show(eb) or {})}}
        if ea is None:
            candidate["interpreter"]["stopped_here"] = True
            candidate["rtl"]["after_stop"] = True
        if eb is None:
            candidate["rtl"]["missing"] = True
        key = (step if step is not None else 1 << 62) * 2 + (1 if ea is None else 0)
        if first is None or key < first["_order"]:
            first = {**candidate, "_order": key}
    if first is not None:
        first.pop("_order")
        status = "MISMATCH"
    elif interp.exit == "hcheck" and not (rtl.halted and all(
            len(interp.events[k]) == len(rtl.events[k]) for k in KINDS)):
        status = "MISMATCH"
        last = len(interp.steps) - 1
        first = {"kind": "EXIT", "index": None,
                 "interpreter": {**_where(program, interp, last),
                                 "value": interp.exit_detail},
                 "rtl": {"halted": rtl.halted, "cycle": rtl.cycles}}
    elif complete:
        status = "PARITY" if interp.final == rtl.final else "MISMATCH"
        if status == "MISMATCH":
            first = {"kind": "FINAL", "index": None,
                     "interpreter": interp.final, "rtl": rtl.final}
    else:
        status = "UNKNOWN"
    reason = ""
    if status == "UNKNOWN":
        parts = []
        if interp.exit not in HALTED:
            parts.append(f"interpreter {interp.exit} after {len(interp.steps)} steps")
        if not rtl.halted:
            parts.append(f"RTL did not halt within {rtl.budget} cycles")
        reason = "; ".join(parts) + " -- compared as far as both ran"
    # The pipeline commits in program order, so once the RTL has produced the
    # change an interpreter step made, it has executed every step before it.
    # Every step up to the latest matched change, and before the earliest
    # unmatched one, therefore ran on both engines and agreed.
    seen = [st for k in KINDS for j in range(matched[k])
            if (st := interp.events[k][j].step) is not None]
    unmatched = [st for k in KINDS if matched[k] < len(interp.events[k])
                 and (st := interp.events[k][matched[k]].step) is not None]
    through = min([max(seen, default=-1)] + [u - 1 for u in unmatched])
    if status == "PARITY":
        through = len(interp.steps) - 1
    if interp.imem_written and status != "PARITY":
        status, reason = "UNKNOWN", ("writes instruction memory, which tb_parity.v "
                                     "does not implement")
        first = None
    return {"status": status, "first_divergence": first, "reason": reason,
            "compared": compared, "agreed_through_step": through,
            "interpreter": {"exit": interp.exit, "exit_detail": interp.exit_detail,
                            "steps": len(interp.steps),
                            "events": {k: len(v) for k, v in interp.events.items()}},
            "rtl": {"halted": rtl.halted, "cycles": rtl.cycles, "budget": rtl.budget,
                    "events": {k: len(v) for k, v in rtl.events.items()}}}


# -- the board ----------------------------------------------------------------

#: Records the model reads, by where they live. The value itself is parsed
#: out of the record at build time and never copied here (R1).
BOARD_TABLES = [
    # (program, record, section heading prefix, row name)
    ("rtl/programs/test_bsm.hasm", "cosmictera-build/PAPAN.md",
     "## Tahap 1 — berkas bertahan melewati mati daya, 18 September 2026", "test_bsm"),
    ("rtl/programs/test_codex.hasm", "cosmictera-build/PAPAN.md",
     "## Tahap 1 — berkas bertahan melewati mati daya, 18 September 2026", "test_codex"),
    ("rtl/programs/test_cset.hasm", "cosmictera-build/PAPAN.md",
     "## Tahap 1 — berkas bertahan melewati mati daya, 18 September 2026", "test_cset"),
    ("rtl/programs/test_hfs.hasm", "cosmictera-build/PAPAN.md",
     "## Tahap 1 — berkas bertahan melewati mati daya, 18 September 2026", "test_hfs"),
]
#: Found by the name the owner gave the entry, not by its prose: the prose
#: heading was renamed once (324d409) and this lookup broke with it.
LADDER_RECORD = ("cosmictera-build/OFF.md", "### OFF-PRINT-SILICON")
RECORD_DATE = {"## Tahap 1 — berkas bertahan melewati mati daya, 18 September 2026":
               "2026-09-18", "### OFF-PRINT-SILICON": "2026-09-20"}


def _section(path: str, heading: str) -> tuple[list[str], int]:
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(heading))
    level = heading.split(" ")[0]
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("#") and len(lines[i].split(" ")[0]) <= len(level)),
               len(lines))
    return lines[start:end], start + 1


def board_row(path: str, heading: str, name: str) -> tuple[str, int]:
    """The first backticked value in the 'keluaran papan' column of the row
    naming `name` in that section, and its line number."""
    lines, first = _section(path, heading)
    header: list[str] = []
    for offset, line in enumerate(lines):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and "keluaran papan" in cells:
            header = cells
            continue
        if header and line.startswith("|") and f"`{name}`" in cells:
            cell = cells[header.index("keluaran papan")]
            value = re.search(r"`([^`]+)`", cell)
            if value:
                return value.group(1), first + offset
    raise LookupError(f"{name} has no board output under {heading!r} in {path}")


def _number(text: str) -> int:
    return int(text.replace(".", ""))


def ladder_records() -> list[dict[str, Any]]:
    """value -> what the board printed, from OFF.md's table. A row reading
    `benar` recorded the value itself; `sampai` covers every power of two up
    to it."""
    path, heading = LADDER_RECORD
    lines, first = _section(path, heading)
    out = []
    for offset, line in enumerate(lines):
        m = re.match(r"\|\s*(sampai\s+)?([\d.]+)\s*\(2[^)]*\)\s*\|\s*(.+?)\s*\|$", line)
        if not m:
            continue
        top, cell = _number(m.group(2)), m.group(3)
        literal = re.search(r"`([^`]+)`", cell)
        values = [1 << k for k in range(32) if (1 << k) <= top] if m.group(1) else [top]
        for v in values:
            out.append({"value": v, "board": literal.group(1) if literal else str(v),
                        "record": f"{path}:{first + offset}"})
    return out


def _printed_text(events: list[Event]) -> str:
    return "".join(chr(e.value) if isinstance(e.value, int) else f"<{e.value}>"
                   for e in events)


def board_rows(programs_: dict[str, Program], interp: dict[str, InterpreterRun],
               rtl: dict[str, RtlRun]) -> list[Model]:
    rows: list[Model] = []
    for program, path, heading, name in BOARD_TABLES:
        value, line = board_row(path, heading, name)
        ours = " ".join(_printed_text(interp[program].events["TX"]).split())
        theirs = " ".join(_printed_text(rtl[program].events["TX"]).split())
        rows.append({"program": program, "board": value, "interpreter": ours, "rtl": theirs,
                     "record": f"{path}:{line}", "date": RECORD_DATE[heading],
                     "status": "PARITY" if value == ours == theirs else "MISMATCH"})
    lines_i = _printed_text(interp[LADDER].events["TX"]).split("\n")
    lines_r = _printed_text(rtl[LADDER].events["TX"]).split("\n")
    prints = [s for s in interp[LADDER].steps if s.mnemonic == "PRINT"]
    for rec in ladder_records():
        k = rec["value"].bit_length() - 1
        step = prints[k] if k < len(prints) else None
        rows.append({"program": LADDER, "value": rec["value"], "board": rec["board"],
                     "interpreter": lines_i[k] if k < len(lines_i) else None,
                     "rtl": lines_r[k] if k < len(lines_r) else None,
                     "record": rec["record"], "date": RECORD_DATE[LADDER_RECORD[1]],
                     "step": step.index if step else None,
                     "status": ("PARITY" if rec["board"] == lines_i[k] == lines_r[k]
                                else "MISMATCH")})
    return rows


# -- the model ----------------------------------------------------------------


def _source_of(mnemonic: str) -> str:
    """Where the RTL decodes an opcode: the line of rtl/hcpu_pkg.vh that
    defines OP_<name>. Evidence of where to look, not a claim of cause."""
    pkg = (ROOT / "rtl" / "hcpu_pkg.vh").read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(pkg, 1):
        if re.match(rf"\s*`define\s+OP_{mnemonic}\s", line):
            return f"rtl/hcpu_pkg.vh:{number}"
    return ""


def _line_of(path: str, text: str) -> str:
    """path:line of the first line containing `text`, found, never typed."""
    for number, line in enumerate((ROOT / path).read_text(encoding="utf-8").splitlines(), 1):
        if text in line:
            return f"{path}:{number}"
    return ""


def _print_source() -> str:
    return _line_of("rtl/hcpu_top.v", "print_val % 10")


def _stop_source() -> str:
    """Where a stop takes effect: `halted` is set from wb_halt one clock after
    the stopping instruction reaches writeback, and the writeback write
    enable is not gated by it -- so the instruction behind it writes."""
    return ", ".join(x for x in (_line_of("rtl/hcpu_controller.v", "else if (wb_halt)"),
                                 _line_of("rtl/hcpu_writeback.v", "assign wb_gpr_we")) if x)


def build(jobs: int | None = None) -> Model:
    progs = corpus()
    by_name = {p.name: p for p in progs}
    interp = {p.name: run_interpreter(p) for p in progs}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        sim = compile_rtl(work)
        with ThreadPoolExecutor(max_workers=jobs or min(8, os.cpu_count() or 2)) as pool:
            futures = {p.name: pool.submit(run_rtl, sim, p.words,
                                           cycle_budget(interp[p.name]), work)
                       for p in progs}
            rtl = {name: f.result() for name, f in futures.items()}
    results = {p.name: compare(p, interp[p.name], rtl[p.name]) for p in progs}
    board = board_rows(by_name, interp, rtl)
    opcodes = _opcode_rollup(by_name, interp, results, board)
    return {
        "generated_by": "src/hijaiyyah/nui/parity_model.py",
        "engines": {
            "python": "book functions for HLOAD, HCADD, HNRM2, HDIST; otherwise the "
                      "interpreter itself (src/hijaiyyah/vm delegates to it)",
            "interpreter": "src/hijaiyyah/hisa/machine.py",
            "rtl": "rtl/*.v under Icarus via rtl/tb/tb_parity.v +TRACE",
            "board": f"recorded output dated after {LAST_CPU_RTL_CHANGE[0]} "
                     f"({LAST_CPU_RTL_CHANGE[1]}), the last change to the CPU's RTL",
        },
        "max_steps": MAX_STEPS,
        "programs": results,
        "python": _python_rollup(interp),
        "board": board,
        "opcodes": opcodes,
        "mmio": _mmio_rollup(results),
        "unknown": _unknowns(results, board, opcodes),
    }


def _python_rollup(interp: dict[str, InterpreterRun]) -> Model:
    out: Model = {}
    for name, source in PY_REFERENCE.items():
        rows = [(program, r) for program, run_ in sorted(interp.items())
                for r in run_.python if r["opcode"] == name]
        checked = [(p, r) for p, r in rows if r["agrees"] is not None]
        wrong = [{"program": p, "step": r["step"], "pc": r["pc"],
                  "reference": r["reference"], "interpreter": r["interpreter"]}
                 for p, r in checked if not r["agrees"]]
        out[name] = {"reference": source, "executions": len(rows),
                     "checked": len(checked), "no_reference": len(rows) - len(checked),
                     "mismatches": wrong,
                     "status": ("MISMATCH" if wrong else "PARITY" if checked else "UNKNOWN")}
    return out


def _opcode_rollup(progs: dict[str, Program], interp: dict[str, InterpreterRun],
                   results: dict[str, Model], board: list[Model]) -> Model:
    board_ok = {r["program"] for r in board if r["status"] == "PARITY" and "value" not in r}
    board_bad: dict[str, list[Model]] = {}
    for r in board:
        if r["status"] == "MISMATCH" and r.get("step") is not None:
            board_bad.setdefault("PRINT", []).append(r)
    python = _python_rollup(interp)
    out: Model = {}
    # TRAP is not an opcode: it is the step on which the machine takes a trap
    # instead of executing, and layer 3 records it under that name.
    for name in [op.name for op in OpCode] + ["TRAP"]:
        agree, mismatch, witness = [], [], None
        for pname, res in sorted(results.items()):
            steps = interp[pname].steps
            div = res["first_divergence"]
            charged = bool(div and div["interpreter"].get("reads_mmio"))
            if res["status"] == "MISMATCH" and div and div["interpreter"].get("opcode") == name \
                    and not charged and div["kind"] not in ("EXIT", "FINAL"):
                mismatch.append({"program": pname, **div})
            upto = res["agreed_through_step"] + 1
            ran = [s for s in steps[:upto] if s.mnemonic == name
                   and s.kind == ("trap" if name == "TRAP" else "instruction")]
            if ran:
                agree.append(pname)
                if witness is None:
                    witness = _witness(pname, interp[pname], ran)
        on_board = sorted(p for p in board_ok
                          if any(s.mnemonic == name for s in interp[p].steps))
        py = python.get(name, {"status": "SAME ENGINE"})
        rtl_status = ("MISMATCH" if mismatch else "PARITY" if agree else "UNKNOWN")
        board_status = ("MISMATCH" if name in board_bad else "PARITY" if on_board else "UNKNOWN")
        py_status = py["status"]
        statuses = (py_status if py_status != "SAME ENGINE" else "PARITY", rtl_status,
                    board_status)
        status = ("MISMATCH" if "MISMATCH" in statuses else
                  "PARITY" if all(s == "PARITY" for s in statuses) else "UNKNOWN")
        entry: Model = {
            "in_rtl": name == "TRAP" or OpCode[name] in RTL_IMPLEMENTED,
            "python": py_status, "rtl": rtl_status, "board": board_status,
            "status": status,
            "agreeing_programs": agree, "mismatches": mismatch,
            "board_programs": on_board, "witness": witness,
        }
        if name in board_bad:
            entry["board_mismatches"] = board_bad[name]
            entry["source"] = _print_source()
        if mismatch:
            after_stop = all(m["rtl"].get("after_stop") for m in mismatch)
            entry["source"] = _stop_source() if after_stop else _source_of(name)
        if name == "TRAP":
            entry["note"] = "not an opcode: the step on which the machine takes a trap"
        if not entry["in_rtl"]:
            entry["reason"] = "not in RTL_IMPLEMENTED: the HCPU halts with HALT_ERR on it"
        elif not agree and not mismatch:
            entry["reason"] = ("no run in the corpus executes it at a step both engines "
                               "reached and agreed on")
        out[name] = entry
    return out


def _witness(program: str, run_: InterpreterRun, ran: list[Step]) -> Model:
    """The first execution of an opcode in a run that agreed, with the state
    it changed -- the concrete line the owner's parity model prints. `event`
    says whether that change is one the RTL stream carries."""
    for s in ran:
        where = f"{s.source[0]}:{s.source[1]}" if s.source else ""
        base = {"program": program, "step": s.index, "where": where}
        if s.gpr:
            r, _, a = s.gpr[0]
            return {**base, "change": f"R{r}={a}", "event": True}
        if s.printed:
            return {**base, "change": f"printed {s.printed[0]}", "event": True}
        if s.hreg:
            h = s.hreg[0][0]
            return {**base, "change": f"H{h}[{s.hreg[0][1]}]={s.hreg[0][3]}", "event": True}
        writes = [acc for acc in s.accesses if acc.kind == "write"]
        if writes:
            first = writes[0]
            place = first.mmio or f"MEM[{first.address:#05x}]"
            return {**base, "change": f"{place}={first.value}", "event": True}
        if s.trap:
            return {**base, "change": f"trap cause={s.trap[0]} epc={s.trap[1]:#05x} "
                                      f"vector={s.trap[2]:#05x}", "event": False}
        if s.mnemonic == "HALT":
            return {**base, "change": "halted", "event": False}
    s = ran[0]
    return {"program": program, "step": s.index,
            "where": f"{s.source[0]}:{s.source[1]}" if s.source else "",
            "change": f"pc {s.pc:#05x} -> {s.pc_after:#05x}", "event": False}


def _mmio_rollup(results: dict[str, Model]) -> Model:
    out: Model = {}
    for pname, res in sorted(results.items()):
        div = res["first_divergence"]
        if not div or not div["interpreter"].get("reads_mmio"):
            continue
        for reg in div["interpreter"]["reads_mmio"]:
            out.setdefault(reg, []).append({"program": pname, **div})
    return out


def _unknowns(results: dict[str, Model], board: list[Model],
              opcodes: Model) -> Model:
    out: Model = {
        "opcodes_not_in_rtl": sorted(n for n, e in opcodes.items() if not e["in_rtl"]),
        "rtl_opcodes_without_an_agreeing_execution": sorted(
            n for n, e in opcodes.items() if e["in_rtl"] and e["rtl"] == "UNKNOWN"),
        "programs_not_halted": sorted(p for p, r in results.items()
                                      if r["status"] == "UNKNOWN"),
        "board_values_not_recorded": [
            f"{LADDER}: 2^{k}" for k in range(32)
            if not any(r.get("value") == 1 << k for r in board)],
        "scope": [
            "rtl/programs/loader.hasm#with-payload is not run on the RTL: tb_parity.v "
            "has no UART receiver input and no instruction-memory write port",
            "the board is not run: it carries the 72-hour burn-in. Only records dated "
            f"after {LAST_CPU_RTL_CHANGE[0]} are read",
            "board records of card, wire, generated or Ka'bah-slot programs are not "
            "compared: no other engine here has a card, a wire, or that slot",
            "cosmictera-build/OFF.md's SD init after a mid-read reconfiguration is "
            "board-only: no other engine has a card or a reconfiguration",
        ],
    }
    return out


# -- persistence and verification ----------------------------------------------


def write(model: Model | None = None) -> Path:
    model = model or build()
    MODEL.write_text(json.dumps(model, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    PAGE.write_text(page(json.loads(MODEL.read_text(encoding="utf-8"))), encoding="utf-8")
    return MODEL


def verify(claimed: Model, fresh: Model | None = None) -> list[str]:
    """Rebuild and name every claim the rebuild does not reproduce."""
    fresh = fresh if fresh is not None else json.loads(json.dumps(build()))
    problems = []
    for section in ("programs", "opcodes", "python", "mmio"):
        a, b = claimed.get(section, {}), fresh.get(section, {})
        for key in sorted(set(a) | set(b)):
            if key not in b:
                problems.append(f"not reproduced: {section} {key}")
            elif key not in a:
                problems.append(f"missing from the model: {section} {key}")
            elif a[key] != b[key]:
                fields = sorted(f for f in set(a[key]) | set(b[key])
                                if a[key].get(f) != b[key].get(f)) \
                    if isinstance(a[key], dict) and isinstance(b[key], dict) else ["value"]
                problems.append(f"differs: {section} {key} {', '.join(fields)}")
    if claimed.get("board") != fresh.get("board"):
        for i, (x, y) in enumerate(zip(claimed.get("board", []), fresh.get("board", []),
                                       strict=False)):
            if x != y:
                problems.append(f"differs: board row {i} ({x.get('program')})")
        if len(claimed.get("board", [])) != len(fresh.get("board", [])):
            problems.append("differs: board row count")
    if claimed.get("unknown") != fresh.get("unknown"):
        problems.append("differs: unknown inventory")
    return problems


# -- the page and the owner's format -------------------------------------------


def _named(kind: str, key: Any, value: Any) -> str:
    if kind == "GPR":
        return f"R{key}={value}"
    if kind == "HREG":
        return f"H{key}={value}"
    if kind in ("RAM", "MMIO") and isinstance(key, int):
        return f"{kind}[{key:#05x}]={value}"
    return f"{kind} {value}"


def _mismatch_line(m: Model, head: str | None = None) -> str:
    i, r = m["interpreter"], m["rtl"]
    if head is None:
        head = f"  {m['program']}: step {i.get('step')} {i.get('where')} ({i.get('opcode')})"
    if m["kind"] == "EXIT":
        return (f"{head}: the interpreter stops on its own check ({i.get('value')}); "
                f"the RTL {'halts later' if r.get('halted') else 'does not halt'}")
    if i.get("stopped_here"):
        return (f"{head}: the interpreter stops here; the RTL then commits "
                f"{_named(m['kind'], r.get('key'), r.get('value'))} at cycle {r.get('cycle')}")
    return (f"{head}: interpreter {_named(m['kind'], i.get('key'), i.get('value'))}, "
            f"RTL {_named(m['kind'], r.get('key'), r.get('value'))}")


def opcode_block(model: Model, name: str) -> str:
    """One opcode in the form the owner wrote it."""
    e = model["opcodes"][name]
    w = e.get("witness")
    lines = [f"OPCODE: {name}" + (f"  ({e['note']})" if e.get("note") else ""), ""]
    py = model["python"].get(name)
    if py:
        lines.append(f"Python: {py['status']} -- {py['checked']} execution(s) checked "
                     f"against {py['reference']}")
    else:
        lines.append("Python: same engine as the interpreter")
    lines.append(f"Interpreter: {w['change']}  ({w['program']}, step {w['step']}, "
                 f"{w['where']})" if w else "Interpreter: no execution both engines reached")
    rtl = f"RTL: {e['rtl']}"
    if w and e["rtl"] != "UNKNOWN":
        rtl += (f" -- {w['change']}" if w["event"] else
                " -- no change of its own; every change before and after it matched")
    lines.append(rtl)
    board = f"Board: {e['board']}"
    bad = e.get("board_mismatches", [])
    if bad:
        board += f" -- {len(bad)} recorded value(s) differ"
    if e["board_programs"]:
        board += (" -- printed output agreed in " +
                  ", ".join(p.split("/")[-1] for p in e["board_programs"]))
    lines.append(board)
    lines += ["", f"STATUS: {e['status']}"]
    lines += [_mismatch_line(m) for m in e["mismatches"][:5]]
    for m in bad[:5]:
        lines.append(f"  {m['program']} {m.get('value')}: interpreter={m['interpreter']!r} "
                     f"rtl={m['rtl']!r} board={m['board']!r}  ({m['record']}, {m['date']})")
    if e.get("source"):
        lines += ["", f"SOURCE: {e['source']}"]
    if e.get("reason"):
        lines.append(f"REASON: {e['reason']}")
    return "\n".join(lines)


def page(model: Model) -> str:
    """NUI/PARITY.md, drawn from the model only. The headings are the only
    words not taken from it; a test holds the committed page to this."""
    progs = model["programs"]
    ops = model["opcodes"]
    count = lambda xs, s: sum(1 for x in xs if x["status"] == s)  # noqa: E731
    out = ["# Model paritas — Lapis 4 NUI", "",
           f"Dihasilkan `{model['generated_by']}`, dan ditarik dari "
           "`NUI/parity_model.json` oleh `page()`. Yang ditulis tangan hanya judulnya.", "",
           "## Mesin", "", "| mesin | apa |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in model["engines"].items()]
    out += ["", "## Program: interpreter ↔ RTL", "", "| status | jumlah |", "|---|---:|"]
    for s in ("PARITY", "MISMATCH", "UNKNOWN"):
        out.append(f"| {s} | {count(progs.values(), s)} |")
    out += ["", "| program | status | selisih pertama |", "|---|---|---|"]
    for name, r in sorted(progs.items()):
        if r["status"] == "PARITY":
            continue
        d = r["first_divergence"]
        if d:
            i = d["interpreter"]
            detail = _mismatch_line(d, head=f"step {i.get('step')} `{i.get('where')}` "
                                             f"(`{i.get('opcode')}`)")
            if i.get("reads_mmio"):
                detail += f" -- the step read {', '.join(i['reads_mmio'])}"
        else:
            detail = r["reason"]
        out.append(f"| `{name}` | {r['status']} | {detail} |")
    out += ["", "## Opcode", "", "| status | jumlah |", "|---|---:|"]
    for s in ("PARITY", "MISMATCH", "UNKNOWN"):
        out.append(f"| {s} | {count(ops.values(), s)} |")
    out += ["", "| opcode | python | interpreter↔RTL | papan | status |", "|---|---|---|---|---|"]
    for name, e in ops.items():
        out.append(f"| `{name}` | {e['python']} | {e['rtl']} | {e['board']} | {e['status']} |")
    out += ["", "## Papan", "",
            "| program | nilai | papan | interpreter | RTL | status | catatan |",
            "|---|---|---|---|---|---|---|"]
    for r in model["board"]:
        out.append(f"| `{r['program']}` | {r.get('value', '')} | `{r['board']}` | "
                   f"`{r['interpreter']}` | `{r['rtl']}` | {r['status']} | `{r['record']}` |")
    out += ["", "## Python", "", "| opcode | referensi | diperiksa | status |",
            "|---|---|---:|---|"]
    for name, p in model["python"].items():
        out.append(f"| `{name}` | `{p['reference']}` | {p['checked']} | {p['status']} |")
    out += ["", "## Selisih yang ditanggung register MMIO", ""]
    for reg, rows in sorted(model["mmio"].items()):
        out.append(f"- `{reg}`: " + ", ".join(f"`{r['program']}`" for r in rows))
    out += ["", "## Inventaris UNKNOWN", ""]
    for key, values in sorted(model["unknown"].items()):
        out += [f"### `{key}` — {len(values)}", ""]
        out += [f"- {v}" for v in values] or ["- (kosong)"]
        out.append("")
    out += ["## Mengulang", "", "```bash",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.parity_model --verify",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.parity_model --opcode PRINT",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.parity_model --write", "```"]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    import sys
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--write":
        print(f"model: {write().relative_to(ROOT)}, page: {PAGE.relative_to(ROOT)}")
        return 0
    if args and args[0] == "--verify":
        problems = verify(json.loads(MODEL.read_text(encoding="utf-8")))
        print("\n".join(problems) if problems else "model reproduced exactly")
        return 1 if problems else 0
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    if len(args) == 2 and args[0] == "--opcode":
        print(opcode_block(model, args[1]))
        return 0
    for name in ("ADD", "SUB", "LOAD", "STORE", "CALL", "RET", "PRINT"):
        print(opcode_block(model, name), end="\n\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
