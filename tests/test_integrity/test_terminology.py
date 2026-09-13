"""A term names a function here, so two names for one thing is a defect.

The repository had two, and they were not synonyms sitting harmlessly side by
side. Component 17 was `H*` in `constants.py` and `Ψ` in the RTL, the HISAB
packer and the crypto record -- while `Ψ` *also* meant the compiler stage that
injects guards. One symbol, two unrelated roles, and one slot with two names:
a reader who knew either convention would misread the other.

`H*` won because `V18_SLOTS` and `SLOT_INDEX` had always used it and because
`Ψ` was already spoken for. These tests keep that decision from eroding, which
matters more than it sounds: the tests in this folder identify slots by name,
so a slot renamed in one file and not another does not fail loudly -- it
quietly checks a different column.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from hijaiyyah.core.constants import SLOT_INDEX, V18_SLOTS

ROOT = Path(__file__).resolve().parents[2]

#: Where component 17 is named. Files that mean the compiler by Psi are not here.
SLOT_NAMING_FILES = [
    "rtl/hcpu_pkg.vh",
    "rtl/hcpu_rom.v",
    "rtl/hcpu_hisab.v",
    "rtl/tb/tb_rom.v",
    "src/hijaiyyah/crypto/guarded_record.py",
]

#: Where Psi legitimately means the guard-injecting compiler stage.
PSI_IS_THE_COMPILER = [
    "src/hijaiyyah/pipeline/__init__.py",
    "src/hijaiyyah/core/hgeo.py",
    "src/hijaiyyah/compiler/psi.py",
]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_the_canonical_name_of_component_17_is_h_star() -> None:
    """The decision itself, stated where a reader will look for it."""
    assert V18_SLOTS[17] == "H*", V18_SLOTS[17]
    assert SLOT_INDEX["Hstar"] == 17
    assert "Psi" not in SLOT_INDEX and "Ψ" not in SLOT_INDEX


@pytest.mark.parametrize("rel", SLOT_NAMING_FILES)
def test_no_file_that_names_slots_calls_component_17_psi(rel: str) -> None:
    """Psi in these files meant the slot, so its absence is the check.

    Not a search for "H*" -- a file may legitimately never mention the slot.
    What it may not do is call it by the name that belongs to something else.
    """
    assert "Ψ" not in _read(rel), (
        f"{rel} calls a codex slot Psi; component 17 is H*, and Psi is the "
        f"guard-injecting compiler stage")


@pytest.mark.parametrize("rel", PSI_IS_THE_COMPILER)
def test_psi_still_means_the_compiler_where_it_should(rel: str) -> None:
    """The rename must not have swept through the other meaning.

    A blanket substitution would have renamed the Psi-Compiler too, and
    nothing else in the suite would have noticed -- it is prose, not code.
    """
    assert "Ψ" in _read(rel), f"{rel} lost the Psi-Compiler it is named for"


def test_the_rtl_slot_macro_agrees_with_the_python_index() -> None:
    """Two copies of the same table, compared rather than trusted."""
    pkg = _read("rtl/hcpu_pkg.vh")
    m = re.search(r"`define C_HSTAR\s+(\d+)", pkg)
    assert m, "hcpu_pkg.vh no longer defines C_HSTAR (was C_PSI)"
    assert int(m.group(1)) == SLOT_INDEX["Hstar"] == 17
    assert "`define C_PSI" not in pkg, "the superseded macro name is back"


def test_every_slot_name_the_rtl_prints_is_a_real_slot() -> None:
    """The eighteen names in the ROM header, checked against the table.

    A slot list written by hand in a comment is the cheapest thing to get
    wrong and the hardest to notice, because nothing reads it.
    """
    header = _read("rtl/hcpu_rom.v")
    m = re.search(r"comp\[0\]=(\S+), comp\[1\]=(\S+), \.\.\., comp\[17\]=(\S+)", header)
    assert m, "hcpu_rom.v no longer names its component layout"
    first, second, last = m.groups()
    assert first == V18_SLOTS[0], (first, V18_SLOTS[0])
    assert second == V18_SLOTS[1], (second, V18_SLOTS[1])
    assert last == V18_SLOTS[17], (last, V18_SLOTS[17])


def test_the_op_prefix_names_opcodes_and_nothing_else() -> None:
    """`OP_` was carrying two meanings, and one of them was miscounting.

    `OP_MSB` and `OP_LSB` were bit positions of the opcode FIELD sitting in
    the same namespace as the opcodes themselves, so every tool that counts
    `define OP_` counted them too. That is how 74 reached an inventory table
    whose answer is 72, and it was believed because the name said opcode.

    Field positions are OPCODE_MSB/OPCODE_LSB now, matching DST_MSB and the
    rest. The check is on the shape of the value, not on a list of known
    exceptions: an opcode is a byte, a bit position is not.
    """
    pkg = _read("rtl/hcpu_pkg.vh")
    defines = re.findall(r"^`define (OP_[A-Z0-9_]+)\s+(\S+)", pkg, re.M)
    assert defines, "hcpu_pkg.vh defines no opcodes"

    not_opcodes = [name for name, value in defines if not value.startswith("8'h")]
    assert not not_opcodes, (
        f"these carry the opcode prefix but are not 8-bit opcodes: {not_opcodes}; "
        f"a bit position or a width belongs in its own namespace, or the next "
        f"count of `define OP_` is wrong again")


def test_the_opcode_count_the_inventory_prints_is_the_count() -> None:
    """teknologi/README publishes this figure, so it is recomputed here."""
    pkg = _read("rtl/hcpu_pkg.vh")
    opcodes = re.findall(r"^`define OP_([A-Z0-9_]+)\s+8'h", pkg, re.M)
    letters = [o for o in opcodes if o.startswith("L_")]

    assert len(letters) == 28, f"{len(letters)} letter opcodes, not 28"
    assert len(opcodes) - len(letters) == 53, len(opcodes) - len(letters)

    readme = _read("teknologi/README.md")
    m = re.search(r"^\| Opcode H-ISA \| (\d+) \|", readme, re.M)
    assert m and int(m.group(1)) == len(opcodes), (
        f"the inventory says {m.group(1) if m else None}, the package defines {len(opcodes)}")
