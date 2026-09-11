// ============================================================================
// HCPU Codex ALU — hcpu_codex_alu.v
// 18-wide parallel vector ALU for hybit codex operations
// (c) 2026 Maulana Amratulloh — HM-28-v1.2-HC18D
// ============================================================================
//
// Operations (all single-cycle, combinational):
//   HCADD: H[dst] ← H[s1] + H[s2]   (18 × 8-bit parallel adds)
//   HNRM2: GPR[dst] ← ‖H[s1]‖²₁₄   (sum of squares, 14 components)
//   HDIST: GPR[dst] ← ‖H[s1]−H[s2]‖²₁₄  (sq. Euclidean distance)
//   CGET: GPR[dst] ← H[s1][index]      (one codex component)
//   CSET: H[dst][index] ← GPR[s1]      (one codex component, written back)
//
// CSET is the write half of CGET, and it reads the register it writes: the
// other seventeen components have to survive, so the codex being modified
// arrives on src2 (decode points the second H-Reg read port at DST) and the
// scalar being written arrives on src_scl.
//
// Values in the master table are small (max Θ̂=8), so:
//   - Each square fits in 7 bits (max 64)
//   - Sum of 14 squares fits in 11 bits (max 896)
//   - For accumulated strings (HCADD), 8-bit per component
//     supports up to ~30 characters safely.
//

`include "hcpu_pkg.vh"

module hcpu_codex_alu (
    // Inputs
    input  wire [2:0]              op,         // 0=HCADD 1=HNRM2 2=HDIST 3=CGET 4=CSET
    input  wire [11:0]             index,      // CGET/CSET: component 0–17
    input  wire [`HREG_W-1:0]     src1,       // H-Reg source 1 (144-bit)
    input  wire [`HREG_W-1:0]     src2,       // H-Reg source 2 (144-bit), CSET: H[dst]
    input  wire [`XLEN-1:0]       src_scl,    // Scalar source, CSET: GPR[s1]
    // Outputs
    output reg  [`HREG_W-1:0]     result_vec, // Vector result (for HCADD/CSET)
    output reg  [`XLEN-1:0]       result_scl, // Scalar result (for HNRM2/HDIST)
    output wire                   done        // Always 1 (single-cycle)
);

    localparam ALU_HCADD = 3'd0;
    localparam ALU_HNRM2 = 3'd1;
    localparam ALU_HDIST = 3'd2;
    localparam ALU_CGET = 3'd3;
    localparam ALU_CSET = 3'd4;

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
    generate
        for (gi = 0; gi < 18; gi = gi + 1) begin : cadd
            assign add_result[gi] = s1[gi] + s2_c[gi];
        end
    endgenerate

    // Pack addition result back into 144-bit vector
    wire [`HREG_W-1:0] packed_add;
    assign packed_add = {add_result[17], add_result[16], add_result[15],
                         add_result[14], add_result[13], add_result[12],
                         add_result[11], add_result[10], add_result[ 9],
                         add_result[ 8], add_result[ 7], add_result[ 6],
                         add_result[ 5], add_result[ 4], add_result[ 3],
                         add_result[ 2], add_result[ 1], add_result[ 0]};

    // ── HNRM2: ‖v‖² = Σ v[i]² for i=0..13 (codex14) ───────────
    // Each v[i] ≤ 8, so v[i]² ≤ 64 (7 bits). Sum of 14 ≤ 896 (10 bits).
    wire [15:0] sq1 [0:13];
    generate
        for (gi = 0; gi < 14; gi = gi + 1) begin : sq_norm
            assign sq1[gi] = s1[gi] * s1[gi];
        end
    endgenerate

    // Adder tree for sum of 14 squares
    wire [15:0] norm2_sum;
    assign norm2_sum = sq1[ 0] + sq1[ 1] + sq1[ 2] + sq1[ 3]
                     + sq1[ 4] + sq1[ 5] + sq1[ 6] + sq1[ 7]
                     + sq1[ 8] + sq1[ 9] + sq1[10] + sq1[11]
                     + sq1[12] + sq1[13];

    // ── HDIST: ‖s1−s2‖² = Σ (s1[i]−s2[i])² for i=0..13 ────────
    wire signed [8:0] diff [0:13];
    wire [15:0] sq_diff [0:13];
    generate
        for (gi = 0; gi < 14; gi = gi + 1) begin : sq_dist
            assign diff[gi]    = $signed({1'b0, s1[gi]}) - $signed({1'b0, s2_c[gi]});
            assign sq_diff[gi] = diff[gi] * diff[gi];
        end
    endgenerate

    wire [15:0] dist2_sum;
    assign dist2_sum = sq_diff[ 0] + sq_diff[ 1] + sq_diff[ 2] + sq_diff[ 3]
                     + sq_diff[ 4] + sq_diff[ 5] + sq_diff[ 6] + sq_diff[ 7]
                     + sq_diff[ 8] + sq_diff[ 9] + sq_diff[10] + sq_diff[11]
                     + sq_diff[12] + sq_diff[13];

    // ── CSET: one component replaced, seventeen kept ────────────
    // A component is eight bits wide (HREG_W = 18 × 8), so only the low byte
    // of the scalar can land in one. The interpreter masks with 0xFF for the
    // same reason -- a width that differs between the two machines is exactly
    // how HLOAD's 0-based/1-based split stayed invisible.
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
            ALU_HNRM2: result_scl = {16'd0, norm2_sum};
            ALU_HDIST: result_scl = {16'd0, dist2_sum};
            // CSET writes one component back into the codex it came from. An
            // index past 17 names no component, so the register keeps the
            // value it had -- the same convention CGET uses when it returns
            // zero for an index that names nothing.
            ALU_CSET: result_vec = (index <= 12'd17) ? packed_set : src2;
            // CGET reads one component out of the codex. An index past
            // 17 has no component to name, so it yields zero rather than
            // whatever the wider bus happens to carry.
            // The whole 12-bit immediate is compared, not its low five
            // bits. Truncating first made IMM=99 arrive as 3 and return Ba's
            // Nd, where the Python machine checked the full immediate and
            // returned 0 — the two disagreed for every out-of-range index
            // whose low five bits named a non-zero component.
            ALU_CGET: result_scl = (index <= 12'd17)
                                  ? {24'd0, s1[index[4:0]]} : {`XLEN{1'b0}};
            default: begin
                result_vec = {`HREG_W{1'b0}};
                result_scl = {`XLEN{1'b0}};
            end
        endcase
    end

endmodule
