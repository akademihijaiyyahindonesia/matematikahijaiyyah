"""Layer 4's board column, prepared: what the board must print for each program
in the parity corpus, delivered exactly as the board receives it.

The board is reached one way only -- loader.hasm in the bitstream, the program
over the wire to address 64, and what comes back on the UART until the
wrapper reports CYCLES= at halt. So the reference here is not the base-0 run
layer 4 compares with the RTL. It is loader.hasm with the payload on its
wire, in the interpreter: the same loader, the same bytes, the same address,
and the registers the loader leaves behind.

-- seeing registers through a wire ---------------------------------------------
The board shows only what it prints. A program that prints nothing has the
HALT that actually stopped it -- found by running it, not by reading it --
replaced by a jump to an observation epilogue appended after its last word,
which prints the state the program wrote:

    FRD    Rs            FLAGS first, before the epilogue's own ALU moves it
    PRINT  Rs
    SHRI   Rs, Rr, 24    every GPR the program changed, one byte at a time --
    ANDI   Rs, Rs, 255   a byte never reaches OFF-PRINT-SILICON, which starts
    PRINT  Rs            above 2^22
    ...
    CGET   Rs, Hh, c     every component of every H-register it changed
    PRINT  Rs
    HALT

Rs is a register the program never changed, so nothing is overwritten before
it is printed. Only the stopping HALT is replaced: syscall.hasm's own HALT
runs in user mode ON PURPOSE, to fault, and rewriting every HALT would have
changed what the program does. The HALT that stops a program ran in
supervisor mode, so the epilogue does too. And every epilogue is checked
before it is trusted: in the interpreter, what it prints must be exactly the
state at the jump into it.

The reference runs with the interpreter's periodic HCHECK off. Layer 4
measured it as the interpreter's alone -- the RTL runs on where it stops --
and under the loader its clock is shifted by the loader's own steps, so it
stopped codex_negative_residue and cset_twice_into_the_same_register at
points the board never stops at.

-- three experiments, not one -----------------------------------------------------
The owner, 22 September 2026: PRINT in silicon and the word behind a stop run
as experiments of their own, not inside this corpus, so neither fault can be
read as the other's or as a parity result. The corpus here is layer 4's
parity programs and the repository's HASM programs; the PRINT ladder and the
stop probes live in board_probes.py. programs_for() names all three.

-- what is not sent --------------------------------------------------------------
A program that touches the SD window is never sent: no other engine here has a
card to compare with -- and until the 72-hour run ends the card is the
burn-in's. Nor is one that does not halt, or one that prints nothing and has
no epilogue. Each exclusion carries its reason.

-- expected answers are written down first ----------------------------------------
Before the board is asked, what it should print is frozen in
NUI/board_expected.json: per program the interpreter's text under the loader,
the simulated RTL's text for the same payload at address 64 behind NOPs, the
memory-mapped registers it reads, the opcodes it executes, and a hash of the
payload. The runner refuses a payload whose hash is not the frozen one, so a
board answer is always held against an expectation recorded before it.

-- reading the answer ---------------------------------------------------------------
classify() puts each program in one of layer 4's three states against the
frozen expectation: PARITY, MISMATCH -- with the first line that differs and
whether the board matched the RTL instead -- or UNKNOWN, with why: not sent,
not in the record, or a program that reads the free-running counter, whose
interpreter counts instructions where silicon counts clocks.
opcode_column() rolls that up per opcode: the hardware column layer 4 waits
for. The wire cannot say which instruction caused a difference, so an opcode
seen in both an agreeing and a differing program stays UNKNOWN, with both
lists.

rtl/scripts/parity_board.py is the half that talks to the board, and writes
the record this module reads. It does not run while a burn-in holds the board.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..hisa.assembler import assemble
from ..hisa.machine import HISAMachine
from ..hisa.opcodes import OpCode
from ..hisa.parity_programs import PROGRAMS
from .execution_trace import source_map
from .freeze import LOAD_BASE, LOADER_HASM, mock_wire
from .parity_model import (
    InterpreterRun,
    Program,
    _printed_text,
    compile_rtl,
    cycle_budget,
    run_interpreter,
    run_rtl,
)
from .program_index import programs
from .repository_index import ROOT

RECORDS = ROOT / "cosmictera-build" / "parity-board"
EXPECTED = ROOT / "NUI" / "board_expected.json"
EXPERIMENTS = ("parity", "print", "stop")
SD_WINDOW = range(HISAMachine.PERIPH_WINDOW, HISAMachine.PERIPH_WINDOW + 16)
#: A payload is at most CODE_DEPTH - LOAD_BASE words, and the loader spends a
#: few dozen steps on each; this leaves room for the program after it.
STEPS_PER_WORD = 60
MIN_STEPS = 20_000


@dataclass
class BoardProgram:
    name: str
    payload: list[int]
    expected: str = ""                      # what the wire should carry
    epilogue: bool = False
    excluded: str = ""                      # why it is not sent, if it is not
    reads: set[str] = field(default_factory=set)
    #: The interpreter run of exactly this payload under the loader, kept so
    #: the corpus does not run it twice.
    run: InterpreterRun | None = field(default=None, repr=False, compare=False)


def loader_program(name: str, payload: list[int]) -> Program:
    """loader.hasm at 0 with the payload's words mapped at LOAD_BASE."""
    loader = LOADER_HASM.relative_to(ROOT).as_posix()
    words = assemble(LOADER_HASM.read_text(encoding="utf-8"))
    sources = dict(enumerate(source_map(loader)))
    for offset in range(len(payload)):
        sources[LOAD_BASE + offset] = (f"<payload:{name}>", offset + 1)
    return Program(f"{name}@loader", words, sources, {})


