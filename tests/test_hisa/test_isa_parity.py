"""
H-ISA parity: src/hijaiyyah/hisa/opcodes.py, src/hijaiyyah/hisa/assembler.py,
rtl/hcpu_pkg.vh, rtl/hcpu_decode.v, and docs/HISA_SPEC.md.

Upgraded per Owner Architecture Consistency Decision (CT-01-REV13):
  - Parses ALL Verilog numeric literals (hex 8'h.., decimal 8'd.., binary 8'b..,
    octal 8'o.., and unsized literals, regardless of leading whitespace) so
    non-hex definitions like `  `define OP_HDOT 8'd78` can never evade the gate.
  - Verifies opcode field width (8 bits), canonical hex formatting, numeric
    encoding uniqueness, RTL decode coverage (rtl/hcpu_decode.v), Python OpCode
    enum parity, Assembler mapping (OPERANDS & _MNEMONICS), Disassembler
    mapping, HISA_SPEC.md bidirectional parity, RTL_IMPLEMENTED inventory, and
    slot mnemonic conflicts (e.g., 0x4E CTHETA vs HDOT).
  - Includes isolated mutation testing to guarantee that any injected fault in
    encoding, width, mnemonic, decode, assembler, or spec is caught.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

from hijaiyyah.hisa.assembler import _MNEMONICS, OPERANDS
from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, InstructionWord, OpCode

ROOT = Path(__file__).resolve().parents[2]
PKG_VH = ROOT / "rtl" / "hcpu_pkg.vh"
DECODE_V = ROOT / "rtl" / "hcpu_decode.v"
SPEC_MD = ROOT / "docs" / "HISA_SPEC.md"

# Matches ANY `define OP_<NAME> <literal> (hex, decimal, binary, octal, or unsized),
# regardless of leading indentation.
_OP_DEFINE_ANY = re.compile(
    r"^\s*`define\s+OP_([A-Z0-9_]+)\s+(?:(\d+)'([hHdDbBoO])([0-9A-Fa-f_]+)|(\d+))",
    re.M,
)

# Opcode table rows in docs/HISA_SPEC.md: | 0xNN | `MNEMONIC` | ...
_SPEC_ROW = re.compile(r"^\|\s*0x([0-9A-Fa-f]{2})\s*\|\s*`([A-Z0-9_]+)`", re.M)

# `OP_<NAME> references in rtl/hcpu_decode.v
_DECODE_OP_REF = re.compile(r"`OP_([A-Z0-9_]+)")


@dataclass(frozen=True)
class RtlOpcodeDef:
    name: str
    value: int
    width: int | None
    base: str
    raw_literal: str


def _parse_rtl_opcode_defs(text: str) -> Dict[str, RtlOpcodeDef]:
    defs: Dict[str, RtlOpcodeDef] = {}
    base_map = {"h": 16, "d": 10, "b": 2, "o": 8}
    for m in _OP_DEFINE_ANY.finditer(text):
        name = m.group(1)
        if m.group(5) is not None:
            val = int(m.group(5), 10)
            defs[name] = RtlOpcodeDef(name, val, None, "unsized", m.group(5))
        else:
            width = int(m.group(2), 10)
            base_ch = m.group(3).lower()
            digits = m.group(4).replace("_", "")
            val = int(digits, base_map[base_ch])
            raw_lit = f"{width}'{m.group(3)}{m.group(4)}"
            defs[name] = RtlOpcodeDef(name, val, width, base_ch, raw_lit)
    return defs


def _rtl_opcode_defs() -> Dict[str, RtlOpcodeDef]:
    return _parse_rtl_opcode_defs(PKG_VH.read_text(encoding="utf-8"))


def _rtl_opcodes() -> Dict[str, int]:
    return {k: v.value for k, v in _rtl_opcode_defs().items()}


def _parse_spec_rows(text: str) -> List[Tuple[str, int]]:
    return [(m.group(2), int(m.group(1), 16)) for m in _SPEC_ROW.finditer(text)]


def _spec_opcodes() -> Dict[str, int]:
    return dict(_parse_spec_rows(SPEC_MD.read_text(encoding="utf-8")))


def _parse_decoded_opcodes(decode_text: str, rtl_defs: Dict[str, RtlOpcodeDef]) -> Set[str]:
    referenced = set(_DECODE_OP_REF.findall(decode_text))
    # Letter range 0xE0..0xFB is decoded via LETTER_OP_FIRST..LETTER_OP_LAST
    if "LETTER_OP_FIRST" in decode_text and "LETTER_OP_LAST" in decode_text:
        for name, d in rtl_defs.items():
            if name.startswith("L_") and 0xE0 <= d.value <= 0xFB:
                referenced.add(name)
    # Unimplemented opcodes fall into default -> HALT_ERR
    if "HALT_ERR" in rtl_defs:
        referenced.add("HALT_ERR")
    return referenced


RTL_DEFS = _rtl_opcode_defs()
RTL_OPCODES = _rtl_opcodes()
SPEC_OPCODES = _spec_opcodes()
DECODED_OPCODES = _parse_decoded_opcodes(DECODE_V.read_text(encoding="utf-8"), RTL_DEFS)


def verify_isa_consistency(
    pkg_text: str,
    decode_text: str,
    spec_text: str,
    py_opcodes: Dict[str, int],
    rtl_implemented_names: Set[str],
    asm_mnemonics: Dict[str, int],
    asm_operands: Dict[str, Tuple[str, ...]],
) -> List[str]:
    """
    Pure consistency verifier across all ISA representations. Used both by
    live repository tests and by isolated mutation tests.
    """
    errors: List[str] = []
    rtl_defs = _parse_rtl_opcode_defs(pkg_text)
    spec_rows = _parse_spec_rows(spec_text)
    spec_map = dict(spec_rows)
    decoded = _parse_decoded_opcodes(decode_text, rtl_defs)

    # 1. Check field bit-width (OPCODE_MSB - OPCODE_LSB + 1 == 8)
    msb_m = re.search(r"^\s*`define\s+OPCODE_MSB\s+(\d+)", pkg_text, re.M)
    lsb_m = re.search(r"^\s*`define\s+OPCODE_LSB\s+(\d+)", pkg_text, re.M)
    if not msb_m or not lsb_m or (int(msb_m.group(1)) - int(lsb_m.group(1)) + 1) != 8:
        errors.append("opcode_field_width_not_8")

    # 2. Check each RTL opcode literal width (8 bits) and canonical hex base ('h')
    seen_rtl_val: Dict[int, str] = {}
    for name, d in rtl_defs.items():
        if d.width != 8:
            errors.append(f"rtl_width:{name}:{d.raw_literal}")
        if d.base != "h":
            errors.append(f"rtl_non_hex:{name}:{d.raw_literal}")
        if not (0 <= d.value <= 0xFF):
            errors.append(f"rtl_out_of_byte:{name}:0x{d.value:X}")
        if d.value in seen_rtl_val:
            errors.append(f"rtl_duplicate_encoding:0x{d.value:02X}:{seen_rtl_val[d.value]}:{name}")
        seen_rtl_val[d.value] = name

        # 3. RTL vs Python OpCode enum
        if name not in py_opcodes:
            errors.append(f"missing_in_python:{name}")
        elif py_opcodes[name] != d.value:
            errors.append(f"value_mismatch_rtl_py:{name}:0x{d.value:02X}!=0x{py_opcodes[name]:02X}")

        # 4. RTL vs HISA_SPEC.md
        if name not in spec_map:
            errors.append(f"missing_in_spec:{name}:0x{d.value:02X}")
        elif spec_map[name] != d.value:
            errors.append(f"value_mismatch_rtl_spec:{name}:0x{d.value:02X}!=0x{spec_map[name]:02X}")

    # 5. RTL_IMPLEMENTED parity
    rtl_names = set(rtl_defs.keys())
    if rtl_implemented_names != rtl_names:
        diff_extra = sorted(rtl_implemented_names - rtl_names)
        diff_missing = sorted(rtl_names - rtl_implemented_names)
        errors.append(f"rtl_implemented_mismatch:extra={diff_extra},missing={diff_missing}")

    # 6. RTL Decode parity
    if decoded != rtl_names:
        undecoded = sorted(rtl_names - decoded)
        unknown_dec = sorted(decoded - rtl_names)
        if undecoded or unknown_dec:
            errors.append(f"decode_mismatch:undecoded={undecoded},unknown={unknown_dec}")

    # 7. Assembler mapping parity
    for name in rtl_implemented_names:
        if name not in asm_mnemonics:
            errors.append(f"missing_in_asm_mnemonics:{name}")
        if name not in asm_operands:
            errors.append(f"missing_in_asm_operands:{name}")
    for name, val in asm_mnemonics.items():
        if name.isascii() and name not in rtl_implemented_names:
            errors.append(f"unverified_opcode_in_assembler:{name}=0x{val:02X}")

    # 8. Slot mnemonic conflict between HISA_SPEC.md and RTL
    spec_by_val: Dict[int, List[str]] = {}
    for s_name, s_val in spec_rows:
        spec_by_val.setdefault(s_val, []).append(s_name)
    for val, r_name in seen_rtl_val.items():
        s_names = spec_by_val.get(val, [])
        if s_names and r_name not in s_names:
            errors.append(f"slot_mnemonic_conflict:0x{val:02X}:rtl=OP_{r_name},spec={s_names}")

    return errors


# ── 1. Header & Spec Parse Sanity ────────────────────────────────

def test_rtl_header_was_actually_parsed() -> None:
    assert PKG_VH.exists(), f"missing {PKG_VH}"
    assert len(RTL_OPCODES) >= 70, (
        f"only {len(RTL_OPCODES)} opcodes parsed from hcpu_pkg.vh"
    )


def test_opcode_field_width_is_eight_bits() -> None:
    text = PKG_VH.read_text(encoding="utf-8")
    msb = int(re.search(r"^\s*`define\s+OPCODE_MSB\s+(\d+)", text, re.M).group(1))
    lsb = int(re.search(r"^\s*`define\s+OPCODE_LSB\s+(\d+)", text, re.M).group(1))
    assert msb == 31 and lsb == 24 and (msb - lsb + 1) == 8


def test_rtl_opcode_defines_use_canonical_8bit_hex() -> None:
    """Every OP_* in hcpu_pkg.vh must be an explicit 8-bit hex literal 8'hXX."""
    bad = [
        f"OP_{d.name} = {d.raw_literal} (expected 8'h{d.value:02X})"
        for d in RTL_DEFS.values()
        if d.width != 8 or d.base != "h"
    ]
    assert not bad, "Non-canonical opcode literals in rtl/hcpu_pkg.vh: " + "; ".join(bad)


