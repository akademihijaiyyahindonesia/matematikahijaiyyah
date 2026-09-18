// tb_hcpu_sd_writer.v -- a container crosses the wire, one acknowledged sector
// at a time, and lands on the card.
//
// The container is test_hfs at 0x200: 437 words, four sectors -- the exact
// container that left the board silent on 18 September 2026, when the writer
// had no acknowledgement and lost bytes while it wrote a sector. The owner's fix
// is an ACK per sector, and this bench behaves like the host that fix needs:
// it waits for the board's `0` (card initialised, listening), sends 128 words,
// waits for the running count, and only then sends the next 128.
//
// It is built by rtl/scripts/build_container.py and framed exactly as
// rtl/scripts/send_container.py frames it, so the bench cannot pass with a
// wire protocol the board would refuse. The card model's own memory is read
// afterwards, byte for byte, rather than believing the program's report.
//
// What it checks:
//   1  the acknowledgements are 0 1 2 3 4, in order, and then 1 4
//   2  sectors 17-20 carry the container words, big-endian, word for word
//   3  the rest of sector 20 is zero -- a sector is written whole
//   4  sector 16 holds the table entry: 1, VALID, 17, 4, and nothing else
//   5  sector 21 is untouched

`timescale 1ns/1ps

module tb_hcpu_sd_writer;
    localparam real    HALF_PERIOD = 18.5;          // 27 MHz
    localparam integer BAUD        = 115200;
    localparam real    BIT_NS      = 1_000_000_000.0 / BAUD;
    localparam integer N_WORDS     = 437;           // test_hfs @0x200: 7 + 12 + 418
    localparam integer N_SECTORS   = (N_WORDS + 127) / 128;   // 4

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

    // ── the wire, as lines of digits ────────────────────────────
    // Every line the program prints is a number, and the host counts lines.
    // Only the digits before the wrapper's CYCLES report are kept.
    reg [8*8-1:0] digits = 0;
    integer       n_digits = 0, lines = 0, bit_i;
    reg [7:0]     shifted;

    initial begin
        forever begin
            @(negedge uart_txd);
            #(BIT_NS * 1.5);
            for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
                shifted[bit_i] = uart_txd;
                #BIT_NS;
            end
            if (shifted == 8'h0A && lines < 8)
                lines = lines + 1;
            else if (shifted >= "0" && shifted <= "9" && n_digits < 7 && lines < 7) begin
                digits = {digits[8*7-1:0], shifted};
                n_digits = n_digits + 1;
            end
        end
    end

    // Wait for the board's next line, bounded: a board that never answers
    // must fail here, not hang the suite.
    task wait_lines(input integer want);
        integer cyc;
        begin
            for (cyc = 0; cyc < 8000000 && lines < want; cyc = cyc + 1)
                @(posedge clk_27m);
        end
    endtask

    reg [7:0]  payload [0:4 + 4*N_WORDS - 1];
    reg [31:0] want    [0:N_WORDS-1];
    integer    i, s, first, last, bad;
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
        $display("=== tb_hcpu_sd_writer: empat sektor, satu ACK per sektor ===");
        $readmemh("container_payload.txt", payload);
        $readmemh("container.hex", want);

        repeat (20) @(posedge clk_27m);
        btn_rst_n = 1'b1;

        // The host speaks only after the board says it is listening.
        wait_lines(1);
        $display("  papan siap sesudah %0d baris", lines);

        for (s = 0; s < N_SECTORS; s = s + 1) begin
            first = (s == 0) ? 0 : 4 + 512 * s;
            last  = 4 + 512 * (s + 1);
            if (last > 4 + 4 * N_WORDS) last = 4 + 4 * N_WORDS;
            for (i = first; i < last; i = i + 1)
                send_byte(payload[i]);
            wait_lines(s + 2);                      // ACK s+1
        end
        wait_lines(N_SECTORS + 3);                  // then "1", then the count
        repeat (20000) @(posedge clk_27m);

        // ── 1: what the wire said ───────────────────────────────
        $display("  kabel: \"%0s\"", digits);
        check(n_digits == 7 && digits[55:0] == "0123414", "ACK 0 1 2 3 4, lalu 1 4");

        // ── 2 and 3: the container, word for word, sector by sector
        bad = 0;
        for (i = 0; i < N_WORDS; i = i + 1) begin
            got = card_word(17 + i / 128, i % 128);
            if (got !== want[i]) begin
                if (bad == 0)
                    $display("  kata %0d: kartu %08h, seharusnya %08h", i, got, want[i]);
                bad = bad + 1;
            end
        end
        check(bad == 0, "sektor 17-20 = container");
        bad = 0;
        for (i = N_WORDS % 128; i < 128; i = i + 1)
            if (card_word(17 + N_SECTORS - 1, i) !== 32'd0) bad = bad + 1;
        check(bad == 0, "sisa sektor 20 nol");

        // ── 4: the table entry ──────────────────────────────────
        check(card_word(16, 0) == 32'd1 && card_word(16, 1) == 32'd1
              && card_word(16, 2) == 32'd17 && card_word(16, 3) == N_SECTORS,
              "tabel: 1, VALID, 17, 4");
        bad = 0;
        for (i = 4; i < 128; i = i + 1)
            if (card_word(16, i) !== 32'd0) bad = bad + 1;
        check(bad == 0, "entri lain kosong");

        // ── 5: nothing beyond what it was given ─────────────────
        bad = 0;
        for (i = 0; i < 128; i = i + 1)
            if (card_word(17 + N_SECTORS, i) !== 32'd0) bad = bad + 1;
        check(bad == 0, "sektor 21 tak tersentuh");

        if (errors == 0)
            $display("tb_hcpu_sd_writer: SEMUA LULUS (6 pemeriksaan)");
        else begin
            $display("tb_hcpu_sd_writer: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
