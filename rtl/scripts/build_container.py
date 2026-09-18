#!/usr/bin/env python3
"""build_container.py -- a .hasm becomes a program container for the card.

    build_container.py PROG.hasm LOAD_ADDR [--entry LABEL] > image.hex

The shape is the owner's, 18 September 2026, seven words of header:

    0  MAGIC       0x48504731  "HPG1"
    1  VERSION     1
    2  WORDS       how many program words follow the relocation table
    3  LOAD_ADDR   where the loader writes them
    4  ENTRY       where execution starts -- not necessarily LOAD_ADDR
    5  RELOC_CNT   how many entries the relocation table has
    6  CRC         sum of the PROGRAM words, mod 2^32; the header is not in it
       RELOC       RELOC_CNT words, each an index into the program words
       PROGRAM     WORDS words, ASSEMBLED AT BASE 0

Program words are stored at base 0 and the loader adds LOAD_ADDR to every word
the relocation table names. That is what makes LOAD_ADDR mean anything: an
image stored already-relocated would only ever load at one address, and the
owner's reason for having a relocation table at all is that absolute labels
broke once when the load base moved (`rtl/scripts/send_program.py`, five
programs returning zero bytes from the board).

-- the relocation table is MEASURED, not declared --------------------------
Nothing in the .hasm says which words hold an address. This assembles the
program twice, at two different bases, and takes the words that MOVED. Each
one must move by exactly the difference between the bases; a word that moves
by anything else means the assembler is doing something this tool does not
understand, and that is an error rather than a guess.

-- the 12-bit immediate, and why its guard never fires alone ----------------
`IMM_W` is 12 (rtl/hcpu_pkg.vh), field [11:0], and relocation is a 32-bit add
of LOAD_ADDR to the whole word, so an address that does not fit in 12 bits
carries into [15:12] -- the S2 register field -- and the instruction quietly
becomes another instruction. Measured, that cannot happen while the program
fits: an immediate reaches 4,095 and instruction memory is 4,096 words, and
every relocatable word names a label inside its own program, so the depth
check below refuses first every time. The immediate check stays as a belt,
one comparison, and it is what would speak first if those two numbers ever
moved apart. tests/test_hisa/test_container.py holds both halves.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hijaiyyah.hisa.assembler import (  # noqa: E402
    assemble,
    collect_labels,
    expand_includes,
)

MAGIC = 0x48504731          # "HPG1"
VERSION = 1
HEADER_WORDS = 7
CODE_DEPTH = 4096
IMM_MASK = 0xFFF            # IMM_W = 12, rtl/hcpu_pkg.vh
PROBE_DELTA = 0x100         # the second base used to find relocations
RELOC_MAX = 128             # the loader's buffer, 0x300-0x37F, owner's decision


def relocations(source: str, base_dir: Path) -> tuple[list[int], list[int]]:
    """The program at base 0, and the indices of the words that hold addresses."""
    at_zero = assemble(source, base_dir=base_dir, base=0)
    at_delta = assemble(source, base_dir=base_dir, base=PROBE_DELTA)
    if len(at_zero) != len(at_delta):
        raise ValueError("the program changes length with its base")
    moved: list[int] = []
    for i, (a, b) in enumerate(zip(at_zero, at_delta)):
        if a == b:
            continue
        if b - a != PROBE_DELTA:
            raise ValueError(
                f"word {i} moves by {b - a:#x} when the base moves by "
                f"{PROBE_DELTA:#x}: this tool only understands whole-word "
                f"addition")
        moved.append(i)
    return at_zero, moved


def build(source: str, base_dir: Path, load_addr: int,
          entry_label: str | None = None) -> list[int]:
    program, moved = relocations(source, base_dir)

    if load_addr < 0 or load_addr + len(program) > CODE_DEPTH:
        raise ValueError(
            f"{len(program)} words at {load_addr:#x} run past the "
            f"{CODE_DEPTH}-word instruction memory")

    for i in moved:
        if (program[i] & IMM_MASK) + load_addr > IMM_MASK:
            raise ValueError(
                f"word {i} ({program[i]:#010x}) holds address "
                f"{program[i] & IMM_MASK:#x}; at {load_addr:#x} it would carry "
                f"out of the 12-bit immediate into the S2 register field")

    if len(moved) > RELOC_MAX:
        raise ValueError(
            f"{len(moved)} relocations will not fit: the loader copies the "
            f"table into {RELOC_MAX} words at 0x300-0x37F, and refusing here "
            f"is cheaper than a board that refuses after reading the card")

    entry = load_addr
    if entry_label is not None:
        labels = collect_labels(expand_includes(source.splitlines(), base_dir))
        if entry_label not in labels:
            raise ValueError(f"no label {entry_label!r} in this program")
        entry = load_addr + labels[entry_label]

    checksum = sum(program) & 0xFFFFFFFF
    return ([MAGIC, VERSION, len(program), load_addr, entry, len(moved),
             checksum] + moved + program)


def relocate(container: list[int]) -> tuple[int, list[int]]:
    """What the loader does, in Python: the words as they land in IMEM.

    Here so a test can hold the board's arithmetic against the assembler's own
    output at the same base, rather than against a second transcription of it.
    """
    words, load_addr, reloc_cnt = container[2], container[3], container[5]
    table = container[HEADER_WORDS:HEADER_WORDS + reloc_cnt]
    program = container[HEADER_WORDS + reloc_cnt:HEADER_WORDS + reloc_cnt + words]
    image = list(program)
    for i in table:
        image[i] = (image[i] + load_addr) & 0xFFFFFFFF
    return load_addr, image


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("program", type=Path)
    ap.add_argument("load_addr", type=lambda s: int(s, 0))
    ap.add_argument("--entry", help="label to start at; default is LOAD_ADDR")
    ap.add_argument("--image", action="store_true",
                    help="print the RELOCATED words instead of the container: "
                         "what instruction memory must hold after a load")
    args = ap.parse_args(argv)

    container = build(args.program.read_text(encoding="utf-8"),
                      args.program.parent, args.load_addr, args.entry)
    if args.image:
        container = relocate(container)[1]
    for word in container:
        print(f"{word & 0xFFFFFFFF:08X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