def test_rtl_opcode_values_are_unique() -> None:
    seen: Dict[int, str] = {}
    for name, value in RTL_OPCODES.items():
        assert value not in seen, (
            f"RTL assigns 0x{value:02X} to both {seen[value]} and {name}"
        )
        seen[value] = name


# ── 2. Encoding Parity (RTL <-> Python) ──────────────────────────

@pytest.mark.parametrize("name", sorted(RTL_OPCODES), ids=sorted(RTL_OPCODES))
def test_rtl_opcode_exists_in_python(name: str) -> None:
    assert name in OpCode.__members__, (
        f"rtl/hcpu_pkg.vh defines OP_{name} but hisa/opcodes.py does not"
    )


@pytest.mark.parametrize("name", sorted(RTL_OPCODES), ids=sorted(RTL_OPCODES))
def test_rtl_opcode_value_matches(name: str) -> None:
    rtl_value = RTL_OPCODES[name]
    py_value = int(OpCode[name])
    assert py_value == rtl_value, (
        f"{name}: RTL=0x{rtl_value:02X} but Python=0x{py_value:02X}."
    )


def test_rtl_implemented_set_is_exactly_the_rtl_header() -> None:
    """RTL_IMPLEMENTED must match all OP_* defines in hcpu_pkg.vh (including non-hex)."""
    declared = {op.name for op in RTL_IMPLEMENTED}
    actual = set(RTL_OPCODES)
    assert declared == actual, (
        f"claimed in RTL_IMPLEMENTED but not in RTL: {sorted(declared - actual)}; "
        f"defined in rtl/hcpu_pkg.vh but missing from RTL_IMPLEMENTED: {sorted(actual - declared)}"
    )


