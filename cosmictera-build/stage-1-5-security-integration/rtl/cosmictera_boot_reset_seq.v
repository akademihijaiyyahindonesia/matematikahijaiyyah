// ============================================================================
// cosmictera_boot_reset_seq.v — Stage 1.2 PLL Lock Qualification & Reset Sequencer
//
// Enforces deterministic hardware initialization order across the 27.000 MHz
// reference clock domain and the 74.250 MHz pixel clock domain:
//   1. Synchronize raw rPLL `pll_lock` into `clk_27m`.
//   2. Qualify `pll_lock` for >= 2.0 ms (54,000 cycles at 27 MHz; resets to 0
//      immediately on any lock glitch).
//   3. Release active-low `clkdiv_rst_n` (CLKDIV.RESETN = 1'b1) FIRST so
//      `pixel_clk` (74.25 MHz) begins oscillating cleanly.
//   4. Wait `CLKDIV_WAIT_CYCLES` reference clocks, then release active-high
//      `oser_rst` (OSER10.RESET = 1'b0) synchronously in `pixel_clk`.
//   5. Wait `TIMING_WAIT_CYCLES` reference clocks, then release active-low
//      `vid_rst_n` synchronously in `pixel_clk`.
//   6. Detect lock loss after qualification, assert safe staged reset, count
//      relock recoveries (`relock_count`), and drive screen state transitions
//      (`SCREEN_STARTUP`, `SCREEN_READY`, `SCREEN_ERROR`).
// ============================================================================

