"""Layer 2, the inventory: every program unit in the repository, parsed.

Layer 1 knows which files touch which. This layer asks what each one DOES,
and the owner's rule from layer 1 still holds: no answer may be an
inference. So a unit is described only by what can be read out of it with
the same parser the rest of the repository already trusts:

    HASM      the assembler's own tokeniser (`_strip`, `_SPLIT_RE`,
              `_MNEMONICS`) -- one definition of what an instruction is,
              not a second one written here
    Python    `ast` -- functions and classes, their arguments, their
              docstrings, the names they call as written
    Verilog   the module header, its ports, the modules it instantiates, its
              always blocks

-- the stated purpose is quoted, never written -------------------------
Every unit carries the first line of its OWN comment or docstring as
`stated_purpose`, attributed as the author's words. What the unit is observed
to do -- the effects in program_summary -- is derived from its instructions,
and the two are kept apart so a reader can see where a claim came from.

-- memory-mapped names come from two real tables ------------------------
0xFF0 and up are named by HISAMachine's REG_* constants, which the
interpreter runs on; 0xFE0 and up by the SD_* defines in rtl/hcpu_pkg.vh,
which the RTL is built from. Neither table is retyped here.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from functools import lru_cache

from ..hisa.assembler import _MNEMONICS, _SPLIT_RE, _strip
from .repository_index import ROOT, index

#: Labels are the same shape the assembler accepts.
LABEL = re.compile(r"^\s*([A-Za-z_][\w]*)\s*:")
INCLUDE = re.compile(r'^\s*\.include\s+"([^"]+)"')
MODULE = re.compile(r"^\s*module\s+(\w+)", re.MULTILINE)
PORT = re.compile(
    r"^\s*(input|output|inout)\s+(?:wire|reg|logic)?\s*(?:signed\s+)?"
    r"(\[[^\]]+\])?\s*(\w+)", re.MULTILINE)
INSTANCE = re.compile(r"^\s*(\w+)\s*(?:#\s*\([^;]*?\))?\s+(u_\w+|\w+_i|i_\w+)\s*\(",
                      re.MULTILINE)
ALWAYS = re.compile(r"always\s*@\s*\(([^)]*)\)")


@dataclass(frozen=True)
class Instruction:
    line: int
    mnemonic: str
    operands: tuple[str, ...]


@dataclass(frozen=True)
class HasmUnit:
    path: str
    stated_purpose: str
    instructions: tuple[Instruction, ...]
    labels: tuple[tuple[str, int], ...]       # (name, source line)
    includes: tuple[str, ...]
    kind: str = "hasm"


@dataclass(frozen=True)
class PythonUnit:
    path: str
    name: str                 # "function" or "Class.method"
    line: int
    stated_purpose: str
    arguments: tuple[str, ...]
    calls: tuple[str, ...]    # names as written; NOT resolved (see graph)
    returns_value: bool
    kind: str = "python"


@dataclass(frozen=True)
class VerilogUnit:
    path: str
    name: str
    stated_purpose: str
    ports: tuple[tuple[str, str, str], ...]   # (direction, width, name)
    instances: tuple[tuple[str, str], ...]    # (module, instance name)
    clocked_blocks: int
    combinational_blocks: int
    kind: str = "verilog"


@dataclass
class Programs:
    hasm: dict[str, HasmUnit] = field(default_factory=dict)
    python: dict[str, PythonUnit] = field(default_factory=dict)
    verilog: dict[str, VerilogUnit] = field(default_factory=dict)


# -- memory-mapped names ---------------------------------------------------


@lru_cache(maxsize=1)
def mmio_names() -> dict[int, str]:
    """Data address -> register name, from the interpreter and the RTL."""
    from ..hisa.machine import HISAMachine
    names = {int(HISAMachine.PERIPH_BASE) + int(getattr(HISAMachine, n)): n[4:]
             for n in dir(HISAMachine) if n.startswith("REG_")}
    pkg = (ROOT / "rtl" / "hcpu_pkg.vh").read_text(encoding="utf-8")
    window = int(HISAMachine.PERIPH_WINDOW)
    for name, value in re.findall(r"`define\s+(SD_\w+)\s+4'h([0-9A-Fa-f])", pkg):
        names[window + int(value, 16)] = name
    return names


# -- HASM ------------------------------------------------------------------


def _first_comment(lines: list[str], marker: str) -> str:
    for line in lines:
        text = line.strip()
        if text.startswith(marker):
            body = text.lstrip(marker).strip(" -")
            if body:
                return body
        elif text:
            break
    return ""


def parse_hasm(path: str) -> HasmUnit:
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    instructions, labels, includes = [], [], []
    for number, line in enumerate(lines, 1):
        inc = INCLUDE.match(line)
        if inc:
            includes.append(inc.group(1))
            continue
        lab = LABEL.match(line.split(";")[0])
        if lab:
            labels.append((lab.group(1), number))
        text = _strip(line)
        if not text:
            continue
        parts = [p for p in _SPLIT_RE.split(text) if p]
        mnemonic = parts[0].upper()
        if mnemonic not in _MNEMONICS:
            raise ValueError(f"{path}:{number}: {mnemonic} is not an opcode")
        instructions.append(Instruction(number, mnemonic, tuple(parts[1:])))
    return HasmUnit(path, _first_comment(lines, ";"), tuple(instructions),
                    tuple(labels), tuple(includes))


# -- Python ----------------------------------------------------------------


def first_sentence(doc: str) -> str:
    """The author's opening sentence, whole. The first LINE is not enough:
    clockwork.run's came back as "Step through `letters` IN ORDER -- order
    genuinely changes the", cut mid-thought by a line break."""
    paragraph = " ".join(doc.strip().split("\n\n")[0].split())
    for end in (". ", ": ", "; "):
        if end in paragraph:
            return paragraph[:paragraph.index(end) + 1]
    return paragraph


