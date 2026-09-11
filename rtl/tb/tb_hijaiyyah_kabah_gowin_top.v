// tb_hijaiyyah_kabah_gowin_top.v — the narrowed interface, over real UART framing.
//
// hijaiyyah_kabah_top.v is already proven against cube.py directly
// (tb_hijaiyyah_kabah_top.v, bit-serial). What is new here is the wrapper's
// OWN logic: a host that only has a UART, sending 128 bytes with real
// start/data/stop framing, and reading 200 bytes back the same way -- never
// touching bit_in, phase, or out_state directly. If this passes, the 1,600-
// bit port is provably gone without the underlying behaviour changing: the
// same message through the wire produces the same state cube.py computes
// for it (rtl/tb/gen_kabah_uart_want.py), just moved across ten pins
// instead of 1,665.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_kabah_gowin_top;

    localparam integer CLK_HZ  = 27_000_000;
    localparam integer BAUD    = 115200;
    localparam integer DIVISOR = CLK_HZ / BAUD;   // matches hcpu_uart_rx/tx exactly

    reg clk = 1'b0, rst_n = 1'b0;
    reg uart_rxd = 1'b1;      // idle high
    wire uart_txd;
    wire [5:0] led;

    always #5 clk = ~clk;

    hijaiyyah_kabah_gowin_top #(.USE_PLL(0), .BAUD(BAUD)) dut (
        .clk_27m   (clk),
        .btn_rst_n (rst_n),
        .uart_rxd  (uart_rxd),
        .uart_txd  (uart_txd),
        .led       (led)
    );

    // ── Host-side UART, bit-banged against DIVISOR clocks per bit ────────
    task send_byte(input [7:0] b);
        integer k;
        begin
            uart_rxd = 1'b0;                       // start bit
            repeat (DIVISOR) @(posedge clk);
            for (k = 0; k < 8; k = k + 1) begin     // LSB first
                uart_rxd = b[k];
                repeat (DIVISOR) @(posedge clk);
            end
            uart_rxd = 1'b1;                        // stop bit
            repeat (DIVISOR) @(posedge clk);
        end
    endtask

    task recv_byte(output [7:0] v);
        integer k;
        integer guard;
        begin
            guard = 0;
            while (uart_txd !== 1'b0 && guard < 2_000_000) begin
                @(posedge clk); guard = guard + 1;
            end
            repeat (DIVISOR + DIVISOR/2) @(posedge clk);  // middle of data bit 0
            for (k = 0; k < 8; k = k + 1) begin
                v[k] = uart_txd;
                if (k < 7) repeat (DIVISOR) @(posedge clk);
            end
            repeat (DIVISOR) @(posedge clk);               // clear the stop bit
        end
    endtask

    reg [1599:0] want_state  [0:0];
    reg [1599:0] want_state2 [0:0];
    reg [7:0]    got   [0:199];
    reg [7:0]    b;
    integer      i, bad, total_bad;
    reg [7:0]    expected_byte;

    task check_frame(input [1599:0] want, input [8*8-1:0] label);
        integer j;
        begin
            bad = 0;
            for (j = 0; j < 200; j = j + 1) begin
                expected_byte = want[(1599 - j*8) -: 8];
                if (got[j] !== expected_byte) begin
                    bad = bad + 1;
                    if (bad <= 5)
                        $display("MISMATCH %0s byte %0d: got %02h want %02h", label, j, got[j], expected_byte);
                end
            end
            total_bad = total_bad + bad;
        end
    endtask

    initial begin
        $readmemh("rtl/tb/kabah_uart_want.hex",  want_state);
        $readmemh("rtl/tb/kabah_uart_want2.hex", want_state2);
        total_bad = 0;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);

        // Frame 1: bytes(range(128)) -- gen_kabah_uart_want.py's block 1.
        for (i = 0; i < 128; i = i + 1)
            send_byte(i[7:0]);
        for (i = 0; i < 200; i = i + 1) begin
            recv_byte(b);
            got[i] = b;
        end
        check_frame(want_state[0], "frame1");

        // Frame 2: bytes(128..255), sent right behind frame 1 with no reset
        // in between. `load` only ever pulses once, so this is a genuine
        // second sponge block absorbed onto the state frame 1 left behind --
        // proving the "multi-block, not re-hashed in isolation" claim in
        // this wrapper's own header rather than leaving it asserted only in
        // a comment.
        for (i = 128; i < 256; i = i + 1)
            send_byte(i[7:0]);
        for (i = 0; i < 200; i = i + 1) begin
            recv_byte(b);
            got[i] = b;
        end
        check_frame(want_state2[0], "frame2");

        if (total_bad == 0)
            $display("PASS: two 128-byte frames over simulated UART, no reset between them -> wrapper dumped exactly cube.py's chained state each time, 400/400 bytes, 10 pins wide");
        else
            $display("FAIL: %0d mismatched bytes total", total_bad);

        $finish;
    end

    initial begin
        #400_000_000;   // guard: two full round trips at this baud should never take this long
        $display("FAIL: timed out waiting for the exchange to finish");
        $finish;
    end

endmodule

`default_nettype wire
