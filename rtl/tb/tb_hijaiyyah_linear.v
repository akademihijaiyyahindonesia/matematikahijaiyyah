// tb_hijaiyyah_linear.v — the linear layer against cube.linear_layer.
//
// Sixty-four random 1600-bit states and their images, produced by the Python.
// A wrong rotation constant or a swapped pi destination changes the output and
// nothing else would notice: the layer stays full rank, avalanche stays at
// 0.5, and only a vector comparison catches it.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_linear;
    localparam integer VECTORS = 64;

    reg  [1599:0] in_state;
    wire [1599:0] out_state;

    reg [1599:0] vin  [0:VECTORS-1];
    reg [1599:0] vout [0:VECTORS-1];

    integer i, bad = 0;

    hijaiyyah_linear dut (.in_state(in_state), .out_state(out_state));

    initial begin
        $readmemh("rtl/tb/linear_in.hex",  vin);
        $readmemh("rtl/tb/linear_out.hex", vout);

        for (i = 0; i < VECTORS; i = i + 1) begin
            in_state = vin[i];
            #1;
            if (out_state !== vout[i]) begin
                bad = bad + 1;
                if (bad <= 3)
                    $display("MISMATCH vector %0d\n  got  %h\n  want %h",
                             i, out_state, vout[i]);
            end
        end

        if (bad == 0)
            $display("PASS: %0d/%0d states match cube.linear_layer", VECTORS, VECTORS);
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
