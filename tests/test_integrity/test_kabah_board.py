"""The Ka'bah lab: what it asks the board, checked against cube.py first.

rtl/scripts/kabah_board.py measures the sponge in silicon -- chained integrity,
replay, avalanche, mutation. Everything it compares against comes from
src/hijaiyyah/crypto/cube.py through kabah_uart_test.expected_states, so these
tests pin the pieces that could quietly stop meaning anything: the bit flip,
the distance, and the two different answers "replay" has.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from kabah_board import STATE_BITS, distance, flip  # noqa: E402
from kabah_uart_test import RATE, STATE_BYTES, expected_states  # noqa: E402


def test_flip_changes_exactly_one_bit() -> None:
    block = bytes(RATE)
    for bit in (0, 7, 8, 511, RATE * 8 - 1):
        assert distance(block, flip(block, bit)) == 1


def test_distance_is_the_hamming_distance() -> None:
    assert distance(b"\x00\x00", b"\x00\x00") == 0
    assert distance(b"\xff", b"\x00") == 8
    assert distance(b"\x0f", b"\xf0") == 8


def test_a_frame_repeated_does_not_repeat_its_state() -> None:
    """The sponge chains: the second frame absorbs on top of the first, so
    'replay' inside one run must NOT give the same state. The board is asked
    for exactly this, and would be wrong if it agreed."""
    block = bytes(range(RATE))
    states = expected_states(block + block)
    assert len(states) == 2
    assert states[0] != states[1]


def test_replay_from_a_fresh_start_repeats_exactly() -> None:
    """And across a reconfiguration it must, which is the other half."""
    block = bytes(range(RATE))
    assert expected_states(block) == expected_states(block)


def test_one_flipped_bit_moves_about_half_the_state() -> None:
    """The figure the board is measured against: cube.py's own ~0.5, computed
    here over the same kind of trial the lab runs on silicon."""
    rng = random.Random(20260920)
    dists = []
    for _ in range(8):
        block = bytes(rng.randrange(256) for _ in range(RATE))
        bit = rng.randrange(RATE * 8)
        a = expected_states(block)[0]
        b = expected_states(flip(block, bit))[0]
        assert len(a) == STATE_BYTES
        dists.append(distance(a, b))
    mean = sum(dists) / len(dists) / STATE_BITS
    assert 0.45 < mean < 0.55, mean
