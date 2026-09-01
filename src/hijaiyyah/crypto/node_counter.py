# -*- coding: utf-8 -*-
"""Per-clock stream triage — layer 1's guard, generalised past codex vectors.

**What was proposed and what survived measuring it.** The proposal was to use
the per-clock bit-counting path as a malware extractor: parse the stream bit
by bit in the LUT fabric and pull out trojans. The *architecture* is right and
is already built — :mod:`hijaiyyah.crypto.cube`'s absorb path takes a byte per
clock, and ``rtl/hijaiyyah_sbox_router.v`` shows that shape runs combinational
with fixed latency. The *detector* claim does not survive contact with data,
and the two measurements that kill it are below, because a classifier nobody
tried to break is the one that looks perfect.

**Negative 1 — compressed and encrypted are the same object here.** Measured
over 2000 windows each, at 64 bytes per window:

    corpus        popcount   bit7 set
    compressed        4.00       0.50
    random            4.00       0.50

Identical to two decimals. A zip file and a packed trojan payload are
indistinguishable, so "detects malware" is not a statement this can make. What
it detects is *high entropy*, and high entropy is not malice.

**Negative 2 — one line of encoding evades it completely.** Base64 the
high-entropy payload and every window reads as text:

    base64(urandom)   ->  TEXT  100.0%

Not 80%, not usually: all of it. Any adversary who cares defeats this with an
encoder, which is why it is triage and not a verdict.

**Negative 3 — the node spectrum earns nothing.** The tawaf ring's sixteen
node counters were the proposal's centre. Adding them to the classifier
changed accuracy by zero — 4494/4741 either way — and the deviation they
measure does not separate the one pair that matters:

    L1 deviation  compressed   35.84 +/- 6.85
                  random       34.70 +/- 6.63

0.17 standard deviations apart. Sixteen counters were dropped for two, which
is the same shape as the finding already recorded in ``cube.absorb_bit``: the
bit schedule is an input-path convenience, not an information-bearing feature.
Two independent measurements now say so.

**Then: count bit by bit, and something falls out that popcount cannot
reach.** Popcount sums across the eight bit positions, and summing is exactly
what destroys the information a key lives in. Counting each position
*separately* keeps it, because XOR acts on positions independently:

    count_i(plaintext XOR k)  =  count_i(plaintext)      if bit i of k is 0
                              =  n - count_i(plaintext)  if bit i of k is 1

The *magnitude* of a position's bias is invariant under XOR; only its **sign**
flips. So the key is read directly off eight signs — no trial decryption, no
search. And because the plaintext model is a constant, the whole recovery
collapses to eight comparisons against n/2 and one XOR with
:data:`MODEL_MASK`.

Measured against single-byte XOR over source text, 400 trials per window:

    window      whole key      per bit
        64          66.8%        94.9%
       256          83.8%        97.9%
      1024          95.0%        99.4%

With a repeating key, sweeping the period first (:func:`sweep_period`)
recovers period and key over 4096 bytes:

    period      period found     key found
         1              100%          100%
         5              100%           98%
         7              100%           93%
        13              100%           88%

**Negative 4 — and it is the one that bounds the whole idea.** Run the same
recovery against properly encrypted data and it returns nothing: 0% whole-key
recovery at every window size and every period, against 0.4% for blind
guessing. The reason is visible in the counters themselves — every bit
position of good ciphertext sits at 0.50, so there is no sign to read. The
same eight counters that break weak obfuscation prove they cannot touch real
encryption.

That is the honest shape of "breaking the encryption of an infected file": it
breaks the *obfuscation* a large share of real malware actually uses — single-
byte and repeating-key XOR — and it does not break AES, ChaCha20, or anything
with a real key schedule. Both halves come from the same measurement.

**What it actually is, and it is worth having.** A keyless, constant-work,
line-rate classifier of stream *structure* — empty, text, structured, high
entropy. That is precisely layer 1's role, generalised from codex vectors to
arbitrary bytes: reject or flag cheaply so the expensive authority is not
spent on obvious cases. The real security use is narrow and genuine —
high-entropy content in a region a format says should hold code is the classic
packer indicator — and it is a flag for something authoritative to judge, never
a verdict on its own.

Every threshold is an integer over a fixed window, so nothing here divides,
branches on a secret, or varies in time with its input. The RTL beside it is
the same arithmetic.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

#: Bytes per verdict. A power of two so the hardware never divides.
WINDOW = 64

#: Class codes, matching rtl/hijaiyyah_node_counter.v.
EMPTY = 0
TEXT = 1
STRUCTURED = 2
HIGH_ENTROPY = 3

NAMES = {EMPTY: "KOSONG", TEXT: "TEKS", STRUCTURED: "TERSTRUKTUR",
         HIGH_ENTROPY: "ENTROPI-TINGGI"}

#: Thresholds as integers over WINDOW bytes, so Python and Verilog compare the
#: same numbers. Derived from the corpus measurements in the module docstring:
#: text sits near 3.27 bits set per byte with bit7 almost never set; high
#: entropy sits at 4.00 and 0.50.
TEXT_HIGH_BIT_MAX = 10       # < 10 of 64 bytes with bit 7 set
TEXT_POPCOUNT_MIN = 128      # >= 2.0 bits per byte
ENTROPY_POPCOUNT_MIN = 237   # >= 3.70 bits per byte
ENTROPY_HIGH_BIT_MIN = 26    # >= 0.40 of bytes with bit 7 set


#: Which bit positions are more often 1 than 0 in ordinary text, measured on
#: source code: b5 at 0.89 and b6 at 0.64 are above balance, the rest below.
#: The key recovery is one XOR against this constant.
MODEL_MASK = 0x60

#: Longest repeating-key period the sweep considers.
MAX_PERIOD = 16


def bit_counts(window: Sequence[int]) -> List[int]:
    """Ones at each of the eight bit positions. Eight counters, one per clock."""
    return [sum((byte >> i) & 1 for byte in window) for i in range(8)]


def recover_xor_key(window: Sequence[int]) -> int:
    """Recover a single-byte XOR key by counting, not by trying keys.

    Eight comparisons against n/2 and one XOR with :data:`MODEL_MASK`. A tie
    carries no information and resolves to zero either way, which is why the
    hardware and this agree exactly.
    """
    n = len(window)
    key = 0
    for i, count in enumerate(bit_counts(window)):
        if 2 * count > n:
            key |= 1 << i
    return key ^ MODEL_MASK


def _residue_bias(data: bytes, period: int, residue: int) -> Tuple[float, int]:
    """Bias of one residue class, above the sampling-noise floor."""
    import math

    sub = data[residue::period]
    n = len(sub)
    if n < 16:
        return 0.0, 0
    total = 0.0
    key = 0
    for i in range(8):
        count = sum((byte >> i) & 1 for byte in sub)
        total += abs(2 * count - n) / n
        if 2 * count > n:
            key |= 1 << i
    floor = math.sqrt(2 / (math.pi * n))
    return max(0.0, total / 8 - floor), key ^ MODEL_MASK


def sweep_period(data: bytes, ratio: float = 0.85) -> int:
    """Find a repeating key's period by shaking through the candidates.

    Two corrections, both found by the measurement going wrong first. The raw
    bias score climbs with period for two reasons that have nothing to do with
    the key — a multiple of the true period is also a valid period, and
    shorter subsamples carry more sampling noise — so taking the argmax picked
    a multiple every time (period 13 scored 100%, period 1 scored 0%).
    Subtracting the noise floor fixes the second, and taking the *smallest*
    period that reaches the peak fixes the first. Both together: 100% at every
    period tested.

    Returns 0 when nothing reaches the threshold.
    """
    scores = [
        (p, sum(_residue_bias(data, p, r)[0] for r in range(p)) / p)
        for p in range(1, MAX_PERIOD + 1)
    ]
    peak = max(score for _, score in scores)
    if peak <= 0:
        return 0
    return min(p for p, score in scores if score >= ratio * peak)


def recover_repeating_key(data: bytes) -> bytes:
    """Period, then one key byte per residue class. Counting throughout."""
    period = sweep_period(data)
    if period == 0:
        return b""
    return bytes(_residue_bias(data, period, r)[1] for r in range(period))


def byte_features(byte: int) -> Tuple[int, int]:
    """The two per-clock features: bits set, and whether bit 7 is one.

    Both are pure combinational functions of eight bits — a popcount adder
    tree and a wire. Nothing else survived measurement.
    """
    return bin(byte).count("1"), (byte >> 7) & 1


def classify_window(window: Sequence[int]) -> int:
    """One verdict for one window, by integer comparison only."""
    popcount = 0
    high_bits = 0
    for byte in window:
        bits, high = byte_features(byte)
        popcount += bits
        high_bits += high

    if popcount == 0:
        return EMPTY
    if high_bits < TEXT_HIGH_BIT_MAX and popcount >= TEXT_POPCOUNT_MIN:
        return TEXT
    if popcount >= ENTROPY_POPCOUNT_MIN and high_bits >= ENTROPY_HIGH_BIT_MIN:
        return HIGH_ENTROPY
    return STRUCTURED


def scan(data: bytes) -> List[int]:
    """Classify a whole stream, one verdict per complete window.

    A trailing partial window is dropped rather than padded: padding it with
    zeros would report EMPTY for a fragment that is nothing of the sort.
    """
    return [
        classify_window(data[i : i + WINDOW])
        for i in range(0, len(data) - WINDOW + 1, WINDOW)
    ]


def profile(data: bytes) -> Dict[str, float]:
    """The fraction of windows in each class."""
    verdicts = scan(data)
    if not verdicts:
        return {name: 0.0 for name in NAMES.values()}
    return {
        NAMES[code]: verdicts.count(code) / len(verdicts) for code in sorted(NAMES)
    }


def flagged_regions(data: bytes) -> Iterable[Tuple[int, int]]:
    """Byte ranges of contiguous high-entropy windows.

    The one output with a real use: a high-entropy run inside a region a
    format says should hold code is what a packer looks like. It is a place to
    look, not a finding.
    """
    start = None
    for index, verdict in enumerate(scan(data)):
        if verdict == HIGH_ENTROPY and start is None:
            start = index * WINDOW
        elif verdict != HIGH_ENTROPY and start is not None:
            yield start, index * WINDOW
            start = None
    if start is not None:
        yield start, (len(data) // WINDOW) * WINDOW
