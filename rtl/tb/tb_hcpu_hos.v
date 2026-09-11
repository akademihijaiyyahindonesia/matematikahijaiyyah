// tb_hcpu_hos.v — HOS on the real pipeline: heap, guarded HFS, HAR.
//
// The same seven checks tests/test_integrity/test_hos.py runs in the
// interpreter, run here through fetch/decode/execute/memory/writeback.
// HOS's routines are software over the ISA, so this bench is really proving
// the pipeline's CALL/RET, LOAD/STORE and SHR/XOR paths compose correctly
// across ~30 subroutine calls in a row, which nothing before this exercised
// at this depth -- and, since CSET landed, that hos_fs_read rebuilds a live
// H-Reg on the pipeline rather than only in the interpreter.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_hos;
    reg clk = 0, rst_n = 0;
    wire uart_txd;
    integer errors = 0;

    always #5 clk = ~clk;

    hcpu_gowin_top #(.USE_PLL(0), .PROGRAM_HEX("hos_demo.hex")) dut (
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

    integer distinct, reuse, dbl_free, hfs_ok, hfs_rebuilt, hfs_corrupt, har_c0;

    initial begin
        repeat (4) @(negedge clk); rst_n = 1;
        repeat (30000) @(posedge clk);

        distinct    = dut.u_hcpu.u_dataram.mem[12'h100];
        reuse       = dut.u_hcpu.u_dataram.mem[12'h101];
        dbl_free    = dut.u_hcpu.u_dataram.mem[12'h102];
        hfs_ok      = dut.u_hcpu.u_dataram.mem[12'h103];
        hfs_corrupt = dut.u_hcpu.u_dataram.mem[12'h104];
        har_c0      = dut.u_hcpu.u_dataram.mem[12'h105];
        hfs_rebuilt = dut.u_hcpu.u_dataram.mem[12'h106];

        $display("");
        $display("  HOS di atas pipeline:");
        $display("    dua alokasi berbeda alamat = %0d", distinct);
        $display("    bebas-lalu-realloc pakai ulang = %0d", reuse);
        $display("    double-free ditolak = %0d", dbl_free);
        $display("    HFS: huruf kanonik round-trip = %0d", hfs_ok);
        $display("    HFS: H-Reg dibangun ulang lewat CSET = %0d", hfs_rebuilt);
        $display("    HFS: vektor korup ditolak = %0d", hfs_corrupt);
        $display("    HAR: komponen-0 huruf 10 = %0d", har_c0);
        $display("");

        check(distinct == 1, "dua alokasi 5 kata harus beda alamat");
        check(reuse == 1, "bebas lalu realloc ukuran sama harus pakai ulang alamat");
        check(dbl_free == 0, "double-free harus ditolak (hasil 0)");  // two frees, no realloc between
        check(hfs_ok == 1, "huruf kanonik harus tersimpan dan terbaca identik");
        check(hfs_rebuilt == 1, "baca harus mengembalikan H-Reg hidup yang lulus guard-nya sendiri");
        check(hfs_corrupt == 1, "vektor korup (indeks 31) harus ditolak, tak pernah tersimpan");
        check(har_c0 == 1, "HAR harus mengembalikan komponen 0 huruf 10 yang benar");

        if (errors == 0)
            $display("tb_hcpu_hos: SEMUA LULUS (7 pemeriksaan)");
        else begin
            $display("tb_hcpu_hos: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
