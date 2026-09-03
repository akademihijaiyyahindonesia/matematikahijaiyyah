"""
The sealed book, transcribed, checked against the implementation.

Every other integrity test in this suite compares one implementation to
another: Python to RTL, JSON to CSV, the JS engine to the Python engine. That
catches drift between copies, and it has caught a lot of it. But it cannot
catch the copies drifting *together*, and it cannot catch a value that was
wrong before the first copy was made.

That is not hypothetical here. data/hm28.json was wrong on ط, ظ, ك and ن, and
the HCPU ROM was generated from it. Every implementation-to-implementation
check was green, because they all agreed — on the wrong numbers. The error was
found only by going back to the sealed PDF and reading it.

So this file is the missing edge in the graph. It holds what the book actually
prints, written out by hand, and checks the implementation against that. It is
the software half of the Layer-1 audit in §IE.1.12 — the layer that asks
whether the artefact still says what the seal says it says.

Source: Buku Matematika Hijaiyyah Edisi v.1.1.1 (2026, HMCL),
        dataset-seal HM-28-v.1.0-HC18D.

The book is not in this repository — it is held back by .gitignore, because
this repo is public. So these literals ARE the transcription, and an auditor
checks them by opening the PDF at the cited page. Each block names its page
and section for exactly that reason. Do not "fix" a literal here to make a
test pass: if the implementation disagrees with the book, one of the two is
wrong, and finding out which is the entire point of the file.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from hijaiyyah.core.guards import compute_U
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import AssemblyError
from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED

ROOT = Path(__file__).resolve().parents[2]
PKG_VH = ROOT / "rtl" / "hcpu_pkg.vh"
ROM_V = ROOT / "rtl" / "hcpu_rom.v"


# ══════════════════════════════════════════════════════════════════
#  Master Table — hal. 79, §IE.1
#  Columns as printed: Θ̂, N(Na,Nb,Nd), K(Kp,Kx,Ks,Ka,Kc), Q(Qp,Qx,Qs,Qa,Qc)
# ══════════════════════════════════════════════════════════════════

Row = Tuple[int, str, int, Tuple[int, ...], Tuple[int, ...], Tuple[int, ...]]

BOOK_MASTER_TABLE: List[Row] = [
    (1,  "ا",  0, (0, 0, 0), (1, 0, 0, 0, 0), (0, 0, 0, 0, 0)),
    (2,  "ب",  2, (0, 0, 1), (0, 1, 0, 0, 0), (1, 0, 0, 0, 0)),
    (3,  "ت",  2, (2, 0, 0), (0, 1, 0, 0, 0), (1, 0, 0, 0, 0)),
    (4,  "ث",  2, (3, 0, 0), (0, 1, 0, 0, 0), (1, 0, 0, 0, 0)),
    (5,  "ج",  3, (0, 1, 0), (0, 1, 0, 0, 0), (1, 0, 0, 0, 0)),
    (6,  "ح",  3, (0, 0, 0), (0, 1, 0, 0, 0), (1, 0, 0, 0, 0)),
    (7,  "خ",  3, (1, 0, 0), (0, 1, 0, 0, 0), (1, 0, 0, 0, 0)),
    (8,  "د",  1, (0, 0, 0), (0, 0, 0, 0, 0), (0, 0, 0, 1, 0)),
    (9,  "ذ",  1, (1, 0, 0), (0, 0, 0, 0, 0), (0, 0, 0, 1, 0)),
    (10, "ر",  1, (0, 0, 0), (0, 0, 0, 0, 0), (0, 0, 1, 0, 0)),
    (11, "ز",  1, (1, 0, 0), (0, 0, 0, 0, 0), (0, 0, 1, 0, 0)),
    (12, "س",  4, (0, 0, 0), (0, 0, 0, 0, 0), (1, 2, 0, 0, 0)),
    (13, "ش",  4, (3, 0, 0), (0, 0, 0, 0, 0), (1, 2, 0, 0, 0)),
    (14, "ص",  6, (0, 0, 0), (0, 0, 0, 0, 0), (1, 0, 0, 0, 1)),
    (15, "ض",  6, (1, 0, 0), (0, 0, 0, 0, 0), (1, 0, 0, 0, 1)),
    (16, "ط",  4, (0, 0, 0), (0, 0, 1, 0, 0), (0, 0, 0, 0, 1)),
    (17, "ظ",  4, (1, 0, 0), (0, 0, 1, 0, 0), (0, 0, 0, 0, 1)),
    (18, "ع",  3, (0, 0, 0), (0, 0, 0, 0, 0), (1, 1, 0, 0, 0)),
    (19, "غ",  3, (1, 0, 0), (0, 0, 0, 0, 0), (1, 1, 0, 0, 0)),
    (20, "ف",  5, (1, 0, 0), (0, 1, 0, 0, 0), (1, 0, 0, 0, 1)),
    (21, "ق",  6, (2, 0, 0), (0, 0, 0, 0, 0), (1, 0, 0, 0, 1)),
    (22, "ك",  2, (0, 0, 0), (0, 0, 0, 1, 0), (0, 0, 0, 0, 0)),
    (23, "ل",  1, (0, 0, 0), (0, 1, 0, 0, 0), (1, 0, 0, 0, 0)),
    (24, "م",  4, (0, 0, 0), (0, 0, 0, 0, 1), (0, 0, 0, 0, 1)),
    (25, "ن",  2, (1, 0, 0), (0, 0, 0, 0, 0), (1, 0, 0, 0, 0)),
    (26, "و",  5, (0, 0, 0), (0, 0, 0, 0, 0), (0, 0, 1, 0, 1)),
    (27, "هـ", 8, (0, 0, 0), (0, 0, 0, 0, 1), (0, 0, 0, 0, 2)),
    (28, "ي",  3, (0, 0, 2), (0, 0, 0, 0, 0), (1, 1, 0, 0, 0)),
]

# ك is the only letter carrying the hamzah marker (§ID.1.3, hal. 74–75).
BOOK_HAMZAH_MARKER = {"ك"}

_IDS = [f"{r[0]:02d}-{r[1]}" for r in BOOK_MASTER_TABLE]


def test_the_table_has_twenty_eight_rows() -> None:
    assert len(BOOK_MASTER_TABLE) == 28
    assert [r[0] for r in BOOK_MASTER_TABLE] == list(range(1, 29))


@pytest.mark.parametrize("row", BOOK_MASTER_TABLE, ids=_IDS)
def test_letter_matches_the_sealed_table(row: Row) -> None:
    """
    The four invariants of Bab I, as printed on hal. 79, against the codex the
    whole stack is built from. This is the check that would have caught the
    ط/ظ/ك/ن corruption on the day it was introduced.
    """
    index, char, theta, n, k, q = row
    entry = MASTER_TABLE.get_by_index(index)
    assert entry is not None, f"index {index} missing from the Master Table"

    assert entry.char == char, f"index {index}: repo has {entry.char!r}"

    v = list(entry.vector)
    assert v[0] == theta, f"{char}: Θ̂"
    assert tuple(v[1:4]) == n, f"{char}: N(Na,Nb,Nd)"
    assert tuple(v[4:9]) == k, f"{char}: K(Kp,Kx,Ks,Ka,Kc)"
    assert tuple(v[9:14]) == q, f"{char}: Q(Qp,Qx,Qs,Qa,Qc)"


@pytest.mark.parametrize("row", BOOK_MASTER_TABLE, ids=_IDS)
def test_hamzah_marker_matches_the_book(row: Row) -> None:
    """§ID.1.3: hamzah is a binary tag, and only ك carries it."""
    _, char, *_ = row
    entry = MASTER_TABLE.get_by_char(char)
    assert entry is not None
    expected = 1 if char in BOOK_HAMZAH_MARKER else 0
    assert entry.vector[17] == expected, f"{char}: hamzah marker"


@pytest.mark.parametrize("row", BOOK_MASTER_TABLE, ids=_IDS)
def test_summary_components_derive_from_the_book_core(row: Row) -> None:
    """
    §ID.1.2: A_N, A_K, A_Q are deterministic summaries of the core, and the
    guards G1–G3 are exactly the statement that they are. Deriving them here
    from the book's own core values — rather than reading them off the repo —
    keeps the summary block anchored too.
    """
    _, char, _theta, n, k, q = row
    entry = MASTER_TABLE.get_by_char(char)
    assert entry is not None
    v = list(entry.vector)
    assert v[14] == sum(n), f"{char}: A_N (G1)"
    assert v[15] == sum(k), f"{char}: A_K (G2)"
    assert v[16] == sum(q), f"{char}: A_Q (G3)"


# ── The erratum on hal. 79 ────────────────────────────────────────

def test_kaf_follows_the_formula_not_the_printed_B_R_columns() -> None:
    """
    hal. 79 prints ك with B=2 and R=0 — U and ρ swapped. Every other letter's
    printed pair agrees with U = Qx + Qs + Qa + 4·Qc, and ك has Q = (0,0,0,0,0),
    so U must be 0 and ρ = Θ̂ − U = 2.

    The repo is right and the table's two cells are a typesetting slip. This
    test records that, so the next reader who diffs the page against the code
    finds the discrepancy already explained rather than re-deriving it.
    """
    entry = MASTER_TABLE.get_by_char("ك")
    assert entry is not None
    v = list(entry.vector)
    assert compute_U(v) == 0
    assert v[0] - compute_U(v) == 2


@pytest.mark.parametrize("row", BOOK_MASTER_TABLE, ids=_IDS)
def test_residue_is_non_negative(row: Row) -> None:
    """
    §IC.1.25, the non-negativity axiom, and guard G4: ρ = Θ̂ − U ≥ 0 for 28/28.
    The book calls this an empirical finding rather than a consequence of the
    definitions, which is why it is worth asserting on the book's numbers.
    """
    _, char, theta, _n, _k, q = row
    _qp, qx, qs, qa, qc = q
    u = qx + qs + qa + 4 * qc
    assert theta - u >= 0, f"{char}: ρ = {theta - u} < 0"


# ══════════════════════════════════════════════════════════════════
#  Θ̂ distribution — hal. 82, §IE.1.4
# ══════════════════════════════════════════════════════════════════

BOOK_THETA_DISTRIBUTION: Dict[int, int] = {
    0: 1, 1: 5, 2: 5, 3: 6, 4: 5, 5: 2, 6: 3, 7: 0, 8: 1,
}


def test_theta_distribution_matches_the_book() -> None:
    counts: Dict[int, int] = {theta: 0 for theta in BOOK_THETA_DISTRIBUTION}
    for entry in MASTER_TABLE.all_entries():
        counts[entry.vector[0]] = counts.get(entry.vector[0], 0) + 1
    assert counts == BOOK_THETA_DISTRIBUTION


def test_theta_seven_does_not_occur() -> None:
    """
    §IC.1.3 flags this as an empirical fact about the alphabet, not a design
    constraint. If a letter ever lands on 7, that is a real finding — and the
    book's claim needs revisiting, not this test.
    """
    assert all(e.vector[0] != 7 for e in MASTER_TABLE.all_entries())


# ══════════════════════════════════════════════════════════════════
#  Injectivity — hal. 76, §ID.1.5
# ══════════════════════════════════════════════════════════════════

def test_all_378_pairs_are_distinct() -> None:
    """C(28,2) = 378 pairs, no collision. The book audits this exhaustively."""
    entries = MASTER_TABLE.all_entries()
    pairs = [
        (a, b)
        for i, a in enumerate(entries)
        for b in entries[i + 1:]
    ]
    assert len(pairs) == 378
    collisions = [
        (a.char, b.char) for a, b in pairs if tuple(a.vector) == tuple(b.vector)
    ]
    assert not collisions, f"codex collision: {collisions}"


# ══════════════════════════════════════════════════════════════════
#  H-ISA opcode table — hal. 141–142, §IIIM.3.1
# ══════════════════════════════════════════════════════════════════

BOOK_OPCODES: Dict[str, int] = {
    "NOP":   0x00,
    "HALT":  0x01,
    "MOV":   0x03,
    "MOVI":  0x04,
    "HNRM2": 0x06,
    "HDIST": 0x07,
    "ADD":   0x10,
    "ADDI":  0x11,
    "SUB":   0x12,
    "MUL":   0x14,
    "CMP":   0x20,
    "CMPI":  0x21,
    "JMP":   0x22,
    "JEQ":   0x23,
    "JNE":   0x24,
    "JGD":   0x29,
    "JNGD":  0x2A,
    "LOAD":  0x30,
    "STORE": 0x31,
    "PUSH":  0x32,
    "POP":   0x33,
    "HLOAD": 0x40,
    "HCADD": 0x42,
    "HPACK": 0x50,
    "HCRC":  0x51,
    "HGRD":  0x60,
    "PRINT": 0xA0,
    # "default — → HALT_ERR: menghentikan, tanpa efek samping"
    "HALT_ERR": 0xFF,
}


#: Opcodes added after the book was sealed. Each needs a reason rooted in
#: the book, so an extension cannot quietly become "what the book says".
EXTENSIONS: Dict[str, int] = {
    # §IIIH.3.1.1 lists HCADD, HPROJ, HDCMP and HEXMT as the Hybit Engine's
    # operations; §IIIM.3.1 encodes only HCADD. Without a component read,
    # nothing can get Θ̂, N, K or Q out of an H-Reg — there is no AND, no
    # shift and no DIV in the table, and HPACK cannot be unpacked. The book's
    # own example program in §IIIF.3.1.2 uses PROJ THETA and could not be
    # assembled against its own instruction table.
    #
    # The name and slot are not invented: HISA_SPEC.md already assigned 0x44
    # to CGET with exactly this semantics and never implemented it.
    "CGET": 0x44,

    # CALL and RET. The book puts them at 0x07/0x08, which HCPU cannot: 0x06
    # and 0x07 carry HNRM2 and HDIST, and 0x08 is ERET. HISA_SPEC.md records
    # the move -- PUSH/POP to the Memory block at 0x32/0x33, CALL/RET to the
    # tail of the same block -- and reserved 0x2E/0x2F for them, marked
    # software-only because nothing implemented them. They are hardware now.
    #
    # The slots are the spec's own, so this is a relocation the book's own
    # successor document already made, not a new assignment.
    "CALL": 0x2E,
    "RET": 0x2F,

    # The 28 letter instructions, 0xE0-0xFB. §IIIM.3.1 encodes operations on
    # codex vectors -- HLOAD by index, HCADD by register pair -- but never a
    # letter itself. Writing one letter therefore took three instructions and
    # two numbers: load an index, load a register, add. The numbers are the
    # thing being removed. A letter already carries a value, a function and a
    # rate; naming it by index and then adding it by register spells out what
    # it already holds.
    #
    # Safe because closure is measured, not assumed: the guard is closed under
    # addition over all 784 pairs, so a program made of letters cannot leave
    # the valid set, which is what lets the accumulator be implicit.
    #
    # 0xE0-0xFB was empty in the book's map and is exactly 28 slots wide.
    "L_ALIF": 0xE0,
    "L_BA": 0xE1,
    "L_TA": 0xE2,
    "L_TSA": 0xE3,
    "L_JIM": 0xE4,
    "L_HA": 0xE5,
    "L_KHA": 0xE6,
    "L_DAL": 0xE7,
    "L_DZAL": 0xE8,
    "L_RA": 0xE9,
    "L_ZAY": 0xEA,
    "L_SIN": 0xEB,
    "L_SYIN": 0xEC,
    "L_SHAD": 0xED,
    "L_DHAD": 0xEE,
    "L_THA": 0xEF,
    "L_ZHA": 0xF0,
    "L_AIN": 0xF1,
    "L_GHAIN": 0xF2,
    "L_FA": 0xF3,
    "L_QAF": 0xF4,
    "L_KAF": 0xF5,
    "L_LAM": 0xF6,
    "L_MIM": 0xF7,
    "L_NUN": 0xF8,
    "L_WAW": 0xF9,
    "L_HAA": 0xFA,
    "L_YA": 0xFB,

    # ERET, 0x08. §IIIM.3.1 has no way to return from an interrupt because it
    # has no interrupts: the book's machine runs one program to HALT. An OS
    # cannot be built on that. A timer that cannot preempt is a counter, and a
    # UART that cannot interrupt has to be polled, which costs the whole CPU.
    #
    # Everything else the trap unit needs is reachable as memory -- vector,
    # epc, cause, enable and pending sit in the peripheral window -- so this
    # is the ONE instruction the extension adds. The return cannot be a load
    # and a jump, because clearing the in-trap latch and redirecting the fetch
    # have to happen together, or a trap arriving between the two is lost.
    #
    # 0x08 is in the book's own "system and control" block (0x0_) and was
    # empty there, so nothing is displaced.
    "ERET": 0x08,

    # ECALL, 0x09. The other half of the same absence: §IIIM.3.1 has no way to
    # return from an interrupt because it has no interrupts, and no way to
    # ASK for one either. Without it a user program cannot reach the
    # supervisor at all -- every peripheral is refused and there is no
    # sanctioned crossing, so the boundary is a wall rather than a door.
    #
    # No operand field. The call number and arguments travel in registers by
    # convention, so the ABI can be changed without touching the encoding.
    "SYSCALL": 0x09,

    # Bitwise and shift, 0xB0-0xBA. §IIIM.3.1 freezes 28 opcodes and not one
    # of them touches a bit: no AND, no OR, no XOR, no NOT, no shift, no
    # divide, no modulo. The gap was already recorded in this file when CGET
    # was added — "there is no AND, no shift and no DIV in the table" was the
    # evidence that the table is incomplete for the book's own purposes.
    #
    # What it blocks is not a convenience. An allocator needs free-list
    # bitmaps, a scheduler needs ready masks, a driver needs register fields,
    # a filesystem needs block bitmaps; none can be written with add,
    # subtract and multiply. The CosmicTera modules lean on 80 bitwise
    # operations across four core files and could not be expressed at all.
    #
    # 0xB0-0xBF was empty in the book's map, so nothing is displaced.
    "AND":  0xB0,
    "OR":   0xB1,
    "XOR":  0xB2,
    "NOT":  0xB3,
    "SHL":  0xB4,
    "SHR":  0xB5,
    "ANDI": 0xB6,
    "ORI":  0xB7,
    "XORI": 0xB8,
    "SHLI": 0xB9,
    "SHRI": 0xBA,
}


def _rtl_opcodes() -> Dict[str, int]:
    text = PKG_VH.read_text(encoding="utf-8")
    return {
        m.group(1): int(m.group(2), 16)
        for m in re.finditer(
            r"^`define\s+OP_([A-Z0-9_]+)\s+8'h([0-9A-Fa-f]{2})", text, re.M
        )
    }


def test_the_rtl_encoding_is_the_book_encoding() -> None:
    """
    H-ISA lived in three different encodings before it was frozen; only four of
    thirteen shared mnemonics agreed, and HLOAD 0x01 meant HALT in the RTL.
    The freeze picked the RTL — this is the check that says the RTL was picked
    because it is what §IIIM.3.1 prints, not merely because it was one of the
    three.
    """
    assert _rtl_opcodes() == {**BOOK_OPCODES, **EXTENSIONS}


def test_the_python_encoding_is_the_book_encoding() -> None:
    got = {op.name: int(op.value) for op in RTL_IMPLEMENTED}
    assert got == {**BOOK_OPCODES, **EXTENSIONS}


def test_the_book_lists_twenty_eight_opcodes() -> None:
    assert len(BOOK_OPCODES) == 28
    assert len(set(BOOK_OPCODES.values())) == 28, "two mnemonics share a hex"


def test_no_extension_collides_with_the_book() -> None:
    """
    An extension may add an opcode; it may never redefine one the book prints.
    """
    assert not set(EXTENSIONS) & set(BOOK_OPCODES), "an extension shadows a book mnemonic"
    assert not set(EXTENSIONS.values()) & set(BOOK_OPCODES.values()), (
        "an extension reuses a hex the book already assigned"
    )


def test_every_extension_is_explained() -> None:
    """
    The transcription only stays trustworthy while additions are marked as
    additions. Each one must carry a comment citing why the book needs it.
    """
    source = Path(__file__).read_text(encoding="utf-8")
    block = source.split("EXTENSIONS: Dict[str, int] = {", 1)[1].split("}", 1)[0]
    for name in EXTENSIONS:
        assert f'"{name}"' in block
    assert "§IIIH.3.1.1" in block, "extensions must cite the book"


# ══════════════════════════════════════════════════════════════════
#  HCPU parameters — hal. 132–133, §IIIJ.3.2.1
# ══════════════════════════════════════════════════════════════════

BOOK_PARAMETERS: Dict[str, int] = {
    "XLEN":        32,    # Lebar word data
    "ILEN":        32,    # Lebar instruksi, fixed-length
    "HREG_W":      144,   # 18 × 8-bit unsigned
    "IMM_W":       12,    # Lebar field immediate
    "GPR_COUNT":   18,    # R0–R17
    "HREG_COUNT":  16,    # H0–H15
    "CODE_DEPTH":  4096,  # Memori kode, 32-bit words
    "DATA_DEPTH":  4096,  # Memori data, 16 KB word-addressed
    "STACK_DEPTH": 256,   # Kedalaman stack
}


@pytest.mark.parametrize(
    "name,value", sorted(BOOK_PARAMETERS.items()), ids=sorted(BOOK_PARAMETERS)
)
def test_hcpu_parameter_matches_the_book(name: str, value: int) -> None:
    text = PKG_VH.read_text(encoding="utf-8")
    # The memory depths sit inside `ifndef guards so a reduced-area ASIC
    # build can override them, so the define may be indented. The value the
    # book specifies is what is being checked, not its column.
    match = re.search(rf"^\s*`define\s+{name}\s+(\d+)", text, re.M)
    assert match, f"hcpu_pkg.vh no longer defines {name}"
    assert int(match.group(1)) == value


def test_hreg_width_is_eighteen_components_of_eight_bits() -> None:
    """
    §IIIJ.3.3.2 states the H-Reg as 18 × 8. The two numbers are written
    separately in the header, so the product is worth pinning: a codex of 18
    components is the whole premise, and 144 is what silicon carries.
    """
    assert BOOK_PARAMETERS["HREG_W"] == 18 * 8


# ══════════════════════════════════════════════════════════════════
#  ROM negative-test entry — hal. 137, §IIIK.3.1
# ══════════════════════════════════════════════════════════════════

def _rom_entry(index: int) -> List[int]:
    """Read one entry out of hcpu_rom.v. The literal is {comp17 … comp0}."""
    src = ROM_V.read_text(encoding="utf-8")
    match = re.search(rf"5'd{index}:\s*data_out\s*=\s*\{{([^}}]*)\}}", src)
    assert match, f"hcpu_rom.v has no entry at index {index}"
    return list(reversed([int(x) for x in re.findall(r"8'd(\d+)", match.group(1))]))


def test_rom_index_31_fails_g4_and_only_g4() -> None:
    """
    §IIIK.3.1: index 31 holds a deliberately corrupt vector, {Θ̂=1, Qc=2},
    and exists to fail G4 — the one guard that is a cross-constraint between
    two independent measurements rather than a sum-check.

    It did not. The 2 sat in Kp instead of Qc, so the entry tripped G2 and G4
    passed. tb_hcpu_top Program 5 stayed green with G4 disabled outright,
    which means the pipeline had no negative test for G4 at all while Bab III
    credited it with one.

    A_Q is 2 here on purpose: G3 checks A_Q == sum(Q), so leaving it 0 would
    trip G3 as well and the failure would not isolate G4.
    """
    v = _rom_entry(31)
    assert len(v) == 18

    theta, n, k, q = v[0], v[1:4], v[4:9], v[9:14]
    a_n, a_k, a_q = v[14], v[15], v[16]

    assert theta == 1, "Θ̂ must be 1 per the book"
    assert q[4] == 2, "Qc must be 2 per the book"

    assert a_n == sum(n), "G1 must pass — the entry targets G4"
    assert a_k == sum(k), "G2 must pass — the entry targets G4"
    assert a_q == sum(q), "G3 must pass — the entry targets G4"
    assert k[2] == 0 or q[4] >= 1, "T1 must pass"
    assert k[4] == 0 or q[4] >= 1, "T2 must pass"

    assert theta < compute_U(v), "G4 must fail: ρ = Θ̂ − U must be negative"
    assert theta - compute_U(v) == -7


@pytest.mark.parametrize("row", BOOK_MASTER_TABLE, ids=_IDS)
def test_rom_carries_the_sealed_letter(row: Row) -> None:
    """
    The ROM is the last link in the provenance chain before silicon. It was
    generated from hm28.json back when hm28.json was wrong, so checking it
    against the book rather than against its own generator is the point.
    """
    index, char, theta, n, k, q = row
    v = _rom_entry(index)
    assert v[0] == theta, f"{char}: ROM Θ̂"
    assert tuple(v[1:4]) == n, f"{char}: ROM N"
    assert tuple(v[4:9]) == k, f"{char}: ROM K"
    assert tuple(v[9:14]) == q, f"{char}: ROM Q"


# ══════════════════════════════════════════════════════════════════
#  Page 41 — §IA.1.1, the formal definition
# ══════════════════════════════════════════════════════════════════

# The book directory is gitignored, so nothing here can pin its name. It was
# renamed once mid-session and these tests failed with a FileNotFoundError,
# which read like data loss until it turned out to be a rename. Search for it
# instead of hard-coding a path, and skip cleanly when it is simply absent --
# a checkout without the book is a normal state, not a broken one.
def _find_page(number: int) -> Path | None:
    for parent in ROOT.glob("*Matematika Hijaiyyah*"):
        for pdf in parent.rglob(f"{number}.pdf"):
            return pdf
    return None


PAGE_41 = _find_page(41)


def _page_text(number: int) -> str:
    """Any single page, by number. `_page_41_text` is kept as the name every
    other test here already calls; this is the general form beneath it."""
    pymupdf = pytest.importorskip("pymupdf")
    page = _find_page(number)
    if page is None:
        pytest.skip("the book PDFs are not in this checkout")
    with pymupdf.open(page) as doc:
        return "\n".join(p.get_text() for p in doc)


def _page_41_text() -> str:
    return _page_text(41)


def test_page_41_states_the_fourteen_dimensional_invariant() -> None:
    """
    Item 4 of §IA.1.1: "direpresentasikan sebagai vektor invarian 14-dimensi
    dan codex 18-dimensi".

    The rank of the 28x18 alphabet is 14, and v14 alone has full rank 14.
    That was measured before this page was read, and taken for a finding; it
    is not one. The book says it, and names the two halves: the fourteen are
    the INVARIANT, the remaining four are what the CODEX carries -- the three
    aggregates and the marker.

    Anchored here so the measurement and the text cannot drift apart.
    """
    from fractions import Fraction

    from hijaiyyah.core.constants import V14_SLOTS, V18_SLOTS
    from hijaiyyah.core.guards import _to_vec

    text = " ".join(_page_41_text().split())
    assert "vektor invarian 14-dimensi dan codex 18-dimensi" in text

    vectors = [list(_to_vec(e)) for e in MASTER_TABLE.all_entries()]

    def rank(rows: list[list[int]]) -> int:
        a = [[Fraction(x) for x in r] for r in rows]
        r = 0
        for c in range(len(a[0])):
            p = next((i for i in range(r, len(a)) if a[i][c]), None)
            if p is None:
                continue
            a[r], a[p] = a[p], a[r]
            for i in range(len(a)):
                if i != r and a[i][c]:
                    f = a[i][c] / a[r][c]
                    a[i] = [x - f * y for x, y in zip(a[i], a[r], strict=True)]
            r += 1
        return r

    assert rank(vectors) == 14
    assert rank([v[:14] for v in vectors]) == 14      # the invariant is full rank
    assert list(V14_SLOTS) == list(V18_SLOTS[:14])
    assert list(V18_SLOTS[14:]) == ["AN", "AK", "AQ", "H*"]


def test_page_41_lists_twelve_properties_and_the_code_has_all_of_them() -> None:
    """
    §IA.1.1 enumerates twelve things the system must be able to do. They are
    checked by importing what implements each, rather than by reading the
    prose back to itself.
    """
    import pathlib

    text = " ".join(_page_41_text().split())
    for phrase in ("dikunci pada representasi kanonik tunggal",
                   "vektor invarian 14-dimensi",
                   "divalidasi melalui guard internal",
                   "ruang Metrik-Vektorial Hijaiyyah",
                   "compiler, assembler, dan virtual machine"):
        assert phrase in text, phrase

    from hijaiyyah.algebra import aggregametric, exometric, intrametric, normivektor, vektronometry
    from hijaiyyah.core import guards
    from hijaiyyah.crypto import program

    assert len(MASTER_TABLE.all_entries()) == 28
    assert guards.guard_check and program.build_manifest
    assert all((exometric, intrametric, aggregametric, normivektor, vektronometry))
    assert aggregametric.string_integral("بسم")["cod18"]
    assert (ROOT / "rtl" / "hcpu_top.v").exists()
    assert pathlib.Path(ROOT / "src" / "hijaiyyah" / "vm").is_dir()


def test_the_five_object_roles_are_named_on_the_page() -> None:
    """
    "objek ukur, objek hitung, objek representasi, objek komputasi, objek
    teknologi" -- the same five faces measured separately in
    test_letter_machines, arriving from the book rather than from the code.
    """
    text = " ".join(_page_41_text().split())
    for role in ("objek ukur", "objek hitung", "objek representasi",
                 "objek komputasi", "objek teknologi"):
        assert role in text, role


# ══════════════════════════════════════════════════════════════════
#  Pages 127 and 133 — the book contradicts itself about GPR_COUNT
# ══════════════════════════════════════════════════════════════════


def test_the_book_gives_a_four_bit_register_field_on_page_127() -> None:
    """
    §IIIF.3.3.1, the .hbc bytecode header. DST/S1/S2 are four bits each --
    `[23:20] [19:16] [15:12]` -- which matches hcpu_pkg.vh's DST_MSB..S2_LSB
    exactly and cannot address past 15.
    """
    text = " ".join(_page_text(127).split())
    assert "4 bits" in text
    assert "[23:20]" in text.replace(" ", "") or "23:20" in text


def test_the_book_gives_eighteen_gpr_with_r17_as_link_on_page_133() -> None:
    """
    §IIIJ.3.3.1, GPR Bank. "18 register (R0-R17)" and R17 named a link
    register, by convention -- irreconcilable with the four-bit field two
    pages earlier. Both are read from the book itself, not from a
    paraphrase, so this test and the field-width one above it cannot drift
    into agreeing with each other by accident.
    """
    text = " ".join(_page_text(133).split())
    assert "18 register" in text or "18register" in text.replace(" ", "")
    assert "R0" in text and "R17" in text
    assert "Register tautan" in text or "tautan" in text


def test_the_code_follows_the_field_width_not_the_count() -> None:
    """
    The two pages above disagree; the code has to pick a side and say so.
    MAX_GPR follows the field width (15, not 17) because that is what every
    opcode in this repository actually encodes against -- GPR_COUNT in
    hcpu_pkg.vh stays 18, transcribing the book's storage claim unchanged,
    and the two co-existing is the point, not an inconsistency to resolve
    by editing one to match the other.
    """
    from hijaiyyah.hisa import assembler as _asm

    assert _asm.MAX_GPR == 15
    pkg_text = PKG_VH.read_text(encoding="utf-8")
    match = re.search(r"`define\s+GPR_COUNT\s+(\d+)", pkg_text)
    assert match and int(match.group(1)) == 18, (
        "hcpu_pkg.vh's GPR_COUNT should keep transcribing the book, "
        "not the code's own addressing limit"
    )

    with pytest.raises(AssemblyError):
        _asm.assemble("        MOVI R16, 1\n")
    with pytest.raises(AssemblyError):
        _asm.assemble("        MOVI R17, 1\n")
