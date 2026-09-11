// hijaiyyah_rotate_core.v — the same round, with the multiplexer removed.
//
// hijaiyyah_ramal_core.v picks a slice out of a 1600-bit register with a
// variable part-select, and measuring it showed the cost was almost all in
// that multiplexer rather than in the S-boxes: SLICE=4 came out *more*
// expensive than SLICE=8 (9,517 against 8,673 LUT4), because halving the
// width doubles the slice count and therefore the mux.
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
//     SLICE_BYTES   sliced    rotated   saving   clocks   rotated/20,736
//               4    9,517      4,603    -52%     1,486   22%
//               8    8,673      4,927    -43%       786   23%
//              25   12,074      6,331    -48%       310   30%
//              50       --      9,438       --      198   45%
//
// And the curve is now monotonic in the right direction -- narrower is
// smaller, 4,603 < 4,927 < 6,331 -- which is exactly what should happen once
// the addressing is gone. Under the sliced design it was not, and that
// inversion was the evidence that pointed here.
//
// FULL SYSTEM, impulser and core together at SLICE_BYTES=25, against the
// Tang Nano 20K (GW2AR-18C, 20,736 LUT4 / 15,552 FF):
//
//     6,229 LUT4   30%      14,507 LUT4 left for the UART and the HCPU
//     1,623 FF     10%
//     310 clocks per permutation
//
// Generic 4-LUT mapping, not a vendor fitting report: synth_gowin does not
// complete here and nextpnr is not installed, so this is a strong indication
// that it fits and not a placed-and-routed proof. This module's OWN Fmax is
// still unmeasured -- it has never been placed standalone. What has been
// placed and run is the wrapper that contains it, at 165.98 MHz.
//
// THROUGHPUT PER SECOND -- AT AN ASSUMED CLOCK, WHICH IS THE WHOLE CAVEAT.
// The Tang Nano 20K carries a 27 MHz crystal, so 27 MHz is what the board
// offers, NOT what this design has been shown to close timing at. The
// achievable Fmax is unmeasured -- that is E1, and it still has no value.
// Every figure below therefore reads "if it closes at 27 MHz":
//
//     SLICE   clocks   permutations/s   sponge throughput
//         8      786           34,351       4.40 MB/s
//        25      310           87,097      11.15 MB/s
//        50      198          136,364      17.45 MB/s
//
// at the sponge's 128-byte rate. These are THIS CORE'S figures, fed a byte per
// clock. They are not the system's: hijaiyyah_kabah_top is fed a bit stream,
// and its deserialiser costs 8 clocks per byte -- 3.3x this core's 2.42 -- so
// the system runs at 2.59 MB/s, not 11.15. Quoting the 11.15 as the system's
// throughput overstated it by 4x; see that module's header for the measurement.
//
// Turned around, against the security levels
// the construction claims, one board at 87,097 attempts per second:
//
//     2^288  the sponge's capacity      1.8e74 years
//     2^256  layer 3's HMAC-SHA256      4.2e64 years
//
// Those numbers are arithmetic on an exponent, not a security argument. What
// they show is only that throughput is nowhere near the security level, which
// is the uninteresting direction: no amount of silicon moves 2^256, and the
// figures are here so the ratio is on the record rather than assumed.

