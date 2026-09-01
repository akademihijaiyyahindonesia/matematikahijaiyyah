#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Attack the Ka'bah permutation.

Written after publishing an invitation to attack it, because inviting attacks
without mounting any is half the work. It found something on the first run.

**What it found.** The mixing layer was not invertible. Each column's parity
was added to all five lanes of that column, which forces the new parity to
zero — five copies of a value XOR back to one — so the whole state collapsed
into a subspace. Measured over GF(2), the linear layer had rank 1276 of 1600:
324 dimensions gone, 320 of them exactly five columns times sixty-four bit
positions. A sponge requires a permutation, and that was not one. The layer
now follows Keccak's θ, adding a *neighbour's* parity, and measures 1600.

Random search would never have found it. Twenty thousand random states gave no
collision, because the space is 2^1600 — the flaw was only visible by building
the layer's matrix and computing its rank. That is the lesson worth keeping:
statistical tests on a broken construction can look perfect.

Each check below is a gate, not a report. They run in the test suite too, so a
regression cannot pass unnoticed.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from typing import Callable, Dict, List, Sequence

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from hijaiyyah.crypto import cube as C  # noqa: E402

BITS = C.STATE_LANES * C.LANE_BITS


# ── Linear algebra over GF(2) ────────────────────────────────────

def _to_bits(state: Sequence[int]) -> List[int]:
    return [
        (state[i] >> b) & 1
        for i in range(C.STATE_LANES)
        for b in range(C.LANE_BITS)
    ]


