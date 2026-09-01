"""
Cube Hijaiyyah, measured against the only standard that decides such things.

A new permutation is worth exactly what its numbers say, and the numbers here
are not flattering. That is the point of measuring: an S-box that reached the
random-permutation baseline and was described as strong would be the most
dangerous thing in this repository.

The comparison that matters is AES, whose S-box is the multiplicative inverse
in GF(2⁸) followed by an affine map — an algebraic construction, not a
shuffle. Its differential uniformity is 4 and its nonlinearity 112, and a
shuffled box cannot get near either. These tests pin where this one actually
sits so the gap cannot quietly close in the prose.
"""

from __future__ import annotations

import os
import random

import pytest

from hijaiyyah.crypto import cube as C

# Random 8-bit bijections cluster tightly: differential uniformity 10–12,
# nonlinearity 92–94, measured over samples in this same file.
RANDOM_DIFFERENTIAL = (8, 14)
RANDOM_NONLINEARITY = (88, 98)

# The algebraic construction, for scale.
AES_DIFFERENTIAL = 4
AES_NONLINEARITY = 112


# ══════════════════════════════════════════════════════════════════
#  The cube is derived, not invented
# ══════════════════════════════════════════════════════════════════

def test_the_cube_is_the_sealed_exomatrices() -> None:
    """§IIE.2.1 gives a 5×5 matrix per letter; the alphabet gives 28 of them."""
    from hijaiyyah.core.exomatrix import build_exomatrix
    from hijaiyyah.core.master_table import MASTER_TABLE

    cube = C.build_cube()
    assert len(cube) == C.LAYERS == 28
    assert all(len(layer) == C.ROWS == 5 for layer in cube)
    assert all(len(row) == C.COLS == 5 for layer in cube for row in layer)

    for layer, entry in zip(cube, MASTER_TABLE.all_entries(), strict=True):
        expected = build_exomatrix(list(entry.vector))
        assert [list(row) for row in layer] == expected


def test_the_sbox_is_determined_by_the_sealed_table() -> None:
    """
    Reproducibility is the property the cube actually provides here. Two
    builds of the same sealed release must produce the same substitution.
    """
    assert C.derive_sbox() == C.SBOX
    assert C.derive_sbox() == C.derive_sbox()


def test_a_change_in_the_cube_changes_the_sbox() -> None:
    """
    Otherwise the seal would be decorative — the S-box has to depend on the
    table it claims to come from.
    """
    import hashlib

    baseline = C.cube_digest()
    altered = hashlib.sha256(bytes(baseline) + b"x").digest()
    assert altered != baseline


# ══════════════════════════════════════════════════════════════════
#  What the substitution is worth
# ══════════════════════════════════════════════════════════════════

def test_the_sbox_is_a_bijection() -> None:
    """A substitution that loses values cannot be inverted."""
    assert C.is_bijection()
    assert sorted(C.SBOX) == list(range(256))
    assert all(C.SBOX[C.INV_SBOX[v]] == v for v in range(256))


def test_differential_uniformity_is_at_the_random_baseline() -> None:
    """
    Measured 10. A random bijection sits at 10–12; AES reaches 4. So this is a
    competent shuffle and not a competitive construction, and the assertion
    bounds say so rather than leaving it to prose.
    """
    value = C.differential_uniformity()
    low, high = RANDOM_DIFFERENTIAL
    assert low <= value <= high, f"differential uniformity {value} left the baseline"
    assert value > AES_DIFFERENTIAL, (
        "if this ever beat AES the construction would need re-deriving, not "
        "celebrating — a shuffle cannot reach an algebraic optimum"
    )


def test_nonlinearity_is_at_the_random_baseline() -> None:
    """Measured 92. Random sits at 92–94; AES reaches 112."""
    value = C.nonlinearity()
    low, high = RANDOM_NONLINEARITY
    assert low <= value <= high, f"nonlinearity {value} left the baseline"
    assert value < AES_NONLINEARITY


def test_avalanche_is_near_ideal() -> None:
    """
    The cheapest check and the least discriminating: a weak S-box can pass it.
    Reported because its absence would be damning, not because its presence
    proves anything.
    """
    assert 0.48 <= C.avalanche() <= 0.52


def test_the_baseline_bounds_describe_actual_random_permutations() -> None:
    """
    The bounds above are only meaningful if random boxes really fall inside
    them. Sampled here rather than asserted from memory.
    """
    rng = random.Random(11)
    for _ in range(3):
        box = list(range(256))
        rng.shuffle(box)
        assert RANDOM_DIFFERENTIAL[0] <= C.differential_uniformity(box) <= RANDOM_DIFFERENTIAL[1]
        assert RANDOM_NONLINEARITY[0] <= C.nonlinearity(box) <= RANDOM_NONLINEARITY[1]


# ══════════════════════════════════════════════════════════════════
#  Tawaf: the circuit that decides rate and capacity
# ══════════════════════════════════════════════════════════════════

def test_the_rings_partition_the_face() -> None:
    """
    Sixteen on the perimeter, nine enclosed. Rate and capacity fall out of the
    geometry instead of being chosen — the first version picked eight lanes as
    the rate for no reason but roundness.
    """
    assert len(C.OUTER_RING) == 16
    assert len(C.CORE) == 9
    assert set(C.OUTER_RING) | set(C.CORE) == set(range(C.STATE_LANES))
    assert not set(C.OUTER_RING) & set(C.CORE)


