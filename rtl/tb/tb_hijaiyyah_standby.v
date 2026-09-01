// tb_hijaiyyah_standby.v — the core held, then released, lands the same.
//
// A standby that quietly loses a clock is worse than none: the state would
// still look plausible and be wrong. So this asserts standby in the middle of
// a run, holds it for 40 clocks, checks that not one bit of the state moved,
// releases it, and requires the final answer to be exactly what cube.py gives.
//
// The generator is deliberately NOT gated by standby here. An earlier version
// gated its `enable` too, which meant the core had nothing to do while held
// and its standby branch was never exercised -- deleting that branch left this
// testbench green. Standby now reaches the generator only through the core's
// `stall`, so holding the core is what holds everything.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_standby;
    localparam integer SLICE_BYTES = 25;

    reg clk = 1'b0, rst_n = 1'b0, enable = 1'b0, load = 1'b0, standby = 1'b0;
    reg [1599:0] in_state;
    reg [1599:0] frozen;

    wire lin_pulse, sub_pulse, stall, idle, done;
    wire [7:0] round_index;
    wire [1599:0] out_state;

    reg [1599:0] vin [0:0];
    reg [1599:0] vout [0:0];

    integer i, bad = 0, guard = 0;

    always #5 clk = ~clk;

    hijaiyyah_ramal_impulse #(.ROUNDS(28), .MAX_STRIDE(2)) u_imp (
        .clk(clk), .rst_n(rst_n), .enable(enable), .stall(stall),
        .lin_pulse(lin_pulse), .sub_pulse(sub_pulse),
        .round_index(round_index), .done(done));

    hijaiyyah_rotate_core #(.SLICE_BYTES(SLICE_BYTES)) u_core (
        .clk(clk), .rst_n(rst_n), .standby(standby), .load(load),
        .in_state(in_state), .lin_pulse(lin_pulse), .sub_pulse(sub_pulse),
        .round_index(round_index), .stall(stall), .idle(idle),
        .out_state(out_state));

    task hold;
        input integer which;
        begin
            frozen  = out_state;
            standby = 1'b1;
            for (i = 0; i < 40; i = i + 1) begin
                @(posedge clk); #1;
                if (out_state !== frozen) begin
                    bad = bad + 1;
                    if (bad < 4)
                        $display("MISMATCH hold %0d: state moved at clock %0d",
                                 which, i);
                end
            end
            @(negedge clk);
            standby = 1'b0;
            @(negedge clk);
        end
    endtask

    initial begin
        $readmemh("rtl/tb/core_in.hex",  vin);
        $readmemh("rtl/tb/core_out.hex", vout);
        in_state = vin[0];

        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        @(negedge clk); load = 1'b1;
        @(negedge clk); load = 1'b0; enable = 1'b1;

        // Run part way in, then hold.
        repeat (120) @(posedge clk);
        // Hold at a moment when the core is NOT mid-substitution. Asserting
        // it during one hides a second bug: `substituting` keeps `stall` high
        // on its own, so the generator waits whether or not standby reaches
        // it, and removing standby from `stall` still looked correct. Outside
        // a substitution nothing else holds the generator, and it must.
        // TWO holds, at two different moments, because the two mechanisms
        // cover disjoint cases and testing one position proves only half.
        //
        //   inside a substitution   the core's own standby branch holds it;
        //                           routing standby to `stall` is redundant
        //                           there, since `substituting` already stalls
        //                           the generator.
        //   outside one             nothing else holds the generator, so
        //                           `stall` must carry standby -- and the
        //                           core branch alone is not enough.
        //
        // Each sabotage passes at one position and fails at the other, which
        // is exactly why both are here.
        while (!stall) @(negedge clk);       // ---- hold DURING a substitution
        hold(1);
        while (stall)  @(negedge clk);       // ---- hold OUTSIDE one
        hold(2);

        while (!(done && !stall) && guard < 5000) begin
            @(posedge clk);
            guard = guard + 1;
        end
        repeat (2) @(posedge clk);

        if (out_state !== vout[0]) begin
            bad = bad + 1;
            $display("MISMATCH final state after release");
        end

        if (bad == 0)
            $display("PASS: two holds of 40 clocks, inside and outside a substitution");
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
