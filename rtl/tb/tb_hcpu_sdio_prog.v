// tb_hcpu_sdio_prog.v — the card, reached by a program instead of by wires.
//
// tb_hcpu_sdio.v drives hcpu_sdio's own ports: start, op, sector, buf_we. It
// proves the protocol and it bypasses the machine entirely -- no CPU, no MMIO
// decode, no LOAD or STORE. Nothing in this repository had ever reached the
// card the way software will have to, which is the difference between a
// controller that works and a controller that can be used.
//
// This bench runs rtl/programs/sdio_write.hasm on the real pipeline, through
// the board wrapper, with the card model on the pads. Everything the program
// does to the card it does with LOAD and STORE at 0xFE0-0xFE4.
//
// ── the checks that do not depend on the program's own opinion ──
// Four of the eight read the serial line, which is the program marking its own
// work. The other four ask the card model and the wrapper instead:
//
//   mem[512..]      the block the card actually holds, compared here against
//                   the pattern -- not against what the program printed
//   n_bad_crc7 == 0 every command frame the card received was well formed. A
//                   wrong CRC7 gets silence from a real card, and silence
//                   looks like a missing card rather than a bad frame.
//   n_write == 1    the write happened once. A retry loop that wrote twice
//                   would pass every value check and wear the card.
//   n_read  == 1    and so did the read-back.
//
// ── the pads are resolved here, with the pull-ups the .cst asks for ──
// hcpu_gowin_top drives sd_cmd and sd_dat[0] as inouts and releases them with
// 1'bz so the card can answer. `pullup` is what makes the released state high,
// and on the board that is PULL_MODE=UP in hcpu_gowin.cst. Without it a
// released line floats to x here, and every response the card sends would be
// read as x rather than as data -- which is the simulation twin of the
// btn_rst_n defect the .cst comments record.
//
// ── the init clock is the board's, not a shortened one ──────────
// tb_hcpu_sdio.v overrides INIT_HZ to 6.75 MHz because 400 kHz costs a quarter
// of a million clocks that prove nothing about the protocol. This bench cannot
// and should not: hcpu_mmio passes only CLK_HZ down, so what runs here is the
// divider the board will use. It costs about four milliseconds of simulated
// time, and it is the only way the number that goes to the card is the number
// that went through the synthesis.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_sdio_prog;
    localparam real    HALF_PERIOD = 18.5;       // 27 MHz
    localparam integer BAUD        = 115200;
    localparam real    BIT_NS      = 1_000_000_000.0 / BAUD;
    localparam integer SECTOR      = 1;          // the one sdio_write.hasm uses

    reg  clk_27m = 1'b0;
    reg  btn_rst_n = 1'b0;
    wire uart_txd;
    wire [5:0] led;

    always #HALF_PERIOD clk_27m = ~clk_27m;

    // ── the card's two open lines ───────────────────────────────
    wire sd_clk;
    wire card_cmd_out, card_cmd_oe, card_dat_out, card_dat_oe;

    wire sd_cmd;
    wire [3:0] sd_dat;
    pullup (sd_cmd);
    pullup (sd_dat[0]);

    assign sd_cmd    = card_cmd_oe ? card_cmd_out : 1'bz;
    assign sd_dat[0] = card_dat_oe ? card_dat_out : 1'bz;

    hcpu_gowin_top #(
        .USE_PLL      (0),
        .BAUD         (BAUD),
        .PROGRAM_HEX  ("sdio_write.hex")
    ) u_board (
        .clk_27m   (clk_27m),
        .btn_rst_n (btn_rst_n),
        .uart_rxd  (1'b1),
        .uart_txd  (uart_txd),
        .led       (led),
        .sd_clk    (sd_clk),
        .sd_cmd    (sd_cmd),
        .sd_dat    (sd_dat)
    );

    sd_card_model #(
        .SECTORS     (16),
        .ACMD41_BUSY (3),
        .HIGH_CAP    (1'b1)
    ) u_card (
        .sd_clk(sd_clk),
        .cmd_line(sd_cmd), .cmd_out(card_cmd_out), .cmd_oe(card_cmd_oe),
        .dat_line(sd_dat[0]), .dat_out(card_dat_out), .dat_oe(card_dat_oe)
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

    // An independent receiver, timed from BIT_NS and not from the design.
    reg [7:0] got [0:63];
    integer   count = 0;
    integer   bit_i;
    reg [7:0] shifted;

    initial begin
        forever begin
            @(negedge uart_txd);
            #(BIT_NS * 1.5);
            for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
                shifted[bit_i] = uart_txd;
                #BIT_NS;
            end
            if (count < 64) begin
                got[count] = shifted;
                count = count + 1;
            end
        end
    end

    integer i;
    reg [31:0] want_w, got_w;
    reg        stored_match;

    initial begin
        $dumpfile("tb_hcpu_sdio_prog.vcd");
        $dumpvars(0, tb_hcpu_sdio_prog);

        $display("=== tb_hcpu_sdio_prog: kartu lewat LOAD/STORE ===");

        repeat (20) @(posedge clk_27m);
        btn_rst_n = 1'b1;

        // Four milliseconds at 27 MHz. Initialisation at 400 kHz is most of
        // it: 80 power-up clocks, eight commands, and ACMD41 three times.
        repeat (600000) @(posedge clk_27m);

        $write("  keluar: ");
        for (i = 0; i < count; i = i + 1)
            if (got[i] == 8'h0A) $write(" ");
            else                 $write("%0s", got[i]);
        $display(" (%0d byte)", count);

        // 1 \n 1 \n 1 \n 1 \n 1 0 \n, then the wrapper's CYCLES= epilogue.
        check(count >= 11, "empat jawaban keluar");
        if (count >= 11) begin
            check(got[0] == "1", "init: kartu menjawab");
            check(got[2] == "1", "write: kartu terima blok");
            check(got[4] == "1", "read: sektor kembali");
            check(got[6] == "1", "verify: 128 kata cocok");
            check(got[8] == "1" && got[9] == "0", "status akhir: ok, siap");
        end

        // ── the card's own side, not the program's ──────────────
        // Word i is i + 1000, most significant byte first: the packing the
        // controller documents, checked here against the bytes the card
        // actually holds rather than against the buffer it read back from.
        stored_match = 1'b1;
        for (i = 0; i < 128; i = i + 1) begin
            want_w = 32'd1000 + i;
            got_w  = {u_card.mem[SECTOR*512 + i*4 + 0],
                      u_card.mem[SECTOR*512 + i*4 + 1],
                      u_card.mem[SECTOR*512 + i*4 + 2],
                      u_card.mem[SECTOR*512 + i*4 + 3]};
            if (got_w !== want_w) begin
                if (stored_match)
                    $display("  kartu kata %0d: %08h bukan %08h",
                             i, got_w, want_w);
                stored_match = 1'b0;
            end
        end
        check(stored_match, "kartu menyimpan pola itu");

        $display("  kartu: cmd0=%0d cmd8=%0d acmd41=%0d cmd7=%0d read=%0d write=%0d crc7bad=%0d",
                 u_card.n_cmd0, u_card.n_cmd8, u_card.n_acmd41,
                 u_card.n_cmd7, u_card.n_read, u_card.n_write,
                 u_card.n_bad_crc7);

        check(u_card.n_bad_crc7 == 0,  "tiap frame lolos CRC7");
        check(u_card.n_write == 1,     "satu tulis, bukan dua");
        check(u_card.n_read == 1,      "satu baca, bukan dua");

        if (errors == 0)
            $display("tb_hcpu_sdio_prog: SEMUA LULUS (9 pemeriksaan)");
        else
            $display("tb_hcpu_sdio_prog: %0d GAGAL", errors);
        $finish;
    end
endmodule