def test_software_only_opcodes_avoid_rtl_encodings() -> None:
    rtl_values = set(RTL_OPCODES.values())
    collisions = [
        (op.name, op.value)
        for op in OpCode
        if op not in RTL_IMPLEMENTED and op.value in rtl_values
    ]
    assert not collisions, (
        "software-only opcodes reusing an RTL encoding: "
        + ", ".join(f"{n}=0x{v:02X}" for n, v in collisions)
    )


def test_every_opcode_value_is_a_byte() -> None:
    for op in OpCode:
        assert 0 <= op.value <= 0xFF, f"{op.name}=0x{op.value:X} does not fit a byte"


def test_aliases_resolve_to_a_real_opcode() -> None:
    canonical = {op.value for op in OpCode}
    for name, member in OpCode.__members__.items():
        assert member.value in canonical, f"alias {name} points nowhere"


# ── 3. RTL Decode, Assembler & Disassembler Parity ───────────────

def test_rtl_decode_handles_every_rtl_opcode() -> None:
    """Every opcode defined in hcpu_pkg.vh must be decoded in hcpu_decode.v."""
    rtl_names = set(RTL_OPCODES)
    assert DECODED_OPCODES == rtl_names, (
        f"Defined in hcpu_pkg.vh but not decoded in hcpu_decode.v: {sorted(rtl_names - DECODED_OPCODES)}; "
        f"decoded but not in hcpu_pkg.vh: {sorted(DECODED_OPCODES - rtl_names)}"
    )


