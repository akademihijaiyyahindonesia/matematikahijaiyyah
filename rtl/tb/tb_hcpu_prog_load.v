// tb_hcpu_prog_load.v -- SYSCALL 9: a container on the card becomes an image.
//
// A user process asks, the kernel reads the card, and instruction memory holds
// the program afterwards -- relocated to the address its header names. The
// image is compared against the assembler's own output at that address
// (rtl/scripts/build_container.py --image), not against a second transcription
// of the loader's arithmetic.
//
// The card is filled here rather than by running sd_writer.hasm first: that
// program has its own bench, which already proves those exact bytes reach
// those exact sectors. This one answers a different question.
//
// LOAD_ADDR is 0x900, and the reason is measured: the shell image is 1,245
// words and the probe sits at 0x800, so anything below 0x820 would load on top
// of the kernel that is doing the loading.
//
// What it checks:
//   1  SYSCALL 9 answers 1
//   2  instruction memory at 0x900 is the program, word for word, relocated
//   3  the word before and the word after are still zero -- WORDS words, no more
//   4  the relocation table landed at 0x300-0x37F, where the owner put it
//   5  a PROGRAM_ID no VALID entry names is refused, and answers 0

`timescale 1ns/1ps

module tb_hcpu_prog_load;
    localparam real    HALF_PERIOD = 18.5;          // 27 MHz
    localparam integer BAUD        = 115200;
    localparam integer LOAD_ADDR   = 12'h900;
    localparam integer WORDS       = 51;            // subroutine.hasm
    localparam integer RELOC_CNT   = 14;
    localparam integer C_WORDS     = 7 + RELOC_CNT + WORDS;
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
        $display("=== tb_hcpu_prog_load: SYSCALL 9 memuat program dari kartu ===");
        $readmemh("progload_container.hex", container);
        $readmemh("progload_want.hex", want);

        // After the card model's own initial block has zeroed its memory.
        #1;
        put_word(TABLE_SEC, 0, 32'd1);              // PROGRAM_ID
        put_word(TABLE_SEC, 1, 32'd1);              // FLAGS: bit 0 VALID
        put_word(TABLE_SEC, 2, IMAGE_SEC);          // START_SECTOR
        put_word(TABLE_SEC, 3, 32'd1);              // SECTOR_COUNT
        for (i = 0; i < C_WORDS; i = i + 1)
            put_word(IMAGE_SEC, i, container[i]);

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
            $display("tb_hcpu_prog_load: SEMUA LULUS (7 pemeriksaan)");
        else begin
            $display("tb_hcpu_prog_load: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
