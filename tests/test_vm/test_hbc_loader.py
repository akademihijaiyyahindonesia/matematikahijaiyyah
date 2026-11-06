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

from hijaiyyah.assembler import HBC_HEADER_SIZE, HBC_MAGIC, HASMAssembler, HBCHeader
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble, encode
from hijaiyyah.hisa.opcodes import OpCode
from hijaiyyah.hisa.parity_programs import PROGRAMS as PARITY_PROGRAMS
from hijaiyyah.vm import HVM, ControlFlowReport, verify_control_flow

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = "HLOAD H0, #27\nCGET R1, H0, #0\nCGET R2, H0, #13\nHALT\n"


def build(source: str = PROGRAM) -> bytes:
    result = HASMAssembler().assemble(source)
    assert result.success, result.errors
    return result.bytecode


def _pack_words(words: list[int], *, entry_point: int = 0) -> bytes:
    """Pack raw 32-bit instruction words into a valid .hbc container."""
    code = b"".join(int(w).to_bytes(4, "big") for w in words)
    header = HBCHeader(
        entry_point=entry_point,
        code_offset=HBC_HEADER_SIZE,
        code_size=len(code),
        const_offset=HBC_HEADER_SIZE,
    ).pack()
    return header + code


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


# ══════════════════════════════════════════════════════════════════
#  Static control-flow verification (4-B′ / Q-F9d)
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "op",
    [OpCode.JMP, OpCode.CALL, OpCode.JGP, OpCode.JGF, OpCode.JNP],
    ids=lambda op: op.name,
)
def test_absolute_targets_valid_and_out_of_bounds_or_negative(op: OpCode) -> None:
    """1. Valid absolute targets load; negative or out-of-bounds targets fail."""
    valid_words = [
        encode(op, imm=2),
        encode(OpCode.HALT),
        encode(OpCode.RET if op == OpCode.CALL else OpCode.HALT),
    ]
    report = verify_control_flow(valid_words)
    assert report.valid
    assert HVM().load_bytecode(_pack_words(valid_words)).verify()

    # Out-of-bounds target past the end of the program
    oob_words = [encode(op, imm=10), encode(OpCode.HALT)]
    bad_oob = verify_control_flow(oob_words)
    assert not bad_oob.valid
    assert bad_oob.first_bad == 0
    assert op.name in bad_oob.reason
    with pytest.raises(ValueError, match=op.name):
        HVM().load_bytecode(_pack_words(oob_words))

    # In a 12-bit unsigned imm field, (-1 & 0xFFF) encodes absolute target 4095,
    # not a signed offset; HISAMachine._execute sets pc = imm (4095), which is
    # rejected as an out-of-bounds absolute target.
    high_imm_words = [encode(op, imm=(-1) & 0xFFF), encode(OpCode.HALT)]
    bad_high = verify_control_flow(high_imm_words)
    assert not bad_high.valid
    assert bad_high.first_bad == 0
    assert f"{op.name} target 4095 (word 4095)" in bad_high.reason
    assert "signed" not in bad_high.reason
    with pytest.raises(ValueError, match=rf"{op.name} target 4095 \(word 4095\)"):
        HVM().load_bytecode(_pack_words(high_imm_words))

    bad_before_base = verify_control_flow(
        [encode(op, imm=4), encode(OpCode.HALT)],
        entry_point=10,
        base=10,
    )
    assert not bad_before_base.valid
    assert bad_before_base.first_bad == 0
    assert "word -6" in bad_before_base.reason


@pytest.mark.parametrize(
    "op",
    [OpCode.JEQ, OpCode.JNE, OpCode.JGD, OpCode.JNGD],
    ids=lambda op: op.name,
)
def test_relative_targets_valid_before_start_and_past_end(op: OpCode) -> None:
    """2. Valid PC-relative targets load; targets before 0 or >= len(words) fail."""
    valid_words = [
        encode(OpCode.NOP),
        encode(op, imm=2),              # 1 + 2 -> 3
        encode(OpCode.HALT),
        encode(op, imm=(-1) & 0xFFF),   # 3 - 1 -> 2
        encode(OpCode.HALT),
    ]
    assert verify_control_flow(valid_words).valid
    assert HVM().load_bytecode(_pack_words(valid_words)).verify()

    # Relative target before start of program (0 - 1 = -1)
    before_start = [encode(op, imm=(-1) & 0xFFF), encode(OpCode.HALT)]
    rep_before = verify_control_flow(before_start)
    assert not rep_before.valid
    assert rep_before.first_bad == 0
    assert "word -1" in rep_before.reason
    with pytest.raises(ValueError, match="word -1"):
        HVM().load_bytecode(_pack_words(before_start))

    # Relative target past end of program (0 + 4 = 4 >= 2)
    past_end = [encode(op, imm=4), encode(OpCode.HALT)]
    rep_past = verify_control_flow(past_end)
    assert not rep_past.valid
    assert rep_past.first_bad == 0
    assert "word 4" in rep_past.reason
    with pytest.raises(ValueError, match="word 4"):
        HVM().load_bytecode(_pack_words(past_end))


