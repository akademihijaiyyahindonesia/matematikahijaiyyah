// tb_hcpu_trap_hreg.v — does a codex register survive a trap?
//
// One number, read out of data memory: 1 if the caller's H0 crossed a trap
// intact, 0 if the handler's single HLOAD reached it.
//
// ── what this is for ────────────────────────────────────────────
// HFS's calling convention is hybit. hos_fs_write takes its vector in H0 and
// hos_fs_read returns one there, so promoting those routines from library
// calls to syscalls puts a 144-bit register across a trap boundary. Whether
// it arrives is not a detail of the filesystem -- it decides whether the
// filesystem can have a kernel interface at all.
//
// The process context in rtl/programs/shell.hasm saves R0-R15 and FLAGS.
// It saves no H-register, and there are sixteen.
//
// ── this bench must be able to answer BOTH ways ─────────────────
// It is written before the fix, and it is expected to FAIL here: that is the
// point. A guard that has never been seen red is a guard nobody has tested
// (R3). rtl/programs/trap_hreg.hasm carries the reasoning for using Kaf --
// the only letter whose H* is 1, so a vector rebuilt from zeros cannot
// compare equal by accident, a blind spot this repository has recorded twice.

`timescale 1ns/1ps

module tb_hcpu_trap_hreg;

    reg clk = 0;
    reg rst_n = 0;
    wire uart_txd;
    integer errors = 0;
    integer verdict;

    always #5 clk = ~clk;

    hcpu_gowin_core #(.USE_PLL(0), .PROGRAM_HEX("trap_hreg.hex")) dut (
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
        $display("=== tb_hcpu_trap_hreg: H0 melewati trap, atau tidak ===");
        repeat (4) @(negedge clk); rst_n = 1;
        repeat (3000) @(posedge clk);

        verdict = dut.u_hcpu.u_dataram.mem[12'h100];

        $display("");
        $display("  handler menjalankan SATU instruksi codex (HLOAD H0, 2).");
        $display("  vonis di 0x100 = %0d", verdict);
        $display("    1 = H0 pemanggil utuh     0 = handler mencapainya");
        $display("");

        check(verdict !== 32'hxxxxxxxx, "program harus menulis vonisnya");
        check(verdict == 1, "H0 pemanggil selamat");

        if (errors == 0)
            $display("tb_hcpu_trap_hreg: SEMUA LULUS (2 pemeriksaan)");
        else begin
            $display("tb_hcpu_trap_hreg: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
