"""What a receiver can actually measure, and the number that is not it.

`lock.py` recovers the rung -- 2.77 bits of the 4.81 a letter needs. The
second measurement is frequency, and getting it right meant separating three
quantities that had been read as one:

    matrix order    period of M, M^2, M^3, ... over GF(2)
    state cycle     period of the state trajectory from (1,0,0,0,0)
    wire period     fundamental period of the emitted bit

Only the third reaches a receiver. The three are not equal, and for six
letters -- ba, ha, ta, zha, lam, mim -- they disagree:

    matrix order   {1: 16, 2: 2, 3: 7, 4: 1, 31: 2}    five values
    wire period    {1: 22, 3: 4, 31: 2}                three

`ba` has matrix order 4 and emits `0000`: a cycling matrix whose observable
output is a constant. `ha` and `lam` cycle at 2 and emit `11`. `ta`, `zha`
and `mim` have order 3 and emit a constant. So **22 letters are silent on
the wire, not 16**, and the alphabet is two tones rather than four:

    27_000_000 / 3  = 9.000 MHz    dhal, zay, ghayn, fa
    27_000_000 / 31 = 870.97 kHz   jim, kha
    everything else                silent

This corrects a reading, not a calculation. `test_letter_machines.py`
computes matrix order correctly and `cosmic-codex-jim/WAVE.md` tabulates it
correctly; what was wrong was the sentence attaching those periods to what a
letter *emits*. Both numbers are kept here, under names that say which is
which, because matrix order is a real property of the machine -- it is just
not the frequency anyone can receive.

**Measured discrimination, using only what a receiver observes:**

    rung alone                       8 classes   2.77 bit    2 / 28 unique
    wire period alone                3 classes   0.95 bit    0 / 28
    wire period + motif              6 classes   1.84 bit    3 / 28
    rung x wire period              12 classes   3.33 bit    5 / 28
    rung x wire period x motif      13 classes   3.40 bit    7 / 28

The motif is the cycle itself, so it carries phase as well as frequency:
`dhal`, `zay` and `fa` all emit `110` while `ghayn` emits `101`, which is
the same tone one shift along. Frequency cannot separate them and phase can.

Using matrix order instead would report 16 classes and 3.82 bits -- better
numbers for a measurement no receiver can make. The honest figure is 3.40 of
4.81, and the rest is not in the signal: it is the point, line and curve
counts, and no phase or frequency carries them. So this module returns
candidates and stops.

**"Period" means something else two files over.** `crypto/wave.py` finds a
byte-framing period in an unaligned bit stream. Nothing here is that.
"""
from __future__ import annotations

import collections
from typing import Dict, List, Optional, Tuple

from ..core.exomatrix import build_exomatrix, matrix_order
from ..core.master_table import MASTER_TABLE
from .lock import RUNGS

__all__ = [
    "BOARD_CLOCK_HZ",
    "MATRIX_ORDERS",
    "MOTIFS",
    "SIGNATURES",
    "WIRE_PERIODS",
    "emitted_cycle",
    "matrix_period",
    "narrow",
    "tone_hz",
]

#: The Tang Nano 20K crystal the oscillator bank is clocked at.
BOARD_CLOCK_HZ = 27_000_000

#: The machine's start state, as `cosmic-codex-jim/WAVE.md` clocks it.
START_STATE = (1, 0, 0, 0, 0)


def _entry(letter: str):
    for entry in MASTER_TABLE.all_entries():
        if entry.char == letter:
            return entry
    raise KeyError(f"no sealed letter {letter!r}")


def emitted_cycle(letter: str) -> Tuple[int, ...]:
    """The repeating motif on the wire, transient discarded.

    Runs the state until it repeats, drops the tail, then reduces the cycle
    to its fundamental period -- a state cycle of `0000` is a wire period of
    1, because a receiver measuring frequency sees a constant.
    """
    matrix = [[x & 1 for x in row] for row in build_exomatrix(_entry(letter))]
    state: Tuple[int, ...] = START_STATE
    seen, seq, k = {}, [], 0
    while state not in seen:
        seen[state] = k
        seq.append(state[0])
        state = tuple(
            sum(matrix[i][j] * state[j] for j in range(5)) & 1 for i in range(5))
        k += 1
    cycle = seq[seen[state]:]
    n = len(cycle)
    fundamental = next(
        p for p in range(1, n + 1)
        if n % p == 0 and all(cycle[i] == cycle[i % p] for i in range(n)))
    return tuple(cycle[:fundamental])


def matrix_period(letter: str) -> int:
    """Order of the letter's exomatrix over GF(2). **Not** the emitted period.

    Kept because it is a real property of the machine and the one
    `WAVE.md` tabulates. For six letters it is larger than what the wire
    shows, so it must never be used to compute a frequency.
    """
    _tail, period = matrix_order(_entry(letter), 2)
    if period is None:  # pragma: no cover - no sealed letter does this
        raise ValueError(f"{letter!r} has no GF(2) orbit")
    return period


def _all() -> List[str]:
    return [e.char for e in MASTER_TABLE.all_entries()]


#: Letter -> the motif it emits. Length 1 for the 22 silent letters.
MOTIFS: Dict[str, Tuple[int, ...]] = {c: emitted_cycle(c) for c in _all()}

#: Letter -> observable period. Three values: 1, 3, 31.
WIRE_PERIODS: Dict[str, int] = {c: len(m) for c, m in MOTIFS.items()}

#: Letter -> matrix order. Five values. Kept for comparison, not for tuning.
MATRIX_ORDERS: Dict[str, int] = {c: matrix_period(c) for c in _all()}


def _build_signatures() -> Dict[Tuple[int, int, Tuple[int, ...]], Tuple[str, ...]]:
    by = collections.defaultdict(list)
    for rung, letters in RUNGS.items():
        for char in letters:
            by[(rung, WIRE_PERIODS[char], MOTIFS[char])].append(char)
    return {k: tuple(v) for k, v in by.items()}


#: (rung, wire period, motif) -> letters. 13 classes over 28 letters.
SIGNATURES: Dict[Tuple[int, int, Tuple[int, ...]], Tuple[str, ...]] = _build_signatures()


def tone_hz(letter: str, clock_hz: int = BOARD_CLOCK_HZ) -> float:
    """Frequency on the wire. 0.0 for the 22 letters that emit a constant.

    A constant is not a tone, so period 1 returns zero rather than
    `clock_hz`. Computed from the wire period, never from matrix order --
    that is the substitution this module exists to prevent.
    """
    period = WIRE_PERIODS[letter]
    return 0.0 if period == 1 else clock_hz / period


def narrow(rung: int, period: Optional[int] = None,
           motif: Optional[Tuple[int, ...]] = None) -> Tuple[str, ...]:
    """Candidates for a locked rung, narrowed by whatever else was measured.

    `period=None` means frequency was never recovered, so the rung's full
    set comes back rather than a guess. `motif` narrows further where phase
    was recovered too. An unoccupied combination returns empty -- a
    rejection, not an error.
    """
    if period is None:
        return RUNGS.get(rung, ())
    if motif is not None:
        return SIGNATURES.get((rung, period, motif), ())
    found = [c for (r, p, _m), chars in SIGNATURES.items()
             if r == rung and p == period for c in chars]
    order = {c: i for i, c in enumerate(_all())}
    return tuple(sorted(found, key=lambda c: order[c]))
