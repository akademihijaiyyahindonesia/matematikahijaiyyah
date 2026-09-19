#!/usr/bin/env python3
"""kabah_board.py -- what the Ka'bah sponge does in silicon, measured.

    python3 rtl/scripts/kabah_board.py /dev/tty.usbserial-X \\
        --bitstream rtl/fpga/gowin/hijaiyyah_kabah_gowin_top.fs
    python3 rtl/scripts/kabah_board.py                    # compute only, no board

rtl/scripts/kabah_uart_test.py already proves the wrapper answers bytes(range(256))
with the 400 bytes cube.py computes. That is "the right answer for one message".
This asks the questions the owner named for the third validation report --
avalanche, collisions, bit-flip integrity, mutation, replay -- and it asks them
of the BOARD, since cube.py's own avalanche figure was measured in Python.

-- what is being measured, and what it is not -----------------------------
The sponge is layer 2 of Ka'bah and is marked [EH] in src/hijaiyyah/crypto/
cube.py: "not a vetted hash -- use hashlib.sha256 for anything that matters".
Layer 3, HMAC-SHA256, is the one that carries security. Nothing here is a
security claim; these are measurements of a permutation's diffusion in silicon.

-- the protocol, unchanged -------------------------------------------------
The wrapper takes exactly 128 bytes and answers with 200: the whole state,
most significant byte first. `load` fires once after reset, so frames sent back
to back CHAIN into one absorb. Two messages can therefore only be compared from
a fresh configuration each -- which is why an avalanche trial reconfigures the
board between its two halves, and why "replay" here has two different answers
depending on whether the board was reset in between.
"""
from __future__ import annotations

import argparse
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from kabah_uart_test import RATE, STATE_BYTES, expected_states  # noqa: E402

STATE_BITS = STATE_BYTES * 8


def flip(block: bytes, bit: int) -> bytes:
    b = bytearray(block)
    b[bit // 8] ^= 1 << (bit % 8)
    return bytes(b)


def distance(a: bytes, b: bytes) -> int:
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b, strict=True))


def configure(bitstream: Path) -> None:
    subprocess.run(["openFPGALoader", "-b", "tangnano20k", str(bitstream)],
                   check=True, capture_output=True)
    time.sleep(0.5)


def run_message(port: str, message: bytes, baud: int = 115200) -> list[bytes]:
    """Send the message frame by frame; one 200-byte reply per frame."""
    import serial  # pyserial, optional
    out = []
    with serial.Serial(port, baud, timeout=5) as link:
        link.reset_input_buffer()
        for i in range(0, len(message), RATE):
            link.write(message[i:i + RATE])
            link.flush()
            out.append(link.read(STATE_BYTES))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("port", nargs="?", help="serial device; omit to compute only")
    ap.add_argument("--bitstream", type=Path,
                    default=ROOT / "rtl" / "fpga" / "gowin" / "hijaiyyah_kabah_gowin_top.fs")
    ap.add_argument("--frames", type=int, default=8,
                    help="frames in the chained-integrity run")
    ap.add_argument("--avalanche", type=int, default=16,
                    help="single-bit trials; each reconfigures the board twice")
    ap.add_argument("--seed", type=int, default=20260920)
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    message = bytes(rng.randrange(256) for _ in range(args.frames * RATE))
    wants = expected_states(message)
    trials = [(bytes(rng.randrange(256) for _ in range(RATE)),
               rng.randrange(RATE * 8)) for _ in range(args.avalanche)]

    if args.port is None:
        print(f"chained run: {args.frames} frames, {len(wants)} expected states")
        print(f"avalanche: {len(trials)} trials, one flipped bit each, "
              f"{STATE_BITS} state bits compared")
        print(f"first expected state: {wants[0].hex()[:32]}...")
        return 0

    ok = True
    # Only the states that OUGHT to differ. The replay run and the repeated
    # first frame are deliberate duplicates, and counting them as collisions
    # would report a number that means nothing.
    seen: list[bytes] = []

    # 1. the chain: every frame's state, against cube.py
    configure(args.bitstream)
    got = run_message(args.port, message)
    seen += got
    agree = sum(1 for g, w in zip(got, wants, strict=True) if g == w)
    ok &= agree == len(wants)
    print(f"chained integrity: {agree}/{len(wants)} frames match cube.py "
          f"({STATE_BYTES} bytes each)")

    # 2. replay, both meanings
    configure(args.bitstream)
    again = run_message(args.port, message)
    same_after_reset = again == got
    ok &= same_after_reset
    print(f"replay after reconfiguration: "
          f"{'identical' if same_after_reset else 'DIFFERENT'}")
    one = message[:RATE]
    configure(args.bitstream)
    twice = run_message(args.port, one + one)
    seen += [twice[1]]
    chained = twice[0] != twice[1]
    ok &= chained
    print(f"the same frame twice without reset: "
          f"{'different states -- the sponge chains' if chained else 'IDENTICAL'}")

    # 3. avalanche, and integrity of the mutated input
    dists, bad = [], 0
    for block, bit in trials:
        configure(args.bitstream)
        a = run_message(args.port, block)[0]
        configure(args.bitstream)
        b = run_message(args.port, flip(block, bit))[0]
        if a != expected_states(block)[0] or b != expected_states(flip(block, bit))[0]:
            bad += 1
        dists.append(distance(a, b))
        seen += [a, b]
    ok &= bad == 0
    if dists:
        lo, hi = min(dists), max(dists)
        mean = sum(dists) / len(dists)
        print(f"avalanche over {len(dists)} single-bit flips: "
              f"mean {mean / STATE_BITS:.4f} of {STATE_BITS} bits "
              f"({mean:.1f}), min {lo / STATE_BITS:.4f}, max {hi / STATE_BITS:.4f}")
        print(f"mutated inputs still match cube.py: "
              f"{len(dists) - bad}/{len(dists)}")

    # 4. no two states that should differ came back equal
    distinct = len(set(seen))
    ok &= distinct == len(seen)
    print(f"states that should differ: {distinct}/{len(seen)} distinct")
    print("  no collision found -- which is a statement about "
          f"{len(seen)} states, not about the sponge")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
