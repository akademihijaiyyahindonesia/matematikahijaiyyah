// tb_hijaiyyah_gate_mode.v — the gate actually gating, and the break joined.
//
// Before this, `gate_pulse` went to an output port and the sponge absorbed
// every byte regardless: a detector wired to nothing, which is worse than no
// detector because the output looks like enforcement.
//
// A stream of codex letter indices with ONE byte corrupted at a known
// position. In gate_mode the corrupted byte must not reach the sponge -- the
// absorbed state must equal cube.py over the *admitted* bytes only -- and the
// break must be reported at exactly that position, not merely counted.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_gate_mode;
`ifndef NBITS
  `define NBITS 800
`endif
    localparam integer NBITS    = `NBITS;
    localparam integer BREAK_AT = 37;

    reg clk = 1'b0, rst_n = 1'b0, load = 1'b0, bit_valid = 1'b0, bit_in = 1'b0;

    wire gate_pulse, class_valid, absorbing, permuting, bits_ready;
    wire [3:0] gate_root;
    wire [1:0] class_out;
    wire [7:0] xor_key_out;
    wire [1599:0] out_state;
    wire break_valid;
    wire [31:0] break_at;
    wire [15:0] break_count;

    reg [0:0]    stream [0:NBITS-1];
    reg [1599:0] want   [0:0];

    integer i, bad = 0, guard = 0;

    always #5 clk = ~clk;

    hijaiyyah_kabah_top #(.SLICE_BYTES(25), .WINDOW(64)) dut (
        .clk(clk), .rst_n(rst_n), .standby(1'b0), .load(load),
        .gate_mode(1'b1),
        .phase(3'd0), .bit_valid(bit_valid), .bit_in(bit_in),
        .gate_pulse(gate_pulse), .gate_root(gate_root),
        .break_valid(break_valid), .break_at(break_at), .break_count(break_count),
        .class_valid(class_valid), .class_out(class_out),
        .xor_key_out(xor_key_out),
        .bits_ready(bits_ready), .absorbing(absorbing), .permuting(permuting),
        .out_state(out_state));

    initial begin
        $readmemb("rtl/tb/gate_bits.hex",  stream);
        $readmemh("rtl/tb/gate_state.hex", want);

        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        @(negedge clk); load = 1'b1;
        @(negedge clk); load = 1'b0;

        i = 0;
        while (i < NBITS && guard < 100000) begin
            @(negedge clk);
            if (bits_ready) begin
                bit_in    = stream[i];
                bit_valid = 1'b1;
                i = i + 1;
            end else begin
                bit_valid = 1'b0;
            end
            guard = guard + 1;
        end
        @(negedge clk); bit_valid = 1'b0;

        while (permuting && guard < 100000) begin
            @(posedge clk); guard = guard + 1;
        end
        repeat (4) @(posedge clk);

        if (!break_valid) begin
            bad = bad + 1;
            $display("MISMATCH the break was never reported");
        end
        if (break_at !== BREAK_AT) begin
            bad = bad + 1;
            $display("MISMATCH break reported at %0d, corrupted byte is at %0d",
                     break_at, BREAK_AT);
        end
        if (break_count !== 16'd1) begin
            bad = bad + 1;
            $display("MISMATCH %0d breaks counted, exactly 1 was injected",
                     break_count);
        end
        if (out_state !== want[0]) begin
            bad = bad + 1;
            $display("MISMATCH the refused byte reached the sponge");
        end

        if (bad == 0)
            $display("PASS: break at byte %0d, %0d refused, sponge saw admitted bytes only",
                     break_at, break_count);
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
