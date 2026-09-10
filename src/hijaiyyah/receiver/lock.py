"""The quarter-turn ladder as a phase lock: a wave arrives, a sequence leaves.

Theta-hat counts quarter turns -- `nui/claims.py:actual_theta_degrees` reads
it out as `vector[0] * 90`. That makes the sealed table a **quantiser grid**
as well as a table of letters, and this module is the arm of it that points
at incoming signal rather than at letter geometry: a continuous phase is
snapped to the nearest rung, and a stream of phases becomes a stream of
rungs. That stream is the sequence.

`pipeline.Measurement` has carried a `theta_continuous_rad` field alongside
`theta_hat` since before this module existed, and nothing anywhere ever
wrote to it or read it. The continuous-to-discrete step it implies had no
implementation. This is that step, applied at the signal end.

**A rung is not a letter, and the module never pretends otherwise.**
Measured over the sealed table:

    rung alone          8 classes, 2.77 bit of 4.81   2 / 28 letters unique
    rung + N           21 classes                    16 / 28
    rung + N + K       26 classes                    24 / 28
    rung + N + K + Q   28 classes                    28 / 28

So locking recovers the rung and never more than the rung. `Lock.letters`
is the candidate set standing on it -- up to six characters -- and
narrowing it needs the other blocks, which no phase measurement carries.
A lock that returned one letter would be inventing the other 2.04 bits.

**The ladder is cumulative, not wrapped.** Alif stands at 0 degrees, five
letters at 360, and Haa alone at 720 -- two whole turns. A detector that
reported phase modulo 360 would fold those three rungs onto one another and
lose three of the eight outright, so `PhaseLock` unwraps: it accumulates the
signed step between samples and tracks total turning, the way a rotary
decoder does. The cost is the usual one, and it is real: a step larger than
half a turn between samples is indistinguishable from the same step
backwards, so the input must be sampled faster than twice its frequency.

**Rung 7 is empty and that is useful.** Rungs 0 through 8 are occupied
except 630 degrees, which no letter holds. A signal that locks there is
in range, on grid, and outside the alphabet -- a rejection the geometry
hands over for free, with no threshold to tune.

**Loop tops are the calibration anchors.** `rung % 4 == 0` is the mod-4
gate of Theorem 11.4.1, and in this domain it is the moment accumulated
phase completes a whole number of turns. Residual at a loop top is measured
against a known zero, so it reads as drift rather than as offset.

**Why the quantum is 90 degrees, and not a number picked here.** The codex
is a census of a construction that runs point -> line -> curve -> circle,
and its blocks are named for exactly those: `N` is *nuqtah*, the points;
`K` is *khatt*, the straight segments; `Q` is *qaws*, the curved ones. The
circle is not a fourth block -- it is what a curve becomes when it closes,
and it enters the algebra as a coefficient. Definition 11.1.1 sets
`U = Qx + Qs + Qa + 4*Qc`, and that 4 is the price of one closed curve in
quarter turns. So 360 / QUANTUM_DEG and the weight `Qc` carries in `U` are
the same 4, and `test_the_quantum_comes_from_the_closed_curve_coefficient`
holds the two together. A grid built on any other quantum would be locking
signal to a ladder the guards do not use.
"""
from __future__ import annotations

import collections
from typing import Dict, List, NamedTuple, Sequence, Tuple

from ..core.master_table import MASTER_TABLE

__all__ = [
    "QUANTUM_DEG",
    "RUNGS",
    "Lock",
    "PhaseLock",
    "degrees_of",
    "lock_angle",
    "phase_ramp",
    "rung_of",
]

#: Degrees per unit of Theta-hat. One unit is a quarter turn -- the quantum
#: the sealed table is built on, not a constant chosen here.
QUANTUM_DEG = 90.0


