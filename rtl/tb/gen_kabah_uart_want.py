#!/usr/bin/env python3
"""Golden state for tb_hijaiyyah_kabah_gowin_top.v.

One rate block, bytes(range(128)), absorbed lane-by-lane and permuted --
the same primitive tb_hijaiyyah_sponge.v is checked against, applied to the
exact 128-byte message the wrapper's testbench sends over its simulated
UART. This is what hijaiyyah_kabah_gowin_top.v must dump back out once,
byte-for-byte, MSB first, after one 128-byte frame.

Run from the repository root: python3 rtl/tb/gen_kabah_uart_want.py
"""
from __future__ import annotations

import hashlib
import hmac
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.crypto import cube  # noqa: E402


#: The wrapper's HMAC_KEY: RFC 4231 test case 1, twenty bytes of 0x0b. A
#: published test key, fixed in the bitstream -- it proves the path, nothing more.
TEST_KEY = bytes([0x0B]) * 20


def tag(state_bits: int) -> bytes:
    """Layer 3 over one reply: HMAC-SHA256 of the 200 state bytes as dumped."""
    return hmac.new(TEST_KEY, state_bits.to_bytes(200, "big"), hashlib.sha256).digest()


def _pack(state: list[int]) -> int:
    bits = 0
    for lane_index, value in enumerate(state):
        bits |= (value & cube.LANE_MASK) << (lane_index * cube.LANE_BITS)
    return bits


def main() -> None:
    state = [0] * cube.STATE_LANES
    step = 0

    # Block 1: bytes(range(128)). What the wrapper must dump after the first
    # 128-byte frame -- the only case tb_hijaiyyah_kabah_gowin_top.v checked
    # before this file also generated block 2's golden state.
    block1 = bytes(range(128))
    for i in range(0, len(block1), cube.LANE_BYTES):
        lane = int.from_bytes(block1[i:i + cube.LANE_BYTES], "little")
        state, step = cube.absorb_lane(state, lane, step)
    (ROOT / "rtl" / "tb" / "kabah_uart_want.hex").write_text(
        f"{_pack(state):0400x}\n", encoding="utf-8")
    (ROOT / "rtl" / "tb" / "kabah_uart_tag.hex").write_text(
        tag(_pack(state)).hex() + "\n", encoding="utf-8")

    # Block 2: bytes(128..255), absorbed into the SAME state with no reset in
    # between -- the wrapper only pulses `load` once, right after reset, so a
    # host that keeps streaming gets a real multi-block absorb rather than
    # 128 bytes re-hashed in isolation each time. This is what proves that
    # claim rather than leaving it asserted only in a comment.
    block2 = bytes(range(128, 256))
    for i in range(0, len(block2), cube.LANE_BYTES):
        lane = int.from_bytes(block2[i:i + cube.LANE_BYTES], "little")
        state, step = cube.absorb_lane(state, lane, step)
    (ROOT / "rtl" / "tb" / "kabah_uart_want2.hex").write_text(
        f"{_pack(state):0400x}\n", encoding="utf-8")
    (ROOT / "rtl" / "tb" / "kabah_uart_tag2.hex").write_text(
        tag(_pack(state)).hex() + "\n", encoding="utf-8")

    print("wrote rtl/tb/kabah_uart_want.hex, kabah_uart_want2.hex, "
          "kabah_uart_tag.hex and kabah_uart_tag2.hex")


if __name__ == "__main__":
    main()
