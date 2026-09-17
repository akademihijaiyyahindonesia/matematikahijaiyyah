// tb_hcpu_sd_writer.v -- a container crosses the wire and lands on the card.
//
// Stage 2A needs an image ON the card before a loader can fetch one. This
// drives the real serial pin at the real baud into sd_writer.hasm and then
// reads the card model's own memory, byte for byte, rather than believing what
// the program says about itself.
//
// The container is test_bsm at 0x100, built by rtl/scripts/build_container.py
// and framed by rtl/scripts/send_program.py: the same two host tools that feed
// a board, so the bench cannot pass with a wire format the board would refuse.
//
// What it checks, and why each one:
//   1  sector 17 carries the container words, big-endian, word for word
//   2  the rest of sector 17 is zero -- a sector is written whole, and a
//      writer that left the old contents there would corrupt the next image
//   3  sector 16 holds the table entry: PROGRAM_ID 1, FLAGS 1 (VALID),
//      START_SECTOR 17, SECTOR_COUNT 1
//   4  sector 18 is untouched: the writer wrote what it was given and no more
//   5  the wire says 1 then 1 -- written, one sector

`timescale 1ns/1ps

module tb_hcpu_sd_writer;
    localparam real    HALF_PERIOD = 18.5;          // 27 MHz
    localparam integer BAUD        = 115200;
    localparam real    BIT_NS      = 1_000_000_000.0 / BAUD;
    localparam integer N_WORDS     = 16;            // 7 header + 0 reloc + 9 program
    localparam integer N_BYTES     = 4 + 4 * N_WORDS;

    reg  clk_27m = 1'b0;
    reg  btn_rst_n = 1'b0;
    reg  uart_rxd = 1'b1;
    wire uart_txd;
    wire [5:0] led;

    always #HALF_PERIOD clk_27m = ~clk_27m;

    wire sd_clk;
    wire card_cmd_out, card_cmd_oe, card_dat_out, card_dat_oe;
    wire sd_cmd;
    wire [3:0] sd_dat;
    pullup (sd_cmd);
    pullup (sd_dat[0]);
    assign sd_cmd    = card_cmd_oe ? card_cmd_out : 1'bz;
    assign sd_dat[0] = card_dat_oe ? card_dat_out : 1'bz;

    // Twenty-four sectors: the writer starts at 17, so a sixteen-sector card
    // would refuse the write for the wrong reason.
    sd_card_model #(
        .SECTORS     (24),
        .ACMD41_BUSY (3),
        .HIGH_CAP    (1'b1)
    ) u_card (
        .sd_clk(sd_clk),
        .cmd_line(sd_cmd), .cmd_out(card_cmd_out), .cmd_oe(card_cmd_oe),
        .dat_line(sd_dat[0]), .dat_out(card_dat_out), .dat_oe(card_dat_oe)
    );

    hcpu_gowin_core #(
        .USE_PLL     (0),
        .BAUD        (BAUD),
        .PROGRAM_HEX ("sd_writer.hex")
    ) u_board (
        .clk_27m(clk_27m), .btn_rst_n(btn_rst_n),
        .uart_rxd(uart_rxd), .uart_txd(uart_txd), .led(led),
        .sd_clk(sd_clk), .sd_cmd(sd_cmd), .sd_dat(sd_dat));

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

    task send_byte(input [7:0] b);
        integer i;
        begin
            uart_rxd = 1'b0;  #BIT_NS;
            for (i = 0; i < 8; i = i + 1) begin
                uart_rxd = b[i]; #BIT_NS;
            end
            uart_rxd = 1'b1;  #BIT_NS;
        end
    endtask

    // ── the wire, read back as digits ───────────────────────────
    reg [8*4-1:0] digits = 0;
    integer       n_digits = 0, bit_i;
    reg [7:0]     shifted;

    initial begin
        forever begin
            @(negedge uart_txd);
            #(BIT_NS * 1.5);
            for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
                shifted[bit_i] = uart_txd;
                #BIT_NS;
            end
            // Only the first two: the wrapper prints CYCLES=<hex> after
            // HALT and those digits are not the program speaking.
            if (shifted >= "0" && shifted <= "9" && n_digits < 2) begin
                digits = {digits[8*3-1:0], shifted};
                n_digits = n_digits + 1;
            end
        end
    end

    reg [7:0]  payload [0:255];
    reg [31:0] want    [0:N_WORDS-1];
    integer    i, cyc, bad, sector17, sector16, sector18;
    reg [31:0] got;

    function [31:0] card_word(input integer sector, input integer index);
        begin
            card_word = {u_card.mem[sector*512 + index*4 + 0],
                         u_card.mem[sector*512 + index*4 + 1],
                         u_card.mem[sector*512 + index*4 + 2],
                         u_card.mem[sector*512 + index*4 + 3]};
        end
    endfunction

    initial begin
        $display("=== tb_hcpu_sd_writer: container lewat kabel, mendarat di kartu ===");
        $readmemh("container_payload.txt", payload);
        $readmemh("container.hex", want);

        repeat (20) @(posedge clk_27m);
        btn_rst_n = 1'b1;

        // The card's init runs first, so the writer is not listening yet. Give
        // it room before the first byte: the UART holds exactly one byte, and
        // a byte sent while the program is inside hal_sd_run is a byte lost.
        repeat (200000) @(posedge clk_27m);

        for (i = 0; i < N_BYTES; i = i + 1)
            send_byte(payload[i]);

        // Wait for the TABLE, which sd_writer.hasm writes last: while sector
        // 16 is still zero the image may be half written.
        for (cyc = 0; cyc < 4000000 && card_word(16, 0) == 0; cyc = cyc + 1)
            @(posedge clk_27m);
        $display("  tabel program muncul sesudah %0d siklus", cyc);
        repeat (200000) @(posedge clk_27m);       // and the two prints

        // ── 1: the container, word for word ─────────────────────
        bad = 0;
        for (i = 0; i < N_WORDS; i = i + 1) begin
            got = card_word(17, i);
            if (got !== want[i]) begin
                if (bad == 0)
                    $display("  kata %0d: kartu %08h, seharusnya %08h",
                             i, got, want[i]);
                bad = bad + 1;
            end
        end
        check(bad == 0, "sektor 17 = container");

        // ── 2: and nothing else in that sector ──────────────────
        bad = 0;
        for (i = N_WORDS; i < 128; i = i + 1)
            if (card_word(17, i) !== 32'd0) bad = bad + 1;
        check(bad == 0, "sisa sektor 17 nol");

        // ── 3: the table entry ──────────────────────────────────
        check(card_word(16, 0) == 32'd1,  "PROGRAM_ID = 1");
        check(card_word(16, 1) == 32'd1,  "FLAGS bit 0 = VALID");
        check(card_word(16, 2) == 32'd17, "START_SECTOR = 17");
        check(card_word(16, 3) == 32'd1,  "SECTOR_COUNT = 1");
        bad = 0;
        for (i = 4; i < 128; i = i + 1)
            if (card_word(16, i) !== 32'd0) bad = bad + 1;
        check(bad == 0, "entri lain kosong");

        // ── 4: nothing beyond what it was given ─────────────────
        bad = 0;
        for (i = 0; i < 128; i = i + 1)
            if (card_word(18, i) !== 32'd0) bad = bad + 1;
        check(bad == 0, "sektor 18 tak tersentuh");

        // ── 5: what the wire said ───────────────────────────────
        $display("  kabel: \"%0s\"", digits);
        check(n_digits == 2 && digits[15:0] == "11", "kabel: 1 lalu 1");

        if (errors == 0)
            $display("tb_hcpu_sd_writer: SEMUA LULUS (9 pemeriksaan)");
        else begin
            $display("tb_hcpu_sd_writer: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
