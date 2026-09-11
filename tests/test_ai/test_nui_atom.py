"""atom.py: one address, checked against sources that never agreed on
purpose, and one physical realization already proven on simulated hardware.
"""
from __future__ import annotations

from pathlib import Path

import pytest

torch = pytest.importorskip("torch")  # atom.py itself doesn't need torch; model.py does

from hijaiyyah.core.master_table import MASTER_TABLE  # noqa: E402
from hijaiyyah.hisa.opcodes import OpCode  # noqa: E402
from hijaiyyah.nui.atom import (  # noqa: E402
    ATOMS,
    LETTER_OP_FIRST,
    LETTER_OP_LAST,
    atom_for,
    verify_address_unification,
)
from hijaiyyah.nui.model import LetterAccumulatorNet  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def test_verify_address_unification_passes():
    verify_address_unification()  # raises on any disagreement


def test_28_atoms_cover_the_letter_opcode_range_with_no_gaps_or_duplicates():
    assert len(ATOMS) == 28
    opcodes = sorted(a.opcode for a in ATOMS)
    assert opcodes == list(range(LETTER_OP_FIRST, LETTER_OP_LAST + 1))


def test_letter_index_formula_matches_rtl_independently():
    """rtl/hcpu_execute.v:188-189's own formula, recomputed here directly --
    not by calling atom.py's _opcode_for_index, which is the thing being
    checked."""
    for atom in ATOMS:
        letter_index_in_hardware = (atom.opcode - LETTER_OP_FIRST) + 1
        assert letter_index_in_hardware == atom.master_index


def test_atom_names_agree_with_two_independently_written_sources():
    """OpCode's name (hisa/opcodes.py) and MASTER_TABLE's name field (the
    sealed table) were never cross-checked against each other before
    verify_address_unification did it -- this repeats it per-letter rather
    than trusting the one aggregate assertion."""
    for atom in ATOMS:
        entry = MASTER_TABLE.get_by_char(atom.char)
        assert OpCode(atom.opcode).name == f"L_{entry.name.upper()}"


def test_embedding_row_matches_the_actual_trained_nets_embedding_weight():
    """Ties this module back to Fase 0's own model: atom.physics for a
    letter must be the exact row LetterAccumulatorNet(kind="physics")
    freezes at atom.embedding_row -- not a parallel re-derivation that
    happens to look similar."""
    net = LetterAccumulatorNet(kind="physics")
    for atom in ATOMS:
        row = net.embedding.weight[atom.embedding_row]
        assert row.tolist() == [float(x) for x in atom.physics.as_tuple()]


def test_jim_and_kha_atoms_match_nui_embedding_hasms_proven_physical_output():
    """rtl/programs/nui_embedding.hasm runs L_JIM then L_KHA on real HCPU
    opcodes and PRINTs the summed physics features over a real UART at the
    board's real 27 MHz -- verified in simulation this same session,
    byte-for-byte, as "2\\n2\\n2\\n6\\n6\\n" (tb_hcpu_nui_embedding.v). This
    checks that claim from the software side: do these two atoms' own
    address-derived physics features sum to exactly that, independent of
    ever re-running the RTL simulation."""
    program = (ROOT / "rtl" / "programs" / "nui_embedding.hasm").read_text(encoding="utf-8")
    assert "L_JIM" in program and "L_KHA" in program

    jim, kha = atom_for("ج"), atom_for("خ")
    pairs = zip(jim.physics.as_tuple(), kha.physics.as_tuple(), strict=True)
    summed = tuple(a + b for a, b in pairs)
    assert summed == (2, 2, 2, 6, 6)