`default_nettype none

module hijaiyyah_rotate_core #(
    parameter integer SLICE_BYTES = 8      // 200 must divide by this
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          standby,      // hold: no state change, no toggling
    input  wire          load,
    input  wire [1599:0] in_state,
    input  wire          absorb_valid, // XOR one lane onto the tawaf ring
    input  wire [4:0]    absorb_step,  // position on the ring, 0..15
    input  wire [63:0]   absorb_data,
    input  wire          lin_pulse,
    input  wire          sub_pulse,
    input  wire [7:0]    round_index,
    output wire          stall,
    output wire          idle,         // nothing in flight
    output wire [1599:0] out_state
);

    localparam integer SLICE_BITS = SLICE_BYTES * 8;
    localparam integer SLICES     = 1600 / SLICE_BITS;
    localparam integer COUNT_W    = $clog2(SLICES);

    reg [1599:0]      state;
    reg [COUNT_W-1:0] step;
    reg               substituting;

    assign out_state = state;
    assign stall     = substituting | (lin_pulse & sub_pulse) | standby;

    // Standby holds the datapath AND stalls the generator through the same
    // handshake the substitution uses. Routing it into `stall` rather than
    // gating the generator separately is what makes it testable: the first
    // version gated `enable` at the top level as well, so the core had nothing
    // to do while held and its standby branch carried no load at all. Removing
    // that branch left the testbench green -- a sabotage that passes is a test
    // proving nothing, and it was the second time in this work that a standby
    // -shaped assertion measured the wrong thing.
    //
    // It is not a security feature and is not offered as one: a held state is
    // still a state, and anything that could read it running can read it
    // stopped. It stops toggling, nothing more.
    assign idle      = ~substituting;

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

    // ---- absorption: a one-hot write, never a read mux --------------
    //
    // Input only ever reaches the sixteen lanes of the outer ring; the nine
    // it encloses are the capacity and nothing written from outside touches
    // them. That separation is the sponge's security and here it is the
    // geometry, not an index range.
    //
    // Written as a decoder plus per-lane write-enable rather than an
    // addressed write. An addressed write would rebuild exactly the 1600-bit
    // multiplexer that cost this design 6,000 LUT4 before it was removed.
    //
    // PRIORITY MATTERS AND I GOT IT WRONG. This branch was first inserted
    // ahead of `standby` and `load`, so an absorb overrode both: asserting
    // standby did not hold an absorb, and load did not clear the state while
    // one was in flight. Neither showed up in any existing test, because the
    // sponge never drives those signals together. A hold must hold
    // everything and a clear must clear everything, so both now come first.
    //
    // TAWAF_PATH = 0, 1, 2, 3, 4, 9, 14, 19, 24, 23, 22, 21, 20, 15, 10, 5
    wire ring0 = absorb_valid & (absorb_step == 5'd0);
    wire ring1 = absorb_valid & (absorb_step == 5'd1);
    wire ring2 = absorb_valid & (absorb_step == 5'd2);
    wire ring3 = absorb_valid & (absorb_step == 5'd3);
    wire ring4 = absorb_valid & (absorb_step == 5'd4);
    wire ring5 = absorb_valid & (absorb_step == 5'd5);
    wire ring6 = absorb_valid & (absorb_step == 5'd6);
    wire ring7 = absorb_valid & (absorb_step == 5'd7);
    wire ring8 = absorb_valid & (absorb_step == 5'd8);
    wire ring9 = absorb_valid & (absorb_step == 5'd9);
    wire ring10 = absorb_valid & (absorb_step == 5'd10);
    wire ring11 = absorb_valid & (absorb_step == 5'd11);
    wire ring12 = absorb_valid & (absorb_step == 5'd12);
    wire ring13 = absorb_valid & (absorb_step == 5'd13);
    wire ring14 = absorb_valid & (absorb_step == 5'd14);
    wire ring15 = absorb_valid & (absorb_step == 5'd15);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state        <= {1600{1'b0}};
            step         <= {COUNT_W{1'b0}};
            substituting <= 1'b0;
        end else if (standby) begin
            state        <= state;
            step         <= step;
            substituting <= substituting;
        end else if (load) begin
            state        <= in_state;
            step         <= {COUNT_W{1'b0}};
            substituting <= 1'b0;
        end else if (absorb_valid) begin
                if (ring0) state[0*64 +: 64] <= state[0*64 +: 64] ^ absorb_data;
                if (ring1) state[1*64 +: 64] <= state[1*64 +: 64] ^ absorb_data;
                if (ring2) state[2*64 +: 64] <= state[2*64 +: 64] ^ absorb_data;
                if (ring3) state[3*64 +: 64] <= state[3*64 +: 64] ^ absorb_data;
                if (ring4) state[4*64 +: 64] <= state[4*64 +: 64] ^ absorb_data;
                if (ring5) state[9*64 +: 64] <= state[9*64 +: 64] ^ absorb_data;
                if (ring6) state[14*64 +: 64] <= state[14*64 +: 64] ^ absorb_data;
                if (ring7) state[19*64 +: 64] <= state[19*64 +: 64] ^ absorb_data;
                if (ring8) state[24*64 +: 64] <= state[24*64 +: 64] ^ absorb_data;
                if (ring9) state[23*64 +: 64] <= state[23*64 +: 64] ^ absorb_data;
                if (ring10) state[22*64 +: 64] <= state[22*64 +: 64] ^ absorb_data;
                if (ring11) state[21*64 +: 64] <= state[21*64 +: 64] ^ absorb_data;
                if (ring12) state[20*64 +: 64] <= state[20*64 +: 64] ^ absorb_data;
                if (ring13) state[15*64 +: 64] <= state[15*64 +: 64] ^ absorb_data;
                if (ring14) state[10*64 +: 64] <= state[10*64 +: 64] ^ absorb_data;
                if (ring15) state[5*64 +: 64] <= state[5*64 +: 64] ^ absorb_data;
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
