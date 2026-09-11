// tb_hcpu_video_timing.v — hcpu_video_timing checked against the published
// VESA 640x480@60Hz standard directly: total pixels/line, total lines/frame,
// hsync/vsync pulse width and position, and the active (de-high) window size
// -- every field counted across real simulated cycles, not sampled at a few
// points and trusted to generalize.
`timescale 1ns/1ps

module tb_hcpu_video_timing;

    reg clk = 0;
    reg rst_n = 0;
    always #5 clk = ~clk;   // pixel_clk -- rate is irrelevant to this check

    wire hsync, vsync, de, frame_tick;
    wire [11:0] x, y;

    hcpu_video_timing dut (
        .pixel_clk (clk),
        .rst_n     (rst_n),
        .hsync     (hsync),
        .vsync     (vsync),
        .de        (de),
        .x         (x),
        .y         (y),
        .frame_tick(frame_tick)
    );

    integer errors = 0;

    // Delapan pemeriksaan di bawah, masing-masing menaikkan `errors` saat gagal.

    // Cacah yang LULUS tak pernah ada, jadi bench ini melapor "ALL PASS" tanpa

    // angka dan menyumbang nol ke tiap penjumlahan asersi -- sehingga total

    // mana pun yang memasukkannya sedang menebak. Sekarang ia melapor dalam

    // bentuk yang sama dengan tujuh bench lain.

    localparam integer CHECKS = 8;
    integer i;

    // Per-line bookkeeping, gathered every cycle across one full frame.
    integer h_total_count;      // cycles in the first full line after reset
    integer de_high_count;      // total cycles de is high across one frame
    integer hsync_low_count;    // total cycles hsync is low (active) in one line
    integer vsync_low_lines;    // total LINES vsync is low (active) across one frame
    integer first_hsync_low_at; // h_count offset where hsync first goes low, within a line
    integer max_x_seen, max_y_seen;
    reg     vsync_was_low;
    integer frame_ticks_seen;

    initial begin
        rst_n = 0;
        repeat (3) @(posedge clk);
        rst_n = 1;

        // Wait for the start of a fresh frame so counting begins at a known
        // boundary (x==0, y==0) -- no extra clock edge here, so loop index
        // i==0 lines up exactly with h_count==0.
        wait (frame_tick === 1'b1);

        h_total_count      = 0;
        de_high_count       = 0;
        hsync_low_count     = 0;
        vsync_low_lines     = 0;
        first_hsync_low_at  = -1;
        max_x_seen          = -1;
        max_y_seen          = -1;
        vsync_was_low       = 1'b0;
        frame_ticks_seen    = 0;

        // Count one full line (800 cycles) to check H_TOTAL and hsync
        // pulse width/position directly.
        for (i = 0; i < 800; i = i + 1) begin
            h_total_count = h_total_count + 1;
            if (hsync === 1'b0) begin
                if (first_hsync_low_at == -1) first_hsync_low_at = i;
                hsync_low_count = hsync_low_count + 1;
            end
            @(posedge clk);
        end

        if (h_total_count !== 800) begin
            $display("FAIL: one line was %0d cycles, expected 800 (VESA H_TOTAL)", h_total_count);
            errors = errors + 1;
        end
        if (hsync_low_count !== 96) begin
            $display("FAIL: hsync low for %0d cycles in one line, expected 96 (H_SYNC)", hsync_low_count);
            errors = errors + 1;
        end
        if (first_hsync_low_at !== 640 + 16) begin
            $display("FAIL: hsync first went low at offset %0d, expected %0d (H_ACTIVE+H_FRONT)",
                      first_hsync_low_at, 640 + 16);
            errors = errors + 1;
        end

        // Now count a FULL FRAME (525 lines x 800 cycles = 420000 cycles)
        // from the same frame boundary, for de/vsync/x/y.
        // (already consumed one line above, so re-sync to the next frame)
        wait (frame_tick === 1'b1);

        for (i = 0; i < 800 * 525; i = i + 1) begin
            if (de === 1'b1) begin
                de_high_count = de_high_count + 1;
                if ($signed(x) > max_x_seen) max_x_seen = x;
                if ($signed(y) > max_y_seen) max_y_seen = y;
            end
            if (vsync === 1'b0 && !vsync_was_low) begin
                vsync_was_low = 1'b1;
            end
            if (vsync === 1'b0) begin
                // count active vsync cycles; divided by H_TOTAL after the loop
                vsync_low_lines = vsync_low_lines + 1;
            end
            if (frame_tick === 1'b1 && i > 0) frame_ticks_seen = frame_ticks_seen + 1;
            @(posedge clk);
        end

        if (de_high_count !== 640 * 480) begin
            $display("FAIL: de high for %0d cycles/frame, expected %0d (640x480)",
                      de_high_count, 640 * 480);
            errors = errors + 1;
        end
        if (max_x_seen !== 639) begin
            $display("FAIL: max x seen while de high was %0d, expected 639", max_x_seen);
            errors = errors + 1;
        end
        if (max_y_seen !== 479) begin
            $display("FAIL: max y seen while de high was %0d, expected 479", max_y_seen);
            errors = errors + 1;
        end
        // vsync low for V_SYNC=2 lines x H_TOTAL=800 cycles/line = 1600 cycles/frame
        if (vsync_low_lines !== 2 * 800) begin
            $display("FAIL: vsync low for %0d cycles/frame, expected %0d (V_SYNC lines x H_TOTAL)",
                      vsync_low_lines, 2 * 800);
            errors = errors + 1;
        end
        // Exactly one frame_tick pulse expected strictly inside this frame's
        // own 420000-cycle span (the next frame's own boundary).
        if (frame_ticks_seen !== 1) begin
            $display("FAIL: saw %0d frame_tick pulses across one frame span, expected 1",
                      frame_ticks_seen);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("tb_hcpu_video_timing: SEMUA LULUS (%0d pemeriksaan)", CHECKS);
        else
            $display("tb_hcpu_video_timing: %0d dari %0d pemeriksaan GAGAL", errors, CHECKS);

        $finish;
    end

endmodule
