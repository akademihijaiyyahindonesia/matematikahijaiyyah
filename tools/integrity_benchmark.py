#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure the integrity claim of Bab III §IIIC.3.2.1.

The book states the advantage as "Validasi O(1) vs CRC O(n)" and never puts a
number on it. This does, in retired instructions, which is the architectural
quantity — wall-clock on a Python interpreter would measure Python.

Two comparisons, kept apart because they are different claims:

**The method.** Guarding a codex is six checks over eighteen integers, and the
aggregate of a whole string is itself one codex, so the cost does not move with
string length. A CRC has to touch every byte. That advantage belongs to the
mathematics and is available on any processor.

**The machine.** HCPU does the guard in one instruction where RV32I needs
forty-four. That is a constant factor, not an asymptotic one — both grow
linearly in the number of letters loaded.

Confusing the two overstates the case, so they are reported separately and
multiplied only where the composition is honest.

**What is measured and what is counted.** The HCPU column is measured: the
programs are assembled and executed on hijaiyyah.hisa.machine, and the number
is the trace length. The RV32I column is a static instruction count taken from
a sequence written out in full at rtl/reference/guard_g1_g4_t1_t2.rv32i.s, so
it can be read and disputed. It is not a measurement, and is labelled as such
in the output. No cache, pipeline or memory effects are modelled on either
side.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import List

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from hijaiyyah.core.master_table import MASTER_TABLE  # noqa: E402
from hijaiyyah.hisa.assembler import assemble  # noqa: E402
from hijaiyyah.hisa.machine import HISAMachine  # noqa: E402

# ── Static instruction counts, from written-out sequences ────────

#: rtl/reference/guard_g1_g4_t1_t2.rv32i.s — 17 loads, 15 arithmetic, 6 branches.
RV32I_GUARD = 44

#: Componentwise add of 18 components, SWAR over five 32-bit words:
#: two loads, six masking operations and a store per word.
RV32I_CADD = 45

#: Loading an 18-component codex, one word each.
RV32I_LOAD = 18

#: Table-driven CRC32, per byte: load, xor, index, load table, xor, shift.
RV32I_CRC_PER_BYTE = 5

#: One letter nibble-packed (§IIIC.3.3): 18 components x 4 bits.
HISAB_BYTES_PER_LETTER = 9


@dataclass
class Row:
    n: int
    hcpu_measured: int
    rv32i_guard: int
    rv32i_crc: int

    @property
    def method_ratio(self) -> float:
        """Guard versus CRC, both on the same processor."""
        return self.rv32i_crc / RV32I_GUARD

    @property
    def machine_ratio(self) -> float:
        """HCPU versus RV32I, both running the guard."""
        return self.rv32i_guard / self.hcpu_measured


def hcpu_cycles(n: int) -> int:
    """Measured: assemble and execute, then count retired instructions.

    Loads n letters, aggregates them, and guards the aggregate.
    """
    letters = [e.index for e in MASTER_TABLE.all_entries()]
    lines: List[str] = []
    # H15 accumulates; H0 is a scratch slot reused for every letter. Without
    # the reuse only the first fifteen letters were aggregated and the ratio
    # drifted upward with n, comparing a short HCPU program against a full
    # RV32I one.
    lines.append(f"HLOAD H15, #{letters[0]}")
    for slot in range(1, n):
        lines.append(f"HLOAD H0, #{letters[slot % len(letters)]}")
        lines.append("HCADD H15, H15, H0")
    lines.append("HGRD H15")
    lines.append("HALT")

    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(assemble("\n".join(lines) + "\n"))
    trace = machine.run()
    return len(trace)


def rv32i_pipeline(n: int) -> int:
    """Static: load n codices, aggregate, guard the result."""
    return RV32I_LOAD * n + RV32I_CADD * max(n - 1, 0) + RV32I_GUARD


def rv32i_crc(n: int) -> int:
    """Static: CRC32 over the packed frames of n letters."""
    return HISAB_BYTES_PER_LETTER * n * RV32I_CRC_PER_BYTE


def collect(lengths: List[int]) -> List[Row]:
    return [
        Row(n, hcpu_cycles(n), rv32i_pipeline(n), rv32i_crc(n)) for n in lengths
    ]


def report(rows: List[Row]) -> None:
    print("Integritas codex — §IIIC.3.2.1, diukur\n")

    print("A · METODE  (prosesor sama, dua cara memvalidasi)")
    print("   Guard tidak bergantung n; agregat n huruf tetap satu codex.\n")
    print(f"   {'n':>6}{'guard':>10}{'CRC32':>12}{'rasio':>10}")
    print("   " + "-" * 38)
    for row in rows:
        print(
            f"   {row.n:>6}{RV32I_GUARD:>10}{row.rv32i_crc:>12,}"
            f"{row.method_ratio:>9.0f}x"
        )

    print("\nB · MESIN  (metode sama, dua prosesor)")
    print("   HCPU: diukur di hisa.machine. RV32I: hitungan statis.\n")
    print(f"   {'n':>6}{'HCPU':>10}{'RV32I':>12}{'rasio':>10}")
    print("   " + "-" * 38)
    for row in rows:
        print(
            f"   {row.n:>6}{row.hcpu_measured:>10}{row.rv32i_guard:>12,}"
            f"{row.machine_ratio:>9.1f}x"
        )

    print("\n   Rasio mesin mendatar: keduanya linear dalam n. Faktor konstan,")
    print("   bukan keunggulan asimtotik — hanya rasio metode tumbuh dengan n.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lengths", type=int, nargs="+", default=[1, 3, 10, 28, 100, 1000],
        help="string lengths to report",
    )
    report(collect(parser.parse_args().lengths))


if __name__ == "__main__":
    main()
