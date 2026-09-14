// tb_hcpu_sdio.v — the controller against a card that can say no.
//
// M4.2.1 through M4.2.4 in simulation: detect and initialise, read a sector,
// write a sector, read it back and compare. The other side of the wire is
// rtl/tb/sd_card_model.v, which checks CRC7 on every frame it receives,
// refuses to answer a transfer command unless CMD7 selected it, and reports
// "still busy" three times before ACMD41 succeeds.
//
// ── the clock is faster here than on the board, on purpose ──────
// INIT_HZ is 400 kHz on hardware because the card requires it. At 27 MHz that
// is 67 system clocks per half period, and the identification sequence alone
// would be a quarter of a million clocks of simulation that prove nothing
// about the protocol. The divider is a parameter precisely so this bench can
// shorten it; the board build uses the real one, and rtl/fpga/gowin is where
// that number has to be right.
//
// ── what each check is defending ────────────────────────────────
// The four that matter most are about the card's side of the conversation,
// not the controller's:
//
//   n_bad_crc7 == 0    every command frame was well formed. A controller
//                      whose CRC7 is wrong gets silence from a real card and
//                      a timeout from this one -- never a wrong answer.
//   n_acmd41 == 4      the retry loop actually ran. A controller that gave up
//                      after one ACMD41 would pass every other check here.
//   n_cmd7 == 1        the card was selected. Skip it and CMD17 is ignored.
//   n_crc_reject == 0  the block the host sent arrived intact by the card's
//                      own arithmetic, not the host's.
`timescale 1ns/1ps

module tb_hcpu_sdio;

    // The gap the controller leaves before each command. Eight is the
    // standard's minimum and the default; the sabotage run overrides it from
    // the command line -- `iverilog -Ptb_hcpu_sdio.NCC=7` -- so that breaking
    // the gate needs no edit to any file and leaves no edit to undo.
    parameter integer NCC = 8;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;               // 100 MHz sim clock, 27 MHz claimed

    reg         start = 1'b0;
    reg  [1:0]  op = 2'd0;
    reg  [31:0] sector = 32'd0;
    wire        busy, ok, err, card_ready;
    wire [3:0]  err_code;

    reg         buf_we = 1'b0;
    reg  [6:0]  buf_addr = 7'd0;
    reg  [31:0] buf_wdata = 32'd0;
    wire [31:0] buf_rdata;

    wire sd_clk;
    wire host_cmd_out, host_cmd_oe, host_dat_out, host_dat_oe;
    wire card_cmd_out, card_cmd_oe, card_dat_out, card_dat_oe;

    // Open-drain with a pull-up, which is what the card sees. Resolving it
    // here rather than inside either module is what lets both be simulated
    // without a bus arbiter.
    wire cmd_line = host_cmd_oe ? host_cmd_out :
                    card_cmd_oe ? card_cmd_out : 1'b1;
    wire dat_line = host_dat_oe ? host_dat_out :
                    card_dat_oe ? card_dat_out : 1'b1;

    hcpu_sdio #(
        .CLK_HZ  (27_000_000),
        .INIT_HZ ( 6_750_000),
        .XFER_HZ (13_500_000),
        .TIMEOUT (   200_000),
        .NCC_CLOCKS (NCC)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .start(start), .op(op), .sector(sector),
        .busy(busy), .ok(ok), .err(err), .err_code(err_code),
        .card_ready(card_ready), .div_sel(2'd0),
        .buf_we(buf_we), .buf_re(1'b1), .buf_addr(buf_addr),
        .buf_wdata(buf_wdata), .buf_rdata(buf_rdata),
        .sd_clk(sd_clk),
        .cmd_out(host_cmd_out), .cmd_oe(host_cmd_oe), .cmd_in(cmd_line),
        .dat_out(host_dat_out), .dat_oe(host_dat_oe), .dat_in(dat_line)
    );

    sd_card_model #(
        .SECTORS     (16),
        .ACMD41_BUSY (3),
        .HIGH_CAP    (1'b1)
    ) u_card (
        .sd_clk(sd_clk),
        .cmd_line(cmd_line), .cmd_out(card_cmd_out), .cmd_oe(card_cmd_oe),
        .dat_line(dat_line), .dat_out(card_dat_out), .dat_oe(card_dat_oe)
    );

    integer errors = 0;
    task check(input cond, input [255:0] what);
        begin
            if (!cond) begin
                $display("  GAGAL: %0s", what);
                errors = errors + 1;
            end else
                $display("  ok   : %0s", what);
        end
    endtask

    task run_op;
        input [1:0]  which;
        input [31:0] lba;
        begin
            @(negedge clk);
            op = which; sector = lba; start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            wait (busy == 1'b1);
            wait (busy == 1'b0);
            @(negedge clk);
        end
    endtask

    integer i, b;
    reg [31:0] expect_w;
    reg [31:0] got_w;
    reg        read_match, card_match, back_match;

    initial begin
        $dumpfile("tb_hcpu_sdio.vcd");
        $dumpvars(0, tb_hcpu_sdio);

        $display("=== tb_hcpu_sdio: kartu TF, SDIO 1-bit ===");

        // A pattern that is different in every byte of every word, so a
        // controller that dropped or duplicated a byte cannot land on it.
        for (i = 0; i < 512; i = i + 1)
            u_card.mem[5*512 + i] = (i * 7 + 3) & 8'hFF;

        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (4) @(negedge clk);

        // ── M4.2.1 — detect and initialise ──────────────────────
        run_op(2'd1, 32'd0);
        check(ok && !err, "init: kartu menjawab");
        if (err) $display("  err_code = %0d", err_code);
        check(u_card.n_cmd0 >= 1, "CMD0 sampai ke kartu");
        check(u_card.n_cmd8 == 1, "CMD8 sekali, pola 0xAA");
        check(u_card.n_acmd41 == 4, "ACMD41 diulang sampai siap");
        check(u_card.n_cmd2 == 1 && u_card.n_cmd3 == 1
           && u_card.n_cmd7 == 1 && u_card.n_cmd16 == 1,
              "CMD2 CMD3 CMD7 CMD16 lengkap");
        check(dut.ccs == 1'b1, "OCR bit30: alamat blok");

        // ── M4.2.2 — read a sector ──────────────────────────────
        run_op(2'd2, 32'd5);
        check(ok && !err, "read sektor 5 selesai");
        if (err) $display("  err_code = %0d", err_code);

        read_match = 1'b1;
        for (i = 0; i < 128; i = i + 1) begin
            expect_w = {u_card.mem[5*512 + i*4 + 0],
                        u_card.mem[5*512 + i*4 + 1],
                        u_card.mem[5*512 + i*4 + 2],
                        u_card.mem[5*512 + i*4 + 3]};
            if (dut.sbuf[i] !== expect_w) begin
                if (read_match)
                    $display("  kata %0d: %08h bukan %08h",
                             i, dut.sbuf[i], expect_w);
                read_match = 1'b0;
            end
        end
        check(read_match, "128 kata sama dengan kartu");

        // ── M4.2.3 — write a sector ─────────────────────────────
        // A different pattern, so a write that quietly re-sent the read
        // buffer would be caught rather than confirmed.
        for (i = 0; i < 128; i = i + 1) begin
            @(negedge clk);
            buf_addr  = i[6:0];
            buf_wdata = 32'hC05_00000 + i;
            buf_we    = 1'b1;
            @(negedge clk);
            buf_we    = 1'b0;
        end

        run_op(2'd3, 32'd9);
        check(ok && !err, "write sektor 9 selesai");
        if (err) $display("  err_code = %0d", err_code);

        card_match = 1'b1;
        for (i = 0; i < 128; i = i + 1) begin
            expect_w = 32'hC05_00000 + i;
            got_w    = {u_card.mem[9*512 + i*4 + 0],
                        u_card.mem[9*512 + i*4 + 1],
                        u_card.mem[9*512 + i*4 + 2],
                        u_card.mem[9*512 + i*4 + 3]};
            if (got_w !== expect_w) begin
                if (card_match)
                    $display("  kartu kata %0d: %08h bukan %08h",
                             i, got_w, expect_w);
                card_match = 1'b0;
            end
        end
        check(card_match, "kartu menyimpan yang dikirim");
        check(u_card.n_crc_reject == 0, "kartu tak menolak CRC data");

        // ── M4.2.4 — read it back ───────────────────────────────
        run_op(2'd2, 32'd9);
        back_match = (ok && !err);
        for (i = 0; i < 128; i = i + 1)
            if (dut.sbuf[i] !== (32'hC05_00000 + i)) back_match = 1'b0;
        check(back_match, "baca ulang: sama persis");

        // Every frame the card heard was well formed. This is the check that
        // fails first when CRC7 is wrong, and it fails silently on hardware.
        check(u_card.n_bad_crc7 == 0, "tiap frame lolos CRC7 kartu");

        // ── Ncc: the clocks every command is owed ───────────────
        // These two exist because the board taught them. The controller sent
        // CMD8 with a gap of ZERO after CMD0 and CMD55 with a gap of ZERO
        // after a response; this model answered anyway, twelve checks stayed
        // green, and a healthy SDHC card said nothing at all -- E_CMD8, a full
        // 100 ms timeout, four runs on a Tang Nano 20K.
        //
        // The first check is the boundary itself, in clocks, so a regression
        // says what it was rather than only that something was refused. The
        // second is the card's own refusal count, which catches every other
        // boundary at once -- including the ones after a response, which the
        // first measurement of this defect missed entirely.
        $display("  gap sesudah CMD0 = %0d clock, kartu menuntut %0d, ditolak = %0d",
                 u_card.gap_after_cmd0, u_card.NCC_MIN, u_card.n_ncc_reject);
        check(u_card.gap_after_cmd0 >= 8, "CMD0 -> CMD8: 8 clock atau lebih");
        check(u_card.n_ncc_reject == 0,   "tak ada perintah datang kepagian");

        if (errors == 0)
            $display("tb_hcpu_sdio: SEMUA LULUS (14 pemeriksaan)");
        else
            $display("tb_hcpu_sdio: %0d GAGAL", errors);
        $finish;
    end

    // A run that hangs is a failure with no message. This is the message.
    initial begin
        #20_000_000;
        $display("tb_hcpu_sdio: GAGAL -- waktu habis, controller menggantung");
        $finish;
    end
endmodule
