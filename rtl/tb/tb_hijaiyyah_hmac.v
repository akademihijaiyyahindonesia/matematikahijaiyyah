// tb_hijaiyyah_hmac.v — RFC 4231 cases 1-7 and random keys/messages, bit-exact.
// Also checks that timing is independent of key and message contents.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_hmac;
    reg clk = 0, rst_n = 0;
    always #5 clk = ~clk;

    reg          start = 0, byte_valid = 0, finish = 0;
    reg  [511:0] key = 0;
    reg  [7:0]   byte_in = 0;
    wire         byte_ready, idle, done;
    wire [255:0] mac;

    hijaiyyah_hmac dut (
        .clk(clk), .rst_n(rst_n), .start(start), .key(key),
        .byte_valid(byte_valid), .byte_in(byte_in), .byte_ready(byte_ready),
        .finish(finish), .idle(idle), .done(done), .mac(mac));

    integer fd, n, len, i, r, v, pass = 0, fail = 0;
    reg [7:0]   mem [0:4095];
    reg [255:0] want;
    integer clk_count = 0, t0, c_a, c_b;
    always @(posedge clk) clk_count = clk_count + 1;

    task run(input integer l);
        begin
            @(negedge clk); while (!idle) @(negedge clk);
            start = 1; @(negedge clk); start = 0;
            for (i = 0; i < l; i = i + 1) begin
                while (!byte_ready) @(negedge clk);
                byte_valid = 1; byte_in = mem[i];
                @(negedge clk);
                byte_valid = 0;
            end
            while (!byte_ready) @(negedge clk);
            finish = 1; @(negedge clk); finish = 0;
            while (!done) @(negedge clk);
        end
    endtask

    initial begin
        #22 rst_n = 1;
        fd = $fopen("rtl/tb/hmac_vectors.txt", "r");
        if (fd == 0) $fatal(1, "cannot open rtl/tb/hmac_vectors.txt -- run from the repository root");
        r = $fscanf(fd, "%d\n", n);
        for (v = 0; v < n; v = v + 1) begin
            r = $fscanf(fd, "%h\n", key);
            r = $fscanf(fd, "%d\n", len);
            for (i = 0; i < len; i = i + 1) r = $fscanf(fd, "%h\n", mem[i]);
            r = $fscanf(fd, "%h\n", want);
            t0 = clk_count;
            run(len);
            if (mac === want) pass = pass + 1;
            else begin
                fail = fail + 1;
                $display("FAIL case %0d len=%0d got=%h want=%h", v, len, mac, want);
            end
            if (v < 7) $display("RFC4231-%0d len=%0d cycles=%0d %s", v + 1, len,
                                clk_count - t0, (mac === want) ? "OK" : "BAD");
        end
        $fclose(fd);

        // Timing independence: same length, different key and data.
        for (i = 0; i < 100; i = i + 1) mem[i] = 8'h00;
        key = 512'd0;
        t0 = clk_count; run(100); c_a = clk_count - t0;
        for (i = 0; i < 100; i = i + 1) mem[i] = 8'hff;
        key = {64{8'hff}};
        t0 = clk_count; run(100); c_b = clk_count - t0;
        if (c_a == c_b) pass = pass + 1; else fail = fail + 1;
        $display("TIMING 100 bytes: zeros=%0d cycles, ones=%0d cycles %s",
                 c_a, c_b, (c_a == c_b) ? "EQUAL" : "DIFFERENT");

        $display("HMAC Tests: %0d PASS, %0d FAIL", pass, fail);
        if (fail != 0) $fatal(1, "hijaiyyah_hmac: %0d check(s) wrong", fail);
        $display("SEMUA LULUS (%0d pemeriksaan)", pass);
        $finish;
    end
endmodule
`default_nettype wire