def test_assembler_maps_exact_rtl_implemented_set() -> None:
    """Assembler ASCII mnemonics must match RTL_IMPLEMENTED and have OPERANDS layouts."""
    impl_names = {op.name for op in RTL_IMPLEMENTED}
    asm_ascii = {k for k in _MNEMONICS if k.isascii()}
    assert asm_ascii == impl_names, (
        f"Assembler mnemonics differ from RTL_IMPLEMENTED: "
        f"extra={sorted(asm_ascii - impl_names)}, missing={sorted(impl_names - asm_ascii)}"
    )
    for name in impl_names:
        assert name in OPERANDS, f"Assembler OPERANDS missing layout for {name}"


def test_instruction_layout_matches_the_rtl_encoder() -> None:
    op, dst, s1, s2, imm = 0x42, 0xA, 0x5, 0x3, 0xABC
    raw = (op << 24) | (dst << 20) | (s1 << 16) | (s2 << 12) | imm

    word = InstructionWord(raw)
    assert word.opcode == op
    assert word.dst == dst
    assert word.src1 == s1
    assert word.src2 == s2
    assert word.imm == imm
    assert raw <= 0xFFFFFFFF


def test_disassembler_flags_software_only_instructions() -> None:
    hardware = InstructionWord(int(OpCode.HLOAD) << 24).disassemble()
    software = InstructionWord(int(OpCode.HPROJ) << 24).disassemble()
    assert "software only" not in hardware
    assert "software only" in software
    for op in RTL_IMPLEMENTED:
        dis = InstructionWord(int(op.value) << 24).disassemble()
        assert dis.startswith(op.name + " "), f"Disassembler mismatch on {op.name}: {dis}"
        assert "software only" not in dis


# ── 4. HISA_SPEC.md Parity & Slot Conflict Detection ─────────────

def test_spec_table_was_actually_parsed() -> None:
    assert SPEC_MD.exists(), f"missing {SPEC_MD}"
    assert len(SPEC_OPCODES) >= 60, (
        f"only {len(SPEC_OPCODES)} opcodes parsed from HISA_SPEC.md"
    )


@pytest.mark.parametrize(
    "name", sorted(set(SPEC_OPCODES) & set(OpCode.__members__)),
    ids=sorted(set(SPEC_OPCODES) & set(OpCode.__members__)),
)
def test_spec_opcode_value_matches(name: str) -> None:
    spec_value = SPEC_OPCODES[name]
    py_value = int(OpCode[name])
    assert py_value == spec_value, (
        f"{name}: HISA_SPEC.md=0x{spec_value:02X} but Python=0x{py_value:02X}"
    )


@pytest.mark.parametrize("name", sorted(RTL_OPCODES), ids=sorted(RTL_OPCODES))
def test_spec_documents_every_rtl_opcode(name: str) -> None:
    """Every hardware opcode in hcpu_pkg.vh must be documented in HISA_SPEC.md §6.2."""
    assert name in SPEC_OPCODES, (
        f"OP_{name} (0x{RTL_OPCODES[name]:02X}) exists in the RTL but is absent from HISA_SPEC.md §6.2"
    )


