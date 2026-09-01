// tb_hijaiyyah_rotate_core.v — impulser and datapath together, end to end.
//
// The pulses converted back into a computation, which is the only thing that
// makes a pacing generator more than a table. One random 1600-bit state runs
// the full ramal schedule -- a wide opening stride then 27 walking rounds --
// and must land on exactly what cube.py produces for the same schedule.
//
// The datapath is what proves the schedule is real: the impulser is stalled
// for eight clocks on every substitution, so the round count and the clock
// count are different numbers and both have to come out right.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_rotate_core;
    localparam integer ROUNDS = 28;
    localparam integer STRIDE = 2;
`ifndef SLICE_BYTES
  `define SLICE_BYTES 25
`endif
    localparam integer SLICE_BYTES = `SLICE_BYTES;
    // 29 linear pulses + 28 substitutions x 8 slices.
    localparam integer EXPECT_CLK = (ROUNDS + STRIDE - 1) + ROUNDS * 8;

    reg clk = 1'b0, rst_n = 1'b0, enable = 1'b0, load = 1'b0;
    reg [1599:0] in_state;

    wire lin_pulse, sub_pulse, done, stall;
    wire [7:0] round_index;
    wire [1599:0] out_state;

    reg [1599:0] vin  [0:0];
    reg [1599:0] vout [0:0];

    integer bad = 0, guard = 0, subs = 0;

    always #5 clk = ~clk;

    hijaiyyah_ramal_impulse #(.ROUNDS(ROUNDS), .MAX_STRIDE(STRIDE)) u_imp (
        .clk(clk), .rst_n(rst_n), .start(1'b0), .enable(enable), .stall(stall),
        .lin_pulse(lin_pulse), .sub_pulse(sub_pulse),
        .round_index(round_index), .done(done)
    );

    hijaiyyah_rotate_core #(.SLICE_BYTES(SLICE_BYTES)) u_core (
        .clk(clk), .rst_n(rst_n), .standby(1'b0), .load(load), .in_state(in_state),
        .absorb_valid(1'b0), .absorb_step(5'd0), .absorb_data(64'd0),
        .lin_pulse(lin_pulse), .sub_pulse(sub_pulse), .round_index(round_index),
        .stall(stall), .idle(), .out_state(out_state)
    );

    always @(posedge clk) if (rst_n && sub_pulse) subs = subs + 1;

    initial begin
        $readmemh("rtl/tb/core_in.hex",  vin);
        $readmemh("rtl/tb/core_out.hex", vout);
        in_state = vin[0];

        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        @(negedge clk);
        load = 1'b1;
        @(negedge clk);
        load = 1'b0;
        enable = 1'b1;

        while (!(done && !stall) && guard < 5000) begin
            @(posedge clk);
            guard = guard + 1;
        end
        repeat (2) @(posedge clk);

        if (subs !== ROUNDS) begin
            bad = bad + 1;
            $display("MISMATCH %0d substitution pulses, expected %0d", subs, ROUNDS);
        end
        if (out_state !== vout[0]) begin
            bad = bad + 1;
            $display("MISMATCH final state\n  got  %h\n  want %h", out_state, vout[0]);
        end

        if (bad == 0)
            $display("PASS: %0d rounds, %0d clocks, state matches cube.py",
                     ROUNDS, guard);
        else
            $display("FAIL: %0d mismatches (%0d clocks)", bad, guard);
        $finish;
    end
endmodule

`default_nettype wire
