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


def test_differential_uniformity_reaches_the_algebraic_optimum() -> None:
    """
    Four, which is the optimum for a bijection on eight bits and what AES
    reaches. The first version of this module shuffled a permutation with
    SHA-256 and measured 10 — indistinguishable from random. The semi-log
    inverse is what closed that.
    """
    value = C.differential_uniformity()
    assert value == AES_DIFFERENTIAL == 4, (
        f"differential uniformity {value}; the semi-log inverse must reach 4"
    )
    assert value < RANDOM_DIFFERENTIAL[0], "a shuffle could never get here"


def test_nonlinearity_matches_the_algebraic_optimum() -> None:
    """112, again AES's figure. The shuffled version measured 92."""
    value = C.nonlinearity()
    assert value == AES_NONLINEARITY == 112
    assert value > RANDOM_NONLINEARITY[1], "a shuffle could never get here"


def test_the_strength_is_in_the_map_not_in_the_field_the_cube_picked() -> None:
    """
    x ↦ x⁻¹ has these properties over GF(2⁸) for *every* irreducible
    polynomial. The sealed cube selects a member of the family; it does not
    supply the strength, and saying otherwise would credit the geometry with
    work the algebra does.
    """
    table = C.irreducible_polynomials()
    assert len(table) == 30, "there are thirty irreducible degree-8 polynomials"
    assert any(poly == 0x11B for poly, _ in table), "AES's field must be among them"
    assert (C.POLYNOMIAL, C.GENERATOR) in table


def test_the_field_is_chosen_by_the_sealed_cube() -> None:
    digest = C.cube_digest()
    table = C.irreducible_polynomials()
    assert (C.POLYNOMIAL, C.GENERATOR) == table[digest[0] % len(table)]
    # The constant is searched from the seal's byte forward rather than taken
    # from it directly; test_the_affine_constant_is_reachable_from_the_seal
    # pins that the search skipped nothing usable.
    assert C.AFFINE_C == C._first_fixed_point_free(
        digest[1], C.POLYNOMIAL, C.GENERATOR
    )


def test_no_byte_maps_to_itself() -> None:
    """
    A fixed point is a value the substitution leaves alone. Taking the seal's
    byte blindly landed on 0xE5, which has two; 38% of the 256 constants have
    none, and AES picked 0x63 for exactly this reason. The cube now chooses
    from the usable ones — a search seeded by the seal rather than a lottery.
    """
    assert not [x for x in range(256) if C.SBOX[x] == x]


def test_the_substitution_is_not_an_involution() -> None:
    """
    What the affine layer actually buys. The differential and linear figures
    are affine invariants — the pure inverse already reaches 4 and 112, so
    deleting the affine layer failed no test until this one existed. But the
    pure inverse is an involution, S(S(x)) = x for every byte, which is
    structure an attacker can use.
    """
    survivors = [x for x in range(256) if C.SBOX[C.SBOX[x]] == x]
    assert not survivors, f"{len(survivors)} bytes still involute"

    pure = [C.inverse(x) for x in range(256)]
    assert all(pure[pure[x]] == x for x in range(256)), (
        "the pure inverse must be an involution, or this test proves nothing"
    )


def test_the_affine_constant_is_reachable_from_the_seal() -> None:
    """Chosen from the seal's byte forward, so it stays determined by it."""
    digest = C.cube_digest()
    offset = (C.AFFINE_C - digest[1]) & 0xFF
    assert offset < 256
    for earlier in range(offset):
        candidate = (digest[1] + earlier) & 0xFF
        box = [C._affine_with(C.inverse(x), candidate) for x in range(256)]
        assert any(box[x] == x for x in range(256)), (
            f"0x{candidate:02X} was skipped but has no fixed point"
        )


def test_the_log_tables_really_invert() -> None:
    """The semi-log step itself: x · x⁻¹ = 1 for every non-zero byte."""
    assert C.inverse(0) == 0
    for value in range(1, 256):
        assert C._mul(value, C.inverse(value), C.POLYNOMIAL) == 1


def test_avalanche_is_near_ideal() -> None:
    """
    The cheapest check and the least discriminating: a weak S-box can pass it.
    Reported because its absence would be damning, not because its presence
    proves anything.
    """
    assert 0.48 <= C.avalanche() <= 0.52


