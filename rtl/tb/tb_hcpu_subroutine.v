// tb_hcpu_subroutine.v — CALL and RET on the pipeline.
//
// The spec reserved 0x2E/0x2F long ago and marked them software-only, which is
// why every program in rtl/programs/ is written straight -- kernel.hasm
// included. They resolve in Execute like a branch, because the return address
// sits on its own combinationally-read stack.
//
// The last check is the one that pins the design decision rather than the
// feature: `messy` leaves the DATA stack with an extra PUSH on it and still
// returns. On a shared stack that RET would jump to 5.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_subroutine;
    reg clk = 0, rst_n = 0;
    wire uart_txd;
    integer errors = 0;
    integer flat, nested, deep, messy;

    always #5 clk = ~clk;

    hcpu_gowin_core #(.USE_PLL(0), .PROGRAM_HEX("subroutine.hex")) dut (
        .clk_27m(clk), .btn_rst_n(rst_n),
        .uart_rxd(1'b1), .uart_txd(uart_txd), .led());

    task check(input cond, input [255:0] what);
        begin
            if (!cond) begin
                $display("  GAGAL: %0s", what);
                errors = errors + 1;
            end else
                $display("  ok   : %0s", what);
        end
    endtask

    initial begin
        repeat (4) @(negedge clk); rst_n = 1;
        repeat (3000) @(posedge clk);

        flat   = dut.u_hcpu.u_dataram.mem[12'h100];
        nested = dut.u_hcpu.u_dataram.mem[12'h101];
        deep   = dut.u_hcpu.u_dataram.mem[12'h102];
        messy  = dut.u_hcpu.u_dataram.mem[12'h103];

        $display("");
        $display("  subrutin di atas pipeline:");
        $display("    tiga panggilan datar = %0d   (21)", flat);
        $display("    bersarang            = %0d   (111)", nested);
        $display("    delapan tingkat      = %0d   (8)", deep);
        $display("    stack data timpang   = %0d   (3)", messy);
        $display("");

        check(flat   == 21,  "tiga panggilan datar harus kembali tiga kali");
        check(nested == 111, "sarang harus kembali ke pemanggil yang benar");
        check(deep   == 8,   "delapan tingkat harus terurai berurutan");
        check(messy  == 3,
              "PUSH timpang tidak boleh merusak alamat kembali");

        if (errors == 0)
            $display("tb_hcpu_subroutine: SEMUA LULUS (4 pemeriksaan)");
        else begin
            $display("tb_hcpu_subroutine: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