def _build_rungs() -> Dict[int, Tuple[str, ...]]:
    """Rung -> the letters standing on it, read from the sealed table.

    Derived rather than written down, so a change to the table moves the
    ladder instead of silently disagreeing with it.
    """
    by = collections.defaultdict(list)
    for entry in MASTER_TABLE.all_entries():
        by[entry.vector[0]].append(entry.char)
    return {k: tuple(v) for k, v in sorted(by.items())}


#: The ladder: 8 occupied rungs spanning 0..8, with 7 absent.
RUNGS: Dict[int, Tuple[str, ...]] = _build_rungs()


class Lock(NamedTuple):
    """One sample, snapped to the grid, with what the grid can and cannot say."""

    rung: int
    """Cumulative quarter turns -- Theta-hat, in the same units as vector[0]."""

    unwrapped_deg: float
    """Total accumulated turning. Not reduced modulo 360; see the module note."""

    residual_deg: float
    """Signed distance to the rung, in [-45, 45). How far off grid the sample sat."""

    letters: Tuple[str, ...]
    """Every letter on this rung. Empty at rung 7 and outside 0..8."""

    @property
    def in_alphabet(self) -> bool:
        """False when the rung holds no letter -- rung 7, or off the ladder."""
        return bool(self.letters)

    @property
    def is_loop_top(self) -> bool:
        """A whole number of turns: the mod-4 gate, and the calibration anchor."""
        return self.rung % 4 == 0


def degrees_of(letter: str) -> float:
    """The letter's angle on the ladder. The redeem direction: code -> wave."""
    for entry in MASTER_TABLE.all_entries():
        if entry.char == letter:
            return entry.vector[0] * QUANTUM_DEG
    raise KeyError(f"no sealed letter {letter!r}")


def rung_of(degrees: float) -> int:
    """Nearest quarter turn to an unwrapped angle."""
    return round(degrees / QUANTUM_DEG)


def lock_angle(degrees: float) -> Lock:
    """Snap one already-unwrapped angle. `PhaseLock` is what handles a stream."""
    rung = rung_of(degrees)
    return Lock(
        rung=rung,
        unwrapped_deg=float(degrees),
        residual_deg=degrees - rung * QUANTUM_DEG,
        letters=RUNGS.get(rung, ()),
    )


def phase_ramp(hz: float, sample_rate: float, samples: int,
               phase0_deg: float = 0.0) -> List[float]:
    """A tone, as the wrapped phase a detector would actually report.

    Wrapped on purpose: handing `PhaseLock` pre-unwrapped phase would test
    the arithmetic against itself and skip the only hard part.
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    step = 360.0 * hz / sample_rate
    return [(phase0_deg + n * step) % 360.0 for n in range(samples)]


class PhaseLock:
    """Wrapped phase in, cumulative rungs out.

    Holds the accumulator, so it is stateful by nature: rung 4 and rung 8
    are the same wrapped phase and only the history separates them.
    """

    def __init__(self) -> None:
        self._last_wrapped: float | None = None
        self._unwrapped: float = 0.0

    @property
    def unwrapped_deg(self) -> float:
        """Turning accumulated so far."""
        return self._unwrapped

    def reset(self) -> None:
        """Drop the history. The next sample starts a new ladder at its own phase."""
        self._last_wrapped = None
        self._unwrapped = 0.0

    def feed(self, wrapped_deg: float) -> Lock:
        """One sample of wrapped phase, unwrapped against the accumulator.

        The step is taken as the shortest signed path, which is the choice
        that makes the sampling limit real: a true step beyond half a turn
        comes back as its short complement, with the wrong sign.
        """
        w = wrapped_deg % 360.0
        if self._last_wrapped is None:
            self._unwrapped = w
        else:
            self._unwrapped += ((w - self._last_wrapped + 180.0) % 360.0) - 180.0
        self._last_wrapped = w
        return lock_angle(self._unwrapped)

    def sequence(self, wrapped: Sequence[float]) -> List[Lock]:
        """Feed a stream. This is the wave becoming a sequence."""
        return [self.feed(sample) for sample in wrapped]
