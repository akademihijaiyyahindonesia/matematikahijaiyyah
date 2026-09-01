// tb_hijaiyyah_node_counter.v — the same stream through Verilog and Python.
//
// The vectors are real corpus windows -- zeros, source text, a Mach-O binary,
// gzip output, urandom, and base64'd urandom -- drawn with a fixed seed and
// labelled by src/hijaiyyah/crypto/node_counter.py. A disagreement on any
// window is a disagreement between the two implementations, which is the only
// thing this can be.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_node_counter;
    localparam integer WINDOW  = 64;
    localparam integer WINDOWS = 72;
    localparam integer BYTES   = WINDOW * WINDOWS;

    reg        clk = 1'b0;
    reg        rst_n = 1'b0;
    reg        valid_in = 1'b0;
    reg  [7:0] byte_in = 8'h00;
    wire       valid_out;
    wire [1:0] class_out;
    wire [7:0] xor_key_out;

    reg [7:0] stream [0:BYTES-1];
    reg [3:0] wanted [0:WINDOWS-1];
    reg [7:0] wantkey [0:WINDOWS-1];

    integer i, seen = 0, bad = 0;

    always #5 clk = ~clk;

    hijaiyyah_node_counter #(.WINDOW(WINDOW)) dut (
        .clk(clk), .rst_n(rst_n), .valid_in(valid_in), .byte_in(byte_in),
        .valid_out(valid_out), .class_out(class_out), .xor_key_out(xor_key_out)
    );

    // Check each verdict as it arrives, against the Python label for that window.
    always @(posedge clk) begin
        if (rst_n && valid_out) begin
            if (xor_key_out !== wantkey[seen]) begin
                bad = bad + 1;
                $display("MISMATCH window %0d key got=%02h want=%02h",
                         seen, xor_key_out, wantkey[seen]);
            end
            if (class_out !== wanted[seen][1:0]) begin
                bad = bad + 1;
                $display("MISMATCH window %0d got=%0d want=%0d",
                         seen, class_out, wanted[seen][1:0]);
            end
            seen = seen + 1;
        end
    end

    initial begin
        $readmemh("rtl/tb/node_counter_stream.hex", stream);
        $readmemh("rtl/tb/node_counter_expect.hex", wanted);
        $readmemh("rtl/tb/node_counter_key.hex", wantkey);

        // Stimulus is driven on the NEGATIVE edge, deliberately. Driving it
        // just before the posedge -- `byte_in = ...; @(posedge clk);` -- puts
        // the testbench write and the DUT's sample in the same time step with
        // no ordering between them, and the DUT read the *next* byte. That
        // race produced fourteen mismatches that looked exactly like a design
        // fault: windows of zeros scoring 6, 5 and 3 bits. The design was
        // correct; the harness was not.
        repeat (2) @(negedge clk);
        rst_n = 1'b1;

        for (i = 0; i < BYTES; i = i + 1) begin
            @(negedge clk);
            byte_in  = stream[i];
            valid_in = 1'b1;
        end
        @(negedge clk);
        valid_in = 1'b0;
        repeat (3) @(posedge clk);

        if (seen !== WINDOWS) begin
            bad = bad + 1;
            $display("MISMATCH emitted %0d verdicts, expected %0d", seen, WINDOWS);
        end

        if (bad == 0)
            $display("PASS: %0d/%0d windows agree with node_counter.py (class and key)", seen, WINDOWS);
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
