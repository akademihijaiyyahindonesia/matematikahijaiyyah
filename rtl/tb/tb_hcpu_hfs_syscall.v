// tb_hcpu_hfs_syscall.v — a process creates, writes and reads a file through
// the kernel, and gets back the vector it wrote.
//
// The first bench to issue HFS_CREATE, HFS_WRITE and HFS_READ at all.
// rtl/programs/shell.hasm serves them and has no process that calls them, so
// until this bench existed the whole suite could be green while every one of
// those arms was unexercised -- and one of them could not have worked: the HOS
// heap was never initialised, so HFS_CREATE would have refused every file.
//
// The image is the shipped shell with ONE word changed: pid 0's first
// instruction jumps to rtl/tb/hfs_syscall_probe.hasm, assembled at
// 0x400 by rtl/scripts/inject_probe.py. The syscall arms, HOS and the H0 save
// routines are the shell's own. The probe's header says what it proves and
// what it deliberately does not.

`timescale 1ns/1ps

module tb_hcpu_hfs_syscall;

    reg clk = 0;
    reg rst_n = 0;
    wire uart_txd;
    integer errors = 0;
    integer i;
    reg [31:0] done_w, create_w, write_w, read_w, verdict_w;

    always #5 clk = ~clk;

    hcpu_gowin_core #(.USE_PLL(0), .PROGRAM_HEX("shell_hfs.hex")) dut (
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
        $display("=== tb_hcpu_hfs_syscall: create, write, read lewat kernel ===");
        repeat (4) @(negedge clk); rst_n = 1;

        // Poll for the probe's done marker rather than guessing a cycle count:
        // pid 0 shares the machine with the shell and is preempted by the
        // timer, so when it finishes depends on the schedule, not the probe.
        done_w = 0;
        for (i = 0; i < 4000 && done_w != 32'h5A; i = i + 1) begin
            repeat (1000) @(posedge clk);
            done_w = dut.u_hcpu.u_dataram.mem[12'h100];
        end

        create_w  = dut.u_hcpu.u_dataram.mem[12'h101];
        write_w   = dut.u_hcpu.u_dataram.mem[12'h102];
        read_w    = dut.u_hcpu.u_dataram.mem[12'h103];
        verdict_w = dut.u_hcpu.u_dataram.mem[12'h104];

        $display("");
        $display("  selesai sesudah %0d ribu siklus", i);
        $display("  HFS_CREATE = %0d   HFS_WRITE = %0d   HFS_READ = %0d", create_w, write_w, read_w);
        $display("  vektor terbaca == Kaf yang ditulis ? %0d", verdict_w);
        $display("");

        check(done_w == 32'h5A,  "probe selesai");
        check(create_w == 1,     "HFS_CREATE membuat berkas");
        check(write_w == 1,      "HFS_WRITE menulis");
        check(read_w == 1,       "HFS_READ menemukan berkas");
        check(verdict_w == 1,    "vektor kembali utuh (Kaf)");

        if (errors == 0)
            $display("tb_hcpu_hfs_syscall: SEMUA LULUS (5 pemeriksaan)");
        else begin
            $display("tb_hcpu_hfs_syscall: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
