"""Layer 3: what actually happens when a program runs, recorded as it runs.

Layers 1 and 2 read the code. This layer runs it -- in HISAMachine, the
interpreter every other check in this repository already trusts -- and
writes down, step by step, what the machine did. Nothing here is predicted.
Every register change, every memory access, every trap is observed.

-- how an access is observed rather than computed ------------------------
HISAMachine sends every data access, memory-mapped or not, through two
methods: `_mem_read(addr)` and `_mem_write(addr, value)`. This module wraps
those two on one machine instance and records each call as it happens -- the
effective address the MACHINE computed from the registers it actually held.
That closes the gap layer 2 had to leave open: `LOAD R1, R5, 0xFF0` touches
the UART only if R5 is zero, and here R5's value at that step is simply known.
The wrapper calls straight through; the instrumented machine behaves
identically to an uninstrumented one, and a test holds it to that.

-- what a trace holds ------------------------------------------------------
    ENTRY   the program counter the run starts from
    STEP    one executed instruction, one trap taken, or the interpreter's
            periodic HCHECK stopping the run -- the last two execute nothing
    CHANGE  registers, H-register components, flags, data memory, machine
            state, output -- each recorded as before -> after, or NO_CHANGE
    EXIT    halt | fault | hcheck | end_of_code | step_cap, and why

`run()` hands exactly those lines to a sink when it is given one: the CLI
prints them, and the model keeps their SHA-256, so a trace nobody printed is
still held to its run.

Every step carries the source file and line its instruction came from. That
map is built by walking `.include` the way the assembler walks it, and it is
checked: the number of mapped instructions must equal the number of words the
assembler produces, or the trace is refused.

-- machine state, without naming it here --------------------------------
Memory-mapped registers are not stored in data memory; a write to TRAP_EPC
lands in the interpreter's `trap_epc`, a write to IMEM_DATA in `code`. So the
state model does not map addresses to fields -- that map would be a second
copy of `_periph_write`. It snapshots every integer the machine instance
holds, under the machine's own attribute names, and reports the ones that
moved; `cycle` is left out, because it advances on every step and the STEP
index already says so. A memory-mapped write is also checked against the
code memory it may have filled, word by word.

-- what the interpreter cannot show, said here ---------------------------
It has no SD card: the block reads as zero, so a traced driver takes its
empty-slot path, and the card path exists on the board only. Its timer
counts instructions, not clocks. Its register file has 18 slots where the
hardware has 16. These go into the UNKNOWN inventory, not into a claim.
"""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..hisa.assembler import _INCLUDE_RE, _strip, assemble, collect_labels, expand_includes
from ..hisa.opcodes import InstructionWord, OpCode
from .program_index import mmio_names
from .repository_index import ROOT

CONDITIONAL = {"JEQ", "JNE", "JLT", "JGE", "JGT", "JLE", "JZ", "JNZ"}
HARDWARE_GPRS = 16            # R0..R15; e239964 found R16/R17 absent in RTL
_LABEL = re.compile(r"^\s*[A-Za-z_]\w*\s*:")
_NOT_STATE = {"cycle"}


# -- where each instruction came from --------------------------------------


def source_map(path: str) -> list[tuple[str, int]]:
    """(file, line) for every instruction word, in address order.

    Walks .include in the assembler's own order and with its own `_strip`,
    and is checked against it: a map that disagrees with the assembler in
    length is refused rather than trusted."""
    seen: set[Path] = set()
    out: list[tuple[str, int]] = []

    def walk(file: Path) -> None:
        for number, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            match = _INCLUDE_RE.match(line)
            if match:
                target = (file.parent / match.group(1)).resolve()
                if target not in seen and target.is_file():
                    seen.add(target)
                    walk(target)
                continue
            if _strip(line):
                out.append((target_rel(file), number))

    def target_rel(file: Path) -> str:
        return file.resolve().relative_to(ROOT).as_posix()

    source = ROOT / path
    walk(source)
    words = assemble(source.read_text(encoding="utf-8"), base_dir=source.parent)
    if len(words) != len(out):
        raise ValueError(f"{path}: source map has {len(out)} lines for "
                         f"{len(words)} words -- refusing a trace it cannot place")
    return out


