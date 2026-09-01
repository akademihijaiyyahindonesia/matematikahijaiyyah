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

**The substitution is algebraic, and that was a correction.** The first
version shuffled a permutation with SHA-256, which produced a bijection
indistinguishable from random — differential uniformity 10 where AES reaches
4, nonlinearity 92 where AES reaches 112. The substitution is now the
multiplicative inverse in GF(2⁸) read out of log tables, followed by an affine
map, and it measures 4 and 112 exactly.

Said plainly, because the division matters: those properties hold for *every*
irreducible degree-8 polynomial. The sealed cube chooses which of the thirty
fields is used and what the affine constant is; the strength comes from the
inverse map. The geometry selects a member of a family, and crediting it with
the algebra's work would be false.

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

Twenty-eight rounds: four tawaf of seven, which is also the alphabet. The
number comes from measurement. Diffusion saturates at three rounds — round 1
reaches 20 of 25 lanes at avalanche 0.055, round 2 all 25 at 0.302, round 3
sits at 0.496 and nothing after it moves — so three is the floor and the rest
is margin. Seven, the first version, gave 2.3× that floor, and attacks on
constructions of this shape reach two to three times the floor. Seven sat
inside the range. Twenty-eight gives 9.3×, the posture Keccak holds with
twenty-four, and the cost is 150 MB/s falling to 78.5 at 27 MHz.

The S-box is a 256-entry lookup, which on the Tang Nano is block RAM rather
than logic, and absorption needs no multiplier and no division.

**The table is a software side channel, and this is the honest statement of
it.** A 256-entry lookup indexed by data is the exact target of the AES
cache-timing attacks — Bernstein in 2005, then Osvik, Shamir and Tromer in
2006 — where the pattern of cache lines touched leaks the index, and the index
depends on the state. Nothing in this module is constant-time and nothing here
claims to be.

Two things bound what that costs. This layer is keyless: it is the [EH]
sponge, and no key enters it — layer 3's HMAC-SHA256 is where a secret is
touched, and that runs in a vetted constant-time implementation. And the
intended target is HCPU silicon, where the table is one block RAM with a
single fixed access latency and there is no cache to observe. A property
software cannot have and the hardware gets for free is worth naming rather
than leaving for a reader to find.

"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Sequence, Tuple

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

#: Circuits in one tawaf.
CIRCUIT = 7

#: Tawaf performed. Four of them, which is 28 — the alphabet.
TAWAF = 4

#: Rounds of the permutation: 7 × 4 = 28.
#:
#: Not a preference. Diffusion saturates at three rounds, measured: round 1
#: reaches 20 of 25 lanes at avalanche 0.055, round 2 reaches all 25 at 0.302,
#: round 3 sits at 0.496 and nothing after it moves. Three is the floor, and
#: everything above it is margin.
#:
#: Seven gave 2.3× that floor. Attacks on constructions of this shape reach
#: two to three times the diffusion floor — six to nine rounds here — so seven
#: sat inside the range an attack would plausibly reach. Twenty-eight gives
#: 9.3×, which is the posture Keccak holds with twenty-four.
#:
#: The cost is measured too: 150 MB/s falls to 78.5 at 27 MHz.
CIRCUITS = CIRCUIT * TAWAF


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


# ── Substitution: semi-log ───────────────────────────────────────────────

def _mul(a: int, b: int, poly: int) -> int:
    """Carry-less multiply in GF(2⁸) modulo an irreducible polynomial."""
    result = 0
    while b:
        if b & 1:
            result ^= a
        a <<= 1
        if a & 0x100:
            a ^= poly
        b >>= 1
    return result


def _generator(poly: int) -> Optional[int]:
    """The smallest element whose powers cover all 255 non-zero values.

    A polynomial with such an element is irreducible; one without is not, so
    this doubles as the irreducibility test.
    """
    for candidate in range(2, 256):
        seen, x = set(), 1
        for _ in range(255):
            x = _mul(x, candidate, poly)
            seen.add(x)
        if len(seen) == 255:
            return candidate
    return None


def irreducible_polynomials() -> Tuple[Tuple[int, int], ...]:
    """Every irreducible degree-8 polynomial and a generator for each.

    Thirty of them, AES's 0x11B among them.
    """
    return tuple(
        (poly, gen)
        for poly in range(0x100, 0x200)
        if (gen := _generator(poly)) is not None
    )


