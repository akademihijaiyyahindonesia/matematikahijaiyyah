"""Lock mode: the range receiver `HCServer` was a placeholder for.

`net/server.py` held a class called `HCServer` that printed a line and had
no callers anywhere in the tree. The name said HTTP server; the role it was
reserved for was a **receiver of an output range** -- the module that catches
the wave and hands back something discrete. This is that module, named for
what it does.

The receiver adds one thing to `PhaseLock`, and it is the thing that makes
"lock mode" a mode rather than a label: **lock can be absent, acquired, and
lost.** A phase lock always returns a rung, even for a sample sitting 44
degrees off grid, and a receiver that reported that rung with the same
confidence as a clean one would be hiding its own error. So the state here
is earned -- `LOCK_AFTER` consecutive samples inside tolerance -- and dropped
the moment a sample falls outside it.

Two outputs, and they answer different questions:

    locks       one Lock per sample: what arrived, sample by sample
    sequence    the rung transitions, runs collapsed: what was said

A held tone spends many samples on one rung. Left uncollapsed it reads as a
repeated symbol, which is a statement about the sample rate rather than about
the signal, so `sequence` reports each rung once per visit and `locks` keeps
the raw stream for anyone measuring drift.

**Calibration rides on the loop tops.** At `rung % 4 == 0` the accumulated
phase is a whole number of turns, so the residual there is measured against
a known zero and reads as drift. `calibration()` returns those anchors in
order; a residual that grows monotonically across them is a clock offset,
not noise.
"""
from __future__ import annotations

from typing import List, NamedTuple, Optional, Sequence, Tuple

from .lock import QUANTUM_DEG, Lock, PhaseLock

__all__ = ["Anchor", "RangeReceiver"]


class Anchor(NamedTuple):
    """A loop top: whole turns completed, and how far off the sample sat.

    `sample` was called `index` and that shadowed `tuple.index` -- the
    method, not just the name. An `Anchor` is a tuple, and asking one
    where a value sits inside it returned the sample number instead of
    searching. Nothing read the field, so nothing had yet been bitten.
    """

    sample: int
    rung: int
    residual_deg: float


class RangeReceiver:
    """Wrapped phase in; a locked rung sequence out.

    Stateful on purpose -- both the unwrapping and the lock state are
    history, and neither can be recovered from a single sample.
    """

    #: Consecutive in-tolerance samples before lock is declared. Above 1 so a
    #: single sample that happens to land near a rung cannot claim lock.
    LOCK_AFTER = 4

    def __init__(self, sample_rate: float = 1.0, tolerance_deg: float = 10.0,
                 lock_after: int | None = None) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if not 0 < tolerance_deg < QUANTUM_DEG / 2:
            raise ValueError(
                f"tolerance must sit inside a rung: 0 < t < {QUANTUM_DEG / 2}")
        self.sample_rate = float(sample_rate)
        self.tolerance_deg = float(tolerance_deg)
        self.lock_after = self.LOCK_AFTER if lock_after is None else lock_after
        self._phase = PhaseLock()
        self._locks: List[Lock] = []
        self._streak = 0
        self._locked = False

    # ── state ────────────────────────────────────────────────────

    @property
    def locked(self) -> bool:
        """True only after `lock_after` consecutive samples inside tolerance."""
        return self._locked

    @property
    def locks(self) -> Tuple[Lock, ...]:
        """Every sample, in order, unmerged."""
        return tuple(self._locks)

    def reset(self) -> None:
        self._phase.reset()
        self._locks.clear()
        self._streak = 0
        self._locked = False

    # ── the stream ───────────────────────────────────────────────

    def feed(self, wrapped_deg: float) -> Lock:
        """One sample. Updates the accumulator and the lock state together."""
        result = self._phase.feed(wrapped_deg)
        if abs(result.residual_deg) <= self.tolerance_deg:
            self._streak += 1
            if self._streak >= self.lock_after:
                self._locked = True
        else:
            self._streak = 0
            self._locked = False
        self._locks.append(result)
        return result

    def receive(self, wrapped: Sequence[float]) -> Tuple[Lock, ...]:
        """Feed a stream and return what it locked to."""
        for sample in wrapped:
            self.feed(sample)
        return self.locks

    # ── the outputs ──────────────────────────────────────────────

    @property
    def sequence(self) -> Tuple[int, ...]:
        """Rung transitions, runs collapsed. The wave, as a sequence."""
        out: List[int] = []
        for lock in self._locks:
            if not out or out[-1] != lock.rung:
                out.append(lock.rung)
        return tuple(out)

    @property
    def candidates(self) -> Tuple[Tuple[str, ...], ...]:
        """The letters standing on each rung of `sequence`.

        A tuple per rung, never a single letter: a rung carries at most 2.77
        bits and a letter needs 4.81. Empty where the rung holds none.
        """
        from .lock import RUNGS
        return tuple(RUNGS.get(rung, ()) for rung in self.sequence)

    @property
    def rejected(self) -> Tuple[int, ...]:
        """Positions in `sequence` whose rung holds no letter -- rung 7, or off
        the ladder entirely. On grid and outside the alphabet."""
        return tuple(i for i, letters in enumerate(self.candidates) if not letters)

    def calibration(self) -> Tuple[Anchor, ...]:
        """Residual at each loop top, in order. Drift, against a known zero."""
        return tuple(
            Anchor(i, lock.rung, lock.residual_deg)
            for i, lock in enumerate(self._locks)
            if lock.is_loop_top
        )

    def frequency_hz(self) -> Optional[float]:
        """Recovered from total turning, not from the collapsed sequence.

        The sequence is quantised to quarter turns and would give a frequency
        quantised with it; the accumulator holds the continuous span, so the
        estimate comes from there. Meaningless above half the sample rate --
        see the unwrapping note in `lock`.

        **Returns None, not 0.0, when there is nothing to measure.** The first
        version returned zero for "fewer than two samples", and zero is also
        the correct answer for a phase that never moved. One number for
        "nothing arrived" and "a constant arrived" is the same defect class as
        `OP_NOP = 8'h00`, where erased instruction memory and memory full of
        NOPs are identical bits -- a bug that survived every simulation this
        project ever ran, because the silence had a legal encoding. A caller
        that cannot tell the two apart cannot report either honestly, so
        absence is given a value of its own.
        """
        if len(self._locks) < 2:
            return None
        span = self._locks[-1].unwrapped_deg - self._locks[0].unwrapped_deg
        return span / 360.0 * self.sample_rate / (len(self._locks) - 1)
