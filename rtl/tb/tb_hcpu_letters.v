// tb_hcpu_letters.v — the twenty-eight letter opcodes, on the pipeline.
//
// They were listed as implemented and were not. RTL_IMPLEMENTED is a Python
// set: it says which opcodes the RTL is meant to carry, which is a statement
// of intent that nothing was checking. No bench and no program had ever
// executed one, so a second `default:` in hcpu_execute.v's codex case -- which
// iverilog silently resolved to `default: ;` -- left all twenty-eight writing
// nothing, and every suite still passed.
//
// Both numbers here are borrowed rather than invented. 112 is the squared norm
// of Ba+Sin+Mim that tb_gowin_top already reads out of the explicit
// HLOAD/HCADD path, so the letters have to agree with a route that was proved
// separately. 10,814 is all twenty-eight accumulated, cross-checked against
// the interpreter.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_letters;
    reg clk = 0, rst_n = 0;
    wire uart_txd;
    integer errors = 0;
    integer bsm, all28;

    always #5 clk = ~clk;

    hcpu_gowin_top #(.USE_PLL(0), .PROGRAM_HEX("letters.hex")) dut (
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
        repeat (2000) @(posedge clk);

        bsm   = dut.u_hcpu.u_dataram.mem[12'h100];
        all28 = dut.u_hcpu.u_dataram.mem[12'h101];

        $display("");
        $display("  instruksi huruf di atas pipeline:");
        $display("    ||Ba+Sin+Mim||^2 = %0d   (jalur HLOAD/HCADD memberi 112)", bsm);
        $display("    ||28 huruf||^2   = %0d", all28);
        $display("");

        check(bsm != 0, "opcode huruf harus menulis sesuatu sama sekali");
        check(bsm == 112,
              "tiga huruf harus setuju dengan jalur HLOAD/HCADD yang sudah terbukti");
        check(all28 == 10814, "penyapuan 28 huruf harus setuju dengan penafsir");

        if (errors == 0)
            $display("tb_hcpu_letters: SEMUA LULUS (3 pemeriksaan)");
        else begin
            $display("tb_hcpu_letters: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