def label_map(path: str) -> dict[int, str]:
    """address -> label, from the assembler's own first pass. Where two
    labels name one address both are kept, joined by a comma."""
    source = ROOT / path
    lines = expand_includes(source.read_text(encoding="utf-8").splitlines(), source.parent)
    out: dict[int, list[str]] = {}
    for name, address in collect_labels(lines).items():
        out.setdefault(address, []).append(name)
    return {address: ",".join(sorted(names)) for address, names in out.items()}


# -- observed state --------------------------------------------------------


@dataclass(frozen=True)
class Access:
    kind: str            # "read" | "write"
    address: int
    value: int
    mmio: str | None     # register name, if memory-mapped
    consumed: bool       # a read that changed machine state (RX_DATA pops)
    before: int | None = None   # data memory only: the word before a write
    after: int | None = None    # and after it -- equal when a write changed nothing
    #: Code words a memory-mapped write changed: (address, before, after),
    #: `before` None where the word did not exist yet.
    code: tuple[tuple[int, int | None, int], ...] = ()


@dataclass(frozen=True)
class Step:
    index: int
    pc: int
    source: tuple[str, int] | None
    kind: str                                   # "instruction" | "trap" | "hcheck"
    mnemonic: str
    pc_after: int
    gpr: tuple[tuple[int, int, int], ...]        # (reg, before, after)
    hreg: tuple[tuple[int, int, int, int], ...]  # (H, component, before, after)
    flags: tuple[tuple[str, bool, bool], ...]
    accesses: tuple[Access, ...]
    printed: tuple[int, ...]
    trap: tuple[int, int, int] | None            # (cause, epc, vector)
    state: tuple[tuple[str, int, int], ...] = ()  # machine attribute, before, after

    @property
    def changed(self) -> bool:
        return bool(self.gpr or self.hreg or self.flags or self.printed or self.trap
                    or self.state
                    or any(a.consumed or a.code
                           or (a.kind == "write" and a.before != a.after)
                           for a in self.accesses))


@dataclass
class Trace:
    program: str
    entry: int
    steps: list[Step] = field(default_factory=list)      # first `keep` in full
    total_steps: int = 0
    exit: str = ""
    exit_detail: str = ""
    lines_executed: set[tuple[str, int]] = field(default_factory=set)
    opcodes: Counter[str] = field(default_factory=Counter)
    gprs_modified: set[int] = field(default_factory=set)
    hregs_modified: set[int] = field(default_factory=set)
    # (verb, register name, address)
    mmio: Counter[tuple[str, str, int]] = field(default_factory=Counter)
    memory_written: set[int] = field(default_factory=set)
    # (step, cause, epc, vector)
    traps: list[tuple[int, int, int, int]] = field(default_factory=list)
    # (mnemonic, step, pc from, pc to)
    transfers: list[tuple[str, int, int, int]] = field(default_factory=list)
    branches: dict[int, set[bool]] = field(default_factory=dict)
    final_window_mmio: set[str] = field(default_factory=set)
    printed: list[int] = field(default_factory=list)
    #: Integer attributes that appeared on the machine during the run and were
    #: not there when it started: name -> (first step, "file:line"). An
    #: attribute nobody declared is usually a misspelling of one somebody did.
    undeclared: dict[str, tuple[int, str]] = field(default_factory=dict)
    #: (KIND, target) -> [first step, pc, source "file:line", times]. Recorded
    #: during the run, so the evidence exists whatever `keep` was.
    edges: dict[tuple[str, str], list[object]] = field(default_factory=dict)

    def observe(self, kind: str, target: str, step: int, pc: int,
                source: tuple[str, int] | None) -> None:
        key = (kind, target)
        if key in self.edges:
            self.edges[key][3] = int(self.edges[key][3]) + 1   # type: ignore[call-overload]
        else:
            where = f"{source[0]}:{source[1]}" if source else "<unmapped>"
            self.edges[key] = [step, pc, where, 1]


