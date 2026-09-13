// tb_hcpu_shell.v — the shell answers the serial line, on the real pipeline.
//
// tb_hcpu_kernel.v proved a scheduler with processes that only counted; this
// bench proves the piece M3 asks for on top of it: a user process that READS,
// a kernel that serves the read, and an answer that comes back out of the
// same wire the command went in on.
//
// Nothing here is hierarchical except the two counters at the end. The
// commands go in as real serial bytes on uart_rxd and the answers are decoded
// off uart_txd by a receiver timed from BIT_NS rather than from the RTL --
// tb_gowin_loader_nui.v's own pattern, and the reason is the same: a bench
// that reads the design's own timing cannot catch the design getting the
// timing wrong.
//
// ── what each command proves ────────────────────────────────────
//   'A' -> 65    the whole route. The byte crossed the wire into the RX
//                register, the SHELL asked for it by SYSCALL (it cannot reach
//                0xFF0 itself -- that address is outside its window), the
//                kernel read it through hal_uart_rx_get, handed it back in
//                the block, and the shell asked the kernel to print it. 65 is
//                ASCII 'A', which this program did not choose.
//   'p' -> 2 0 1 the process model. The count is READ from the word the
//                kernel published into the shell's own window, then every pid
//                below it.
//
// And the counter at 0x100 is pid 0, which never yields: it can only have
// advanced because the TIMER took the CPU away from it. Preemption, measured
// rather than assumed.
`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hcpu_shell;
    localparam real    HALF_PERIOD = 18.5;          // 27 MHz
    localparam integer BAUD        = 115200;
    localparam real    BIT_NS      = 1_000_000_000.0 / BAUD;

    localparam P0_COUNT = 12'h100;                  // pid 0's window
    localparam CUR_PID  = 12'hF00;
    localparam TICKS    = 12'hF01;

    reg  clk_27m = 1'b0;
    reg  btn_rst_n = 1'b0;
    reg  uart_rxd = 1'b1;                            // idle high
    wire uart_txd;
    wire [5:0] led;

    always #HALF_PERIOD clk_27m = ~clk_27m;

    hcpu_gowin_top #(
        .USE_PLL      (0),
        .BAUD         (BAUD),
        .PROGRAM_HEX  ("shell.hex")
    ) u_board (
        .clk_27m   (clk_27m),
        .btn_rst_n (btn_rst_n),
        .uart_rxd  (uart_rxd),
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

    // ── one byte to the shell, LSB first ────────────────────────
    task send_byte(input [7:0] b);
        integer i;
        begin
            uart_rxd = 1'b0;  #BIT_NS;                // start
            for (i = 0; i < 8; i = i + 1) begin
                uart_rxd = b[i]; #BIT_NS;             // LSB first
            end
            uart_rxd = 1'b1;  #BIT_NS;                // stop
        end
    endtask

    // ── independent receiver for whatever the shell answers ─────
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

    integer p0_before, p0_after, ticks_after, i;

    initial begin
        $dumpfile("tb_hcpu_shell.vcd");
        $dumpvars(0, tb_hcpu_shell);

        $display("=== tb_hcpu_shell: the shell answers the serial line ===");

        repeat (20) @(posedge clk_27m);
        btn_rst_n = 1'b1;

        // Boot, then long enough for the scheduler to be running both blocks.
        repeat (20000) @(posedge clk_27m);
        p0_before = u_board.u_hcpu.u_dataram.mem[P0_COUNT];

        // ── 'A' -> 65 ───────────────────────────────────────────
        send_byte(8'h41);
        repeat (60000) @(posedge clk_27m);

        check(count == 3, "echo: three bytes back");
        if (count >= 3) begin
            check(got[0] == 8'h36 && got[1] == 8'h35 && got[2] == 8'h0A,
                  "'A' came back as 65");
        end

        // ── 'p' -> 2 0 1 ────────────────────────────────────────
        count = 0;
        send_byte(8'h70);
        repeat (90000) @(posedge clk_27m);

        check(count == 6, "ps: six bytes back");
        if (count >= 6) begin
            check(got[0] == 8'h32 && got[1] == 8'h0A, "ps: two processes");
            check(got[2] == 8'h30 && got[3] == 8'h0A, "ps: pid 0");
            check(got[4] == 8'h31 && got[5] == 8'h0A, "ps: pid 1");
        end

        // ── preemption, and the kernel still dispatching ────────
        p0_after    = u_board.u_hcpu.u_dataram.mem[P0_COUNT];
        ticks_after = u_board.u_hcpu.u_dataram.mem[TICKS];

        $display("  pid 0 counter %0d -> %0d, ticks %0d",
                 p0_before, p0_after, ticks_after);
        check(ticks_after > 2, "kernel keeps dispatching");

        // ── PREEMPTION, AND THE ROW THIS ONE REPLACES ───────────
        // This used to expect pid 0 NOT to advance, with the reason written
        // beside it: a process taken away by the timer was resumed at address
        // 0, because a trap landing in a redirect's shadow read Fetch's
        // "nothing here" as an address. hcpu_fetch now says so in a signal of
        // its own and hcpu_top drives the trap unit's pc_valid from it, so the
        // trap waits a cycle for a real PC instead of inventing one.
        //
        // pid 0 never yields. It can only have advanced because the TIMER took
        // the CPU away from it and the kernel put it back where it was.
        check(p0_after > p0_before, "pid 0 jalan lagi sesudah preempt");

        if (errors == 0)
            $display("tb_hcpu_shell: SEMUA LULUS (7 pemeriksaan)");
        else
            $display("tb_hcpu_shell: %0d GAGAL", errors);
        $finish;
    end
endmodule