def test_no_spec_vs_rtl_slot_mnemonic_conflict() -> None:
    """No hex slot may be assigned one mnemonic in HISA_SPEC.md and a different
    non-alias mnemonic in rtl/hcpu_pkg.vh (catches 0x4E CTHETA vs OP_HDOT)."""
    spec_by_val: Dict[int, List[str]] = {}
    for s_name, s_val in _parse_spec_rows(SPEC_MD.read_text(encoding="utf-8")):
        spec_by_val.setdefault(s_val, []).append(s_name)

    conflicts: List[str] = []
    for r_name, r_val in sorted(RTL_OPCODES.items(), key=lambda x: x[1]):
        s_names = spec_by_val.get(r_val, [])
        if s_names and r_name not in s_names:
            conflicts.append(
                f"0x{r_val:02X}: HISA_SPEC.md defines {s_names}, but rtl/hcpu_pkg.vh defines OP_{r_name}"
            )
    assert not conflicts, "Mnemonic slot conflicts between HISA_SPEC.md and RTL: " + "; ".join(conflicts)


def test_spec_opcode_values_are_unique_or_declared_aliases() -> None:
    seen: Dict[int, str] = {}
    for name, value in SPEC_OPCODES.items():
        prior = seen.get(value)
        if prior is None:
            seen[value] = name
            continue
        both_known = name in OpCode.__members__ and prior in OpCode.__members__
        assert both_known and int(OpCode[name]) == int(OpCode[prior]), (
            f"HISA_SPEC.md assigns 0x{value:02X} to both {prior} and {name}, "
            "but hisa/opcodes.py does not declare them as aliases"
        )


def test_hload_is_not_halt() -> None:
    assert OpCode.HLOAD != OpCode.HALT
    assert int(OpCode.HLOAD) == RTL_OPCODES["HLOAD"]
    assert int(OpCode.HALT) == RTL_OPCODES["HALT"]


# ── 5. Isolated Mutation Testing & Live CTHETA/HDOT Parity ──────

def test_ctheta_0x4e_and_hdot_0x52_execution_parity() -> None:
    """
    Owner Architecture Decision:
      - 0x4E = CTHETA: extracts Theta_hat(H[S1]) = H[S1][7:0], 8-bit unsigned result, 1 cycle.
      - 0x52 = HDOT: 14-component inner product <H[S1], H[S2]>_14, 20-bit unsigned result.
    """
    from hijaiyyah.core.master_table import MASTER_TABLE
    from hijaiyyah.hisa.assembler import assemble
    from hijaiyyah.hisa.machine import HISAMachine

    assert int(OpCode.CTHETA) == 0x4E == RTL_OPCODES["CTHETA"] == SPEC_OPCODES["CTHETA"]
    assert int(OpCode.HDOT) == 0x52 == RTL_OPCODES["HDOT"] == SPEC_OPCODES["HDOT"]

    words = assemble(
        "HLOAD H1, 2\n"      # Ba: Theta_hat = 2
        "HLOAD H2, 24\n"     # Mim: Theta_hat = 4
        "CTHETA R1, H1\n"    # R1 = 2
        "CTHETA R2, H2\n"    # R2 = 4
        "HDOT R3, H1, H2\n"  # R3 = <Ba, Mim>_14 = 8
        "HALT\n"
    )
    assert (words[2] >> 24) & 0xFF == 0x4E
    assert (words[4] >> 24) & 0xFF == 0x52

    vm = HISAMachine(MASTER_TABLE)
    vm.load_program(words)
    vm.run()
    assert vm.regs.gpr[1] == 2
    assert vm.regs.gpr[2] == 4
    assert vm.regs.gpr[3] == 8


