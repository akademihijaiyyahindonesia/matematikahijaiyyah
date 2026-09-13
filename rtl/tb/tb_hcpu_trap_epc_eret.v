// tb_hcpu_trap_epc_eret.v — how much distance a handler needs between writing
// its return address and returning, on the whole pipeline rather than the
// trap unit alone.
//
// tb_hcpu_trap.v's check 18 asks the unit: a write to TRAP_EPC in the same
// cycle as ERET must be the value ERET takes. This bench asks the machine, in
// the shape a real handler has -- LOAD the epc, add one, STORE it back, then
// ERET after N instructions -- and sweeps N from nothing to four.
//
// ── what it used to answer ──────────────────────────────────────
// Before hcpu_trap.v carried `epc_at_eret`:
//
//     0 NOP: fire=15, handler entered 15 times, R7=0   <- epc lama
//     1 NOP: fire=1,  handler entered 1 time,  R7=1
//     2..4 : the same as 1
//
// At zero the trap unit's `trap_target` read the `epc` REGISTER, which the
// software write had not reached yet, so ERET returned to the SYSCALL that
// caused the trap -- for ever. Fifteen is only how many times that fits in the
// observation window; the program never advanced past it.
//
// Exactly one instruction of distance was the whole difference, and that is
// why nothing in the tree ever tripped over it: hal_epc_set is followed by
// hal_mode_user, hal_timer_arm and sixteen restore loads before any ERET, and
// rtl/programs/trap_flags.hasm happened to use three NOPs. A handler written
// tightly was silently wrong, and the symptom was an instruction that repeated
// rather than anything that announced itself.
//
// ── what it asks now ────────────────────────────────────────────
// That zero is as correct as four. The row for gap 0 is the whole point of the
// file: it is the one that used to fail, and R3 says a gate is worth what it
// catches when the thing it guards is broken.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_trap_epc_eret;

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

    // ── the program ─────────────────────────────────────────────
    //  0: MOVI  R5, 0
    //  1: MOVI  R1, HANDLER
    //  2: STORE R1, [R5 + TRAP_VECTOR]
    //  3..5: NOP        -- the vector write is an MMIO write and needs to land
    //                      before the SYSCALL below can use it
    //  6: SYSCALL       -- epc names THIS instruction
    //  7: MOVI  R7, 1   -- reached only if the handler advanced epc
    //  8: HALT
    //
    // handler at 20: count the entry in R6, read epc, add one, store it back,
    //                N filler instructions, ERET.
    localparam HANDLER = 20;

    task load_program;
        input integer gap;
        integer i;
        begin
            for (i = 0; i < `CODE_DEPTH; i = i + 1)
                imem[i] = {`OP_NOP, 24'h0};
            imem[0] = enc(`OP_MOVI,  4'd5, 4'd0, 4'd0, 0);
            imem[1] = enc(`OP_MOVI,  4'd1, 4'd0, 4'd0, HANDLER);
            imem[2] = enc(`OP_STORE, 4'd0, 4'd1, 4'd5, 'hFF8);
            imem[6] = enc(`OP_SYSCALL, 4'd0, 4'd0, 4'd0, 0);
            imem[7] = enc(`OP_MOVI,  4'd7, 4'd0, 4'd0, 1);
            imem[8] = enc(`OP_HALT,  4'd0, 4'd0, 4'd0, 0);

            imem[HANDLER]   = enc(`OP_ADDI,  4'd6,  4'd6,  4'd0, 1);
            imem[HANDLER+1] = enc(`OP_LOAD,  4'd11, 4'd5,  4'd0, 'hFF9);
            imem[HANDLER+2] = enc(`OP_ADDI,  4'd11, 4'd11, 4'd0, 1);
            imem[HANDLER+3] = enc(`OP_STORE, 4'd0,  4'd11, 4'd5, 'hFF9);
            for (i = 0; i < gap; i = i + 1)
                imem[HANDLER+4+i] = {`OP_NOP, 24'h0};
            imem[HANDLER+4+gap] = enc(`OP_ERET, 4'd0, 4'd0, 4'd0, 0);
        end
    endtask

    integer g, cyc, entries, r7, fires;
    always @(posedge clk) if (dut.u_trap.fire) fires = fires + 1;

    initial begin
        $dumpfile("tb_hcpu_trap_epc_eret.vcd");
        $dumpvars(0, tb_hcpu_trap_epc_eret);

        $display("=== tb_hcpu_trap_epc_eret: jarak STORE TRAP_EPC sebelum ERET ===");

        for (g = 0; g <= 4; g = g + 1) begin
            load_program(g);
            rst_n = 0; fires = 0;
            repeat (4) @(negedge clk);
            rst_n = 1;
            for (cyc = 0; cyc < 200; cyc = cyc + 1) @(posedge clk);
            entries = dut.u_regfile.gpr[6];
            r7      = dut.u_regfile.gpr[7];

            $display("  %0d NOP: fire=%0d, handler masuk %0d kali, R7=%0d",
                     g, fires, entries, r7);
            check(entries == 1,
                  g == 0 ? "0 NOP: masuk tepat sekali"
                         : "masuk tepat sekali");
            check(r7 == 1, "epc maju: SYSCALL terlewati");
        end

        if (errors == 0)
            $display("tb_hcpu_trap_epc_eret: SEMUA LULUS (10 pemeriksaan)");
        else
            $display("tb_hcpu_trap_epc_eret: %0d GAGAL", errors);
        $finish;
    end
endmodule
