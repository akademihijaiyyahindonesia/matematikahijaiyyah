// ============================================================================
// HCPU HISAB Serializer — hcpu_hisab.v
// Hardware HISAB nibble-packer + CRC32 engine
// Implements §4.6.1 (LETTER frame) nibble-packing and CRC32 digest
// (c) 2026 Maulana Amratulloh — Hybit Technology
// ============================================================================
//
// HISAB = Hijaiyyah Inter-System Standard for Auditable Bridging
//
// This module provides two operations:
//
//   HPACK (op=0):  H-Reg (144-bit, 18×8-bit) → nibble-packed output
//                  Output: 3 GPR words (pack[31:0], pack[63:32], pack[79:72]+guard)
//                  9 bytes nibble-packed + 1 byte guard status = 10 bytes → 3 words
//
//   HCRC  (op=1):  Compute CRC32 over HISAB frame header+payload+guard
//                  Input: GPR[S1] = word0, GPR[S2] = word1 (of packed data)
//                         IMM[7:0] = word2_byte (last pack byte + guard)
//                  Output: 32-bit CRC32 digest
//
// All operations are single-cycle combinational.
//

`include "hcpu_pkg.vh"

module hcpu_hisab (
    input  wire [1:0]           op,          // 0 = HPACK, 1 = HCRC
    input  wire [`HREG_W-1:0]   vec_in,      // 144-bit H-Reg for HPACK
    input  wire [`XLEN-1:0]     gpr_s1,      // GPR input for HCRC (word0)
    input  wire [`XLEN-1:0]     gpr_s2,      // GPR input for HCRC (word1)
    input  wire [7:0]           extra_byte,  // Extra byte for HCRC (guard+tail)

    output wire [`XLEN-1:0]     pack_word0,  // Nibble-packed bytes 0-3
    output wire [`XLEN-1:0]     pack_word1,  // Nibble-packed bytes 4-7
    output wire [`XLEN-1:0]     pack_word2,  // Byte 8 + guard_status + 00 + 00
    output wire [7:0]           guard_status,// Guard bitmask (G1-G4, T1-T2)
    output wire [`XLEN-1:0]     crc_out,     // CRC32 result (for HCRC)
    output wire                 done
);

    assign done = 1'b1;  // Single-cycle

    // ── Extract 18 components from H-Reg ────────────────────────
    wire [7:0] c [0:17];
    genvar gi;
    generate
        for (gi = 0; gi < 18; gi = gi + 1) begin : comp_extract
            assign c[gi] = vec_in[8*gi +: 8];
        end
    endgenerate

    // ── Canonical Guard evaluation via hcpu_guard (R1, GAP-02) ──
    // Single-cycle combinational latency (PIPELINE_GUARD = 0).
    // All full-width sums (10-bit sum_n, 11-bit sum_k, 11-bit sum_q),
    // 11-bit U, signed 12-bit rho, T1, T2, and coupled H* come directly
    // from hcpu_guard.v with zero duplicate formulas.
    wire guard_pass;
    wire g1, g2, g3, g4, t1, t2;
    wire [`XLEN-1:0] unused_guard_u, unused_guard_rho;

    hcpu_guard #(.PIPELINE_GUARD(0)) u_guard (
        .clk        (1'b0),
        .rst_n      (1'b1),
        .vec        (vec_in),
        .guard_pass (guard_pass),
        .g1_pass    (g1),
        .g2_pass    (g2),
        .g3_pass    (g3),
        .g4_pass    (g4),
        .t1_pass    (t1),
        .t2_pass    (t2),
        .u_value    (unused_guard_u),
        .rho_value  (unused_guard_rho)
    );
    wire [5:0] raw_guards = {t2, t1, g4, g3, g2, g1};
    assign guard_status = (&raw_guards && !guard_pass) ? 8'h00 : {2'b00, t2, t1, g4, g3, g2, g1};

    // ── Nibble-packing (§4.6.1) ─────────────────────────────────
    // 18 components → 9 nibble-packed bytes
    // Pair layout: (Θ̂|Na), (Nb|Nd), (Kp|Kx), (Ks|Ka), (Kc|Qp),
    //              (Qx|Qs), (Qa|Qc), (A_N|A_K), (A_Q|H*)
    wire [7:0] nb [0:8];
    assign nb[0] = {c[0][3:0],  c[1][3:0]};   // Θ̂  | Na
    assign nb[1] = {c[2][3:0],  c[3][3:0]};   // Nb | Nd
    assign nb[2] = {c[4][3:0],  c[5][3:0]};   // Kp | Kx
    assign nb[3] = {c[6][3:0],  c[7][3:0]};   // Ks | Ka
    assign nb[4] = {c[8][3:0],  c[9][3:0]};   // Kc | Qp
    assign nb[5] = {c[10][3:0], c[11][3:0]};   // Qx | Qs
    assign nb[6] = {c[12][3:0], c[13][3:0]};   // Qa | Qc
    assign nb[7] = {c[14][3:0], c[15][3:0]};   // A_N| A_K
    assign nb[8] = {c[16][3:0], c[17][3:0]};   // A_Q| H*

    // Pack into 3 words
    assign pack_word0 = {nb[3], nb[2], nb[1], nb[0]};   // bytes 0-3
    assign pack_word1 = {nb[7], nb[6], nb[5], nb[4]};   // bytes 4-7
    assign pack_word2 = {16'h0000, guard_status, nb[8]}; // byte 8 + guard

    // ── CRC32 computation (HISAB §4.10) ─────────────────────────
    // CRC32 over the full HISAB LETTER frame:
    //   Header (4B): 0x48, 0x42, 0x01, 0x01
    //   Payload (9B): nibble-packed
    //   Guard (1B): guard_status
    //   = 14 bytes total → CRC32
    //
    // For hardware efficiency, we use a lookup-table-free
    // bit-serial CRC32 (polynomial 0x04C11DB7, reflected).
    // This computes CRC32 over an arbitrary byte sequence.

    // CRC32 function: process one byte
    function [31:0] crc32_byte;
        input [31:0] crc_in;
        input [7:0]  data_byte;
        reg [31:0] crc;
        integer j;
        begin
            crc = crc_in ^ {24'h0, data_byte};
            for (j = 0; j < 8; j = j + 1) begin
                if (crc[0])
                    crc = (crc >> 1) ^ 32'hEDB88320;
                else
                    crc = crc >> 1;
            end
            crc32_byte = crc;
        end
    endfunction

    // Compute CRC32 over HISAB LETTER frame (14 bytes)
    wire [31:0] crc_0  = crc32_byte(32'hFFFFFFFF, 8'h48);       // Magic 'H'
    wire [31:0] crc_1  = crc32_byte(crc_0,        8'h42);       // Magic 'B'
    wire [31:0] crc_2  = crc32_byte(crc_1,        8'h01);       // Version
    wire [31:0] crc_3  = crc32_byte(crc_2,        8'h01);       // FrameType LETTER
    wire [31:0] crc_4  = crc32_byte(crc_3,        nb[0]);       // Payload B0
    wire [31:0] crc_5  = crc32_byte(crc_4,        nb[1]);       // Payload B1
    wire [31:0] crc_6  = crc32_byte(crc_5,        nb[2]);       // Payload B2
    wire [31:0] crc_7  = crc32_byte(crc_6,        nb[3]);       // Payload B3
    wire [31:0] crc_8  = crc32_byte(crc_7,        nb[4]);       // Payload B4
    wire [31:0] crc_9  = crc32_byte(crc_8,        nb[5]);       // Payload B5
    wire [31:0] crc_10 = crc32_byte(crc_9,        nb[6]);       // Payload B6
    wire [31:0] crc_11 = crc32_byte(crc_10,       nb[7]);       // Payload B7
    wire [31:0] crc_12 = crc32_byte(crc_11,       nb[8]);       // Payload B8
    wire [31:0] crc_13 = crc32_byte(crc_12,       guard_status);// Guard byte

    assign crc_out = ~crc_13;  // Final XOR

endmodule
