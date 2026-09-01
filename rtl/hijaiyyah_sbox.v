// hijaiyyah_sbox.v — the substitution as logic, not as memory.
//
// GENERATED from src/hijaiyyah/crypto/sbox_logic.py. Do not hand-edit: the
// constants below are derived from the sealed polynomial 0x12b, and a
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
// 0x12b, so nu, beta and both matrices were searched for this field,
// minimising XOR weight across T, T^-1 and multiplication by nu.
//
//   nu   = 0xd        beta = 0x71       subfield x^4+x+1
//   XOR cost: T = 19, T^-1 = 19, *nu = 3
//   table entries: 0
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
    assign t[0] = ^(x & 8'h47);
    assign t[1] = ^(x & 8'h80);
    assign t[2] = ^(x & 8'h08);
    assign t[3] = ^(x & 8'hD4);
    assign t[4] = ^(x & 8'h1A);
    assign t[5] = ^(x & 8'h56);
    assign t[6] = ^(x & 8'h7E);
    assign t[7] = ^(x & 8'hE8);

    wire [3:0] ah = t[7:4];
    wire [3:0] al = t[3:0];

    // ---- inverse in GF((2^4)^2) ---------------------------------------
    wire [3:0] ah2   = gf4_mul(ah, ah);
    wire [3:0] norm  = gf4_mul(ah2, 4'hd) ^ gf4_mul(ah, al) ^ gf4_mul(al, al);
    wire [3:0] scale = gf4_inv(norm);

    wire [7:0] w = {gf4_mul(ah, scale), gf4_mul(ah ^ al, scale)};

    // ---- change of basis back -----------------------------------------
    wire [7:0] u;
    assign u[0] = ^(w & 8'h1F);
    assign u[1] = ^(w & 8'h2A);
    assign u[2] = ^(w & 8'hD6);
    assign u[3] = ^(w & 8'h04);
    assign u[4] = ^(w & 8'h3E);
    assign u[5] = ^(w & 8'h64);
    assign u[6] = ^(w & 8'hE2);
    assign u[7] = ^(w & 8'h02);

    // ---- affine tail: rotate, sum, add the sealed constant -------------
    assign y = u
             ^ {u[6:0], u[7]}
             ^ {u[5:0], u[7:6]}
             ^ {u[4:0], u[7:5]}
             ^ {u[3:0], u[7:4]}
             ^ 8'hE7;

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
            gf4_inv[0] = a[0] ^ a[1] ^ a[2] ^ a[0] & a[2] ^ a[1] & a[2] ^ a[0] & a[1] & a[2] ^ a[3] ^ a[1] & a[2] & a[3];
            gf4_inv[1] = a[0] & a[1] ^ a[0] & a[2] ^ a[1] & a[2] ^ a[3] ^ a[1] & a[3] ^ a[0] & a[1] & a[3];
            gf4_inv[2] = a[0] & a[1] ^ a[2] ^ a[0] & a[2] ^ a[3] ^ a[0] & a[3] ^ a[0] & a[2] & a[3];
            gf4_inv[3] = a[1] ^ a[2] ^ a[3] ^ a[0] & a[3] ^ a[1] & a[3] ^ a[2] & a[3] ^ a[1] & a[2] & a[3];
        end
    endfunction

endmodule

`default_nettype wire
