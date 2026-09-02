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


# ══════════════════════════════════════════════════════════════════
#  The whole corpus under one seal
# ══════════════════════════════════════════════════════════════════

def test_the_manifest_covers_every_program_that_assembles() -> None:
    """
    Sealing programs one at a time gives one record each, and a set of records
    is only as good as the habit around it — one goes missing and nothing says
    so. A manifest turns that into a single question.
    """
    from hijaiyyah.crypto.program import build_manifest

    manifest = build_manifest(ROOT)
    assert len(manifest.entries) >= 18
    assert sum(entry.words for entry in manifest.entries) > 300
    assert all(len(entry.digest) == 32 for entry in manifest.entries)


def test_programs_that_cannot_compile_are_recorded_not_skipped() -> None:
    """
    None of the ten .hc examples reduce to H-ISA: seven use string literals,
    which have no representation, and the rest hit FnDecl, ForStmt and
    string_integral(). That is the code generator's scope, not a sealing
    failure — and it belongs *in* the manifest.

    A manifest that quietly omits what it could not handle answers "is
    everything I sealed unchanged?" when the question worth answering is "is
    everything unchanged?" The gap between those is where something goes
    missing unnoticed.
    """
    from hijaiyyah.crypto.program import build_manifest

    manifest = build_manifest(ROOT)
    assert len(manifest.unsealed) >= 10
    assert all(item.reason for item in manifest.unsealed)
    assert any("string literal" in item.reason for item in manifest.unsealed)


def test_an_empty_image_is_refused_rather_than_hashed() -> None:
    """
    The first version of `image_of` used `compile_hc`, which writes a file and
    returns a status rather than words — so every .hc entry carried the
    SHA-256 of the empty string. A manifest certifying nothing is worse than
    no manifest, so an empty image is now a refusal.
    """
    from hijaiyyah.crypto.program import image_of

    empty = ROOT / "rtl" / "programs" / "_empty_probe.hasm"
    empty.write_text("; nothing here\n", encoding="utf-8")
    try:
        with pytest.raises(CryptoRefusal, match="no instructions"):
            image_of(empty)
    finally:
        empty.unlink()


def test_the_manifest_round_trips_and_is_deterministic() -> None:
    from hijaiyyah.crypto.program import Manifest, build_manifest

    manifest = build_manifest(ROOT)
    assert Manifest.from_bytes(manifest.to_bytes()) == manifest
    assert build_manifest(ROOT).to_bytes() == manifest.to_bytes()
    with pytest.raises(CryptoRefusal, match="trailing bytes"):
        Manifest.from_bytes(manifest.to_bytes() + b"\x00")


def test_a_changed_program_is_named_not_merely_counted() -> None:
    """
    "One program differs" is not actionable; "rtl/programs/test_loop.hasm
    differs" is.
    """
    from hijaiyyah.crypto.program import build_manifest, verify_manifest

    manifest = build_manifest(ROOT)
    assert verify_manifest(manifest, ROOT) == []

    target = ROOT / "rtl" / "programs" / "test_loop.hasm"
    original = target.read_text(encoding="utf-8")
    try:
        target.write_text(original + "        NOP\n", encoding="utf-8")
        assert verify_manifest(manifest, ROOT) == ["rtl/programs/test_loop.hasm"]
    finally:
        target.write_text(original, encoding="utf-8")


def test_a_deleted_program_counts_as_a_mismatch() -> None:
    """
    A silent skip would turn deletion into a way of passing, which is the one
    failure a manifest exists to catch.
    """
    from hijaiyyah.crypto.program import Manifest, ProgramEntry, verify_manifest

    ghost = Manifest((ProgramEntry("rtl/programs/gone.hasm", 4, bytes(32)),))
    assert "rtl/programs/gone.hasm" in verify_manifest(ghost, ROOT)


def test_the_manifest_digest_is_sha256_and_not_the_sponge() -> None:
    """
    The sponge fingerprint is [EH]. Using an unproven hash for the one
    artefact that certifies every other would invert the whole layering,
    however convenient the project's own primitive would be here.
    """
    import hashlib

    from hijaiyyah.crypto.program import build_manifest, image_of

    entry = next(e for e in build_manifest(ROOT).entries
                 if e.path == "rtl/programs/test_loop.hasm")
    assert entry.digest == hashlib.sha256(
        image_of(ROOT / "rtl" / "programs" / "test_loop.hasm")).digest()


# ══════════════════════════════════════════════════════════════════
#  The whole system, not only its programs
# ══════════════════════════════════════════════════════════════════

def test_the_system_manifest_covers_the_rtl_as_well_as_the_programs() -> None:
    """
    A program is only half of what decides what happens: change
    hcpu_execute.v and every sealed program still verifies while doing
    something different on the board.
    """
    from hijaiyyah.crypto.program import build_system_manifest

    manifest = build_system_manifest(ROOT)
    kinds = {entry.path.split(":")[0] for entry in manifest.entries if ":" in entry.path}
    assert {"rtl", "header", "testbench", "vector", "fpga", "seal"} <= kinds
    assert len(manifest.entries) >= 85