class _Recorder:
    """Wraps one machine's two data-access methods and records every call."""

    def __init__(self, machine) -> None:
        self.machine = machine
        self.names = mmio_names()
        self.log: list[Access] = []
        read, write = machine._mem_read, machine._mem_write

        def recorded_read(addr: int) -> int:
            queue = len(machine.rx_queue)
            value: int = read(addr)
            masked = addr & machine.DATA_ADDR_MASK
            self.log.append(Access("read", masked, value, self.names.get(masked),
                                   len(machine.rx_queue) != queue))
            return value

        def recorded_write(addr: int, value: int) -> None:
            masked = addr & machine.DATA_ADDR_MASK
            plain = masked < machine.PERIPH_WINDOW
            before = machine.data_mem.get(masked, 0) if plain else None
            code = [] if plain else list(machine.code)
            write(addr, value)
            after = machine.data_mem.get(masked, 0) if plain else None
            filled = () if plain else tuple(
                (i, code[i] if i < len(code) else None, word)
                for i, word in enumerate(machine.code)
                if i >= len(code) or code[i] != word)
            self.log.append(Access("write", masked, value & 0xFFFFFFFF,
                                   self.names.get(masked), False, before, after, filled))

        machine._mem_read = recorded_read
        machine._mem_write = recorded_write

    def take(self) -> tuple[Access, ...]:
        out, self.log = tuple(self.log), []
        return out


def _state(machine) -> dict[str, int]:
    """Every integer the machine holds, by its own name, plus the lengths of
    the queues and stacks it keeps -- the part of its state that is neither a
    register nor data memory."""
    out = {k: int(v) for k, v in vars(machine).items()
           if isinstance(v, (bool, int)) and k not in _NOT_STATE}
    out["len(rx_queue)"] = len(machine.rx_queue)
    out["len(return_stack)"] = len(machine.return_stack)
    out["len(regs.stack)"] = len(machine.regs.stack)
    out["len(code)"] = len(machine.code)
    out["len(chars)"] = len(machine.chars)
    return out


def _mnemonic(word: int) -> str:
    try:
        return OpCode(InstructionWord(word).opcode).name
    except ValueError:
        return f"?{InstructionWord(word).opcode:#04x}"


