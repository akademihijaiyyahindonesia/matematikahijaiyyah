"""
Tab: Bytecode Inspector — Interactive H-ISA Instruction Decoder
================================================================
Real-time instruction word decoder synchronized with ``hisa/opcodes.py``:
  - Live hex input with instant decode
  - Visual bit-field breakdown
  - Opcode reference table (all 105 canonical opcodes + 17 aliases)
  - Instruction builder (reverse: pick opcode → get hex)
  - Batch decode mode
  - Copy-to-clipboard
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional, Tuple

from ...core.master_table import MASTER_TABLE
from ...hisa.opcodes import RTL_IMPLEMENTED, InstructionWord, OpCode, is_rtl_implemented
from ..theme import THEME
from ..widgets import OutputWriter, make_text

# ── Letter index → name for HLOAD (1-based: 1..28) ────────────────

_LETTER_NAMES: Dict[int, str] = {}
for _e in MASTER_TABLE.all_entries():
    _LETTER_NAMES[_e.index] = f"{_e.index}: {_e.char} ({_e.name})"

# ── Category & documentation metadata keyed by canonical OpCode ───

_CATEGORY_RANGES: List[Tuple[int, int, str]] = [
    (0x00, 0x0F, "System & Control"),
    (0x10, 0x1F, "Integer Arithmetic"),
    (0x20, 0x2F, "Compare & Control Flow"),
    (0x30, 0x3F, "Memory & Stack"),
    (0x40, 0x5F, "Codex Operations"),
    (0x60, 0x6F, "Guards & Audit"),
    (0x70, 0x7F, "Crypto"),
    (0x80, 0x8F, "Vector Math"),
    (0xA0, 0xAF, "I/O & Debug"),
    (0xB0, 0xBF, "Bitwise & Shift"),
    (0xE0, 0xFB, "Letter Instructions (0xE0–0xFB)"),
    (0xFF, 0xFF, "System Fault"),
]

_OP_OVERRIDES: Dict[int, Tuple[str, str, str, str]] = {
    0x00: ("NOP", "No operation", "No operands", "0x00000000 → NOP"),
    0x01: ("HALT", "Terminate execution", "No operands", "0x01000000 → HALT"),
    0x03: ("MOV dst s1", "GPR[dst] ← GPR[s1]", "DST, SRC1", "0x03100000 → MOV R1, R0"),
    0x04: ("MOVI dst imm", "GPR[dst] ← sext12(imm)", "DST, IMM", "0x0400000A → MOVI R0, 10"),
    0x06: ("HNRM2 dst s1", "GPR[dst] ← ‖H[s1]‖² (14D)", "DST=GPR, SRC1=H-reg", "0x06000000 → HNRM2 R0, H0"),
    0x07: ("HDIST dst s1 s2", "GPR[dst] ← ‖H[s1] − H[s2]‖² (14D)", "DST=GPR, SRC1/2=H-reg", "0x07001000 → HDIST R0, H0, H1"),
    0x08: ("ERET", "Return from trap (PC ← EPC)", "No operands", "0x08000000 → ERET"),
    0x09: ("SYSCALL", "Supervisor call (number & args in GPR)", "Registers by ABI", "0x09000000 → SYSCALL"),
    0x0A: ("FRD dst", "GPR[dst] ← FLAGS (zero-extended)", "DST=GPR", "0x0A000000 → FRD R0"),
    0x0B: ("FWR s1", "FLAGS ← GPR[s1][7:0]", "SRC1=GPR", "0x0B000000 → FWR R0"),
    0x10: ("ADD dst s1 s2", "GPR[dst] ← GPR[s1] + GPR[s2]", "DST, SRC1, SRC2", "0x10201000 → ADD R2, R0, R1"),
    0x11: ("ADDI dst s1 imm", "GPR[dst] ← GPR[s1] + sext12(imm)", "DST, SRC1, IMM", "0x11000001 → ADDI R0, R0, 1"),
    0x12: ("SUB dst s1 s2", "GPR[dst] ← GPR[s1] − GPR[s2]", "DST, SRC1, SRC2", "0x12201000 → SUB R2, R0, R1"),
    0x14: ("MUL dst s1 s2", "GPR[dst] ← GPR[s1] × GPR[s2]", "DST, SRC1, SRC2", "0x14201000 → MUL R2, R0, R1"),
    0x20: ("CMP s1 s2", "Compare GPR[s1] and GPR[s2], update FLAGS", "SRC1, SRC2", "0x20001000 → CMP R0, R1"),
    0x21: ("CMPI s1 imm", "Compare GPR[s1] with sext12(imm)", "SRC1, IMM", "0x2100001C → CMPI R0, 28"),
    0x22: ("JMP imm", "Unconditional jump to word address imm", "IMM=target word", "0x22000010 → JMP 16"),
    0x23: ("JEQ imm", "Branch relative by sext12(imm) if FLAGS.Z=1", "IMM=rel offset", "0x23000002 → JEQ +2"),
    0x24: ("JNE imm", "Branch relative by sext12(imm) if FLAGS.Z=0", "IMM=rel offset", "0x24000FFE → JNE -2"),
    0x29: ("JGD imm", "Branch relative if GUARD_PASS=1", "IMM=rel offset", "0x29000002 → JGD +2"),
    0x2A: ("JNGD imm", "Branch relative if GUARD_PASS=0", "IMM=rel offset", "0x2A000002 → JNGD +2"),
    0x2B: ("JGP imm", "Jump to imm if guard pass (software only)", "IMM=target word", "0x2B000010 → JGP 16"),
    0x2C: ("JGF imm", "Jump to imm if guard fail (software only)", "IMM=target word", "0x2C000010 → JGF 16"),
    0x2D: ("JNP imm", "Jump to imm if not pass (software only)", "IMM=target word", "0x2D000010 → JNP 16"),
    0x2E: ("CALL imm", "Call subroutine at word address imm", "IMM=target word", "0x2E000020 → CALL 32"),
    0x2F: ("RET", "Return from subroutine", "No operands", "0x2F000000 → RET"),
    0x30: ("LOAD dst s1 imm", "GPR[dst] ← MEM[GPR[s1] + sext12(imm)]", "DST, SRC1, IMM", "0x30000000 → LOAD R0, [R0+0]"),
    0x31: ("STORE s1 s2 imm", "MEM[GPR[s1] + sext12(imm)] ← GPR[s2]", "SRC1=base, SRC2=val", "0x31001000 → STORE [R0+0], R1"),
    0x32: ("PUSH s1", "Push GPR[s1] onto stack", "SRC1=GPR", "0x32000000 → PUSH R0"),
    0x33: ("POP dst", "Pop stack into GPR[dst]", "DST=GPR", "0x33000000 → POP R0"),
    0x40: ("HLOAD dst 0 0 imm", "Load letter/entry[imm] from Master Table into H[dst]", "DST=H-reg, IMM=1..28 (31..36 neg)", "0x40000001 → HLOAD H0 ← #1 (ا Alif)"),
    0x42: ("HCADD dst s1 s2", "H[dst] ← H[s1] + H[s2] (18D monoid sum)", "DST, SRC1, SRC2=H-reg", "0x42201000 → HCADD H2 = H0 + H1"),
    0x43: ("CSUB dst s1 s2", "H[dst] ← H[s1] − H[s2] (14D Delta; deferred)", "DST, SRC1, SRC2=H-reg", "0x43201000 → CSUB H2 = H0 − H1"),
    0x44: ("CGET dst s1 imm", "GPR[dst] ← H[s1][imm] (component 0..17)", "DST=GPR, SRC1=H-reg, IMM=0..17", "0x44000000 → CGET R0, H0[0]"),
    0x45: ("CSET dst s1 imm", "H[dst][imm] ← GPR[s1] (component 0..17)", "DST=H-reg, SRC1=GPR, IMM=0..17", "0x45000000 → CSET H0[0], R0"),
    0x46: ("CMOV dst s1", "H[dst] ← H[s1]", "DST, SRC1=H-reg", "0x46100000 → CMOV H1, H0"),
    0x47: ("CZERO dst", "H[dst] ← 0 (monoid identity)", "DST=H-reg", "0x47000000 → CZERO H0"),
    0x48: ("CEQ s1 s2", "FLAGS.Z ← (H[s1] == H[s2])", "SRC1, SRC2=H-reg", "0x48001000 → CEQ H0, H1"),
    0x49: ("CDOT dst s1 s2", "GPR[dst] ← ⟨H[s1], H[s2]⟩₁₄ (software only)", "DST=GPR, SRC1/2=H-reg", "0x49001000 → CDOT R0, H0, H1"),
    0x4A: ("VNORM dst s1", "GPR[dst] ← ‖H[s1]‖² (software alias; RTL: HNRM2)", "DST=GPR, SRC1=H-reg", "0x4A000000 → VNORM R0, H0"),
    0x4B: ("VDIST dst s1 s2", "GPR[dst] ← ‖H[s1]−H[s2]‖² (software; RTL: HDIST)", "DST=GPR, SRC1/2=H-reg", "0x4B001000 → VDIST R0, H0, H1"),
    0x4C: ("CRHO dst s1", "GPR[dst] ← ρ(H[s1]) = Θ̂ − U (signed)", "DST=GPR, SRC1=H-reg", "0x4C000000 → CRHO R0, H0"),
    0x4D: ("CU dst s1", "GPR[dst] ← U(H[s1]) = Qx + Qs + Qa + 4Qc", "DST=GPR, SRC1=H-reg", "0x4D000000 → CU R0, H0"),
    0x4E: ("CTHETA dst s1", "GPR[dst] ← Θ̂(H[s1]) = H[s1][7:0]", "DST=GPR, SRC1=H-reg", "0x4E000000 → CTHETA R0, H0"),
    0x4F: ("CMOD4 dst s1", "GPR[dst] ← Θ̂(H[s1]) mod 4", "DST=GPR, SRC1=H-reg", "0x4F000000 → CMOD4 R0, H0"),
    0x50: ("HPACK dst s1", "Nibble-pack hybit H[s1] into words", "DST, SRC1", "0x50000000 → HPACK R0, H0"),
    0x51: ("HCRC dst s1", "IEEE 802.3 CRC32 over packed frame", "DST, SRC1", "0x51000000 → HCRC R0, R0"),
    0x52: ("HDOT dst s1 s2", "GPR[dst] ← ⟨H[s1], H[s2]⟩₁₄ (20-bit unsigned RTL)", "DST=GPR, SRC1/2=H-reg", "0x52001000 → HDOT R0, H0, H1"),
    0x55: ("HEXMT dst s1", "Build 5×5 Exomatrix from H[s1]", "DST, SRC1=H-reg", "0x55000000 → HEXMT"),
    0x56: ("HDCMP dst s1", "Decompose H[s1] into (U, ρ)", "DST, SRC1=H-reg", "0x56000000 → HDCMP"),
    0x57: ("HSER dst s1", "Serialize H[s1] to HISAB frame", "DST, SRC1", "0x57000000 → HSER"),
    0x58: ("HDES dst s1", "Deserialize HISAB frame into H[dst]", "DST, SRC1", "0x58000000 → HDES"),
    0x59: ("VSCL dst s1 s2", "Scalar multiply H[dst] ← s2 · H[s1]", "DST, SRC1, SRC2", "0x59001000 → VSCL"),
    0x60: ("HGRD 0 s1", "Guard check G1–G4, T1–T2 on H[s1] → GUARD flag", "SRC1=H-reg", "0x60000000 → HGRD H0"),
    0x68: ("HCHK", "Periodic runtime integrity scan (HCHECK)", "No operands", "0x68000000 → HCHK"),
    0x70: ("CHASH dst s1", "Compute SHA-256 digest of H[s1]", "DST, SRC1", "0x70100000 → CHASH H1, H0"),
    0x72: ("CSIGN dst s1", "Cryptographic sign / verify H[s1]", "DST, SRC1", "0x72100000 → CSIGN"),
    0x80: ("HPROJ dst s1 imm", "Project H[s1] onto layer IMM (0:Θ,1:N,2:K,3:Q)", "DST, SRC1, IMM=0..3", "0x80100001 → HPROJ H1, H0, N"),
    0x88: ("VPROJ_T dst s1", "Project H[s1] to Θ̂ subspace", "DST, SRC1=H-reg", "0x88100000 → VPROJ_T H1, H0"),
    0x89: ("VPROJ_N dst s1", "Project H[s1] to Nuqṭah (N) subspace", "DST, SRC1=H-reg", "0x89100000 → VPROJ_N H1, H0"),
    0x8A: ("VPROJ_K dst s1", "Project H[s1] to Khaṭṭ (K) subspace", "DST, SRC1=H-reg", "0x8A100000 → VPROJ_K H1, H0"),
    0x8B: ("VPROJ_Q dst s1", "Project H[s1] to Qaws (Q) subspace", "DST, SRC1=H-reg", "0x8B100000 → VPROJ_Q H1, H0"),
    0xA0: ("PRINT s1", "Emit scalar/register value from GPR[s1]", "SRC1=GPR", "0xA0000000 → PRINT R0"),
    0xA1: ("PRINTH s1", "Print detailed H[s1] breakdown", "SRC1=H-reg", "0xA1000000 → PRINTH H0"),
    0xA2: ("EMITS imm", "Print zero-terminated ASCII string at RAM[imm]", "IMM=word addr", "0xA2000100 → EMITS 256"),
    0xB0: ("AND dst s1 s2", "GPR[dst] ← GPR[s1] & GPR[s2]", "DST, SRC1, SRC2", "0xB0201000 → AND R2, R0, R1"),
    0xB1: ("OR dst s1 s2", "GPR[dst] ← GPR[s1] | GPR[s2]", "DST, SRC1, SRC2", "0xB1201000 → OR R2, R0, R1"),
    0xB2: ("XOR dst s1 s2", "GPR[dst] ← GPR[s1] ^ GPR[s2]", "DST, SRC1, SRC2", "0xB2201000 → XOR R2, R0, R1"),
    0xB3: ("NOT dst s1", "GPR[dst] ← ~GPR[s1]", "DST, SRC1", "0xB3100000 → NOT R1, R0"),
    0xB4: ("SHL dst s1 s2", "GPR[dst] ← GPR[s1] << (GPR[s2] & 31)", "DST, SRC1, SRC2", "0xB4201000 → SHL R2, R0, R1"),
    0xB5: ("SHR dst s1 s2", "GPR[dst] ← GPR[s1] >> (GPR[s2] & 31) (logical)", "DST, SRC1, SRC2", "0xB5201000 → SHR R2, R0, R1"),
    0xB6: ("ANDI dst s1 imm", "GPR[dst] ← GPR[s1] & zext12(imm)", "DST, SRC1, IMM", "0xB60000FF → ANDI R0, R0, 0xFF"),
    0xB7: ("ORI dst s1 imm", "GPR[dst] ← GPR[s1] | zext12(imm)", "DST, SRC1, IMM", "0xB700000F → ORI R0, R0, 0x0F"),
    0xB8: ("XORI dst s1 imm", "GPR[dst] ← GPR[s1] ^ zext12(imm)", "DST, SRC1, IMM", "0xB80000FF → XORI R0, R0, 0xFF"),
    0xB9: ("SHLI dst s1 imm", "GPR[dst] ← GPR[s1] << (imm & 31)", "DST, SRC1, IMM", "0xB9000004 → SHLI R0, R0, 4"),
    0xBA: ("SHRI dst s1 imm", "GPR[dst] ← GPR[s1] >> (imm & 31) (logical)", "DST, SRC1, IMM", "0xBA000004 → SHRI R0, R0, 4"),
    0xFF: ("HALT_ERR", "Halt processor on unimplemented or faulting opcode", "No operands", "0xFF000000 → HALT_ERR"),
}


def _category_for(code: int) -> str:
    for lo, hi, cat in _CATEGORY_RANGES:
        if lo <= code <= hi:
            return cat
    return "Other"


def build_opcode_catalog() -> Dict[int, Dict[str, Any]]:
    """
    Build the canonical opcode catalog directly from ``hisa/opcodes.py``.

    Guarantees zero duplicate counting across aliases and covers all 105 unique
    OpCode values, including the 28 letter instructions (0xE0–0xFB).
    """
    aliases_by_val: Dict[int, List[str]] = {}
    for member_name, member in OpCode.__members__.items():
        if member_name != member.name:
            aliases_by_val.setdefault(int(member.value), []).append(member_name)

    entries_by_idx = {e.index: e for e in MASTER_TABLE.all_entries()}
    catalog: Dict[int, Dict[str, Any]] = {}

    for op in OpCode:
        code = int(op.value)
        rtl = op in RTL_IMPLEMENTED
        aliases = aliases_by_val.get(code, [])

        if 0xE0 <= code <= 0xFB:
            letter_idx = (code - 0xE0) + 1
            entry = entries_by_idx.get(letter_idx)
            char_label = f"{entry.char} ({entry.name})" if entry else f"#{letter_idx}"
            syntax = op.name
            desc = f"H[0] ← H[0] + v₁₈({char_label})  [native letter opcode]"
            fields = "Implicit accumulator H0, no operands"
            example = f"0x{code:02X}000000 → {op.name} ({char_label})"
        elif code in _OP_OVERRIDES:
            syntax, desc, fields, example = _OP_OVERRIDES[code]
        else:
            syntax = f"{op.name} dst s1 s2 imm"
            desc = f"H-ISA opcode {op.name}"
            fields = "Standard 32-bit H-ISA encoding"
            example = f"0x{code:02X}000000 → {op.name}"

        catalog[code] = {
            "code": code,
            "name": op.name,
            "category": _category_for(code),
            "rtl": rtl,
            "aliases": aliases,
            "syntax": syntax,
            "desc": desc,
            "fields": fields,
            "example": example,
        }

    return catalog


def get_opcode_summary() -> Dict[str, Any]:
    """
    Return exact counts derived from ``hisa/opcodes.py`` without double-counting:
      - unique_opcodes: total canonical OpCode values (105)
      - rtl_implemented: canonical opcodes implemented in RTL (84)
      - software_only: canonical opcodes defined in OpCode but not in RTL (21)
      - aliases: alternate enum names pointing to canonical opcodes (17)
      - total_members: total enum members including aliases (122)
      - letter_opcodes: native 0xE0–0xFB letter instructions (28)
    """
    catalog = build_opcode_catalog()
    rtl_count = sum(1 for doc in catalog.values() if doc["rtl"])
    sw_count = sum(1 for doc in catalog.values() if not doc["rtl"])
    aliases = {
        name: member.name
        for name, member in OpCode.__members__.items()
        if name != member.name
    }
    letter_count = sum(1 for code in catalog if 0xE0 <= code <= 0xFB)
    return {
        "unique_opcodes": len(catalog),
        "rtl_implemented": rtl_count,
        "software_only": sw_count,
        "aliases": aliases,
        "alias_count": len(aliases),
        "total_members": len(OpCode.__members__),
        "letter_opcodes": letter_count,
    }


OPCODE_DOCS: Dict[int, Dict[str, Any]] = build_opcode_catalog()


class BytecodeTab:
    """
    Tab: Bytecode Inspector

    Four sections:
      1. DECODE    — type hex → see breakdown
      2. BUILD     — pick opcode + operands → get hex
      3. BATCH     — paste multiple hex words → decode all
      4. REFERENCE — complete H-ISA catalog from opcodes.py
    """

    def __init__(self, notebook: ttk.Notebook) -> None:
        self._tab = ttk.Frame(notebook)
        notebook.add(self._tab, text="  ⬡ Bytecode Inspector  ")

        self._hex_var = tk.StringVar(value="40000001")
        self._result_text: Optional[tk.Text] = None
        self._result_out: Optional[OutputWriter] = None
        self._batch_input: Optional[tk.Text] = None
        self._batch_output: Optional[tk.Text] = None
        self._batch_out: Optional[OutputWriter] = None

        # Builder variables
        self._build_op_var = tk.StringVar(value="HLOAD")
        self._build_dst_var = tk.StringVar(value="0")
        self._build_s1_var = tk.StringVar(value="0")
        self._build_s2_var = tk.StringVar(value="0")
        self._build_imm_var = tk.StringVar(value="1")
        self._build_hex_var = tk.StringVar(value="")
        self._build_asm_var = tk.StringVar(value="")

        self._build()
        self._decode_live()

    def _build(self) -> None:
        """Build the four-tab layout."""
        notebook = ttk.Notebook(self._tab)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 1: Decoder
        decode_tab = ttk.Frame(notebook)
        notebook.add(decode_tab, text="  🔍 Decode Hex  ")
        self._build_decoder(decode_tab)

        # Tab 2: Builder
        build_tab = ttk.Frame(notebook)
        notebook.add(build_tab, text="  🔧 Build Instruction  ")
        self._build_builder(build_tab)

        # Tab 3: Batch
        batch_tab = ttk.Frame(notebook)
        notebook.add(batch_tab, text="  📋 Batch Decode  ")
        self._build_batch(batch_tab)

        # Tab 4: Reference
        ref_tab = ttk.Frame(notebook)
        notebook.add(ref_tab, text="  📖 Opcode Reference  ")
        self._build_reference(ref_tab)

    # ══════════════════════════════════════════════════════════════
    #  SECTION 1 — LIVE HEX DECODER
    # ══════════════════════════════════════════════════════════════

    def _build_decoder(self, parent: ttk.Frame) -> None:
        """Build the hex decoder panel with real-time updates."""

        info = ttk.Frame(parent)
        info.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(
            info,
            text="H-ISA Instruction Word Decoder",
            font=THEME.font_ui_bold,
        ).pack(anchor=tk.W)
        ttk.Label(
            info,
            text=(
                "Type a 32-bit hex value (8 hex digits) below.\n"
                "Format: [OPCODE:8 bits][DST:4][SRC1:4][SRC2:4][IMM:12]\n"
                "Synchronized with src/hijaiyyah/hisa/opcodes.py (105 opcodes, 84 RTL)."
            ),
            foreground=THEME.dim_fg,
        ).pack(anchor=tk.W, pady=(2, 0))

        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(input_frame, text="Hex (32-bit):").pack(side=tk.LEFT)
        ttk.Label(input_frame, text="0x").pack(side=tk.LEFT)

        hex_entry = tk.Entry(
            input_frame,
            textvariable=self._hex_var,
            font=("Consolas", 18, "bold"),
            width=12,
            bg=THEME.text_bg,
            fg=THEME.number_fg,
            insertbackground=THEME.number_fg,
        )
        hex_entry.pack(side=tk.LEFT, padx=5)

        self._hex_var.trace_add("write", lambda *_: self._decode_live())

        examples_frame = ttk.Frame(parent)
        examples_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(examples_frame, text="Examples:").pack(side=tk.LEFT)

        quick_examples = [
            ("HLOAD ا", "40000001"),
            ("HCADD H2=H0+H1", "42201000"),
            ("HGRD H0", "60000000"),
            ("HDIST", "07001000"),
            ("CRHO", "4C000000"),
            ("L_BA (ب)", "E1000000"),
            ("HALT", "01000000"),
        ]
        for label, hex_val in quick_examples:
            ttk.Button(
                examples_frame,
                text=label,
                command=lambda h=hex_val: self._set_hex(h),
            ).pack(side=tk.LEFT, padx=2)

        self._result_text, _ = make_text(parent, font=THEME.font_mono)
        self._result_out = OutputWriter(self._result_text)
        self._result_out.add_tags(
            {
                "header": {"foreground": THEME.hijaiyyah_fg, "font": (*THEME.font_mono, "bold")},
                "value": {"foreground": THEME.number_fg},
                "field": {"foreground": "#ffeaa7"},
                "dim": {"foreground": THEME.dim_fg},
                "pass": {"foreground": THEME.success},
                "error": {"foreground": THEME.error},
                "bit": {"foreground": "#fd79a8", "font": ("Consolas", 12, "bold")},
            }
        )

    def _set_hex(self, hex_val: str) -> None:
        """Set the hex input to a specific value."""
        self._hex_var.set(hex_val)

    def _decode_live(self) -> None:
        """Decode the current hex value and display results in real-time."""
        if self._result_out is None:
            return

        hex_str = self._hex_var.get().strip()
        self._result_out.clear()

        if not hex_str:
            self._result_out.writeln("Enter a hex value above (e.g., 40000001)", "dim")
            return

        try:
            if hex_str.startswith(("0x", "0X")):
                hex_str = hex_str[2:]
            raw = int(hex_str, 16)
        except ValueError:
            self._result_out.writeln(f"Invalid hex: '{hex_str}'", "error")
            self._result_out.writeln("Enter 1-8 hex digits (0-9, A-F)", "dim")
            return

        if raw > 0xFFFFFFFF:
            self._result_out.writeln("Value exceeds 32 bits (max: FFFFFFFF)", "error")
            return

        iw = InstructionWord(raw)

        self._result_out.writeln("INSTRUCTION WORD DECODE", "header")
        self._result_out.writeln("=" * 55)
        self._result_out.writeln()

        self._result_out.writeln(f"  Hex:    0x{raw:08X}", "value")
        self._result_out.writeln(f"  Binary: {raw:032b}", "bit")
        self._result_out.writeln(f"  Dec:    {raw}", "dim")
        self._result_out.writeln()

        self._result_out.writeln("BIT FIELD BREAKDOWN", "header")
        self._result_out.writeln(
            "  ┌────────────┬──────┬──────┬──────┬──────────────┐",
            "dim",
        )
        self._result_out.writeln(
            "  │  OPCODE    │ DST  │ SRC1 │ SRC2 │     IMM      │",
            "dim",
        )
        self._result_out.writeln(
            "  │  bits 31-24│ 23-20│ 19-16│ 15-12│   bits 11-0  │",
            "dim",
        )
        self._result_out.writeln(
            "  ├────────────┼──────┼──────┼──────┼──────────────┤",
            "dim",
        )

        op_bits = f"{iw.opcode:08b}"
        dst_bits = f"{iw.dst:04b}"
        s1_bits = f"{iw.src1:04b}"
        s2_bits = f"{iw.src2:04b}"
        imm_bits = f"{iw.imm:012b}"

        self._result_out.writeln(
            f"  │ {op_bits} │ {dst_bits} │ {s1_bits} │ {s2_bits} │ {imm_bits} │",
            "bit",
        )
        self._result_out.writeln(
            f"  │ 0x{iw.opcode:02X}      │  {iw.dst}   │  {iw.src1}   │  {iw.src2}   │  {iw.imm:<10d} │",
            "value",
        )
        self._result_out.writeln(
            "  └────────────┴──────┴──────┴──────┴──────────────┘",
            "dim",
        )
        self._result_out.writeln()

        self._result_out.writeln("DECODED FIELDS", "header")
        self._result_out.writeln(f"  Opcode:  0x{iw.opcode:02X} ({iw.opcode})", "field")
        self._result_out.writeln(f"  DST:     H{iw.dst} (register {iw.dst})", "field")
        self._result_out.writeln(f"  SRC1:    H{iw.src1} (register {iw.src1})", "field")
        self._result_out.writeln(f"  SRC2:    H{iw.src2} (register {iw.src2})", "field")
        self._result_out.writeln(f"  IMM:     {iw.imm} (0x{iw.imm:03X})", "field")
        self._result_out.writeln()

        self._result_out.writeln("INSTRUCTION MEANING", "header")
        disasm = iw.disassemble()
        self._result_out.writeln(f"  Assembly: {disasm}", "pass")

        doc = OPCODE_DOCS.get(iw.opcode)
        if doc:
            rtl_label = "RTL-IMPLEMENTED (HCPU)" if doc["rtl"] else "SOFTWARE-ONLY (HVM / H-ISA)"
            self._result_out.writeln()
            self._result_out.writeln(f"  Name:     {doc['name']}", "value")
            self._result_out.writeln(f"  Category: {doc['category']}", "dim")
            self._result_out.writeln(f"  Target:   {rtl_label}", "pass" if doc["rtl"] else "field")
            if doc["aliases"]:
                self._result_out.writeln(f"  Aliases:  {', '.join(doc['aliases'])}", "dim")
            self._result_out.writeln(f"  Syntax:   {doc['syntax']}", "dim")
            self._result_out.writeln(f"  Desc:     {doc['desc']}", "dim")
            self._result_out.writeln(f"  Fields:   {doc['fields']}", "dim")

            if iw.opcode == int(OpCode.HLOAD) and iw.imm in _LETTER_NAMES:
                letter_info = _LETTER_NAMES[iw.imm]
                self._result_out.writeln()
                self._result_out.writeln(f"  Letter:   IMM {letter_info}", "pass")
        else:
            self._result_out.writeln("  (Unknown opcode — not defined in OpCode)", "error")

    # ══════════════════════════════════════════════════════════════
    #  SECTION 2 — INSTRUCTION BUILDER
    # ══════════════════════════════════════════════════════════════

    def _build_builder(self, parent: ttk.Frame) -> None:
        """Build the instruction constructor panel."""

        info = ttk.Frame(parent)
        info.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(
            info,
            text="Instruction Builder — Construct H-ISA Words",
            font=THEME.font_ui_bold,
        ).pack(anchor=tk.W)
        ttk.Label(
            info,
            text=(
                "Select any canonical opcode from opcodes.py and set operands below.\n"
                "The hex instruction word is generated automatically."
            ),
            foreground=THEME.dim_fg,
        ).pack(anchor=tk.W, pady=(2, 0))

        op_frame = ttk.Frame(parent)
        op_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(op_frame, text="Opcode:").pack(side=tk.LEFT)
        op_names = [OPCODE_DOCS[code]["name"] for code in sorted(OPCODE_DOCS.keys())]
        op_combo = ttk.Combobox(
            op_frame,
            textvariable=self._build_op_var,
            values=op_names,
            width=16,
            state="readonly",
        )
        op_combo.pack(side=tk.LEFT, padx=5)
        op_combo.bind("<<ComboboxSelected>>", lambda _: self._update_builder())

        operand_frame = ttk.Frame(parent)
        operand_frame.pack(fill=tk.X, padx=10, pady=5)

        for label, var, hint in [
            ("DST (0-15):", self._build_dst_var, "Target register"),
            ("SRC1 (0-15):", self._build_s1_var, "First source"),
            ("SRC2 (0-15):", self._build_s2_var, "Second source"),
            ("IMM (0-4095):", self._build_imm_var, "Immediate value"),
        ]:
            col = ttk.Frame(operand_frame)
            col.pack(side=tk.LEFT, padx=5)
            ttk.Label(col, text=label).pack(anchor=tk.W)
            entry = tk.Entry(
                col,
                textvariable=var,
                width=6,
                font=("Consolas", 12),
                bg=THEME.text_bg,
                fg=THEME.number_fg,
            )
            entry.pack()
            ttk.Label(col, text=hint, foreground=THEME.dim_fg).pack(anchor=tk.W)
            var.trace_add("write", lambda *_: self._update_builder())

        letter_frame = ttk.Frame(parent)
        letter_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(letter_frame, text="Quick letter (for HLOAD IMM):").pack(side=tk.LEFT)

        entries = MASTER_TABLE.all_entries()
        # IMM is the 1-based letter index the ROM and HLOAD use, so the button
        # passes letter.index rather than its position in the list.
        for i, letter in enumerate(entries):
            if i >= 14:
                break
            ttk.Button(
                letter_frame,
                text=letter.char,
                width=2,
                command=lambda idx=letter.index: self._set_imm_letter(idx),
            ).pack(side=tk.LEFT, padx=1)

        letter_frame2 = ttk.Frame(parent)
        letter_frame2.pack(fill=tk.X, padx=10, pady=(0, 5))
        for i, letter in enumerate(entries):
            if i < 14:
                continue
            ttk.Button(
                letter_frame2,
                text=letter.char,
                width=2,
                command=lambda idx=letter.index: self._set_imm_letter(idx),
            ).pack(side=tk.LEFT, padx=1)

        result_frame = ttk.Frame(parent)
        result_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(result_frame, text="Result:", font=THEME.font_ui_bold).pack(anchor=tk.W)

        hex_frame = ttk.Frame(result_frame)
        hex_frame.pack(fill=tk.X, pady=5)

        ttk.Label(hex_frame, text="Hex:").pack(side=tk.LEFT)
        hex_result = tk.Entry(
            hex_frame,
            textvariable=self._build_hex_var,
            font=("Consolas", 18, "bold"),
            width=12,
            bg=THEME.text_bg,
            fg=THEME.number_fg,
            state="readonly",
        )
        hex_result.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            hex_frame,
            text="📋 Copy Hex",
            command=lambda: self._copy_to_clipboard(self._build_hex_var.get()),
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            hex_frame,
            text="→ Send to Decoder",
            command=lambda: self._hex_var.set(self._build_hex_var.get().replace("0x", "")),
        ).pack(side=tk.LEFT, padx=5)

        asm_frame = ttk.Frame(result_frame)
        asm_frame.pack(fill=tk.X)
        ttk.Label(asm_frame, text="ASM:").pack(side=tk.LEFT)
        tk.Entry(
            asm_frame,
            textvariable=self._build_asm_var,
            font=("Consolas", 14),
            width=36,
            bg=THEME.text_bg,
            fg="#81ecec",
            state="readonly",
        ).pack(side=tk.LEFT, padx=5)

        self._update_builder()

    def _set_imm_letter(self, idx: int) -> None:
        """Set IMM to a 1-based letter index and switch the opcode to HLOAD."""
        self._build_op_var.set("HLOAD")
        self._build_imm_var.set(str(idx))
        self._update_builder()

    def _update_builder(self) -> None:
        """Recompute the instruction word from builder inputs."""
        op_name = self._build_op_var.get()

        op_val = 0
        for code, doc in OPCODE_DOCS.items():
            if doc["name"] == op_name:
                op_val = code
                break

        try:
            dst = int(self._build_dst_var.get()) & 0xF
        except ValueError:
            dst = 0
        try:
            s1 = int(self._build_s1_var.get()) & 0xF
        except ValueError:
            s1 = 0
        try:
            s2 = int(self._build_s2_var.get()) & 0xF
        except ValueError:
            s2 = 0
        try:
            imm = int(self._build_imm_var.get()) & 0xFFF
        except ValueError:
            imm = 0

        word = (op_val << 24) | (dst << 20) | (s1 << 16) | (s2 << 12) | imm
        self._build_hex_var.set(f"0x{word:08X}")

        rtl_tag = "RTL" if is_rtl_implemented(op_val) else "SW-ONLY"
        asm = f"{op_name} {dst} {s1} {s2} {imm}"
        if op_val == int(OpCode.HLOAD) and imm in _LETTER_NAMES:
            asm += f"  ; {_LETTER_NAMES[imm]} [{rtl_tag}]"
        else:
            asm += f"  ; [{rtl_tag}]"
        self._build_asm_var.set(asm)

    # ══════════════════════════════════════════════════════════════
    #  SECTION 3 — BATCH DECODE
    # ══════════════════════════════════════════════════════════════

    def _build_batch(self, parent: ttk.Frame) -> None:
        """Build the batch decode panel."""

        info = ttk.Frame(parent)
        info.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(
            info,
            text="Batch Decode — Paste Multiple Hex Words",
            font=THEME.font_ui_bold,
        ).pack(anchor=tk.W)
        ttk.Label(
            info,
            text="Paste one hex value per line (e.g., program dump from H-ISA machine).",
            foreground=THEME.dim_fg,
        ).pack(anchor=tk.W)

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        left = ttk.Frame(paned)
        paned.add(left, weight=1)
        ttk.Label(left, text="Hex Input (one per line):").pack(anchor=tk.W)
        self._batch_input = tk.Text(
            left,
            font=THEME.font_mono,
            bg=THEME.text_bg,
            fg=THEME.number_fg,
            insertbackground=THEME.number_fg,
            height=15,
            width=15,
        )
        self._batch_input.pack(fill=tk.BOTH, expand=True)
        self._batch_input.insert(
            "1.0", "40000001\n40100002\n42201000\n60020000\nA0020000\n01000000"
        )

        btn = ttk.Frame(left)
        btn.pack(fill=tk.X, pady=5)
        ttk.Button(btn, text="▶ Decode All", command=self._batch_decode).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="Clear", command=self._batch_clear).pack(side=tk.LEFT, padx=2)

        right = ttk.Frame(paned)
        paned.add(right, weight=2)
        ttk.Label(right, text="Decoded Output:").pack(anchor=tk.W)
        self._batch_output, _ = make_text(right, font=THEME.font_mono_sm)
        self._batch_out = OutputWriter(self._batch_output)
        self._batch_out.add_tags(
            {
                "addr": {"foreground": THEME.dim_fg},
                "hex": {"foreground": THEME.number_fg},
                "asm": {"foreground": "#81ecec"},
                "desc": {"foreground": THEME.fg},
                "pass": {"foreground": THEME.success},
                "error": {"foreground": THEME.error},
            }
        )

    def _batch_decode(self) -> None:
        """Decode all hex values from batch input."""
        if self._batch_input is None or self._batch_out is None:
            return

        text = self._batch_input.get("1.0", tk.END).strip()
        if not text:
            return

        self._batch_out.clear()
        self._batch_out.writeln("BATCH DECODE", "pass")
        self._batch_out.writeln(
            f"{'Addr':<6} {'Hex':<12} {'RTL':<8} {'Assembly':<35} {'Description'}",
            "addr",
        )
        self._batch_out.writeln("-" * 92, "addr")

        for i, line in enumerate(text.split("\n")):
            line = line.strip()
            if not line:
                continue

            try:
                clean = line.replace("0x", "").replace("0X", "")
                raw = int(clean, 16)
                iw = InstructionWord(raw)
                disasm = iw.disassemble()

                doc = OPCODE_DOCS.get(iw.opcode)
                desc = doc["desc"] if doc else "Unknown"
                rtl_col = "RTL" if (doc and doc["rtl"]) else ("SW-ONLY" if doc else "UNKNOWN")

                extra = ""
                if iw.opcode == int(OpCode.HLOAD) and iw.imm in _LETTER_NAMES:
                    extra = f" [{_LETTER_NAMES[iw.imm]}]"

                self._batch_out.writeln(
                    f"  {i:04d}  0x{raw:08X}  {rtl_col:<7s}  {disasm:<33s}  {desc}{extra}",
                    "asm",
                )
            except ValueError:
                self._batch_out.writeln(f"  {i:04d}  {line:<12s}  ERROR: invalid hex", "error")

        self._batch_out.writeln()
        self._batch_out.writeln("Decode complete.", "pass")

    def _batch_clear(self) -> None:
        if self._batch_input is not None:
            self._batch_input.delete("1.0", tk.END)
        if self._batch_out is not None:
            self._batch_out.clear()

    # ══════════════════════════════════════════════════════════════
    #  SECTION 4 — OPCODE REFERENCE
    # ══════════════════════════════════════════════════════════════

    def _build_reference(self, parent: ttk.Frame) -> None:
        """Build the complete opcode reference table from opcodes.py."""
        summary = get_opcode_summary()

        ttk.Label(
            parent,
            text="H-ISA Opcode Reference — Synchronized with hisa/opcodes.py",
            font=THEME.font_ui_bold,
        ).pack(anchor=tk.W, padx=10, pady=(10, 5))

        ttk.Label(
            parent,
            text=(
                "Instruction word format: [OPCODE: 8 | DST: 4 | SRC1: 4 | SRC2: 4 | IMM: 12]\n"
                f"Unique OpCode: {summary['unique_opcodes']}  │  "
                f"RTL Implemented: {summary['rtl_implemented']}  │  "
                f"Software-Only (not in RTL): {summary['software_only']}  │  "
                f"Aliases: {summary['alias_count']} (Total enum members: {summary['total_members']})"
            ),
            foreground=THEME.dim_fg,
        ).pack(anchor=tk.W, padx=10)

        ref_text, _ = make_text(parent, font=THEME.font_mono_sm, wrap=tk.NONE)
        ref_out = OutputWriter(ref_text)
        ref_out.add_tags(
            {
                "header": {"foreground": THEME.hijaiyyah_fg, "font": (*THEME.font_mono, "bold")},
                "value": {"foreground": THEME.number_fg},
                "sw": {"foreground": "#ffeaa7"},
                "dim": {"foreground": THEME.dim_fg},
            }
        )

        ref_out.writeln("OPCODE SUMMARY COUNTS", "header")
        ref_out.writeln("=" * 85, "dim")
        ref_out.writeln(f"  1. Unique OpCode entries:               {summary['unique_opcodes']}", "value")
        ref_out.writeln(f"  2. RTL-implemented (RTL_IMPLEMENTED):   {summary['rtl_implemented']} (incl. {summary['letter_opcodes']} letter opcodes 0xE0–0xFB)", "value")
        ref_out.writeln(f"  3. Defined but software-only (no RTL):  {summary['software_only']}", "sw")
        ref_out.writeln(f"  4. Source-compatibility aliases:        {summary['alias_count']}", "dim")
        ref_out.writeln()

        ref_out.writeln(
            f"{'Hex':<6} {'Status':<9} {'Name':<11} {'Syntax':<22} {'Description'}",
            "header",
        )
        ref_out.writeln("=" * 95, "dim")

        for code in sorted(OPCODE_DOCS.keys()):
            doc = OPCODE_DOCS[code]
            status = "RTL" if doc["rtl"] else "SW-ONLY"
            tag = "value" if doc["rtl"] else "sw"
            ref_out.writeln(
                f"0x{code:02X}   {status:<9} {doc['name']:<11} {doc['syntax']:<22} {doc['desc']}",
                tag,
            )
            if doc["aliases"]:
                ref_out.writeln(f"       Aliases: {', '.join(doc['aliases'])}", "dim")

        ref_out.writeln()
        ref_out.writeln("REGISTER LAYOUT", "header")
        ref_out.writeln("=" * 50, "dim")
        ref_out.writeln("  H0–H15: Codex registers (18 × uint8 each)", "value")
        ref_out.writeln("  R0–R15: 16 general purpose registers (32-bit)", "value")
        ref_out.writeln("  FLAGS:  Status flags (Z, N, C, GUARD_PASS)", "value")
        ref_out.writeln()
        ref_out.writeln("LETTER INDEX TABLE (for HLOAD IMM field, 1-based)", "header")
        ref_out.writeln("=" * 50, "dim")
        for idx, name in sorted(_LETTER_NAMES.items()):
            ref_out.writeln(f"  IMM={idx:<3d} → {name}", "value")

    # ── Utility ──────────────────────────────────────────────────

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to system clipboard."""
        self._tab.clipboard_clear()
        self._tab.clipboard_append(text)
