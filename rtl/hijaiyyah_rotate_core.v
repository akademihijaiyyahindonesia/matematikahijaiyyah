// hijaiyyah_rotate_core.v — the same round, with the multiplexer removed.
//
// hijaiyyah_ramal_core.v picks a slice out of a 1600-bit register with a
// variable part-select, and measuring it showed the cost was almost all in
// that multiplexer rather than in the S-boxes: SLICE=4 came out *more*
// expensive than SLICE=8 (9,517 against 8,673 LUT4), because halving the
// width doubles the slice count and therefore the mux. Nothing fit a Tang
// Nano 9K's 8,640.
//
// THE FIX IS TO STOP ADDRESSING THE STATE. Rotate it instead: the bottom
// SLICE_BITS always feed the substitution, and the result is shifted in at
// the top. After SLICES clocks every byte has passed through the one fixed
// position and the state is back in its original orientation -- a full
// 1600-bit rotation. There is no address, so there is no mux; a shift by a
// constant is wiring.
//
//     state <= { substituted_bottom, state[1599:SLICE_BITS] }
//
// The round constant lands on the last of those clocks, when the state is
// already back in position, so it is XORed into the final value rather than
// into a rotated one.
//
// This is bit-identical to the sliced core and to cube.py, at every width and
// in the same clock count. What changes is only how bytes are presented to
// the substitution, and the S-box does not care where a byte came from -- the
// same position-independence the sliced core relies on.
//
// MEASURED, flattened, yosys abc -lut 4. The mux was the whole problem:
//
//     SLICE_BYTES   sliced    rotated   saving   clocks   fits 8,640?
//               4    9,517      4,603    -52%     1,486   yes
//               8    8,673      4,927    -43%       786   yes
//              25   12,074      6,331    -48%       310   yes
//              50       --      9,438       --      198   no
//
// And the curve is now monotonic in the right direction -- narrower is
// smaller, 4,603 < 4,927 < 6,331 -- which is exactly what should happen once
// the addressing is gone. Under the sliced design it was not, and that
// inversion was the evidence that pointed here.
//
// FULL SYSTEM, impulser and core together at SLICE_BYTES=25, on a Tang Nano
// 9K (GW1NR-9, 8,640 LUT4 / 6,693 FF):
//
//     6,229 LUT4   72%       2,411 LUT4 left for the UART and the HCPU
//     1,623 FF     24%
//     310 clocks per permutation
//
// Generic 4-LUT mapping, not a vendor fitting report: synth_gowin does not
// complete here and nextpnr is not installed, so this is a strong indication
// that it fits and not a placed-and-routed proof. Fmax has no value until the
// board arrives.

`default_nettype none

module hijaiyyah_rotate_core #(
    parameter integer SLICE_BYTES = 8      // 200 must divide by this
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          load,
    input  wire [1599:0] in_state,
    input  wire          lin_pulse,
    input  wire          sub_pulse,
    input  wire [7:0]    round_index,
    output wire          stall,
    output wire [1599:0] out_state
);

    localparam integer SLICE_BITS = SLICE_BYTES * 8;
    localparam integer SLICES     = 1600 / SLICE_BITS;
    localparam integer COUNT_W    = $clog2(SLICES);

    reg [1599:0]      state;
    reg [COUNT_W-1:0] step;
    reg               substituting;

    assign out_state = state;
    assign stall     = substituting | (lin_pulse & sub_pulse);

    // ---- the linear layer, over the whole state ------------------------
    wire [1599:0] linear_out;
    hijaiyyah_linear u_linear (.in_state(state), .out_state(linear_out));

    // ---- one fixed substitution position, no address -------------------
    wire [SLICE_BITS-1:0] head = state[SLICE_BITS-1:0];
    wire [SLICE_BITS-1:0] head_sub;

    genvar b;
    generate
        for (b = 0; b < SLICE_BYTES; b = b + 1) begin : sub_byte
            hijaiyyah_sbox u_sbox (
                .x (head    [b*8 +: 8]),
                .y (head_sub[b*8 +: 8])
            );
        end
    endgenerate

    wire [1599:0] rotated = {head_sub, state[1599:SLICE_BITS]};

    // ---- the round constant --------------------------------------------
    wire [63:0] round_constant;
    hijaiyyah_round_constants u_rc (
        .round_index    (round_index),
        .round_constant (round_constant)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state        <= {1600{1'b0}};
            step         <= {COUNT_W{1'b0}};
            substituting <= 1'b0;
        end else if (load) begin
            state        <= in_state;
            step         <= {COUNT_W{1'b0}};
            substituting <= 1'b0;
        end else if (substituting) begin
            if (step == SLICES - 1) begin
                // Last rotation: the state is back in position, so the
                // constant goes onto the final value.
                state        <= rotated ^ {{1536{1'b0}}, round_constant};
                substituting <= 1'b0;
                step         <= {COUNT_W{1'b0}};
            end else begin
                state <= rotated;
                step  <= step + 1'b1;
            end
        end else if (lin_pulse) begin
            state <= linear_out;
            if (sub_pulse) begin
                substituting <= 1'b1;
                step         <= {COUNT_W{1'b0}};
            end
        end
    end

endmodule

`default_nettype wire
