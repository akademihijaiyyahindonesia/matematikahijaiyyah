// tb_hijaiyyah_sponge.v — sponge, impulser and core, against cube.digest.
//
// A padded message goes in one 64-bit lane at a time. Every sixteen lanes the
// ring is full and a permutation runs; the state that comes out must be
// exactly what cube.py's absorb_lane loop produces for the same message.
//
// This is the first point where the whole crypto datapath is in gates at
// once: substitution, linear layer, round constants, pacing, and now the
// sponge scheduling around them.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_sponge;
    // Bound to the vector file at build time, deliberately. Written as a
    // literal it was wrong twice -- 32 against a 16-lane file, then 48 against
    // a 32-lane one -- and each time the run absorbed lanes of X, poisoned the
    // state, and produced a mismatch that read exactly like a design fault.
    // The Makefile target passes -DLANES=$(wc -l < sponge_lanes.hex).
`ifndef LANES
  `define LANES 32
`endif
    localparam integer LANES = `LANES;

    reg clk = 1'b0, rst_n = 1'b0, load = 1'b0;
    reg lane_valid = 1'b0;
    reg [63:0] lane_in = 64'd0;

    wire lane_ready, busy;
    wire [1599:0] out_state;
    wire perm_start, perm_enable, perm_done;
    wire absorb_valid; wire [4:0] absorb_step; wire [63:0] absorb_data;
    wire lin_pulse, sub_pulse, stall, idle;
    wire [7:0] round_index;

    reg [63:0]   lanes [0:LANES-1];
    reg [1599:0] want  [0:0];

    integer i, bad = 0, guard = 0;

    always #5 clk = ~clk;

    hijaiyyah_sponge u_sponge (
        .clk(clk), .rst_n(rst_n), .load(load),
        .lane_valid(lane_valid), .lane_in(lane_in),
        .lane_ready(lane_ready), .busy(busy), .out_state(out_state),
        .perm_start(perm_start), .perm_enable(perm_enable), .perm_done(perm_done),
        .absorb_valid(absorb_valid), .absorb_step(absorb_step),
        .absorb_data(absorb_data));

    hijaiyyah_ramal_impulse #(.ROUNDS(28), .MAX_STRIDE(1)) u_imp (
        .clk(clk), .rst_n(rst_n), .start(perm_start), .enable(perm_enable),
        .stall(stall), .lin_pulse(lin_pulse), .sub_pulse(sub_pulse),
        .round_index(round_index), .done(perm_done));

    hijaiyyah_rotate_core #(.SLICE_BYTES(25)) u_core (
        .clk(clk), .rst_n(rst_n), .standby(1'b0), .load(load),
        .in_state({1600{1'b0}}),
        .absorb_valid(absorb_valid), .absorb_step(absorb_step),
        .absorb_data(absorb_data),
        .lin_pulse(lin_pulse), .sub_pulse(sub_pulse), .round_index(round_index),
        .stall(stall), .idle(idle), .out_state(out_state));

    initial begin
        $readmemh("rtl/tb/sponge_lanes.hex", lanes);
        $readmemh("rtl/tb/sponge_state.hex", want);

        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        @(negedge clk); load = 1'b1;
        @(negedge clk); load = 1'b0;

        // A proper ready/valid feed. The first version offered a lane, waited
        // one edge, and then advanced whether or not the sponge had taken it --
        // so every lane offered while a permutation was running was dropped on
        // the floor. The state came out fully defined and completely wrong,
        // which is the worst shape a testbench bug can take.
        //
        // Here the index only advances on an edge where the sponge was ready.
        i = 0;
        while (i < LANES) begin
            @(negedge clk);
            if (lane_ready) begin
                lane_in    = lanes[i];
                lane_valid = 1'b1;
                i = i + 1;
            end else begin
                lane_valid = 1'b0;
            end
        end
        @(negedge clk);
        lane_valid = 1'b0;

        // Let the last permutation finish.
        while (busy && guard < 20000) begin
            @(posedge clk);
            guard = guard + 1;
        end
        repeat (4) @(posedge clk);

        if (out_state !== want[0]) begin
            bad = bad + 1;
            $display("MISMATCH state after absorption\n  got  %h\n  want %h",
                     out_state, want[0]);
        end

        if (bad == 0)
            $display("PASS: %0d lanes absorbed, state matches cube.py", LANES);
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
