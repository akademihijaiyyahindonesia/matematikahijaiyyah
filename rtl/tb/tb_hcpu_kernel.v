// tb_hcpu_kernel.v — the H-Kernel on the real pipeline, not the interpreter.
//
// Three processes now. The third is the guard daemon, which is H-Kernel's
// fourth responsibility in the book and the one that needed a scheduler before
// it could exist at all: HCHECK is defined there as the periodic half of a
// pair, and periodic is exactly what nothing could provide.
//
// The Python machine is a model. It agrees with the RTL about the trap unit,
// the timer and the memory window because both were built against the same
// spec, but a context switch leans on their interaction, and interaction is
// exactly where a model and a machine drift apart. So the kernel runs here
// too, and the answer that matters is one number: process B counts by a
// hundred, so its total stays an exact multiple of a hundred only if its R1
// was never once left holding process A's value.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_kernel;
    localparam A_COUNT = 12'h100;   // process A's window
    localparam B_COUNT = 12'h200;   // process B's window
    localparam C_SWEEP = 12'h300;   // the guard daemon's window
    localparam C_FAIL  = 12'h301;
    localparam CUR_PID = 12'hF00;
    localparam TICKS   = 12'hF01;

    reg clk = 0, rst_n = 0;
    wire uart_txd;
    integer errors = 0;
    integer a, b, t, dispatches, sweeps, failures;

    always #5 clk = ~clk;

    hcpu_gowin_top #(
        .USE_PLL      (0),
        .PROGRAM_HEX  ("kernel.hex")
    ) dut (
        .clk_27m   (clk),
        .btn_rst_n (rst_n),
        .uart_rxd  (1'b1),
        .uart_txd  (uart_txd),
        .led       ()
    );

    task check(input cond, input [255:0] what);
        begin
            if (!cond) begin
                $display("  GAGAL: %0s", what);
                errors = errors + 1;
            end else
                $display("  ok   : %0s", what);
        end
    endtask

    initial begin
        repeat (4) @(negedge clk); rst_n = 1;

        // Long enough for the quantum (256 counter ticks) to expire many
        // times over. Too short and every assertion below reads zero and
        // says nothing.
        repeat (400000) @(posedge clk);

        a = dut.u_hcpu.u_dataram.mem[A_COUNT];
        b = dut.u_hcpu.u_dataram.mem[B_COUNT];
        t        = dut.u_hcpu.u_dataram.mem[TICKS];
        sweeps   = dut.u_hcpu.u_dataram.mem[C_SWEEP];
        failures = dut.u_hcpu.u_dataram.mem[C_FAIL];
        dispatches = b / 100;

        $display("");
        $display("  H-Kernel di atas pipeline:");
        $display("    ticks        = %0d", t);
        $display("    A (preempt)  = %0d", a);
        $display("    B (yield)    = %0d  → %0d dispatch", b, dispatches);
        $display("    C (daemon)   = %0d sapuan, %0d kegagalan guard", sweeps, failures);
        $display("");

        check(t > 4,  "timer harus mempersenjatai ulang berkali-kali");
        check(a > 0,  "proses A harus berjalan");
        check(b > 0,  "proses B harus berjalan — dan itu membuktikan epc maju untuk cause 5");
        check((b % 100) == 0,
              "hitungan B harus kelipatan 100: register tiap proses tidak boleh bocor");
        check(dispatches * 3 >= t - 3 && dispatches * 3 <= t + 3,
              "penjadwal harus berputar di antara tiga");
        check(sweeps > 0,
              "daemon penjaga harus benar-benar berjalan, bukan sekadar terjadwal");
        check(failures == 0,
              "sapuan 28 huruf tidak boleh menemukan kegagalan guard");

        if (errors == 0)
            $display("tb_hcpu_kernel: SEMUA LULUS (7 pemeriksaan)");
        else begin
            $display("tb_hcpu_kernel: %0d GAGAL", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
