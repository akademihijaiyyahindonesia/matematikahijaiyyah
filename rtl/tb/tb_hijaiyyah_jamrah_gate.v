// tb_hijaiyyah_jamrah_gate.v — all 256 bytes, every node, and the gate.
//
// The tree is checked node by node rather than only at the root, because the
// root is a popcount and a popcount would still look right with the internal
// structure wrong. Seven taps, one pulse, 256 inputs, no sampling.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_jamrah_gate;
    reg clk = 1'b0, rst_n = 1'b0, valid_in = 1'b0;
    reg [7:0] byte_in = 8'd0;

    wire pulse;
    wire [3:0] root, node6;
    wire [1:0] node0, node1, node2, node3;
    wire [2:0] node4, node5;

    integer fd, code, bad = 0, seen = 0;
    integer b, p, w0, w1, w2, w3, w4, w5, w6;

    always #5 clk = ~clk;

    hijaiyyah_jamrah_gate dut (
        .clk(clk), .rst_n(rst_n), .valid_in(valid_in), .byte_in(byte_in),
        .pulse(pulse), .root(root),
        .node0(node0), .node1(node1), .node2(node2), .node3(node3),
        .node4(node4), .node5(node5), .node6(node6)
    );

    initial begin
        fd = $fopen("rtl/tb/jamrah_vectors.txt", "r");
        if (fd == 0) begin
            $display("FAIL: cannot open vectors");
            $finish;
        end

        repeat (2) @(negedge clk);
        rst_n = 1'b1;

        code = $fscanf(fd, "%h %d %d %d %d %d %d %d %h\n",
                       b, p, w0, w1, w2, w3, w4, w5, w6);
        while (code == 9) begin
            @(negedge clk);
            byte_in  = b[7:0];
            valid_in = 1'b1;
            @(posedge clk);
            #1;
            seen = seen + 1;
            if (pulse !== p[0]) begin
                bad = bad + 1;
                $display("MISMATCH byte %02h pulse got=%b want=%b", b, pulse, p[0]);
            end
            if (node0 !== w0[1:0] || node1 !== w1[1:0] ||
                node2 !== w2[1:0] || node3 !== w3[1:0] ||
                node4 !== w4[2:0] || node5 !== w5[2:0] ||
                node6 !== w6[3:0] || root !== w6[3:0]) begin
                bad = bad + 1;
                $display("MISMATCH byte %02h nodes %0d %0d %0d %0d %0d %0d %0d",
                         b, node0, node1, node2, node3, node4, node5, node6);
            end
            code = $fscanf(fd, "%h %d %d %d %d %d %d %d %h\n",
                           b, p, w0, w1, w2, w3, w4, w5, w6);
        end
        $fclose(fd);

        if (seen !== 256) begin
            bad = bad + 1;
            $display("MISMATCH saw %0d bytes, expected 256", seen);
        end

        if (bad == 0)
            $display("PASS: 256/256 bytes, seven nodes each, gate agrees");
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
