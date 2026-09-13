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
// how Fetch says "I am not presenting an instruction". For two cycles that is
// the whole truth of the front end, and `pc_now` used to read `if_pc` through
// it -- so a maskable interrupt did not read "nothing here", it read the
// ADDRESS ZERO and saved it as the place to come back to.
//
// ── what it cost, in one number ─────────────────────────────────
// A three-instruction loop that ends in JMP takes six cycles, and TWO of those
// six were the shadow. A process in a tight loop therefore had one chance in
// three of being sent back to address 0 by its very first preemption -- and
// address 0 is boot code, in user mode, where its first peripheral store
// faults it for ever. kernel.hasm's process A froze at 337 exactly that way,
// from the day the scheduler was built, and its own bench never asked whether
// A was still moving.
//
// ── what closed it ──────────────────────────────────────────────
// hcpu_fetch now carries `if_pc_valid`, written in the same places it writes
// `if_pc`, and hcpu_top drives the trap unit's `pc_valid` from it instead of
// from 1'b1. hcpu_top's own comment had asked for exactly that in advance:
// "if the front end ever gains a state with no meaningful PC, this has to
// become that state's inverse or a trap will return into a bubble."
//
// A trap no longer fires while the front end is empty; it fires a cycle or two
// later with a real PC to name. Nothing is lost by the wait -- the timer's
// `expired` is a sticky level, not a pulse -- and this bench measures that the
// wait actually happens (`held`) rather than assuming it.
//
// This bench was written the other way round first, asserting the defect as it
// measured, so that the day the repair landed these rows would go red and ask
// to be inverted. That is the day. The rows below now say what they always had
// to end up saying: a preempted process resumes where it was.
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
    // `held` is the direct evidence that the sweep reaches the shadow at all:
    // cycles where the timer was armed and nothing else stood in the way, and
    // the fire was suppressed only because the front end had no PC to name.
    // Without it, a sweep that never came near a redirect would pass this
    // bench by never testing anything.
    reg        fired, coincide, in_loop, running;
    reg [31:0] saved_epc, saw_ifpc;
    integer    since_fire, held;

    task run_with_compare;
        input [31:0] compare_value;
        integer cyc;
        begin
            load_program;
            rst_n = 0;
            fired = 0; coincide = 0; in_loop = 0; running = 0;
            saved_epc = 32'hDEAD; saw_ifpc = 0; since_fire = 0; held = 0;
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
                // The loop has been entered once Fetch has presented its
                // first instruction: before that, address 0 is a legitimate
                // place for a trap to return to, because the machine has not
                // started.
                if (dut.if_pc_valid && dut.if_pc >= LOOP) running = 1;
                if (!fired && (|dut.u_trap.armed) && !dut.u_trap.trap_active
                           && !dut.if_pc_valid)
                    held = held + 1;
                if (dut.u_trap.fire && !fired) begin
                    fired    = 1;
                    coincide = dut.branch_taken_w;
                    saw_ifpc = dut.if_pc;
                    // Latched AT the fire, not after it: before the machine
                    // has run its first instruction, address 0 is a
                    // legitimate place for a trap to return to, and a run
                    // that reaches the loop later must not make that look
                    // like a defect.
                    in_loop  = running;
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

    integer c, n_fire, n_coincide, n_held, n_zero_running, n_valid, n_bad_target;

    initial begin
        $dumpfile("tb_hcpu_trap_redirect_shadow.vcd");
        $dumpvars(0, tb_hcpu_trap_redirect_shadow);

        $display("=== tb_hcpu_trap_redirect_shadow: where a timer saves zero ===");
        n_fire = 0; n_coincide = 0; n_held = 0;
        n_zero_running = 0; n_valid = 0; n_bad_target = 0;

        // The counter free-runs from reset, so sweeping the deadline across
        // sixty cycles walks the whole six-cycle phase of the loop many times
        // over, without having to hand-derive the pipeline's latency.
        for (c = 1; c <= 60; c = c + 1) begin
            run_with_compare(c);
            // 32'hDEAD means the run ended before epc could be read back --
            // a fact about the observation window, not about the machine.
            if (held > 0) n_held = n_held + 1;
            if (fired && saved_epc != 32'hDEAD) begin
                n_fire = n_fire + 1;
                if (coincide) begin
                    n_coincide = n_coincide + 1;
                    // A trap sharing its cycle with a taken branch resumes at
                    // the branch's own target -- the fix hcpu_top.v already
                    // carried, and this sweep keeps it honest.
                    if (saved_epc != LOOP) n_bad_target = n_bad_target + 1;
                end
                if (saved_epc == 0 && in_loop) begin
                    n_zero_running = n_zero_running + 1;
                    $display("  KEMBALI KE 0 cmp=%0d coincide=%0b if_pc=%0d",
                             c, coincide, saw_ifpc);
                end else n_valid = n_valid + 1;
            end
        end

        $display("  %0d fire: %0d sah, %0d kembali ke 0 saat berjalan",
                 n_fire, n_valid, n_zero_running);
        $display("  sekelas siklus dengan cabang: %0d   lari yang trapnya ditahan: %0d",
                 n_coincide, n_held);

        check(n_fire >= 50, "timer menyala hampir tiap kali");
        check(n_coincide > 0, "sapuan capai siklus cabang");

        // Coverage, and it has to be measured rather than assumed: a sweep
        // that never reached a redirect would satisfy every row below by
        // never testing one.
        check(n_held > 0, "sapuan capai bayangan redirect");
        check(n_held * 4 > n_fire, "bayangan bukan kasus langka");

        // The fix hcpu_top.v already carried, kept honest.
        check(n_bad_target == 0, "tabrakan pulang ke sasaran");

        // ── what the repair had to buy ──────────────────────────
        check(n_zero_running == 0, "tak ada yang pulang ke alamat 0");
        check(n_valid == n_fire, "tiap fire simpan PC yang sah");

        if (errors == 0)
            $display("tb_hcpu_trap_redirect_shadow: SEMUA LULUS (7 pemeriksaan)");
        else
            $display("tb_hcpu_trap_redirect_shadow: %0d GAGAL", errors);
        $finish;
    end
endmodule
