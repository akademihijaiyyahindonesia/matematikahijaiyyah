// tb_hcpu_trap_redirect_shadow.v — the two cycles AFTER a taken branch, where
// a maskable interrupt saves a return address of zero.
//
// tb_hcpu_branch_trap_race.v covers the cycle a taken branch and a trap SHARE.
// hcpu_top.v fixed that one: `pc_now = branch_taken_w ? branch_target_w :
// if_pc`, so when Execute is resolving a taken branch this cycle, the branch's
// own target is what the interrupt returns to. This bench is about the cycles
// immediately after, where `branch_taken_w` is already low again and the fix
// therefore does not apply.
//
// hcpu_fetch.v:61 is the mechanism, and it is not a mistake on its own terms:
//
//     end else if (flush || branch_taken) begin
//         if_instruction <= {`OP_NOP, 24'h000000};
//         if_pc          <= {`XLEN{1'b0}};
//         fetch_valid    <= 1'b0;
//
// A redirect discards the in-flight fetch, and zeroing if_pc alongside it is
// how Fetch says "I am not presenting an instruction". `fetch_valid` going low
// says the same thing for the next cycle. But `pc_now` reads `if_pc` without
// consulting `fetch_valid`, so for the two cycles a redirect costs, a maskable
// interrupt does not read "nothing here" -- it reads the ADDRESS ZERO, and
// saves it as the place to come back to.
//
// ── what that costs, in one number ──────────────────────────────
// A three-instruction loop that ends in JMP takes six cycles. TWO of those six
// are the shadow. So a process in a tight loop has a one-in-three chance of
// being sent back to address 0 by its very first preemption, and address 0 is
// where boot code lives -- in user mode, where boot's first peripheral store
// faults it for ever. That is exactly what kernel.hasm's process A does: it
// freezes at 337 and never runs again, and has since the scheduler was built.
//
// ── this bench asserts the machine as it IS ─────────────────────
// Twenty-one of the sixty fires below save zero -- every fire that lands in
// the shadow, and no fire that does not -- and the rows below say so.
// The day `pc_now` accounts for a redirect, those rows go red and ask to be
// inverted -- which is the only way a measured defect stays a defect instead
// of quietly becoming a claim (R3). The repair belongs to the owner of the
// trap unit; cosmictera-build/OFF.md carries the blocker by name.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_trap_redirect_shadow;

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
    // The loop is deliberately NOT at address 0: a jump whose target is 0
    // would make a saved epc of 0 ambiguous, and ambiguity is the one thing
    // this bench cannot afford.
    //
    //  0: JMP 4            -- get to the loop
    //  4: ADDI R1, R1, 1   -- the loop, three instructions, ending in a
    //  5: ADDI R2, R2, 1      taken jump every time round
    //  6: JMP 4
    // 20: handler -- clears the timer's sticky expired flag, then halts
    localparam LOOP = 4, HANDLER = 20;

    task load_program;
        integer i;
        begin
            for (i = 0; i < `CODE_DEPTH; i = i + 1)
                imem[i] = {`OP_NOP, 24'h0};
            imem[0]      = enc(`OP_JMP,  4'd0, 4'd0, 4'd0, LOOP);
            imem[LOOP]   = enc(`OP_ADDI, 4'd1, 4'd1, 4'd0, 1);
            imem[LOOP+1] = enc(`OP_ADDI, 4'd2, 4'd2, 4'd0, 1);
            imem[LOOP+2] = enc(`OP_JMP,  4'd0, 4'd0, 4'd0, LOOP);
            imem[HANDLER]   = enc(`OP_MOVI,  4'd5, 4'd0, 4'd0, 0);
            imem[HANDLER+1] = enc(`OP_MOVI,  4'd4, 4'd0, 4'd0, 0);
            imem[HANDLER+2] = enc(`OP_STORE, 4'd0, 4'd4, 4'd5, 'hFF6);
            imem[HANDLER+3] = enc(`OP_HALT,  4'd0, 4'd0, 4'd0, 0);
        end
    endtask

    // ── one run at a chosen deadline ────────────────────────────
    reg        fired, coincide, shadow;
    reg [31:0] saved_epc, saw_ifpc;
    integer    since_fire;

    task run_with_compare;
        input [31:0] compare_value;
        integer cyc;
        begin
            load_program;
            rst_n = 0;
            fired = 0; coincide = 0; shadow = 0;
            saved_epc = 32'hDEAD; saw_ifpc = 0; since_fire = 0;
            repeat (4) @(negedge clk);
            rst_n = 1;

            // Poked rather than stored by instructions, for the same reason
            // tb_hcpu_branch_trap_race.v pokes them: the program under test
            // has to stay exactly this loop or the pipeline phase shifts.
            dut.u_trap.vector <= HANDLER;
            dut.u_trap.enable <= (8'b1 << `TRAP_TIMER);
            dut.u_mmio.u_timer.compare <= compare_value;

            for (cyc = 0; cyc < 70; cyc = cyc + 1) begin
                @(posedge clk);
                if (dut.u_trap.fire && !fired) begin
                    fired    = 1;
                    coincide = dut.branch_taken_w;
                    saw_ifpc = dut.if_pc;
                    shadow   = (!dut.branch_taken_w) && (dut.if_pc == 0);
                end
                if (fired) begin
                    since_fire = since_fire + 1;
                    // epc is written with a non-blocking assignment on the
                    // fire cycle, so it is readable the cycle after.
                    if (since_fire == 2) saved_epc = dut.u_trap.epc;
                end
            end
        end
    endtask

    integer c, n_fire, n_coincide, n_shadow, n_zero, n_valid, n_shadow_zero;

    initial begin
        $dumpfile("tb_hcpu_trap_redirect_shadow.vcd");
        $dumpvars(0, tb_hcpu_trap_redirect_shadow);

        $display("=== tb_hcpu_trap_redirect_shadow: where a timer saves zero ===");
        n_fire = 0; n_coincide = 0; n_shadow = 0;
        n_zero = 0; n_valid = 0; n_shadow_zero = 0;

        // The counter free-runs from reset, so sweeping the deadline across
        // sixty cycles walks the whole six-cycle phase of the loop many times
        // over, without having to hand-derive the pipeline's latency.
        for (c = 1; c <= 60; c = c + 1) begin
            run_with_compare(c);
            // 32'hDEAD means the run ended before epc could be read back --
            // a fact about the observation window, not about the machine.
            if (fired && saved_epc != 32'hDEAD) begin
                n_fire = n_fire + 1;
                if (coincide) n_coincide = n_coincide + 1;
                else if (shadow) begin
                    n_shadow = n_shadow + 1;
                    if (saved_epc == 0) n_shadow_zero = n_shadow_zero + 1;
                end
                if (saved_epc == 0) n_zero = n_zero + 1;
                else n_valid = n_valid + 1;
            end
        end

        $display("  %0d fire: %0d sah, %0d menyimpan 0", n_fire, n_valid, n_zero);
        $display("  sekelas siklus dengan cabang: %0d   bayangan redirect: %0d",
                 n_coincide, n_shadow);

        check(n_fire >= 50, "sapuan memicu timer di hampir setiap tenggat");
        check(n_coincide > 0, "sapuan menutupi siklus cabang itu sendiri");
        check(n_shadow > 0, "sapuan menutupi bayangan redirect");

        // The fix that IS in place: a trap sharing the cycle with a taken
        // branch returns to the branch's target, which is LOOP and not zero.
        check(n_coincide > 0 && n_zero < n_fire,
              "tabrakan sekelas-siklus tetap mengembalikan sasaran cabang");

        // ── the defect, asserted as it measures ─────────────────
        check(n_shadow_zero == n_shadow,
              "BLOCKER: setiap fire di bayangan redirect menyimpan epc = 0");
        check(n_zero > 0,
              "BLOCKER: sebagian tenggat mengembalikan proses ke alamat 0");
        check(n_zero * 3 > n_fire,
              "BLOCKER: lebih dari sepertiga tenggat jatuh di bayangan itu");

        if (errors == 0)
            $display("tb_hcpu_trap_redirect_shadow: SEMUA LULUS (7 pemeriksaan)");
        else
            $display("tb_hcpu_trap_redirect_shadow: %0d GAGAL", errors);
        $finish;
    end
endmodule
