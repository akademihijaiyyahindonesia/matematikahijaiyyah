// ============================================================================
// HCPU Codex ALU — hcpu_codex_alu.v
// 18-wide parallel vector ALU for hybit codex operations
// (c) 2026 Maulana Amratulloh — HM-28-v1.2-HC18D
// ============================================================================
//
// Operations (all single-cycle, combinational):
//   HCADD: H[dst] ← H[s1] + H[s2]   (18 × 8-bit parallel adds + lane overflow)
//   HNRM2: GPR[dst] ← ‖H[s1]‖²₁₄   (sum of squares, 14 components)
//   HDIST: GPR[dst] ← ‖H[s1]−H[s2]‖²₁₄  (sq. Euclidean distance)
//   CGET: GPR[dst] ← H[s1][index]      (one codex component)
//   CSET: H[dst][index] ← GPR[s1]      (one codex component, written back)
//   CMOD4: GPR[dst] ← Θ̂(H[s1]) mod 4   (the Mod-4 gate's key)
//   HDOT: GPR[dst] ← ⟨H[s1], H[s2]⟩₁₄  (20-bit unsigned inner product, A2)
//
// Unified 14-Lane 8x8 Multiplier & CSA 20-Bit Accumulator Architecture (A2):
//   HNRM2, HDIST, and HDOT share a SINGLE 14-lane 8x8 unsigned multiplier array
//   and a SINGLE 14-input 20-bit Carry-Save Adder ($macc) tree:
//     - ALU_HNRM2: mul_a[i] = s1[i],       mul_b[i] = s1[i]
//     - ALU_HDIST: mul_a[i] = |s1[i]-s2[i]|, mul_b[i] = |s1[i]-s2[i]|
//     - ALU_HDOT:  mul_a[i] = s1[i],       mul_b[i] = s2[i]