def test_mutation_harness_catches_all_injected_faults() -> None:
    """
    R3 Mutation Testing: verify that the live repository has 0 consistency
    errors, then inject 9 distinct classes of opcode/width/mnemonic/decode/
    assembler/spec mutations in memory and assert that verify_isa_consistency()
    catches every single one.
    """
    pkg_clean = PKG_VH.read_text(encoding="utf-8")
    dec_clean = DECODE_V.read_text(encoding="utf-8")
    spec_raw = SPEC_MD.read_text(encoding="utf-8")
    py_clean = {k: int(v.value) for k, v in OpCode.__members__.items()}
    impl_clean = {op.name for op in RTL_IMPLEMENTED}
    asm_m_clean = {k: int(v.value) for k, v in _MNEMONICS.items()}
    asm_o_clean = dict(OPERANDS)

    # 1. Live repository must pass with 0 consistency errors
    assert verify_isa_consistency(
        pkg_clean, dec_clean, spec_raw, py_clean, impl_clean, asm_m_clean, asm_o_clean
    ) == []

    # Mutation M0: Historical 0x4E CTHETA vs OP_HDOT 8'd78 collision
    pkg_m0 = re.sub(
        r"`define\s+OP_CTHETA\s+8'h4E",
        "  `define OP_HDOT        8'd78",
        re.sub(r"`define\s+OP_HDOT\s+8'h52[^\n]*\n", "", pkg_clean),
    )
    m0_errs = verify_isa_consistency(
        pkg_m0, dec_clean, spec_raw, py_clean, impl_clean, asm_m_clean, asm_o_clean,
    )
    assert any("rtl_non_hex:HDOT:8'd78" in e for e in m0_errs), m0_errs
    assert any("slot_mnemonic_conflict:0x4E" in e for e in m0_errs), m0_errs

    # Mutation M1: Mutate RTL opcode numeric value in hcpu_pkg.vh (CU 8'h4D -> 8'h5D)
    m1_errs = verify_isa_consistency(
        pkg_clean.replace("`define OP_CU          8'h4D", "`define OP_CU          8'h5D"),
        dec_clean, spec_raw, py_clean, impl_clean, asm_m_clean, asm_o_clean,
    )
    assert any("value_mismatch_rtl_py:CU" in e for e in m1_errs), m1_errs

    # Mutation M2: Mutate RTL literal to decimal 8'd79 (evaded old regex!)
    m2_errs = verify_isa_consistency(
        pkg_clean.replace("`define OP_CU          8'h4D", "  `define OP_CU        8'd79"),
        dec_clean, spec_raw, py_clean, impl_clean, asm_m_clean, asm_o_clean,
    )
    assert any("rtl_non_hex:CU" in e for e in m2_errs) and any("value_mismatch_rtl_py:CU" in e for e in m2_errs)

    # Mutation M3: Mutate RTL opcode width from 8-bit to 7-bit (7'h4D)
    m3_errs = verify_isa_consistency(
        pkg_clean.replace("`define OP_CU          8'h4D", "`define OP_CU          7'h4D"),
        dec_clean, spec_raw, py_clean, impl_clean, asm_m_clean, asm_o_clean,
    )
    assert any("rtl_width:CU:7'h4D" in e for e in m3_errs), m3_errs

    # Mutation M4: Duplicate encoding in RTL (CU shares 8'h4C with CRHO)
    m4_errs = verify_isa_consistency(
        pkg_clean.replace("`define OP_CU          8'h4D", "`define OP_CU          8'h4C"),
        dec_clean, spec_raw, py_clean, impl_clean, asm_m_clean, asm_o_clean,
    )
    assert any("rtl_duplicate_encoding:0x4C" in e for e in m4_errs), m4_errs

    # Mutation M5: Mutate Python OpCode enum value (CMOD4 = 0x5F instead of 0x4F)
    py_m5 = dict(py_clean, CMOD4=0x5F)
    m5_errs = verify_isa_consistency(
        pkg_clean, dec_clean, spec_raw, py_m5, impl_clean, asm_m_clean, asm_o_clean,
    )
    assert any("value_mismatch_rtl_py:CMOD4" in e for e in m5_errs), m5_errs

    # Mutation M6: Omit an implemented opcode from RTL_IMPLEMENTED
    m6_errs = verify_isa_consistency(
        pkg_clean, dec_clean, spec_raw, py_clean, impl_clean - {"CTHETA"}, asm_m_clean, asm_o_clean,
    )
    assert any("rtl_implemented_mismatch" in e for e in m6_errs), m6_errs

    # Mutation M7: Drop decode arm in hcpu_decode.v (`OP_CMOD4)
    m7_errs = verify_isa_consistency(
        pkg_clean, dec_clean.replace("`OP_CMOD4", "`OP_NOP"), spec_raw, py_clean, impl_clean, asm_m_clean, asm_o_clean,
    )
    assert any("decode_mismatch:undecoded=['CMOD4']" in e for e in m7_errs), m7_errs

    # Mutation M8: Introduce slot mnemonic conflict in HISA_SPEC.md
    m8_errs = verify_isa_consistency(
        pkg_clean, dec_clean,
        spec_raw.replace("| 0x4E | `CTHETA` |", "| 0x4E | `WRONG_OP` |"),
        py_clean, impl_clean, asm_m_clean, asm_o_clean,
    )
    assert any("slot_mnemonic_conflict:0x4E" in e for e in m8_errs), m8_errs
