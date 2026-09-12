#!/usr/bin/env python3
"""The bitstream rack: slots loaded in sequence, not fitted side by side.

For a while this project treated "HCPU and Ka'bah on one chip" as a single
top level, measured it at 105% -- over by 960 cells -- and filed it as a
blocker. That framing was an assumption, not a requirement. Nothing ever
demanded the two occupy the fabric at the same instant.

A rack does not. Each slot is its own bitstream, and the FPGA is
reconfigured between them, so the fabric is spent **in sequence**. The
budget question changes shape with it:

    side by side   sum(slots)   must fit at once   14,726 + 12,061 + 15,141 = 202%
    in sequence    max(slots)   one at a time                      15,141 =  73%

So the rack costs what its **largest** slot costs, and the 105% has nothing
to fit into. What each slot does not use is not waste either: it is the
budget a comparator can occupy alongside that slot, and it is largest
exactly where the slot is smallest.

**Nothing here is simulated.** Every bitstream listed is one the gowin
Makefile builds (`bitstream`, `kabah_bitstream`, `hdmi_bitstream`), every
figure is nextpnr's own post-routing report copied from the wrapper that
records it, and `openFPGALoader` is what loads them. The .fs files are
build outputs git does not carry, so a clean checkout has none until built. Where a figure has not
been measured it is None, not a guess. The HDMI slot was exactly that
until 11 September -- it had run on the board and nothing recorded its
cost -- and while it was, the rack quoted 67%: the maximum of the two slots
that had numbers, true of them and false of the rack. Measured, the video
slot is the largest, and the rack costs 73%.

    python3 rtl/scripts/rack.py            # print the rack
    python3 rtl/scripts/rack.py --detect   # is a board attached
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: GW2AR-LV18QN88C8/I7, the board this project has.
BOARD_LUT4 = 20_736
BOARD_DFF = 15_552
BOARD_BSRAM = 46


@dataclass(frozen=True)
class Slot:
    """One bitstream, and what occupying the fabric costs it.

    `lut4`/`dff`/`bsram`/`fmax_mhz` are nextpnr's post-routing figures,
    copied from the wrapper header that records them under a fingerprint.
    None means never measured -- the rack refuses to fill a column it has no
    measurement for.
    """

    name: str
    bitstream: str
    runs: str
    verified: str
    lut4: Optional[int] = None
    dff: Optional[int] = None
    bsram: Optional[int] = None
    fmax_mhz: Optional[float] = None

    @property
    def path(self) -> pathlib.Path:
        return ROOT / self.bitstream

    @property
    def built(self) -> bool:
        return self.path.is_file()

    @property
    def measured(self) -> bool:
        return self.lut4 is not None

    @property
    def occupancy(self) -> Optional[float]:
        """Fraction of the board's LUT4 this slot holds while it is loaded.

        Rendered with truncation, not rounding, because that is what nextpnr
        does: 14,005 / 20,736 is 67.5%, and its report says 67%. Rounding
        here would put a third number -- 68% -- next to two that agree.
        """
        return None if self.lut4 is None else self.lut4 / BOARD_LUT4

    @property
    def spare_lut4(self) -> Optional[int]:
        """What a comparator could occupy alongside this slot."""
        return None if self.lut4 is None else BOARD_LUT4 - self.lut4


#: The rack, in load order. Order is the sequence, and the sequence is the
#: point: these never coexist, so their costs never add.
SLOTS: Tuple[Slot, ...] = (
    Slot(
        name="hcpu",
        bitstream="rtl/fpga/gowin/hcpu_gowin_top.fs",
        runs="H-ISA pipeline, 79 opcodes, sealed 28-letter ROM",
        verified="UART returned 23 bytes matching simulation byte for byte; "
                 "e3_sweep28 returned 28/28 Theta-hat",
        lut4=14_726, dff=4_481, bsram=17, fmax_mhz=120.31,
    ),
    Slot(
        name="kabah",
        bitstream="rtl/fpga/gowin/hijaiyyah_kabah_gowin_top.fs",
        runs="Ka'bah sponge, SLICE_BYTES=25, UART feed and dump",
        verified="2/2 frames, 400/400 bytes matching cube.py, chained with "
                 "no reset between them",
        lut4=12_061, dff=1_965, bsram=0, fmax_mhz=165.98,
    ),
    Slot(
        name="hdmi",
        bitstream="rtl/fpga/gowin/hcpu_hdmi_top.fs",
        runs="1280x720 over TMDS, carrying loader and HCPU in the same "
             "bitstream",
        verified="rebuilt by the Makefile byte-identical to the bitstream the "
                 "board ran with the monitor lit; answered test_bsm over the "
                 "wire, 23 bytes, 112",
        lut4=15_141, dff=4_552, bsram=17, fmax_mhz=63.21,
    ),
)


def largest() -> Slot:
    """The slot that sets the rack's cost. Sequence means max, not sum."""
    measured = [s for s in SLOTS if s.measured]
    if not measured:
        raise RuntimeError("no slot has a measured LUT4 figure")
    return max(measured, key=lambda s: s.lut4 or 0)


