// hijaiyyah_sponge.v — what turns the permutation into a hash.
//
// The core computes a permutation; a sponge is what makes that a digest.
// This is the scheduler between them: it takes 64-bit lanes, walks them onto
// the tawaf ring, and runs one permutation every time the ring is full.
//
//     absorb 16 lanes onto the outer ring   (1024 bits, the rate)
//     permute                                (310 clocks at SLICE=25)
//     repeat
//
// The nine lanes the ring encloses are the capacity -- 576 bits, about 288
// bits of security -- and no input path reaches them. That is geometry here,
// not an index check.
//
// SQUEEZING IS NOT IN THIS MODULE, deliberately. The whole 1600-bit state is
// already on `out_state`, so a consumer reads the lanes it wants directly.
// Adding a read port would rebuild the 1600-bit multiplexer that cost this
// design six thousand LUT4 before it was removed, and for no gain: the
// consumer has the wires either way.
//
// PADDING IS NOT IN THIS MODULE either, and that is a real boundary rather
// than an omission. The rule is append 0x01, zero-fill to the rate, then XOR
// 0x80 into the last byte -- it needs the message length, which a streaming
// interface does not have until the stream ends. The caller pads; this
// absorbs. Said here so nobody assumes a padded stream went in.

`default_nettype none

module hijaiyyah_sponge (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        load,          // clear the state to zero
    input  wire        lane_valid,
    input  wire [63:0] lane_in,
    output wire        lane_ready,    // a lane can be taken this clock
    output wire        busy,          // permuting
    output wire [1599:0] out_state,

    // to the impulser
    output reg         perm_start,
    output wire        perm_enable,
    input  wire        perm_done,

    // to the core
    output reg         absorb_valid,
    output reg  [4:0]  absorb_step,
    output reg  [63:0] absorb_data
);

    //: Lanes on the outer ring. 16 x 64 = 1024 bits of rate.
    localparam integer RATE_LANES = 16;

    localparam [1:0] S_ABSORB  = 2'd0;
    localparam [1:0] S_PERMUTE = 2'd1;
    localparam [1:0] S_LAUNCH  = 2'd2;
    localparam [1:0] S_WAIT    = 2'd3;

    reg [1:0] phase;
    reg [4:0] step;

    assign lane_ready  = (phase == S_ABSORB);
    assign busy        = (phase != S_ABSORB);
    assign perm_enable = (phase == S_LAUNCH) || (phase == S_WAIT);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase        <= S_ABSORB;
            step         <= 5'd0;
            absorb_valid <= 1'b0;
            absorb_step  <= 5'd0;
            absorb_data  <= 64'd0;
            perm_start   <= 1'b0;
        end else begin
            absorb_valid <= 1'b0;
            perm_start   <= 1'b0;

            case (phase)
                S_ABSORB: begin
                    if (load) begin
                        step <= 5'd0;
                    end else if (lane_valid) begin
                        absorb_valid <= 1'b1;
                        absorb_step  <= step;
                        absorb_data  <= lane_in;
                        if (step == RATE_LANES - 1) begin
                            step  <= 5'd0;
                            phase <= S_PERMUTE;
                        end else begin
                            step <= step + 5'd1;
                        end
                    end
                end

                S_PERMUTE: begin
                    // One clock for the absorb write to land, then start.
                    perm_start <= 1'b1;
                    phase      <= S_LAUNCH;
                end

                S_LAUNCH: begin
                    // Wait for `done` to actually fall before waiting for it
                    // to rise. Going straight to S_WAIT reads the PREVIOUS
                    // permutation's `done`, which is still high for one clock
                    // after `start` -- so the second block sailed through
                    // without permuting at all: 28 substitutions in the first,
                    // ZERO in the second, and a state that was fully defined
                    // and wrong.
                    //
                    // Third time this shape of bug appeared here. A status
                    // signal sampled in the same clock it is being changed
                    // reads the old value, and the fix is always to observe
                    // the transition rather than the level.
                    //
                    // A bare one-clock delay would also work today, and the
                    // first sabotage of this line proved it by passing --
                    // `start` happens to clear `done` in exactly one clock.
                    // Waiting for the transition instead does not depend on
                    // that timing holding, which is the difference between a
                    // fix and a coincidence.
                    if (!perm_done) phase <= S_WAIT;
                end

                S_WAIT: begin
                    if (perm_done) phase <= S_ABSORB;
                end

                default: phase <= S_ABSORB;
            endcase
        end
    end

endmodule

`default_nettype wire
