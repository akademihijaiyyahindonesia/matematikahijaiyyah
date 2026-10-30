// tb_hcpu_prog_load_multi.v -- SYSCALL 9 across sector boundaries.
//
// tb_hcpu_prog_load.v loads a one-sector container, and so did every board run
// on 18 September 2026. Every program that matters -- the shell, HVM, the NUI
// runtime, Ka'bah and Hijrah modules -- is larger than a sector, and the
// loader's path from one sector to the next had never been run by anything.
//
// The container here is the shell itself, built for 0x900: 1,248 words, 124
// relocations, 1,379 words in all = ELEVEN sectors. It crosses both boundaries
// the loader has:
//
//   the relocation table   header 7 + table 124 = 131 words, so the table
//                          itself runs out of sector 17 into sector 18
//   the program words      then run on through sector 27
//
// and its relocations land in words spread across all of them, so the cursor
// into the table at 0x300 has to survive every sector change as well.
//
// The shell's table is 124 entries against the owner's cap of 128, measured
// again on 26 September 2026 when CHECKSUM32 went in (K-8, K-10): the loader's
// pass one lost a branch, so the shell grew three words and gave back one
// relocation (it was 1,245 and 125). That margin is worth watching, and this
// bench is where it will show first.
//
// What it checks: SYSCALL 9 answers 1; instruction memory at 0x900 is the
// assembler's output at that address, all 1,248 words; the words either side
// are untouched; all 124 table entries reached 0x300; an absent id answers 0.

`timescale 1ns/1ps

module tb_hcpu_prog_load_multi;
    localparam real    HALF_PERIOD = 18.5;          // 27 MHz
    localparam integer BAUD        = 115200;
    localparam integer LOAD_ADDR   = 12'h900;
    localparam integer WORDS       = 1505;          // shell.hasm
    localparam integer RELOC_CNT   = 124;
    localparam integer C_WORDS     = 7 + RELOC_CNT + WORDS;
    localparam integer IMAGE_SEC   = 17;
    localparam integer TABLE_SEC   = 16;
    localparam integer SEC_COUNT   = (C_WORDS + 127) / 128;   // 13

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
        .SECTORS     (32),
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

    reg [31:0] container [0:C_WORDS-1];
    reg [31:0] want      [0:WORDS-1];
    integer    i, cyc, bad;
    reg [31:0] done_w, answer, absent;

    task put_word(input integer sector, input integer index, input [31:0] w);
        begin
            u_card.mem[sector*512 + index*4 + 0] = w[31:24];
            u_card.mem[sector*512 + index*4 + 1] = w[23:16];
            u_card.mem[sector*512 + index*4 + 2] = w[15:8];
            u_card.mem[sector*512 + index*4 + 3] = w[7:0];
        end
    endtask

    initial begin
        $display("=== tb_hcpu_prog_load_multi: SYSCALL 9 melintasi sebelas sektor ===");
        $readmemh("multi_container.hex", container);
        $readmemh("multi_want.hex", want);

        // After the card model's own initial block has zeroed its memory.
        #1;
        dut.u_hcpu.u_dataram.mem[12'hED7] = 32'd1;  // Stage 2 raw container path
        put_word(TABLE_SEC, 0, 32'd1);              // PROGRAM_ID
        put_word(TABLE_SEC, 1, 32'd1);              // FLAGS: bit 0 VALID
        put_word(TABLE_SEC, 2, IMAGE_SEC);          // START_SECTOR
        put_word(TABLE_SEC, 3, SEC_COUNT);          // SECTOR_COUNT
        for (i = 0; i < C_WORDS; i = i + 1)             // word i -> sector 17 + i/128
            put_word(IMAGE_SEC + i / 128, i % 128, container[i]);

        repeat (4) @(negedge clk); rst_n = 1'b1;

        done_w = 0;
        for (cyc = 0; cyc < 20000 && done_w != 32'h5A; cyc = cyc + 1) begin
            repeat (1000) @(posedge clk);
            done_w = dut.u_hcpu.u_dataram.mem[12'h100];
        end
        answer = dut.u_hcpu.u_dataram.mem[12'h101];
        absent = dut.u_hcpu.u_dataram.mem[12'h102];
        $display("  selesai sesudah %0d ribu siklus, SYSCALL 9 menjawab %0d",
                 cyc, answer);

        check(done_w == 32'h5A, "probe selesai");
        check(answer == 32'd1,  "SYSCALL 9 = 1");

        bad = 0;
        for (i = 0; i < WORDS; i = i + 1) begin
            if (dut.imem[LOAD_ADDR + i] !== want[i]) begin
                if (bad == 0)
                    $display("  kata %0d di %03h: %08h, seharusnya %08h",
                             i, LOAD_ADDR + i, dut.imem[LOAD_ADDR + i], want[i]);
                bad = bad + 1;
            end
        end
        check(bad == 0, "imem = program, direlokasi");

        check(dut.imem[LOAD_ADDR - 1] === 32'd0, "kata sebelumnya utuh");
        check(dut.imem[LOAD_ADDR + WORDS] === 32'd0, "kata sesudahnya utuh");

        bad = 0;
        for (i = 0; i < RELOC_CNT; i = i + 1)
            if (dut.u_hcpu.u_dataram.mem[12'h300 + i] !== container[7 + i])
                bad = bad + 1;
        check(bad == 0, "tabel relokasi di 0x300");
        check(absent == 32'd0, "id yang tak ada = 0");

        if (errors == 0)
            $display("tb_hcpu_prog_load_multi: SEMUA LULUS (7 pemeriksaan)");
        else begin
            $display("tb_hcpu_prog_load_multi: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
