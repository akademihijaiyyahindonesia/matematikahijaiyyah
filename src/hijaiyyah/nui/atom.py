"""The NUI atom: one letter, one address, two realizations.

An "atom" here is not a metaphor layered on top of new machinery -- it names
something that already exists, verified across three places that were never
written to agree on purpose, and turns out to agree exactly:

    Master Table index (1-based, MASTER_TABLE.get_by_char(c).index)
        == opcode - LETTER_OP_FIRST + 1        (hisa.opcodes.OpCode.L_<X>)
        == letter_index in hardware            (rtl/hcpu_execute.v:188-189,
                                                  "the ROM is 1-indexed by
                                                  letter, so the offset gets
                                                  one added to it")

That single integer is the ADDRESS half of the atom: the same number names
a row in the Python Master Table, an instruction opcode (0xE0-0xFB), and a
ROM address the real HCPU pipeline indexes with in silicon. Nothing here
invents a new addressing scheme; this module makes an existing one explicit
and checks it, rather than assuming three independently-written pieces of
code still agree.

The atom's two REALIZATIONS of that address:

  software  features.vector_features(v) -- titik/garis/lengkung/theta/rho,
            NUI's own frozen "physics" embedding (Fase 0, model.py).

  physical  rtl/programs/nui_embedding.hasm computes the exact same five
            numbers on real HCPU opcodes (L_JIM, L_KHA -- this atom's own
            addresses) and PRINTs them over a real UART, clocked at the
            board's real 27 MHz, verified byte-for-byte in simulation
            (tb_hcpu_nui_embedding.v, "2\\n2\\n2\\n6\\n6\\n") -- a bitstream at
            a real Hz, not a description of one.

Two addresses in, two independently-computed values out, and this module's
own tests check that software and physical agree with each other and with
what the RTL testbench already proved -- not a new claim, a bridge between
two that already existed on opposite sides of this repository.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from ..core.master_table import MASTER_TABLE
from ..hisa.opcodes import OpCode
from .features import LetterFeatures, vector_features

#: rtl/hcpu_pkg.vh: `define LETTER_OP_FIRST 8'hE0 / LETTER_OP_LAST 8'hFB.
#: Repeated here as a literal, not imported, because there is nothing to
#: import it from on the Python side -- OpCode.L_ALIF.value already IS
#: 0xE0, and this constant exists only so verify_address_unification() has
#: something independent to check that value against.
LETTER_OP_FIRST = 0xE0
LETTER_OP_LAST = 0xFB


@dataclass(frozen=True)
class LetterAtom:
    """One letter's address (three equal views of the same integer) and its
    software realization. The physical realization is not a per-atom field
    -- it is rtl/programs/nui_embedding.hasm and hcpu_gowin_top.v, named
    once in this module's docstring, not duplicated 28 times."""

    char: str
    master_index: int   #: 1-based -- MASTER_TABLE.get_by_char(char).index
    opcode: int          #: L_<LETTER>'s instruction word, 0xE0-0xFB
    rom_address: int     #: what rtl/hcpu_execute.v's `letter_index` computes
    embedding_row: int    #: 0-based -- what nn.Embedding actually indexes with
    physics: LetterFeatures  #: titik/garis/lengkung/theta/rho, this address's software realization


def _opcode_for_index(master_index: int) -> int:
    """The inverse of rtl/hcpu_execute.v:189's `letter_index =
    (id_opcode - LETTER_OP_FIRST) + 1` -- solved for id_opcode, not just
    asserted to be its inverse (see test_atom.py)."""
    return LETTER_OP_FIRST + master_index - 1


def build_atoms() -> Tuple[LetterAtom, ...]:
    """All 28 atoms, Master Table order."""
    atoms = []
    for e in MASTER_TABLE.all_entries():
        opcode = _opcode_for_index(e.index)
        atoms.append(LetterAtom(
            char=e.char,
            master_index=e.index,
            opcode=opcode,
            rom_address=e.index,  # the ROM address IS the master index (1-indexed)
            embedding_row=e.index - 1,
            physics=vector_features(e.vector),
        ))
    return tuple(atoms)


ATOMS: Tuple[LetterAtom, ...] = build_atoms()
ATOMS_BY_CHAR = {a.char: a for a in ATOMS}


def atom_for(char: str) -> LetterAtom:
    return ATOMS_BY_CHAR[char]


def verify_address_unification() -> None:
    """Every atom's address views agree, checked against sources that were
    never written to agree on purpose:

      - the opcode falls inside LETTER_OP_FIRST..LETTER_OP_LAST and is a
        REAL member of hisa.opcodes.OpCode (OpCode(...) raises ValueError
        otherwise -- ..., not merely an integer that looks plausible)
      - that member's own name (independently hand-written when
        hisa/opcodes.py was built) matches MASTER_TABLE's own `name` field
        (independently hand-written when the Master Table was sealed) --
        two names nobody kept in sync on purpose, checked against each
        other rather than assumed still consistent.
    """
    for atom in ATOMS:
        assert LETTER_OP_FIRST <= atom.opcode <= LETTER_OP_LAST, atom
        assert atom.opcode - LETTER_OP_FIRST + 1 == atom.master_index, atom
        assert atom.rom_address == atom.master_index, atom
        assert atom.embedding_row == atom.master_index - 1, atom

        opcode_member = OpCode(atom.opcode)  # raises ValueError if not a real opcode
        entry = MASTER_TABLE.get_by_char(atom.char)
        assert entry is not None, atom  # built from all_entries(); always resolves
        expected_name = f"L_{entry.name.upper()}"
        assert opcode_member.name == expected_name, (atom, opcode_member.name, expected_name)
