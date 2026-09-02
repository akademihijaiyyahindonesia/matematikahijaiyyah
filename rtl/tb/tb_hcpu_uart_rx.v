// tb_hcpu_uart_rx.v — bytes driven onto the line at the real bit period.
//
// Not a shortcut that pokes the shift register: the stimulus holds each bit
// for a full DIVISOR of clocks, exactly as a wire would, so the mid-bit
// sampling is what is being tested rather than assumed. Three cases the
// receiver must separate — a good frame, a glitch on an idle line, and a
// frame whose stop bit is low.
`timescale 1ns/1ps
`default_nettype none

module tb_hcpu_uart_rx;
    localparam integer CLK_HZ  = 27_000_000;
    localparam integer BAUD    = 115200;
    localparam integer DIVISOR = CLK_HZ / BAUD;

    reg clk = 1'b0, rst_n = 1'b0, line = 1'b1;
    wire [7:0] data;
    wire valid, frame_err;

    integer bad = 0, seen = 0, errs = 0;
    integer i, b;
    reg [7:0] want;

    always #5 clk = ~clk;

    hcpu_uart_rx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) dut (
        .clk(clk), .rst_n(rst_n), .rx_in(line),
        .rx_data(data), .rx_valid(valid), .rx_frame_err(frame_err));

    always @(posedge clk) if (rst_n && valid) begin
        seen = seen + 1;
        if (frame_err) errs = errs + 1;
        else if (data !== want) begin
            bad = bad + 1;
            $display("MISMATCH got %02h want %02h", data, want);
        end
    end

    task send;
        input [7:0] byte_in;
        input       good_stop;
        begin
            want = byte_in;
            line = 1'b0;                         // start
            repeat (DIVISOR) @(posedge clk);
            for (b = 0; b < 8; b = b + 1) begin  // LSB first
                line = byte_in[b];
                repeat (DIVISOR) @(posedge clk);
            end
            line = good_stop;                    // stop
            repeat (DIVISOR) @(posedge clk);
            line = 1'b1;
            repeat (DIVISOR) @(posedge clk);
        end
    endtask

    initial begin
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (DIVISOR) @(posedge clk);

        send(8'h41, 1'b1);       // 'A'
        send(8'h00, 1'b1);
        send(8'hFF, 1'b1);
        send(8'h5A, 1'b1);
        if (seen !== 4 || errs !== 0) begin
            bad = bad + 1;
            $display("MISMATCH four clean frames gave seen=%0d errs=%0d", seen, errs);
        end

        // A one-clock glitch on an idle line must not become a frame.
        line = 1'b0; @(posedge clk); line = 1'b1;
        repeat (DIVISOR * 12) @(posedge clk);
        if (seen !== 4) begin
            bad = bad + 1;
            $display("MISMATCH a glitch was read as a frame");
        end

        // A frame whose stop bit is low must be flagged, not delivered.
        send(8'h3C, 1'b0);
        if (errs !== 1) begin
            bad = bad + 1;
            $display("MISMATCH framing error not reported (errs=%0d)", errs);
        end

        if (bad == 0)
            $display("PASS: %0d frames, glitch rejected, framing error caught", seen);
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