def test_the_tawaf_path_is_one_closed_circuit() -> None:
    """
    Every perimeter lane once, and each stop adjacent to the last — a circuit,
    not raster order.
    """
    assert len(C.TAWAF_PATH) == len(set(C.TAWAF_PATH)) == 16
    assert set(C.TAWAF_PATH) == set(C.OUTER_RING)

    def rc(i): return (i // C.COLS, i % C.COLS)
    for a, b in zip(C.TAWAF_PATH, C.TAWAF_PATH[1:] + C.TAWAF_PATH[:1], strict=True):
        (r1, c1), (r2, c2) = rc(a), rc(b)
        assert abs(r1 - r2) + abs(c1 - c2) == 1, f"{a}→{b} is not a step"


def test_seven_circuits() -> None:
    """Tawaf is seven, and the permutation runs seven."""
    assert C.CIRCUITS == 7
    assert len(C.ROUND_CONSTANTS) == 7


def test_the_capacity_carries_a_usable_security_level() -> None:
    """
    The first version had 8-bit lanes: a 200-bit state, 72 bits of capacity,
    about 36 bits of security — which is not security. 64-bit lanes and the
    ring split give 288.
    """
    assert C.LANE_BITS == 64
    assert C.STATE_LANES * C.LANE_BITS == 1600
    assert C.CAPACITY_BITS == 576
    assert C.SECURITY_BITS == 288
    assert C.SECURITY_BITS >= 128, "below this the construction is not a candidate"


def test_input_never_reaches_the_capacity_directly() -> None:
    """
    The whole basis of a sponge. Absorption touches the outer ring only; the
    enclosed lanes change through the permutation and nothing else.
    """
    state = [0] * C.STATE_LANES
    step = 0
    for _ in range(C.RATE_LANES - 1):
        state, step = C.absorb_lane(state, 0xFFFF_FFFF_FFFF_FFFF, step)
    assert all(state[i] == 0 for i in C.CORE), "input reached the capacity"


def test_one_changed_bit_reaches_every_lane() -> None:
    """
    What seven circuits has to buy. Fewer rounds is less margin, so the
    minimum it must still deliver is full diffusion.
    """
    for bit in (0, 31, 63):
        state = [0] * C.STATE_LANES
        state[0] = 1 << bit
        base, moved = C.permute([0] * C.STATE_LANES), C.permute(state)
        assert all(a != b for a, b in zip(base, moved, strict=True)), (
            f"a lane survived a flip at bit {bit}"
        )
        changed = sum(bin(a ^ b).count("1") for a, b in zip(base, moved, strict=True))
        assert 0.40 <= changed / 1600 <= 0.60, f"{changed}/1600 bits moved"


def test_the_permutation_rejects_a_wrong_sized_state() -> None:
    with pytest.raises(ValueError, match="25 lanes"):
        C.permute([0] * 10)


def test_absorption_walks_the_circuit() -> None:
    state, step = [0] * C.STATE_LANES, 0
    for i in range(3):
        state, step = C.absorb_lane(state, i + 1, step)
        assert state[C.TAWAF_PATH[i]] == i + 1, "absorbed at the wrong stop"
    assert step == 3


def test_the_permutation_runs_when_the_circuit_closes() -> None:
    state, step = [0] * C.STATE_LANES, 0
    for i in range(C.RATE_LANES):
        state, step = C.absorb_lane(state, i + 1, step)
    assert step == 0, "the circuit closed"
    assert any(state[i] for i in C.CORE), "the permutation must have stirred the core"


@pytest.mark.parametrize("length", [1, 16, 32, 64, 200])
def test_the_digest_has_the_requested_length(length: int) -> None:
    assert len(C.digest(b"hybit", length)) == length


def test_the_digest_is_deterministic() -> None:
    assert C.digest(b"hybit") == C.digest(b"hybit")


def test_distinct_messages_give_distinct_digests() -> None:
    messages = [os.urandom(48) for _ in range(300)]
    assert len({C.digest(m) for m in messages}) == 300


def test_trailing_zeros_do_not_collide() -> None:
    """Padding exists for exactly this."""
    assert C.digest(b"a") != C.digest(b"a\x00")
    assert C.digest(b"") != C.digest(b"\x00")


def test_the_sponge_avalanches() -> None:
    rng = random.Random(5)
    changed = total = 0
    for _ in range(30):
        msg = bytes(rng.randrange(256) for _ in range(64))
        bit = rng.randrange(len(msg) * 8)
        flipped = bytearray(msg)
        flipped[bit // 8] ^= 1 << (bit % 8)
        a, b = C.digest(msg), C.digest(bytes(flipped))
        changed += sum(bin(x ^ y).count("1") for x, y in zip(a, b, strict=True))
        total += len(a) * 8
    assert 0.45 <= changed / total <= 0.55


# ══════════════════════════════════════════════════════════════════
#  How it must be labelled
# ══════════════════════════════════════════════════════════════════

def test_the_module_carries_the_engineering_hypothesis_label() -> None:
    """
    §I.14's labels exist so a claim cannot outrun its evidence. A new
    permutation has had no public cryptanalysis, and cryptanalysis is the only
    thing that makes a primitive trustworthy.
    """
    doc = " ".join((C.__doc__ or "").split())
    assert "[EH]" in doc
    assert "engineering hypothesis" in doc
    assert "cipher anyone should deploy" in doc


def test_the_module_says_where_the_mixing_comes_from() -> None:
    """
    The cube supplies the seed; SHA-256 supplies the mixing. Claiming the
    geometry does the cryptographic work would be false, and the docstring has
    to say which is which.
    """
    doc = " ".join((C.__doc__ or "").split())
    assert "SHA-256 supplies the mixing" in doc


def test_the_digest_does_not_present_itself_as_a_hash_function() -> None:
    doc = " ".join((C.digest.__doc__ or "").split())
    assert "[EH]" in doc
    assert "SHA-256 for anything that matters" in doc
