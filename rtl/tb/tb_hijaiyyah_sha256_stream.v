// tb_hijaiyyah_sha256_stream.v — every vector in rtl/tb/sha256_vectors.txt, digest compared bit-exact.
// Also measures clocks per message, and checks the one-million-'a' vector.
`timescale 1ns/1ps
`default_nettype none

module tb_hijaiyyah_sha256_stream;
    reg clk = 0, rst_n = 0;
    always #5 clk = ~clk;

    reg          start = 0, use_prefix = 0, byte_valid = 0, finish = 0;
    reg  [511:0] prefix = 0;
    reg  [7:0]   byte_in = 0;
    wire         byte_ready, idle, done;
    wire [255:0] digest;

    hijaiyyah_sha256_stream dut (
        .clk(clk), .rst_n(rst_n), .start(start), .use_prefix(use_prefix),
        .prefix(prefix), .byte_valid(byte_valid), .byte_in(byte_in),
        .byte_ready(byte_ready), .finish(finish), .idle(idle), .done(done),
        .digest(digest));

    integer fd, n, len, i, r, pass = 0, fail = 0, v;
    reg [7:0]   mem [0:4095];
    reg [255:0] want;
    integer t0, cycles;
    integer clk_count = 0;
    always @(posedge clk) clk_count = clk_count + 1;

    task send_byte(input [7:0] b);
        begin
            @(negedge clk);
            while (!byte_ready) @(negedge clk);
            byte_valid = 1; byte_in = b;
            @(negedge clk);
            byte_valid = 0;
        end
    endtask

    task hash_mem(input integer l);
        begin
            @(negedge clk); while (!idle) @(negedge clk);
            start = 1; @(negedge clk); start = 0;
            for (i = 0; i < l; i = i + 1) send_byte(mem[i]);
            @(negedge clk); while (!byte_ready) @(negedge clk);
            finish = 1; @(negedge clk); finish = 0;
            while (!done) @(negedge clk);
        end
    endtask

    initial begin
        #22 rst_n = 1;
        fd = $fopen("rtl/tb/sha256_vectors.txt", "r");
        if (fd == 0) $fatal(1, "cannot open rtl/tb/sha256_vectors.txt -- run from the repository root");
        r = $fscanf(fd, "%d\n", n);
        for (v = 0; v < n; v = v + 1) begin
            r = $fscanf(fd, "%d\n", len);
            for (i = 0; i < len; i = i + 1) r = $fscanf(fd, "%h\n", mem[i]);
            r = $fscanf(fd, "%h\n", want);
            t0 = clk_count;
            hash_mem(len);
            cycles = clk_count - t0;
            if (digest === want) pass = pass + 1;
            else begin
                fail = fail + 1;
                $display("FAIL len=%0d got=%h want=%h", len, digest, want);
            end
            if (v < 4) $display("NIST len=%0d cycles=%0d digest=%h %s", len, cycles,
                                digest, (digest === want) ? "OK" : "BAD");
        end
        $fclose(fd);

        // FIPS 180-4 long vector: one million 'a' (0x61)
        @(negedge clk); while (!idle) @(negedge clk);
        start = 1; @(negedge clk); start = 0;
        t0 = clk_count;
        for (i = 0; i < 1000000; i = i + 1) send_byte(8'h61);
        @(negedge clk); while (!byte_ready) @(negedge clk);
        finish = 1; @(negedge clk); finish = 0;
        while (!done) @(negedge clk);
        want = 256'hcdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0;
        if (digest === want) pass = pass + 1; else begin
            fail = fail + 1; $display("FAIL million-a got=%h", digest); end
        $display("MILLION-a cycles=%0d digest=%h %s", clk_count - t0, digest,
                 (digest === want) ? "OK" : "BAD");

        $display("SHA-256 stream Tests: %0d PASS, %0d FAIL", pass, fail);
        if (fail != 0) $fatal(1, "hijaiyyah_sha256_stream: %0d vector(s) wrong", fail);
        $display("SEMUA LULUS (%0d pemeriksaan)", pass);
        $finish;
    end
endmodule
`default_nettype wire