def _called_names(node: ast.AST) -> tuple[str, ...]:
    names = []
    for item in ast.walk(node):
        if isinstance(item, ast.Call):
            target = item.func
            if isinstance(target, ast.Name):
                names.append(target.id)
            elif isinstance(target, ast.Attribute):
                names.append(target.attr)
    return tuple(dict.fromkeys(names))


def parse_python(path: str) -> list[PythonUnit]:
    text = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(text)
    units = []

    def unit(node: ast.FunctionDef | ast.AsyncFunctionDef, prefix: str) -> PythonUnit:
        doc = first_sentence(ast.get_docstring(node) or "")
        returns = any(isinstance(n, ast.Return) and n.value is not None
                      for n in ast.walk(node))
        return PythonUnit(path, prefix + node.name, node.lineno, doc,
                          tuple(a.arg for a in node.args.args),
                          _called_names(node), returns)

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            units.append(unit(node, ""))
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    units.append(unit(item, node.name + "."))
    return units


# -- Verilog ---------------------------------------------------------------


def parse_verilog(path: str) -> list[VerilogUnit]:
    text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    purpose = _first_comment(lines, "//")
    units = []
    starts = [m for m in MODULE.finditer(text)]
    for i, match in enumerate(starts):
        body = text[match.start():starts[i + 1].start() if i + 1 < len(starts) else len(text)]
        body = body[:body.find("endmodule") + len("endmodule")] if "endmodule" in body else body
        ports = tuple((d, (w or "").replace(" ", ""), n) for d, w, n in PORT.findall(body))
        instances = tuple((m, n) for m, n in INSTANCE.findall(body)
                          if m not in ("module", "input", "output", "wire", "reg"))
        sens = ALWAYS.findall(body)
        clocked = sum(1 for s in sens if "posedge" in s or "negedge" in s)
        units.append(VerilogUnit(path, match.group(1), purpose, ports, instances,
                                 clocked, len(sens) - clocked))
    return units


@lru_cache(maxsize=1)
def programs() -> Programs:
    found = Programs()
    for node in index().values():
        if node.kind == "hasm":
            found.hasm[node.path] = parse_hasm(node.path)
        elif node.kind == "python" and node.path.startswith("src/"):
            for u in parse_python(node.path):
                found.python[f"{u.path}::{u.name}"] = u
        elif node.kind == "verilog":
            for v in parse_verilog(node.path):
                found.verilog[f"{v.path}::{v.name}"] = v
    return found


def main() -> int:
    found = programs()
    print(f"hasm programs     {len(found.hasm)}")
    print(f"python functions  {len(found.python)}  (src/ only)")
    print(f"verilog modules   {len(found.verilog)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
