// tb_hijaiyyah_kabah_top.v — the whole line-rate system, bits to state.
//
// A padded message enters as raw bits, one per clock, at an arbitrary offset
// with no byte boundary given. It must come out as exactly the state cube.py
// produces for the same message: through the deserialiser at the discovered
// phase, the jamrah gate, the node counter, lane assembly, the tawaf ring,
// and three permutations.
//
// `bits_ready` is honoured, which is the point of the test as much as the
// state is: a permutation is 310 clocks and a source that ignores
// backpressure loses every lane offered during one.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_kabah_top;
`ifndef NBITS
  `define NBITS 3069
`endif
    localparam integer NBITS = `NBITS;
    localparam [2:0]   PHASE = 3'd5;

    reg clk = 1'b0, rst_n = 1'b0, standby = 1'b0, load = 1'b0;
    reg bit_valid = 1'b0, bit_in = 1'b0;

    wire gate_pulse, class_valid, absorbing, permuting, bits_ready;
    wire [3:0] gate_root;
    wire [1:0] class_out;
    wire [7:0] xor_key_out;
    wire [1599:0] out_state;

    reg [0:0]    stream [0:NBITS-1];
    reg [1599:0] want   [0:0];

    integer i, bad = 0, guard = 0, gated = 0, classes = 0, held = 0;

    always #5 clk = ~clk;

    hijaiyyah_kabah_top #(.SLICE_BYTES(25), .WINDOW(64)) dut (
        .clk(clk), .rst_n(rst_n), .standby(standby), .load(load),
        .phase(PHASE), .bit_valid(bit_valid), .bit_in(bit_in),
        .gate_pulse(gate_pulse), .gate_root(gate_root),
        .class_valid(class_valid), .class_out(class_out),
        .xor_key_out(xor_key_out),
        .bits_ready(bits_ready), .absorbing(absorbing), .permuting(permuting),
        .out_state(out_state));

    always @(posedge clk) if (rst_n && gate_pulse)  gated   = gated + 1;
    always @(posedge clk) if (rst_n && class_valid) classes = classes + 1;

    initial begin
        $display("  [start] NBITS=%0d", NBITS);
        $readmemb("rtl/tb/kabah_bits.hex",  stream);
        $readmemh("rtl/tb/kabah_state.hex", want);

        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        @(negedge clk); load = 1'b1;
        @(negedge clk); load = 1'b0;

        i = 0;
        while (i < NBITS && guard < 40000) begin
            @(negedge clk);
            if (bits_ready) begin
                bit_in    = stream[i];
                bit_valid = 1'b1;
                i = i + 1;
            end else begin
                bit_valid = 1'b0;
                held = held + 1;
            end
            guard = guard + 1;
        end
        @(negedge clk);
        bit_valid = 1'b0;

        while (permuting && guard < 40000) begin
            @(posedge clk);
            guard = guard + 1;
        end
        repeat (4) @(posedge clk);

        if (out_state !== want[0]) begin
            bad = bad + 1;
            $display("MISMATCH final state\n  got  %h\n  want %h", out_state, want[0]);
        end
        if (gated == 0 || classes == 0) begin
            bad = bad + 1;
            $display("MISMATCH triage produced nothing: gated=%0d classes=%0d",
                     gated, classes);
        end
        if (held == 0) begin
            bad = bad + 1;
            $display("MISMATCH backpressure never asserted, so it is untested");
        end

        if (bad == 0)
            $display("PASS: %0d bits -> state matches cube.py; %0d letters gated, %0d windows classified, %0d clocks held",
                     NBITS, gated, classes, held);
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