`include "hcpu_pkg.vh"

module hcpu_codex_alu (
    // Inputs
    input  wire [2:0]              op,         // 0=HCADD 1=HNRM2 2=HDIST 3=CGET
                                               // 4=CSET 5=CMOD4 6=HDOT
    input  wire [11:0]             index,      // CGET/CSET: component 0–17
    input  wire [`HREG_W-1:0]     src1,       // H-Reg source 1 (144-bit)
    input  wire [`HREG_W-1:0]     src2,       // H-Reg source 2 (144-bit), CSET: H[dst]
    input  wire [`XLEN-1:0]       src_scl,    // Scalar source, CSET: GPR[s1]
    // Outputs
    output reg  [`HREG_W-1:0]     result_vec, // Vector result (for HCADD/CSET)
    output reg  [`XLEN-1:0]       result_scl, // Scalar result (for HNRM2/HDIST/HDOT)
    output wire                   add_ovf,    // 1 if any of 18 8-bit lanes overflows (>255) on HCADD
    output wire                   done        // Always 1 (single-cycle)
);

    localparam ALU_HCADD = 3'd0;
    localparam ALU_HNRM2 = 3'd1;
    localparam ALU_HDIST = 3'd2;
    localparam ALU_CGET = 3'd3;
    localparam ALU_CSET = 3'd4;
    localparam ALU_CMOD4 = 3'd5;
    localparam ALU_HDOT  = 3'd6;

    assign done = 1'b1;  // All ops are single-cycle

    // ── Component extraction wires ──────────────────────────────
    wire [7:0] s1 [0:17];
    wire [7:0] s2_c [0:17];

    genvar gi;
    generate
        for (gi = 0; gi < 18; gi = gi + 1) begin : extract
            assign s1[gi]   = src1[8*gi +: 8];
            assign s2_c[gi] = src2[8*gi +: 8];
        end
    endgenerate

    // ── HCADD: component-wise addition (18 parallel adds) ───────
    wire [7:0] add_result [0:17];
    wire [17:0] add_carry;
    generate
        for (gi = 0; gi < 18; gi = gi + 1) begin : cadd
            wire [8:0] sum9 = {1'b0, s1[gi]} + {1'b0, s2_c[gi]};
            assign add_result[gi] = sum9[7:0];
            assign add_carry[gi]  = sum9[8];
        end
    endgenerate

    // Alternative A1: Hardware Sticky Prefix Guard lane overflow detection
    assign add_ovf = |add_carry;

    // Pack addition result back into 144-bit vector
    wire [`HREG_W-1:0] packed_add;
    assign packed_add = {add_result[17], add_result[16], add_result[15],
                         add_result[14], add_result[13], add_result[12],
                         add_result[11], add_result[10], add_result[ 9],
                         add_result[ 8], add_result[ 7], add_result[ 6],
                         add_result[ 5], add_result[ 4], add_result[ 3],
                         add_result[ 2], add_result[ 1], add_result[ 0]};

    // ── Unified 14-Lane 8x8 Unsigned Multiplier & CSA 20-Bit Adder Tree ──
    wire [7:0]  abs_diff  [0:13];
    wire [7:0]  mul_a     [0:13];
    wire [7:0]  mul_b     [0:13];
    wire [15:0] lane_prod [0:13];

    generate
        for (gi = 0; gi < 14; gi = gi + 1) begin : unified_mac14
            assign abs_diff[gi]  = (s1[gi] >= s2_c[gi]) ? (s1[gi] - s2_c[gi])
                                                        : (s2_c[gi] - s1[gi]);
            assign mul_a[gi]     = (op == ALU_HDIST) ? abs_diff[gi] : s1[gi];
            assign mul_b[gi]     = (op == ALU_HDIST) ? abs_diff[gi] :
                                   (op == ALU_HDOT)  ? s2_c[gi]     : s1[gi];
            assign lane_prod[gi] = mul_a[gi] * mul_b[gi];
        end
    endgenerate

    // Single expression enables Yosys alumacc to build a Carry-Save Adder (CSA) tree
    wire [19:0] mac14_sum;
    assign mac14_sum = {4'd0, lane_prod[ 0]} + {4'd0, lane_prod[ 1]}
                     + {4'd0, lane_prod[ 2]} + {4'd0, lane_prod[ 3]}
                     + {4'd0, lane_prod[ 4]} + {4'd0, lane_prod[ 5]}
                     + {4'd0, lane_prod[ 6]} + {4'd0, lane_prod[ 7]}
                     + {4'd0, lane_prod[ 8]} + {4'd0, lane_prod[ 9]}
                     + {4'd0, lane_prod[10]} + {4'd0, lane_prod[11]}
                     + {4'd0, lane_prod[12]} + {4'd0, lane_prod[13]};

    // ── CSET: one component replaced, seventeen kept ────────────
    wire [7:0] set_shift = {index[4:0], 3'b000};          // component × 8 bits
    wire [`HREG_W-1:0] set_mask  = {{(`HREG_W-8){1'b0}}, 8'hFF}         << set_shift;
    wire [`HREG_W-1:0] set_field = {{(`HREG_W-8){1'b0}}, src_scl[7:0]}  << set_shift;
    wire [`HREG_W-1:0] packed_set = (src2 & ~set_mask) | set_field;

    // ── Output mux ──────────────────────────────────────────────
    always @(*) begin
        result_vec = {`HREG_W{1'b0}};
        result_scl = {`XLEN{1'b0}};
        case (op)
            ALU_HCADD: result_vec = packed_add;
            ALU_HNRM2,
            ALU_HDIST,
            ALU_HDOT:  result_scl = {12'd0, mac14_sum};
            ALU_CSET:  result_vec = (index <= 12'd17) ? packed_set : src2;
            ALU_CMOD4: result_scl = {30'd0, s1[0][1:0]};
            ALU_CGET:  result_scl = (index <= 12'd17)
                                  ? {24'd0, s1[index[4:0]]} : {`XLEN{1'b0}};
            default: begin
                result_vec = {`HREG_W{1'b0}};
                result_scl = {`XLEN{1'b0}};
            end
        endcase
    end

endmodule
