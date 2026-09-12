"""
One H-ISA assembler, held to one dialect.

H-ISA had three assemblers and they did not read the same language.
rtl/scripts/asm2hex.py — the one that feeds silicon — took the dialect Bab III
§IIIM.3.1 writes: register names, comma-separated operands, `#` immediates,
hex, labels. hisa/assembler.py and assembler/__init__.py took bare
space-separated integers and rejected all of it.

That is not a style difference. The parity gate the whole toolchain is built
around needs one .hasm file to reach both HVM and HCPU before anything can
compare them, and it could not: a file that assembled for the FPGA raised
`invalid literal for int()` in the package.

Two silent failures came with the split, and both are pinned below.
hisa/assembler.py looked mnemonics up with `_OP_MAP.get(mnemonic, 0)`, so a
typo assembled to NOP and ran. asm2hex.py's if-chain had no branch for HPACK
or HCRC, so `HCRC R1, H0` fell through to a bare opcode and dropped both
operands — reading H0 and writing R0 whatever the source said.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import (
    MAX_GPR,
    MAX_HREG,
    OPERANDS,
    AssemblyError,
    assemble,
    assemble_line,
    collect_labels,
    encode,
    parse_immediate,
    parse_register,
)
from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED

ROOT = Path(__file__).resolve().parents[2]
ASM2HEX = ROOT / "rtl" / "scripts" / "asm2hex.py"
PROGRAMS = sorted((ROOT / "rtl" / "programs").glob("*.hasm"))


# ══════════════════════════════════════════════════════════════════
#  Parity with the script that feeds silicon
# ══════════════════════════════════════════════════════════════════

def _asm2hex_words(path: Path) -> List[int]:
    result = subprocess.run(
        [sys.executable, str(ASM2HEX), str(path)],
        capture_output=True, text=True, check=True,
    )
    return [
        int(line.split()[0], 16)
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith(";")
    ]


def test_there_are_programs_to_compare() -> None:
    """A parity sweep over an empty corpus proves nothing."""
    assert len(PROGRAMS) >= 5, f"only {len(PROGRAMS)} .hasm programs found"


@pytest.mark.parametrize("path", PROGRAMS, ids=[p.stem for p in PROGRAMS])
def test_package_and_rtl_script_agree(path: Path) -> None:
    """
    The gate. Both ends of the toolchain must encode the same file identically,
    instruction for instruction.
    """
    # base_dir=path.parent: kernel.hasm ends in `.include "hal.hasm"`, and
    # both ends of the parity check have to resolve it the same way asm2hex
    # does (from the including file's own directory).
    assert assemble(path.read_text(encoding="utf-8"), base_dir=path.parent) == \
        _asm2hex_words(path)


# ══════════════════════════════════════════════════════════════════
#  Every opcode has a layout
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "op", sorted(RTL_IMPLEMENTED, key=lambda o: o.value), ids=lambda o: o.name
)
def test_every_frozen_opcode_has_an_operand_layout(op) -> None:
    """
    The defect that hid HPACK and HCRC was a missing branch in an if-chain.
    Layouts are data now, and a mnemonic without one is an error rather than
    a silent fall-through to zeroed operands.
    """
    assert op.name in OPERANDS, (
        f"{op.name} has no entry in OPERANDS — it would assemble with every "
        "operand dropped"
    )


def test_no_layout_describes_an_unknown_mnemonic() -> None:
    """
    Every layout must belong to something the assembler will accept. That is
    not the same as an opcode NAME: the Arabic letters are aliases for their
    own instructions, so `ج` is assemblable while not being a member name.
    """
    from hijaiyyah.hisa.assembler import _MNEMONICS

    assert set(OPERANDS) <= set(_MNEMONICS), (
        f"stale layouts: {sorted(set(OPERANDS) - set(_MNEMONICS))}")
    assert {op.name for op in RTL_IMPLEMENTED} <= set(_MNEMONICS)


# ══════════════════════════════════════════════════════════════════
#  The two silent failures
# ══════════════════════════════════════════════════════════════════

def test_an_unknown_mnemonic_is_an_error_not_a_nop() -> None:
    """`_OP_MAP.get(mnemonic, 0)` made every typo a NOP that ran."""
    with pytest.raises(AssemblyError, match="unknown mnemonic"):
        assemble_line("HXXXX R1, R2")


def test_hpack_and_hcrc_keep_their_operands() -> None:
    """`HCRC R1, H0` used to assemble as 0x51000000 — both operands dropped."""
    assert assemble_line("HPACK R3, H1, R2") == encode(0x50, 3, 1, 2)
    assert assemble_line("HCRC R4, H1") == encode(0x51, 4, 1)

    # The shape of the old bug: a bare opcode with everything zeroed.
    assert assemble_line("HCRC R4, H1") != encode(0x51)


# ══════════════════════════════════════════════════════════════════
#  Branch offsets — anchored to the RTL, not to taste
# ══════════════════════════════════════════════════════════════════

def test_branch_offset_is_relative_to_the_branch_itself() -> None:
    """
    hcpu_pkg.vh: `JNGD: if G=0: PC ← PC + sign_ext(IMM)`, and tb_hcpu_top
    Programme 5 jumps from address 2 with IMM 2 to reach address 4. So the
    offset is target − own address, with no extra increment.

    Getting this wrong is a one-instruction miss on silicon, and it is the
    regression that showed up when the two assemblers were first merged.
    """
    words = assemble("  HALT\n  HALT\n  JNGD target\n  HALT\n  HALT\ntarget:\n  HALT\n")
    branch = words[2]
    assert branch & 0xFFF == 5 - 2


def test_a_backward_branch_encodes_as_a_negative_offset() -> None:
    words = assemble("loop:\n  ADDI R1, R1, 1\n  JNE loop\n")
    offset = words[1] & 0xFFF
    assert offset == (0 - 1) & 0xFFF, "backwards branch must wrap as two's complement"


def test_jmp_takes_an_absolute_target() -> None:
    """JMP is `PC ← zero_ext(IMM)`, unlike the conditional branches."""
    words = assemble("  HALT\n  HALT\n  JMP target\ntarget:\n  HALT\n")
    assert words[2] & 0xFFF == 3


# ══════════════════════════════════════════════════════════════════
#  Dialect
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "source",
    [
        "HNRM2 R1, H0",
        "HNRM2  R1,H0",
        "HNRM2 R1 H0",
        "hnrm2 r1, h0",
        "        HNRM2   R1, H0        ; komentar",
    ],
    ids=["koma", "rapat", "spasi", "huruf kecil", "indentasi+komentar"],
)
def test_operand_separators_and_case(source: str) -> None:
    assert assemble_line(source) == encode(0x06, 1, 0)


@pytest.mark.parametrize(
    "written,value",
    [("42", 42), ("#42", 42), ("0x2A", 42), ("0X2A", 42)],
    ids=["desimal", "hash", "hex", "HEX"],
)
def test_immediate_forms(written: str, value: int) -> None:
    assert assemble_line(f"MOVI R1, {written}") == encode(0x04, 1, 0, 0, value)


def test_a_label_may_share_a_line_with_an_instruction() -> None:
    assert assemble("done: HALT\n") == [encode(0x01)]


def test_underscore_means_unused() -> None:
    assert assemble_line("ADD R1, _, R2") == encode(0x10, 1, 0, 2)


def test_hload_is_immediate_only() -> None:
    """HLOAD's ROM index has to be a compile-time immediate: `rom_addr =
    is_letter ? letter_index : id_imm[...]` in hcpu_execute.v never reads S1
    for HLOAD. A register operand used to be accepted -- "immreg" tried
    parse_immediate, and on failure fell back to parse_register, landing the
    register NUMBER in S1 and 0 in IMM -- so `HLOAD H0, R2` silently became
    `HLOAD H0, 0`, always, regardless of what R2 held. rtl/programs/
    test_guard.hasm was written exactly that way and had been printing 0
    instead of 28 since it was committed; nothing had ever run it and checked."""
    assert assemble_line("HLOAD H0, 31") == encode(0x40, 0, 0, 0, 31)
    with pytest.raises(AssemblyError):
        assemble_line("HLOAD H0, R2")


# ══════════════════════════════════════════════════════════════════
#  Bounds and errors
# ══════════════════════════════════════════════════════════════════

def test_register_bounds_match_the_hardware() -> None:
    assert parse_register(f"R{MAX_GPR}") == MAX_GPR & 0xF
    assert parse_register(f"H{MAX_HREG}") == MAX_HREG
    with pytest.raises(AssemblyError, match="out of range"):
        parse_register(f"R{MAX_GPR + 1}")
    with pytest.raises(AssemblyError, match="out of range"):
        parse_register(f"H{MAX_HREG + 1}")


def test_an_immediate_wider_than_twelve_bits_is_refused() -> None:
    with pytest.raises(AssemblyError, match="12 bits"):
        parse_immediate("4096")
    with pytest.raises(AssemblyError, match="12 bits"):
        parse_immediate("-2049")


def test_wrong_operand_count_is_refused() -> None:
    with pytest.raises(AssemblyError, match="takes"):
        assemble_line("HNRM2 R1")
    with pytest.raises(AssemblyError, match="takes"):
        assemble_line("HALT R1")


def test_an_unknown_label_is_refused() -> None:
    with pytest.raises(AssemblyError, match="neither a number nor a known label"):
        assemble("  JMP nowhere\n")


def test_a_duplicate_label_is_refused() -> None:
    with pytest.raises(AssemblyError, match="defined twice"):
        collect_labels(["a:", "  HALT", "a:", "  HALT"])


def test_errors_carry_the_source_line_number() -> None:
    with pytest.raises(AssemblyError, match="line 3"):
        assemble("  HALT\n  ; komentar\n  HXXXX R1\n")


# ══════════════════════════════════════════════════════════════════
#  Encoding shape
# ══════════════════════════════════════════════════════════════════

def test_instruction_word_field_layout() -> None:
    """{opcode[31:24], dst[23:20], s1[19:16], s2[15:12], imm[11:0]}"""
    word = encode(0xAB, 0xC, 0xD, 0xE, 0xFFF)
    assert word == 0xABCDEFFF


def test_blank_and_comment_lines_produce_nothing() -> None:
    assert assemble_line("") is None
    assert assemble_line("   ; hanya komentar") is None
    assert assemble_line("label_only:") is None


# ══════════════════════════════════════════════════════════════════
#  CGET, and the index bound both machines must agree on
# ══════════════════════════════════════════════════════════════════

def test_cget_encodes_the_component_index_in_the_immediate() -> None:
    assert assemble_line("CGET R1, H0, #13") == encode(0x44, 1, 0, 0, 13)


@pytest.mark.parametrize("index", [18, 31, 32, 99, 4095])
def test_an_index_past_seventeen_reads_nothing_on_either_machine(index: int) -> None:
    """
    A codex has eighteen components, so 18 and up name none of them and must
    yield zero. The bound has to be checked against the whole 12-bit
    immediate, not its low five bits: the RTL first truncated, so IMM=99
    arrived as 3 and returned Ba's Nd = 1 while the Python machine — checking
    the full immediate — returned 0. The two disagreed for every out-of-range
    index whose low five bits named a non-zero component, and Ba is exactly
    such a letter.
    """
    from hijaiyyah.hisa.machine import HISAMachine

    words = assemble(f"HLOAD H0, #2\nCGET R1, H0, #{index}\nHALT\n")
    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(words)
    machine.run()
    assert machine.dump_state()["gpr"][1] == 0, (
        f"index {index} (low five bits {index & 0x1F}) must read nothing"
    )


def test_the_probe_would_notice_truncation() -> None:
    """
    Ba's component 3 is Nd = 1, so a machine that truncated 99 to 3 would
    return 1 and the test above would fail. Without this the probe could pass
    on a letter whose component 3 happens to be zero — which is how the first
    version of the RTL check stayed green while the bound was broken.
    """
    entry = MASTER_TABLE.get_by_char("ب")
    assert entry is not None
    assert entry.vector[99 & 0x1F] != 0


# ══════════════════════════════════════════════════════════════════
#  CSET, the write half, and the width a component actually has
# ══════════════════════════════════════════════════════════════════

def test_cset_encodes_the_component_index_in_the_immediate() -> None:
    assert assemble_line("CSET H0, R1, #4") == encode(0x45, 0, 1, 0, 4)


def _run(source: str) -> dict:
    from hijaiyyah.hisa.machine import HISAMachine

    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(assemble(source))
    machine.run()
    return machine.dump_state()


def test_cset_writes_the_component_it_names_and_leaves_the_rest() -> None:
    """Seventeen components have to survive a write to the eighteenth."""
    before = _run("HLOAD H0, #2\nHALT\n")["hreg"][0]
    after = _run("HLOAD H0, #2\nMOVI R1, 5\nCSET H0, R1, #4\nHALT\n")["hreg"][0]

    assert after[4] == 5
    assert after[:4] == before[:4] and after[5:] == before[5:]


def test_cset_takes_the_low_byte_because_a_component_is_a_byte() -> None:
    """
    H-Reg components are eight bits wide on the hardware (HREG_W = 18 × 8), so
    a wider value cannot land in one whole. The interpreter masks to the same
    width rather than storing a number the silicon could not hold — the
    divergence class HLOAD's 0-based/1-based split belonged to.
    """
    state = _run("MOVI R5, 300\nCSET H2, R5, #2\nHALT\n")
    assert state["hreg"][2][2] == 300 & 0xFF


def test_the_rest_of_the_codex_block_assembles_to_the_spec_hex() -> None:
    """Opcodes the spec named and nothing executed until now. Each lands on the
    hex HISA_SPEC.md prints for it -- none of them is a new assignment.

    Six of them, not the seven the batch started with. CDOT (0x49) is not
    here because the assembler's dialect is RTL_IMPLEMENTED itself: its
    fourteen multipliers cost hcpu_gowin_top its placement, so it stays in the
    HVM with a named blocker in cosmictera-build/OFF.md."""
    assert assemble_line("CMOV H2, H0") == encode(0x46, 2, 0, 0, 0)
    assert assemble_line("CZERO H3") == encode(0x47, 3, 0, 0, 0)
    assert assemble_line("CEQ H0, H1") == encode(0x48, 0, 0, 1, 0)
    assert assemble_line("CRHO R2, H0") == encode(0x4C, 2, 0, 0, 0)
    assert assemble_line("CU R1, H0") == encode(0x4D, 1, 0, 0, 0)
    assert assemble_line("CMOD4 R3, H0") == encode(0x4F, 3, 0, 0, 0)


def test_zero_is_the_identity_and_passes_every_guard() -> None:
    """CZERO is not an erase. Zero is the identity of (V, +): three sum-checks
    of 0 = 0, rho = 0, and T1/T2 vacuous -- so it is a legitimate place to
    start building a vector, which is why the spec gives it an opcode."""
    state = _run("HLOAD H0, 27\n        CZERO H0\n        HGRD  H0\nHALT\n")
    assert state["hreg"][0] == [0] * 18
    assert state["sr"]["guard"] is True


def test_the_residue_of_a_corrupt_vector_is_negative_on_both_machines() -> None:
    """G4 IS the statement that rho is not negative, so the vector that exists
    to fail it has a negative residue -- and a GPR carries that as 32 bits of
    two's complement, the same on silicon and here."""
    from hijaiyyah.core.guards import compute_U
    from hijaiyyah.hisa.machine import ROM_NEGATIVE_VECTORS

    vector, _ = ROM_NEGATIVE_VECTORS[31]
    expected = (vector[0] - compute_U(list(vector))) & 0xFFFFFFFF
    assert expected > 0x7FFF_FFFF, "the probe needs a vector whose residue is negative"

    state = _run("HLOAD H0, 31\n        CRHO  R1, H0\nHALT\n")
    assert state["gpr"][1] == expected


@pytest.mark.parametrize("index", [18, 31, 99, 4095])
def test_an_index_past_seventeen_writes_nothing_on_either_machine(index: int) -> None:
    """CGET returns zero for an index that names nothing; CSET writes nothing."""
    before = _run("HLOAD H1, #12\nHALT\n")["hreg"][1]
    after = _run(f"HLOAD H1, #12\nMOVI R4, 9\nCSET H1, R4, #{index}\nHALT\n")["hreg"][1]
    assert after == before, f"index {index} (low five bits {index & 0x1F}) wrote a component"
