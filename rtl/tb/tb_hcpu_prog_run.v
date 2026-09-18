// tb_hcpu_prog_run.v -- the program off the card runs, and says its own numbers.
//
// tb_hcpu_prog_load.v proves instruction memory holds the right words by
// reading the simulated memory. A board cannot do that: there is no read port.
// So this bench proves the same thing the way a board must -- by running the
// loaded program and reading the wire.
//
// The container is test_from_card.hasm at 0x900, written for this: its loop is
// closed with `JMP`, the one jump in this ISA that carries an ABSOLUTE address
// (a conditional branch is relative -- `JNE` assembles to 0x24000FFD, an offset
// of -3, so it needs no relocation at all). Built for 0x900 its `JMP` carries
// 0x901; loaded without relocation it would carry 0x001 and run into whatever
// sits there. So `1 2 3` on the wire means the words arrived AND the address
// inside one of them was fixed.

`timescale 1ns/1ps

module tb_hcpu_prog_run;
    localparam real    HALF_PERIOD = 18.5;          // 27 MHz
    localparam integer BAUD        = 115200;
    localparam real    BIT_NS      = 1_000_000_000.0 / BAUD;
    localparam integer C_WORDS     = 15;            // 7 header + 1 reloc + 7 program
    localparam integer IMAGE_SEC   = 17;
    localparam integer TABLE_SEC   = 16;

    reg  clk = 1'b0;
    reg  rst_n = 1'b0;
    wire uart_txd;
    wire [5:0] led;

    always #HALF_PERIOD clk = ~clk;

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
        .PROGRAM_HEX ("test_prog_run.hex")
    ) dut (
        .clk_27m(clk), .btn_rst_n(rst_n),
        .uart_rxd(1'b1), .uart_txd(uart_txd), .led(led),
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

    // ── the wire, digits only: the eight answers, then CYCLES ───
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
            // Only the first three: the wrapper prints CYCLES=<hex> after HALT
            // and those digits are not the program speaking.
            if (shifted >= "0" && shifted <= "9" && n_digits < 3) begin
                digits = {digits[8*3-1:0], shifted};
                n_digits = n_digits + 1;
            end
        end
    end

    reg [31:0] container [0:C_WORDS-1];
    integer    i, cyc;

    task put_word(input integer sector, input integer index, input [31:0] w);
        begin
            u_card.mem[sector*512 + index*4 + 0] = w[31:24];
            u_card.mem[sector*512 + index*4 + 1] = w[23:16];
            u_card.mem[sector*512 + index*4 + 2] = w[15:8];
            u_card.mem[sector*512 + index*4 + 3] = w[7:0];
        end
    endtask

    initial begin
        $display("=== tb_hcpu_prog_run: program dari kartu berjalan sendiri ===");
        $readmemh("progrun_container.hex", container);

        #1;                                          // after the card's own init
        put_word(TABLE_SEC, 0, 32'd1);               // PROGRAM_ID
        put_word(TABLE_SEC, 1, 32'd1);               // FLAGS: VALID
        put_word(TABLE_SEC, 2, IMAGE_SEC);           // START_SECTOR
        put_word(TABLE_SEC, 3, 32'd1);               // SECTOR_COUNT
        for (i = 0; i < C_WORDS; i = i + 1)
            put_word(IMAGE_SEC, i, container[i]);

        repeat (4) @(negedge clk); rst_n = 1'b1;

        for (cyc = 0; cyc < 4000000 && n_digits < 3; cyc = cyc + 1)
            @(posedge clk);
        $display("  tiga angka sesudah %0d siklus", cyc);
        $display("  kabel: \"%0s\"", digits);

        check(n_digits == 3, "tiga angka keluar");
        check(digits[23:0] == "123", "1 2 3 dari kartu");

        if (errors == 0)
            $display("tb_hcpu_prog_run: SEMUA LULUS (2 pemeriksaan)");
        else begin
            $display("tb_hcpu_prog_run: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