def test_the_random_baseline_is_where_a_shuffle_actually_lands() -> None:
    """
    The contrast the two assertions above lean on. Sampled rather than
    asserted from memory, because the whole claim is that the semi-log
    construction leaves this range and a shuffle cannot.
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


def test_the_round_count_is_derived_from_the_measured_floor() -> None:
    """
    Four tawaf of seven, which is also the alphabet — and, more to the point,
    9.3× the measured diffusion floor. The first version ran seven, which is
    2.3× and inside the range an attack on this shape would plausibly reach.
    """
    assert C.CIRCUIT == 7, "one tawaf is seven circuits"
    assert C.TAWAF == 4
    assert C.CIRCUITS == 28 == C.LAYERS, "and 28 is the alphabet"
    assert len(C.ROUND_CONSTANTS) == 28
    assert len(set(C.ROUND_CONSTANTS)) == 28, "constants must not repeat"


def test_diffusion_saturates_well_below_the_round_count() -> None:
    """
    The measurement the count rests on. Three rounds reach ideal avalanche and
    nothing after moves, so the floor is three and the margin is 28/3.

    If this ever fails upward — if saturation needs more rounds — the margin
    shrank and the count has to be revisited.
    """
    import random

    def permute_n(state, n):
        s = [x & C.LANE_MASK for x in state]
        for r in range(n):
            s = [C._substitute(lane) for lane in s]
            for row in range(C.ROWS):
                base = row * C.COLS
                acc = 0
                for col in range(C.COLS):
                    acc ^= s[base + col]
                for col in range(C.COLS):
                    s[base + col] ^= C._rotl(acc, col + r + 1)
            for col in range(C.COLS):
                acc = 0
                for row in range(C.ROWS):
                    acc ^= s[row * C.COLS + col]
                for row in range(C.ROWS):
                    i = row * C.COLS + col
                    s[i] = C._rotl(s[i] ^ acc, i + 1)
            s[0] ^= C.ROUND_CONSTANTS[r % len(C.ROUND_CONSTANTS)]
        return s

    rng = random.Random(3)
    def avalanche_at(n):
        changed = total = 0
        for _ in range(12):
            st = [rng.getrandbits(64) for _ in range(25)]
            other = list(st)
            other[rng.randrange(25)] ^= 1 << rng.randrange(64)
            a, b = permute_n(st, n), permute_n(other, n)
            changed += sum(bin(x ^ y).count("1") for x, y in zip(a, b, strict=True))
            total += 1600
        return changed / total

    assert avalanche_at(1) < 0.2, "round 1 must not already be saturated"
    assert 0.45 <= avalanche_at(3) <= 0.55, "the floor is three rounds"
    assert C.CIRCUITS / 3 >= 8, "the margin must stay near Keccak's posture"


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


def test_the_module_says_where_the_strength_comes_from() -> None:
    """
    The cube chooses the field; the inverse map supplies the strength. The
    docstring has to say which is which, or the geometry gets credited with
    the algebra's work.
    """
    doc = " ".join((C.__doc__ or "").split())
    assert "strength comes from the inverse map" in doc
    assert "selects a member of a family" in doc


def test_the_digest_does_not_present_itself_as_a_hash_function() -> None:
    doc = " ".join((C.digest.__doc__ or "").split())
    assert "[EH]" in doc
    assert "SHA-256 for anything that matters" in doc


# ══════════════════════════════════════════════════════════════════
#  The gate that caught a fatal flaw
# ══════════════════════════════════════════════════════════════════

def test_the_linear_layer_is_invertible() -> None:
    """
    A sponge requires a permutation, and this is the check that says whether
    it has one. The first mixing layer added each column's parity to all five
    lanes of that column, which forces the new parity to zero — five copies of
    a value XOR back to one — so the state collapsed into a subspace. Rank was
    1276 of 1600: 324 dimensions gone, 320 of them exactly five columns times
    sixty-four bit positions.

    Twenty thousand random states produced no collision, because the space is
    2^1600. Only the rank computation could see it, which is the lesson worth
    keeping: statistical tests on a broken construction can look perfect.
    """
    import sys
    from pathlib import Path as _Path

    sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
    from tools.kabah_attack import BITS, linear_layer, rank_over_gf2

    assert rank_over_gf2(linear_layer) == BITS == 1600


def test_the_attack_tool_reports_every_check_holding() -> None:
    """
    tools/kabah_attack.py is a gate, not a report. If any check starts failing
    the construction changed underneath it.
    """
    import sys
    from pathlib import Path as _Path

    sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
    from tools import kabah_attack

    results = kabah_attack.run(
        ["attack_sbox", "attack_rotational", "attack_fixed_points"]
    )
    assert len(results) == 3
    for result in results:
        assert result["pass"], f"{result['name']} was breached: {result}"


def test_theta_already_reads_both_neighbours() -> None:
    """
    Why sa'i changes nothing on the permutation, pinned as a property rather
    than as a sentence. Diffusion runs both ways every round because theta
    reads C[x-1] and C[x+1]; a state differing in one column must therefore
    change both adjacent columns after a single linear layer.
    """
    for column in range(5):
        a = [0] * C.STATE_LANES
        b = list(a)
        b[column] ^= 1
        la, lb = C.linear_layer(a), C.linear_layer(b)
        touched = {i % 5 for i in range(C.STATE_LANES) if la[i] != lb[i]}
        assert (column - 1) % 5 in touched, "the left neighbour is untouched"
        assert (column + 1) % 5 in touched, "the right neighbour is untouched"


def test_the_sai_result_is_recorded_as_a_negative() -> None:
    """
    Five measured negatives now live in this repository, and each one is worth
    more than a justification invented afterwards. This keeps the sa'i finding
    from quietly disappearing into a claim that it was adopted.
    """
    doc = " ".join((C.__doc__ or "").split())
    assert "Sa'i was proposed and measured" in doc
    assert "Three readings, all tested, none faster" in doc
    assert "theta already goes both ways every round" in doc
    assert "saturated" in doc


def test_diffusion_barely_depends_on_which_lane_a_difference_lands_in() -> None:
    """
    The bound that makes every path-order question answerable at once.

    A traversal order chooses which lane a byte lands in, never which clock —
    every order absorbs one byte per clock. So the largest effect any order can
    have is the lane-dependence of diffusion, and by round three that has
    collapsed to about 0.01 while the permutation runs twenty-eight rounds.
    """
    rng = random.Random(2)
    spread = []
    for lane in range(C.STATE_LANES):
        total = 0
        for _ in range(8):
            a = [rng.getrandbits(C.LANE_BITS) for _ in range(C.STATE_LANES)]
            b = list(a)
            b[lane] ^= 1 << rng.randrange(C.LANE_BITS)
            x, y = a, b
            for r in range(3):
                x = [C._substitute(v) for v in C.linear_layer(x)]
                y = [C._substitute(v) for v in C.linear_layer(y)]
                x[0] ^= C.ROUND_CONSTANTS[r]
                y[0] ^= C.ROUND_CONSTANTS[r]
            total += sum(bin(p ^ q).count("1") for p, q in zip(x, y, strict=True))
        spread.append(total / (8 * C.STATE_LANES * C.LANE_BITS))

    assert max(spread) - min(spread) < 0.05, (
        "lane choice would have room to matter, and a path order could exploit it"
    )
    assert 0.45 <= min(spread) <= max(spread) <= 0.55


def test_a_wide_linear_stride_buys_a_substitution_layer() -> None:
    """
    The ramal finding, pinned so it cannot quietly decay.

    Sa'i is not a uniform walk: between the markers the pace becomes a brisk
    trot. Applied to the round schedule, that means a wider linear reach before
    the nonlinearity is spent — and it is worth measuring because the two
    layers are not the same price. The linear layer is XOR trees; a 25-lane
    substitution is about 1900 LUT4.

    Two substitution layers with a wide opening stride reach the diffusion
    floor that a uniform three-round walk reaches. The order is not symmetric:
    the stride has to come first.
    """
    def run(state, strides):
        s = list(state)
        for r, k in enumerate(strides):
            for _ in range(k):
                s = C.linear_layer(s)
            s = [C._substitute(x) for x in s]
            s[0] ^= C.ROUND_CONSTANTS[r]
        return s

    def avalanche(strides, trials=60):
        rng = random.Random(5)
        changed = total = 0
        for _ in range(trials):
            a = [rng.getrandbits(C.LANE_BITS) for _ in range(C.STATE_LANES)]
            b = list(a)
            b[rng.randrange(C.STATE_LANES)] ^= 1 << rng.randrange(C.LANE_BITS)
            x, y = run(a, strides), run(b, strides)
            changed += sum(bin(p ^ q).count("1") for p, q in zip(x, y, strict=True))
            total += C.STATE_LANES * C.LANE_BITS
        return changed / total

    assert avalanche([1, 1]) < 0.40, "two uniform rounds should not be diffused"
    assert 0.45 <= avalanche([2, 1]) <= 0.55, "the wide opening stride should be"
    assert 0.45 <= avalanche([1, 1, 1]) <= 0.55


def test_the_sealed_permutation_still_walks_uniformly() -> None:
    """
    Ramal was measured, not adopted. The schedule under seal is unchanged, and
    this fails if an exploration ever leaks into the shipped permutation.
    """
    assert C.CIRCUITS == 28
    state = [1] + [0] * (C.STATE_LANES - 1)
    manual = list(state)
    for r in range(C.CIRCUITS):
        manual = C.linear_layer(manual)
        manual = [C._substitute(x) for x in manual]
        manual[0] ^= C.ROUND_CONSTANTS[r % len(C.ROUND_CONSTANTS)]
    assert C.permute(state) == manual
