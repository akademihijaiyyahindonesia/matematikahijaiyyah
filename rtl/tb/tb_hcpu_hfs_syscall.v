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
    reg [31:0] card_magic, card_version, card_exists, card_size, blk, cw, rw;
    integer k, same, nonzero;

    function [31:0] card_word(input integer sector, input integer w);
        card_word = {u_card.mem[sector*512 + w*4 + 0], u_card.mem[sector*512 + w*4 + 1],
                     u_card.mem[sector*512 + w*4 + 2], u_card.mem[sector*512 + w*4 + 3]};
    endfunction

    always #5 clk = ~clk;

    // ── a card in the slot ──────────────────────────────────────
    // Blank at start. shell.hasm mounts HFS from the card at boot, so a board with a
    // card present is the shape this bench must run in. A blank card answers
    // init, reads back zeros, fails MAGIC, and the filesystem starts empty --
    // "card present, never formatted", which is also a real board.
    wire sd_clk;
    wire card_cmd_out, card_cmd_oe, card_dat_out, card_dat_oe;
    wire sd_cmd;
    wire [3:0] sd_dat;
    pullup (sd_cmd);
    pullup (sd_dat[0]);
    assign sd_cmd    = card_cmd_oe ? card_cmd_out : 1'bz;
    assign sd_dat[0] = card_dat_oe ? card_dat_out : 1'bz;

    sd_card_model #(
        .SECTORS     (16),
        .ACMD41_BUSY (3),
        .HIGH_CAP    (1'b1)
    ) u_card (
        .sd_clk(sd_clk),
        .cmd_line(sd_cmd), .cmd_out(card_cmd_out), .cmd_oe(card_cmd_oe),
        .dat_line(sd_dat[0]), .dat_out(card_dat_out), .dat_oe(card_dat_oe)
    );

    hcpu_gowin_core #(.USE_PLL(0), .PROGRAM_HEX("shell_hfs.hex")) dut (
        .clk_27m(clk), .btn_rst_n(rst_n),
        .uart_rxd(1'b1), .uart_txd(uart_txd), .led(),
        .sd_clk(sd_clk), .sd_cmd(sd_cmd), .sd_dat(sd_dat));

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

        // ── and on the card ───────────────────────────────────────
        // CREATE and WRITE commit through to the card. Read the card's own
        // memory, not the RAM table, so a commit that never happened cannot
        // pass: sector 1 must carry HFS1 v1 and file 0's entry, and sector 2's
        // first eighteen words must equal the block the RAM holds for file 0.
        card_magic   = card_word(1, 0);
        card_version = card_word(1, 1);
        card_exists  = card_word(1, 2);
        card_size    = card_word(1, 3);
        blk          = dut.u_hcpu.u_dataram.mem[12'hE82];
        same = 1; nonzero = 0;
        for (k = 0; k < 18; k = k + 1) begin
            cw = card_word(2, k);
            rw = dut.u_hcpu.u_dataram.mem[blk + k];
            if (cw !== rw) same = 0;
            if (cw != 0) nonzero = 1;
        end
        $display("  kartu: magic=%08h versi=%0d ada=%0d size=%0d", card_magic, card_version, card_exists, card_size);
        $display("  kartu sektor 2 == blok RAM berkas 0 ? %0d", same);
        $display("");

        check(card_magic == 32'h48465331, "kartu: MAGIC HFS1");
        check(card_version == 1,           "kartu: VERSION 1");
        check(card_exists == 1 && card_size == 18, "kartu: entri berkas 0");
        check(same == 1 && nonzero == 1,   "kartu: data == blok RAM");

        if (errors == 0)
            $display("tb_hcpu_hfs_syscall: SEMUA LULUS (9 pemeriksaan)");
        else begin
            $display("tb_hcpu_hfs_syscall: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
