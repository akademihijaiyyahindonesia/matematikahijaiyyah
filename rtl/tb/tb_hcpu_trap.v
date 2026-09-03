// Trap unit, on its own bench. Wiring it into the pipeline first would mean
// every failure has two possible homes.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_trap;
    reg clk = 0, rst_n = 0;
    reg src_timer = 0, src_uart_rx = 0, src_illegal = 0, src_priv = 0, src_mem = 0;
    reg [`XLEN-1:0] pc_now = 0, pc_fault = 0;
    reg pc_valid = 1;
    reg reg_we = 0; reg [3:0] reg_sel = 0; reg [`XLEN-1:0] reg_wdata = 0;
    wire [`XLEN-1:0] reg_rdata;
    reg eret = 0;
    wire trap_redirect, in_trap, in_user;
    wire [`XLEN-1:0] trap_target;

    integer errors = 0;

    hcpu_trap dut (.clk(clk), .rst_n(rst_n),
        .src_timer(src_timer), .src_uart_rx(src_uart_rx), .src_illegal(src_illegal),
        .src_priv(src_priv), .src_mem(src_mem),
        .pc_now(pc_now), .pc_valid(pc_valid), .pc_fault(pc_fault),
        .reg_we(reg_we), .reg_sel(reg_sel), .reg_wdata(reg_wdata), .reg_rdata(reg_rdata),
        .eret(eret), .trap_redirect(trap_redirect), .trap_target(trap_target),
        .in_trap(in_trap), .in_user(in_user));

    always #5 clk = ~clk;

    task check(input cond, input [255:0] what);
        begin
            if (!cond) begin
                $display("  GAGAL: %0s", what);
                errors = errors + 1;
            end
        end
    endtask

    task wr(input [3:0] sel, input [`XLEN-1:0] val);
        begin
            @(negedge clk); reg_we = 1; reg_sel = sel; reg_wdata = val;
            @(negedge clk); reg_we = 0;
        end
    endtask

    initial begin
        repeat (2) @(negedge clk); rst_n = 1;

        // ── 1. Disabled sources do not trap ─────────────────────
        src_timer = 1;
        repeat (3) @(negedge clk);
        check(!trap_redirect, "sumber tanpa enable tidak boleh menjebak");
        check(reg_rdata !== 32'hx, "read path harus terdefinisi");

        // pending must still SHOW it, even while masked
        reg_sel = `REG_TRAP_PENDING; #1;
        check(reg_rdata[`TRAP_TIMER] === 1'b1, "pending harus tampak walau termasker");

        // ── 2. Enable it: now it fires ──────────────────────────
        // Configure with the source LOW. `fire` is combinational, so if the
        // source is already high when enable lands, the very next posedge
        // latches trap_active and the redirect is over before it can be read.
        src_timer = 0;
        wr(`REG_TRAP_VECTOR, 32'h0000_0100);
        wr(`REG_TRAP_ENABLE, 32'h0000_0001);   // timer only
        pc_now = 32'h0000_0042;
        src_timer = 1; #1;
        check(trap_redirect, "trap harus menyala saat enable dan sumber aktif");
        check(trap_target == 32'h0000_0100, "target harus vector");

        @(negedge clk);
        check(in_trap, "in_trap harus terkunci setelah masuk");
        reg_sel = `REG_TRAP_EPC; #1;
        check(reg_rdata == 32'h0000_0042, "epc harus PC saat masuk");
        reg_sel = `REG_TRAP_CAUSE; #1;
        check(reg_rdata == `TRAP_TIMER, "cause harus INDEKS, bukan mask");

        // ── 3. No re-entry while in_trap ────────────────────────
        // The source is STILL high. Without in_trap this re-traps forever.
        pc_now = 32'h0000_0999;
        repeat (4) @(negedge clk);
        check(!trap_redirect, "tidak boleh masuk lagi selama in_trap");
        reg_sel = `REG_TRAP_EPC; #1;
        check(reg_rdata == 32'h0000_0042, "epc tidak boleh tertimpa saat in_trap");

        // ── 4. ERET returns and clears ──────────────────────────
        src_timer = 0;                          // handler clears its source
        @(negedge clk); eret = 1;
        #1 check(trap_redirect, "eret harus mengalihkan");
        #1 check(trap_target == 32'h0000_0042, "eret harus kembali ke epc");
        @(negedge clk); eret = 0;
        @(negedge clk);
        check(!in_trap, "in_trap harus lepas setelah eret");

        // ── 5. A source left high traps again on return ─────────
        // Documented behaviour, and worth pinning: a handler that forgets to
        // clear its source must not silently lose the interrupt either.
        src_timer = 1; #1;
        check(trap_redirect, "sumber yang masih tinggi harus menjebak lagi");
        @(negedge clk); @(negedge clk);
        src_timer = 0; @(negedge clk); eret = 1; @(negedge clk); eret = 0;
        @(negedge clk);

        // ── 6. Priority: lowest index, and it must be FIXED ─────
        wr(`REG_TRAP_ENABLE, 32'h0000_0007);   // all three
        src_uart_rx = 1; src_illegal = 1; #1;  // 1 and 2, not 0
        check(trap_redirect, "harus menjebak dengan dua sumber");
        @(negedge clk);
        reg_sel = `REG_TRAP_CAUSE; #1;
        check(reg_rdata == `TRAP_UART_RX, "indeks terendah harus menang");
        src_uart_rx = 0; src_illegal = 0;
        @(negedge clk); eret = 1; @(negedge clk); eret = 0; @(negedge clk);

        // ── 7. pc_valid gates entry ─────────────────────────────
        pc_valid = 0; src_timer = 1;
        repeat (3) @(negedge clk);
        check(!trap_redirect, "tidak boleh menjebak saat pc_valid rendah");
        pc_valid = 1; #1;
        check(trap_redirect, "harus menjebak begitu pc_valid naik");
        src_timer = 0; @(negedge clk); eret = 1; @(negedge clk); eret = 0; @(negedge clk);

        // ── 8. CAUSE and PENDING reject writes ──────────────────
        wr(`REG_TRAP_CAUSE, 32'h0000_0007);
        reg_sel = `REG_TRAP_CAUSE; #1;
        check(reg_rdata != 32'h0000_0007, "CAUSE harus read-only");
        wr(`REG_TRAP_PENDING, 32'h0000_00FF);
        reg_sel = `REG_TRAP_PENDING; #1;
        check(reg_rdata == 32'h0000_0000, "PENDING harus read-only dan cermin sumber");

        // ── 9. ERET beats a simultaneous trap ───────────────────
        // The contention is NOT inside a handler: `fire` needs !trap_active, so
        // while a trap runs the two can never coincide. The real case is a
        // stray ERET outside a trap with a source already armed -- there both
        // are true in the same cycle, and only there does the priority show.
        //
        // A first version of this test staged it inside the handler, where fire
        // was 0 the whole time. Inverting the priority in the module left it
        // passing.
        src_timer = 0; src_uart_rx = 0; src_illegal = 0;
        @(negedge clk); eret = 1; @(negedge clk); eret = 0; @(negedge clk);
        check(!in_trap, "prasyarat: harus di luar trap");

        wr(`REG_TRAP_VECTOR, 32'h0000_0700);
        wr(`REG_TRAP_ENABLE, 32'h0000_0001);
        wr(`REG_TRAP_EPC,    32'h0000_0055);
        src_timer = 1;                           // fire is now 1: not in a trap
        eret      = 1;                           // and eret is 1 in the same cycle
        #1;
        check(trap_redirect, "keduanya aktif: harus tetap mengalihkan");
        check(trap_target == 32'h0000_0055,
              "eret harus menang atas trap serentak (epc, bukan vector)");
        @(negedge clk); eret = 0; src_timer = 0;

        // ── 10. Privilege: reset is supervisor ──────────────────
        check(!in_user, "reset harus mendarat di supervisor");

        // ── 11. Entering user mode: write prev, then ERET ───────
        wr(`REG_TRAP_EPC, 32'h0000_0200);
        wr(`REG_TRAP_MODE, 32'h0000_0000);      // bit1 = 0 -> previous = USER
        @(negedge clk); eret = 1; @(negedge clk); eret = 0; @(negedge clk);
        check(in_user, "eret dengan prev=USER harus menurunkan privilese");

        // ── 12. Bit 0 is read-only ─────────────────────────────
        wr(`REG_TRAP_MODE, 32'h0000_0001);      // try to set mode = SUPER
        @(negedge clk);
        check(in_user, "bit mode saat ini harus read-only");

        // ── 13. A privilege fault is NOT maskable ──────────────
        wr(`REG_TRAP_ENABLE, 32'h0000_0000);    // everything masked
        wr(`REG_TRAP_VECTOR, 32'h0000_0300);
        pc_now   = 32'h0000_09AA;
        pc_fault = 32'h0000_0055;
        src_priv = 1; #1;
        check(trap_redirect, "TRAP_PRIV harus menyala walau semua enable nol");
        check(trap_target == 32'h0000_0300, "target harus vector");
        @(negedge clk);
        check(!in_user, "handler harus berjalan di supervisor");
        reg_sel = `REG_TRAP_CAUSE; #1;
        check(reg_rdata == `TRAP_PRIV, "cause harus TRAP_PRIV");

        // ── 14. An exception names its own instruction ─────────
        reg_sel = `REG_TRAP_EPC; #1;
        check(reg_rdata == 32'h0000_0055,
              "epc harus pc_fault, bukan pc_now — exception menyebut instruksinya");
        reg_sel = `REG_TRAP_MODE; #1;
        check(reg_rdata[1] == 1'b0, "prev harus mengingat USER");

        src_priv = 0;
        @(negedge clk); eret = 1; @(negedge clk); eret = 0; @(negedge clk);
        check(in_user, "eret harus mengembalikan ke USER");

        // ── 15. An interrupt still uses pc_now ─────────────────
        wr(`REG_TRAP_MODE, 32'h0000_0002);      // prev = SUPER
        @(negedge clk); eret = 1; @(negedge clk); eret = 0; @(negedge clk);
        check(!in_user, "kembali ke supervisor");
        wr(`REG_TRAP_ENABLE, 32'h0000_0001);
        pc_now = 32'h0000_0AAA; pc_fault = 32'h0000_0055;
        src_timer = 1; #1;
        check(trap_redirect, "interupsi timer harus menyala");
        @(negedge clk);
        reg_sel = `REG_TRAP_EPC; #1;
        check(reg_rdata == 32'h0000_0AAA,
              "interupsi harus memakai pc_now, bukan pc_fault");
        src_timer = 0; @(negedge clk); eret = 1; @(negedge clk); eret = 0;

        // ── 16. TRAP_MEM: juga exception, juga non-maskable ─────
        wr(`REG_TRAP_ENABLE, 32'h0000_0000);
        wr(`REG_TRAP_VECTOR, 32'h0000_0400);
        pc_now = 32'h0000_0BBB; pc_fault = 32'h0000_0077;
        src_mem = 1; #1;
        check(trap_redirect, "TRAP_MEM harus menyala walau semua enable nol");
        @(negedge clk);
        reg_sel = `REG_TRAP_CAUSE; #1;
        check(reg_rdata == `TRAP_MEM, "cause harus TRAP_MEM");
        reg_sel = `REG_TRAP_EPC; #1;
        check(reg_rdata == 32'h0000_0077,
              "TRAP_MEM harus memakai pc_fault — ia exception, bukan interupsi");
        src_mem = 0;
        @(negedge clk); eret = 1; @(negedge clk); eret = 0; @(negedge clk);

        // ── 17. Prioritas: TRAP_PRIV di bawah TRAP_MEM ─────────
        src_priv = 1; src_mem = 1; #1;
        check(trap_redirect, "dua exception serentak harus menyala");
        @(negedge clk);
        reg_sel = `REG_TRAP_CAUSE; #1;
        check(reg_rdata == `TRAP_PRIV, "indeks terendah tetap menang");
        src_priv = 0; src_mem = 0;
        @(negedge clk); eret = 1; @(negedge clk); eret = 0;

        if (errors == 0) $display("PASS: tb_hcpu_trap — semua pemeriksaan lulus");
        else             $display("FAIL: tb_hcpu_trap — %0d gagal", errors);
        $finish;
    end
endmodule
