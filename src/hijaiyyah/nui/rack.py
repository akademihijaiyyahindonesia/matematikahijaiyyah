"""The 28-letter rack: every atom, as a chip -- and every chip, a mock chip
that RUNS, not a record a caller reads and processes elsewhere.

A "rack" here is exactly what the word means for hardware -- a frame
holding a fixed number of standardized slots. 28 slots, Master Table
order, one per letter. Each slot is a "chip": a NODE (this letter's own
address -- opcode, the same ROM address real HCPU silicon indexes with,
nui.atom) carrying its own DATA -- point, line, curve (titik/garis/
lengkung), plus the turning pair (theta, rho) features.py already
established from the sealed Master Table.

A Chip is not only that data, sitting wherever Python happens to keep it.
`Chip.step()` and `Chip.boot()` are the chip DOING something with an input
and producing an output -- composing a running state with this chip's own
letter, one clock tick -- not a value read out of the chip by a caller who
does the composing itself. The result of running a chip is a fresh matrix,
handed back to whoever called it; nothing is written to a shared record for
someone else to later go and read.

Nothing computed inside step()/boot() is new: both are exactly
core.exomatrix.compose_step / build_exomatrix, called with this chip's own
vector. nui.clockwork.run() calls these rather than composing letters
itself, which is the point -- the chip runs, clockwork only sequences which
chip runs when.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from ..core.exomatrix import build_exomatrix, compose_step
from ..core.master_table import MASTER_TABLE
from .atom import ATOMS, LetterAtom

NUM_SLOTS = 28

Matrix = Tuple[Tuple[int, ...], ...]


@dataclass(frozen=True)
class Chip:
    """One rack slot: a node (address) carrying its own data (point, line,
    curve, plus the turning pair) -- and its own run behaviour."""

    node: LetterAtom  #: this chip's address -- opcode/master_index/rom_address
    point: int        #: titik -- Nuqthah, point/node count (guard G1)
    line: int         #: garis -- Khat, straight-stroke count (guard G2)
    curve: int        #: lengkung -- Qaws, curve-stroke count (guard G3)
    theta: int        #: Theta-hat, total turning in units of 90 degrees
    rho: int          #: turning NOT explained by curves

    @property
    def char(self) -> str:
        return self.node.char

    @property
    def opcode(self) -> int:
        return self.node.opcode

    def _vector(self) -> tuple:
        entry = MASTER_TABLE.get_by_char(self.char)
        assert entry is not None, self  # built from all_entries(); always resolves
        return entry.vector

    def boot(self, p: int = 2) -> Matrix:
        """Run this chip as the FIRST one in a sequence: seed a fresh state
        from this chip's own exomatrix, unmodified -- automate()'s "boot"
        stage, as something the chip itself does rather than something a
        caller builds by hand."""
        matrix = build_exomatrix(self._vector())
        return tuple(tuple(x % p for x in row) for row in matrix)

    def step(self, state: Matrix, p: int = 2) -> Matrix:
        """Run this chip against an already-running state: compose `state`
        with this chip's OWN letter, one clock tick. The chip supplies its
        own data (nothing external is passed in but the state it is
        composing with); the result is handed back, not stashed anywhere
        for a caller to fetch separately."""
        return compose_step(state, self._vector(), p)


def _build_rack() -> Tuple[Chip, ...]:
    return tuple(
        Chip(node=a, point=a.physics.titik, line=a.physics.garis,
             curve=a.physics.lengkung, theta=a.physics.theta, rho=a.physics.rho)
        for a in ATOMS
    )


RACK: Tuple[Chip, ...] = _build_rack()
RACK_BY_CHAR: Dict[str, Chip] = {c.char: c for c in RACK}


def chip_for(char: str) -> Chip:
    return RACK_BY_CHAR[char]
