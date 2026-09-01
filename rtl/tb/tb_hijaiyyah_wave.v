// tb_hijaiyyah_wave.v — a raw bitstream through the line-rate stages.
//
// 39997 bits of repeating-key-XOR'd source text, offered one per clock with no
// byte boundary. The phase is the one software discovered; everything after it
// -- deserialising, classifying, key recovery -- must agree window for window
// with hijaiyyah.crypto.wave running on the same stream.
//
// Stimulus is driven on the negative edge. Driving it just before the posedge
// races the DUT's sample; that mistake cost fourteen phantom mismatches in
// tb_hijaiyyah_node_counter and is not repeated here.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_wave;
    localparam integer WINDOW  = 64;
    localparam integer NBITS   = 39997;
    localparam integer WINDOWS = 78;
    localparam [2:0]   PHASE   = 3'd5;

    reg        clk = 1'b0;
    reg        rst_n = 1'b0;
    reg        bit_valid = 1'b0;
    reg        bit_in = 1'b0;
    wire       found_valid;
    wire [1:0] found_class;
    wire [7:0] found_key;

    reg [0:0] stream [0:NBITS-1];
    reg [3:0] wanted [0:WINDOWS-1];
    reg [7:0] wantkey[0:WINDOWS-1];

    integer i, seen = 0, bad = 0;

    always #5 clk = ~clk;

    hijaiyyah_wave #(.WINDOW(WINDOW)) dut (
        .clk(clk), .rst_n(rst_n), .phase(PHASE),
        .bit_valid(bit_valid), .bit_in(bit_in),
        .found_valid(found_valid), .found_class(found_class), .found_key(found_key)
    );

    always @(posedge clk) begin
        if (rst_n && found_valid && seen < WINDOWS) begin
            if (found_class !== wanted[seen][1:0]) begin
                bad = bad + 1;
                $display("MISMATCH window %0d class got=%0d want=%0d",
                         seen, found_class, wanted[seen][1:0]);
            end
            if (found_key !== wantkey[seen]) begin
                bad = bad + 1;
                $display("MISMATCH window %0d key got=%02h want=%02h",
                         seen, found_key, wantkey[seen]);
            end
            seen = seen + 1;
        end
    end

    initial begin
        $readmemb("rtl/tb/wave_bits.hex",   stream);
        $readmemh("rtl/tb/wave_expect.hex", wanted);
        $readmemh("rtl/tb/wave_key.hex",    wantkey);

        repeat (2) @(negedge clk);
        rst_n = 1'b1;

        for (i = 0; i < NBITS; i = i + 1) begin
            @(negedge clk);
            bit_in    = stream[i];
            bit_valid = 1'b1;
        end
        @(negedge clk);
        bit_valid = 1'b0;
        repeat (4) @(posedge clk);

        if (seen !== WINDOWS) begin
            bad = bad + 1;
            $display("MISMATCH emitted %0d windows, expected %0d", seen, WINDOWS);
        end

        if (bad == 0)
            $display("PASS: %0d/%0d windows agree, from bits with no boundary given",
                     seen, WINDOWS);
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
