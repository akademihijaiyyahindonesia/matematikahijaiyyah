// tb_hcpu_hfs_lifecycle.v — create, write, read, verify.
//
// M4.1 asks for the four operations of a filesystem on the machine itself,
// before metadata, before persistence, before a service layer. This is them,
// in one file's life, read off the serial line as seven numbers:
//
//   1  create  file 3 did not exist, and now does
//   0  create  the same id again is refused -- a file is made once
//   1  write   a guarded vector committed into it
//   1  read    it comes back, and the entry says it was there
//   1  verify  what came back IS what went in, all 144 bits
//   1  verify  and it still passes its own guard
//   0  read    file 5 was never created, and says so
//
// ── the second line is why create is its own operation ──────────
// Creation used to be a side effect of the first write. That works, and it
// leaves a filesystem unable to say "this already exists" -- there was no
// operation to ask. A file that EXISTS and is empty is not a file that was
// never made, and hos_fs_create is what makes the difference sayable: size
// stays 0 until something is committed.
//
// ── the fifth line is the one that can lie, and does not ────────
// VERIFY is not "did read return something". It is CEQ against a copy taken
// BEFORE the write -- eighteen components including H*, which is not derived
// from the other seventeen and so cannot come back right by luck. And H0 is
// deliberately clobbered between the write and the read (Haa over Kaf), so a
// read that quietly handed back the register instead of the stored words
// would return Haa and this line would say so.
//
// Kaf is not an arbitrary choice: it is the ONLY letter in the table whose H*
// is 1, so it is the only one that makes the eighteenth component differ from
// the clobber's. Stored as Lam first, this bench passed while the read's last
// CSET was deleted -- the component a partial rebuild drops last was zero on
// both sides and the comparison could not see it.
//
// ── what it does not claim ──────────────────────────────────────
// Persistence. HFS is data RAM from 0xE00 up and it is gone at reset. That is
// its own item in cosmictera-build/OFF.md and it is not folded in here.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_hfs_lifecycle;
    localparam real    HALF_PERIOD = 18.5;       // 27 MHz
    localparam integer BAUD        = 115200;
    localparam real    BIT_NS      = 1_000_000_000.0 / BAUD;

    reg  clk_27m = 1'b0;
    reg  btn_rst_n = 1'b0;
    wire uart_txd;
    wire [5:0] led;

    always #HALF_PERIOD clk_27m = ~clk_27m;

    hcpu_gowin_top #(
        .USE_PLL      (0),
        .BAUD         (BAUD),
        .PROGRAM_HEX  ("hfs_lifecycle.hex")
    ) u_board (
        .clk_27m   (clk_27m),
        .btn_rst_n (btn_rst_n),
        .uart_rxd  (1'b1),
        .uart_txd  (uart_txd),
        .led       (led)
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

    initial begin
        $dumpfile("tb_hcpu_hfs_lifecycle.vcd");
        $dumpvars(0, tb_hcpu_hfs_lifecycle);

        $display("=== tb_hcpu_hfs_lifecycle: create, write, read, verify ===");

        repeat (20) @(posedge clk_27m);
        btn_rst_n = 1'b1;
        repeat (400000) @(posedge clk_27m);

        $write("  keluar: ");
        for (i = 0; i < count; i = i + 1)
            if (got[i] == 8'h0A) $write(" ");
            else                 $write("%0s", got[i]);
        $display(" (%0d byte)", count);

        // Seven answers, each followed by PRINT's own newline -- and then the
        // wrapper's own `CYCLES=` epilogue, which every program that reaches
        // HALT emits. So the count is at least fourteen, not exactly: the
        // first fourteen bytes are the answers and the rest is the board
        // saying how long it took.
        check(count >= 14, "tujuh jawaban keluar");
        if (count >= 14) begin
            check(got[0]  == "1", "create: file 3 dibuat");
            check(got[2]  == "0", "create lagi: ditolak");
            check(got[4]  == "1", "write: vektor terjaga dikomit");
            check(got[6]  == "1", "read: entri bilang ia ada");
            check(got[8]  == "1", "verify: sama persis, 144 bit");
            check(got[10] == "1", "verify: dan masih lolos guardnya");
            check(got[12] == "0", "baca file tak pernah dibuat: 0");
        end

        if (errors == 0)
            $display("tb_hcpu_hfs_lifecycle: SEMUA LULUS (8 pemeriksaan)");
        else
            $display("tb_hcpu_hfs_lifecycle: %0d GAGAL", errors);
        $finish;
    end
endmodule
