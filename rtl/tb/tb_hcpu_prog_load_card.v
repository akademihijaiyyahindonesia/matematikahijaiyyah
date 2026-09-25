// tb_hcpu_prog_load_card.v -- SYSCALL 9 on a card image handed in from outside.
//
// The owner's condition for P6, 26 September 2026: the builder, the Python
// loader and the HCPU loader must not hold three readings of CHECKSUM32. So
// this bench decides nothing about the card. It takes one image -- sectors 16
// to 23, 128 words each, written by tests/test_integrity/test_checksum32.py from
// the same card the Python loader in rtl/scripts/build_container.py judged --
// puts it on the card model most significant byte first, the order
// rtl/hcpu_sdio.v reads, and reports what the real loader answered:
//
//     vvp tb_hcpu_prog_load_card.vvp +CARD=<file of 1,024 hex words>
//     DONE=1 ANSWER=<SYSCALL 9 for PROGRAM_ID 1> ABSENT=<for PROGRAM_ID 2>
//
// The kernel doing the loading is the shell with rtl/tb/prog_load_probe.hasm
// injected, exactly as tb_hcpu_prog_load.v runs it. Not in `make all`: one run
// is one case, and the test is what compares.

`timescale 1ns/1ps

module tb_hcpu_prog_load_card;
    localparam real    HALF_PERIOD = 18.5;          // 27 MHz
    localparam integer BAUD        = 115200;
    localparam integer FIRST_SEC   = 16;
    localparam integer SECS        = 8;             // 16..23, all the model has

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
        .SECTORS     (FIRST_SEC + SECS),
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
        .PROGRAM_HEX ("shell_progload.hex")
    ) dut (
        .clk_27m(clk), .btn_rst_n(rst_n),
        .uart_rxd(1'b1), .uart_txd(uart_txd), .led(led),
        .sd_clk(sd_clk), .sd_cmd(sd_cmd), .sd_dat(sd_dat));

    reg [31:0]    card [0:SECS*128-1];
    reg [8*512:1] card_file;
    integer       i, cyc;
    reg [31:0]    done_w, answer, absent;

    task put_word(input integer sector, input integer index, input [31:0] w);
        begin
            u_card.mem[sector*512 + index*4 + 0] = w[31:24];
            u_card.mem[sector*512 + index*4 + 1] = w[23:16];
            u_card.mem[sector*512 + index*4 + 2] = w[15:8];
            u_card.mem[sector*512 + index*4 + 3] = w[7:0];
        end
    endtask

    initial begin
        if (!$value$plusargs("CARD=%s", card_file)) begin
            $display("tb_hcpu_prog_load_card: +CARD=<file> is required");
            $fatal(1);
        end
        for (i = 0; i < SECS*128; i = i + 1) card[i] = 32'd0;
        $readmemh(card_file, card);

        // After the card model's own initial block has zeroed its memory.
        #1;
        for (i = 0; i < SECS*128; i = i + 1)
            put_word(FIRST_SEC + i / 128, i % 128, card[i]);

        repeat (4) @(negedge clk); rst_n = 1'b1;

        done_w = 0;
        for (cyc = 0; cyc < 20000 && done_w != 32'h5A; cyc = cyc + 1) begin
            repeat (1000) @(posedge clk);
            done_w = dut.u_hcpu.u_dataram.mem[12'h100];
        end
        answer = dut.u_hcpu.u_dataram.mem[12'h101];
        absent = dut.u_hcpu.u_dataram.mem[12'h102];
        $display("DONE=%0d ANSWER=%0d ABSENT=%0d", done_w == 32'h5A ? 1 : 0,
                 answer, absent);
        $finish;
    end
endmodule
