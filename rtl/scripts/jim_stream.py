#!/usr/bin/env python3
"""jim_stream.py -- Jim's own machine, used as a test-case generator.

    python3 rtl/scripts/jim_stream.py --field 2 --bytes 32

cosmic-codex-jim/ measures one thing about the letter Jim: read its 5x5 face as
a linear map and iterate it, and over GF(2) it is a maximum-length LFSR --
period 31, the largest a 5-dimensional state can have -- while over GF(5) it
reaches 3124, also maximal. That is the whole of what is claimed, and
cosmic-codex-jim/LIMITS.md records three readings that were tried and FAILED:
Jim is not the metric centre, centring the encoding on it is 12% worse, and it
is a poor pivot.

So this module uses Jim for the one thing it measurably is: a deterministic
sequence generator with a known period. The stream is structured rather than
random, and that is the point of asking it for attack cases -- whether a
structured sweep reaches anything a random one does not. It is NOT claimed to
be a better generator, and nothing here is evidence about security.

-- the stream -------------------------------------------------------------
State is a 5-vector over GF(p), stepped by v <- M v mod p with M the face.
Over GF(2) each step yields five bits, packed most significant first; over
GF(5) each state is read as a base-5 number, 0..3124, and taken mod 256. Both
mappings are stated here because a generator whose output depends on an unstated
convention cannot be reproduced.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.core.exomatrix import build_exomatrix  # noqa: E402
from hijaiyyah.core.master_table import MASTER_TABLE  # noqa: E402

JIM = 4                     # 0-based index; HLOAD 5 on the board
PERIODS = {2: 31, 5: 3124}  # measured in cosmic-codex-jim/MACHINE.md


def face(p: int) -> list[list[int]]:
    entry = MASTER_TABLE.all_entries()[JIM]
    return [[x % p for x in row] for row in build_exomatrix(entry)]


def states(p: int, start: list[int] | None = None):
    """Successive states v, Mv, M^2 v, ... mod p. Infinite, and periodic."""
    m = face(p)
    v = list(start) if start else [1, 0, 0, 0, 0]
    while True:
        yield list(v)
        v = [sum(m[i][k] * v[k] for k in range(5)) % p for i in range(5)]


def period(p: int, start: list[int] | None = None, cap: int = 100_000) -> int:
    """How many steps before a state repeats -- measured, not assumed."""
    seen: dict[tuple[int, ...], int] = {}
    for i, v in enumerate(states(p, start)):
        key = tuple(v)
        if key in seen:
            return i - seen[key]
        seen[key] = i
        if i > cap:
            raise ValueError("no repeat within the cap")
    raise AssertionError("unreachable")


def stream(p: int, count: int, start: list[int] | None = None) -> bytes:
    """`count` bytes from the sequence, by the mapping stated in the header."""
    out = bytearray()
    if p == 2:
        bits: list[int] = []
        for v in states(p, start):
            bits.extend(v)
            while len(bits) >= 8:
                byte, bits = bits[:8], bits[8:]
                out.append(int("".join(str(b) for b in byte), 2))
                if len(out) == count:
                    return bytes(out)
    else:
        for v in states(p, start):
            value = sum(c * p ** i for i, c in enumerate(v))
            out.append(value % 256)
            if len(out) == count:
                return bytes(out)
    raise AssertionError("unreachable")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--field", type=int, default=2, choices=sorted(PERIODS))
    ap.add_argument("--bytes", type=int, default=32)
    args = ap.parse_args(argv)
    measured = period(args.field)
    print(f"GF({args.field}): period {measured} "
          f"(cosmic-codex-jim records {PERIODS[args.field]})")
    print(stream(args.field, args.bytes).hex())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
