// tb_hijaiyyah_ramal_impulse.v — the pacing, counted.
//
// What must hold: exactly ROUNDS substitutions, one per round; a linear pulse
// on every clock the generator is running; the opening round carrying the wide
// stride and every later round walking; and `done` exactly once.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_ramal_impulse;
    localparam integer ROUNDS = 28;
    localparam integer STRIDE = 2;
    // A wide opening stride costs one extra linear pulse over a uniform walk.
    localparam integer EXPECT_LIN = ROUNDS + (STRIDE - 1);

    reg clk = 1'b0, rst_n = 1'b0, enable = 1'b0;
    wire lin_pulse, sub_pulse, done;
    wire [7:0] round_index;

    integer lins = 0, subs = 0, dones = 0, bad = 0, guard = 0;

    always #5 clk = ~clk;

    hijaiyyah_ramal_impulse #(.ROUNDS(ROUNDS), .MAX_STRIDE(STRIDE)) dut (
        .clk(clk), .rst_n(rst_n), .start(1'b0), .enable(enable), .stall(1'b0),
        .lin_pulse(lin_pulse), .sub_pulse(sub_pulse),
        .round_index(round_index), .done(done)
    );

    always @(posedge clk) begin
        if (rst_n) begin
            if (lin_pulse) lins = lins + 1;
            // Rounds are zero-indexed, so the Nth substitution belongs to
            // round N-1. Comparing against the post-increment count made all
            // twenty-eight look wrong when the sequence was exactly right.
            if (sub_pulse) begin
                if (round_index !== subs[7:0]) begin
                    bad = bad + 1;
                    $display("MISMATCH substitution %0d carried round index %0d",
                             subs + 1, round_index);
                end
                subs = subs + 1;
            end
        end
    end

    always @(posedge done) dones = dones + 1;

    initial begin
        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        @(negedge clk);
        enable = 1'b1;

        while (!done && guard < 1000) begin
            @(posedge clk);
            guard = guard + 1;
        end
        repeat (3) @(posedge clk);

        if (subs !== ROUNDS) begin
            bad = bad + 1;
            $display("MISMATCH %0d substitutions, expected %0d", subs, ROUNDS);
        end
        if (lins !== EXPECT_LIN) begin
            bad = bad + 1;
            $display("MISMATCH %0d linear pulses, expected %0d", lins, EXPECT_LIN);
        end
        if (dones !== 1) begin
            bad = bad + 1;
            $display("MISMATCH done asserted %0d times", dones);
        end

        if (bad == 0)
            $display("PASS: %0d substitutions, %0d linear pulses, one wide stride",
                     subs, lins);
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