def run(machine, sources: dict[int, tuple[str, int]], program: str,
        max_steps: int = 20_000, keep: int = 400,
        labels: dict[int, str] | None = None,
        sink: Callable[[str], None] | None = None) -> Trace:
    """Step `machine` to its end or to `max_steps`, recording every change.
    `sink`, if given, receives the rendered trace line by line: ENTRY, every
    STEP with its CHANGE or NO_CHANGE, EXIT -- kept or not."""
    labels = labels or {}

    def place(pc: int) -> str:
        return f"label:{labels[pc]}@{pc:#05x}" if pc in labels else f"pc:{pc:#05x}"

    recorder = _Recorder(machine)
    trace = Trace(program=program, entry=machine.regs.pc)
    declared = set(_state(machine))
    last_mnemonic = ""
    if sink is not None:
        sink(render_entry(trace))
    window: list[set[str]] = []
    for index in range(max_steps):
        pc = machine.regs.pc
        if machine._halted or pc >= len(machine.code):
            break
        word = machine.code[pc]
        gpr_before = list(machine.regs.gpr)
        hreg_before = [list(h) for h in machine.regs.hreg]
        sr = machine.regs.sr
        flags_before = (("zero", sr.zero), ("overflow", sr.overflow),
                        ("guard_pass", sr.guard_pass))
        active_before, printed_before = machine.trap_active, len(machine.output)
        state_before = _state(machine)

        entry = machine.step()
        if entry is None:
            break
        accesses = recorder.take()
        trapped = entry.description.startswith("TRAP") and machine.trap_active \
            and not active_before
        # step() returns an HCHECK entry INSTEAD of executing: the scan runs
        # before the fetch and halts on corruption. The first version recorded
        # that step as the instruction at pc, which never ran.
        hcheck = entry.description.startswith("HCHECK")
        kind = "trap" if trapped else "hcheck" if hcheck else "instruction"
        mnemonic = "TRAP" if trapped else "HCHECK" if hcheck else _mnemonic(word)

        gpr = tuple((r, b, a) for r, (b, a) in
                    enumerate(zip(gpr_before, machine.regs.gpr, strict=True)) if b != a)
        hreg = tuple((h, c, b, a) for h, (hb, ha) in
                     enumerate(zip(hreg_before, machine.regs.hreg, strict=True))
                     for c, (b, a) in enumerate(zip(hb, ha, strict=True)) if b != a)
        state_after = _state(machine)
        state = tuple((k, state_before.get(k, 0), v) for k, v in sorted(state_after.items())
                      if state_before.get(k, 0) != v)
        for name in state_after.keys() - declared:
            if name not in trace.undeclared:
                src = sources.get(pc)
                trace.undeclared[name] = (index, f"{src[0]}:{src[1]}" if src else "<unmapped>")
        sr = machine.regs.sr
        flags_after = (("zero", sr.zero), ("overflow", sr.overflow),
                       ("guard_pass", sr.guard_pass))
        flags = tuple((n, b, a) for (n, b), (_, a) in
                      zip(flags_before, flags_after, strict=True) if b != a)
        printed = tuple(machine.output[printed_before:])
        trap = ((machine.trap_cause, machine.trap_epc, machine.trap_vector)
                if trapped else None)
        step = Step(index, pc, sources.get(pc), kind, mnemonic, machine.regs.pc,
                    gpr, hreg, flags, accesses, printed, trap, state)
        if sink is not None:
            for line in render_step(step):
                sink(line)

        trace.total_steps += 1
        last_mnemonic = mnemonic
        if len(trace.steps) < keep:
            trace.steps.append(step)
        seen = trace.observe
        src = step.source
        if kind == "instruction":
            seen("EXECUTES", f"opcode:{mnemonic}", index, pc, src)
        for r, _, _ in gpr:
            seen("MODIFIES", f"reg:R{r}", index, pc, src)
        for h in sorted({h for h, _, _, _ in hreg}):
            seen("MODIFIES", f"hreg:H{h}", index, pc, src)
        for access in accesses:
            if access.mmio:
                verb = "WRITES" if access.kind == "write" else (
                    "READS" if access.consumed else "OBSERVES")
                seen(verb, f"mmio:{access.mmio}@{access.address:#05x}", index, pc, src)
            else:
                page = access.address & ~0xFF
                verb = "WRITES" if access.kind == "write" else "READS"
                seen(verb, f"mem:{page:#05x}-{page + 0xFF:#05x}", index, pc, src)
        if trap:
            seen("TRAPS", f"trap:cause={trap[0]}", index, pc, src)
        if mnemonic == "CALL":
            seen("CALLS", place(machine.regs.pc), index, pc, src)
        elif mnemonic == "RET":
            seen("RETURNS", place(machine.regs.pc), index, pc, src)
        elif mnemonic == "ERET":
            seen("RESUMES", place(machine.regs.pc), index, pc, src)
        if step.source and kind == "instruction":
            trace.lines_executed.add(step.source)
        trace.opcodes[mnemonic] += 1
        trace.gprs_modified.update(r for r, _, _ in gpr)
        trace.hregs_modified.update(h for h, _, _, _ in hreg)
        trace.printed += list(printed)
        for access in accesses:
            if access.mmio:
                verb = "write" if access.kind == "write" else (
                    "read" if access.consumed else "observe")
                trace.mmio[(verb, access.mmio, access.address)] += 1
            elif access.kind == "write":
                trace.memory_written.add(access.address)
        if trap:
            trace.traps.append((index, *trap))
        if mnemonic in ("CALL", "RET", "ERET", "JMP"):
            trace.transfers.append((mnemonic, index, pc, machine.regs.pc))
        if mnemonic in CONDITIONAL:
            trace.branches.setdefault(pc, set()).add(machine.regs.pc != pc + 1)
        window.append({a.mmio for a in accesses if a.mmio and a.kind == "read"})
        if len(window) > 200:
            window.pop(0)
    else:
        trace.exit = "step_cap"

    if not trace.exit:
        # Decided from what the MACHINE did, never from how many steps were
        # kept: the first version read `trace.steps`, so a survey that kept
        # none reported all 62 programs as falling off the end of their code,
        # HALT included.
        last = machine.trace[-1].description if machine.trace else ""
        if last.startswith("HCHECK"):
            trace.exit = "hcheck"
            trace.exit_detail = last
        elif machine._halted and last_mnemonic == "HALT":
            trace.exit = "halt"
        elif machine._halted:
            # Stopped by the machine itself, not by a HALT -- HALT_ERR, an
            # HLOAD index naming no entry, an opcode it does not know. Its
            # own words say which. Counting any HALT ever executed, as the
            # first version did, would have called these a clean halt.
            trace.exit = "fault"
            trace.exit_detail = last
        else:
            trace.exit = "end_of_code"
    trace.final_window_mmio = set().union(*window) if window else set()
    if sink is not None:
        sink(render_exit(trace))
    return trace


