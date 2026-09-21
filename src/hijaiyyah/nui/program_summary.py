"""Layer 2, the answer: what a program unit does, derived from its body.

The owner's example asks "Apa fungsi loader.hasm?" and gives the answer he
expects -- reads the UART stream, writes instruction memory, jumps into the
loaded program. The discipline here is that NUI may not WRITE that answer; it
has to read it out of the instructions. So every effect below is produced by
a rule over parsed code and carries the line that produced it:

    HASM      LOAD / STORE whose offset names a memory-mapped register, PRINT
              and EMITS, HALT, ERET, SYSCALL, CALL and JMP targets, the codex
              opcodes, and .include
    Python    the I/O a function performs (files, subprocesses, the serial
              port, the console), what it returns, and the names it calls
    Verilog   its ports, its clocked and combinational blocks, and the
              modules it instantiates

Beside the derived effects sits the unit's own first comment or docstring,
quoted as `stated`. The two are never merged: one is the author's claim, the
other is what the code shows, and a reader must be able to tell them apart.

-- what a derived effect cannot say --------------------------------------
`LOAD R1, R5, 0xFF0` reads the UART only if R5 holds zero when it runs. That
is a question about EXECUTION, and it is layer 3's. So a memory-mapped effect
here says the instruction NAMES the register at that offset -- which is
exactly what the text shows -- and not that it was reached.
"""
from __future__ import annotations

from dataclasses import dataclass

from .program_index import (
    HasmUnit,
    PythonUnit,
    VerilogUnit,
    mmio_names,
    programs,
)

CODEX_OPS = {"HLOAD", "HCADD", "CGET", "CSET", "CU", "CRHO", "CMOD4", "CEQ",
             "CMOV", "CZERO", "HNRM2", "HDIST"}
IO_CALLS = {
    "open": "opens a file", "read_text": "reads a file", "write_text": "writes a file",
    "read_bytes": "reads a file", "write_bytes": "writes a file",
    "run": "runs a subprocess", "Popen": "starts a subprocess",
    "Serial": "opens a serial port", "print": "prints to the console",
}


@dataclass(frozen=True)
class Effect:
    what: str
    line: int
    times: int = 1


@dataclass(frozen=True)
class Summary:
    target: str
    kind: str
    stated: str
    effects: tuple[Effect, ...]
    interface: tuple[str, ...]

    def render(self) -> str:
        out = [f"{self.target}  [{self.kind}]"]
        if self.stated:
            out.append(f'  stated:   "{self.stated}"')
        if self.interface:
            out.append("  interface:")
            out += [f"    {item}" for item in self.interface]
        out.append("  observed:" if self.effects else "  observed: nothing derivable")
        for e in self.effects:
            more = f" (x{e.times})" if e.times > 1 else ""
            out.append(f"    {e.what}  -- line {e.line}{more}")
        return "\n".join(out)


def _collect(pairs: list[tuple[str, int]]) -> tuple[Effect, ...]:
    """One effect per kind of thing, first line kept, the rest counted."""
    first: dict[str, Effect] = {}
    for what, line in pairs:
        if what in first:
            kept = first[what]
            first[what] = Effect(kept.what, kept.line, kept.times + 1)
        else:
            first[what] = Effect(what, line)
    return tuple(first.values())


def _address(operand: str) -> int | None:
    try:
        return int(operand, 0)
    except ValueError:
        return None


def summarize_hasm(unit: HasmUnit) -> Summary:
    names = mmio_names()
    pairs: list[tuple[str, int]] = []
    for ins in unit.instructions:
        m, ops = ins.mnemonic, ins.operands
        if m in ("LOAD", "STORE") and ops:
            addr = _address(ops[-1])
            if addr is not None and addr in names:
                verb = "reads" if m == "LOAD" else "writes"
                pairs.append((f"{verb} {names[addr]} ({addr:#05x})", ins.line))
        elif m in ("PRINT", "EMITS"):
            pairs.append(("prints to the UART", ins.line))
        elif m == "HALT":
            pairs.append(("halts", ins.line))
        elif m == "ERET":
            pairs.append(("returns from a trap (ERET)", ins.line))
        elif m == "SYSCALL":
            pairs.append((f"makes system call {ops[0] if ops else '?'}", ins.line))
        elif m == "CALL" and ops:
            pairs.append((f"calls {ops[0]}", ins.line))
        elif m == "JMP" and ops:
            pairs.append((f"jumps to {ops[0]}", ins.line))
        elif m in CODEX_OPS:
            pairs.append(("uses the codex unit (" + m + ")", ins.line))
    interface = [f"{len(unit.instructions)} instructions, {len(unit.labels)} labels"]
    interface += [f'includes "{name}"' for name in unit.includes]
    return Summary(unit.path, "hasm", unit.stated_purpose, _collect(pairs),
                   tuple(interface))


def summarize_python(unit: PythonUnit) -> Summary:
    pairs = [(IO_CALLS[c], unit.line) for c in unit.calls if c in IO_CALLS]
    if unit.returns_value:
        pairs.append(("returns a value", unit.line))
    interface = [f"arguments: {', '.join(unit.arguments) or '(none)'}"]
    others = [c for c in unit.calls if c not in IO_CALLS]
    if others:
        interface.append("calls (as written, not resolved): " + ", ".join(others[:12])
                         + (" ..." if len(others) > 12 else ""))
    return Summary(f"{unit.path}::{unit.name}", "python", unit.stated_purpose,
                   _collect(pairs), tuple(interface))


def summarize_verilog(unit: VerilogUnit) -> Summary:
    inputs = [p for p in unit.ports if p[0] == "input"]
    outputs = [p for p in unit.ports if p[0] == "output"]
    interface = [f"{len(inputs)} inputs, {len(outputs)} outputs, "
                 f"{unit.clocked_blocks} clocked block(s), "
                 f"{unit.combinational_blocks} combinational block(s)"]
    interface += [f"instantiates {mod} as {inst}" for mod, inst in unit.instances]
    return Summary(f"{unit.path}::{unit.name}", "verilog", unit.stated_purpose, (),
                   tuple(interface))


def explain(target: str) -> Summary:
    """A HASM path, or `path::function`, or `path::module`."""
    found = programs()
    if target in found.hasm:
        return summarize_hasm(found.hasm[target])
    if target in found.python:
        return summarize_python(found.python[target])
    if target in found.verilog:
        return summarize_verilog(found.verilog[target])
    raise KeyError(f"{target} is not a program unit")


def main(argv: list[str] | None = None) -> int:
    import sys
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: program_summary <hasm path | path::function | path::module>")
        return 1
    try:
        print(explain(args[0]).render())
    except KeyError as missing:
        print(missing)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