def test_entry_point_valid_and_invalid() -> None:
    """3. Valid non-zero entry_point starts there; invalid entry_point is refused."""
    words = [
        encode(OpCode.MOVI, dst=1, imm=99),
        encode(OpCode.HALT),
        encode(OpCode.MOVI, dst=1, imm=42),
        encode(OpCode.HALT),
    ]
    vm = HVM()
    header = vm.load_bytecode(_pack_words(words, entry_point=2))
    assert header.entry_point == 2
    assert vm.pc == 2
    assert vm._machine.regs.pc == 2
    trace = vm.run()
    assert len(trace) == 2
    assert trace[0].cycle == 1
    assert "MOVI R1 = 42" in trace[0].description
    assert "99" not in trace[0].description
    assert trace[1].cycle == 2
    assert "HALT" in trace[1].description
    assert vm.state()["gpr"][1] == 42

    for bad_entry in (-1, 4, 100):
        rep = verify_control_flow(words, entry_point=bad_entry)
        assert not rep.valid
        assert "entry_point" in rep.reason

    with pytest.raises(ValueError, match="entry_point"):
        HVM().load_bytecode(_pack_words(words, entry_point=4))

    assert not verify_control_flow([]).valid


def test_ordinary_last_instruction_falling_through_past_end_is_refused() -> None:
    """4. A program whose execution path ends in a non-terminating instruction fails."""
    fallthrough = [
        encode(OpCode.MOVI, dst=1, imm=7),
        encode(OpCode.NOP),
    ]
    rep = verify_control_flow(fallthrough)
    assert not rep.valid
    assert rep.first_bad == 1
    assert "falls through" in rep.reason
    with pytest.raises(ValueError, match="falls through"):
        HVM().load_bytecode(_pack_words(fallthrough))

    # Even if the last word in the binary is HALT, a reachable path that jumps
    # over HALT or reaches a trailing non-terminator must be rejected.
    jump_to_non_terminator = [
        encode(OpCode.JMP, imm=2),
        encode(OpCode.HALT),
        encode(OpCode.MOVI, dst=1, imm=5),
    ]
    rep2 = verify_control_flow(jump_to_non_terminator)
    assert not rep2.valid
    assert rep2.first_bad == 2
    with pytest.raises(ValueError, match="falls through"):
        HVM().load_bytecode(_pack_words(jump_to_non_terminator))


@pytest.mark.parametrize(
    "cond_op,is_rel",
    [
        (OpCode.JEQ, True),
        (OpCode.JNE, True),
        (OpCode.JGD, True),
        (OpCode.JNGD, True),
        (OpCode.JGP, False),
        (OpCode.JGF, False),
        (OpCode.JNP, False),
    ],
)
def test_conditional_branch_with_either_path_falling_through_is_refused(
    cond_op: OpCode, is_rel: bool
) -> None:
    """5. Both the taken and untaken paths of a conditional branch must terminate."""
    # Case A: Conditional branch at the last word (taken jumps to 0, untaken falls off)
    imm_to_zero = ((-1) & 0xFFF) if is_rel else 0
    untaken_falls_off = [
        encode(OpCode.HALT),
        encode(cond_op, imm=imm_to_zero),
    ]
    rep_a = verify_control_flow(untaken_falls_off, entry_point=1)
    assert not rep_a.valid
    assert rep_a.first_bad == 1
    assert "falls through" in rep_a.reason
    with pytest.raises(ValueError, match="falls through"):
        HVM().load_bytecode(_pack_words(untaken_falls_off, entry_point=1))

    # Case B: Untaken path halts at word 1, but taken path lands on word 2 (NOP)
    imm_to_two = 2
    taken_falls_off = [
        encode(cond_op, imm=imm_to_two),
        encode(OpCode.HALT),
        encode(OpCode.NOP),
    ]
    rep_b = verify_control_flow(taken_falls_off)
    assert not rep_b.valid
    assert rep_b.first_bad == 2
    assert "falls through" in rep_b.reason
    with pytest.raises(ValueError, match="falls through"):
        HVM().load_bytecode(_pack_words(taken_falls_off))


