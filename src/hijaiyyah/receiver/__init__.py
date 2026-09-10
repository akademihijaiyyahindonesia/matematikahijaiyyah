"""The receive path: a signal arrives, candidates leave.

`core/` and `algebra/` read Theta-hat off letter geometry. This package
reads it off an incoming phase, on the same grid and with the same quantum,
and narrows what is left with the period the letter emits.

Named for the role `net.HCServer` was reserved for and never filled. It is
deliberately not called `wave`: `crypto/wave.py` already uses that word for
the CMASS-to-seal pipeline, and `cosmic-codex-jim/WAVE.md` uses it for the
emitted bit stream. Three different things, and a fourth reuse of the word
would have made all three harder to read.
"""

from .identify import (
    BOARD_CLOCK_HZ,
    MATRIX_ORDERS,
    MOTIFS,
    SIGNATURES,
    WIRE_PERIODS,
    emitted_cycle,
    matrix_period,
    narrow,
    tone_hz,
)
from .lock import (
    QUANTUM_DEG,
    RUNGS,
    Lock,
    PhaseLock,
    degrees_of,
    lock_angle,
    phase_ramp,
    rung_of,
)
from .rx import Anchor, RangeReceiver

__all__ = [
    "BOARD_CLOCK_HZ",
    "MATRIX_ORDERS",
    "MOTIFS",
    "QUANTUM_DEG",
    "RUNGS",
    "SIGNATURES",
    "WIRE_PERIODS",
    "Anchor",
    "Lock",
    "PhaseLock",
    "RangeReceiver",
    "degrees_of",
    "emitted_cycle",
    "lock_angle",
    "matrix_period",
    "narrow",
    "phase_ramp",
    "rung_of",
    "tone_hz",
]