@pytest.mark.parametrize(
    "target,suffix",
    [
        ("rtl/hcpu_execute.v", "\n// probe\n"),
        ("rtl/hcpu_pkg.vh", "\n// probe\n"),
        ("rtl/tb/tb_hijaiyyah_sbox.v", "\n// probe\n"),
        ("rtl/tb/linear_in.hex", "0\n"),
        ("rtl/programs/test_loop.hasm", "        NOP\n"),
    ],
)
def test_a_change_to_any_kind_of_artefact_is_detected(target: str, suffix: str) -> None:
    from hijaiyyah.crypto.program import build_system_manifest, verify_manifest

    manifest = build_system_manifest(ROOT)
    path = ROOT / target
    original = path.read_bytes()
    try:
        path.write_bytes(original + suffix.encode())
        changed = verify_manifest(manifest, ROOT)
        assert any(target in name for name in changed), f"{target} went unnoticed"
    finally:
        path.write_bytes(original)
    assert verify_manifest(manifest, ROOT) == []


def test_programs_are_digested_by_image_and_sources_by_text() -> None:
    """
    The difference is deliberate. A program's seal is about what runs, so
    reformatting a comment must not break it. An RTL file has no canonical
    compiled form here, so any byte of it could change the gates and every
    byte is covered.
    """
    from hijaiyyah.crypto.program import build_system_manifest

    def loop_entry(manifest):
        return next(e for e in manifest.entries
                    if e.path.endswith("test_loop.hasm"))

    before = build_system_manifest(ROOT)
    program = ROOT / "rtl" / "programs" / "test_loop.hasm"
    original = program.read_text(encoding="utf-8")
    try:
        program.write_text(original + "; a comment changes nothing\n", encoding="utf-8")
        assert loop_entry(before).digest == loop_entry(build_system_manifest(ROOT)).digest
    finally:
        program.write_text(original, encoding="utf-8")


def test_the_dataset_seal_travels_in_the_manifest() -> None:
    """So a manifest that verifies also pins which sealed release it belongs to."""
    from hijaiyyah.crypto.guarded_record import dataset_seal
    from hijaiyyah.crypto.program import build_system_manifest

    entry = next(e for e in build_system_manifest(ROOT).entries
                 if e.path == "seal:master-table")
    assert entry.digest.hex() == dataset_seal()


def test_the_summary_does_not_call_bytes_instructions() -> None:
    """
    `words` counts instructions for a program and bytes for a source file, so
    summing the column and calling the total "instructions" is false — the
    first system manifest reported 479,626 of them.
    """
    from hijaiyyah.crypto.program import build_system_manifest

    line = build_system_manifest(ROOT).summary()
    assert "sources" in line and "bytes" in line
    instructions = int(line.split(" instructions")[0].split(", ")[-1])
    assert instructions < 10_000


# ══════════════════════════════════════════════════════════════════
#  The board path: what actually gets flashed
# ══════════════════════════════════════════════════════════════════

def test_the_manifest_covers_what_decides_the_board() -> None:
    """
    Constraints assign the pins and the clock, the Makefile names which
    program is built in, and program.hex is what `$readmemh` puts in the
    instruction memory. Sealing the RTL without them seals a design and not
    the thing flashed onto the part.
    """
    from hijaiyyah.crypto.program import build_system_manifest

    paths = {e.path for e in build_system_manifest(ROOT).entries}
    for expected in ("board:rtl/fpga/gowin/hcpu_gowin.cst",
                     "board:rtl/fpga/gowin/Makefile",
                     "board:rtl/fpga/gowin/program.hex"):
        assert expected in paths, f"{expected} is not covered"


def test_build_products_are_not_manifest_entries() -> None:
    """
    A compiled simulator is derived from what is sealed. Digesting it would
    make the manifest churn on every build while adding nothing a rebuild
    could not re-derive.
    """
    from hijaiyyah.crypto.program import BUILD_PRODUCTS, build_system_manifest

    paths = [e.path for e in build_system_manifest(ROOT).entries]
    assert ".vvp" in BUILD_PRODUCTS
    assert not any(path.endswith(tuple(BUILD_PRODUCTS)) for path in paths)


def test_each_program_hex_is_the_assembly_of_the_source_its_makefile_names() -> None:
    """
    A digest over program.hex proves it did not change; it does not prove it
    was ever right. The interesting failure is a hex edited directly — the
    .hasm reads correctly, review passes, and the board runs something else.
    """
    from hijaiyyah.crypto.program import check_board_hex

    assert check_board_hex(ROOT) == []


def test_a_hex_edited_behind_its_source_is_caught() -> None:
    from hijaiyyah.crypto.program import check_board_hex

    target = ROOT / "rtl" / "fpga" / "gowin" / "program.hex"
    original = target.read_text(encoding="utf-8")
    try:
        lines = original.splitlines()
        lines[3] = "00000000  // addr    3: NOP"
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        problems = check_board_hex(ROOT)
        assert problems and "program.hex is not the assembly" in problems[0]
    finally:
        target.write_text(original, encoding="utf-8")
    assert check_board_hex(ROOT) == []


def test_both_makefile_forms_are_readable() -> None:
    """
    Gowin writes `PROGRAM  = $(RTL_DIR)/programs/...`, Xilinx writes
    `PROGRAM ?= ../../programs/...`. The first version of the regex matched
    only the first and reported the second as unverifiable when its hex was
    in fact correct — a check that cannot read half its inputs invents
    failures.
    """
    import re

    pattern = re.compile(r"^PROGRAM\s*\??=\s*(\S+)\s*$", re.M)
    for makefile in sorted(ROOT.glob("rtl/fpga/*/Makefile")):
        assert pattern.search(makefile.read_text(encoding="utf-8")), makefile