def _unit(index: int) -> List[int]:
    state = [0] * C.STATE_LANES
    state[index // C.LANE_BITS] |= 1 << (index % C.LANE_BITS)
    return state


def rank_over_gf2(transform: Callable[[List[int]], List[int]]) -> int:
    """Rank of a linear transform on the state, by Gaussian elimination.

    The check that caught the flaw. A linear layer of less than full rank is
    not invertible, and no amount of avalanche testing will say so.
    """
    columns = [_to_bits(transform(_unit(k))) for k in range(BITS)]
    rows = [[columns[k][i] for k in range(BITS)] for i in range(BITS)]

    rank = 0
    for col in range(BITS):
        pivot = next((r for r in range(rank, BITS) if rows[r][col]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for r in range(BITS):
            if r != rank and rows[r][col]:
                rows[r] = [a ^ b for a, b in zip(rows[r], rows[rank], strict=True)]
        rank += 1
    return rank


def linear_layer(state: List[int]) -> List[int]:
    """The permutation's linear layer — imported, never reimplemented.

    This function first carried its own copy of θ and ρ·π. Sabotaging the real
    layer in cube.py then left every check green, because the tool was
    measuring its own copy: it attacked a different construction, which is the
    exact failure the specification warns an attacker about. Now it calls
    cube.linear_layer, so a change there is a change here.
    """
    return C.linear_layer(state)


def permute_rounds(state: Sequence[int], rounds: int) -> List[int]:
    """The permutation stopped after a given number of rounds.

    Composed from cube's own pieces for the same reason: a reduced-round
    attack has to run the real round function, or it measures nothing.
    """
    s = [x & C.LANE_MASK for x in state]
    for r in range(rounds):
        s = C.linear_layer(s)
        s = [C._substitute(lane) for lane in s]
        s[0] ^= C.ROUND_CONSTANTS[r % len(C.ROUND_CONSTANTS)]
    return s


# ── Attacks ──────────────────────────────────────────────────────

def attack_invertibility() -> Dict[str, object]:
    """Is the linear layer a bijection? The one that found the flaw."""
    rank = rank_over_gf2(linear_layer)
    return {
        "name": "invertibility",
        "rank": rank,
        "of": BITS,
        "lost": BITS - rank,
        "pass": rank == BITS,
        "note": "a sponge requires a permutation; rank below full is not one",
    }


def attack_diffusion_floor(trials: int = 15) -> Dict[str, object]:
    """How many rounds until one flipped bit moves half the state?

    Everything above this is margin, and the round count is set from it.
    """
    rng = random.Random(3)
    floor = None
    profile = []
    for rounds in range(1, 9):
        changed = total = 0
        for _ in range(trials):
            state = [rng.getrandbits(C.LANE_BITS) for _ in range(C.STATE_LANES)]
            other = list(state)
            other[rng.randrange(C.STATE_LANES)] ^= 1 << rng.randrange(C.LANE_BITS)
            a, b = permute_rounds(state, rounds), permute_rounds(other, rounds)
            changed += sum(
                bin(x ^ y).count("1") for x, y in zip(a, b, strict=True)
            )
            total += BITS
        avalanche = changed / total
        profile.append((rounds, round(avalanche, 4)))
        if floor is None and 0.45 <= avalanche <= 0.55:
            floor = rounds

    margin = C.CIRCUITS / floor if floor else 0
    return {
        "name": "diffusion floor",
        "floor": floor,
        "rounds": C.CIRCUITS,
        "margin": round(margin, 1),
        "profile": profile,
        "pass": floor is not None and margin >= 8,
        "note": "Keccak holds 8x; below that the count needs revisiting",
    }


def attack_rotational() -> Dict[str, object]:
    """Does rotating every lane rotate the output?

    The mixing layer is built from rotations, so a rotational relation would
    survive it. The S-box is what has to break the property.
    """
    rng = random.Random(11)
    survived = 0
    for _ in range(200):
        state = [rng.getrandbits(C.LANE_BITS) for _ in range(C.STATE_LANES)]
        for shift in (1, 8, 32):
            turned = [C._rotl(x, shift) for x in state]
            a = permute_rounds(state, C.CIRCUITS)
            b = permute_rounds(turned, C.CIRCUITS)
            if [C._rotl(x, shift) for x in a] == b:
                survived += 1
    return {
        "name": "rotational",
        "survivors": survived,
        "pass": survived == 0,
        "note": "a surviving relation would be an immediate distinguisher",
    }


def attack_fixed_points(trials: int = 400) -> Dict[str, object]:
    """States the permutation leaves alone, and short cycles."""
    rng = random.Random(7)
    fixed = short_cycle = 0
    for _ in range(trials):
        state = [rng.getrandbits(C.LANE_BITS) for _ in range(C.STATE_LANES)]
        once = permute_rounds(state, C.CIRCUITS)
        if once == state:
            fixed += 1
        elif permute_rounds(once, C.CIRCUITS) == state:
            short_cycle += 1
    if permute_rounds([0] * C.STATE_LANES, C.CIRCUITS) == [0] * C.STATE_LANES:
        fixed += 1
    return {
        "name": "fixed points",
        "fixed": fixed,
        "two_cycles": short_cycle,
        "pass": fixed == 0 and short_cycle == 0,
        "note": "the all-zero state is checked explicitly, not sampled",
    }


def attack_sbox() -> Dict[str, object]:
    """The substitution's own numbers, against the algebraic optimum."""
    du = C.differential_uniformity()
    nl = C.nonlinearity()
    fixed = [x for x in range(256) if C.SBOX[x] == x]
    involutive = [x for x in range(256) if C.SBOX[C.SBOX[x]] == x]
    return {
        "name": "s-box",
        "differential_uniformity": du,
        "nonlinearity": nl,
        "fixed_points": len(fixed),
        "involutive": len(involutive),
        "pass": du == 4 and nl == 112 and not fixed and not involutive,
        "note": "4 and 112 are the optimum for a bijection on eight bits",
    }


def attack_output_bias(samples: int = 400) -> Dict[str, object]:
    """Is any output bit biased away from balance?"""
    counts = [0] * 256
    for _ in range(samples):
        digest = C.digest(os.urandom(32), 32)
        for index, byte in enumerate(digest):
            for bit in range(8):
                counts[index * 8 + bit] += (byte >> bit) & 1
    worst = max(abs(count / samples - 0.5) for count in counts)
    return {
        "name": "output bias",
        "worst_bias": round(worst, 4),
        "samples": samples,
        "pass": worst < 0.12,
        "note": "sampling noise alone is about 0.025 at this sample count",
    }


ATTACKS = (
    attack_invertibility,
    attack_sbox,
    attack_diffusion_floor,
    attack_rotational,
    attack_fixed_points,
    attack_output_bias,
)


def run(names: Sequence[str] = ()) -> List[Dict[str, object]]:
    chosen = [a for a in ATTACKS if not names or a.__name__ in names]
    return [attack() for attack in chosen]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", default=[], help="attack function names")
    parser.add_argument("--quick", action="store_true", help="skip the rank check")
    args = parser.parse_args()

    chosen = list(args.only)
    if args.quick and not chosen:
        chosen = [a.__name__ for a in ATTACKS if a is not attack_invertibility]

    print("Ka'bah — menyerang permutasinya sendiri\n")
    failures = 0
    for result in run(chosen):
        verdict = "BERTAHAN" if result["pass"] else "TEMBUS"
        if not result["pass"]:
            failures += 1
        print(f"  [{verdict:>8}]  {result['name']}")
        for key, value in result.items():
            if key in ("name", "pass", "note"):
                continue
            print(f"              {key}: {value}")
        print(f"              — {result['note']}\n")

    print(f"{len(run(chosen)) - failures} bertahan, {failures} tembus")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