def run_under_loader(name: str, payload: list[int],
                     steps: int | None = None) -> InterpreterRun:
    steps = steps or max(MIN_STEPS, STEPS_PER_WORD * len(payload) + MIN_STEPS)
    return run_interpreter(loader_program(name, payload), steps, wire=mock_wire(payload),
                           hcheck_interval=0)


def _payload_steps(run: InterpreterRun) -> list[Any]:
    return [s for s in run.steps if s.pc >= LOAD_BASE]


def epilogue(gprs: list[int], hregs: list[int], scratch: int) -> str:
    """HASM that prints FLAGS, then each GPR byte by byte, then each H-register
    component, then halts. `scratch` is the one register it writes."""
    s = f"R{scratch}"
    lines = [f"FRD   {s}", f"PRINT {s}"]
    for r in gprs:
        for shift in (24, 16, 8):
            lines += [f"SHRI  {s}, R{r}, {shift}", f"ANDI  {s}, {s}, 255", f"PRINT {s}"]
        lines += [f"ANDI  {s}, R{r}, 255", f"PRINT {s}"]
    for h in hregs:
        for c in range(18):
            lines += [f"CGET  {s}, H{h}, {c}", f"PRINT {s}"]
    lines.append("HALT")
    return "".join(f"        {line}\n" for line in lines)


def _reads_and_writes(run: InterpreterRun) -> tuple[set[str], bool, bool]:
    reads, sd, imem = set(), False, False
    for s in _payload_steps(run):
        for a in s.accesses:
            if a.mmio and a.kind == "read":
                reads.add(a.mmio)
            if a.address in SD_WINDOW:
                sd = True
            if a.mmio == "IMEM_DATA" and a.kind == "write":
                imem = True
    return reads, sd, imem


def _dump(text: str, gprs: list[int], hregs: list[int]) -> dict[str, Any] | None:
    """The epilogue's output read back as state, or None if it is not one."""
    lines = [x for x in text.split("\n") if x]
    need = 1 + 4 * len(gprs) + 18 * len(hregs)
    if len(lines) < need or not all(x.isdigit() for x in lines[-need:]):
        return None
    values = [int(x) for x in lines[-need:]]
    gpr = {r: (values[1 + 4 * i] << 24) | (values[2 + 4 * i] << 16)
           | (values[3 + 4 * i] << 8) | values[4 + 4 * i] for i, r in enumerate(gprs)}
    base = 1 + 4 * len(gprs)
    hreg = {h: values[base + 18 * i: base + 18 * (i + 1)] for i, h in enumerate(hregs)}
    return {"flags": values[0], "gpr": gpr, "hreg": hreg}


