// ============================================================================
// HCPU Codex ALU — hcpu_codex_alu.v
// 18-wide parallel vector ALU for hybit codex operations
// (c) 2026 Maulana Amratulloh — HM-28-v1.2-HC18D
// ============================================================================
//
// Operations:
//   HCADD: H[dst] ← H[s1] + H[s2]       (18 × 8-bit parallel adds + lane overflow)
//   HNRM2: GPR[dst] ← ‖H[s1]‖²₁₄       (sum of squares, 14 components)
//   HDIST: GPR[dst] ← ‖H[s1]−H[s2]‖²₁₄ (sq. Euclidean distance)
//   CGET:  GPR[dst] ← H[s1][index]      (one codex component)
//   CSET:  H[dst][index] ← GPR[s1]      (one codex component, written back)
//   CMOD4: GPR[dst] ← Θ̂(H[s1]) mod 4   (the Mod-4 gate's key)
//   HDOT:  GPR[dst] ← ⟨H[s1], H[s2]⟩₁₄  (20-bit unsigned inner product, A2)
//
// Three Target Hardware Profiles (Paket 8 — COSMICTERA):
//   - CODEX_PROFILE = 0 (COSMICTERA ASIC / Generic):
//       Shared 14-lane 8x8 MAC (8x2 Radix-4 partial-product reduction +
//       balanced binary adder tree) + single-subtractor abs_diff.
//       All operations (including HDOT) execute in 1 cycle (done = 1).
//   - CODEX_PROFILE = 1 (COSMICTERA FPGA DSP — Tang Nano 20K with MULT9X9):
//       Shared 14-lane 8x8 MAC (mul_a * mul_b behavioral -> 14x MULT9X9 hard
//       DSP blocks + CSA tree) + single-subtractor abs_diff.
//       All operations (including HDOT) execute in 1 cycle (done = 1).
//   - CODEX_PROFILE = 2 (COSMICTERA FPGA No-DSP — Tang Nano 20K -nodsp):
//       Dedicated 14-lane Nibble-Split Squarer ({sq4(H), sq4(L)} + ((H*L)<<5))
//       + single-subtractor abs_diff for single-cycle HNRM2 and HDIST, paired
//       with a resource-shared 14-cycle sequential lane shift-add multiplier
//       and 20-bit accumulator for HDOT (asserting done = 0 for 13 cycles and
//       done = 1 on cycle 14 to stall the HCPU pipeline without 14 parallel
//       8x8 multipliers).