def trace_program(path: str, max_steps: int = 20_000, keep: int = 400,
                  sink: Callable[[str], None] | None = None) -> Trace:
    """One HASM program, alone, at address 0, with nothing on its wire."""
    from ..core.master_table import MASTER_TABLE
    from ..hisa.machine import HISAMachine

    source = ROOT / path
    words = assemble(source.read_text(encoding="utf-8"), base_dir=source.parent)
    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(words)
    sources = dict(enumerate(source_map(path)))
    return run(machine, sources, path, max_steps, keep, label_map(path), sink)


def trace_loader(program_src: str, max_steps: int = 20_000, keep: int = 2_000,
                 sink: Callable[[str], None] | None = None) -> Trace:
    """loader.hasm with a program on its wire, exactly as freeze_load() runs
    it -- the same assembly, the same mocked wire -- but instrumented, so the
    handover can be seen rather than inferred."""
    from ..core.master_table import MASTER_TABLE
    from ..hisa.machine import HISAMachine
    from .freeze import LOAD_BASE, LOADER_HASM, mock_wire

    loader = LOADER_HASM.relative_to(ROOT).as_posix()
    payload = assemble(program_src, base=LOAD_BASE)
    machine = HISAMachine(MASTER_TABLE)
    machine.code = assemble(LOADER_HASM.read_text(encoding="utf-8"))
    machine.rx_queue = mock_wire(payload)
    sources = dict(enumerate(source_map(loader)))
    for offset in range(len(payload)):
        sources[LOAD_BASE + offset] = ("<payload>", offset + 1)
    return run(machine, sources, loader, max_steps, keep, label_map(loader), sink)


# -- the trace as the owner asked for it: ENTRY, STEP, CHANGE, EXIT ----------


def render_entry(trace: Trace) -> str:
    return f"ENTRY pc={trace.entry:#05x} {trace.program}"


def render_step(step: Step) -> list[str]:
    """One STEP line, what it touched, then its CHANGE lines or NO_CHANGE."""
    where = f"{step.source[0]}:{step.source[1]}" if step.source else "<unmapped>"
    out = [f"STEP {step.index} pc={step.pc:#05x} {where} {step.mnemonic} "
           f"-> pc={step.pc_after:#05x}"]
    for a in step.accesses:
        what = f"mmio {a.mmio}@{a.address:#05x}" if a.mmio else f"mem {a.address:#05x}"
        consumed = " consumed" if a.consumed else ""
        out.append(f"  {a.kind} {what} = {a.value}{consumed}")
    if not step.changed:
        out.append("  NO_CHANGE")
        return out
    out += [f"  CHANGE R{r} {b} -> {a}" for r, b, a in step.gpr]
    out += [f"  CHANGE H{h}[{c}] {b} -> {a}" for h, c, b, a in step.hreg]
    out += [f"  CHANGE flag {n} {b} -> {a}" for n, b, a in step.flags]
    for a in step.accesses:
        if a.kind == "write" and not a.mmio and a.before != a.after:
            out.append(f"  CHANGE mem {a.address:#05x} {a.before} -> {a.after}")
        for address, before, after in a.code:
            was = "absent" if before is None else f"{before:#010x}"
            out.append(f"  CHANGE code[{address:#05x}] {was} -> {after:#010x}")
    out += [f"  CHANGE state {k} {b} -> {a}" for k, b, a in step.state]
    out += [f"  CHANGE print {v}" for v in step.printed]
    if step.trap:
        cause, epc, vector = step.trap
        out.append(f"  CHANGE trap cause={cause} epc={epc:#05x} vector={vector:#05x}")
    return out


def render_exit(trace: Trace) -> str:
    detail = f" {trace.exit_detail}" if trace.exit_detail else ""
    return f"EXIT {trace.exit} after {trace.total_steps} steps{detail}"
