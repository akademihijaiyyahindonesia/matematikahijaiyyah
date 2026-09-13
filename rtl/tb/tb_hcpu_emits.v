// tb_hcpu_emits.v — the character path, and the three ways to break it.
//
// EMITS (0xA2) prints the string at IMM: one ASCII byte per 32-bit word, a
// zero word ends it, and the address is a WORD address so the next character
// is at addr + 1. §13.1.1 of docs/HISA_SPEC.md fixes that shape; before v1.1
// the slot was named and the layout was not, which is why nothing implemented
// it.
//
// ── what it prints, and what it does not ────────────────────────
// Nine characters and no newline. PRINT appends one because it prints a
// number; a string carries its own ending if it wants one, and that is what
// lets a prompt sit on the line and wait.
//
// ── the same transmitter, not a second one ──────────────────────
// hcpu_mmio.v refuses a second driver on the serial port -- "a second driver
// on the same port is a bus conflict rather than a feature" -- and that
// refusal is kept. EMITS drives no new hardware: the print state machine in
// hcpu_top.v gained three states and another source. The data RAM port is
// multiplexed rather than duplicated for the same reason, and it is safe
// because the pipeline is stalled throughout, exactly as it is for PRINT.
//
// ── the three sabotages this file is built to catch ─────────────
// Each was run against this bench and each turned it red:
//
//   the terminator removed     -- the string runs on into the Z words
//   one character changed      -- the wrong byte reaches the wire
//   the step made +4 not +1    -- three words in four are skipped
//
// The third is the one worth stating: +4 is how the same layout is written in
// byte addresses, and this machine addresses data memory by word. A reader
// who carries the byte-address habit here gets "Hah" and a run past the end,
// not a compile error (R3).
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_emits;
    localparam integer BAUD   = 5_000_000;
    localparam real    BIT_NS = 1_000_000_000.0 / BAUD;
    localparam         STR_AT = 12'h200;

    reg clk, rst_n;
    wire uart_tx, halted, guard_led;

    reg [`ILEN-1:0] imem [0:`CODE_DEPTH-1];
    wire [`CODE_ADDR_W-1:0] imem_addr;
    wire imem_ce;
    reg  [`ILEN-1:0] imem_data_r;
    wire [`ILEN-1:0] imem_data;
    always @(posedge clk)
        if (imem_ce) imem_data_r <= imem[imem_addr];
    assign imem_data = imem_data_r;

    hcpu_top #(.CLK_HZ(50_000_000), .BAUD(BAUD)) dut (
        .clk(clk), .rst_n(rst_n),
        .imem_addr(imem_addr), .imem_ce(imem_ce), .imem_data(imem_data),
        .uart_tx(uart_tx), .halted(halted), .guard_led(guard_led),
        .dbg_gpr_raddr(5'd0), .dbg_gpr_rdata(), .dbg_flags()
    );

    initial clk = 0;
    always #10 clk = ~clk;

    function [`ILEN-1:0] enc;
        input [7:0]  op;
        input [3:0]  dst, s1, s2;
        input [11:0] imm;
        enc = {op, dst, s1, s2, imm};
    endfunction

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

    // ── an independent receiver, timed from BIT_NS ──────────────
    // Not from the design's own counters: a bench that reads the timing out
    // of the thing it is testing cannot catch the timing being wrong.
    reg [7:0] got [0:63];
    integer   count = 0;
    integer   bit_i;
    reg [7:0] shifted;

    initial begin
        forever begin
            @(negedge uart_tx);
            #(BIT_NS * 1.5);
            for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
                shifted[bit_i] = uart_tx;
                #BIT_NS;
            end
            if (count < 64) begin
                got[count] = shifted;
                count = count + 1;
            end
        end
    end

    integer i, pc;
    reg [7:0] str [0:8];

    initial begin
        $dumpfile("tb_hcpu_emits.vcd");
        $dumpvars(0, tb_hcpu_emits);

        $display("=== tb_hcpu_emits: jalur karakter ===");

        str[0] = "H"; str[1] = "i"; str[2] = "j"; str[3] = "a"; str[4] = "i";
        str[5] = "y"; str[6] = "y"; str[7] = "a"; str[8] = "h";

        for (i = 0; i < `CODE_DEPTH; i = i + 1) imem[i] = {`OP_NOP, 24'h0};

        // One character per word, then the terminator, then EMITS.
        pc = 0;
        for (i = 0; i < 9; i = i + 1) begin
            imem[pc]   = enc(`OP_MOVI,  4'd1, 4'd0, 4'd0, {4'd0, str[i]});
            imem[pc+1] = enc(`OP_STORE, 4'd0, 4'd1, 4'd0, STR_AT + i[11:0]);
            pc = pc + 2;
        end
        // Junk written OVER the terminator's own word and the two past it,
        // and this is the whole reason the first sabotage means anything.
        // Simulation starts the data RAM at zero, so a terminator that is
        // merely not written is still a zero: deleting it changed no output at
        // all, and the test passed while measuring nothing. Twice -- the first
        // fix put the Z words past the terminator and left its own word zero,
        // which failed for the same reason one step along. The terminator is
        // written LAST, over a Z, so removing that store leaves a Z there.
        imem[pc]   = enc(`OP_MOVI,  4'd2, 4'd0, 4'd0, {4'd0, 8'h5A});
        imem[pc+1] = enc(`OP_STORE, 4'd0, 4'd2, 4'd0, STR_AT + 12'd9);
        imem[pc+2] = enc(`OP_STORE, 4'd0, 4'd2, 4'd0, STR_AT + 12'd10);
        imem[pc+3] = enc(`OP_STORE, 4'd0, 4'd2, 4'd0, STR_AT + 12'd11);
        imem[pc+4] = enc(`OP_MOVI,  4'd1, 4'd0, 4'd0, 0);
        imem[pc+5] = enc(`OP_STORE, 4'd0, 4'd1, 4'd0, STR_AT + 12'd9);
        imem[pc+6] = enc(`OP_EMITS, 4'd0, 4'd0, 4'd0, STR_AT);
        imem[pc+7] = enc(`OP_HALT,  4'd0, 4'd0, 4'd0, 0);

        rst_n = 0;
        repeat (4) @(negedge clk);
        rst_n = 1;
        repeat (4000) @(posedge clk);

        $write("  keluar: \"");
        for (i = 0; i < count; i = i + 1) $write("%0s", got[i]);
        $display("\"  (%0d byte)", count);

        check(count == 9, "sembilan byte, tanpa newline");
        if (count >= 9) begin
            check(got[0] == "H" && got[1] == "i" && got[2] == "j"
               && got[3] == "a" && got[4] == "i" && got[5] == "y"
               && got[6] == "y" && got[7] == "a" && got[8] == "h",
                  "urutannya Hijaiyyah");
        end
        // The terminator is a stop, not a character: a tenth byte would mean
        // EMITS printed the zero word or ran past it.
        check(count <= 9, "penutup tidak ikut tercetak");
        check(halted, "mesin sampai ke HALT sesudahnya");

        if (errors == 0)
            $display("tb_hcpu_emits: SEMUA LULUS (4 pemeriksaan)");
        else
            $display("tb_hcpu_emits: %0d GAGAL", errors);
        $finish;
    end
endmodule