`include "hcpu_pkg.vh"

module hcpu_codex_alu #(
    parameter USE_DSP       = 0,
    parameter CODEX_PROFILE = -1, // -1 = auto (USE_DSP ? 1 : 2), 0 = ASIC MAC, 1 = FPGA DSP, 2 = FPGA No-DSP
    parameter HDOT_ENABLE   = 1   // 1 = OP_HDOT enabled, 0 = OP_HDOT disabled on target profile
)(
    // Optional clock/reset/stall for multi-cycle iterative HDOT in CODEX_PROFILE=2.
    // Unconnected inputs in legacy combinational benches resolve safely via ===.
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   stall,
    // Inputs
    input  wire [2:0]             op,          // 0=HCADD 1=HNRM2 2=HDIST 3=CGET
                                               // 4=CSET  5=CMOD4 6=HDOT
    input  wire [11:0]            index,       // CGET/CSET: component 0–17
    input  wire [`HREG_W-1:0]     src1,        // H-Reg source 1 (144-bit)
    input  wire [`HREG_W-1:0]     src2,        // H-Reg source 2 (144-bit), CSET: H[dst]
    input  wire [`XLEN-1:0]       src_scl,     // Scalar source, CSET: GPR[s1]
    // Outputs
    output reg  [`HREG_W-1:0]     result_vec,  // Vector result (for HCADD/CSET)
    output reg  [`XLEN-1:0]       result_scl,  // Scalar result (for HNRM2/HDIST/HDOT)
    output wire                   add_ovf,     // 1 if any of 18 8-bit lanes overflows (>255) on HCADD
    output wire                   done         // 1 when result is ready (always 1 in Profile 0/1)
);

    localparam EFF_PROFILE = (CODEX_PROFILE == 0 || CODEX_PROFILE == 1 || CODEX_PROFILE == 2)
                           ? CODEX_PROFILE
                           : ((USE_DSP != 0) ? 1 : 2);

    localparam ALU_HCADD = 3'd0;
    localparam ALU_HNRM2 = 3'd1;
    localparam ALU_HDIST = 3'd2;
    localparam ALU_CGET  = 3'd3;
    localparam ALU_CSET  = 3'd4;
    localparam ALU_CMOD4 = 3'd5;
    localparam ALU_HDOT  = 3'd6;

    // ── 4-bit Nibble Square Lookup (4 inputs -> 1 LUT4 per output bit) ──
    function [7:0] sq4;
        input [3:0] n;
        case (n)
            4'd0:  sq4 = 8'd0;   4'd1:  sq4 = 8'd1;   4'd2:  sq4 = 8'd4;   4'd3:  sq4 = 8'd9;
            4'd4:  sq4 = 8'd16;  4'd5:  sq4 = 8'd25;  4'd6:  sq4 = 8'd36;  4'd7:  sq4 = 8'd49;
            4'd8:  sq4 = 8'd64;  4'd9:  sq4 = 8'd81;  4'd10: sq4 = 8'd100; 4'd11: sq4 = 8'd121;
            4'd12: sq4 = 8'd144; 4'd13: sq4 = 8'd169; 4'd14: sq4 = 8'd196; 4'd15: sq4 = 8'd225;
        endcase
    endfunction

    // ── Exact 8-bit Nibble-Split Squarer: (16H + L)^2 = {H^2, L^2} + ((H*L)<<5) ──
    function [15:0] sq8_nibble;
        input [7:0] x;
        reg [3:0] h, l;
        reg [7:0] hl;
        begin
            h = x[7:4];
            l = x[3:0];
            hl = ({4'd0, h & {4{l[0]}}}      )
               + ({3'd0, h & {4{l[1]}}, 1'b0})
               + ({2'd0, h & {4{l[2]}}, 2'b0})
               + ({1'd0, h & {4{l[3]}}, 3'b0});
            sq8_nibble = {sq4(h), sq4(l)} + {3'b000, hl, 5'b00000};
        end
    endfunction

    // ── Component extraction wires ──────────────────────────────
    wire [7:0] s1   [0:17];
    wire [7:0] s2_c [0:17];

    genvar gi;
    generate
        for (gi = 0; gi < 18; gi = gi + 1) begin : extract
            assign s1[gi]   = src1[8*gi +: 8];
            assign s2_c[gi] = src2[8*gi +: 8];
        end
    endgenerate

    // ── HCADD: component-wise addition (18 parallel adds) ───────
    wire [7:0]  add_result [0:17];
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

    // ── Single-Subtractor Absolute Difference |s1[gi] - s2_c[gi]| (Paket 8) ──
    wire [7:0] abs_diff [0:13];
    generate
        for (gi = 0; gi < 14; gi = gi + 1) begin : abs_diff_gen
            wire [8:0] df       = {1'b0, s1[gi]} - {1'b0, s2_c[gi]};
            assign abs_diff[gi] = df[8] ? (8'd0 - df[7:0]) : df[7:0];
        end
    endgenerate

    // ── Target Profile Datapath Selection (Profiles 0, 1, 2) ────
    wire [19:0] scalar_sum_out;
    wire [19:0] hdot_sum_out;

    generate
        if (EFF_PROFILE == 1) begin : g_profile_fpga_dsp
            // ── PROFILE B (CODEX_PROFILE = 1): Tang Nano 20K Hard-DSP (14x MULT9X9) ──
            wire [7:0]  mul_a     [0:13];
            wire [7:0]  mul_b     [0:13];
            wire [15:0] lane_prod [0:13];
            for (gi = 0; gi < 14; gi = gi + 1) begin : mac14_dsp
                assign mul_a[gi]     = (op == ALU_HDIST) ? abs_diff[gi] : s1[gi];
                assign mul_b[gi]     = (op == ALU_HDIST) ? abs_diff[gi] :
                                       (op == ALU_HDOT)  ? s2_c[gi]     : s1[gi];
                assign lane_prod[gi] = mul_a[gi] * mul_b[gi];
            end
            wire [19:0] mac14_sum =
                  {4'd0, lane_prod[ 0]} + {4'd0, lane_prod[ 1]}
                + {4'd0, lane_prod[ 2]} + {4'd0, lane_prod[ 3]}
                + {4'd0, lane_prod[ 4]} + {4'd0, lane_prod[ 5]}
                + {4'd0, lane_prod[ 6]} + {4'd0, lane_prod[ 7]}
                + {4'd0, lane_prod[ 8]} + {4'd0, lane_prod[ 9]}
                + {4'd0, lane_prod[10]} + {4'd0, lane_prod[11]}
                + {4'd0, lane_prod[12]} + {4'd0, lane_prod[13]};
            assign scalar_sum_out = mac14_sum;
            assign hdot_sum_out   = mac14_sum;
            assign done           = 1'b1;

        end else if (EFF_PROFILE == 0) begin : g_profile_asic
            // ── PROFILE A (CODEX_PROFILE = 0): ASIC / Generic Unified 14-Lane MAC ──
            wire [7:0]  mul_a     [0:13];
            wire [7:0]  mul_b     [0:13];
            wire [15:0] lane_prod [0:13];
            for (gi = 0; gi < 14; gi = gi + 1) begin : mac14_asic
                assign mul_a[gi] = (op == ALU_HDIST) ? abs_diff[gi] : s1[gi];
                assign mul_b[gi] = (op == ALU_HDIST) ? abs_diff[gi] :
                                   (op == ALU_HDOT)  ? s2_c[gi]     : s1[gi];
                wire [9:0] p0 = {2'b00, mul_a[gi] & {8{mul_b[gi][0]}}}
                              + {1'b0,  mul_a[gi] & {8{mul_b[gi][1]}}, 1'b0};
                wire [9:0] p1 = {2'b00, mul_a[gi] & {8{mul_b[gi][2]}}}
                              + {1'b0,  mul_a[gi] & {8{mul_b[gi][3]}}, 1'b0};
                wire [9:0] p2 = {2'b00, mul_a[gi] & {8{mul_b[gi][4]}}}
                              + {1'b0,  mul_a[gi] & {8{mul_b[gi][5]}}, 1'b0};
                wire [9:0] p3 = {2'b00, mul_a[gi] & {8{mul_b[gi][6]}}}
                              + {1'b0,  mul_a[gi] & {8{mul_b[gi][7]}}, 1'b0};
                wire [11:0] q0 = {2'b00, p0} + {p1, 2'b00};
                wire [11:0] q1 = {2'b00, p2} + {p3, 2'b00};
                assign lane_prod[gi] = {4'b0000, q0} + {q1, 4'b0000};
            end
            wire [16:0] t0 = {1'b0, lane_prod[ 0]} + {1'b0, lane_prod[ 1]};
            wire [16:0] t1 = {1'b0, lane_prod[ 2]} + {1'b0, lane_prod[ 3]};
            wire [16:0] t2 = {1'b0, lane_prod[ 4]} + {1'b0, lane_prod[ 5]};
            wire [16:0] t3 = {1'b0, lane_prod[ 6]} + {1'b0, lane_prod[ 7]};
            wire [16:0] t4 = {1'b0, lane_prod[ 8]} + {1'b0, lane_prod[ 9]};
            wire [16:0] t5 = {1'b0, lane_prod[10]} + {1'b0, lane_prod[11]};
            wire [16:0] t6 = {1'b0, lane_prod[12]} + {1'b0, lane_prod[13]};
            wire [17:0] u0 = {1'b0, t0} + {1'b0, t1};
            wire [17:0] u1 = {1'b0, t2} + {1'b0, t3};
            wire [17:0] u2 = {1'b0, t4} + {1'b0, t5};
            wire [18:0] v0 = {1'b0, u0} + {1'b0, u1};
            wire [18:0] v1 = {1'b0, u2} + {2'b00, t6};
            wire [19:0] mac14_sum = {1'b0, v0} + {1'b0, v1};
            assign scalar_sum_out = mac14_sum;
            assign hdot_sum_out   = mac14_sum;
            assign done           = 1'b1;

        end else begin : g_profile_fpga_nodsp
            // ── PROFILE C (CODEX_PROFILE = 2): Tang Nano 20K No-DSP ────────
            // 1. Dedicated 14-lane Nibble-Split Squarer for single-cycle HNRM2 & HDIST
            wire [7:0]  sq_in   [0:13];
            wire [15:0] lane_sq [0:13];
            for (gi = 0; gi < 14; gi = gi + 1) begin : sq14
                assign sq_in[gi]   = (op == ALU_HDIST) ? abs_diff[gi] : s1[gi];
                assign lane_sq[gi] = sq8_nibble(sq_in[gi]);
            end
            wire [19:0] sq14_sum =
                  {4'd0, lane_sq[ 0]} + {4'd0, lane_sq[ 1]}
                + {4'd0, lane_sq[ 2]} + {4'd0, lane_sq[ 3]}
                + {4'd0, lane_sq[ 4]} + {4'd0, lane_sq[ 5]}
                + {4'd0, lane_sq[ 6]} + {4'd0, lane_sq[ 7]}
                + {4'd0, lane_sq[ 8]} + {4'd0, lane_sq[ 9]}
                + {4'd0, lane_sq[10]} + {4'd0, lane_sq[11]}
                + {4'd0, lane_sq[12]} + {4'd0, lane_sq[13]};

            // 2. Iterative 14-cycle sequential lane shift-add multiplier for OP_HDOT
            wire rst_n_int = (rst_n === 1'b0) ? 1'b0 : 1'b1;
            wire stall_int = (stall === 1'b1) ? 1'b1 : 1'b0;
            reg  [3:0]  hdot_lane;
            reg  [19:0] hdot_acc;
            wire        is_hdot = (HDOT_ENABLE != 0) && (op == ALU_HDOT);

            wire [7:0]  cur_a    = (hdot_lane <= 4'd13) ? s1[hdot_lane]   : 8'd0;
            wire [7:0]  cur_b    = (hdot_lane <= 4'd13) ? s2_c[hdot_lane] : 8'd0;
            wire [15:0] cur_prod = ({8'd0, cur_a & {8{cur_b[0]}}}       )
                                 + ({7'd0, cur_a & {8{cur_b[1]}}, 1'd0})
                                 + ({6'd0, cur_a & {8{cur_b[2]}}, 2'd0})
                                 + ({5'd0, cur_a & {8{cur_b[3]}}, 3'd0})
                                 + ({4'd0, cur_a & {8{cur_b[4]}}, 4'd0})
                                 + ({3'd0, cur_a & {8{cur_b[5]}}, 5'd0})
                                 + ({2'd0, cur_a & {8{cur_b[6]}}, 6'd0})
                                 + ({1'd0, cur_a & {8{cur_b[7]}}, 7'd0});
            wire [19:0] hdot_next = ((hdot_lane == 4'd0) ? 20'd0 : hdot_acc) + {4'd0, cur_prod};

            always @(posedge clk or negedge rst_n_int) begin
                if (!rst_n_int) begin
                    hdot_lane <= 4'd0;
                    hdot_acc  <= 20'd0;
                end else if (!stall_int) begin
                    if (is_hdot) begin
                        if (hdot_lane == 4'd13) begin
                            hdot_lane <= 4'd0;
                            hdot_acc  <= 20'd0;
                        end else begin
                            hdot_lane <= hdot_lane + 4'd1;
                            hdot_acc  <= hdot_next;
                        end
                    end else begin
                        hdot_lane <= 4'd0;
                        hdot_acc  <= 20'd0;
                    end
                end
            end

            assign scalar_sum_out = sq14_sum;
            assign hdot_sum_out   = (HDOT_ENABLE != 0) ? hdot_next : 20'd0;
            assign done           = is_hdot ? (hdot_lane == 4'd13) : 1'b1;
        end
    endgenerate

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
            ALU_HDIST: result_scl = {12'd0, scalar_sum_out};
            ALU_HDOT:  result_scl = (HDOT_ENABLE != 0) ? {12'd0, hdot_sum_out} : {`XLEN{1'b0}};
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
