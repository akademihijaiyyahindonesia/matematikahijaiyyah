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
from pathlib import Path
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


# ── The whole corpus, in one record ──────────────────────────────

@dataclass(frozen=True)
class ProgramEntry:
    """One program: where it lives, how big it is, what it hashes to."""

    path: str
    words: int
    digest: bytes                       # SHA-256 of the assembled image

    def line(self) -> str:
        return f"{self.digest.hex()}  {self.words:>6}  {self.path}"


@dataclass(frozen=True)
class Unsealed:
    """A program that could not be reduced to instructions, and why.

    These are recorded rather than skipped. A manifest that quietly omits what
    it could not handle answers "is everything I sealed unchanged?" when the
    question worth answering is "is everything unchanged?" — and the gap
    between those two is exactly where something goes missing unnoticed.
    """

    path: str
    reason: str


@dataclass(frozen=True)
class Manifest:
    """Every program in a tree, under one seal.

    Sealing twenty-eight programs individually gives twenty-eight records to
    keep, and a set of records is only as trustworthy as the weakest habit
    around it — one goes missing and nothing says so. A manifest turns that
    into a single question: does the corpus still match?

    **The digest is SHA-256, not the sponge.** The sponge fingerprint is [EH]
    and must not carry integrity weight, however convenient it would be to
    use the project's own primitive here. Using an unproven hash for the one
    artefact that certifies everything else would invert the whole layering.

    Canonical by construction: entries sorted by path, fixed-width counts,
    no optional fields. Two builds over one tree produce identical bytes.
    """

    entries: Tuple[ProgramEntry, ...]
    unsealed: Tuple[Unsealed, ...] = ()

    def to_bytes(self) -> bytes:
        out = bytearray(b"HMF1")
        out += len(self.entries).to_bytes(4, "big")
        for entry in self.entries:
            encoded = entry.path.encode("utf-8")
            out += len(encoded).to_bytes(2, "big") + encoded
            out += entry.words.to_bytes(4, "big")
            out += entry.digest
        out += len(self.unsealed).to_bytes(4, "big")
        for item in self.unsealed:
            for field_text in (item.path, item.reason):
                encoded = field_text.encode("utf-8")[:255]
                out += bytes([len(encoded)]) + encoded
        return bytes(out)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Manifest":
        if not data.startswith(b"HMF1"):
            raise CryptoRefusal("not a program manifest: wrong magic")
        count = int.from_bytes(data[4:8], "big")
        at = 8
        entries = []
        for _ in range(count):
            length = int.from_bytes(data[at : at + 2], "big")
            at += 2
            path = data[at : at + length].decode("utf-8")
            at += length
            words = int.from_bytes(data[at : at + 4], "big")
            at += 4
            entries.append(ProgramEntry(path, words, data[at : at + 32]))
            at += 32

        skipped = int.from_bytes(data[at : at + 4], "big")
        at += 4
        unsealed = []
        for _ in range(skipped):
            values = []
            for _field in range(2):
                length = data[at]
                at += 1
                values.append(data[at : at + length].decode("utf-8"))
                at += length
            unsealed.append(Unsealed(*values))

        if at != len(data):
            raise CryptoRefusal(f"{len(data) - at} trailing bytes after {count} entries")
        return cls(tuple(entries), tuple(unsealed))

    def summary(self) -> str:
        total = sum(entry.words for entry in self.entries)
        tail = f", {len(self.unsealed)} not compilable" if self.unsealed else ""
        return f"{len(self.entries)} programs, {total} instructions{tail}"


def image_of(path: Path) -> bytes:
    """Assemble or compile one source file into instruction words.

    Both front ends land in the same place, which is the point: a `.hc`
    program and a `.hasm` program are the same thing once they are words, and
    the seal should not care which one a file started as.
    """
    import struct

    from hijaiyyah.hisa.assembler import assemble

    text = path.read_text(encoding="utf-8")
    if path.suffix == ".hc":
        # `compile_hc` writes a file and returns a status, so it hands back no
        # words at all. Using it here produced a manifest whose ten HC entries
        # all carried the SHA-256 of the empty string — a manifest certifying
        # nothing, which is worse than no manifest. The lower-level path is
        # what the integration tests use, and it returns the assembly.
        from hijaiyyah.compiler.codegen import generate
        from hijaiyyah.compiler.psi import inject
        from hijaiyyah.language.lexer import Lexer
        from hijaiyyah.language.parser import Parser

        ast = Parser(Lexer(text).tokenize()).parse()
        text = generate(ast, inject(ast)).text

    words = assemble(text)
    if not words:
        raise CryptoRefusal(f"{path} produced no instructions")
    return b"".join(struct.pack("<I", int(word)) for word in words)


def build_manifest(root: Path, patterns: Sequence[str] = ("*.hasm", "*.hc")) -> Manifest:
    """Assemble every program under `root` and record what it hashes to."""
    import hashlib

    found: List[ProgramEntry] = []
    skipped: List[Unsealed] = []
    for pattern in patterns:
        for path in root.rglob(pattern):
            if ".git" in path.parts:
                continue
            name = str(path.relative_to(root))
            try:
                image = image_of(path)
            except Exception as reason:
                skipped.append(Unsealed(name, str(reason)[:120]))
                continue
            found.append(ProgramEntry(
                name, len(image) // WORD, hashlib.sha256(image).digest()))
    return Manifest(
        tuple(sorted(found, key=lambda e: e.path)),
        tuple(sorted(skipped, key=lambda u: u.path)))


def verify_manifest(manifest: Manifest, root: Path) -> List[str]:
    """Paths whose program no longer matches the manifest.

    Reports *which* ones, and reports a missing file as a mismatch rather
    than skipping it — a program that vanished is exactly the case a manifest
    exists to catch, and a silent skip would turn deletion into a way of
    passing.
    """
    current = {entry.path: entry for entry in build_manifest(root).entries}
    changed = []
    for entry in manifest.entries:
        found = current.get(entry.path)
        if found is None or found.digest != entry.digest:
            changed.append(entry.path)
    for path in current:
        if not any(entry.path == path for entry in manifest.entries):
            changed.append(path)
    return sorted(changed)


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
