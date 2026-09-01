// hijaiyyah_ramal_impulse.v — the pacing generator for a sa'i round schedule.
//
// Drives hijaiyyah_ramal_core.v and waits on its `stall`: a 200-byte
// substitution runs 25 bytes per clock, so eight clocks pass between the
// pulse and the next round. A generator that ignored that would emit a
// schedule the datapath never actually performs.
//
// Sa'i is not a uniform walk. Between the two green markers the pace changes
// to ramal, a brisk trot, and returns to walking after. This module is that
// pacing in silicon: it drives a datapath holding ONE linear layer and ONE
// substitution layer, and decides per clock which of them fires.
//
// WHY IT EXISTS, measured rather than asserted. The linear layer is XOR trees;
// the substitution is 76 LUT4 per lane, so a 25-lane layer is ~1900 LUT4. They
// are not the same price, and the schedule had been treating them as if they
// were. Giving the linear layer a wider stride before each substitution:
//
//     schedule        S-box   linear   avalanche   degree reached
//     walk  [1,1]         2        2      0.3311   4, 8
//     ramal [1,2]         2        3      0.4999   4, 8
//     ramal [2,1]         2        3      0.4984   4, 8, 16
//     walk  [1,1,1]       3        3      0.5001   4, 8, 16
//
// `ramal [2,1]` matches the uniform three-round walk on BOTH measures with one
// fewer substitution layer. The order matters and is not symmetric: [1,2]
// reaches only degree 8, [2,1] reaches 16. The wide stride has to come FIRST,
// so the reach is in place before the nonlinearity is spent.
//
// WHAT THIS DOES NOT CLAIM. The sealed permutation is unchanged and still runs
// a uniform 28 rounds; this is a generator for exploring a schedule, not a
// replacement for one that has been measured end to end. Diffusion and degree
// are two of the properties a round count answers to, not all of them.

`default_nettype none

module hijaiyyah_ramal_impulse #(
    parameter integer ROUNDS    = 28,
    parameter integer MAX_STRIDE = 2
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,        // begin a fresh schedule, clearing done
    input  wire       enable,
    input  wire       stall,        // datapath is busy; hold the pacing
    output reg        lin_pulse,      // fire the linear layer this clock
    output reg        sub_pulse,      // fire the substitution this clock
    output reg  [7:0] round_index,    // which round constant to apply
    output reg        done
);

    localparam integer STRIDE_W = $clog2(MAX_STRIDE + 1);

    reg [STRIDE_W-1:0] stride_left;
    reg [7:0]          round_no;
    reg                waiting;        // substitution issued, datapath busy

    // The pacing itself: a wide stride first, then walking. Rounds are indexed
    // from zero, and the trot is the opening step of each round.
    function [STRIDE_W-1:0] stride_for;
        input [7:0] r;
        begin
            stride_for = (r == 8'd0) ? MAX_STRIDE[STRIDE_W-1:0]
                                     : {{(STRIDE_W-1){1'b0}}, 1'b1};
        end
    endfunction

    // An explicit wait state, because the obvious version is wrong. Issuing
    // sub_pulse and then testing `stall` on the next clock races the datapath:
    // `stall` is registered there, so it is still low when the generator
    // advances, and the next round's linear pulse arrives while the core is
    // mid-substitution and is dropped on the floor. That cost one linear layer
    // per round -- 142 clocks instead of 253, and a wrong final state.
    //
    // So the generator enters `waiting` on the clock it issues the
    // substitution and leaves only after `stall` has risen and fallen again.
    // The datapath's duration is never assumed here; it is observed.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stride_left <= stride_for(8'd0);
            round_no    <= 8'd0;
            waiting     <= 1'b0;
            lin_pulse   <= 1'b0;
            sub_pulse   <= 1'b0;
            round_index <= 8'd0;
            done        <= 1'b0;
        end else if (start) begin
            // A sponge runs one permutation per rate block, so the schedule
            // has to be restartable. Without this `done` latches once and the
            // second block never runs.
            stride_left <= stride_for(8'd0);
            round_no    <= 8'd0;
            waiting     <= 1'b0;
            done        <= 1'b0;
            lin_pulse   <= 1'b0;
            sub_pulse   <= 1'b0;
        end else if (waiting) begin
            lin_pulse <= 1'b0;
            sub_pulse <= 1'b0;
            if (!stall) begin
                waiting <= 1'b0;
                if (round_no == ROUNDS[7:0] - 8'd1) begin
                    done <= 1'b1;
                end else begin
                    round_no    <= round_no + 8'd1;
                    stride_left <= stride_for(round_no + 8'd1);
                end
            end
        end else if (enable && !done) begin
            round_index <= round_no;
            if (stride_left > 1) begin
                // Still trotting: linear only, no nonlinearity spent yet.
                lin_pulse   <= 1'b1;
                sub_pulse   <= 1'b0;
                stride_left <= stride_left - 1'b1;
            end else begin
                // Last linear step of the round, and the substitution with it.
                lin_pulse <= 1'b1;
                sub_pulse <= 1'b1;
                waiting   <= 1'b1;
            end
        end else begin
            lin_pulse <= 1'b0;
            sub_pulse <= 1'b0;
        end
    end

endmodule

`default_nettype wire
