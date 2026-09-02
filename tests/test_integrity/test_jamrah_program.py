"""
The jamrah gate as an H-ISA program, sealed by the system it implements.

This is the loop closed. Until the bitwise instructions existed the gate could
not be written as a program at all — extracting a bit needs a shift and a
mask, and the instruction set had neither. Now CosmicTera's own logic runs as
a program, and CosmicTera seals it.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.crypto.guarded_record import CryptoRefusal, GuardedRecord
from hijaiyyah.crypto.kabah import Kabah
from hijaiyyah.crypto.program import check_code, load_verified, seal_program
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import HISAMachine

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "rtl" / "programs" / "jamrah_gate.hasm"


def _words():
    return assemble(SOURCE.read_text(encoding="utf-8"))


def _run(byte: int):
    """Run the program with a byte patched into its opening MOVI."""
    program = list(_words())
    program[0] = (program[0] & 0xFFFFF000) | byte
    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(program)
    machine.run()
    return machine.regs.gpr[2], machine.regs.gpr[3]


# ══════════════════════════════════════════════════════════════════
#  The program agrees with the gate it reimplements
# ══════════════════════════════════════════════════════════════════

def test_the_program_matches_the_rtl_gate_on_every_byte() -> None:
    """
    All 256, against the same two answers hijaiyyah_jamrah_gate.v gives: the
    root of the seven-node tree, and whether the byte names a letter.
    """
    for byte in range(256):
        root, gate = _run(byte)
        assert root == bin(byte).count("1"), f"root wrong for {byte:#04x}"
        assert gate == int(1 <= byte <= 28), f"gate wrong for {byte:#04x}"


def test_the_tree_really_has_seven_internal_nodes() -> None:
    """
    Not a metaphor: an 8-leaf binary reduction has 4 + 2 + 1 internal nodes,
    and the program computes them in that shape rather than summing bits in a
    loop. Six ADDs build the levels; the seventh node is the root.
    """
    text = SOURCE.read_text(encoding="utf-8")
    adds = [line for line in text.splitlines()
            if line.strip().startswith("ADD ") and ";" not in line.split("ADD")[0]]
    assert len(adds) == 7


def test_the_range_check_is_branchless() -> None:
    """
    The instruction set has only JEQ and JNE in hardware, so a range check
    used to need a comparison chain. With shifts it needs none — bit 31 of
    (x - 29) is 1 exactly when x < 29.

    Branchless matters beyond elegance: a gate that branches on its input
    takes a different number of cycles for different bytes, and that is a
    timing channel on the very check meant to be cheap and uniform.
    """
    # Comments must be stripped first. The first version of this searched the
    # raw text and matched "JEQ" inside the comment explaining that JEQ is not
    # used — a test that reads documentation instead of instructions.
    text = SOURCE.read_text(encoding="utf-8")
    body = text[text.index("the gate:"):]
    code = [line.split(";")[0].strip() for line in body.splitlines()]
    code = [line for line in code if line]

    assert code, "no instructions found after the gate comment"
    for jump in ("JEQ", "JNE", "JGD", "JNGD", "JMP"):
        assert not any(line.startswith(jump) for line in code), f"{jump} branches"
    assert any(line.startswith("SHRI") for line in code)
    assert any(line.startswith("AND ") for line in code)


def test_every_byte_takes_the_same_number_of_instructions() -> None:
    """The claim above, measured rather than asserted."""
    counts = set()
    for byte in (0x00, 0x01, 0x1C, 0x1D, 0x80, 0xFF):
        program = list(_words())
        program[0] = (program[0] & 0xFFFFF000) | byte
        machine = HISAMachine(MASTER_TABLE)
        machine.load_program(program)
        steps = 0
        while machine.step() and steps < 200:
            steps += 1
        counts.add(steps)
    assert len(counts) == 1, f"cycle count varies with input: {sorted(counts)}"


# ══════════════════════════════════════════════════════════════════
#  Sealed by the system it implements
# ══════════════════════════════════════════════════════════════════

def _system() -> Kabah:
    return Kabah(bytes(range(32)), "programs", track_replays=False)


def _image() -> bytes:
    return b"".join(struct.pack("<I", word) for word in _words())


def test_the_program_seals_and_opens_byte_identical() -> None:
    system = _system()
    assert load_verified(seal_program(_image(), system), system) == _image()


def test_a_flipped_bit_in_the_sealed_gate_is_refused() -> None:
    system = _system()
    wire = bytearray(seal_program(_image(), system).to_bytes())
    wire[70] ^= 0x01
    with pytest.raises(CryptoRefusal):
        load_verified(GuardedRecord.from_bytes(bytes(wire)), system)


def test_the_program_is_structurally_valid_before_it_is_signed() -> None:
    """Signing something that cannot run is a way of certifying a mistake."""
    report = check_code(_image())
    assert report.valid
    assert report.words == len(_words())


def test_it_uses_the_instructions_that_were_missing() -> None:
    """
    The point of the whole exercise. Without ANDI, SHRI and AND this program
    does not exist — a bit cannot be extracted with add, subtract and
    multiply.
    """
    text = SOURCE.read_text(encoding="utf-8")
    for mnemonic in ("ANDI", "SHRI", "AND", "SUB"):
        assert mnemonic in text
