#!/usr/bin/env python3
"""Send a program container to sd_writer.hasm, one sector at a time.

    python3 rtl/scripts/send_container.py /dev/tty.usbserial-X image.hex \
        --writer rtl/programs/sd_writer.hasm

The board must be running loader.hasm. `--writer` sends sd_writer.hasm through
it and then KEEPS THE PORT OPEN: the board announces it is ready a few
milliseconds after the writer starts, and a port closed and reopened in between
would miss that line. Without `--writer` the board must already be running the
writer and not yet have spoken. The container comes from
rtl/scripts/build_container.py.

The wire format is loader.hasm's -- four bytes of word count, most significant
first, then the words -- with ONE difference, and it is the reason this file
exists: the host speaks only when the board has said it is listening. The
board says it with a line, the running sector count: `0` once the card is
initialised, then `1`, `2`, ... after each sector is on the card, and the host
sends the next 128 words only after the line for the previous ones.

Why not simply send everything, as send_program.py does? Measured on the board,
18 September 2026: the RX register holds one byte, the board is deaf while it
writes a sector, and a 437-word container produced not one byte of output. The
owner chose an acknowledgement over a delay -- a delay only happens to fit one
cable and one card; an acknowledgement holds on any of them.

With no port given it prints the chunk plan instead, so it can be checked
without a board.
"""
from __future__ import annotations

import argparse
import struct
import sys
import time
from pathlib import Path

SECTOR_WORDS = 128
ACK_TIMEOUT_S = 5.0     # one sector write takes milliseconds; five seconds is a dead card


def chunks(words: list[int]) -> list[bytes]:
    """The byte groups sent between acknowledgements.

    The first carries the word count in front of the first sector's words, so
    the board reads its count and then exactly one sector before it answers.
    """
    out: list[bytes] = []
    for start in range(0, len(words), SECTOR_WORDS):
        body = b"".join(struct.pack(">I", w & 0xFFFFFFFF)
                        for w in words[start:start + SECTOR_WORDS])
        if start == 0:
            body = struct.pack(">I", len(words)) + body
        out.append(body)
    return out


def read_line(link, deadline: float) -> bytes:  # type: ignore[no-untyped-def]
    line = bytearray()
    while time.time() < deadline:
        b = link.read(1)
        if not b:
            continue
        if b == b"\n":
            return bytes(line)
        line += b
    raise TimeoutError(f"no acknowledgement; got {bytes(line)!r} so far")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("port", nargs="?", help="serial device; omit to print the plan")
    ap.add_argument("container", type=Path)
    ap.add_argument("--writer", type=Path,
                    help="send this program through loader.hasm first, on the same open port")
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args(argv)

    words = [int(t, 16) for t in args.container.read_text().split() if t.strip()]
    plan = chunks(words)

    if args.port is None:
        print(f"{len(words)} words, {len(plan)} sectors; wait for '0' first")
        for i, c in enumerate(plan, 1):
            print(f"  sector {i}: {len(c)} bytes, then wait for '{i}'")
        return 0

    try:
        import serial  # pyserial, optional
    except ImportError:
        print("pyserial is not installed: pip install pyserial", file=sys.stderr)
        return 2

    with serial.Serial(args.port, args.baud, timeout=0.1) as link:
        link.reset_input_buffer()
        if args.writer is not None:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from send_program import encode, load
            link.write(encode(load(args.writer)))
            link.flush()
        ready = read_line(link, time.time() + ACK_TIMEOUT_S).strip()
        if ready != b"0":
            print(f"board is not ready: said {ready!r}", file=sys.stderr)
            return 1
        for i, c in enumerate(plan, 1):
            link.write(c)
            link.flush()
            ack = read_line(link, time.time() + ACK_TIMEOUT_S).strip()
            if ack != str(i).encode():
                print(f"sector {i}: expected ACK {i}, board said {ack!r}",
                      file=sys.stderr)
                return 1
            print(f"sector {i} acknowledged", file=sys.stderr)
        final = [read_line(link, time.time() + ACK_TIMEOUT_S).strip()
                 for _ in range(2)]
    print("board:", b" ".join(final).decode("ascii", "replace"))
    return 0 if final == [b"1", str(len(plan)).encode()] else 1


if __name__ == "__main__":
    raise SystemExit(main())
