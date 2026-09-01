// Priority probe: does standby actually hold an absorb, and does load clear?
`timescale 1ns/1ps
module tb_prio;
    reg clk=0, rst_n=0, standby=0, load=0, absorb_valid=0;
    reg [4:0] step=0; reg [63:0] data=0;
    wire [1599:0] st; wire stall, idle;
    integer bad=0;
    always #5 clk=~clk;
    hijaiyyah_rotate_core #(.SLICE_BYTES(25)) dut (.clk(clk), .rst_n(rst_n),
        .standby(standby), .load(load), .in_state({1600{1'b0}}),
        .absorb_valid(absorb_valid), .absorb_step(step), .absorb_data(data),
        .lin_pulse(1'b0), .sub_pulse(1'b0), .round_index(8'd0),
        .stall(stall), .idle(idle), .out_state(st));
    initial begin
        repeat(2) @(negedge clk); rst_n=1;
        // 1. absorb while standby is asserted -- must NOT change the state
        @(negedge clk); standby=1; absorb_valid=1; step=5'd0; data=64'hDEADBEEFCAFEBABE;
        @(posedge clk); #1;
        if (st !== {1600{1'b0}}) begin
            bad=bad+1; $display("MISMATCH standby did not hold an absorb");
        end
        @(negedge clk); standby=0; absorb_valid=0;
        // 2. load while absorb is asserted -- must clear
        @(negedge clk); absorb_valid=1; data=64'hFFFFFFFFFFFFFFFF;
        @(posedge clk);
        @(negedge clk); load=1;
        @(posedge clk); #1;
        if (st !== {1600{1'b0}}) begin
            bad=bad+1; $display("MISMATCH load did not clear during an absorb");
        end
        if (bad==0) $display("PASS: standby holds an absorb, load clears one");
        else $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule
