# -*- coding: utf-8 -*-
"""Cube Hijaiyyah — a sponge over the sealed exomatrix cube. **[EH]**

Epistemic label first, because it decides how everything below should be read.
This is an **engineering hypothesis**, in the book's own §I.14 sense. It is
built, it is measured, and it is *not* a cipher anyone should deploy. A new
permutation has had no public cryptanalysis, and cryptanalysis is the only
thing that makes a primitive trustworthy. What can be done here is build it
carefully, measure it against the metrics that decide whether a construction
is even a candidate, and report the numbers without decoration.

**Why a cube, and where it comes from.** The codex is an 18-dimensional vector,
which is the wrong shape for a permutation: mixing wants a grid so that
diffusion has two directions to travel. Bab II §IIE.2.1 already defines the
Letter Exomatrix E(h), a 5×5 matrix per letter, and the alphabet is 28 letters.
Stacking them gives a 5×5×28 cube that is derived rather than invented.

**Why a sponge.** Because it is the framework where a permutation's security
reduces to properties of the permutation itself, which are measurable. Keccak
made this standard: absorb, permute, squeeze. Building anything else would mean
inventing the framework as well as the primitive, and then nothing could be
evaluated at all.

**Where the mixing actually comes from, said plainly.** The S-box is a
bijection on 0..255 produced by a deterministic shuffle seeded from the sealed
cube. The cube supplies the seed and the reproducibility; SHA-256 supplies the
mixing. Claiming the geometry does the cryptographic work would be false, and
the measurements below are what the construction is entitled to claim instead.

**Tawaf decides the schedule, and it corrects an arbitrary choice.** The first
version filled lanes 0..7 in order and called eight of them the rate, which
was a number picked rather than derived. A circuit around a centre decomposes
the 5×5 face on its own: sixteen lanes on the perimeter, eight on the inner
ring, one at the centre. The perimeter takes the data; the nine it encloses
are never touched by input, which is exactly what a sponge means by capacity.
Absorption walks that circuit rather than raster order, and the permutation
runs seven times because tawaf is seven.

Lane width followed from the same correction. Eight-bit lanes put the state at
200 bits and the capacity at 72 — about 36 bits of security, which is not
security. Sixty-four-bit lanes give 1600 bits, the size Keccak settled on, and
the ring split then yields 576 bits of capacity and about 288 of security.

Seven circuits is fewer than Keccak's twenty-four, and the cost is stated
rather than hidden: fewer rounds is less margin, and margin is what absorbs
cryptanalysis nobody has done yet. What seven does buy is measured — a single
changed bit reaches all twenty-five lanes and moves about half the state.

The S-box is a 256-entry lookup, which on the Tang Nano is block RAM rather
than logic, and absorption needs no multiplier and no division.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Sequence, Tuple

from hijaiyyah.core.exomatrix import build_exomatrix
from hijaiyyah.core.master_table import MASTER_TABLE

#: The exomatrix is 5×5 (§IIE.2.1) and the alphabet is 28 letters.
ROWS = COLS = 5
LAYERS = 28

#: Lane width. The first version used 8-bit lanes, which put the whole state
#: at 200 bits and the capacity at 72 — about 36 bits of security, which is
#: not security. 64-bit lanes give a 1600-bit state, the same size Keccak
#: settled on, and the ring split below then yields 288.
LANE_BITS = 64
LANE_MASK = (1 << LANE_BITS) - 1
LANE_BYTES = LANE_BITS // 8

#: Circuits of the permutation. Tawaf is seven.
CIRCUITS = 7


def _rings() -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    """Split the 5×5 face into an outer ring and everything it encloses.

    This is where the absorption schedule stops being arbitrary. The first
    version filled lanes 0..7 in order and called eight of them the rate,
    which was a number chosen rather than derived. A circuit around a centre
    decomposes the face on its own: 16 lanes on the perimeter, 8 on the inner
    ring, 1 at the centre.

    The outer ring takes the data; the nine it encloses are never touched by
    input, which is precisely what a sponge means by capacity. Rate and
    capacity fall out of the geometry instead of being picked.
    """
    outer, inner = [], []
    for row in range(ROWS):
        for col in range(COLS):
            index = row * COLS + col
            if row in (0, ROWS - 1) or col in (0, COLS - 1):
                outer.append(index)
            else:
                inner.append(index)
    return tuple(outer), tuple(inner)


OUTER_RING, CORE = _rings()

#: Absorption walks the perimeter as one closed circuit rather than raster
#: order, so consecutive input lands on adjacent lanes, and the walk closes on
#: itself the way a circuit does.
TAWAF_PATH: Tuple[int, ...] = (
    tuple(range(COLS))                                              # top edge
    + tuple(r * COLS + (COLS - 1) for r in range(1, ROWS))           # right edge
    + tuple((ROWS - 1) * COLS + c for c in range(COLS - 2, -1, -1))  # bottom edge
    + tuple(r * COLS for r in range(ROWS - 2, 0, -1))                # left edge
)

#: Lanes, and the bytes each part of the split carries.
STATE_LANES = ROWS * COLS
RATE_LANES = len(OUTER_RING)
RATE = RATE_LANES * LANE_BYTES
CAPACITY_BITS = len(CORE) * LANE_BITS

#: Sponge security is about capacity/2.
SECURITY_BITS = CAPACITY_BITS // 2


def build_cube() -> Tuple[Tuple[Tuple[int, ...], ...], ...]:
    """The 5×5×28 cube: one exomatrix per sealed letter, in ROM order."""
    return tuple(
        tuple(tuple(row) for row in build_exomatrix(list(entry.vector)))
        for entry in MASTER_TABLE.all_entries()
    )


def cube_digest() -> bytes:
    """SHA-256 over the cube in canonical order.

    Every value that seeds the construction, in one deterministic reading, so
    a change anywhere in the sealed table changes the S-box.
    """
    flat = bytearray()
    for layer in build_cube():
        for row in layer:
            flat.extend(row)
    return hashlib.sha256(bytes(flat)).digest()


# ── Substitution ─────────────────────────────────────────────────

def derive_sbox() -> Tuple[int, ...]:
    """A bijection on 0..255, seeded by the sealed cube.

    Fisher-Yates driven by SHA-256 in counter mode over the cube digest. The
    shuffle is what guarantees bijectivity; the cube decides which permutation
    of the 256! available is chosen, and does so reproducibly.
    """
    box = list(range(256))
    seed = cube_digest()

    stream = bytearray()
    counter = 0
    for i in range(255, 0, -1):
        while not stream:
            stream.extend(
                hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            )
            counter += 1
        # Rejection-free: modulo bias over i+1 is acceptable here because the
        # result only has to be a fixed permutation, not a uniform one.
        j = stream.pop() % (i + 1)
        box[i], box[j] = box[j], box[i]
    return tuple(box)


SBOX: Tuple[int, ...] = derive_sbox()
INV_SBOX: Tuple[int, ...] = tuple(
    SBOX.index(value) for value in range(256)
)


# ── Measurement ──────────────────────────────────────────────────

def is_bijection(box: Sequence[int] = SBOX) -> bool:
    """A substitution that loses values cannot be inverted."""
    return sorted(box) == list(range(256))


def differential_uniformity(box: Sequence[int] = SBOX) -> int:
    """The largest count in the difference distribution table.

    For every input difference a ≠ 0 and output difference b, count the inputs
    with S(x) ⊕ S(x⊕a) = b. The maximum is what a differential attack exploits:
    lower is better. AES reaches 4. A random bijection sits far higher, and
    that gap is the difference between an algebraic construction and a
    shuffled one.
    """
    worst = 0
    for a in range(1, 256):
        counts = [0] * 256
        for x in range(256):
            counts[box[x] ^ box[x ^ a]] += 1
        worst = max(worst, max(counts))
    return worst


def linearity(box: Sequence[int] = SBOX) -> int:
    """The largest Walsh coefficient magnitude, over all nonzero masks.

    Nonlinearity is 128 − linearity/2. AES reaches nonlinearity 112, which is
    linearity 32. Higher linearity means a better linear approximation exists,
    which is what a linear attack exploits.
    """
    worst = 0
    for a in range(1, 256):
        for b in range(1, 256):
            total = 0
            for x in range(256):
                parity = bin((a & x) ^ (b & box[x])).count("1") & 1
                total += 1 if parity == 0 else -1
            worst = max(worst, abs(total))
    return worst


def nonlinearity(box: Sequence[int] = SBOX) -> int:
    """128 − linearity/2, the usual way the same measurement is reported."""
    return 128 - linearity(box) // 2


def avalanche(box: Sequence[int] = SBOX) -> float:
    """Mean fraction of output bits that change when one input bit flips.

    An ideal substitution sits at 0.5. This is the cheapest sanity check and
    the least discriminating: a bad S-box can still pass it.
    """
    total = 0
    for x in range(256):
        for bit in range(8):
            total += bin(box[x] ^ box[x ^ (1 << bit)]).count("1")
    return total / (256 * 8 * 8)


def measure(box: Sequence[int] = SBOX) -> Dict[str, object]:
    """Every metric, with AES quoted alongside for scale."""
    return {
        "bijection": is_bijection(box),
        "differential_uniformity": differential_uniformity(box),
        "linearity": linearity(box),
        "nonlinearity": nonlinearity(box),
        "avalanche": avalanche(box),
        "aes_differential_uniformity": 4,
        "aes_nonlinearity": 112,
    }


# ── Permutation ──────────────────────────────────────────────────

def _round_constants() -> Tuple[int, ...]:
    """One constant per circuit, from the cube digest.

    Round constants break the symmetry that would otherwise let a state of
    equal lanes stay equal. Keccak takes its from an LFSR; these come from the
    sealed cube, which is the same idea with a different source.
    """
    material = hashlib.sha256(cube_digest() + b"tawaf").digest()
    return tuple(
        int.from_bytes(material[i * 8 : (i + 1) * 8], "big") & LANE_MASK
        if (i + 1) * 8 <= len(material)
        else int.from_bytes(
            hashlib.sha256(material + bytes([i])).digest()[:8], "big"
        ) & LANE_MASK
        for i in range(CIRCUITS)
    )


ROUND_CONSTANTS = _round_constants()


def _rotl(value: int, amount: int) -> int:
    amount %= LANE_BITS
    return ((value << amount) | (value >> (LANE_BITS - amount))) & LANE_MASK


def _substitute(lane: int) -> int:
    """The byte S-box applied across a lane, eight bytes at a time."""
    out = 0
    for i in range(LANE_BYTES):
        out |= SBOX[(lane >> (8 * i)) & 0xFF] << (8 * i)
    return out


def permute(state: List[int]) -> List[int]:
    """Seven circuits: substitute, mix rows, mix columns, add a constant.

    Seven because tawaf is seven. That is a smaller number than Keccak's
    twenty-four, and the cost is stated rather than hidden: fewer rounds is
    less margin, and margin is what absorbs cryptanalysis nobody has done yet.
    The diffusion test asserts a single changed bit still reaches every lane,
    which is the minimum seven has to buy.
    """
    if len(state) != STATE_LANES:
        raise ValueError(f"state must be {STATE_LANES} lanes, got {len(state)}")

    s = [lane & LANE_MASK for lane in state]
    for circuit in range(CIRCUITS):
        s = [_substitute(lane) for lane in s]

        for row in range(ROWS):
            base = row * COLS
            acc = 0
            for col in range(COLS):
                acc ^= s[base + col]
            for col in range(COLS):
                s[base + col] ^= _rotl(acc, col + circuit + 1)

        for col in range(COLS):
            acc = 0
            for row in range(ROWS):
                acc ^= s[row * COLS + col]
            for row in range(ROWS):
                index = row * COLS + col
                s[index] = _rotl(s[index] ^ acc, row * COLS + col + 1)

        s[0] ^= ROUND_CONSTANTS[circuit]
    return s


# ── Sponge ───────────────────────────────────────────────────────

def absorb_lane(state: List[int], value: int, step: int) -> Tuple[List[int], int]:
    """Absorb one lane's worth of data at the next stop on the circuit.

    Input only ever reaches the outer ring. The nine lanes it encloses are the
    capacity, and nothing written from outside touches them — that separation
    is what a sponge's security rests on, and here it is the geometry rather
    than an index range.
    """
    s = list(state)
    s[TAWAF_PATH[step]] ^= value & LANE_MASK
    step += 1
    if step == RATE_LANES:
        s = permute(s)
        step = 0
    return s, step


def digest(data: bytes, length: int = 32) -> bytes:
    """Sponge over the cube permutation. **[EH] — not a vetted hash.**

    Use SHA-256 for anything that matters. This exists to be measured, and to
    give the FPGA something to stream.
    """
    state = [0] * STATE_LANES
    step = 0

    padded = bytearray(data)
    padded.append(0x01)
    while len(padded) % RATE:
        padded.append(0x00)
    padded[-1] ^= 0x80

    for offset in range(0, len(padded), LANE_BYTES):
        lane = int.from_bytes(padded[offset : offset + LANE_BYTES], "little")
        state, step = absorb_lane(state, lane, step)

    out = bytearray()
    while len(out) < length:
        for index in TAWAF_PATH:
            out.extend(state[index].to_bytes(LANE_BYTES, "little"))
            if len(out) >= length:
                break
        if len(out) < length:
            state = permute(state)
    return bytes(out[:length])
