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
OVERLAY_MAX_WORDS = 1792    # 0x380-0xA7F staging window (4096 - 0x900)
OVERLAY_MAX_CALL_DEPTH = 28 # RA_DEPTH (32) - 4 supervisor trap margin
OVERLAY_WORK_MAX = 252      # 0x004-0x0FF worklist capacity in hos_prog_load.hasm
_ROOT_OWNER = 0x7FF

# 256-bit allowed opcode bitmap (8 x 32-bit chunks) matching hos_prog_load.hasm
# Phase V1: the 80 valid RTL opcodes for 4-B' overlays under H-ISA v1.3-hmcl
# (includes OP_CTHETA 0x4E and OP_HDOT 0x52; excludes ERET 0x08, PUSH 0x32,
# POP 0x33, HALT_ERR 0xFF, and all unimplemented/non-RTL opcodes).
_OVERLAY_OPCODE_MASKS: tuple[int, ...] = (
    0x00170EDB,  # 0x00..0x1F
    0x0003C61F,  # 0x20..0x3F
    0x0007F1F5,  # 0x40..0x5F (includes OP_CTHETA 0x4E and OP_HDOT 0x52)
    0x00000001,  # 0x60..0x7F
    0x00000000,  # 0x80..0x9F
    0x07FF0005,  # 0xA0..0xBF
    0x00000000,  # 0xC0..0xDF
    0x0FFFFFFF,  # 0xE0..0xFF
)

_OVERLAY_OPCODE_MASKS_V1_2: tuple[int, ...] = (
    0x00170EDB,
    0x0003C61F,
    0x0003B1F5,  # 0x40..0x5F without OP_CTHETA 0x4E / OP_HDOT 0x52 (legacy v1.2)
    0x00000001,
    0x00000000,
    0x07FF0005,
    0x00000000,
    0x0FFFFFFF,
)


def _sext12(imm: int) -> int:
    val = imm & IMM_MASK
    return val - 0x1000 if (val & 0x800) else val


def relocations(source: str, base_dir: Path) -> tuple[list[int], list[int]]:
    """The program at base 0, and the indices of the words that hold addresses."""
    at_zero = assemble(source, base_dir=base_dir, base=0)
    at_delta = assemble(source, base_dir=base_dir, base=PROBE_DELTA)
    if len(at_zero) != len(at_delta):
        raise ValueError("the program changes length with its base")
    moved: list[int] = []
    for i, (a, b) in enumerate(zip(at_zero, at_delta, strict=True)):
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


def verify_overlay(relocated: list[int], load_addr: int,
                   entry: int, *,
                   isa_profile: str = "v1.3-hmcl") -> tuple[bool, str]:
    """Two-phase 4-B' overlay verification matching hos_prog_load.hasm.

    Distinguishes provably invalid programs (`invalid: ...`) from programs
    whose control flow or call depth cannot be statically proven
    (`unverified: ...`).
    """
    n = len(relocated)
    if n > OVERLAY_MAX_WORDS:
        return False, "invalid: WORDS over overlay staging buffer"

    masks = _OVERLAY_OPCODE_MASKS_V1_2 if isa_profile == "v1.2" else _OVERLAY_OPCODE_MASKS

    # Phase V1: opcode bitmap & static branch/jump/call target bounds
    for idx, word in enumerate(relocated):
        op = (word >> 24) & 0xFF
        imm = word & IMM_MASK
        chunk = op >> 5
        bit = (masks[chunk] >> (op & 31)) & 1
        if not bit:
            if op == 0x08:
                return False, f"unverified: dynamic control transfer ERET at word {idx}"
            if op == 0x32:
                return False, f"invalid: forbidden opcode PUSH at word {idx}"
            if op == 0x33:
                return False, f"invalid: forbidden opcode POP at word {idx}"
            if op == 0xFF:
                return False, f"invalid: forbidden opcode HALT_ERR at word {idx}"
            return False, f"invalid: illegal opcode {op:#04x} at word {idx}"

        if op in (0x22, 0x2E):  # JMP, CALL
            if op == 0x2E and idx == n - 1:
                return False, f"invalid: CALL at final word {idx} falls past end"
            target = imm - load_addr
            if not (0 <= target < n):
                return False, f"invalid: absolute target {imm:#x} at word {idx} outside program"
        elif op in (0x23, 0x24, 0x29, 0x2A):  # JEQ, JNE, JGD, JNGD
            if idx == n - 1:
                return False, f"invalid: conditional branch at final word {idx} falls past end"
            target = idx + _sext12(imm)
            if not (0 <= target < n):
                return False, f"invalid: relative target {target} at word {idx} outside program"

    # Phase V2: worklist control-flow & call-depth <= 28 verification from ENTRY
    entry_idx = entry - load_addr
    state = [0] * n
    work: list[tuple[int, int, int]] = []
    pc = entry_idx
    owner = _ROOT_OWNER
    d = 0

    while True:
        st = state[pc]
        if st != 0:
            old_owner = st >> 5
            old_d_plus_1 = st & 0x1F
            if old_owner != owner:
                if pc == entry_idx and owner == pc + 1:
                    return False, f"unverified: recursive call to ENTRY at word {pc}"
                return False, f"unverified: cross-procedure control flow at word {pc}"
            if old_d_plus_1 >= d + 1:
                if not work:
                    return True, "loaded"
                pc, owner, d = work.pop()
                continue

        state[pc] = (owner << 5) | (d + 1)
        word = relocated[pc]
        op = (word >> 24) & 0xFF
        imm = word & IMM_MASK

        if op == 0x01:  # HALT
            if not work:
                return True, "loaded"
            pc, owner, d = work.pop()
            continue

        if op == 0x2F:  # RET
            if d == 0:
                return False, f"invalid: RET reachable at call depth 0 at word {pc}"
            if not work:
                return True, "loaded"
            pc, owner, d = work.pop()
            continue

        if op == 0x22:  # JMP
            pc = imm - load_addr
            continue

        if op == 0x2E:  # CALL
            callee = imm - load_addr
            callee_owner = callee + 1
            if d == OVERLAY_MAX_CALL_DEPTH:
                active_owners = {owner} | {w_owner for _, w_owner, _ in work}
                if callee_owner in active_owners or callee == entry_idx:
                    return False, f"unverified: recursive call cycle at word {pc}"
                return (
                    False,
                    f"invalid: call depth {d + 1} exceeds maximum "
                    f"{OVERLAY_MAX_CALL_DEPTH} at word {pc}",
                )
            if len(work) >= OVERLAY_WORK_MAX:
                return (
                    False,
                    f"unverified: worklist capacity {OVERLAY_WORK_MAX} "
                    f"exceeded at word {pc}",
                )
            work.append((pc + 1, owner, d))
            pc = callee
            owner = callee_owner
            d = d + 1
            continue

        if op in (0x23, 0x24, 0x29, 0x2A):  # JEQ, JNE, JGD, JNGD
            if len(work) >= OVERLAY_WORK_MAX:
                return (
                    False,
                    f"unverified: worklist capacity {OVERLAY_WORK_MAX} "
                    f"exceeded at word {pc}",
                )
            target = pc + _sext12(imm)
            work.append((target, owner, d))
            pc = pc + 1
            continue

        pc = pc + 1
        if pc >= n:
            return False, f"invalid: fall-through past end of program at word {pc - 1}"