def _log_tables(poly: int, gen: int) -> Tuple[List[int], List[int]]:
    """Antilog and log for one field — the semi-log step's lookup tables."""
    antilog = [0] * 512
    log = [0] * 256
    x = 1
    for i in range(255):
        antilog[i] = x
        log[x] = i
        x = _mul(x, gen, poly)
    for i in range(255, 512):
        antilog[i] = antilog[i - 255]
    return log, antilog


def _first_fixed_point_free(start: int, poly: int, gen: int) -> int:
    """Walk from the seal's byte to the first constant with no fixed point."""
    log, antilog = _log_tables(poly, gen)

    def inv(value: int) -> int:
        return 0 if value == 0 else antilog[255 - log[value]]

    for offset in range(256):
        candidate = (start + offset) & 0xFF
        if not any(_affine_with(inv(x), candidate) == x for x in range(256)):
            return candidate
    raise RuntimeError("no fixed-point-free affine constant exists in this field")


def _affine_with(byte: int, constant: int) -> int:
    result = byte
    for shift in (1, 2, 3, 4):
        result ^= ((byte << shift) | (byte >> (8 - shift))) & 0xFF
    return result ^ constant


def _field() -> Tuple[int, int, int, List[int], List[int]]:
    """Choose the field from the sealed cube and build its log tables.

    The construction is algebraic; the sealed table only chooses *which*
    field and which affine constant. That division matters: the security
    properties come from the inverse map and hold for any irreducible
    polynomial, so the geometry selects a member of a family rather than
    supplying the strength itself.
    """
    digest = cube_digest()
    table = irreducible_polynomials()
    poly, gen = table[digest[0] % len(table)]

    # The affine constant is not simply the next digest byte. A fixed point,
    # S(x) = x, is a value the substitution leaves alone, and 38% of the 256
    # constants avoid them entirely — AES picked 0x63 for exactly this reason.
    # Taking the digest byte blindly landed on 0xE5, which has two. The cube
    # still chooses; it now chooses from the constants that are actually
    # usable, which is a search seeded by the seal rather than a lottery.
    affine_c = _first_fixed_point_free(digest[1], poly, gen)

    log, antilog = _log_tables(poly, gen)
    return poly, gen, affine_c, log, antilog


POLYNOMIAL, GENERATOR, AFFINE_C, LOG, ANTILOG = _field()


def inverse(value: int) -> int:
    """Multiplicative inverse in GF(2⁸), read out of the log tables.

    This is the semi-log step, and it is the whole reason the numbers below
    reach AES's. The first version of this module shuffled a permutation with
    SHA-256 instead, which produced a bijection indistinguishable from random:
    differential uniformity 10 against AES's 4, nonlinearity 92 against 112.
    Then the review said an algebraic construction was the only way to close
    that gap — while the algebraic construction was the instruction that had
    been skipped.

    x ↦ x⁻¹ has differential uniformity 4 and nonlinearity 112 over GF(2⁸)
    for every irreducible polynomial, so the strength is in the map and not in
    which field the cube happened to pick.
    """
    return 0 if value == 0 else ANTILOG[255 - LOG[value]]


def _affine(byte: int) -> int:
    """Rotate-and-sum, then add a constant.

    What this buys is not the differential or linear numbers — those are
    affine invariants and the pure inverse already reaches 4 and 112. It buys
    two other things AES ends its S-box for. The pure inverse is an
    *involution*, S(S(x)) = x for every byte, which is a structure an attacker
    can use; after the affine layer only two bytes survive that. And the
    constant is chosen so no byte maps to itself.
    """
    return _affine_with(byte, AFFINE_C)


def derive_sbox() -> Tuple[int, ...]:
    """The substitution: semi-log inverse, then the affine map."""
    return tuple(_affine(inverse(value)) for value in range(256))


SBOX: Tuple[int, ...] = derive_sbox()
INV_SBOX: Tuple[int, ...] = tuple(SBOX.index(value) for value in range(256))


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
    seed = cube_digest() + b"tawaf"
    return tuple(
        int.from_bytes(
            hashlib.sha256(seed + bytes([i])).digest()[:8], "big"
        ) & LANE_MASK
        for i in range(CIRCUITS)
    )


ROUND_CONSTANTS = _round_constants()


def _rotl(value: int, amount: int) -> int:
    amount %= LANE_BITS
    return ((value << amount) | (value >> (LANE_BITS - amount))) & LANE_MASK


