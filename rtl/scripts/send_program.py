#!/usr/bin/env python3
"""
Send a program to a running loader over the serial line.

This is the host half of the boot path. The board holds loader.hasm in its
bitstream; everything else arrives through here, so changing a program costs a
second instead of a resynthesis.

    python3 rtl/scripts/send_program.py /dev/tty.usbserial-X prog.hasm

The wire format is the loader's, most significant byte first:

    4 bytes   word count N
    4N bytes  the program

Big-endian because the loader assembles each word with `SHLI 8` then `OR`, so
the first byte it sees has to be the most significant one. Little-endian would
load every instruction byte-reversed and the board would run garbage that
looks almost like a program.

With no port given it writes the byte stream to stdout, which is what the
tests use -- there is no board in a test run, and a tool that can only talk to
hardware cannot be checked before the hardware exists.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from hijaiyyah.hisa.assembler import assemble  # noqa: E402

MAX_WORDS = 4096 - 64          # CODE_DEPTH minus where the loader puts things


def encode(words: list[int]) -> bytes:
    """The byte stream the loader expects."""
    if len(words) > MAX_WORDS:
        raise ValueError(
            f"{len(words)} words will not fit: the loader writes from address "
            f"64 and instruction memory holds 4096, so {MAX_WORDS} is the limit")
    out = bytearray(struct.pack(">I", len(words)))
    for word in words:
        out += struct.pack(">I", word & 0xFFFFFFFF)
    return bytes(out)


def load(path: Path) -> list[int]:
    """A .hasm is assembled; a .hex is read as one hex word per line."""
    if path.suffix == ".hex":
        return [int(line, 16) for line in path.read_text().split() if line.strip()]
    return assemble(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("port", nargs="?", help="serial device; omit to write stdout")
    ap.add_argument("program", type=Path)
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args(argv)

    words = load(args.program)
    stream = encode(words)

    if args.port is None:
        sys.stdout.buffer.write(stream)
        return 0

    try:
        import serial                       # pyserial, optional
    except ImportError:
        print("pyserial is not installed: pip install pyserial", file=sys.stderr)
        return 2

    with serial.Serial(args.port, args.baud, timeout=2) as link:
        link.write(stream)
        link.flush()
    print(f"sent {len(words)} words ({len(stream)} bytes) to {args.port}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
