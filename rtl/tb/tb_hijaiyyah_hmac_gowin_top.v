// tb_hijaiyyah_hmac_gowin_top.v — the board wrapper, driven through its UART pins only.
// Real 27 MHz clock, real 115200 baud: what the host script will see.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_hmac_gowin_top;
    reg clk = 0;
    always #18.518 clk = ~clk;          // 27 MHz

    reg  rxd = 1'b1, btn = 1'b1;
    wire txd;
    wire [5:0] led;

    hijaiyyah_hmac_gowin_top dut (.clk_27m(clk), .btn_rst_n(btn), .uart_rxd(rxd),
                        .uart_txd(txd), .led(led));

    localparam real BIT_NS = 1.0e9 / 115200.0;

    task uart_send(input [7:0] b);
        integer k;
        begin
            rxd = 0; #(BIT_NS);
            for (k = 0; k < 8; k = k + 1) begin rxd = b[k]; #(BIT_NS); end
            rxd = 1; #(BIT_NS);
        end
    endtask

    task uart_recv(output [7:0] b);
        integer k;
        begin
            @(negedge txd);
            #(BIT_NS * 1.5);
            for (k = 0; k < 8; k = k + 1) begin b[k] = txd; #(BIT_NS); end
        end
    endtask

    integer fd, n, len, i, r, v, pass = 0, fail = 0;
    reg [511:0] key;
    reg [7:0]   mem [0:4095];
    reg [255:0] want, got;
    reg [31:0]  cyc;
    reg [7:0]   b;

    initial begin
        #2000;
        fd = $fopen("rtl/tb/hmac_vectors.txt", "r");
        if (fd == 0) $fatal(1, "cannot open rtl/tb/hmac_vectors.txt -- run from the repository root");
        r = $fscanf(fd, "%d\n", n);
        for (v = 0; v < 10; v = v + 1) begin          // RFC 4231 1-7 + 3 random
            r = $fscanf(fd, "%h\n", key);
            r = $fscanf(fd, "%d\n", len);
            for (i = 0; i < len; i = i + 1) r = $fscanf(fd, "%h\n", mem[i]);
            r = $fscanf(fd, "%h\n", want);
            fork
                begin
                    for (i = 0; i < 64; i = i + 1) uart_send(key[511 - 8*i -: 8]);
                    uart_send(len[15:8]); uart_send(len[7:0]);
                    for (i = 0; i < len; i = i + 1) uart_send(mem[i]);
                end
                begin : rx
                    integer j;
                    for (j = 0; j < 32; j = j + 1) begin uart_recv(b); got = {got[247:0], b}; end
                    for (j = 0; j < 4; j = j + 1)  begin uart_recv(b); cyc = {cyc[23:0], b}; end
                end
            join
            if (got === want) pass = pass + 1;
            else begin fail = fail + 1; $display("FAIL case %0d got=%h want=%h", v, got, want); end
            $display("case %0d len=%0d engine_clocks=%0d %s", v, len, cyc,
                     (got === want) ? "OK" : "BAD");
        end
        $display("HMAC wrapper (UART) Tests: %0d PASS, %0d FAIL", pass, fail);
        if (fail != 0) $fatal(1, "hijaiyyah_hmac_gowin_top: %0d case(s) wrong", fail);
        $display("SEMUA LULUS (%0d pemeriksaan)", pass);
        $finish;
    end
endmodule
`default_nettype wire
