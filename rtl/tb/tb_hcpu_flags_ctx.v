// tb_hcpu_flags_ctx.v — FLAGS belongs to the process, not to whoever ran last.
//
// Two processes, two flag patterns, and a timer taking the CPU away from both
// for as long as this bench watches. Each publishes what FRD hands back into
// its own window, so the answer is a number in memory rather than a claim.
//
// ── what the two numbers have to be ─────────────────────────────
//   0x100 == 0x05   pid 0 set G and O, and still reads G and O
//   0x200 == 0x0A   pid 1 set Z and LT, and still reads Z and LT
//
// The patterns share no bit. A process reading the other's, or the kernel's,
// cannot be mistaken for a near miss.
//
// ── and why the counters matter as much ─────────────────────────
// Both must climb. A process that never ran would leave its window at whatever
// boot put there, and a bench that only checked the patterns would call that a
// pass -- which is exactly the shape of the defect tb_hcpu_kernel.v carried for
// as long as it existed, where `A > 0` was satisfied by a process that had
// been dead since its first quantum.
//
// ── what this could not have asked before H-ISA v1.1 ────────────
// Nothing read FLAGS into a register, so a kernel could not save it and this
// bench could not observe it. The cost was measured the only way it could be:
// a loop carrying one comparison, swept against sixty timer deadlines, had
// five of them REVERSE the branch, because the handler's own CMP of TRAP_CAUSE
// overwrote the process's. FRD and FWR (0x0A/0x0B) are what closed it, and
// this file is what keeps it closed.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_flags_ctx;
    localparam real HALF_PERIOD = 18.5;          // 27 MHz

    localparam P0_SEEN  = 12'h100;
    localparam P0_COUNT = 12'h101;
    localparam P1_SEEN  = 12'h200;
    localparam P1_COUNT = 12'h201;
    localparam TICKS    = 12'hF01;

    localparam P0_PATTERN = 32'h05;              // G and O
    localparam P1_PATTERN = 32'h0A;              // Z and LT

    reg  clk_27m = 1'b0;
    reg  btn_rst_n = 1'b0;
    wire uart_txd;
    wire [5:0] led;

    always #HALF_PERIOD clk_27m = ~clk_27m;

    hcpu_gowin_top #(
        .USE_PLL      (0),
        .PROGRAM_HEX  ("flags_ctx.hex")
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

    integer p0_seen, p1_seen, p0_mid, p1_mid, p0_end, p1_end, ticks;

    initial begin
        $dumpfile("tb_hcpu_flags_ctx.vcd");
        $dumpvars(0, tb_hcpu_flags_ctx);

        $display("=== tb_hcpu_flags_ctx: FLAGS milik prosesnya ===");

        repeat (20) @(posedge clk_27m);
        btn_rst_n = 1'b1;

        repeat (40000) @(posedge clk_27m);
        p0_mid = u_board.u_hcpu.u_dataram.mem[P0_COUNT];
        p1_mid = u_board.u_hcpu.u_dataram.mem[P1_COUNT];

        repeat (60000) @(posedge clk_27m);
        p0_seen = u_board.u_hcpu.u_dataram.mem[P0_SEEN];
        p1_seen = u_board.u_hcpu.u_dataram.mem[P1_SEEN];
        p0_end  = u_board.u_hcpu.u_dataram.mem[P0_COUNT];
        p1_end  = u_board.u_hcpu.u_dataram.mem[P1_COUNT];
        ticks   = u_board.u_hcpu.u_dataram.mem[TICKS];

        $display("  pid 0: baca 0x%0h, cacah %0d -> %0d", p0_seen, p0_mid, p0_end);
        $display("  pid 1: baca 0x%0h, cacah %0d -> %0d", p1_seen, p1_mid, p1_end);
        $display("  ticks = %0d", ticks);

        // Both ran, and kept running: a pattern read by a dead process proves
        // nothing at all.
        check(p0_end > p0_mid, "pid 0 masih berjalan");
        check(p1_end > p1_mid, "pid 1 masih berjalan");
        check(ticks > 10, "timer memreempt berkali-kali");

        // And each still sees its own.
        check(p0_seen == P0_PATTERN, "pid 0 membaca polanya sendiri");
        check(p1_seen == P1_PATTERN, "pid 1 membaca polanya sendiri");
        check(p0_seen != p1_seen, "keduanya tidak tertukar");

        if (errors == 0)
            $display("tb_hcpu_flags_ctx: SEMUA LULUS (6 pemeriksaan)");
        else
            $display("tb_hcpu_flags_ctx: %0d GAGAL", errors);
        $finish;
    end
endmodule
