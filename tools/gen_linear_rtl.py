#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate rtl/hijaiyyah_linear.v and its parity vectors from the sealed cube.

RHO and PI live in one place. This emits the Verilog that uses them and the
sixty-four random states the testbench checks against, so the RTL cannot fall
behind ``cube.linear_layer`` without ``--check`` failing.

    python3 tools/gen_linear_rtl.py            write the files
    python3 tools/gen_linear_rtl.py --check    fail if they are stale
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Dict

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from hijaiyyah.crypto import cube as C  # noqa: E402

#: Fixed so the vectors are reproducible; a generated file that changes on
#: every run is not a generated file.
SEED = 20260902
VECTORS = 64


def _rot(name: str, r: int) -> str:
    return name if r == 0 else f"{{{name}[{63 - r}:0], {name}[63:{64 - r}]}}"


def render() -> Dict[Path, str]:
    parity = "\n".join(
        f"    wire [63:0] parity{c} = lane[{c}] ^ lane[{c + 5}] ^ lane[{c + 10}] "
        f"^ lane[{c + 15}] ^ lane[{c + 20}];"
        for c in range(5)
    )
    fold = "\n".join(
        f"    wire [63:0] fold{c} = parity{(c - 1) % 5} ^ "
        f"{_rot(f'parity{(c + 1) % 5}', 1)};"
        for c in range(5)
    )
    theta = "\n".join(f"    wire [63:0] th{i} = lane[{i}] ^ fold{i % 5};" for i in range(25))
    moved = "\n".join(
        f"    assign out_state[{C.PI[i]}*64 +: 64] = {_rot(f'th{i}', C.RHO[i])};"
        for i in range(25)
    )

    rng = random.Random(SEED)
    ins, outs = [], []
    for _ in range(VECTORS):
        state = [rng.getrandbits(64) for _ in range(25)]
        image = C.linear_layer(state)
        ins.append("".join(f"{x:016x}" for x in reversed(state)))
        outs.append("".join(f"{x:016x}" for x in reversed(image)))

    return {
        _ROOT / "rtl" / "hijaiyyah_linear.v": _TEMPLATE.format(
            parity=parity, fold=fold, theta=theta, moved=moved
        ),
        _ROOT / "rtl" / "tb" / "linear_in.hex": "\n".join(ins) + "\n",
        _ROOT / "rtl" / "tb" / "linear_out.hex": "\n".join(outs) + "\n",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if stale")
    args = parser.parse_args(argv)

    stale = []
    for path, text in render().items():
        if path.exists() and path.read_text(encoding="utf-8") == text:
            continue
        stale.append(path)
        if not args.check:
            path.write_text(text, encoding="utf-8")

    if args.check and stale:
        names = ", ".join(str(p.relative_to(_ROOT)) for p in stale)
        print(f"stale: {names} — run python3 tools/gen_linear_rtl.py", file=sys.stderr)
        return 1
    if not args.check:
        print(f"wrote {len(render())} files")
    return 0


_TEMPLATE = '''// hijaiyyah_linear.v — theta then rho-pi, the round's linear layer.
//
// GENERATED from src/hijaiyyah/crypto/cube.py. Do not hand-edit: RHO and PI
// below come from the sealed cube, and a hand-edit is how the RTL and the
// Python stop agreeing. Regenerate with
//     python3 tools/gen_linear_rtl.py
//
// Pure wiring and XOR -- every lane rotation is a bit-select, costing nothing
// -- but "pure XOR" is not the same as "free". Synthesised, this layer is
// **2560 LUT4**, because each of 1600 output bits folds in two column
// parities as well as its own lane. That is more than a 25-byte substitution
// router (2023 LUT4), and it corrects the loose reasoning that first
// motivated the ramal schedule.
//
// The trade still holds, and now with numbers instead of a hand-wave. Against
// a full 200-byte substitution at 15,200 LUT4:
//
//     walk  [1,1,1]   3 linear + 3 sub   =  7,680 + 45,600 = 53,280 LUT4
//     ramal [2,1]     3 linear + 2 sub   =  7,680 + 30,400 = 38,080 LUT4
//
// a 28.5% saving. Time-multiplexed -- 25 bytes per clock, which is the shape
// that leaves room for the rest -- the same trade reads in clocks: 3 + 3x8 = 27
// against 3 + 2x8 = 19, a 30% saving. Buying a linear layer to sell a
// substitution layer is a good trade because the two are an order of
// magnitude apart, not because one of them is free.
//
//   theta   parity of each column, folded with a neighbour's rotated parity
//           D[x] = C[x-1] XOR rotl(C[x+1], 1)   <- both neighbours, every round
//   rho     lane i rotates left by RHO[i] = i(i+1)/2 mod 64
//   pi      lane i moves to PI[i] = 5(i mod 5) + ((i div 5) + 3(i mod 5)) mod 5
//
// Combinational: one propagation delay, no clock, no state. Checked against
// cube.linear_layer over 64 random states by rtl/tb/tb_hijaiyyah_linear.v.
// Three sabotages were induced before trusting that testbench -- a shifted rho
// rotation, a swapped pi destination, and a dropped theta neighbour -- and all
// three are caught. The first attempt at the rho sabotage silently matched
// nothing and reported PASS, which is its own lesson about sabotage tests.

`default_nettype none

module hijaiyyah_linear (
    input  wire [1599:0] in_state,
    output wire [1599:0] out_state
);

    wire [63:0] lane [0:24];
    genvar g;
    generate
        for (g = 0; g < 25; g = g + 1) begin : split
            assign lane[g] = in_state[g*64 +: 64];
        end
    endgenerate

    // ---- theta: column parity, folded with both neighbours -------------
{parity}

{fold}

{theta}

    // ---- rho and pi: rotate each lane, then move it -------------------
{moved}

endmodule

`default_nettype wire
'''


if __name__ == "__main__":
    sys.exit(main())
