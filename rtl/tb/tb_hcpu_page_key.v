// tb_hcpu_page_key.v — one button, and it must not mean both things at once.
//
// The audit that opened M5 found exactly one human input on the HDMI slot, so
// short press and long press have to be told apart by the same contact. The
// failure that matters is not a missed press: it is a LONG press that also
// advances the page on release, so holding the button to go home lands you on
// page 1 instead of page 0.
//
// The thresholds are parameters, and this bench shrinks them. A one-second
// long press at 74.25 MHz is 74 million cycles; simulating that to learn
// something about a comparator would take minutes and prove the same thing
// as simulating sixty.

`timescale 1ns/1ps
`default_nettype none

module tb_hcpu_page_key;

    localparam DEB   = 4;      // the board uses 750,000
    localparam LONGP = 60;     // the board uses 74,250,000
    localparam PAGES = 9;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg key_n = 1'b1;          // active low, idle high
    always #5 clk = ~clk;

    wire [3:0] page;

    hcpu_page_key #(.DEBOUNCE(DEB), .LONG(LONGP), .PAGES(PAGES)) dut (
        .clk(clk), .rst_n(rst_n), .key_n(key_n), .page(page)
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

    task press;
        input integer cycles;
        begin
            key_n = 1'b0;
            repeat (cycles) @(posedge clk);
            key_n = 1'b1;
            repeat (40) @(posedge clk);
        end
    endtask

    // A contact that chatters on the way down, which is what a real one does.
    task bouncy_press;
        input integer cycles;
        integer k;
        begin
            for (k = 0; k < 6; k = k + 1) begin
                key_n = ~key_n;
                @(posedge clk);
            end
            key_n = 1'b0;
            repeat (cycles) @(posedge clk);
            for (k = 0; k < 6; k = k + 1) begin
                key_n = ~key_n;
                @(posedge clk);
            end
            key_n = 1'b1;
            repeat (40) @(posedge clk);
        end
    endtask

    integer i;
    reg wrapped;

    initial begin
        $display("=== tb_hcpu_page_key: pendek maju, panjang pulang ===");

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);

        check(page == 4'd0, "mulai di halaman 0");

        press(20);
        check(page == 4'd1, "tekan pendek: ke halaman 1");

        press(20);
        press(20);
        check(page == 4'd3, "tiga pendek: halaman 3");

        // ── the long press, and the release that must do nothing ──
        press(LONGP + 20);
        check(page == 4'd0, "tekan panjang: pulang ke 0");

        // If the release of a long press also counted, this would be 1.
        repeat (40) @(posedge clk);
        check(page == 4'd0, "lepas dari panjang: tetap 0");

        // ── bouncing is not four presses ────────────────────────
        bouncy_press(20);
        check(page == 4'd1, "kontak memantul: satu maju");

        // ── the counter wraps rather than running off ───────────
        wrapped = 1'b0;
        for (i = 0; i < PAGES; i = i + 1) begin
            press(20);
            if (page >= PAGES) wrapped = 1'b1;
        end
        check(!wrapped, "halaman tak pernah lewati batas");
        check(page == 4'd1, "sesudah satu putaran: kembali");

        if (errors == 0)
            $display("tb_hcpu_page_key: SEMUA LULUS (8 pemeriksaan)");
        else
            $display("tb_hcpu_page_key: %0d GAGAL", errors);
        $finish;
    end

    initial begin
        #200_000;
        $display("tb_hcpu_page_key: GAGAL -- waktu habis");
        $finish;
    end

endmodule

`default_nettype wire
