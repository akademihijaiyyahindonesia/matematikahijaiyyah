#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate rtl/hijaiyyah_sbox.v and its testbench from the sealed field.

One definition, two languages. The constants in the RTL — the tower's ν, the
two basis matrices, the affine constant, and every one of the 256 expected
outputs in the testbench — are derived from
:mod:`hijaiyyah.crypto.sbox_logic`, which derives them in turn from
``cube.POLYNOMIAL``. Hand-editing the Verilog is how the two stop agreeing,
so the header says not to and this is what to run instead.

    python3 tools/gen_sbox_rtl.py            write the files
    python3 tools/gen_sbox_rtl.py --check    fail if they are stale

``--check`` is the gate: the test suite runs it, so a change to the seal that
is not carried into the RTL is a failing test rather than a silicon bug.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Tuple

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from hijaiyyah.crypto import cube  # noqa: E402
from hijaiyyah.crypto import sbox_logic as logic  # noqa: E402

MODULE = _ROOT / "rtl" / "hijaiyyah_sbox.v"
TESTBENCH = _ROOT / "rtl" / "tb" / "tb_hijaiyyah_sbox.v"


def _inverse_anf():
    """The 4-bit inverse as algebraic normal form, one line per output bit.

    Written as a `case` first, and yosys inferred a 16x4 memory from it —
    `1 memories, 64 memory bits` in the netlist — while the comment above it
    claimed four LUT4s. On this FPGA the difference would not have mattered
    (a ROM that small maps to LUTs anyway), but a comment the netlist
    contradicts is how a timing claim becomes false somewhere it does matter.
    A sum of products over four variables cannot be inferred as memory by any
    flow, so the claim is now structural rather than a hope about synthesis.
    """
    for bit in range(4):
        truth = [(logic.GF4_INVERSE[x] >> bit) & 1 for x in range(16)]
        step = 1
        while step < 16:                       # Mobius transform, in place
            for i in range(16):
                if i & step:
                    truth[i] ^= truth[i ^ step]
            step <<= 1
        terms = [
            "1'b1" if m == 0
            else " & ".join(f"a[{i}]" for i in range(4) if (m >> i) & 1)
            for m in range(16)
            if truth[m]
        ]
        yield bit, " ^ ".join(terms)


