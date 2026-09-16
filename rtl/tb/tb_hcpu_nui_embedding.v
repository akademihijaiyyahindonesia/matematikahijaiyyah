// tb_hcpu_nui_embedding.v — NUI's physics embedding sum, on the real pipeline.
//
// nui_embedding.hasm computes the same five numbers
// src/hijaiyyah/nui/features.py's vector_features() computes in Python for
// Jim+Kha accumulated -- titik, garis, lengkung, theta, rho -- using only
// opcodes that existed before this bench (letter accumulation, CGET,
// ADD/SUB). No new RTL. This proves the winning embedding from the
// physics-vs-baseline comparison in NUI/README.md runs as real hardware,
// not just as a Python feature extractor.
//
// Checked two ways: by peeking the pipeline's own data RAM through
// hierarchy (what a testbench can see), and by decoding the actual UART
// bytes off `uart_txd` with an independently-timed receiver (what a person
// with a Tang Nano and a serial terminal would see). The second is the
// answer to "what does it look like on the board" -- five digits, one per
// line, then the wrapper's own CYCLES= report.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_nui_embedding;
    localparam integer OSC_HZ     = 27_000_000;
    localparam integer BAUD       = 115200;
    localparam real    BIT_NS     = 1_000_000_000.0 / BAUD;
    // A real 27 MHz clock, not an arbitrary #5. The UART TX divisor inside
    // the DUT is CLK_HZ/BAUD clock CYCLES, so an independent receiver timed
    // in real nanoseconds (BIT_NS below) only decodes correctly if a DUT
    // cycle really is 1/27,000,000 s -- tb_gowin_top.v's own fix for
    // exactly this, rediscovered here the same way the first time: bytes
    // came out garbled because #5 gives 100 MHz, transmitting each bit in
    // 234 cycles * 10 ns = 2,340 ns against the 8,681 ns BIT_NS expected.
    localparam real HALF_PERIOD = 18.5;

    reg clk = 0, rst_n = 0;
    wire uart_txd;
    integer errors = 0;

    always #HALF_PERIOD clk = ~clk;

    hcpu_gowin_core #(.USE_PLL(0), .BAUD(BAUD), .PROGRAM_HEX("nui_embedding.hex")) dut (
        .clk_27m(clk), .btn_rst_n(rst_n),
        .uart_rxd(1'b1), .uart_txd(uart_txd), .led());

    task check(input [31:0] got, input [31:0] want, input [255:0] what);
        begin
            if (got !== want) begin
                $display("  GAGAL: %0s -- got %0d want %0d", what, got, want);
                errors = errors + 1;
            end else
                $display("  ok   : %0s = %0d", what, got);
        end
    endtask

    integer titik, garis, lengkung, theta, rho;

    // ── Independent UART receiver, timed from BIT_NS, not from the RTL ──
    // (rtl/tb/tb_gowin_top.v's own pattern -- it only decodes correctly if
    // the transmitter really is at 115200 baud, which is the whole point).
    reg [7:0] received [0:63];
    integer   count = 0;
    integer   bit_i;
    reg [7:0] shifted;

    initial begin
        forever begin
            @(negedge uart_txd);
            #(BIT_NS * 1.5);
            for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
                shifted[bit_i] = uart_txd;
                #BIT_NS;
            end
            if (count < 64) begin
                received[count] = shifted;
                count = count + 1;
            end
        end
    end

    integer i;

    initial begin
        repeat (4) @(negedge clk); rst_n = 1;
        // Five PRINTs, two bytes each (digit + '\n'), each byte 10 bit
        // times at 234 clocks/bit (27 MHz / 115200 baud) -- transmission
        // alone is ~23,400 clocks; this margin covers compute too.
        repeat (60000) @(posedge clk);

        titik    = dut.u_hcpu.u_dataram.mem[12'h100];
        garis    = dut.u_hcpu.u_dataram.mem[12'h101];
        lengkung = dut.u_hcpu.u_dataram.mem[12'h102];
        theta    = dut.u_hcpu.u_dataram.mem[12'h103];
        rho      = dut.u_hcpu.u_dataram.mem[12'h104];

        $display("");
        $display("  NUI physics embedding, Jim+Kha, di atas pipeline:");

        // Ground truth: python3 -c "from hijaiyyah.core.master_table import
        // MASTER_TABLE as M; from hijaiyyah.nui.features import
        // vector_features as v; print(v([a+b for a,b in
        // zip(M.get_by_char('ج').vector, M.get_by_char('خ').vector)]))"
        check(titik,    2, "titik");
        check(garis,    2, "garis");
        check(lengkung, 2, "lengkung");
        check(theta,    6, "theta");
        check(rho,      6, "rho");

        $display("");
        $display("  Yang muncul di kabel serial (115200 baud), %0d byte:", count);
        $write("    ");
        for (i = 0; i < count; i = i + 1) begin
            if (received[i] == 8'h0A) $write("\\n");
            else $write("%c", received[i]);
        end
        $display("");

        // PRINT sends each digit then a bare '\n' (0x0A) -- five
        // single-digit values, so exactly "2\n2\n2\n6\n6\n" (10 bytes)
        // before the wrapper's own idle-triggered CYCLES= report.
        if (count < 10) begin
            $display("  GAGAL: kurang dari 10 byte muncul sebelum tenggat");
            errors = errors + 1;
        end else begin
            check(received[0], "2", "byte serial 0 (titik)");
            check(received[1], 8'h0A, "byte serial 1 (newline)");
            check(received[2], "2", "byte serial 2 (garis)");
            check(received[3], 8'h0A, "byte serial 3 (newline)");
            check(received[4], "2", "byte serial 4 (lengkung)");
            check(received[5], 8'h0A, "byte serial 5 (newline)");
            check(received[6], "6", "byte serial 6 (theta)");
            check(received[7], 8'h0A, "byte serial 7 (newline)");
            check(received[8], "6", "byte serial 8 (rho)");
            check(received[9], 8'h0A, "byte serial 9 (newline)");
        end

        if (errors == 0)
            $display("tb_hcpu_nui_embedding: SEMUA LULUS (10 pemeriksaan)");
        else begin
            $display("tb_hcpu_nui_embedding: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
