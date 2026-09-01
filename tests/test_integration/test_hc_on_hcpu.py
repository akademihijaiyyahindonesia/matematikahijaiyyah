"""
An HC program, executed by the processor it was written for.

This is the loop the whole toolchain exists to close. One source file goes
three ways — a tree-walking interpreter in Python, the H-ISA machine in
Python, and a Verilog simulation of the HCPU — and all three must return the
same number. Until code generation existed the third path could not be
reached at all: `hc run` walked the AST and the HCPU ran hand-written .hasm,
with nothing in between.

The chain under test:

    .hc → HCC (lex, parse, Ψ-inject, codegen)
        → .hasm
        → rtl/scripts/asm2hex.py
        → .hex
        → tb_parity.v on hcpu_top.v

Requires iverilog. Skipped without it, like the other RTL integration tests,
so the suite still runs on a machine with no Verilog toolchain.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

import pytest

from hijaiyyah.compiler.codegen import generate
from hijaiyyah.compiler.psi import inject
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import HISAMachine
from hijaiyyah.language.evaluator import HCEvaluator
from hijaiyyah.language.lexer import Lexer
from hijaiyyah.language.parser import Parser

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "rtl"

pytestmark = pytest.mark.skipif(
    shutil.which("iverilog") is None and os.environ.get("HOM_REQUIRE_IVERILOG") != "1",
    reason="iverilog is not installed",
)

PROGRAMS = {
    "ba_norm": "let b = 'ب';\nprintln(b.norm2());\n",
    "bism_sum": (
        "let b = 'ب';\nlet s = 'س';\nlet m = 'م';\n"
        "let w = b + s + m;\nw.guard();\nprintln(w.norm2());\n"
    ),
    "distance": "let a = 'ب';\nlet b = 'ت';\nprintln(a.dist2(b));\n",
    "scalar": "let x = 6;\nlet y = 7;\nprintln(x * y);\n",
    "dynamic_load": "let h = load_id(27);\nh.guard();\nprintln(h.norm2());\n",
    # CGET, and the derived quantities built on it.
    "theta": "let h = 'هـ';\nprintln(h.theta());\n",
    "budget_u": "let h = 'و';\nprintln(h.U());\n",
    "residue_rho": "let h = 'س';\nprintln(h.rho());\n",
    "dots": "let h = 'ث';\nprintln(h.Na());\n",
}


@pytest.fixture(scope="module")
def simulation(tmp_path_factory) -> Path:
    """Build tb_parity.v once for the whole module."""
    work = tmp_path_factory.mktemp("hcpu")
    vvp = work / "parity.vvp"
    sources = [str(RTL / "tb" / "tb_parity.v")] + [str(p) for p in sorted(RTL.glob("*.v"))]

    result = subprocess.run(
        ["iverilog", "-g2005", "-I", str(RTL), "-o", str(vvp), *sources],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"iverilog failed:\n{result.stderr}"
    return vvp


def _expected(source: str) -> int:
    printed: List[str] = []
    HCEvaluator(print_func=lambda *a: printed.extend(a)).evaluate(
        Parser(Lexer(source).tokenize()).parse()
    )
    assert len(printed) == 1, "each program prints exactly one value"
    return int(printed[0])


def _compile(source: str) -> str:
    ast = Parser(Lexer(source).tokenize()).parse()
    return generate(ast, inject(ast)).text


def _print_register(asm: str) -> int:
    """Which GPR the program prints. Allocation order is not fixed to R1."""
    matches = re.findall(r"^\s*PRINT\s+R(\d+)", asm, re.M)
    assert len(matches) == 1, f"expected one PRINT, found {len(matches)}"
    return int(matches[0])


def _run_rtl(vvp: Path, hex_path: Path) -> Dict[str, int]:
    result = subprocess.run(
        ["vvp", str(vvp), f"+PROGRAM={hex_path}"],
        capture_output=True, text=True, check=True,
    )
    state: Dict[str, int] = {}
    for match in re.finditer(r"GPR\[(\d+)\]=([0-9a-fA-F]+)", result.stdout):
        state[f"R{int(match.group(1))}"] = int(match.group(2), 16)
    assert "HALTED=1" in result.stdout, "the program did not halt"
    return state


@pytest.mark.parametrize("name", sorted(PROGRAMS), ids=sorted(PROGRAMS))
def test_hc_program_agrees_across_all_three_engines(
    name: str, simulation: Path, tmp_path: Path
) -> None:
    """
    Interpreter, H-ISA machine, and HCPU simulation, on one source file.
    """
    source = PROGRAMS[name]
    expected = _expected(source)

    asm = _compile(source)
    register = _print_register(asm)
    asm_path = tmp_path / f"{name}.hasm"
    asm_path.write_text(asm, encoding="utf-8")

    # Python H-ISA machine.
    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(assemble(asm))
    machine.run()
    assert machine.dump_state()["gpr"][register] == expected, "H-ISA machine disagrees"

    # The RTL path assembles through the script the FPGA flow uses.
    hex_path = tmp_path / f"{name}.hex"
    hex_text = subprocess.run(
        ["python3", str(RTL / "scripts" / "asm2hex.py"), str(asm_path)],
        capture_output=True, text=True, check=True,
    ).stdout
    hex_path.write_text(hex_text, encoding="utf-8")

    state = _run_rtl(simulation, hex_path)
    assert state[f"R{register}"] == expected, (
        f"the HCPU disagrees with the interpreter: "
        f"{state[f'R{register}']} != {expected}\n{asm}"
    )


def test_a_proven_guard_reaches_silicon_as_no_instruction(tmp_path: Path) -> None:
    """
    Ψ's elision is not a Python-side convenience: the HGRD never appears in
    the hex the processor loads.
    """
    asm = _compile(PROGRAMS["bism_sum"])
    words = assemble(asm)
    assert all(word >> 24 != 0x60 for word in words), "HGRD survived into the image"
    assert "dihilangkan" in asm, "the elision must say why, in the listing"