def naive_sum_lut4() -> int:
    """What the slots would cost side by side -- the framing this replaces."""
    return sum(s.lut4 or 0 for s in SLOTS if s.measured)


def detect() -> bool:
    """Is a board attached. Runs openFPGALoader, reports rather than raises."""
    try:
        out = subprocess.run(["openFPGALoader", "--detect"],
                             capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return "GW2A" in (out.stdout + out.stderr)


def flash(slot: Slot, sram: bool = True) -> subprocess.CompletedProcess:
    """Load one slot onto the board.

    Deliberately one slot per call and never a loop over SLOTS: reconfiguring
    the board is what makes a slot the *current* one, and a caller sequencing
    the rack should be the thing deciding when that happens -- not a helper
    doing it three times because a list had three entries.
    """
    if not slot.built:
        raise FileNotFoundError(f"{slot.bitstream} has not been built")
    cmd = ["openFPGALoader", "-b", "tangnano20k"]
    if sram:
        cmd.append("-m")  # SRAM: gone at power-off, which a rack wants
    cmd.append(str(slot.path))
    return subprocess.run(cmd, capture_output=True, text=True)


def _fmt(value: Optional[float], unit: str = "") -> str:
    return "—" if value is None else f"{value:,.0f}{unit}".replace(",", ".")


def render() -> str:
    lines = [
        "RACK BITSTREAM — slot berurutan, bukan berdampingan",
        "",
        f"{'slot':8} {'LUT4':>8} {'%':>6} {'DFF':>7} {'BSRAM':>6} "
        f"{'Fmax':>9} {'sisa LUT4':>11}  bitstream",
    ]
    for s in SLOTS:
        pct = "—" if s.occupancy is None else f"{int(s.occupancy * 100)}%"
        fmax = "—" if s.fmax_mhz is None else f"{s.fmax_mhz:.2f}"
        lines.append(
            f"{s.name:8} {_fmt(s.lut4):>8} {pct:>6} {_fmt(s.dff):>7} "
            f"{_fmt(s.bsram):>6} {fmax:>9} {_fmt(s.spare_lut4):>11}  "
            f"{'ada' if s.built else 'BELUM DIBANGUN'}")

    top = largest()
    lines += [
        "",
        f"Biaya rack   = slot terbesar ({top.name}) = {top.lut4:,} LUT4 = "
        f"{int(top.occupancy * 100)}%".replace(",", "."),
        f"Jumlah naif  = {naive_sum_lut4():,} LUT4 = "
        f"{int(naive_sum_lut4() / BOARD_LUT4 * 100)}% — angka yang hanya berlaku "
        f"kalau slot harus muat bersamaan".replace(",", "."),
        "",
        f"Anggaran pembanding di slot tersempit: {top.spare_lut4:,} LUT4"
        .replace(",", "."),
    ]
    unmeasured = [s.name for s in SLOTS if not s.measured]
    if unmeasured:
        lines.append(f"Belum terukur: {', '.join(unmeasured)} — kolomnya "
                     f"dikosongkan, bukan ditebak.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--detect", action="store_true",
                        help="check whether a board is attached")
    args = parser.parse_args()

    print(render())
    if args.detect:
        print()
        print("Papan terdeteksi." if detect() else "Tidak ada papan terdeteksi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
