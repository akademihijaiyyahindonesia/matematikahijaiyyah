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

Byte-per-clock absorption is the shape the HCPU wants: one byte in, one lane
updated, no wide multiplier and no division. The S-box is a 256-entry lookup,
which on the Tang Nano is block RAM rather than logic.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Sequence, Tuple

from hijaiyyah.core.exomatrix import build_exomatrix
from hijaiyyah.core.master_table import MASTER_TABLE

#: The exomatrix is 5×5 (§IIE.2.1) and the alphabet is 28 letters.
ROWS = COLS = 5
LAYERS = 28

#: Sponge state: 5×5 lanes of one byte — 200 bits.
STATE_BYTES = ROWS * COLS

#: Bytes absorbed before a permutation. Capacity is STATE_BYTES - RATE.
RATE = 8

#: Rounds per permutation.
ROUNDS = 12


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
    """One constant per round, from the cube digest.

    Round constants break the symmetry that would otherwise let a state of
    all-equal lanes stay that way. Keccak takes its from an LFSR; these come
    from the sealed cube, which is the same idea with a different source.
    """
    material = hashlib.sha256(cube_digest() + b"rounds").digest()
    return tuple(material[i] for i in range(ROUNDS))


ROUND_CONSTANTS = _round_constants()


def permute(state: List[int]) -> List[int]:
    """The cube permutation: substitute, mix rows, mix columns, add constant.

    Four steps per round, each with one job — the separation Keccak's θ, ρ, π,
    χ, ι established. Substitution is the only nonlinear step; everything else
    moves information sideways so that one changed byte reaches every lane.
    """
    if len(state) != STATE_BYTES:
        raise ValueError(f"state must be {STATE_BYTES} bytes, got {len(state)}")

    s = list(state)
    for r in range(ROUNDS):
        s = [SBOX[b] for b in s]

        # Rows: each lane takes its row's running parity, so a change spreads
        # along the row within one round.
        for row in range(ROWS):
            base = row * COLS
            acc = 0
            for col in range(COLS):
                acc ^= s[base + col]
            for col in range(COLS):
                s[base + col] ^= acc ^ ((col + r) & 0xFF)

        # Columns, rotated, so diffusion travels the other axis too.
        for col in range(COLS):
            acc = 0
            for row in range(ROWS):
                acc ^= s[row * COLS + col]
            for row in range(ROWS):
                index = row * COLS + col
                rot = (row + col + 1) & 7
                mixed = s[index] ^ acc
                s[index] = ((mixed << rot) | (mixed >> (8 - rot))) & 0xFF

        s[0] ^= ROUND_CONSTANTS[r]
    return s


# ── Sponge ───────────────────────────────────────────────────────

def absorb_byte(state: List[int], byte: int, position: int) -> Tuple[List[int], int]:
    """Absorb one byte into one lane — the shape the HCPU wants.

    One byte in, one lane XORed, no multiplier and no division. The
    permutation runs when the rate is full, which is the only step that costs
    more than a clock.
    """
    s = list(state)
    s[position] ^= byte & 0xFF
    position += 1
    if position == RATE:
        s = permute(s)
        position = 0
    return s, position


def digest(data: bytes, length: int = 32) -> bytes:
    """Sponge over the cube permutation. **[EH] — not a vetted hash.**

    Use SHA-256 for anything that matters. This exists to be measured, and to
    give the FPGA something to run byte per clock.
    """
    state = [0] * STATE_BYTES
    position = 0

    for byte in data:
        state, position = absorb_byte(state, byte, position)

    # Padding: a 0x01 marker then zeros, so two messages differing only in
    # trailing zero bytes cannot absorb identically.
    state[position] ^= 0x01
    state[RATE - 1] ^= 0x80
    state = permute(state)

    out = bytearray()
    while len(out) < length:
        out.extend(state[:RATE])
        state = permute(state)
    return bytes(out[:length])
