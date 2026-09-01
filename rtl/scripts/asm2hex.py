#!/usr/bin/env python3
"""
asm2hex.py — H-ISA Assembly to Hex Converter (v3.0)

Emits the ``$readmemh`` image the HCPU code ROM loads, one 32-bit word per
line with the source line as a trailing comment.

The assembler itself lives in ``hijaiyyah.hisa.assembler`` and is imported
from there. This script used to carry its own copy, and the two drifted: the
if-chain here had no branch for HPACK or HCRC, so ``HPACK R3, H1, R2`` fell
through to a bare opcode and assembled as ``0x50000000`` — every operand
dropped, reading H0 and writing R0 instead of the registers named. Nothing
caught it because no ``.hasm`` file in the tree used either instruction, and
the RTL testbench builds those words directly in Verilog.

One assembler, one operand table. The FPGA flow runs this script standalone,
so the package is located relative to this file rather than assumed installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hijaiyyah.hisa.assembler import (  # noqa: E402
    AssemblyError,
    assemble_line,
    collect_labels,
)


def main() -> None:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    if len(args) < 1:
        print("Usage: asm2hex.py input.hasm [--verbose] > program.hex", file=sys.stderr)
        sys.exit(1)

    lines = Path(args[0]).read_text(encoding="utf-8").splitlines()

    try:
        labels = collect_labels(lines)
    except AssemblyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if verbose:
        print(f"; Labels: {labels}", file=sys.stderr)

    address = 0
    for number, line in enumerate(lines, start=1):
        try:
            word = assemble_line(line, labels, address)
        except AssemblyError as exc:
            print(f"error: line {number}: {exc}", file=sys.stderr)
            sys.exit(1)
        if word is None:
            continue
        comment = line.split(";")[0].strip()
        print(f"{word:08X}  // addr {address:4d}: {comment}")
        address += 1

    if verbose:
        print(f"; Assembled {address} instructions", file=sys.stderr)


if __name__ == "__main__":
    main()
