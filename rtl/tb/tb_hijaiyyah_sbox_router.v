// tb_hijaiyyah_sbox_router.v — the wiring, not the substitution.
//
// tb_hijaiyyah_sbox.v already checks all 256 outputs against cube.SBOX, so
// what is left to verify here is what this module adds: that every lane gets
// its own byte and not its neighbour's, that latency is exactly one clock for
// every input, and that reset clears the stage. Lane crossing is the failure
// this catches -- a generate loop with the wrong slice produces a module that
// substitutes correctly and permutes the bytes, which no S-box test sees.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_sbox_router;
    localparam integer W = 4;

    reg              clk = 1'b0;
    reg              rst_n = 1'b0;
    reg              valid_in = 1'b0;
    reg  [W*8-1:0]   data_in = {W*8{1'b0}};
    wire             valid_out;
    wire [W*8-1:0]   data_out;

    integer bad = 0;
    integer i, trial;
    reg [W*8-1:0] sent;

    always #5 clk = ~clk;

    hijaiyyah_sbox_router #(.WIDTH(W)) dut (
        .clk(clk), .rst_n(rst_n), .valid_in(valid_in),
        .data_in(data_in), .valid_out(valid_out), .data_out(data_out)
    );

    // Reference: one standalone S-box per lane, combinational.
    wire [W*8-1:0] expected;
    genvar g;
    generate
        for (g = 0; g < W; g = g + 1) begin : ref_lane
            hijaiyyah_sbox u_ref (.x(sent[g*8 +: 8]), .y(expected[g*8 +: 8]));
        end
    endgenerate

    initial begin
        repeat (2) @(posedge clk);
        if (data_out !== {W*8{1'b0}} || valid_out !== 1'b0) begin
            bad = bad + 1;
            $display("MISMATCH reset did not clear the stage");
        end
        rst_n = 1'b1;
        @(posedge clk);

        for (trial = 0; trial < 64; trial = trial + 1) begin
            for (i = 0; i < W; i = i + 1)
                data_in[i*8 +: 8] = (trial * 4 + i) & 8'hFF;
            sent     = data_in;
            valid_in = 1'b1;
            @(posedge clk);
            #1;
            if (valid_out !== 1'b1) begin
                bad = bad + 1;
                $display("MISMATCH valid did not arrive one clock later, trial %0d", trial);
            end
            if (data_out !== expected) begin
                bad = bad + 1;
                $display("MISMATCH trial %0d got=%h want=%h", trial, data_out, expected);
            end
        end

        valid_in = 1'b0;
        @(posedge clk);
        #1;
        if (valid_out !== 1'b0) begin
            bad = bad + 1;
            $display("MISMATCH valid stayed high after the stream ended");
        end

        if (bad == 0)
            $display("PASS: 64 groups x %0d lanes, one clock each, no lane crossing", W);
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
