# -*- coding: utf-8 -*-
"""Modular wave — CMASS, the node counter and Ka'bah as one pipeline.

**Why these two systems belong in one.** A classifier that says "this region
is high entropy" is worth nothing if an attacker can rewrite that verdict
downstream. Triage output is untrusted until something authenticates it, and
Ka'bah's layer 3 is exactly that. So the composition is not two tools stapled
together: the counter produces findings, and the seal is what makes the
findings survive the trip to whoever acts on them.

**The wave.** Data enters as bits on a wire, with no alignment given, and
comes out as an authenticated report. Every stage takes its input per clock,
has a fixed latency, and branches on nothing:

    stage 1   CMASS        bits per clock, no byte boundary assumed
                           -> discovers phase and period by counting
    stage 2   node counter aligned bytes per clock
                           -> class per window, XOR key where one exists
    stage 3   report       canonical encoding, fixed width, one reading
    stage 4   Ka'bah       HMAC-SHA256 over a seal-bound key
                           -> the findings become tamper-evident

Stages 1 and 2 exist in RTL (``rtl/hijaiyyah_wave.v``) and run at line rate.
**Stage 4 does not**: HMAC-SHA256 is in RTL only as a slot of its own
(``rtl/hijaiyyah_hmac.v``, 1 October 2026), not on this path, so the findings
are unauthenticated until they are signed. A pipeline diagram that implied
otherwise would be the most convincing wrong thing here, so it is said plainly
instead.

**What the composition inherits, and what it does not.** It inherits every
limit measured on the parts, and none of them are softened by putting them
together: high entropy is not malice, compressed and encrypted are the same
object to the counter, base64 defeats the classifier completely, and nothing
here recovers a key from real encryption. What the seal adds is that the
report of those findings cannot be forged — not that the findings mean more
than they did.

**The report is canonical by construction**, which is layer 0's property
rather than a new one: fixed-width integers, one reading per value, no
optional fields and no variable-length anything. Two parties cannot disagree
about what a report says.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from hijaiyyah.crypto.guarded_record import CryptoRefusal, GuardedRecord
from hijaiyyah.crypto.kabah import Kabah
from hijaiyyah.crypto.node_counter import (
    NAMES,
    WINDOW,
    align,
    bitstream,
    classify_window,
    recover_xor_key,
)

#: Report format identifier. One suite, no negotiation — the same posture as
#: the record format, and for the same reason.
REPORT_MAGIC = b"HWV1"

#: Bytes per window entry: class, then recovered XOR key.
ENTRY_LEN = 2


@dataclass(frozen=True)
class WaveReport:
    """What the wave found, before anything authenticates it."""

    phase: int
    period: int
    classes: Tuple[int, ...]
    keys: Tuple[int, ...]

    def to_bytes(self) -> bytes:
        """Canonical: fixed width throughout, so there is one reading."""
        if not 0 <= self.phase < 8:
            raise CryptoRefusal(f"phase {self.phase} is outside one byte period")
        if not 1 <= self.period <= 0xFF:
            raise CryptoRefusal(f"period {self.period} does not fit one byte")
        if len(self.classes) != len(self.keys):
            raise CryptoRefusal("a class without its key, or the reverse")
        body = b"".join(
            bytes((c & 0xFF, k & 0xFF))
            for c, k in zip(self.classes, self.keys, strict=True)
        )
        return (
            REPORT_MAGIC
            + bytes((self.phase, self.period))
            + len(self.classes).to_bytes(4, "big")
            + body
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "WaveReport":
        """Parse strictly. Nothing is repaired and trailing bytes are refused."""
        head = len(REPORT_MAGIC) + 2 + 4
        if len(data) < head:
            raise CryptoRefusal(f"report is {len(data)} bytes; too short")
        if data[: len(REPORT_MAGIC)] != REPORT_MAGIC:
            raise CryptoRefusal("not a wave report: wrong magic")
        phase, period = data[4], data[5]
        count = int.from_bytes(data[6:head], "big")
        if len(data) != head + count * ENTRY_LEN:
            raise CryptoRefusal(
                f"header declares {count} windows, which does not match the "
                f"{(len(data) - head) // ENTRY_LEN} that follow"
            )
        body = data[head:]
        return cls(
            phase,
            period,
            tuple(body[i] for i in range(0, len(body), ENTRY_LEN)),
            tuple(body[i + 1] for i in range(0, len(body), ENTRY_LEN)),
        )

    def summary(self) -> dict:
        """Counts per class, by name."""
        return {
            name: self.classes.count(code)
            for code, name in sorted(NAMES.items())
        }


class Wave:
    """The pipeline, wired. Nothing new is computed here; it is composition."""

    def __init__(self, master: Optional[bytes] = None, purpose: str = "wave") -> None:
        self._kabah = Kabah(master, purpose, track_replays=False)

    # ── stages 1-3 ───────────────────────────────────────────────
    @staticmethod
    def survey(bits: Sequence[int]) -> WaveReport:
        """Align a raw bitstream, then classify every complete window.

        No byte boundary goes in. Phase and period come out of counting, and
        the windows are cut from the stream the alignment produced — not from
        an offset chosen by whoever handed over the bits.
        """
        phase, period, data = align(bits)
        classes: List[int] = []
        keys: List[int] = []
        for start in range(0, len(data) - WINDOW + 1, WINDOW):
            window = data[start : start + WINDOW]
            classes.append(classify_window(window))
            keys.append(recover_xor_key(window))
        return WaveReport(phase, period, tuple(classes), tuple(keys))

    @staticmethod
    def survey_bytes(data: bytes, offset: int = 0) -> WaveReport:
        """Convenience for callers holding bytes rather than a wire."""
        return Wave.survey(bitstream(data, offset))

    # ── stage 4 ──────────────────────────────────────────────────
    def seal(self, report: WaveReport) -> GuardedRecord:
        """Authenticate the findings so they survive the trip to whoever acts."""
        return self._kabah.seal(report.to_bytes())

    def open(self, record: GuardedRecord) -> WaveReport:
        """Recover findings, or refuse. A failed MAC returns nothing at all."""
        return WaveReport.from_bytes(self._kabah.open(record))

    # ── the whole wave ───────────────────────────────────────────
    def run(self, bits: Sequence[int]) -> GuardedRecord:
        """Bits on a wire in, an authenticated report out."""
        return self.seal(self.survey(bits))