def _instrument(name: str, words: list[int]) -> BoardProgram:
    """Replace the HALT that stopped the run with a jump to an epilogue
    appended after the last word, then prove the epilogue prints the state."""
    bare = run_under_loader(name, words)
    if bare.exit != "halt":
        return BoardProgram(name, words, excluded=f"does not halt under the loader "
                                                  f"({bare.exit} after {len(bare.steps)} steps)")
    stop = bare.steps[-1].pc - LOAD_BASE
    payload_steps = _payload_steps(bare)
    gprs = sorted({r for s in payload_steps for r, _, _ in s.gpr})
    hregs = sorted({h for s in payload_steps for h, _, _, _ in s.hreg})
    free = [r for r in range(15, -1, -1) if r not in gprs]
    if not free:
        return BoardProgram(name, words, excluded="changes all sixteen registers: "
                                                  "no scratch for the epilogue")
    jump = (int(OpCode.JMP) << 24) | (LOAD_BASE + len(words))
    payload = [jump if i == stop else w for i, w in enumerate(words)]
    payload += assemble(epilogue(gprs, hregs, free[0]))
    run = run_under_loader(name, payload)
    got = _dump(_printed_text(run.events["TX"]), gprs, hregs)
    # What the epilogue must print is the state at the jump into it, in the
    # SAME run -- not the final state of the run without it. The two differ
    # for a program that reads the free-running counter: the longer payload
    # takes the loader longer to receive, and timer_poll's registers came back
    # 2,021 cycles larger. The state at the jump is read by rerunning to it.
    # An instruction step: a trap taken while pc sat on that word is recorded
    # at the same pc (mem_protect.hasm takes one there) and is not the jump.
    jump_step = next((st.index for st in run.steps
                      if st.pc == LOAD_BASE + stop and st.kind == "instruction"), None)
    if jump_step is None:
        return BoardProgram(name, payload, epilogue=True,
                            excluded="the run never reaches the replaced HALT")
    at = run_under_loader(name, payload, steps=jump_step + 1).final
    want = {"flags": at["flags"], "gpr": {r: at["gpr"][r] for r in gprs},
            "hreg": {h: at["hreg"][h] for h in hregs}}
    if got != want:
        return BoardProgram(name, payload, epilogue=True,
                            excluded="the epilogue does not print the final state "
                                     "it replaced -- not trusted")
    return BoardProgram(name, payload, epilogue=True, run=run)


def corpus() -> list[BoardProgram]:
    out = [_instrument(f"parity:{name}", list(words))
           for name, words in sorted(PROGRAMS.items())]
    for path in sorted(programs().hasm):
        source = ROOT / path
        words = assemble(source.read_text(encoding="utf-8"), base_dir=source.parent,
                         base=LOAD_BASE)
        bare = run_under_loader(path, words)
        prints = bool(bare.events["TX"])
        out.append(BoardProgram(path, words, run=bare) if prints or bare.exit != "halt"
                   else _instrument(path, words))
    for bp in out:
        if bp.excluded:
            continue
        run = bp.run or run_under_loader(bp.name, bp.payload)
        reads, sd, imem = _reads_and_writes(run)
        bp.reads = reads
        text = _printed_text(run.events["TX"])
        if sd:
            bp.excluded = ("touches the SD window: no other engine here has a card to "
                           "compare with, and until the burn-in ends the card is its")
        elif imem:
            bp.excluded = "writes instruction memory itself"
        elif run.exit != "halt":
            bp.excluded = (f"does not halt under the loader ({run.exit} after "
                           f"{len(run.steps)} steps)")
        elif not text:
            bp.excluded = "prints nothing, and has no epilogue"
        else:
            bp.expected = text
    return out


def programs_for(experiment: str) -> list[BoardProgram]:
    """The programs one experiment sends: the parity corpus, the PRINT ladder,
    or the stop probes."""
    if experiment == "parity":
        return corpus()
    from . import board_probes
    if experiment == "print":
        return board_probes.print_programs()
    if experiment == "stop":
        return board_probes.stop_programs()
    raise ValueError(f"an experiment is one of {', '.join(EXPERIMENTS)}")


# -- the expected answers, frozen before the board is asked --------------------------


def payload_sha256(payload: list[int]) -> str:
    return hashlib.sha256(b"".join(w.to_bytes(4, "big") for w in payload)).hexdigest()


def _opcodes(run: InterpreterRun) -> list[str]:
    return sorted({s.mnemonic for s in _payload_steps(run) if s.kind == "instruction"})


