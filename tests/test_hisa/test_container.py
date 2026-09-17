"""The program container, held against the assembler rather than against itself.

Stage 2 of the gate to KV260 loads programs from the card, and the owner fixed
the container's shape on 18 September 2026: seven header words, a relocation
table, then the program stored at base 0. `rtl/scripts/build_container.py`
builds one; these tests say what a built one must satisfy.

The load-bearing test is the first: relocating a container has to produce
exactly what the assembler produces when told to assemble at that address. Any
other check compares the tool with a second transcription of itself.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from build_container import (  # noqa: E402
    CODE_DEPTH,
    HEADER_WORDS,
    IMM_MASK,
    MAGIC,
    VERSION,
    build,
    relocate,
    relocations,
)

from hijaiyyah.hisa.assembler import assemble  # noqa: E402

PROGRAMS = ROOT / "rtl" / "programs"
# Three programs with different shapes: one that uses HFS and the card, one
# that is a handful of words, and one that carries subroutines.
SAMPLES = ["test_hfs.hasm", "test_bsm.hasm", "subroutine.hasm"]


@pytest.mark.parametrize("name", SAMPLES)
@pytest.mark.parametrize("addr", [0x040, 0x100, 0x300, 0x800])
def test_relocating_a_container_equals_assembling_at_that_address(
        name: str, addr: int) -> None:
    src = PROGRAMS / name
    text = src.read_text(encoding="utf-8")
    load_addr, image = relocate(build(text, src.parent, addr))
    assert load_addr == addr
    assert image == assemble(text, base_dir=src.parent, base=addr)


@pytest.mark.parametrize("name", SAMPLES)
def test_the_header_says_what_the_body_is(name: str) -> None:
    src = PROGRAMS / name
    text = src.read_text(encoding="utf-8")
    c = build(text, src.parent, 0x100)
    magic, version, words, load_addr, entry, reloc_cnt, crc = c[:HEADER_WORDS]
    assert (magic, version) == (MAGIC, VERSION)
    assert len(c) == HEADER_WORDS + reloc_cnt + words
    assert (load_addr, entry) == (0x100, 0x100)
    program = c[HEADER_WORDS + reloc_cnt:]
    assert crc == sum(program) & 0xFFFFFFFF, "the sum covers the program words"
    assert crc != sum(c) & 0xFFFFFFFF, "the header must not be inside its own sum"


def test_the_relocation_table_is_the_words_that_actually_move() -> None:
    """Measured against the assembler twice, not read out of the source."""
    src = PROGRAMS / "test_hfs.hasm"
    text = src.read_text(encoding="utf-8")
    program, moved = relocations(text, src.parent)
    at_300 = assemble(text, base_dir=src.parent, base=0x300)
    differ = {i for i, (a, b) in enumerate(zip(program, at_300, strict=True)) if a != b}
    assert set(moved) == differ
    for i in moved:
        assert at_300[i] - program[i] == 0x300


def test_entry_may_differ_from_the_load_address() -> None:
    """The owner separated LOAD_ADDR and ENTRY so a program can hold a table or
    a bootstrap in front of the code that runs first."""
    src = PROGRAMS / "subroutine.hasm"
    text = src.read_text(encoding="utf-8")
    labels = [ln.split(":")[0] for ln in text.splitlines()
              if ln and not ln[0].isspace() and ":" in ln and not ln.startswith(";")]
    assert labels, "this program has no label to enter at"
    c = build(text, src.parent, 0x200, entry_label=labels[-1])
    assert c[3] == 0x200
    assert c[4] > c[3], "the last label cannot sit at the first word"


@pytest.mark.parametrize("name", SAMPLES)
def test_the_immediate_cannot_overflow_while_the_program_fits(name: str) -> None:
    """MEASURED, and it is why the immediate guard never fires on its own.

    IMM_W is 12 bits, so an immediate reaches 4,095 -- and instruction memory
    is 4,096 words. Every relocatable word holds a label INSIDE its own
    program, so its immediate is at most len(program) - 1, and any load address
    that keeps the program inside instruction memory keeps every immediate
    inside 12 bits too. The guard in build_container.py stays as a belt: it
    costs one comparison and it is the thing that would speak first if either
    of those two numbers ever moved apart.
    """
    src = PROGRAMS / name
    text = src.read_text(encoding="utf-8")
    program, moved = relocations(text, src.parent)
    if not moved:
        pytest.skip(f"{name} has no relocatable word")
    highest = max(program[i] & IMM_MASK for i in moved)
    assert highest <= len(program) - 1
    last_addr = CODE_DEPTH - len(program)
    assert highest + last_addr <= IMM_MASK
    build(text, src.parent, last_addr)                  # the last address that fits
    with pytest.raises(ValueError, match="instruction memory"):
        build(text, src.parent, last_addr + 1)


def test_a_program_that_would_run_past_instruction_memory_is_refused() -> None:
    src = PROGRAMS / "test_hfs.hasm"
    text = src.read_text(encoding="utf-8")
    words = len(relocations(text, src.parent)[0])
    with pytest.raises(ValueError, match="instruction memory"):
        build(text, src.parent, CODE_DEPTH - words + 1)


def test_a_missing_entry_label_is_an_error_not_a_guess() -> None:
    src = PROGRAMS / "test_bsm.hasm"
    with pytest.raises(ValueError, match="no label"):
        build(src.read_text(encoding="utf-8"), src.parent, 0x100,
              entry_label="tidak_ada")