`default_nettype none

module cosmictera_boot_reset_seq #(
    parameter integer LOCK_QUAL_CYCLES   = 54_000, // 2.0 ms at 27.000 MHz
    parameter integer CLKDIV_WAIT_CYCLES = 16,     // ~592 ns after CLKDIV release
    parameter integer TIMING_WAIT_CYCLES = 32,     // ~1.18 us after CLKDIV release
    parameter integer STARTUP_FRAMES     = 1       // frames in STARTUP before READY
) (
    input  wire       clk_27m,
    input  wire       ext_rst_n,        // 1'b1 in board build (pin 87 is MODE1); testbench controllable
    input  wire       pll_lock,         // raw lock from TMDS_rPLL
    input  wire       pixel_clk,        // 74.25 MHz from CLKDIV
    input  wire       de,               // active video data-enable
    input  wire       frame_tick,       // start-of-frame pulse from hcpu_video_timing
    input  wire       logo_rom_ok,      // 1'b1 when logo ROM self-check passes
    input  wire       fault_inject,     // 1'b1 to force error state in verification

    // Reset outputs to primitives
    output reg        clkdiv_rst_n,     // active-low reset for CLKDIV.RESETN
    output wire       oser_rst,         // active-high reset for OSER10.RESET (sync to pixel_clk)
    output wire       vid_rst_n,        // active-low reset for video timing & pipeline (sync to pixel_clk)

    // Stage status outputs (synchronized to pixel_clk for compositor & events)
    output wire       st_ref_clk_ok,
    output wire       st_pll_locked,
    output wire       st_pix_clk_ok,
    output wire       st_clkdiv_ok,
    output wire       st_tmds_ok,
    output wire       st_timing_ok,
    output wire       st_font_ok,
    output wire       st_logo_ok,
    output wire       st_comp_ok,
    output wire       st_vout_ok,

    output wire       lock_lost_pix,    // current lock-loss fault active
    output wire       lock_lost_sticky_pix, // sticky indicator that lock was lost at least once
    output wire [7:0] relock_count_pix, // number of successful relocks after lock loss
    output reg  [1:0] screen_state      // 0 = STARTUP, 1 = DISPLAY READY, 2 = DISPLAY ERROR
);

    localparam [1:0] SCREEN_STARTUP = 2'd0,
                     SCREEN_READY   = 2'd1,
                     SCREEN_ERROR   = 2'd2;

    localparam integer QUAL_W = $clog2(LOCK_QUAL_CYCLES + 1);
    localparam integer WAIT_W = $clog2(TIMING_WAIT_CYCLES + 1);

    // ── 1. 27 MHz reference clock domain: PLL lock qualification ─
    reg pll_s1 = 1'b0, pll_s2 = 1'b0;
    always @(posedge clk_27m or negedge ext_rst_n) begin
        if (!ext_rst_n) begin
            pll_s1 <= 1'b0;
            pll_s2 <= 1'b0;
        end else begin
            pll_s1 <= pll_lock;
            pll_s2 <= pll_s1;
        end
    end

    reg [QUAL_W-1:0] qual_cnt             = {QUAL_W{1'b0}};
    reg [WAIT_W-1:0] seq_cnt              = {WAIT_W{1'b0}};
    reg              pll_qual_27m         = 1'b0;
    reg              ever_qualified_27m   = 1'b0;
    reg              in_lock_loss_27m     = 1'b0;
    reg              lock_lost_sticky_27m = 1'b0;
    reg [7:0]        relock_count_27m     = 8'd0;
    reg              oser_rel_27m         = 1'b0;
    reg              timing_rel_27m       = 1'b0;

    initial begin
        clkdiv_rst_n = 1'b0;
        screen_state = SCREEN_STARTUP;
    end

    always @(posedge clk_27m or negedge ext_rst_n) begin
        if (!ext_rst_n) begin
            qual_cnt             <= {QUAL_W{1'b0}};
            seq_cnt              <= {WAIT_W{1'b0}};
            pll_qual_27m         <= 1'b0;
            ever_qualified_27m   <= 1'b0;
            in_lock_loss_27m     <= 1'b0;
            lock_lost_sticky_27m <= 1'b0;
            relock_count_27m     <= 8'd0;
            clkdiv_rst_n         <= 1'b0;
            oser_rel_27m         <= 1'b0;
            timing_rel_27m       <= 1'b0;
        end else if (!pll_s2) begin
            qual_cnt       <= {QUAL_W{1'b0}};
            seq_cnt        <= {WAIT_W{1'b0}};
            pll_qual_27m   <= 1'b0;
            clkdiv_rst_n   <= 1'b0;
            oser_rel_27m   <= 1'b0;
            timing_rel_27m <= 1'b0;
            if (ever_qualified_27m) begin
                in_lock_loss_27m     <= 1'b1;
                lock_lost_sticky_27m <= 1'b1;
            end
        end else begin
            if (!pll_qual_27m) begin
                if (qual_cnt >= LOCK_QUAL_CYCLES - 1) begin
                    pll_qual_27m       <= 1'b1;
                    clkdiv_rst_n       <= 1'b1; // Stage 1: Release CLKDIV.RESETN first
                    seq_cnt            <= {WAIT_W{1'b0}};
                    ever_qualified_27m <= 1'b1;
                    if (in_lock_loss_27m) begin
                        in_lock_loss_27m <= 1'b0;
                        if (relock_count_27m != 8'hFF)
                            relock_count_27m <= relock_count_27m + 8'd1;
                    end
                end else begin
                    qual_cnt <= qual_cnt + 1'b1;
                end
            end else begin
                if (seq_cnt < TIMING_WAIT_CYCLES[WAIT_W-1:0])
                    seq_cnt <= seq_cnt + 1'b1;
                if (seq_cnt >= CLKDIV_WAIT_CYCLES[WAIT_W-1:0] - 1'b1)
                    oser_rel_27m <= 1'b1;       // Stage 2: Release OSER10.RESET
                if (seq_cnt >= TIMING_WAIT_CYCLES[WAIT_W-1:0] - 1'b1)
                    timing_rel_27m <= 1'b1;     // Stage 3: Release Video Timing & Pipeline
            end
        end
    end

    // ── 2. Pixel clock domain reset bridges ──────────────────────
    reg oser_rst_s1 = 1'b1, oser_rst_s2 = 1'b1;
    always @(posedge pixel_clk or negedge oser_rel_27m) begin
        if (!oser_rel_27m) begin
            oser_rst_s1 <= 1'b1;
            oser_rst_s2 <= 1'b1;
        end else begin
            oser_rst_s1 <= 1'b0;
            oser_rst_s2 <= oser_rst_s1;
        end
    end
    assign oser_rst = oser_rst_s2;

    reg vid_rst_s1 = 1'b0, vid_rst_s2 = 1'b0;
    always @(posedge pixel_clk or negedge timing_rel_27m) begin
        if (!timing_rel_27m) begin
            vid_rst_s1 <= 1'b0;
            vid_rst_s2 <= 1'b0;
        end else begin
            vid_rst_s1 <= 1'b1;
            vid_rst_s2 <= vid_rst_s1;
        end
    end
    assign vid_rst_n = vid_rst_s2;

    // ── 3. CDC synchronization of status into pixel_clk ──────────
    reg pll_qual_p1    = 1'b0, pll_qual_p2    = 1'b0;
    reg clkdiv_ok_p1   = 1'b0, clkdiv_ok_p2   = 1'b0;
    reg lock_loss_p1   = 1'b0, lock_loss_p2   = 1'b0;
    reg lock_sticky_p1 = 1'b0, lock_sticky_p2 = 1'b0;
    reg [7:0] relock_p1 = 8'd0, relock_p2     = 8'd0;

    always @(posedge pixel_clk or negedge ext_rst_n) begin
        if (!ext_rst_n) begin
            pll_qual_p1    <= 1'b0; pll_qual_p2    <= 1'b0;
            clkdiv_ok_p1   <= 1'b0; clkdiv_ok_p2   <= 1'b0;
            lock_loss_p1   <= 1'b0; lock_loss_p2   <= 1'b0;
            lock_sticky_p1 <= 1'b0; lock_sticky_p2 <= 1'b0;
            relock_p1      <= 8'd0; relock_p2      <= 8'd0;
        end else begin
            pll_qual_p1    <= pll_qual_27m;         pll_qual_p2    <= pll_qual_p1;
            clkdiv_ok_p1   <= clkdiv_rst_n;         clkdiv_ok_p2   <= clkdiv_ok_p1;
            lock_loss_p1   <= in_lock_loss_27m;     lock_loss_p2   <= lock_loss_p1;
            lock_sticky_p1 <= lock_lost_sticky_27m; lock_sticky_p2 <= lock_sticky_p1;
            relock_p1      <= relock_count_27m;     relock_p2      <= relock_p1;
        end
    end

    assign lock_lost_pix        = lock_loss_p2;
    assign lock_lost_sticky_pix = lock_sticky_p2;
    assign relock_count_pix     = relock_p2;

    reg       de_seen     = 1'b0;
    reg [3:0] frames_seen = 4'd0;

    always @(posedge pixel_clk or negedge vid_rst_n) begin
        if (!vid_rst_n) begin
            de_seen     <= 1'b0;
            frames_seen <= 4'd0;
        end else begin
            if (de)
                de_seen <= 1'b1;
            if (frame_tick && de_seen && (frames_seen < 4'd15))
                frames_seen <= frames_seen + 4'd1;
        end
    end

    assign st_ref_clk_ok = 1'b1;
    assign st_pll_locked = pll_qual_p2 && !lock_loss_p2;
    assign st_clkdiv_ok  = clkdiv_ok_p2 && !lock_loss_p2;
    assign st_pix_clk_ok = clkdiv_ok_p2 && !lock_loss_p2;
    assign st_tmds_ok    = (~oser_rst) && st_pix_clk_ok;
    assign st_timing_ok  = vid_rst_n && de_seen;
    assign st_font_ok    = vid_rst_n;
    assign st_logo_ok    = vid_rst_n && logo_rom_ok;
    assign st_comp_ok    = vid_rst_n && de_seen;
    assign st_vout_ok    = st_tmds_ok && st_timing_ok && st_logo_ok && (frames_seen >= STARTUP_FRAMES[3:0]);

    wire any_fault = fault_inject || lock_loss_p2 || (!logo_rom_ok);

    always @(posedge pixel_clk or negedge ext_rst_n) begin
        if (!ext_rst_n) begin
            screen_state <= SCREEN_STARTUP;
        end else if (any_fault) begin
            screen_state <= SCREEN_ERROR;
        end else if (st_vout_ok) begin
            screen_state <= SCREEN_READY;
        end else begin
            screen_state <= SCREEN_STARTUP;
        end
    end

endmodule

`default_nettype wire