def runs_at_64(progs: list[BoardProgram], jobs: int = 8) -> dict[str, tuple[Any, Any]]:
    """Each payload at address 64 behind NOPs, on the interpreter and on the
    simulated RTL. The RTL harness has no UART receiver, so the loader cannot
    deliver the payload there; the two engines are compared in the one
    context both can run, and neither is compared with a loader run."""
    nop = int(OpCode.NOP) << 24
    work = Path(tempfile.mkdtemp())
    try:
        sim = compile_rtl(work)

        def one(b: BoardProgram) -> tuple[str, Any]:
            words = [nop] * LOAD_BASE + b.payload
            prog = Program(b.name, words, {}, {})
            i = run_interpreter(prog, max_steps=len(words) * 40 + 20_000, hcheck_interval=0)
            return b.name, (i, run_rtl(sim, words, cycle_budget(i) + 2_000, work))

        with ThreadPoolExecutor(max_workers=jobs) as pool:
            return dict(pool.map(one, progs))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def expectations(experiment: str) -> dict[str, Any]:
    """What the board should print for each program of one experiment.

    `interpreter` is the board's expectation: the interpreter running the
    loader with the payload on its wire, as the board does. `interpreter_at_64`
    and `rtl_at_64` are both engines on the payload at 64 behind NOPs -- the
    context the RTL can run -- and they are compared only with each other: the
    loader leaves FLAGS and registers behind that a start from zero does not,
    and an epilogue prints them."""
    progs = programs_for(experiment)
    at_64 = runs_at_64([b for b in progs if not b.excluded])
    out: dict[str, Any] = {}
    for b in progs:
        if b.excluded:
            out[b.name] = {"sent": False, "excluded": b.excluded}
            continue
        run = b.run or run_under_loader(b.name, b.payload)
        interp_64, rtl_64 = at_64[b.name]
        entry = {"sent": True, "words": len(b.payload),
                 "payload_sha256": payload_sha256(b.payload),
                 "interpreter": b.expected,
                 "interpreter_at_64": _printed_text(interp_64.events["TX"]),
                 "rtl_at_64": _printed_text(rtl_64.events["TX"]),
                 "reads": sorted(_reads_and_writes(run)[0]), "opcodes": _opcodes(run)}
        if experiment == "stop":
            from .board_probes import after_stop
            entry["after_stop"] = after_stop(b.name, interp_64, rtl_64)
        out[b.name] = entry
    return {"programs": out}


def write_expected() -> None:
    data = {"generated_by": "src/hijaiyyah/nui/board_parity.py",
            "interpreter": "src/hijaiyyah/hisa/machine.py running rtl/programs/loader.hasm "
                           "with the payload on its wire, periodic HCHECK off -- what the "
                           "board should print",
            "interpreter_at_64": "the same interpreter, the payload at address 64 behind "
                                 "NOPs, HCHECK off",
            "rtl_at_64": "rtl/*.v under Icarus via rtl/tb/tb_parity.v, the same payload at "
                         "address 64 behind NOPs",
            **{e: expectations(e) for e in EXPERIMENTS}}
    EXPECTED.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def load_expected() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(EXPECTED.read_text(encoding="utf-8"))
    return data


# -- reading what the board sent back ---------------------------------------------


def parse_capture(raw: bytes) -> dict[str, Any]:
    """The text before CYCLES=, the cycle count after it, and what was dropped.

    Same rules as rtl/scripts/jamrah_board.py's parse: a byte outside printable
    ASCII other than a newline is dropped and COUNTED, never silently lost."""
    head, _, tail = raw.partition(b"CYCLES=")
    # The wrapper's report is "\r\nCYCLES=" + 8 hex digits + "\r\n"
    # (rtl/fpga/gowin/hcpu_gowin_top.v): the two bytes before CYCLES= are the
    # report's, not the program's.
    if tail and head.endswith(b"\r\n"):
        head = head[:-2]
    kept = bytes(c for c in head if c == 10 or 32 <= c < 127)
    cycles = re.match(rb"\s*([0-9A-Fa-f]+)", tail)
    return {"text": kept.decode("ascii").replace("\r", ""),
            "dropped": len(head) - len(kept),
            "halted": bool(tail) or raw.endswith(b"CYCLES="),
            "cycles": int(cycles.group(1), 16) if cycles else None}


def latest_record(experiment: str = "parity") -> dict[str, Any] | None:
    files = (sorted(p for p in RECORDS.glob(f"*-{experiment}.json"))
             if RECORDS.is_dir() else [])
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None


def compare_text(expected: str, board: str) -> dict[str, Any]:
    """PARITY, or the first printed line that differs and both lines."""
    want, got = expected.split("\n"), board.split("\n")
    for i, (a, b) in enumerate(zip(want, got, strict=False)):
        if a != b:
            return {"status": "MISMATCH", "line": i, "expected": a, "board": b}
    if len(want) != len(got):
        return {"status": "MISMATCH", "line": min(len(want), len(got)),
                "expected": None if len(want) <= len(got) else want[len(got)],
                "board": None if len(got) <= len(want) else got[len(want)]}
    return {"status": "PARITY"}


