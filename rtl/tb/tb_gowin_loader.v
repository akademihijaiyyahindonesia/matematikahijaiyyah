// ============================================================================
// The boot path, proved in RTL — tb_gowin_loader.v
// ============================================================================
//
// The interpreter already loads a program over the wire and runs it. That is
// worth something, and it is not the same claim: the interpreter has no UART
// timing, no BRAM latency, no pipeline, and no write port that could land a
// word one address late. This drives the actual serial pin at the actual baud
// into the actual design.
//
// The board is built with loader.hex rather than program.hex, which is what
// the bridge means in practice: the bitstream holds the loader, and every
// program after it arrives through here.

`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_gowin_loader;
    localparam real    HALF_PERIOD = 18.5;          // 27 MHz
    localparam integer BAUD        = 115200;
    localparam real    BIT_NS      = 1_000_000_000.0 / BAUD;

    reg  clk_27m = 1'b0;
    reg  btn_rst_n = 1'b0;
    reg  uart_rxd = 1'b1;                            // idle high
    wire uart_txd;
    wire [5:0] led;

    always #HALF_PERIOD clk_27m = ~clk_27m;

    hcpu_gowin_top #(
        .USE_PLL      (0),
        .BAUD         (BAUD),
        .PROGRAM_HEX  ("loader.hex")
    ) u_board (
        .clk_27m   (clk_27m),
        .btn_rst_n (btn_rst_n),
        .uart_rxd  (uart_rxd),
        .uart_txd  (uart_txd),
        .led       (led)
    );

    integer errors = 0;
    task check(input cond, input [255:0] what);
        begin
            if (!cond) begin $display("  GAGAL: %0s", what); errors = errors + 1; end
        end
    endtask

    // ── transmit one byte, LSB first, as a real UART does ────────
    task send_byte(input [7:0] b);
        integer i;
        begin
            uart_rxd = 1'b0;  #BIT_NS;                // start
            for (i = 0; i < 8; i = i + 1) begin
                uart_rxd = b[i]; #BIT_NS;             // LSB first
            end
            uart_rxd = 1'b1;  #BIT_NS;                // stop
        end
    endtask

    reg [7:0] payload [0:255];
    integer   n_bytes, i;

    initial begin
        $readmemh("payload.txt", payload);
        n_bytes = 16;                                  // 4 count + 3 words

        repeat (20) @(posedge clk_27m);
        btn_rst_n = 1'b1;
        repeat (200) @(posedge clk_27m);

        for (i = 0; i < n_bytes; i = i + 1)
            send_byte(payload[i]);

        // The loader spins on RX_STATUS, so it consumes bytes as fast as they
        // arrive and then hands over. Give it room to finish and run.
        repeat (20000) @(posedge clk_27m);

        // The loaded program set two registers. Peek at the file rather than
        // the wire: it proves the words landed at the right addresses, which
        // is the thing a one-off write-port bug would break.
        check(u_board.u_hcpu.u_regfile.gpr[9] == 32'd42,
              "R9 harus 42 — program yang dimuat tidak berjalan");
        check(u_board.u_hcpu.u_regfile.gpr[10] == 32'd7,
              "R10 harus 7");

        // And it landed where the loader said, not one word off.
        // And it landed where the loader said, word for word. A write port
        // that asserted one cycle late would put every word at the address
        // after its own -- a program that almost works.
        check(u_board.imem[64] == 32'h0490_002a, "kata 0 salah alamat");
        check(u_board.imem[65] == 32'h04a0_0007, "kata 1 salah alamat");
        check(u_board.imem[66] == 32'h0100_0000, "kata 2 salah alamat");
        check(u_board.u_hcpu.u_mmio.imem_waddr == 67,
              "alamat tulis harus maju sendiri, tepat tiga kali");


        if (errors == 0) $display("PASS: tb_gowin_loader — program dimuat lewat kabel dan berjalan");
        else             $display("FAIL: tb_gowin_loader — %0d gagal", errors);
        $finish;
    end
endmodule
