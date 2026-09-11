"""A clock-driven matrix-sequence mechanism -- deterministic, not learned,
not attention over a whole sequence at once.

Fase 0 and Fase 1 (model.py, multitask.py) are neural networks: an
embedding, summed, read by a trained head. This is neither. There are no
weights here and nothing is fit to data. Given an ORDERED sequence of
letters, it steps through them one at a time -- one clock TICK per letter,
each tick seeing only the running state and the next letter, never the
whole sequence at once the way an LLM's attention does -- and at every tick
it grounds the running state in two independently-computed true/false
facts, not a single label at the end.

The per-tick mechanism is core.exomatrix.compose_step: GF(2) (or GF(p), any
p) matrix multiplication, order-sensitive (confirmed empirically in
nui/pattern_language.py -- about 31% of ordered pairs give a different
composed rank depending on which letter came first). compose_mod's own
internal loop already runs exactly this, tick by tick; this module exposes
what that loop passes through at every step instead of collapsing it to
only the final matrix.

Each tick's letter is addressed the way nui/atom.py already established --
its opcode is the same integer that names its row in the Master Table and
its ROM address in real HCPU silicon -- so "which letter fired this tick"
is the same address throughout this codebase, not a new one invented here.

atom.py's physical realization is rtl/programs/nui_embedding.hasm,
computing SUMMED (v18 addition) features on real HCPU opcodes -- an
operation HCPU has instructions for (L_<letter>, CGET, ADD). This
module's per-tick composition is GF(2) MATRIX MULTIPLICATION, an
operation HCPU has no instruction for; NUI/ROADMAP.md's Fase 2 covers
what a sequence encoder over real HISAMachine execution would need.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from ..core.exomatrix import gf2_rank, matrix_order_of
from .atom import atom_for
from .rack import RACK, chip_for

Matrix = Tuple[Tuple[int, ...], ...]


@dataclass(frozen=True)
class Tick:
    """One clock tick: one letter, in sequence order, and the running
    composed matrix's own true/false groundings immediately after it -- a
    fact about the STATE AT THIS MOMENT, not a label for the whole
    sequence."""

    step: int        #: 1-based position in the sequence
    char: str
    opcode: int       #: this letter's real HCPU/ROM address (nui.atom)
    state: Matrix     #: composed matrix after this tick
    rank: int         #: gf2_rank(state), 0..5
    full_rank: bool   #: rank == 5
    primitive: bool   #: matrix_order_of(state, p)'s period == p**5 - 1 (max)


def run(letters: Sequence[str], *, p: int = 2, order_cap: int = 4000) -> List[Tick]:
    """Step through `letters` IN ORDER -- order genuinely changes the
    result here (compose_step does not commute), unlike dataset.py's v18
    accumulation. No learned parameters: each tick is a pure function of
    the previous tick's state and the next letter.

    The composing itself is not done here -- it is delegated to each
    letter's own Chip (nui.rack): `chip.boot()` for the first letter,
    `chip.step(state)` for every one after. This function only sequences
    WHICH chip runs WHEN; the chip is what runs.
    """
    if not letters:
        raise ValueError("run needs at least one letter")
    max_period = p**5 - 1

    def grounded(step: int, char: str, state: Matrix) -> Tick:
        rank = gf2_rank(state)
        _, period = matrix_order_of(state, p, cap=order_cap)
        return Tick(step=step, char=char, opcode=atom_for(char).opcode, state=state,
                    rank=rank, full_rank=(rank == 5), primitive=(period == max_period))

    state: Matrix = chip_for(letters[0]).boot(p)
    ticks = [grounded(1, letters[0], state)]
    for i, char in enumerate(letters[1:], start=2):
        state = chip_for(char).step(state, p)
        ticks.append(grounded(i, char, state))
    return ticks


def run_rack(*, p: int = 2, order_cap: int = 4000) -> List[Tick]:
    """run() over the WHOLE rack, Master Table order, RACK[0] booting and
    every chip after it stepping in the same fixed sequence -- not an
    ad-hoc hand-picked subset. One canonical 28-tick clock run per rack,
    the same one every caller gets, rather than each caller improvising
    its own letter list."""
    return run([c.char for c in RACK], p=p, order_cap=order_cap)


@dataclass(frozen=True)
class PermutationScore:
    """One ordering of `letters`, run through run() and scored by its own
    ticks -- a fact about what compose_step does with this SPECIFIC order,
    not about which letters are in it (the same 28 letters, reordered,
    score differently -- that is the whole point of ranking them)."""

    order: Tuple[str, ...]
    full_rank_ticks: int   #: count of ticks with full_rank == True
    primitive_ticks: int   #: count of ticks with primitive == True
    final_rank: int        #: rank of the last tick


def rank_permutations(letters: Optional[Sequence[str]] = None, *,
                       count: int = 1000, seed: int = 0, p: int = 2,
                       order_cap: int = 4000) -> List[PermutationScore]:
    """Sample `count` random orderings of `letters` (RACK's own 28, by
    default), run each through run(), and rank them by how many ticks
    (clicks) the running GF(2) matrix held full rank -- ties broken by
    primitive-tick count, then final rank, both read off the same ticks
    run() already computed, not a new calculation.

    28! orderings cannot be enumerated; this is a random sample, seeded
    for reproducibility (same seed, same permutations, same ranking,
    every run) -- not a claim that the top-scoring sample is the true
    maximum over all 28! orderings.
    """
    rng = random.Random(seed)
    base = list(letters) if letters is not None else [c.char for c in RACK]
    scored = []
    for _ in range(count):
        order = base[:]
        rng.shuffle(order)
        ticks = run(order, p=p, order_cap=order_cap)
        scored.append(PermutationScore(
            order=tuple(order),
            full_rank_ticks=sum(1 for t in ticks if t.full_rank),
            primitive_ticks=sum(1 for t in ticks if t.primitive),
            final_rank=ticks[-1].rank,
        ))
    scored.sort(key=lambda s: (s.full_rank_ticks, s.primitive_ticks, s.final_rank),
                reverse=True)
    return scored


@dataclass(frozen=True)
class Channel:
    """The link between two consecutive nodes in a clocked run -- "kanal":
    which node fed in, which one it composed with, and the state on each
    side of that one compose_step. Not a new computation: exactly the
    transition run() already makes going from ticks[i] to ticks[i+1]; this
    names it as its own object instead of leaving it implicit between two
    Ticks."""

    from_node: str    #: char
    to_node: str      #: char
    state_before: Matrix
    state_after: Matrix


def channels(ticks: Sequence[Tick]) -> List[Channel]:
    """Every channel in a run's own tick sequence -- one per consecutive
    pair, so a single-tick run (one node, no link yet) has none. Reads
    ticks[i].state / ticks[i+1].state straight off what run() already
    computed; nothing here re-derives a state via compose_step itself."""
    return [
        Channel(from_node=ticks[i].char, to_node=ticks[i + 1].char,
                state_before=ticks[i].state, state_after=ticks[i + 1].state)
        for i in range(len(ticks) - 1)
    ]


# ── automate(): the same run(), staged as three named steps ─────
#
# Three stages, named after the three geometric primitives features.py
# already reads off the Master Table (titik/garis/lengkung) rather than
# invented fresh here:
#
#   BOOT  ("garis," a straight flow) -- run()'s own first tick: the first
#         letter's exomatrix, unmodified. A straight line -- what goes in
#         is exactly what comes out, no composition has happened yet.
#
#   BEND  ("lengkung," a curve) -- every following tick: compose_step's
#         matrix multiplication bends the straight opening state into
#         something that is no longer just one letter's own exomatrix.
#         This IS run()'s tick loop; nothing new computes here, this stage
#         is the same ticks, named for what they do to the state.
#
#   EMIT  ("titik," a small hole, under real computational pressure) --
#         the running state, a whole 5x5 matrix, is squeezed down to ONE
#         bit: a single true/false grounding, not the matrix itself. That
#         squeeze is not a metaphor for what happens -- Automation.emitted
#         really is one bool, read off the last tick's own full_rank or
#         primitive field (nothing new computed here either).


@dataclass(frozen=True)
class Automation:
    """One boot-bend-emit pass over an ordered sequence: every tick along
    the way (the full "bend"), and the single grounding squeezed out at the
    end (the "emit")."""

    ticks: Tuple[Tick, ...]   #: the whole run -- boot is ticks[0], bend is all of it
    boot_char: str            #: the letter that opened the flow
    ground: str               #: which of Tick's own fields was emitted
    emitted: bool             #: the "titik" -- one grounding, not a matrix


def automate(letters: Sequence[str], *, p: int = 2, ground: str = "full_rank",
             order_cap: int = 4000) -> Automation:
    """boot -> bend -> emit, one modular pass. Not a new mechanism: run()
    IS the boot+bend (its first tick opens the flow straight, every tick
    after bends it); this only names the stages and does the final squeeze
    to one bit -- `ground` picks which of Tick's own two true/false fields
    is what comes out the small hole, "full_rank" or "primitive"."""
    if ground not in ("full_rank", "primitive"):
        raise ValueError(f"ground must be 'full_rank' or 'primitive', got {ground!r}")
    ticks = run(letters, p=p, order_cap=order_cap)
    emitted = getattr(ticks[-1], ground)
    return Automation(ticks=tuple(ticks), boot_char=letters[0], ground=ground, emitted=emitted)
