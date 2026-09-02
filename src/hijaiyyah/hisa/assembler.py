# -*- coding: utf-8 -*-
"""The H-ISA assembler: one dialect, one operand table.

H-ISA had three assemblers, and they did not read the same language.

``rtl/scripts/asm2hex.py`` — the one that feeds silicon — takes the dialect the
book writes: register names, comma-separated operands, ``#`` immediates, hex,
and labels. ``hisa/assembler.py`` and ``assembler/__init__.py`` took bare
space-separated integers and rejected every one of those forms. A ``.hasm``
file that assembled for the FPGA could not be assembled by the package at all,
which makes the parity gate the whole toolchain is built around impossible:
the same program has to reach HVM and HCPU before anything can compare them.

Two silent failures came with the split. This module's predecessor looked up
mnemonics with ``_OP_MAP.get(mnemonic, 0)``, so a typo assembled to NOP —
opcode ``0x00`` — and ran. And ``asm2hex.py``'s if-chain had no branch for
HPACK or HCRC, so ``HPACK R3, H1, R2`` fell through to a bare opcode and
became ``0x50000000``: every operand dropped, reading H0 and writing R0.

The fix in both cases is the same shape: operand layouts are data here, not
control flow. :data:`OPERANDS` names the fields each mnemonic takes, every
opcode in the frozen set has an entry, and a missing one is an error rather
than a default. Adding an opcode without a layout fails the tests.

Syntax, per Bab III §IIIM.3.1:

.. code-block:: text

    ; komentar
    main:
            HLOAD   H0, #2          ; letter index, 1-based
            HGRD    H0
            HNRM2   R1, H0
            JNGD    fail            ; PC-relative, resolved from the label
            PRINT   R1
    fail:   HALT

Registers are ``R0``–``R17`` and ``H0``–``H15``; ``_`` means "unused". A bare
integer is accepted where a register is expected, which is what the older
dialect wrote, so existing files keep assembling.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from hijaiyyah.core.exceptions import HijaiyyahError

from .opcodes import RTL_IMPLEMENTED, OpCode

#: Highest general-purpose register index (R0–R17, §IIIJ.3.3.1).
MAX_GPR = 17

#: Highest hybit register index (H0–H15, §IIIJ.3.3.2).
MAX_HREG = 15

#: Immediate field width in bits (§IIIJ.3.2.1).
IMM_BITS = 12


class AssemblyError(HijaiyyahError):
    """Raised for any line the assembler cannot encode exactly."""

    def __init__(self, message: str, line_number: Optional[int] = None) -> None:
        self.line_number = line_number
        super().__init__(
            message if line_number is None else f"line {line_number}: {message}"
        )


# ── Operand layouts ──────────────────────────────────────────────
#
# Field names in the order they are written in source. "dst", "s1" and "s2"
# are register slots; "imm" is the 12-bit immediate; "bimm" is an immediate
# that a label resolves to PC-relative rather than absolute.

OPERANDS: Dict[str, Tuple[str, ...]] = {
    "NOP":      (),
    "HALT":     (),
    "ERET":     (),
    "HALT_ERR": (),
    "MOV":      ("dst", "s1"),
    "MOVI":     ("dst", "imm"),
    "ADD":      ("dst", "s1", "s2?"),
    "ADDI":     ("dst", "s1", "imm"),
    "SUB":      ("dst", "s1", "s2?"),
    "MUL":      ("dst", "s1", "s2?"),
    "AND":      ("dst", "s1", "s2?"),
    "OR":       ("dst", "s1", "s2?"),
    "XOR":      ("dst", "s1", "s2?"),
    "NOT":      ("dst", "s1"),
    "SHL":      ("dst", "s1", "s2?"),
    "SHR":      ("dst", "s1", "s2?"),
    "ANDI":     ("dst", "s1", "imm"),
    "ORI":      ("dst", "s1", "imm"),
    "XORI":     ("dst", "s1", "imm"),
    "SHLI":     ("dst", "s1", "imm"),
    "SHRI":     ("dst", "s1", "imm"),
    "CMP":      ("s1", "s2"),
    "CMPI":     ("s1", "imm"),
    "JMP":      ("imm",),
    "JEQ":      ("bimm",),
    "JNE":      ("bimm",),
    "JGD":      ("bimm",),
    "JNGD":     ("bimm",),
    "LOAD":     ("dst", "s1", "imm?"),
    "STORE":    ("s1", "s2", "imm?"),
    "PUSH":     ("s1",),
    "POP":      ("dst",),
    "HLOAD":    ("dst", "immreg"),
    "CGET":     ("dst", "s1", "imm"),
    "HCADD":    ("dst", "s1", "s2"),
    "HNRM2":    ("dst", "s1"),
    "HDIST":    ("dst", "s1", "s2"),
    "HPACK":    ("dst", "s1", "s2?"),
    "HCRC":     ("dst", "s1"),
    "HGRD":     ("s1",),
    "PRINT":    ("s1",),
}

#: A layout entry ending in "?" may be omitted, defaulting to zero.
#: "immreg" accepts either an immediate or a register — HLOAD takes a literal
#: letter index or, for dynamic indexing, a register holding one.

_MNEMONICS: Dict[str, OpCode] = {op.name: op for op in RTL_IMPLEMENTED}

_LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*")
_SPLIT_RE = re.compile(r"[,\s]+")


# ── Operand parsing ──────────────────────────────────────────────

def parse_register(text: str) -> int:
    """Parse ``R0``–``R17``, ``H0``–``H15``, ``_``, or a bare index.

    Args:
        text: One operand as written in the source.

    Returns:
        The 4-bit register index.

    Raises:
        AssemblyError: If the name is malformed or the index is out of range.
    """
    token = text.strip().upper()
    if token in ("", "_"):
        return 0

    if token[0] in "RH" and token[1:].isdigit():
        index = int(token[1:])
        limit = MAX_GPR if token[0] == "R" else MAX_HREG
        if index > limit:
            raise AssemblyError(
                f"register {token} is out of range (max {token[0]}{limit})"
            )
        return index & 0xF

    if token.lstrip("-").isdigit():
        index = int(token)
        if not 0 <= index <= MAX_GPR:
            raise AssemblyError(f"register index {index} is out of range 0..{MAX_GPR}")
        return index

    raise AssemblyError(f"'{text}' is not a register")


def parse_immediate(
    text: str,
    labels: Optional[Dict[str, int]] = None,
    address: int = 0,
    pc_relative: bool = False,
) -> int:
    """Parse a decimal, ``#``-prefixed, hex, or label immediate.

    Args:
        text: The operand as written.
        labels: Label table from the first pass, if any.
        address: Address of the instruction being assembled.
        pc_relative: True for branches, whose labels resolve to an offset.

    Returns:
        The value masked into the 12-bit immediate field.

    Raises:
        AssemblyError: If the token is neither a number nor a known label.
    """
    token = text.strip().lstrip("#")
    labels = labels or {}

    if token in labels:
        target = labels[token]
        value = target - address if pc_relative else target
    else:
        try:
            value = int(token, 16) if token.lower().startswith("0x") else int(token, 10)
        except ValueError:
            raise AssemblyError(f"'{text}' is neither a number nor a known label") from None

    if not -(1 << (IMM_BITS - 1)) <= value < (1 << IMM_BITS):
        raise AssemblyError(f"immediate {value} does not fit {IMM_BITS} bits")
    return value & ((1 << IMM_BITS) - 1)


def encode(op: int, dst: int = 0, s1: int = 0, s2: int = 0, imm: int = 0) -> int:
    """Pack one instruction word: ``{op[31:24], dst, s1, s2, imm[11:0]}``."""
    return (
        ((op & 0xFF) << 24)
        | ((dst & 0xF) << 20)
        | ((s1 & 0xF) << 16)
        | ((s2 & 0xF) << 12)
        | (imm & 0xFFF)
    )


# ── Lines and programs ───────────────────────────────────────────

def _strip(line: str) -> str:
    """Remove a comment and any leading label definition."""
    text = line.split(";")[0].strip()
    match = _LABEL_RE.match(text)
    return text[match.end():].strip() if match else text


def assemble_line(
    line: str,
    labels: Optional[Dict[str, int]] = None,
    address: int = 0,
) -> Optional[int]:
    """Assemble one line into a 32-bit word.

    Args:
        line: Source line, which may carry a label, a comment, or both.
        labels: Label table from the first pass.
        address: Address this instruction will occupy.

    Returns:
        The instruction word, or None for a line that holds no instruction.

    Raises:
        AssemblyError: On an unknown mnemonic, a bad operand, or the wrong
            number of operands. Nothing is silently defaulted.
    """
    text = _strip(line)
    if not text:
        return None

    parts = [p for p in _SPLIT_RE.split(text) if p]
    mnemonic = parts[0].upper()

    if mnemonic not in _MNEMONICS:
        raise AssemblyError(f"unknown mnemonic '{parts[0]}'")
    if mnemonic not in OPERANDS:
        raise AssemblyError(f"'{mnemonic}' has no operand layout")

    fields = OPERANDS[mnemonic]
    given = parts[1:]

    required = sum(1 for f in fields if not f.endswith("?"))
    if not required <= len(given) <= len(fields):
        shape = " ".join(fields) if fields else "(none)"
        raise AssemblyError(
            f"{mnemonic} takes {shape}, got {len(given)} operand(s)"
        )

    slots = {"dst": 0, "s1": 0, "s2": 0, "imm": 0}
    # Shorter than fields when an optional tail operand is omitted.
    for field, raw in zip(fields, given, strict=False):
        kind = field.rstrip("?")
        if kind in ("dst", "s1", "s2"):
            slots[kind] = parse_register(raw)
        elif kind == "immreg":
            # HLOAD takes a literal letter index, or a register holding one.
            try:
                slots["imm"] = parse_immediate(raw, labels, address)
            except AssemblyError:
                slots["s1"] = parse_register(raw)
        else:
            slots["imm"] = parse_immediate(
                raw, labels, address, pc_relative=(kind == "bimm")
            )

    return encode(
        int(_MNEMONICS[mnemonic].value),
        slots["dst"], slots["s1"], slots["s2"], slots["imm"],
    )


def collect_labels(lines: Sequence[str]) -> Dict[str, int]:
    """First pass: map each label to the address of the next instruction."""
    labels: Dict[str, int] = {}
    address = 0
    for line in lines:
        text = line.split(";")[0].strip()
        match = _LABEL_RE.match(text)
        if match:
            name = match.group(1)
            if name in labels:
                raise AssemblyError(f"label '{name}' is defined twice")
            labels[name] = address
            text = text[match.end():].strip()
        if text:
            address += 1
    return labels


def assemble(source: str) -> List[int]:
    """Assemble a whole program into instruction words.

    Args:
        source: The ``.hasm`` text.

    Returns:
        One 32-bit word per instruction, in address order.

    Raises:
        AssemblyError: Carrying the source line number of the first problem.
    """
    lines = source.splitlines()
    labels = collect_labels(lines)

    words: List[int] = []
    for number, line in enumerate(lines, start=1):
        try:
            word = assemble_line(line, labels, len(words))
        except AssemblyError as exc:
            raise AssemblyError(str(exc), line_number=number) from None
        if word is not None:
            words.append(word)
    return words