def classify(record: dict[str, Any], expected: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Each program of one experiment: PARITY, MISMATCH or UNKNOWN, against
    the frozen expectation, never against a rerun made after the board spoke."""
    out: dict[str, dict[str, Any]] = {}
    for name, exp in expected["programs"].items():
        got = record["programs"].get(name)
        if not exp["sent"]:
            out[name] = {"status": "UNKNOWN", "reason": f"not sent: {exp['excluded']}"}
        elif got is None or "text" not in got:
            out[name] = {"status": "UNKNOWN", "reason": "not in this record"}
        elif got.get("payload_sha256") != exp["payload_sha256"]:
            out[name] = {"status": "UNKNOWN",
                         "reason": "the payload sent is not the one the expectation froze"}
        elif not got["halted"]:
            out[name] = {"status": "MISMATCH", "kind": "no halt report",
                         "board": got["text"], "timed_out": got.get("timed_out")}
        elif "COUNTER" in exp["reads"] and exp["rtl_at_64"] != exp["interpreter_at_64"]:
            out[name] = {"status": "UNKNOWN", "board": got["text"],
                         "reason": "reads the free-running counter: the interpreter counts "
                                   "instructions, silicon counts clocks"}
        else:
            # Whether the board matched the RTL instead can only be asked where
            # the loader's context changes nothing the program prints.
            context_free = exp["interpreter"] == exp["interpreter_at_64"]
            out[name] = {**compare_text(exp["interpreter"], got["text"]),
                         "board_equals_rtl": (got["text"] == exp["rtl_at_64"]
                                              if context_free else None),
                         "dropped": got["dropped"]}
    return out


def opcode_column(classified: dict[str, dict[str, Any]],
                  expected: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Layer 4's hardware column, per opcode, from one board run."""
    seen: dict[str, dict[str, list[str]]] = {}
    for name, c in classified.items():
        for op in expected["programs"][name].get("opcodes", []):
            seen.setdefault(op, {"PARITY": [], "MISMATCH": [], "UNKNOWN": []})[
                c["status"]].append(name)
    out: dict[str, dict[str, Any]] = {}
    for op in [o.name for o in OpCode]:
        s = seen.get(op, {"PARITY": [], "MISMATCH": [], "UNKNOWN": []})
        if s["PARITY"] and not s["MISMATCH"]:
            status, reason = "PARITY", ""
        elif s["MISMATCH"] and not s["PARITY"]:
            status, reason = "MISMATCH", "every board run that executed it differed"
        elif s["MISMATCH"]:
            status, reason = "UNKNOWN", ("executed in agreeing and differing runs: the "
                                         "wire alone cannot say which instruction differed")
        elif s["UNKNOWN"]:
            status, reason = "UNKNOWN", "executed only in runs the board could not decide"
        else:
            status, reason = "UNKNOWN", "no program sent executes it"
        out[op] = {"board": status, "reason": reason, "agreeing": s["PARITY"],
                   "differing": s["MISMATCH"], "undecided": s["UNKNOWN"]}
    return out


def report(record: dict[str, Any], expected: dict[str, Any] | None = None) -> dict[str, Any]:
    """Everything one board record says, against what was frozen before it."""
    experiment = record["experiment"]
    section = (expected or load_expected())[experiment]
    classified = classify(record, section)
    counts = {s: sum(1 for c in classified.values() if c["status"] == s)
              for s in ("PARITY", "MISMATCH", "UNKNOWN")}
    out: dict[str, Any] = {"experiment": experiment, "record": record.get("date"),
                           "commit": record.get("commit"), "counts": counts,
                           "programs": classified}
    if experiment == "parity":
        out["opcodes"] = opcode_column(classified, section)
    if experiment == "print":
        from .board_probes import PRINT_NAME, print_table
        got = record["programs"].get(PRINT_NAME, {})
        out["ladder"] = print_table(section, got.get("text"))
    if experiment == "stop":
        from .board_probes import stop_table
        out["probes"] = stop_table(section, record)
    return out


def plan(experiment: str = "parity") -> list[dict[str, Any]]:
    """What a board run would send, and why the rest is not sent."""
    return [{"name": bp.name, "words": len(bp.payload), "epilogue": bp.epilogue,
             "expected_bytes": len(bp.expected), "excluded": bp.excluded}
            for bp in programs_for(experiment)]


def main() -> int:
    import sys
    if sys.argv[1:] == ["--write-expected"]:
        write_expected()
        print(f"expected: {EXPECTED.relative_to(ROOT)}")
        return 0
    for experiment in EXPERIMENTS:
        rows = plan(experiment)
        sent = [r for r in rows if not r["excluded"]]
        print(f"{experiment}: {len(sent)} of {len(rows)} programs would be sent")
        for r in rows:
            mark = "send" if not r["excluded"] else "skip"
            print(f"  {mark} {r['name']:<50} {r['words']:>5} words  "
                  f"{r['expected_bytes']:>5} bytes back  {r['excluded']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
