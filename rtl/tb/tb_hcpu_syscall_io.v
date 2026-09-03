// tb_hcpu_syscall_io.v — I/O through the kernel, and only through it.
//
// PRINT is the machine's one output path and it was not privileged, so user
// mode wrote to the serial line with nothing in between. That is unmediated
// I/O, not absent I/O, and it is the worse of the two.
//
// The check is deliberately two-sided. Something coming out proves nothing on
// its own: the user asks for 42 and tries to print 99 directly, so the wire
// must carry 42 and must never carry 99.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_syscall_io;
    localparam integer BAUD   = 115200;
    localparam real    BIT_NS = 1_000_000_000.0 / BAUD;
    // 18.5 ns half-period is the board's 27 MHz oscillator. The other benches
    // here use #5 and get away with it because they never look at the wire;
    // this one decodes it, so a 100 MHz clock would push every character out
    // 3.7x too fast and the receiver would read noise. It did.
    localparam real    HALF_PERIOD = 18.5;

    reg clk = 0, rst_n = 0;
    wire uart_txd;
    integer errors = 0;

    always #HALF_PERIOD clk = ~clk;

    hcpu_gowin_top #(.USE_PLL(0), .BAUD(BAUD), .PROGRAM_HEX("syscall_io.hex")) dut (
        .clk_27m(clk), .btn_rst_n(rst_n),
        .uart_rxd(1'b1), .uart_txd(uart_txd), .led());

    // An independent receiver, timed from BIT_NS rather than from the design.
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

    task check(input cond, input [255:0] what);
        begin
            if (!cond) begin
                $display("  GAGAL: %0s", what);
                errors = errors + 1;
            end else
                $display("  ok   : %0s", what);
        end
    endtask

    integer k;
    reg saw_42, saw_99;

    initial begin
        repeat (4) @(negedge clk); rst_n = 1;
        #(BIT_NS * 40 * 10);          // room for a few characters at 115200

        saw_42 = 1'b0;
        saw_99 = 1'b0;
        for (k = 0; k + 1 < count; k = k + 1) begin
            if (received[k] == "4" && received[k+1] == "2") saw_42 = 1'b1;
            if (received[k] == "9" && received[k+1] == "9") saw_99 = 1'b1;
        end

        $display("");
        $display("  syscall I/O di atas pipeline:");
        $display("    R8  = %0d  (lanjut setelah PRINT ditolak)", dut.u_hcpu.u_regfile.gpr[8]);
        $display("    R10 = %0d  (handler menolak PRINT langsung)", dut.u_hcpu.u_regfile.gpr[10]);
        $display("    R7  = %0d  (syscall kembali)", dut.u_hcpu.u_regfile.gpr[7]);
        $display("    R1  = %0d  (hasil panggilan)", dut.u_hcpu.u_regfile.gpr[1]);
        $display("    byte di kabel = %0d", count);
        $display("");

        check(dut.u_hcpu.u_regfile.gpr[10] == 1,
              "PRINT langsung dari mode user harus menjebak");
        check(dut.u_hcpu.u_regfile.gpr[8] == 1,
              "handler harus melangkahi instruksi yang ditolak");
        check(dut.u_hcpu.u_regfile.gpr[7] == 1, "syscall harus kembali");
        check(dut.u_hcpu.u_regfile.gpr[1] == 1, "panggilan harus dilayani");
        check(saw_42, "42 harus sampai ke kabel — kernel mencetak untuk user");
        check(!saw_99, "99 tidak boleh pernah sampai ke kabel");

        if (errors == 0)
            $display("tb_hcpu_syscall_io: SEMUA LULUS (6 pemeriksaan)");
        else begin
            $display("tb_hcpu_syscall_io: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
