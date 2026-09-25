#!/usr/bin/env python3
"""build_container.py -- a .hasm becomes a program container for the card.

    build_container.py PROG.hasm LOAD_ADDR [--entry LABEL] > image.hex

The shape is the owner's, 18 September 2026, seven words of header:

    0  MAGIC       0x48504731  "HPG1"
    1  VERSION     2 -- 1 summed the program words only
    2  WORDS       how many program words follow the relocation table
    3  LOAD_ADDR   where the loader writes them
    4  ENTRY       where execution starts -- not necessarily LOAD_ADDR
    5  RELOC_CNT   how many entries the relocation table has
    6  CHECKSUM32  the whole container's integrity, below
       RELOC       RELOC_CNT words, each an index into the program words
       PROGRAM     WORDS words, ASSEMBLED AT BASE 0

-- CHECKSUM32, the owner's K-8 and K-10 -----------------------------------
Version 1 summed the program words only, and the attack lab showed what that
leaves open: a relocation entry moved, and WORDS raised by one over zero
padding, both loaded without a refusal. The owner widened the cover on 22
September 2026 (K-8) and fixed the algorithm on 23 September (K-10):

    CHECKSUM32 = sum(canonical words) mod 2^32

    canonical words = the program-table record in sector 16
                        PROGRAM_ID, FLAGS, START_SECTOR, SECTOR_COUNT
                    + the seven header words, CHECKSUM32 itself counted as 0
                    + the relocation table
                    + the program words

Nothing outside the container and its record is in it: not the zero padding
after the last word, not another table entry, not another sector.

A word is a 32-bit unsigned value, and there is ONE way to read it -- the way
rtl/hcpu_sdio.v fills its buffer: "Word 0 holds the first four bytes of the
block, most significant byte first". send_program.py puts words on the wire
the same way, and the loader's hal_sd_get returns exactly the word this tool
emits. card_bytes() and card_words() below are that order in Python, and the
tests hold all three -- this builder, the Python loader here, and
rtl/programs/hos_prog_load.hasm -- to the same sum. VERSION is 2 for it: a
version-1 loader refuses these containers by name instead of misreading them,
the route the owner set on 18 September 2026.

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
VERSION = 2                 # CHECKSUM32 over the whole container, K-8 and K-10
HEADER_WORDS = 7
CHECKSUM_AT = 6
MASK = 0xFFFFFFFF
SECTOR_WORDS = 128
TABLE_SECTOR = 16
#: The one table entry rtl/programs/sd_writer.hasm writes: PROGRAM_ID 1, FLAGS
#: with bit 0 VALID, the container from sector 17. SECTOR_COUNT follows from
#: the container's length. A test reads these back out of sd_writer.hasm.
PROGRAM_ID, FLAGS_VALID, START_SECTOR = 1, 1, 17
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

    container = [MAGIC, VERSION, len(program), load_addr, entry, len(moved), 0,
                 *moved, *program]
    return seal(container, table_record(len(container)))


def table_record(container_words: int, program_id: int = PROGRAM_ID,
                 flags: int = FLAGS_VALID, start_sector: int = START_SECTOR) -> list[int]:
    """The sector-16 entry a container of this length gets from sd_writer."""
    return [program_id, flags, start_sector, -(-container_words // SECTOR_WORDS)]


def canonical_words(record: list[int], container: list[int]) -> list[int]:
    """What CHECKSUM32 sums, in order: the record, then the container with its
    own checksum field counted as zero."""
    body = list(container)
    body[CHECKSUM_AT] = 0
    return [w & MASK for w in list(record) + body]


def checksum32(record: list[int], container: list[int]) -> int:
    return sum(canonical_words(record, container)) & MASK


def seal(container: list[int], record: list[int]) -> list[int]:
    """The container with CHECKSUM32 computed for `record`. build() seals for
    the entry sd_writer will write; the attack lab seals for another one to
    stand for a table entry changed after sealing."""
    out = list(container)
    out[CHECKSUM_AT] = checksum32(record, out)
    return out


def card_bytes(words: list[int]) -> bytes:
    """Words as a sector holds them: most significant byte first."""
    return b"".join((w & MASK).to_bytes(4, "big") for w in words)


def card_words(data: bytes) -> list[int]:
    """A sector's bytes back into the words hal_sd_get returns."""
    return [int.from_bytes(data[i:i + 4], "big") for i in range(0, len(data) - 3, 4)]


def card_image(container: list[int], record: list[int] | None = None,
               extra: list[int] | None = None) -> dict[int, list[int]]:
    """Sector number -> 128 words, laid out as sd_writer lays them out: the
    record as entry 0 of sector 16, the container from its START_SECTOR, zero
    padding after. `extra` is appended after the container, inside its last
    sector -- the out-of-container case."""
    stream = list(container) + list(extra or [])
    record = record if record is not None else table_record(len(stream))
    sectors: dict[int, list[int]] = {TABLE_SECTOR: list(record) + [0] * (SECTOR_WORDS - 4)}
    for i in range(0, len(stream), SECTOR_WORDS):
        chunk = stream[i:i + SECTOR_WORDS]
        sectors[record[2] + i // SECTOR_WORDS] = chunk + [0] * (SECTOR_WORDS - len(chunk))
    return sectors


def load_check(sectors: dict[int, list[int]], program_id: int = PROGRAM_ID
               ) -> tuple[bool, str]:
    """The Python loader: rtl/programs/hos_prog_load.hasm's refusals, in its
    order, over the words it would read. Values are taken below 2^31, where
    the HCPU's size comparison and Python's agree."""
    table = sectors.get(TABLE_SECTOR, [0] * SECTOR_WORDS)
    for e in range(SECTOR_WORDS // 4):
        pid, flags, start, count = table[4 * e:4 * e + 4]
        if flags & 1 and pid == program_id:
            break
    else:
        return False, "no VALID entry carries that PROGRAM_ID"
    if count == 0:
        return False, "the entry claims no sectors"
    words = [w for s in range(start, start + count)
             for w in sectors.get(s, [0] * SECTOR_WORDS)]
    magic, version, n, load_addr, entry, reloc_cnt, stored = words[:HEADER_WORDS]
    if magic != MAGIC:
        return False, "MAGIC"
    if version != VERSION:
        return False, "VERSION"
    if n == 0:
        return False, "WORDS = 0"
    if load_addr + n - 1 > CODE_DEPTH - 1:
        return False, "the image runs past instruction memory"
    if not load_addr <= entry <= load_addr + n - 1:
        return False, "ENTRY outside the image"
    if reloc_cnt > RELOC_MAX:
        return False, "RELOC_CNT over the buffer"
    total = HEADER_WORDS + reloc_cnt + n
    if total > len(words):
        return False, "fewer words on the card than the header says"
    if checksum32([pid, flags, start, count], words[:total]) != stored:
        return False, "CHECKSUM32"
    return True, "loaded"


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