def test_call_with_out_of_bounds_or_non_terminating_return_is_refused() -> None:
    """6. CALL at the final word or with a falling-through continuation is refused."""
    # CALL at the final word has return address len(words), which is out of bounds
    call_at_end = [
        encode(OpCode.RET),
        encode(OpCode.CALL, imm=0),
    ]
    rep_end = verify_control_flow(call_at_end, entry_point=1)
    assert not rep_end.valid
    assert rep_end.first_bad == 1
    assert "CALL return address" in rep_end.reason
    with pytest.raises(ValueError, match="CALL return address"):
        HVM().load_bytecode(_pack_words(call_at_end, entry_point=1))

    # CALL whose continuation word (pc + 1) falls through past the end of the program
    call_continuation_falls_off = [
        encode(OpCode.RET),
        encode(OpCode.CALL, imm=0),
        encode(OpCode.NOP),
    ]
    rep_cont = verify_control_flow(call_continuation_falls_off, entry_point=1)
    assert not rep_cont.valid
    assert rep_cont.first_bad == 2
    with pytest.raises(ValueError, match="falls through"):
        HVM().load_bytecode(_pack_words(call_continuation_falls_off, entry_point=1))


@pytest.mark.parametrize(
    "terminator",
    [OpCode.HALT, OpCode.HALT_ERR, OpCode.RET, OpCode.ERET],
    ids=lambda op: op.name,
)
def test_valid_terminators_and_unconditional_jmp_are_accepted(
    terminator: OpCode,
) -> None:
    """7. HALT, HALT_ERR, RET, ERET, and JMP to a valid target are accepted."""
    words = [
        encode(OpCode.MOVI, dst=1, imm=3),
        encode(terminator),
    ]
    rep = verify_control_flow(words)
    assert isinstance(rep, ControlFlowReport)
    assert rep.valid
    assert HVM().load_bytecode(_pack_words(words)).verify()

    jmp_words = [
        encode(OpCode.JMP, imm=2),
        encode(OpCode.NOP),
        encode(terminator),
    ]
    assert verify_control_flow(jmp_words).valid
    assert HVM().load_bytecode(_pack_words(jmp_words)).verify()


def test_intentional_infinite_loop_is_accepted() -> None:
    """8. Intentional endless loops (self-JMP or multi-word JMP loop) are accepted."""
    spin = [
        encode(OpCode.MOVI, dst=1, imm=1),
        encode(OpCode.JMP, imm=1),
    ]
    assert verify_control_flow(spin).valid
    assert HVM().load_bytecode(_pack_words(spin)).verify()

    multi_step_loop = [
        encode(OpCode.MOVI, dst=0, imm=0),
        encode(OpCode.ADDI, dst=0, s1=0, imm=1),
        encode(OpCode.JMP, imm=1),
    ]
    assert verify_control_flow(multi_step_loop).valid
    assert HVM().load_bytecode(_pack_words(multi_step_loop)).verify()


def test_all_62_hasm_and_41_parity_programs_pass_control_flow_verification() -> None:
    """9. Every existing .hasm and parity program in the repository remains valid."""
    hasm_files = sorted(
        p for p in ROOT.rglob("*.hasm")
        if p.relative_to(ROOT).parts[0] != "cosmictera-build"
    )
    assert len(hasm_files) == 62
    for path in hasm_files:
        words = assemble(path.read_text(encoding="utf-8"), base_dir=path.parent)
        report = verify_control_flow(words)
        assert report.valid, f"{path.relative_to(ROOT)}: {report.reason}"
        assert HVM().load_bytecode(_pack_words(words)).verify()

    assert len(PARITY_PROGRAMS) == 41
    for name, words in PARITY_PROGRAMS.items():
        report = verify_control_flow(words)
        assert report.valid, f"{name}: {report.reason}"
        assert HVM().load_bytecode(_pack_words(words)).verify()
