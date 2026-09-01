"""
The .hbc loader, and the format that had a writer and no reader.

Bab III §IIIH.3.1.1 gives HVM five components: Loader, Interpreter, Hybit
Engine, Guard System, HCHECK. Three were there. The two missing ones were the
two that make it a machine, so HVM held `load_hybit`, `cadd`, `proj`,
`guard_check` and `run_hcheck` — operations on a vector — and `load(v18)`
took a hybit, not a program.

Meanwhile the assembler had been writing .hbc images with a correct HBYT
header and a real instruction stream, and nothing ever read one back. A
format with a writer and no reader is not a format anybody depends on.

The loader refuses a bad image rather than executing it. That matters more
here than usual: an .hbc is the artefact that crosses a system boundary, and
the header carries the CRC that says it arrived intact.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest

from hijaiyyah.assembler import HBC_HEADER_SIZE, HBC_MAGIC, HASMAssembler
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.vm import HVM

PROGRAM = "HLOAD H0, #27\nCGET R1, H0, #0\nCGET R2, H0, #13\nHALT\n"


def build(source: str = PROGRAM) -> bytes:
    result = HASMAssembler().assemble(source)
    assert result.success, result.errors
    return result.bytecode


# ══════════════════════════════════════════════════════════════════
#  The round trip
# ══════════════════════════════════════════════════════════════════

def test_an_assembled_image_loads_and_runs() -> None:
    vm = HVM()
    header = vm.load_bytecode(build())
    vm.run()

    assert header.verify()
    entry = MASTER_TABLE.get_by_char("هـ")
    assert entry is not None
    state = vm.state()
    assert state["gpr"][1] == entry.vector[0], "Θ̂"
    assert state["gpr"][2] == entry.vector[13], "Qc"


def test_the_interpreter_exists_at_all() -> None:
    """
    _try_init_machine called HISAMachine with no arguments behind a bare
    `except Exception: return None`. HISAMachine takes the Master Table, so
    the call raised every time and was swallowed: the VM silently had no
    interpreter, and only said so when something asked it to run.
    """
    assert HVM()._machine is not None


def test_load_file_reads_from_disk(tmp_path: Path) -> None:
    path = tmp_path / "program.hbc"
    path.write_bytes(build())

    vm = HVM()
    vm.load_file(str(path))
    vm.run()
    assert vm.state()["gpr"][1] == 8


def test_the_image_really_carries_instructions() -> None:
    """
    The encoder once emitted `bytes(count)` — NUL bytes, one per instruction.
    An image of zeros loads and runs as a string of NOPs, so the round trip
    above would pass while carrying nothing.
    """
    image = build()
    body = image[HBC_HEADER_SIZE:]
    assert body, "no code section"
    assert any(body), "the code section is all zeros"
    assert body[0] == 0x40, "the first instruction should be HLOAD"


# ══════════════════════════════════════════════════════════════════
#  What the loader refuses
# ══════════════════════════════════════════════════════════════════

def test_a_truncated_image_is_refused() -> None:
    with pytest.raises(ValueError, match="header alone is"):
        HVM().load_bytecode(build()[:20])


def test_a_foreign_file_is_refused() -> None:
    with pytest.raises(ValueError, match="verification"):
        HVM().load_bytecode(b"NOTHBYT!" + bytes(40))


def test_a_corrupted_header_is_refused() -> None:
    """
    The CRC covers bytes 0–27. Flipping one bit in the code offset must be
    caught before a single instruction executes.
    """
    image = bytearray(build())
    image[16] ^= 0x01
    with pytest.raises(ValueError, match="CRC32"):
        HVM().load_bytecode(bytes(image))


def _reheader(image: bytes, **fields: int) -> bytes:
    """Rewrite header fields and recompute the CRC, so only the field is wrong."""
    magic, ver, har, flags, res, entry, off, size, const = struct.unpack(
        "<4sHHHHIIII", image[:28]
    )
    values = {
        "entry_point": entry, "code_offset": off,
        "code_size": size, "const_offset": const,
    }
    values.update(fields)
    body = struct.pack(
        "<4sHHHHIIII", magic, ver, har, flags, res,
        values["entry_point"], values["code_offset"],
        values["code_size"], values["const_offset"],
    )
    crc = zlib.crc32(body) & 0xFFFFFFFF
    return body + struct.pack("<I", crc) + image[HBC_HEADER_SIZE:]


def test_a_code_section_past_the_end_is_refused() -> None:
    """A valid CRC over a header that lies about its own size."""
    image = _reheader(build(), code_size=4096)
    with pytest.raises(ValueError, match="runs to"):
        HVM().load_bytecode(image)


def test_a_ragged_code_section_is_refused() -> None:
    """Instructions are 32 bits; a size that is not a multiple of four is wrong."""
    image = _reheader(build(), code_size=7)
    with pytest.raises(ValueError, match="whole number"):
        HVM().load_bytecode(image)


def test_the_reheader_helper_is_not_the_thing_being_tested() -> None:
    """An unchanged rewrite must still verify, or the refusals above prove nothing."""
    assert HVM().load_bytecode(_reheader(build())).verify()


def test_the_magic_is_what_the_book_specifies() -> None:
    """§IIIF.3.3.1: magic 0x48425954, "HBYT"."""
    assert HBC_MAGIC == b"HBYT"
    assert build()[:4] == HBC_MAGIC
