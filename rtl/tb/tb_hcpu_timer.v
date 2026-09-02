// tb_hcpu_timer.v — the counter, the compare, and the sticky flag.
//
// Four properties, each one a way the timer could be quietly useless: the
// counter must actually advance, the flag must rise when they meet, it must
// STAY up until cleared, and setting a new compare must not leave a stale
// expiry behind.
`timescale 1ns/1ps
`default_nettype none

module tb_hcpu_timer;
    reg clk = 1'b0, rst_n = 1'b0, compare_we = 1'b0, clear = 1'b0;
    reg [31:0] compare_in = 32'd0;
    wire [31:0] counter, compare;
    wire expired;

    integer bad = 0, i;
    reg [31:0] mark;

    always #5 clk = ~clk;

    hcpu_timer dut (.clk(clk), .rst_n(rst_n), .compare_in(compare_in),
        .compare_we(compare_we), .clear(clear),
        .counter(counter), .compare(compare), .expired(expired));

    initial begin
        repeat (2) @(negedge clk);
        rst_n = 1'b1;

        // 1. the counter advances
        mark = counter;
        repeat (10) @(posedge clk);
        #1;
        if (counter - mark !== 32'd10) begin
            bad = bad + 1;
            $display("MISMATCH counter advanced %0d in 10 clocks", counter - mark);
        end

        // 2. the flag rises when they meet
        @(negedge clk);
        compare_in = counter + 32'd20;
        compare_we = 1'b1;
        @(negedge clk);
        compare_we = 1'b0;
        if (expired) begin
            bad = bad + 1;
            $display("MISMATCH expired before the deadline");
        end
        repeat (25) @(posedge clk);
        #1;
        if (!expired) begin
            bad = bad + 1;
            $display("MISMATCH deadline passed without expiring");
        end

        // 3. it stays up until cleared — a flag that clears itself cannot be
        //    polled by two pieces of code
        repeat (30) @(posedge clk);
        #1;
        if (!expired) begin
            bad = bad + 1;
            $display("MISMATCH the flag did not stay up");
        end

        // 4. a new compare must not carry a stale expiry — and this has to be
        //    tested while the flag is STILL UP. Clearing first and then setting
        //    a compare passes even when the write keeps the old value, which
        //    is exactly how the first version of this test let that sabotage
        //    through: it checked a zero that was already zero.
        @(negedge clk);
        compare_in = counter + 32'd50;
        compare_we = 1'b1;
        @(negedge clk);
        compare_we = 1'b0;
        #1;
        if (expired) begin
            bad = bad + 1;
            $display("MISMATCH a new deadline came up already expired");
        end

        // 5. and an explicit clear still clears
        @(negedge clk);
        compare_in = counter + 32'd5;
        compare_we = 1'b1;
        @(negedge clk); compare_we = 1'b0;
        repeat (10) @(posedge clk);
        #1;
        if (!expired) begin
            bad = bad + 1;
            $display("MISMATCH short deadline did not expire");
        end
        @(negedge clk); clear = 1'b1;
        @(negedge clk); clear = 1'b0;
        #1;
        if (expired) begin
            bad = bad + 1;
            $display("MISMATCH clear did not clear");
        end

        if (bad == 0)
            $display("PASS: counts, expires, stays up, and clears on write");
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
