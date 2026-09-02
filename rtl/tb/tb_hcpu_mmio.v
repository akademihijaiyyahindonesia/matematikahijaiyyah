// tb_hcpu_mmio.v — the bus a program will actually drive.
//
// Six properties, each one a way MMIO goes quietly wrong: RAM below the base
// still works, a peripheral write does not land in RAM, a read has the same
// one-cycle latency as the RAM, a received byte is held and its ready flag
// clears on read, an unread byte followed by another is reported as an
// overrun rather than dropped, and the timer is reachable through the bus.
`timescale 1ns/1ps
`default_nettype none

`include "hcpu_pkg.vh"

module tb_hcpu_mmio;
    localparam integer CLK_HZ  = 27_000_000;
    localparam integer BAUD    = 115200;
    localparam integer DIVISOR = CLK_HZ / BAUD;

    reg clk = 1'b0, rst_n = 1'b0, re = 1'b0, we = 1'b0, line = 1'b1;
    reg [`DATA_ADDR_W-1:0] addr = 12'd0;
    reg [`XLEN-1:0] wdata = 32'd0;
    wire [`XLEN-1:0] rdata;

    wire ram_re, ram_we;
    wire [`DATA_ADDR_W-1:0] ram_addr;
    wire [`XLEN-1:0] ram_wdata, ram_rdata;

    integer bad = 0, b;
    reg [`XLEN-1:0] got, first;

    // Watch the RAM write-enable directly. The first version of this
    // testbench wrote to a peripheral address and then read a *different* RAM
    // address to prove nothing landed — which proves nothing, because the
    // write would have gone to the peripheral's own address in RAM. Ungating
    // `ram_we` passed it. The signal is the only place the property is
    // visible.
    integer ram_writes_during_periph = 0;
    always @(posedge clk)
        if (rst_n && ram_we && addr >= 12'hFF0)
            ram_writes_during_periph = ram_writes_during_periph + 1;

    always #5 clk = ~clk;

    hcpu_mmio #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) dut (
        .clk(clk), .rst_n(rst_n), .re(re), .we(we), .addr(addr),
        .wdata(wdata), .rdata(rdata),
        .ram_re(ram_re), .ram_we(ram_we), .ram_addr(ram_addr),
        .ram_wdata(ram_wdata), .ram_rdata(ram_rdata),
        .uart_rx_in(line), .uart_tx_busy(1'b0));

    hcpu_dataram u_ram (.clk(clk), .re(ram_re), .we(ram_we),
        .addr(ram_addr), .wdata(ram_wdata), .rdata(ram_rdata));

    task bus_write; input [11:0] a; input [31:0] d;
        begin
            @(negedge clk); addr = a; wdata = d; we = 1'b1;
            @(negedge clk); we = 1'b0;
        end
    endtask

    task bus_read; input [11:0] a;
        begin
            @(negedge clk); addr = a; re = 1'b1;
            @(negedge clk); re = 1'b0;          // data valid one cycle later
            #1; got = rdata;
        end
    endtask

    task send; input [7:0] byte_in;
        begin
            line = 1'b0; repeat (DIVISOR) @(posedge clk);
            for (b = 0; b < 8; b = b + 1) begin
                line = byte_in[b]; repeat (DIVISOR) @(posedge clk);
            end
            line = 1'b1; repeat (DIVISOR * 2) @(posedge clk);
        end
    endtask

    initial begin
        repeat (3) @(negedge clk);
        rst_n = 1'b1;

        // 1. RAM below the base still behaves
        bus_write(12'h010, 32'hDEADBEEF);
        bus_read (12'h010);
        if (got !== 32'hDEADBEEF) begin
            bad = bad + 1; $display("MISMATCH RAM read %h", got);
        end

        // 2. a peripheral write must not reach RAM
        bus_write(12'hFF5, 32'h0000_1234);      // timer compare
        bus_write(12'hFF6, 32'd0);              // clear timer status
        if (ram_writes_during_periph !== 0) begin
            bad = bad + 1;
            $display("MISMATCH %0d peripheral writes reached RAM",
                     ram_writes_during_periph);
        end
        bus_read (12'h010);
        if (got !== 32'hDEADBEEF) begin
            bad = bad + 1; $display("MISMATCH RAM changed under a peripheral write");
        end

        // 3. the compare reads back through the bus
        bus_read(12'hFF5);
        if (got !== 32'h0000_1234) begin
            bad = bad + 1; $display("MISMATCH compare read back %h", got);
        end

        // 4. the counter is running
        bus_read(12'hFF4); first = got;
        repeat (12) @(posedge clk);
        bus_read(12'hFF4);
        if (got <= first) begin
            bad = bad + 1; $display("MISMATCH counter did not advance");
        end

        // 5. a byte arrives, is held, and ready clears on read
        send(8'h41);
        bus_read(12'hFF1);
        if (got[0] !== 1'b1) begin
            bad = bad + 1; $display("MISMATCH ready not set after a byte");
        end
        bus_read(12'hFF0);
        if (got !== 32'h0000_0041) begin
            bad = bad + 1; $display("MISMATCH rx data %h", got);
        end
        bus_read(12'hFF1);
        if (got[0] !== 1'b0) begin
            bad = bad + 1; $display("MISMATCH ready did not clear on read");
        end

        // 6. two bytes without a read is an overrun, not a silent drop
        send(8'h42);
        send(8'h43);
        bus_read(12'hFF1);
        if (got[2] !== 1'b1) begin
            bad = bad + 1; $display("MISMATCH overrun not reported (status %h)", got);
        end

        if (bad == 0)
            $display("PASS: RAM, peripherals, latency, hold, and overrun");
        else
            $display("FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule

`default_nettype wire
