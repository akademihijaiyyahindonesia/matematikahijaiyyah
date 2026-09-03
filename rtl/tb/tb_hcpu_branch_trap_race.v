// tb_hcpu_branch_trap_race.v — a taken branch and a maskable interrupt
// resolving in the same cycle.
//
// Found through the guard daemon in kernel.hasm: JGD (guard-passed, taken)
// and the scheduler's own timer interrupt landed in the same Execute cycle
// once in 400,000, and C resumed at the branch's FALL-THROUGH instead of its
// TARGET -- silently taking the "guard failed" path after a guard that had
// actually passed. That reproduction needed a specific kernel, a specific
// quantum, and about nineteen sweeps of good luck to hit; this one hits it on
// purpose, every run, by sweeping the timer's own deadline against a fixed,
// tiny, unconditional-jump program until the two land on the same cycle.
//
// The mechanism: `pc_now`, what a maskable interrupt saves as its return
// address, was wired to `if_pc` -- the PC Fetch is CURRENTLY presenting,
// which is a SPECULATIVE sequential PC+1 that has not yet been corrected for
// whatever Execute decides this same cycle. A jump resolves in Execute, one
// stage behind Fetch, so at the moment a trap and a taken jump coincide,
// `if_pc` already shows the jump's FALL-THROUGH address, not its target --
// the redirect that discards the jump's own effect for fetching purposes
// also, silently, discards it for the return address. On resume, execution
// picks up as though the jump had fallen through, even though it was taken
// and its other side effects (a CALL's return-address push, for instance)
// already committed on that same cycle regardless.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_branch_trap_race;

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

    hcpu_top #(.CLK_HZ(50_000_000), .BAUD(5_000_000)) dut (
        .clk(clk), .rst_n(rst_n),
        .imem_addr(imem_addr), .imem_ce(imem_ce), .imem_data(imem_data),
        .uart_tx(uart_tx), .halted(halted), .guard_led(guard_led),
        .dbg_gpr_raddr(5'd0), .dbg_gpr_rdata(), .dbg_flags()
    );

    initial clk = 0;
    always #5 clk = ~clk;

    function [`ILEN-1:0] enc;
        input [7:0]  op;
        input [3:0]  dst, s1, s2;
        input [11:0] imm;
        enc = {op, dst, s1, s2, imm};
    endfunction

    // ── the program ──────────────────────────────────────────────
    // 0: JMP  10          -- unconditional, always taken
    // 1: MOVI R2, 111     -- the fall-through: must NOT run if the fix holds
    // 2: HALT
    // ...
    // 10: MOVI R2, 222    -- the target: must run
    // 11: HALT
    // 20: MOVI R5, 0
    // 21: MOVI R4, 0
    // 22: STORE R4, R5, 0xFF6  -- clear the timer's sticky expired flag, or
    //                             it re-fires the instant ERET redirects and
    //                             this handler never actually returns
    // 23: MOVI R3, 999    -- the handler ran
    // 24: ERET
    localparam JMP_ADDR = 0, TARGET_ADDR = 10, HANDLER_ADDR = 20;

    task load_program;
        integer i;
        begin
            for (i = 0; i < `CODE_DEPTH; i = i + 1)
                imem[i] = {`OP_NOP, 24'h0};
            imem[JMP_ADDR]      = enc(`OP_JMP,  4'd0, 4'd0, 4'd0, TARGET_ADDR);
            imem[JMP_ADDR+1]    = enc(`OP_MOVI, 4'd2, 4'd0, 4'd0, 111);
            imem[JMP_ADDR+2]    = enc(`OP_HALT, 4'd0, 4'd0, 4'd0, 0);
            imem[TARGET_ADDR]   = enc(`OP_MOVI, 4'd2, 4'd0, 4'd0, 222);
            imem[TARGET_ADDR+1] = enc(`OP_HALT, 4'd0, 4'd0, 4'd0, 0);
            imem[HANDLER_ADDR]   = enc(`OP_MOVI,  4'd5, 4'd0, 4'd0, 0);
            imem[HANDLER_ADDR+1] = enc(`OP_MOVI,  4'd4, 4'd0, 4'd0, 0);
            imem[HANDLER_ADDR+2] = enc(`OP_STORE, 4'd0, 4'd4, 4'd5, 'hFF6); // MEM[R5+0xFF6] <- R4
            imem[HANDLER_ADDR+3] = enc(`OP_MOVI,  4'd3, 4'd0, 4'd0, 999);
            imem[HANDLER_ADDR+4] = enc(`OP_ERET,  4'd0, 4'd0, 4'd0, 0);
        end
    endtask

    // ── drive one run at a chosen deadline ─────────────────────────
    reg collided;   // branch_taken_w and u_trap.fire on the same cycle
    reg [31:0] r2_after, r3_after;

    task run_with_compare;
        input [31:0] compare_value;
        integer cyc;
        begin
            load_program;
            rst_n = 0;
            collided = 1'b0;
            repeat (4) @(negedge clk);
            rst_n = 1;

            // Poked directly rather than encoded as STORE instructions: the
            // program under test has to stay exactly the jump/fall-through
            // pair above, or the pipeline timing this test depends on shifts.
            dut.u_trap.vector <= HANDLER_ADDR;
            dut.u_trap.enable <= (8'b1 << `TRAP_TIMER);
            dut.u_mmio.u_timer.compare <= compare_value;

            for (cyc = 0; cyc < 60; cyc = cyc + 1) begin
                @(posedge clk);
                if (dut.branch_taken_w && dut.u_trap.fire)
                    collided = 1'b1;
            end
            r2_after = dut.u_regfile.gpr[2];
            r3_after = dut.u_regfile.gpr[3];
        end
    endtask

    integer c, hits, correct, wrong;
    initial begin
        hits = 0; correct = 0; wrong = 0;
        // The counter free-runs from reset; sweeping the deadline across the
        // first several dozen cycles is guaranteed to cross whichever one
        // lines up with the jump resolving in Execute, without having to
        // hand-derive the pipeline's exact latency.
        for (c = 1; c <= 40; c = c + 1) begin
            run_with_compare(c);
            if (collided) begin
                hits = hits + 1;
                $display("  compare=%0d  tabrakan  R2=%0d R3=%0d  %s",
                    c, r2_after, r3_after,
                    (r2_after == 222) ? "BENAR (target)" :
                    (r2_after == 111) ? "SALAH (fall-through)" : "?");
                if (r2_after == 222 && r3_after == 999) correct = correct + 1;
                else wrong = wrong + 1;
            end
        end

        $display("");
        $display("  tabrakan ditemukan: %0d kali di antara compare=1..40", hits);
        if (hits == 0) begin
            $display("GAGAL: tidak ada tabrakan ditemukan -- sapuan tidak menutupi jendela pipeline");
            $fatal(1);
        end else if (wrong > 0) begin
            $display("GAGAL: %0d dari %0d tabrakan resume di fall-through, bukan target", wrong, hits);
            $fatal(1);
        end else begin
            $display("PASS: tb_hcpu_branch_trap_race -- %0d/%0d tabrakan resume benar di target",
                correct, hits);
        end
        $finish;
    end
endmodule
