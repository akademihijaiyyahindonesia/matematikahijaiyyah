# -*- coding: utf-8 -*-
"""Sealed H-ISA programs — the equivalent of a signed binary.

Linux and Windows both refuse to run code that fails a signature check, and
neither invented cryptography to do it: they compose a hash, a signature, and
a loader that declines. This is the same composition for H-ISA, using the
layers that already exist.

**The threat is the gap between building and running.** A `.hbc` file is
bytes on a disk. Between the assembler writing it and the HCPU fetching it,
anything with write access can change an instruction word — and a changed
instruction word is a different program with the same name. Nothing in the
loader noticed, because there was nothing to notice with: ``read_hbc`` was
never called from anywhere in the tree.

**Two checks, in the order the rest of this system uses.**

*Structure first, keyless and O(1) per word.* Every instruction word must
decode to a defined opcode. A program whose code section holds undefined
opcodes is refused before a hash is computed — the same shape as refusing a
letter index outside 1..28, and useful for the same reason: under a flood of
corrupt files, garbage never reaches SHA-256. It proves nothing about origin.
Anyone can assemble a structurally valid program.

*Then the seal.* HMAC-SHA256 over the whole file with a key derived through
HKDF from the dataset seal, so a program signed for one sealed release cannot
be presented to another. **This is the check that means anything**, and the
structural one is triage in front of it.

**What this does not do.** It does not sandbox, meter, or isolate anything —
a verified program is trusted completely once it runs, which is what
verification means and also its whole limitation. It does not establish who
signed: the key is symmetric, so anyone who can verify can also sign. That is
adequate for a build pipeline handing programs to its own boards and
inadequate for distributing software to parties who should not be able to
forge it; that needs a signature, not a MAC, and this module does not pretend
otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Set, Tuple

from hijaiyyah.crypto.guarded_record import CryptoRefusal, GuardedRecord
from hijaiyyah.crypto.kabah import Kabah

#: Bytes in one H-ISA instruction word.
WORD = 4


def defined_opcodes() -> Set[int]:
    """Every opcode the instruction set defines, from the set itself.

    Read from :mod:`hijaiyyah.hisa.opcodes` rather than listed here, so an
    opcode added there is admitted here without anyone remembering to.
    """
    from hijaiyyah.hisa import opcodes as table

    found: Set[int] = set()
    for name in dir(table):
        member = getattr(table, name)
        if isinstance(member, type):
            for entry in getattr(member, "__members__", {}).values():
                found.add(int(entry))
    return found


@dataclass(frozen=True)
class StructureReport:
    """What the keyless check found, and where."""

    valid: bool
    words: int
    first_bad: Optional[int] = None
    reason: str = ""


def check_code(code: bytes, opcodes: Optional[Set[int]] = None) -> StructureReport:
    """Validate a code section without a key.

    One comparison per instruction word: the top byte must name an opcode the
    instruction set defines. Cheap enough to run on everything, and it reports
    *which* word failed rather than only that one did — "word 412 holds opcode
    0x9C" is actionable in a way "the program is corrupt" is not.
    """
    known = defined_opcodes() if opcodes is None else opcodes
    if len(code) % WORD:
        return StructureReport(
            False, len(code) // WORD, len(code) // WORD,
            f"{len(code)} bytes is not a whole number of {WORD}-byte words")

    for index in range(0, len(code), WORD):
        opcode = code[index + 3]          # little-endian word, opcode in the top byte
        if opcode not in known:
            return StructureReport(
                False, len(code) // WORD, index // WORD,
                f"word {index // WORD} holds opcode {opcode:#04x}, which is undefined")
    return StructureReport(True, len(code) // WORD)


def seal_program(image: bytes, system: Kabah) -> GuardedRecord:
    """Authenticate a built program image.

    Raises:
        CryptoRefusal: If the image is not structurally a program. Signing
            something that cannot run is a way of certifying a mistake.
    """
    report = check_code(_code_section(image))
    if not report.valid:
        raise CryptoRefusal(f"refusing to seal: {report.reason}")
    return system.seal(image)


def load_verified(record: GuardedRecord, system: Kabah) -> bytes:
    """Recover a program image, or refuse.

    Structure is checked again after opening, not only before sealing. The
    seal proves the bytes are the ones that were signed; it does not prove
    they were worth signing, and a build pipeline that signed a broken image
    should still not have it run.
    """
    image = system.open(record)
    report = check_code(_code_section(image))
    if not report.valid:
        raise CryptoRefusal(f"sealed image is not a program: {report.reason}")
    return image


def _code_section(image: bytes) -> bytes:
    """The code bytes, or the whole image when it carries no header."""
    from hijaiyyah.hisa.hbc_format import HBC_HEADER_SIZE, HbcFile

    if len(image) < HBC_HEADER_SIZE:
        return image
    try:
        return HbcFile.from_bytes(image).code
    except Exception:
        # Not an .hbc container: treat the whole thing as instruction words.
        # Refusing here would make this module unusable for raw images, which
        # the assembler also emits.
        return image


def disassemble_opcodes(code: bytes) -> List[Tuple[int, int]]:
    """(word index, opcode) for each instruction, for a report or a diff."""
    return [(i // WORD, code[i + 3]) for i in range(0, len(code) - WORD + 1, WORD)]


def compare(before: Sequence[Tuple[int, int]],
            after: Sequence[Tuple[int, int]]) -> List[int]:
    """Word indices whose opcode changed between two images.

    What a refusal cannot tell you on its own: a MAC says *that* the program
    changed, never *where*. This is for the case where both images are in hand
    and the question is which instruction moved.
    """
    changed = []
    for (index, first), (_, second) in zip(before, after, strict=False):
        if first != second:
            changed.append(index)
    if len(before) != len(after):
        changed.extend(range(min(len(before), len(after)), max(len(before), len(after))))
    return changed
