#!/usr/bin/env python3
"""hijrah_board.py -- HIJRAH counted by the HCPU, held against the Python.

    python3 rtl/scripts/hijrah_board.py /dev/tty.usbserial-X   # the board
    python3 rtl/scripts/hijrah_board.py                          # the interpreter

The board must be running loader.hasm. Runs rtl/programs/hijrah_sweep.hasm and
compares what it prints with the definition in src/: every letter's face from
hijaiyyah.core.exomatrix.build_exomatrix, reduced mod p, multiplied with
hijaiyyah.core.exomatrix._matmul_mod -- the same function the rest of the
repository composes faces with, not a second transcription of it.

What must agree, per modulus p in 2, 3, 4, 5:

  the 28 faces themselves, 700 values        -- the construction from the ROM
  distinct faces mod p                        -- length 1
  which pairs of letters collide mod p        -- the four of GF(2) by name
  distinct maps of length 1 OR 2              -- the faces and their 784
                                                 products as one set, the
                                                 cumulative count hijrah's
                                                 densities are built on

Densities are printed by this tool, log2(count)/length, from counts the board
had to get right; the board is not asked to take logarithms.

Timing is the free-running counter at 0xFF4: CLOCKS on the board, INSTRUCTIONS
in the interpreter. Each is printed with its unit and never compared.

Length 3 is not attempted, and hijrah_sweep.hasm says why: over mod 5 it
reaches 16,359 distinct maps, about 49,000 words packed, against 4,096 words
of data memory.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from jamrah_board import parse  # noqa: E402

from hijaiyyah.core.exomatrix import _matmul_mod, build_exomatrix  # noqa: E402
from hijaiyyah.core.master_table import MASTER_TABLE  # noqa: E402
from hijaiyyah.hisa.assembler import assemble  # noqa: E402
from hijaiyyah.hisa.machine import HISAMachine  # noqa: E402

PROGRAM = ROOT / "rtl" / "programs" / "hijrah_sweep.hasm"
LOAD_BASE = 64
MODULI = (2, 3, 4, 5)
RAW_DUMP = Path("/tmp/hijrah_board_raw.bin")

Face = tuple[tuple[int, ...], ...]


def faces() -> list[list[list[int]]]:
    return [build_exomatrix(e) for e in MASTER_TABLE.all_entries()]


def reduce(m: list[list[int]], p: int) -> Face:
    return tuple(tuple(x % p for x in row) for row in m)


def expected() -> dict[str, object]:
    """What the board must print, from the definition in src/."""
    fs = faces()
    out: dict[str, object] = {"faces": [x for m in fs for row in m for x in row]}
    for p in MODULI:
        red = [reduce(m, p) for m in fs]
        pairs = [(i + 1, j + 1) for i in range(28) for j in range(i + 1, 28)
                 if red[i] == red[j]]
        products = {_matmul_mod(a, b, p) for a in red for b in red}
        # Cumulative, like test_hijrah.py's _reachable: words of length 1 OR 2.
        out[p] = {"len1": len(set(red)), "pairs": pairs,
                  "len2": len(set(red) | products)}
    return out


def split(values: list[int]) -> dict[str, object]:
    """The printed stream, in the order hijrah_sweep.hasm prints it."""
    out: dict[str, object] = {"faces": values[:700]}
    pos = 700
    for p in MODULI:
        if values[pos] != p:
            raise ValueError(f"expected modulus {p} at position {pos}, got {values[pos]}")
        len1, npairs = values[pos + 1], values[pos + 2]
        flat = values[pos + 3:pos + 3 + 2 * npairs]
        pairs = [(flat[k], flat[k + 1]) for k in range(0, len(flat), 2)]
        q = pos + 3 + 2 * npairs
        out[p] = {"len1": len1, "pairs": pairs, "len2": values[q],
                  "t_products": values[q + 1], "t_count": values[q + 2]}
        pos = q + 3
    return out


def run_interpreter() -> list[int]:
    m = HISAMachine(MASTER_TABLE)
    m.load_program(assemble(PROGRAM.read_text(encoding="utf-8"),
                            base_dir=PROGRAM.parent))
    m.run()
    return list(m.output)


def run_board(port: str, timeout_s: float = 120.0) -> tuple[list[int], int, list[bytes]]:
    import serial  # pyserial, optional
    from send_program import encode
    stream = encode(assemble(PROGRAM.read_text(encoding="utf-8"),
                             base_dir=PROGRAM.parent, base=LOAD_BASE))
    raw = bytearray()
    with serial.Serial(port, 115200, timeout=0.2) as link:
        link.reset_input_buffer()
        link.write(stream)
        link.flush()
        deadline = time.time() + timeout_s
        while b"CYCLES=" not in raw and time.time() < deadline:
            raw += link.read(4096)
        raw += link.read(64)
    RAW_DUMP.write_bytes(bytes(raw))
    return parse(bytes(raw.split(b"CYCLES=")[0]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("port", nargs="?", help="serial device; omit to use the interpreter")
    args = ap.parse_args(argv)

    dropped, rejected = 0, []
    if args.port:
        values, dropped, rejected = run_board(args.port)
    else:
        values = run_interpreter()
    got, want = split(values), expected()
    unit = "clocks" if args.port else "instructions"
    ok = True

    faces_ok = got["faces"] == want["faces"]
    ok &= faces_ok
    print(f"faces: {'700/700 values agree' if faces_ok else 'DISAGREE'} "
          f"with build_exomatrix")
    for p in MODULI:
        g, w = got[p], want[p]
        assert isinstance(g, dict) and isinstance(w, dict)
        agree = all(g[k] == w[k] for k in ("len1", "pairs", "len2"))
        ok &= agree
        d1 = math.log2(g["len1"])
        d2 = math.log2(g["len2"]) / 2
        print(f"mod {p}: length 1 = {g['len1']:>3} (want {w['len1']}), "
              f"length 2 = {g['len2']:>4} (want {w['len2']})  "
              f"{d1:.2f} / {d2:.2f} bits per letter  "
              f"{'agree' if agree else 'DISAGREE'}")
        if g["pairs"]:
            print(f"        colliding pairs: {g['pairs']}")
        print(f"        {g['t_products']} {unit} forming 784 products, "
              f"{g['t_count']} {unit} counting them")
    if dropped:
        print(f"dropped {dropped} non-printing byte(s); raw capture in {RAW_DUMP}")
    for r in rejected[:5]:
        print(f"  rejected line, not a number: {r!r}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
