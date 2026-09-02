"""
Sealed H-ISA programs — the equivalent of a signed binary.

The threat is the gap between building and running. A `.hbc` is bytes on a
disk; between the assembler writing it and the HCPU fetching it, anything with
write access can change an instruction word, and a changed word is a different
program under the same name. Nothing noticed, because there was nothing to
notice with: `read_hbc` was never called from anywhere in the tree.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from hijaiyyah.crypto.guarded_record import CryptoRefusal, GuardedRecord
from hijaiyyah.crypto.kabah import Kabah
from hijaiyyah.crypto.program import (
    check_code,
    compare,
    defined_opcodes,
    disassemble_opcodes,
    load_verified,
    seal_program,
)
from hijaiyyah.hisa.assembler import assemble

ROOT = Path(__file__).resolve().parents[2]
PROGRAMS = sorted((ROOT / "rtl" / "programs").glob("*.hasm"))


def _image(path: Path) -> bytes:
    return b"".join(struct.pack("<I", word) for word in assemble(path.read_text()))


def _system(purpose: str = "programs") -> Kabah:
    return Kabah(bytes(range(32)), purpose, track_replays=False)


# ══════════════════════════════════════════════════════════════════
#  Every program in the tree, not one
# ══════════════════════════════════════════════════════════════════

def test_there_are_programs_to_seal() -> None:
    assert len(PROGRAMS) >= 6


@pytest.mark.parametrize("path", PROGRAMS, ids=lambda p: p.stem)
def test_every_hcpu_program_seals_and_opens_byte_identical(path: Path) -> None:
    system = _system()
    image = _image(path)
    assert load_verified(seal_program(image, system), system) == image


@pytest.mark.parametrize("path", PROGRAMS, ids=lambda p: p.stem)
def test_every_sealed_program_refuses_a_single_flipped_bit(path: Path) -> None:
    """
    One bit anywhere in the record, and it does not load. Which of the two
    layers catches it depends where the bit was — the guard rejects a letter
    index that leaves 1..28 before any hash runs, and the MAC catches the rest.
    Both are refusals; the test is that neither lets it through.
    """
    system = _system()
    record = seal_program(_image(path), system)

    wire = bytearray(record.to_bytes())
    wire[60] ^= 0x01
    with pytest.raises(CryptoRefusal):
        load_verified(GuardedRecord.from_bytes(bytes(wire)), system)


# ══════════════════════════════════════════════════════════════════
#  Structure: keyless, O(1) per word, and it names the word
# ══════════════════════════════════════════════════════════════════

def test_an_undefined_opcode_is_refused_before_any_hash() -> None:
    """
    The same shape as refusing a letter index outside 1..28, and useful for
    the same reason: under a flood of corrupt files, garbage never reaches
    SHA-256. It proves nothing about origin — anyone can assemble a
    structurally valid program.
    """
    image = bytearray(_image(PROGRAMS[0]))
    image[3] = 0x9C
    report = check_code(bytes(image))

    assert not report.valid
    assert report.first_bad == 0
    assert "0x9c" in report.reason


def test_the_report_names_which_word_failed() -> None:
    """
    "Word 412 holds opcode 0x9C" is actionable in a way "the program is
    corrupt" is not.
    """
    good = b"".join(struct.pack("<I", (0x10 << 24) | i) for i in range(8))
    bad = good[:12] + struct.pack("<I", 0x9C << 24) + good[16:]
    assert check_code(bad).first_bad == 3


def test_a_ragged_image_is_refused() -> None:
    assert not check_code(_image(PROGRAMS[0])[:-1]).valid


def test_sealing_refuses_a_program_that_cannot_run() -> None:
    """Signing something broken is a way of certifying a mistake."""
    image = bytearray(_image(PROGRAMS[0]))
    image[3] = 0x9C
    with pytest.raises(CryptoRefusal, match="refusing to seal"):
        seal_program(bytes(image), _system())


def test_the_opcode_set_is_read_from_the_instruction_set() -> None:
    """
    Not listed in this module, so an opcode added to the ISA is admitted here
    without anyone remembering to.
    """
    from hijaiyyah.hisa import opcodes

    known = defined_opcodes()
    assert len(known) > 40
    assert int(opcodes.OpCode.HALT) in known
    assert 0x9C not in known


# ══════════════════════════════════════════════════════════════════
#  Purposes, and locating a change
# ══════════════════════════════════════════════════════════════════

def test_a_program_sealed_for_one_purpose_does_not_verify_under_another() -> None:
    record = seal_program(_image(PROGRAMS[0]), _system("build"))
    with pytest.raises(CryptoRefusal, match="authentication failed"):
        load_verified(record, _system("deploy"))


def test_comparison_says_which_word_moved() -> None:
    """
    What a refusal cannot tell you on its own: a MAC says *that* a program
    changed, never *where*. This is for when both images are in hand.
    """
    image = _image(PROGRAMS[0])
    altered = bytearray(image)
    altered[3] = 0x22                      # a defined opcode, so structure passes
    assert check_code(bytes(altered)).valid
    assert compare(disassemble_opcodes(image),
                   disassemble_opcodes(bytes(altered))) == [0]


def test_the_module_states_what_a_symmetric_key_cannot_do() -> None:
    """
    Anyone who can verify can also sign. Adequate for a build pipeline handing
    programs to its own boards, inadequate for distribution — that needs a
    signature, not a MAC, and the module has to keep saying so.
    """
    from hijaiyyah.crypto import program

    doc = " ".join((program.__doc__ or "").split())
    assert "It does not establish who signed" in doc
    assert "needs a signature, not a MAC" in doc
    assert "does not sandbox, meter, or isolate" in doc
