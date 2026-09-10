// hijaiyyah_ramal_core.v — the impulser's pulses, converted back into a
// computation.
//
// A pacing generator that drives nothing proves nothing. This is the datapath
// underneath it: a 1600-bit state, one linear layer, one 25-byte substitution
// slice, and the round constants. The impulser says when each fires; this
// says what happens when it does.
//
// THE SCALE THAT DECIDES THE SHAPE. The state is 25 lanes of 64 bits = 200
// BYTES, so a fully parallel substitution needs 200 S-boxes at 15,200 LUT4
// which is 73% of a Tang Nano 20K on substitution alone. What leaves room
// for the rest of the system is a 25-byte slice at
// ~1,900 LUT4, run eight times. So a substitution costs EIGHT clocks and a
// linear layer costs ONE, and `stall` is how the impulser learns that.
//
// That asymmetry is the whole reason the ramal schedule is worth having:
//
//     walk  [1,1,1]   3 linear + 3 sub  =  3 + 24 = 27 clocks
//     ramal [2,1]     3 linear + 2 sub  =  3 + 16 = 19 clocks
//
// ORDER, which is not symmetric. Within a round the linear layer fires first
// and the substitution follows, matching cube.py exactly:
//
//     s = linear_layer(s); s = substitute(s); s[0] ^= ROUND_CONSTANT[r]
//
// The round constant is applied on the clock that finishes the last slice.
// That is safe rather than lucky: slice 7 covers bytes 175..199, and the
// constant lands in lane 0 at bytes 0..7, so they never touch the same bits.
//
// Substitution is applied to the flat state rather than lane by lane, which
// is legitimate because the S-box is position-independent: substituting the
// 200-byte array and substituting each 64-bit lane give the same result, and
// a test asserts it rather than assuming it.
//
// MEASURED ACROSS SLICE WIDTHS, flattened, yosys abc -lut 4. Every width
// reproduces cube.py exactly; what changes is the trade:
//
//     SLICE_BYTES   LUT4     FF     clocks
//               4   9,517  1,607     1,486
//               8   8,673  1,606       786
//              25  12,074  1,604       310
//
// TWO FINDINGS, AND THE FIRST ONE CONTRADICTS THE OBVIOUS EXPECTATION.
//
// Narrowing the slice does NOT keep shrinking the design. SLICE=4 costs more
// than SLICE=8, because the cost here is not the S-boxes -- 4 of them is 304
// LUT4 -- it is the multiplexer that picks a slice out of a 1600-bit register.
// Halving the width doubles the number of slices and therefore the mux, and
// past a point the mux grows faster than the S-boxes shrink. There is a
// minimum near SLICE=8 and it is a mux minimum, not an arithmetic one.
//
// On the Tang Nano 20K (20,736 LUT4) the cheapest configuration here is
// 8,673 -- 42% -- before the impulser, the UART or anything else. It fits;
// what does not fit is HCPU and Ka'bah as one top level, measured at 105%,
// over by 960 cells. That is the constraint that actually binds.
//
// The fix that follows from the finding: stop random-accessing the state.
// Rotate it through a fixed substitution position instead, so the mux
// disappears and only the S-boxes and a shift path remain. That is the next
// architecture, and it is not built yet.

`default_nettype none

module hijaiyyah_ramal_core #(
    // Bytes substituted per clock. 200 must divide by it, and the trade is
    // exact: area scales with it, clocks scale inversely. Measured, flattened,
    // yosys abc -lut 4 -- see the table in the header.
    parameter integer SLICE_BYTES = 25
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          load,          // latch in_state and begin
    input  wire [1599:0] in_state,
    input  wire          lin_pulse,
    input  wire          sub_pulse,
    input  wire [7:0]    round_index,
    output wire          stall,         // substitution in progress
    output wire [1599:0] out_state
);

    localparam integer SLICE_BITS = SLICE_BYTES * 8;
    localparam integer SLICES     = 1600 / SLICE_BITS;
    localparam integer SLICE_W    = $clog2(SLICES);

    reg [1599:0]      state;
    reg [SLICE_W-1:0] slice;
    reg          substituting;

    assign out_state = state;

    // Combinational, and that is the point. A registered `stall` is one clock
    // late: the generator tests it before `substituting` has risen, advances,
    // and its next linear pulse lands while the core is mid-substitution and
    // is dropped. That cost one linear layer per round and produced a wrong
    // state at 142 clocks instead of 253. Raising stall on the same clock the
    // substitution is accepted closes it -- the generator sees the datapath
    // become busy in the cycle it becomes busy.
    assign stall = substituting | (lin_pulse & sub_pulse);

    // ---- the linear layer, combinational over the whole state ----------
    wire [1599:0] linear_out;
    hijaiyyah_linear u_linear (.in_state(state), .out_state(linear_out));

    // ---- one 25-byte substitution slice --------------------------------
    wire [SLICE_BITS-1:0] slice_in  = state[slice*SLICE_BITS +: SLICE_BITS];
    wire [SLICE_BITS-1:0] slice_out;

    genvar b;
    generate
        for (b = 0; b < SLICE_BYTES; b = b + 1) begin : sub_byte
            hijaiyyah_sbox u_sbox (
                .x (slice_in [b*8 +: 8]),
                .y (slice_out[b*8 +: 8])
            );
        end
    endgenerate

    // ---- the round constant --------------------------------------------
    wire [63:0] round_constant;
    hijaiyyah_round_constants u_rc (
        .round_index    (round_index),
        .round_constant (round_constant)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state        <= {1600{1'b0}};
            slice        <= {SLICE_W{1'b0}};
            substituting <= 1'b0;
        end else if (load) begin
            state        <= in_state;
            slice        <= {SLICE_W{1'b0}};
            substituting <= 1'b0;
        end else if (substituting) begin
            state[slice*SLICE_BITS +: SLICE_BITS] <= slice_out;
            if (slice == SLICES - 1) begin
                // Last slice, and the constant with it. Disjoint bit ranges,
                // so both writes in one clock are safe.
                state[63:0]  <= state[63:0] ^ round_constant;
                substituting <= 1'b0;
                slice        <= {SLICE_W{1'b0}};
            end else begin
                slice <= slice + 1'b1;
            end
        end else if (lin_pulse) begin
            state <= linear_out;
            if (sub_pulse) begin
                substituting <= 1'b1;
                slice        <= {SLICE_W{1'b0}};
            end
        end
    end

endmodule

`default_nettype wire