def _extract_relocated(sectors: dict[int, list[int]],
                       program_id: int = PROGRAM_ID
                       ) -> tuple[bool, str, list[int], int, int]:
    """Shared Pass 1 + Pass 2 relocation checks for Stage 2 and Stage 3."""
    table = sectors.get(TABLE_SECTOR, [0] * SECTOR_WORDS)
    for e in range(SECTOR_WORDS // 4):
        pid, flags, start, count = table[4 * e:4 * e + 4]
        if flags & 1 and pid == program_id:
            break
    else:
        return False, "no VALID entry carries that PROGRAM_ID", [], 0, 0
    if count == 0:
        return False, "the entry claims no sectors", [], 0, 0
    words = [w for s in range(start, start + count)
             for w in sectors.get(s, [0] * SECTOR_WORDS)]
    magic, version, n, load_addr, entry, reloc_cnt, stored = words[:HEADER_WORDS]
    if magic != MAGIC:
        return False, "MAGIC", [], 0, 0
    if version != VERSION:
        return False, "VERSION", [], 0, 0
    if n == 0:
        return False, "WORDS = 0", [], 0, 0
    if load_addr + n - 1 > CODE_DEPTH - 1:
        return False, "the image runs past instruction memory", [], 0, 0
    if not load_addr <= entry <= load_addr + n - 1:
        return False, "ENTRY outside the image", [], 0, 0
    if reloc_cnt > RELOC_MAX:
        return False, "RELOC_CNT over the buffer", [], 0, 0
    total = HEADER_WORDS + reloc_cnt + n
    if total > len(words):
        return False, "fewer words on the card than the header says", [], 0, 0
    if checksum32([pid, flags, start, count], words[:total]) != stored:
        return False, "CHECKSUM32", [], 0, 0

    reloc_table = words[HEADER_WORDS:HEADER_WORDS + reloc_cnt]
    prog_words = words[HEADER_WORDS + reloc_cnt:total]
    relocated: list[int] = []
    r_cursor = 0
    for idx, raw in enumerate(prog_words):
        w = raw & MASK
        if r_cursor < reloc_cnt and reloc_table[r_cursor] == idx:
            if (w & IMM_MASK) + load_addr > IMM_MASK:
                return False, "invalid: relocation immediate overflow", [], 0, 0
            w = (w + load_addr) & MASK
            r_cursor += 1
        relocated.append(w)
    if r_cursor != reloc_cnt:
        return False, "invalid: relocation entry unconsumed", [], 0, 0
    return True, "loaded", relocated, load_addr, entry


def load_check_raw(sectors: dict[int, list[int]], program_id: int = PROGRAM_ID
                   ) -> tuple[bool, str]:
    """Stage 2 raw container loader (hos_prog_load_raw): P6 integrity and
    relocation bounds without 4-B' overlay control-flow restrictions."""
    ok, reason, _, _, _ = _extract_relocated(sectors, program_id)
    return ok, reason


def load_check(sectors: dict[int, list[int]], program_id: int = PROGRAM_ID,
               *, overlay: bool = True,
               isa_profile: str = "v1.3-hmcl") -> tuple[bool, str]:
    """The Python loader: rtl/programs/hos_prog_load.hasm's refusals, in its
    order, over the words it would read. By default (`overlay=True`), enforces
    Stage 3 4-B' static overlay verification after Pass 1 CHECKSUM32."""
    ok, reason, relocated, load_addr, entry = _extract_relocated(sectors, program_id)
    if not ok or not overlay:
        return ok, reason
    return verify_overlay(relocated, load_addr, entry, isa_profile=isa_profile)


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
