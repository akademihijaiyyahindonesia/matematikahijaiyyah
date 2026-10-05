#!/usr/bin/env python3
"""
Test hijaiyyah_kabah_gowin_top.v against real hardware over a real port.

The wrapper's protocol: send exactly 128 bytes (one rate block), it answers
with exactly 232 bytes -- out_state, most-significant byte first, 200 bytes,
then layer 3: the 32-byte HMAC-SHA256 tag of those 200 bytes under the test
key fixed in the bitstream (since 3 October 2026). `load`
fires once, right after reset, so blocks sent back to back chain into one
absorb rather than 128 bytes re-hashed in isolation each time -- the same
thing tb_hijaiyyah_kabah_gowin_top.v proves in simulation, and the reason
this script keeps sending until the input is exhausted rather than stopping
after one frame.

    python3 rtl/scripts/kabah_uart_test.py /dev/tty.usbserial-X
    python3 rtl/scripts/kabah_uart_test.py /dev/tty.usbserial-X --input msg.bin

With no --input, the message is bytes(range(256)) -- two frames, the same
vectors rtl/tb/gen_kabah_uart_want.py already generated golden state for, so
a mismatch here means the board disagrees with a claim already proven in
simulation, not that the test vector itself is unverified.

With no port, it prints what it would have sent, computed, and compared --
what the tests use, since there is no board in a test run.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.crypto import cube  # noqa: E402

RATE = cube.RATE            # 128: one absorbed block
STATE_BYTES = cube.STATE_LANES * cube.LANE_BYTES   # 200: the dumped state
TAG_BYTES = 32                                     # layer 3: HMAC-SHA256 of it
REPLY_BYTES = STATE_BYTES + TAG_BYTES              # 232: one reply on the wire
#: The wrapper's HMAC_KEY: RFC 4231 test case 1, twenty bytes of 0x0b. A
#: published test key fixed in the bitstream -- it proves the path and is no
#: secret; a tag under it authenticates nothing to anyone who can read this.
TEST_KEY = bytes([0x0B]) * 20


def expected_tag(state: bytes) -> bytes:
    """Layer 3 over one reply: HMAC-SHA256 of the 200 state bytes as dumped,
    by hmac/hashlib -- not by anything of this repository's."""
    return hmac.new(TEST_KEY, state, hashlib.sha256).digest()


def expected_states(message: bytes) -> list[bytes]:
    """One 200-byte expected reply per RATE-byte block, chained -- the exact
    computation rtl/tb/gen_kabah_uart_want.py already ran for bytes(range(128))
    and bytes(range(128, 256))."""
    if len(message) % RATE:
        raise ValueError(f"message must be a multiple of {RATE} bytes, "
                          f"got {len(message)}")
    state = [0] * cube.STATE_LANES
    step = 0
    replies = []
    for block_start in range(0, len(message), RATE):
        block = message[block_start:block_start + RATE]
        for i in range(0, RATE, cube.LANE_BYTES):
            lane = int.from_bytes(block[i:i + cube.LANE_BYTES], "little")
            state, step = cube.absorb_lane(state, lane, step)
        bits = 0
        for lane_index, value in enumerate(state):
            bits |= (value & cube.LANE_MASK) << (lane_index * cube.LANE_BITS)
        replies.append(bits.to_bytes(STATE_BYTES, "big"))
    return replies


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", nargs="?", help="serial device; omit to compute and print only")
    ap.add_argument("--input", type=Path,
                     help="binary message, a multiple of 128 bytes (default: bytes(range(256)))")
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args(argv)

    message = args.input.read_bytes() if args.input else bytes(range(256))
    wants = expected_states(message)
    frames = len(message) // RATE

    if args.port is None:
        print(f"{frames} frame(s), {len(message)} bytes total, "
              f"{STATE_BYTES} expected state bytes and a {TAG_BYTES}-byte tag each:",
              file=sys.stderr)
        for i, want in enumerate(wants, 1):
            print(f"frame{i} want: {want.hex()}", file=sys.stderr)
            print(f"frame{i} tag:  {expected_tag(want).hex()}", file=sys.stderr)
        return 0

    try:
        import serial  # pyserial, optional
    except ImportError:
        print("pyserial is not installed: pip install pyserial", file=sys.stderr)
        return 2

    failures = 0
    with serial.Serial(args.port, args.baud, timeout=5) as link:
        for i in range(frames):
            block = message[i * RATE:(i + 1) * RATE]
            link.write(block)
            link.flush()
            reply = link.read(REPLY_BYTES)
            got, tag = reply[:STATE_BYTES], reply[STATE_BYTES:]
            want = wants[i]
            if len(reply) != REPLY_BYTES:
                print(f"frame{i + 1}: only got {len(reply)}/{REPLY_BYTES} bytes "
                      f"-- timed out or the wrapper sent less than it should",
                      file=sys.stderr)
                failures += 1
                continue
            # The tag is checked against the bytes the board SENT, so a wrong
            # state and a wrong tag are two findings, not one.
            if not hmac.compare_digest(tag, expected_tag(got)):
                print(f"frame{i + 1}: TAG MISMATCH -- got {tag.hex()}, "
                      f"HMAC-SHA256 of the state received is {expected_tag(got).hex()}",
                      file=sys.stderr)
                failures += 1
            else:
                print(f"frame{i + 1}: tag PASS, HMAC-SHA256 of the 200 bytes received",
                      file=sys.stderr)
            if got != want:
                mismatches = [j for j in range(STATE_BYTES) if got[j] != want[j]]
                print(f"frame{i + 1}: MISMATCH at {len(mismatches)} byte(s), "
                      f"first at index {mismatches[0]}: "
                      f"got {got[mismatches[0]]:02x} want {want[mismatches[0]]:02x}",
                      file=sys.stderr)
                failures += 1
            else:
                print(f"frame{i + 1}: PASS, 200/200 bytes match cube.py", file=sys.stderr)

    if failures:
        print(f"FAIL: {failures}/{frames} frame(s) mismatched", file=sys.stderr)
        return 1
    print(f"PASS: {frames}/{frames} frame(s), {STATE_BYTES * frames} bytes total, "
          f"all match cube.py, and {frames}/{frames} tag(s) are HMAC-SHA256 of them",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