#: Per-lane rotation offsets, triangular numbers modulo the lane width. Every
#: lane turns by a different amount, so a difference cannot stay aligned.
RHO: Tuple[int, ...] = tuple((i * (i + 1) // 2) % LANE_BITS for i in range(25))

#: Lane repositioning, Keccak's π. Diffusion needs lanes to change columns as
#: well as mix within them, or θ only ever sees the same groupings.
PI: Tuple[int, ...] = tuple(
    5 * (i % 5) + ((i // 5) + 3 * (i % 5)) % 5 for i in range(25)
)


def _substitute(lane: int) -> int:
    """The byte S-box applied across a lane, eight bytes at a time."""
    out = 0
    for i in range(LANE_BYTES):
        out |= SBOX[(lane >> (8 * i)) & 0xFF] << (8 * i)
    return out


def linear_layer(state: Sequence[int]) -> List[int]:
    """θ then ρ·π — the round with the substitution and constant removed.

    Exposed rather than inlined so that an audit measures *this* layer. The
    attack tool first carried its own copy, which meant a sabotage of the real
    one left every check green: it was attacking a different construction,
    which is exactly the failure the specification warns an attacker about.
    """
    s = [lane & LANE_MASK for lane in state]

    parity = [0] * COLS
    for col in range(COLS):
        for row in range(ROWS):
            parity[col] ^= s[row * COLS + col]
    fold = [
        parity[(col - 1) % COLS] ^ _rotl(parity[(col + 1) % COLS], 1)
        for col in range(COLS)
    ]
    for row in range(ROWS):
        for col in range(COLS):
            s[row * COLS + col] ^= fold[col]

    rotated = [_rotl(s[i], RHO[i]) for i in range(STATE_LANES)]
    moved = [0] * STATE_LANES
    for i in range(STATE_LANES):
        moved[PI[i]] = rotated[i]
    return moved


def permute(state: List[int]) -> List[int]:
    """Twenty-eight rounds: θ, ρ·π, substitute, add a constant.

    Four tawaf of seven circuits each, which is also the alphabet. The count
    is measured rather than chosen — see :data:`CIRCUITS`.

    **The mixing layer was rewritten after it failed its own audit.** The first
    version computed each column's parity and added it to all five lanes of
    that column. That is not invertible, and a sponge requires a permutation:
    the new column parity is then always zero, because five copies of the
    parity XOR back to one, so the whole state collapses into a subspace.
    Measured over GF(2), the linear layer had rank 1276 of 1600 — 320
    dimensions lost, exactly five columns times sixty-four bit positions, and
    five more from the row step for the same reason.

    Keccak's θ avoids it by adding a *neighbour's* parity rather than the
    lane's own: D[x] = C[x−1] ⊕ rotl(C[x+1], 1). That is invertible, and the
    rewritten layer measures rank 1600.
    """
    if len(state) != STATE_LANES:
        raise ValueError(f"state must be {STATE_LANES} lanes, got {len(state)}")

    s = [lane & LANE_MASK for lane in state]
    for circuit in range(CIRCUITS):
        s = linear_layer(s)
        s = [_substitute(lane) for lane in s]
        s[0] ^= ROUND_CONSTANTS[circuit]
    return s


# ── Sponge ───────────────────────────────────────────────────────

#: Bits absorbed before the circuit closes and the permutation runs.
RATE_BITS = RATE_LANES * LANE_BITS


def absorb_bit(state: List[int], bit: int, step: int) -> Tuple[List[int], int]:
    """Absorb one bit, spreading consecutive bits across different nodes.

    The spectrum schedule: bit *n* lands on node ``TAWAF_PATH[n % 16]`` at
    position ``n // 16``, so one byte reaches eight nodes instead of filling
    one lane. Lane-major would put all eight in a single lane.

    **Measured, and the result is negative.** Digest avalanche is ~0.5 under
    both schedules at every message length from 1 to 256 bytes — the
    permutation is strong enough that the input schedule does not matter for
    diffusion. Reporting that plainly is worth more than a justification
    invented after the fact.

    What the schedule is actually for is the input path. Bit-serial absorption
    needs one wire and one bit of state, not a 64-bit bus, which is the
    cheapest thing an FPGA can be asked to accept — 27 Mbit/s at 27 MHz, one
    bit per clock, with no shift register per lane.
    """
    s = list(state)
    node = TAWAF_PATH[step % RATE_LANES]
    position = step // RATE_LANES
    s[node] ^= (bit & 1) << position
    step += 1
    if step == RATE_BITS:
        s = permute(s)
        step = 0
    return s, step


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