def render() -> Tuple[str, str]:
    """The module and its testbench, as text."""
    r = logic.report()
    to_tower = "\n".join(
        f"    assign t[{i}] = ^(x & 8'h{m:02X});" for i, m in enumerate(logic.TO_TOWER)
    )
    from_tower = "\n".join(
        f"    assign u[{i}] = ^(w & 8'h{m:02X});" for i, m in enumerate(logic.FROM_TOWER)
    )
    cases = "\n".join(
        f"            gf4_inv[{bit}] = {expr};" for bit, expr in _inverse_anf()
    )
    vectors = "\n".join(
        f"        check(8'h{x:02X}, 8'h{cube.SBOX[x]:02X});" for x in range(256)
    )
    return (
        _MODULE_TEMPLATE.format(
            poly=r["polynomial"],
            nu=r["nu"],
            beta=r["beta"],
            affine=r["affine_constant"],
            xor_to=r["xor_to_tower"],
            xor_from=r["xor_from_tower"],
            xor_nu=r["xor_nu"],
            entries=r["table_entries"],
            to_tower=to_tower,
            from_tower=from_tower,
            cases=cases,
        ),
        _TESTBENCH_TEMPLATE.format(vectors=vectors),
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if stale")
    args = parser.parse_args(argv)

    module, testbench = render()
    stale = []
    for path, text in ((MODULE, module), (TESTBENCH, testbench)):
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == text:
            continue
        stale.append(path)
        if not args.check:
            path.write_text(text, encoding="utf-8")

    if args.check and stale:
        names = ", ".join(str(p.relative_to(_ROOT)) for p in stale)
        print(f"stale: {names} — run python3 tools/gen_sbox_rtl.py", file=sys.stderr)
        return 1
    if not args.check:
        print(f"wrote {MODULE.name} and {TESTBENCH.name}")
    return 0


_MODULE_TEMPLATE = '''// hijaiyyah_sbox.v — the substitution as logic, not as memory.
//
// GENERATED from src/hijaiyyah/crypto/sbox_logic.py. Do not hand-edit: the
// constants below are derived from the sealed polynomial {poly:#x}, and a
// hand-edit is how the RTL and the Python stop agreeing. Regenerate with
//     python3 tools/gen_sbox_rtl.py
//
// WHY THIS EXISTS. cube.py reads the S-box out of a 256-entry table. In
// software that is a data-indexed memory access — the target of the AES
// cache-timing attacks (Bernstein 2005; Osvik, Shamir, Tromer 2006), because
// the cache lines touched leak the index and the index is the state. This
// module has no memory in it at all. There is no address, no port to
// contend for, and no latency that depends on the value: one propagation
// delay, the same for every input. The timing property is not defended
// here, it is absent by construction.
//
// HOW. GF(2^8) is isomorphic to GF((2^4)^2), where inversion is cheap:
//
//     N     = nu*ah^2 + ah*al + al^2                  the norm, into GF(2^4)
//     A^-1  = (ah*N^-1)*y + ((ah^al)*N^-1)
//
// so the substitution is  x -> T -> composite inverse -> T^-1 -> affine,
// with T and T^-1 GF(2)-linear, which in gates means XOR trees.
//
// This is Canright's structure. What is NOT borrowed is the isomorphism:
// Canright's constants are for AES's 0x11B and the sealed cube chooses
// {poly:#x}, so nu, beta and both matrices were searched for this field,
// minimising XOR weight across T, T^-1 and multiplication by nu.
//
//   nu   = {nu:#x}        beta = {beta:#x}       subfield x^4+x+1
//   XOR cost: T = {xor_to}, T^-1 = {xor_from}, *nu = {xor_nu}
//   table entries: {entries}
//
// Checked bit-for-bit against cube.SBOX over all 256 inputs by
// tests/test_integrity/test_sbox_logic.py, and against this module by
// rtl/tb/tb_hijaiyyah_sbox.v. Neither is a claim; both are gates.

`default_nettype none

module hijaiyyah_sbox (
    input  wire [7:0] x,
    output wire [7:0] y
);

    // ---- change of basis into the tower -------------------------------
    wire [7:0] t;
{to_tower}

    wire [3:0] ah = t[7:4];
    wire [3:0] al = t[3:0];

    // ---- inverse in GF((2^4)^2) ---------------------------------------
    wire [3:0] ah2   = gf4_mul(ah, ah);
    wire [3:0] norm  = gf4_mul(ah2, 4'h{nu:x}) ^ gf4_mul(ah, al) ^ gf4_mul(al, al);
    wire [3:0] scale = gf4_inv(norm);

    wire [7:0] w = {{gf4_mul(ah, scale), gf4_mul(ah ^ al, scale)}};

    // ---- change of basis back -----------------------------------------
    wire [7:0] u;
{from_tower}

    // ---- affine tail: rotate, sum, add the sealed constant -------------
    assign y = u
             ^ {{u[6:0], u[7]}}
             ^ {{u[5:0], u[7:6]}}
             ^ {{u[4:0], u[7:5]}}
             ^ {{u[3:0], u[7:4]}}
             ^ 8'h{affine:02X};

    // ---- GF(2^4), x^4 + x + 1 ------------------------------------------
    // Unrolled shift-and-reduce. A function body with a bounded loop is
    // combinational: the synthesiser flattens it, no clock is involved.
    function [3:0] gf4_mul;
        input [3:0] a;
        input [3:0] b;
        reg   [3:0] acc;
        reg   [3:0] cur;
        integer i;
        begin
            acc = 4'h0;
            cur = a;
            for (i = 0; i < 4; i = i + 1) begin
                if (b[i]) acc = acc ^ cur;
                cur = cur[3] ? ((cur << 1) ^ 4'b0011) : (cur << 1);
            end
            gf4_mul = acc;
        end
    endfunction

    // The 4-bit inverse in algebraic normal form: four functions of four
    // variables, one LUT4 each. Written as a case statement first, which
    // yosys inferred as a 16x4 memory -- harmless on this part, but a
    // netlist that says "memory" under a comment that says "logic" is how a
    // timing claim quietly becomes false. A sum of products cannot be
    // inferred as memory by any flow.
    function [3:0] gf4_inv;
        input [3:0] a;
        begin
{cases}
        end
    endfunction

endmodule

`default_nettype wire
'''

_TESTBENCH_TEMPLATE = '''// tb_hijaiyyah_sbox.v — every input, against the sealed table.
//
// GENERATED from src/hijaiyyah/crypto/sbox_logic.py. The 256 expected values
// come from cube.SBOX itself, so this testbench cannot drift from the Python
// without the generator being re-run against a changed seal.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_sbox;
    reg  [7:0] x;
    wire [7:0] y;
    integer bad = 0;

    hijaiyyah_sbox dut (.x(x), .y(y));

    task check;
        input [7:0] input_byte;
        input [7:0] expected;
        begin
            x = input_byte;
            #1;
            if (y !== expected) begin
                bad = bad + 1;
                $display("MISMATCH x=%02h got=%02h want=%02h", input_byte, y, expected);
            end
        end
    endtask

    initial begin
{vectors}
        if (bad == 0)
            $display("PASS: 256/256 match cube.SBOX, no table in the path");
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
'''


if __name__ == "__main__":
    sys.exit(main())
