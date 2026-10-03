// tb_hijaiyyah_portal8888_gowin_top.v -- the board wrapper, driven through its UART pins only.
//
// The bench judges nothing. It sends the commands ref/portal_uart.py wrote,
// writes every reply byte to build/portal_top_reply.txt and the Portal's clock
// at each frame's first byte to build/portal_top_sof.txt, and
// `ref/portal_uart.py check` recomputes all of it with hashlib/hmac. A reply
// that does not come, or a byte nobody asked for, ends the run non-zero.
//
// The clock is the board's 27 MHz. BAUD defaults to 2,700,000 (10 clocks a
// bit) so the 9,216-byte frames finish in reasonable time; the board's own
// 115200 is -Ptb_hijaiyyah_portal8888_gowin_top.BAUD=115200, with the short
// scenario.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_portal8888_gowin_top;
    parameter integer BAUD = 2_700_000;
    localparam integer QUIET_LIMIT = 2_000_000;   // clocks with no byte either way

    reg clk = 0;
    always #18.518 clk = ~clk;          // 27 MHz

    reg  rxd = 1'b1, btn = 1'b1;
    wire txd;
    wire [5:0] led;

    hijaiyyah_portal8888_gowin_top #(.BAUD(BAUD)) dut (
        .clk_27m(clk), .btn_rst_n(btn), .uart_rxd(rxd), .uart_txd(txd), .led(led));

    localparam real BIT_NS = 1.0e9 / BAUD;

    integer quiet = 0;
    reg     finished = 1'b0, extra = 1'b0;

    task uart_send(input [7:0] b);
        integer k;
        begin
            rxd = 0; #(BIT_NS);
            for (k = 0; k < 8; k = k + 1) begin rxd = b[k]; #(BIT_NS); end
            rxd = 1; #(BIT_NS);
            quiet = 0;
        end
    endtask

    task uart_recv(output [7:0] b);
        integer k;
        begin
            @(negedge txd);
            #(BIT_NS * 1.5);
            for (k = 0; k < 8; k = k + 1) begin b[k] = txd; #(BIT_NS); end
            quiet = 0;
        end
    endtask

    integer fd, fo, fs, ncmd, rlen, clen, c, i, j, r;
    reg [7:0] sb, rb;

    // The Portal's own clock on the clock a frame's first byte enters it: what
    // a record's T_sec and T_tick must be if the time is latched at SOF.
    always @(posedge clk)
        if (dut.p_valid && dut.fcnt == 16'd0)
            $fwrite(fs, "%0d %08x %08x\n", c, dut.u_portal.ts_sec, dut.u_portal.ts_tick);

    always @(posedge clk) begin
        quiet = quiet + 1;
        if (quiet > QUIET_LIMIT && !finished) begin
            $fwrite(fo, "\n"); $fclose(fo); $fclose(fs);
            $fatal(1, "command %0d: no byte for %0d clocks", c, QUIET_LIMIT);
        end
    end

    always @(negedge txd) if (finished) extra = 1'b1;

    initial begin
        fd = $fopen("build/portal_top_cmd.txt", "r");
        if (fd == 0) $fatal(1, "run: python3 ref/portal_uart.py vec build");
        fo = $fopen("build/portal_top_reply.txt", "w");
        fs = $fopen("build/portal_top_sof.txt", "w");
        c = 0;
        #2000;
        r = $fscanf(fd, "%d\n", ncmd);
        for (c = 0; c < ncmd; c = c + 1) begin
            r = $fscanf(fd, "%d %d\n", rlen, clen);
            fork
                begin
                    for (i = 0; i < clen; i = i + 1) begin
                        r = $fscanf(fd, "%h\n", sb);
                        uart_send(sb);
                    end
                end
                begin
                    for (j = 0; j < rlen; j = j + 1) begin
                        uart_recv(rb);
                        $fwrite(fo, "%02x", rb);
                    end
                end
            join
            $fwrite(fo, "\n");
        end
        finished = 1'b1;
        #(BIT_NS * 40);
        $fclose(fo); $fclose(fs);
        if (extra) $fatal(1, "a byte came after the last reply");
        $display("tb_hijaiyyah_portal8888_gowin_top: %0d commands at %0d baud, replies written",
                 ncmd, BAUD);
        $finish;
    end
endmodule

`default_nettype wire
