// tb_hcpu_hfs_persist.v — a file written in one boot is read in the next, and
// the card is the only thing that carried it.
//
// Boot 1 creates file 0 and writes Kaf into it. The CPU is then held in reset
// and EVERY word of data RAM is set to zero -- the volatile memory a power loss
// takes away -- while the card model keeps its sectors. Boot 2 mounts HFS from
// the card at startup and reads file 0 back.
//
// Why zero the RAM by hand: hcpu_dataram.v clears only in an `initial` block,
// not on reset. Skip that and the first boot's HFS table is still at 0xE80, so
// the second boot finds the file without the card having anything to do with
// it. The sabotage that removes hos_fs_mount from boot must turn this bench
// red; it only can if the RAM really was lost.
//
// What this does NOT prove: that the physical card on the Tang Nano 20K keeps
// its sectors through a real power cycle. The card model cannot lose power.
// Stage 1 of the gate to KV260 closes on that physical test, not on this one.

`timescale 1ns/1ps

module tb_hcpu_hfs_persist;

    reg clk = 0;
    reg rst_n = 0;
    wire uart_txd;
    integer errors = 0;
    integer i, boot1_k, boot2_k;
    reg [31:0] done_w, phase1, create1, write1, phase2;

    always #5 clk = ~clk;

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

    hcpu_gowin_core #(.USE_PLL(0), .PROGRAM_HEX("shell_persist.hex")) dut (
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

    task wait_done(output integer thousands);
        begin
            done_w = 0;
            for (thousands = 0; thousands < 20000 && done_w != 32'h5A;
                 thousands = thousands + 1) begin
                repeat (1000) @(posedge clk);
                done_w = dut.u_hcpu.u_dataram.mem[12'h100];
            end
        end
    endtask

    initial begin
        $display("=== tb_hcpu_hfs_persist: berkas melewati reboot, lewat kartu ===");

        // ── boot 1 ───────────────────────────────────────────────
        repeat (4) @(negedge clk); rst_n = 1;
        wait_done(boot1_k);
        phase1  = dut.u_hcpu.u_dataram.mem[12'h101];
        create1 = dut.u_hcpu.u_dataram.mem[12'h102];
        write1  = dut.u_hcpu.u_dataram.mem[12'h103];
        $display("  boot 1 (%0d ribu siklus): fase=%0d create=%0d write=%0d",
                 boot1_k, phase1, create1, write1);

        // ── power lost: reset held, volatile memory gone ────────
        @(negedge clk); rst_n = 0;
        repeat (4) @(negedge clk);
        for (i = 0; i < 4096; i = i + 1)
            dut.u_hcpu.u_dataram.mem[i] = 32'd0;
        @(negedge clk); rst_n = 1;

        // ── boot 2 ───────────────────────────────────────────────
        wait_done(boot2_k);
        phase2 = dut.u_hcpu.u_dataram.mem[12'h101];
        $display("  boot 2 (%0d ribu siklus): fase=%0d  (2 = ditemukan dan sama)",
                 boot2_k, phase2);
        $display("");

        check(phase1 == 1,                 "boot 1: berkas belum ada");
        check(create1 == 1 && write1 == 1, "boot 1: create dan write");
        check(done_w == 32'h5A,            "boot 2 selesai");
        check(phase2 == 2,                 "boot 2: Kaf dari kartu");

        if (errors == 0)
            $display("tb_hcpu_hfs_persist: SEMUA LULUS (4 pemeriksaan)");
        else begin
            $display("tb_hcpu_hfs_persist: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
