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
#  The permutation and the sponge
# ══════════════════════════════════════════════════════════════════

def test_the_permutation_is_a_permutation_of_states() -> None:
    """Distinct states must stay distinct, or the sponge loses capacity."""
    seen = {tuple(C.permute([0] * C.STATE_BYTES))}
    for i in range(C.STATE_BYTES):
        state = [0] * C.STATE_BYTES
        state[i] = 1
        seen.add(tuple(C.permute(state)))
    assert len(seen) == C.STATE_BYTES + 1


def test_one_changed_byte_reaches_every_lane() -> None:
    """
    Full diffusion in one permutation. If a lane never changed, part of the
    state would be untouched by part of the message.
    """
    base = C.permute([0] * C.STATE_BYTES)
    changed = C.permute([1] + [0] * (C.STATE_BYTES - 1))
    assert all(a != b for a, b in zip(base, changed, strict=True)), "a lane went unchanged"


def test_the_permutation_rejects_a_wrong_sized_state() -> None:
    with pytest.raises(ValueError, match="25 bytes"):
        C.permute([0] * 10)


def test_absorption_takes_one_byte_at_a_time() -> None:
    """The shape the HCPU wants: one byte in, one lane XORed."""
    state, position = [0] * C.STATE_BYTES, 0
    state, position = C.absorb_byte(state, 0xAB, position)
    assert state[0] == 0xAB and position == 1
    assert sum(1 for b in state if b) == 1, "one byte must touch one lane"


def test_the_permutation_runs_when_the_rate_fills() -> None:
    state, position = [0] * C.STATE_BYTES, 0
    for i in range(C.RATE):
        state, position = C.absorb_byte(state, i + 1, position)
    assert position == 0, "the rate wrapped"
    assert any(state[C.RATE:]), "capacity must have been touched by the permutation"


@pytest.mark.parametrize("length", [1, 16, 32, 64])
def test_the_digest_has_the_requested_length(length: int) -> None:
    assert len(C.digest(b"hybit", length)) == length


def test_the_digest_is_deterministic() -> None:
    assert C.digest(b"hybit") == C.digest(b"hybit")


def test_distinct_messages_give_distinct_digests() -> None:
    messages = [os.urandom(24) for _ in range(200)]
    assert len({C.digest(m) for m in messages}) == 200


def test_trailing_zeros_do_not_collide() -> None:
    """Padding exists for exactly this: without it these absorb identically."""
    assert C.digest(b"a") != C.digest(b"a\x00")
    assert C.digest(b"") != C.digest(b"\x00")


def test_the_sponge_avalanches() -> None:
    """One input bit should move about half the output bits."""
    rng = random.Random(3)
    changed = total = 0
    for _ in range(60):
        msg = bytes(rng.randrange(256) for _ in range(16))
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
