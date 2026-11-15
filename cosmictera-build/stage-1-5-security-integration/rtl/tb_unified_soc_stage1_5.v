// ============================================================================
// tb_unified_soc_stage1_5.v — Unified SoC Stage 1.5 Integration Testbench
//
// Verifies simultaneously on `cosmictera_unified_soc_top`:
//   1. HCPU UART 23-byte output parity (`112\n\nCYCLES=00001B89\r\n\n`,
//      exact hex `3131320a0a4359434c45533d30303030314238390d0a0a`) at 27 MHz /
//      115,200 baud, plus active-low LED[0..4] & Guard assertions.
//   2. Live 87-bit CDC Telemetry Bridge from `u_hcpu_core` (`clk_27m`) into
//      Boot Display `u_subsys_bridge` (`pixel_clk`): verifies `snap_cycles ==
//      32'h0000_1B89`, `snap_halted == 1`, `snap_guard == 0` (OK), `snap_valid == 1`.
//   3. HISA `CTHETA = 0x4E` (1-cycle Theta_hat extraction), `HDOT = 0x52`
//      (14-cycle 14-component inner product on Profile 2), and `GAP-02`
//      (`hcpu_hisab` canonical `u_guard` sharing) inside `u_hcpu_core`.
//   4. All 30 Boot Display & HDMI 1280x720@60Hz assertions (`T01..T24f`),
//      `P0..P12` Pin 88 navigation, reset sequencing & recovery, and
//      golden frame scanline dumps (`STARTUP`, `READY`, `ERROR`, `512x184` Logo).
// ============================================================================

`timescale 1ns / 1ps
`include "hcpu_pkg.vh"

module rPLL #(
    parameter FCLKIN = "27.0",
    parameter integer IDIV_SEL = 3,
    parameter integer FBDIV_SEL = 54,
    parameter integer ODIV_SEL = 2
) (
    input  wire       CLKIN,
    input  wire       RESET,
    input  wire       RESET_P,
    input  wire       CLKFB,
    input  wire [5:0] FBDSEL,
    input  wire [5:0] IDSEL,
    input  wire [5:0] ODSEL,
    input  wire [3:0] PSDA,
    input  wire [3:0] DUTYDA,
    input  wire [3:0] FDLY,
    output reg        CLKOUT,
    output wire       CLKOUTP,
    output wire       CLKOUTD,
    output wire       CLKOUTD3,
    output reg        LOCK
);
    assign CLKOUTP  = 1'b0;
    assign CLKOUTD  = 1'b0;
    assign CLKOUTD3 = 1'b0;
    initial begin
        CLKOUT = 1'b0;
        LOCK   = 1'b0;
    end
endmodule

module CLKDIV #(
    parameter DIV_MODE = "5",
    parameter GSREN    = "false"
) (
    input  wire RESETN,
    input  wire HCLKIN,
    input  wire CALIB,
    output reg  CLKOUT
);
    initial CLKOUT = 1'b0;
    always @(negedge RESETN) begin
        if (!RESETN) CLKOUT <= 1'b0;
    end
endmodule

module OSER10 #(
    parameter GSREN = "false",
    parameter LSREN = "true"
) (
    output reg  Q,
    input  wire D0, D1, D2, D3, D4, D5, D6, D7, D8, D9,
    input  wire PCLK,
    input  wire FCLK,
    input  wire RESET
);
    reg [9:0] shift_reg;
    reg [3:0] bit_idx;
    wire [9:0] d_word = {D9, D8, D7, D6, D5, D4, D3, D2, D1, D0};

    always @(posedge PCLK or posedge RESET) begin
        if (RESET) begin
            shift_reg <= 10'd0;
            bit_idx   <= 4'd0;
            Q         <= 1'b0;
        end else begin
            shift_reg <= d_word;
            bit_idx   <= 4'd0;
            Q         <= d_word[0];
        end
    end

    always @(posedge FCLK or posedge RESET) begin
        if (RESET) begin
            bit_idx <= 4'd0;
            Q       <= 1'b0;
        end else begin
            Q       <= d_word[bit_idx];
            bit_idx <= (bit_idx == 4'd9) ? 4'd0 : (bit_idx + 4'd1);
        end
    end
endmodule

module tb_unified_soc_stage1_5;

    localparam real    HALF_PERIOD_27M = 18.5;          // 27.027 MHz (~37.0 ns)
    localparam integer BAUD            = 115200;
    localparam real    BIT_NS          = 1_000_000_000.0 / BAUD;

    localparam integer SIM_QUAL_CYCLES  = 64;
    localparam integer SIM_CLKDIV_WAIT  = 8;
    localparam integer SIM_TIMING_WAIT  = 16;
    localparam integer SIM_CLKS_PER_SEC = 200;

    reg        clk_27m   = 1'b0;
    reg        btn_rst_n = 1'b0;
    reg        mode_key  = 1'b1;
    reg        uart_rxd  = 1'b1;
    wire       uart_txd;
    wire [5:0] led;
    wire       sd_clk;
    wire       sd_cmd;
    wire [3:0] sd_dat;
    wire       tmds_clk_p;
    wire [2:0] tmds_data_p;

    pullup(sd_cmd);
    pullup(sd_dat[0]);

    cosmictera_unified_soc_top #(
        .PROGRAM_HEX        ("program.hex"),
        .BAUD               (BAUD),
        .USE_DSP            (0),
        .FONT_HEX           ("hcpu_font8x8.hex"),
        .TEXT_HEX           ("boot_text_rom.hex"),
        .COMP_HEX           ("boot_comp_rom.hex"),
        .LOGO_HEX           ("logo_rle_rom.hex"),
        .LOCK_QUAL_CYCLES   (SIM_QUAL_CYCLES),
        .CLKDIV_WAIT_CYCLES (SIM_CLKDIV_WAIT),
        .TIMING_WAIT_CYCLES (SIM_TIMING_WAIT),
        .STARTUP_FRAMES     (1),
        .CLKS_PER_SEC       (SIM_CLKS_PER_SEC),
        .KEY_DEBOUNCE       (16),
        .KEY_LONG           (128)
    ) dut (
        .clk_27m     (clk_27m),
        .btn_rst_n   (btn_rst_n),
        .mode_key    (mode_key),
        .uart_rxd    (uart_rxd),
        .uart_txd    (uart_txd),
        .led         (led),
        .sd_clk      (sd_clk),
        .sd_cmd      (sd_cmd),
        .sd_dat      (sd_dat),
        .tmds_clk_p  (tmds_clk_p),
        .tmds_data_p (tmds_data_p)
    );

    always #HALF_PERIOD_27M clk_27m = ~clk_27m;

    always #7.0 begin
        if (dut.u_clkdiv.RESETN)
            dut.u_clkdiv.CLKOUT = ~dut.u_clkdiv.CLKOUT;
        else
            dut.u_clkdiv.CLKOUT = 1'b0;
    end

    // ── Independent 115,200-baud UART Receiver on `uart_txd` ─────
    reg [7:0] uart_rx_buf [0:63];
    integer   uart_rx_cnt = 0;
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
            if (uart_rx_cnt < 64) begin
                uart_rx_buf[uart_rx_cnt] = shifted;
                uart_rx_cnt = uart_rx_cnt + 1;
            end
        end
    end

    integer pass_cnt = 0;
    integer fail_cnt = 0;
    reg     keep_startup = 1'b0;

    task check_cond;
        input            cond;
        input [8*80-1:0] name;
        begin
            if (cond) begin
                pass_cnt = pass_cnt + 1;
                $display("[PASS] %0s", name);
            end else begin
                fail_cnt = fail_cnt + 1;
                $display("[FAIL] %0s", name);
            end
        end
    endtask

    task capture_scanline;
        input integer fd;
        input [11:0]  target_y;
        output integer blank_err_out;
        integer x_i;
        begin
            blank_err_out = 0;
            @(posedge dut.pixel_clk); #1;
            dut.u_timing.v_count = (target_y == 12'd0) ? 12'd749 : (target_y - 12'd1);
            dut.u_timing.h_count = 12'd1648;
            @(posedge dut.pixel_clk); #1;
            @(posedge dut.pixel_clk); #1;
            if (keep_startup) begin
                dut.u_reset_seq.frames_seen = 4'd0;
                dut.u_reset_seq.screen_state = 2'd0;
            end
            for (x_i = 0; x_i < 1280; x_i = x_i + 1) begin
                if (!dut.de) blank_err_out = blank_err_out + 1;
                $fwrite(fd, "%c%c%c", dut.red, dut.green, dut.blue);
                @(posedge dut.pixel_clk); #1;
            end
            repeat (6) begin
                if (dut.de || dut.red != 8'h00 || dut.green != 8'h00 || dut.blue != 8'h00)
                    blank_err_out = blank_err_out + 1;
                @(posedge dut.pixel_clk); #1;
            end
        end
    endtask

    task dump_region_scanlines;
        input [8*64-1:0] filename;
        integer fd;
        integer b_err, total_b_err;
        begin
            fd = $fopen(filename, "wb");
            total_b_err = 0;

            capture_scanline(fd, 12'd0,   b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd18,  b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd34,  b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd62,  b_err); total_b_err = total_b_err + b_err;

            @(posedge dut.pixel_clk); #1;
            dut.u_timing.v_count = 12'd75;
            dut.u_timing.h_count = 12'd0;
            repeat (3) begin @(posedge dut.pixel_clk); #1; end
            capture_scanline(fd, 12'd76,  b_err); total_b_err = total_b_err + b_err;

            capture_scanline(fd, 12'd274, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd290, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd320, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd330, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd354, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd386, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd434, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd450, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd458, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd474, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd482, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd490, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd506, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd522, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd538, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd554, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd570, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd602, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd618, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd650, b_err); total_b_err = total_b_err + b_err;
            capture_scanline(fd, 12'd682, b_err); total_b_err = total_b_err + b_err;

            $fclose(fd);
            check_cond(total_b_err == 0,
                       "T04/T07/T08/T20 Captured 26 region scanlines (incl. all 16 entries) with 0 blanking leaks");
        end
    endtask

    task dump_full_hero_logo_rtl;
        input [8*64-1:0] filename;
        integer fd;
        integer ly, lx;
        begin
            fd = $fopen(filename, "wb");
            @(posedge dut.pixel_clk); #1;
            dut.u_timing.v_count = 12'd75;
            dut.u_timing.h_count = 12'd0;
            repeat (3) begin @(posedge dut.pixel_clk); #1; end

            for (ly = 76; ly < 260; ly = ly + 1) begin
                dut.u_timing.v_count = ly[11:0];
                dut.u_timing.h_count = 12'd383;
                @(posedge dut.pixel_clk); #1;
                for (lx = 0; lx < 512; lx = lx + 1) begin
                    $fwrite(fd, "%c%c%c", dut.red, dut.green, dut.blue);
                    @(posedge dut.pixel_clk); #1;
                end
            end
            $fclose(fd);
            check_cond(dut.u_logo.rd_ptr == 14'd16305 && dut.logo_rom_ok == 1'b1,
                       "T05 Full 512x184 RLE Hero Logo streamed exact 16,304 words (rom_ok=1)");
        end
    endtask

    integer cyc, k;
    reg clkdiv_released_before_oser;
    reg oser_released_before_vid;
    reg [8*23-1:0] gold_uart_23;
    reg uart_23_match;

    initial begin
        $display("=== COSMICTERA STAGE 1.5 UNIFIED SOC RTL VERIFICATION ===");
        btn_rst_n = 1'b0;
        mode_key  = 1'b1;
        dut.u_tmds_rpll.pll.LOCK = 1'b0;

        repeat (10) @(posedge clk_27m); #1;
        btn_rst_n = 1'b1;

        // ── T14a: Glitch test on PLL lock before qualification completes ──
        dut.u_tmds_rpll.pll.LOCK = 1'b1;
        repeat (SIM_QUAL_CYCLES / 2) @(posedge clk_27m); #1;
        dut.u_tmds_rpll.pll.LOCK = 1'b0;
        repeat (3) @(posedge clk_27m); #1;
        check_cond(dut.u_reset_seq.pll_qual_27m == 1'b0 &&
                   dut.u_reset_seq.qual_cnt == 0 &&
                   dut.clkdiv_rst_n == 1'b0,
                   "T14a PLL lock glitch before 2ms threshold resets qualification");

        // ── T14b & T13: Sustained PLL lock qualification & staged reset order ──
        dut.u_tmds_rpll.pll.LOCK = 1'b1;
        clkdiv_released_before_oser = 1'b0;
        oser_released_before_vid    = 1'b0;

        for (cyc = 0; cyc < SIM_QUAL_CYCLES + 40; cyc = cyc + 1) begin
            @(posedge clk_27m); #1;
            if (dut.clkdiv_rst_n == 1'b1 && dut.oser_rst == 1'b1)
                clkdiv_released_before_oser = 1'b1;
            if (dut.oser_rst == 1'b0 && dut.vid_rst_n == 1'b0)
                oser_released_before_vid = 1'b1;
        end

        check_cond(dut.u_reset_seq.pll_qual_27m == 1'b1,
                   "T14b PLL lock qualified after full threshold");
        check_cond(clkdiv_released_before_oser && oser_released_before_vid &&
                   dut.clkdiv_rst_n == 1'b1 && dut.oser_rst == 1'b0 && dut.vid_rst_n == 1'b1,
                   "T13 Reset order: CLKDIV.RESETN -> OSER10.RESET -> vid_rst_n");

        // ── T12 & T18: Verify STARTUP screen state on Frame 0 and capture STARTUP scanlines ──
        keep_startup                = 1'b1;
        force dut.u_reset_seq.frames_seen = 4'd0;
        dut.u_uptime.sim_freeze     = 1'b1;
        dut.u_uptime.sub_cnt        = 1;
        dut.u_uptime.bcd_hold_27m   = 24'h000000;
        dut.u_uptime.uptime_bcd_pix = 24'h000000;
        dut.u_reset_seq.de_seen     = 1'b1;
        repeat (6) begin @(posedge clk_27m); #1; end
        repeat (10) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.screen_state == 2'd0,
                   "T12/T18 Initial screen state is SCREEN_STARTUP (2'd0)");
        dump_region_scanlines("../frame_previews/rtl_scanlines_startup.raw");
        release dut.u_reset_seq.frames_seen;
        keep_startup                = 1'b0;
        dut.u_uptime.sim_freeze     = 1'b0;

        // ── T05: Verify full 512x184 Hero Logo RLE streaming in RTL ──
        dump_full_hero_logo_rtl("../frame_previews/rtl_hero_logo_512x184.raw");

        // ── T01: Verify HDMI 1280x720@60Hz timing parameters & sync polarities ──
        @(posedge dut.pixel_clk); #1;
        dut.u_timing.v_count = 12'd0;
        dut.u_timing.h_count = 12'd1279;
        @(posedge dut.pixel_clk); #1;
        check_cond(dut.de == 1'b0 && dut.hsync == 1'b0,
                   "T01a H_FRONT (h_count=1280): de=0, hsync=0");
        dut.u_timing.h_count = 12'd1389;
        @(posedge dut.pixel_clk); #1;
        check_cond(dut.hsync == 1'b1,
                   "T01b H_SYNC (h_count=1390..1429): hsync=1 positive pulse");
        dut.u_timing.h_count = 12'd1429;
        @(posedge dut.pixel_clk); #1;
        check_cond(dut.hsync == 1'b0,
                   "T01c H_BACK (h_count=1430..1649): hsync=0");

        dut.u_timing.v_count = 12'd725;
        @(posedge dut.pixel_clk); #1;
        check_cond(dut.vsync == 1'b1 && dut.de == 1'b0,
                   "T01d V_SYNC (v_count=725..729): vsync=1 positive pulse, de=0");

        // ── T02 & T03: Verify TMDS encoding & OSER10 serialization ──
        repeat (20) begin
            #1 dut.u_tmds_rpll.pll.CLKOUT = ~dut.u_tmds_rpll.pll.CLKOUT;
        end
        check_cond(dut.u_dvi_tx.u_red.disparity >= -8 && dut.u_dvi_tx.u_red.disparity <= 8 &&
                   dut.u_dvi_tx.u_green.disparity >= -8 && dut.u_dvi_tx.u_green.disparity <= 8 &&
                   dut.u_dvi_tx.u_blue.disparity >= -8 && dut.u_dvi_tx.u_blue.disparity <= 8,
                   "T02/T03 TMDS 8b/10b disparity bounded [-8..+8] & OSER10 active");

        // ── T12 & T10: Trigger frame_tick at (0, 0) to advance to SCREEN_READY ──
        @(posedge dut.pixel_clk); #1;
        dut.u_timing.v_count = 12'd749;
        dut.u_timing.h_count = 12'd1649;
        repeat (10) begin @(posedge dut.pixel_clk); #1; end

        check_cond(dut.screen_state == 2'd1 && dut.st_vout_ok == 1'b1,
                   "T12 All 10 stages READY -> SCREEN_READY (2'd1)");
        check_cond(dut.fifo_count == 4'd6 && dut.fifo_overflow == 1'b0,
                   "T10 Event FIFO recorded 6 hardware boot events (EV01..EV06)");

        // ── T09 & T20b: Verify monotonic 1 Hz BCD uptime counter & CDC handshake ──
        @(posedge clk_27m); #1;
        dut.u_uptime.hr1     = 4'd0;
        dut.u_uptime.hr0     = 4'd0;
        dut.u_uptime.min1    = 4'd0;
        dut.u_uptime.min0    = 4'd5;
        dut.u_uptime.sec1    = 4'd4;
        dut.u_uptime.sec0    = 4'd1;
        dut.u_uptime.sub_cnt = 1;
        repeat (SIM_CLKS_PER_SEC + 10) begin @(posedge clk_27m); #1; end
        repeat (10) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.uptime_bcd_pix == 24'h000542,
                   "T09/T20b Uptime BCD counter + CDC incremented to 00:05:42");

        dut.u_uptime.sim_freeze = 1'b1;
        dut.u_events.ev0_ts     = 24'h000000;
        dut.u_events.ev1_ts     = 24'h000000;
        dut.u_events.ev2_ts     = 24'h000000;
        dut.u_events.ev3_ts     = 24'h000000;
        dut.u_events.ev4_ts     = 24'h000000;
        dut.u_events.ev5_ts     = 24'h000001;

        // ── T04, T06, T07, T08: Capture SCREEN_READY scanlines ──
        dump_region_scanlines("../frame_previews/rtl_scanlines_ready.raw");
        dut.u_uptime.sim_freeze = 1'b0;

        // ── T25 (NEW — Unified SoC): Wait for HCPU 23-Byte UART Output & Verify Parity ──
        // By now ~1.5 ms have elapsed; wait enough time for all 23 UART bytes to finish draining.
        #(BIT_NS * 10 * 28);
        gold_uart_23 = {
            8'h31, 8'h31, 8'h32, 8'h0a, 8'h0a,
            8'h43, 8'h59, 8'h43, 8'h4c, 8'h45, 8'h53, 8'h3d,
            8'h30, 8'h30, 8'h30, 8'h30, 8'h31, 8'h42, 8'h38, 8'h39,
            8'h0d, 8'h0a, 8'h0a
        };
        uart_23_match = (uart_rx_cnt == 23);
        for (k = 0; k < 23; k = k + 1) begin
            if (uart_rx_buf[k] !== gold_uart_23[(22 - k)*8 +: 8])
                uart_23_match = 1'b0;
        end
        check_cond(uart_23_match && dut.u_hcpu_core.cycle_count == 32'h0000_1B89 &&
                   dut.led[0] == 1'b0 && dut.led[1] == 1'b0 && dut.led[4] == 1'b0,
                   "T25 Unified SoC HCPU UART emitted exact 23 bytes (112, CYCLES=00001B89) & Guard/Halt LEDs ON");

        // ── T26 (NEW — Unified SoC): Live HCPU Telemetry Bridge -> Boot Display ──
        dut.sim_use_live_hcpu = 1'b1;
        @(posedge dut.pixel_clk); #1;
        dut.u_timing.v_count = 12'd0;
        dut.u_timing.h_count = 12'd0;
        repeat (6) begin @(posedge clk_27m); #1; end
        repeat (10) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.snap_valid == 1'b1 &&
                   dut.snap_cycles == 32'h0000_1B89 &&
                   dut.snap_halted == 1'b1 &&
                   dut.snap_guard == 1'b0,
                   "T26 Unified SoC live HCPU telemetry CDC captured CYCLES=00001B89, HLT=1, G=OK");
        dut.sim_use_live_hcpu = 1'b0;
        // Restore BIST snapshot for subsequent Stage 1.4 golden ERROR frame comparison
        @(posedge dut.pixel_clk); #1;
        dut.u_timing.v_count = 12'd0;
        dut.u_timing.h_count = 12'd0;
        repeat (6) begin @(posedge clk_27m); #1; end
        repeat (10) begin @(posedge dut.pixel_clk); #1; end

        // ── T27 (NEW — Unified SoC): Verify CTHETA=0x4E, HDOT=0x52 & GAP-02 in u_hcpu_core ──
        // Load a 6-instruction micro-program into u_hcpu_core.imem and reset HCPU to execute it:
        //   0: HLOAD  H0, 27       (Haa: Theta_hat = 8, ||Haa||^2_14 = 69) -> 0x4000_001B
        //   1: CTHETA R1, H0       (0x4E: R1 <- Theta_hat(H0) = 8)         -> 0x4E10_0000
        //   2: HDOT   R2, H0, H0   (0x52: R2 <- <H0, H0>_14 = 69, 14 cyc)  -> 0x5220_0000
        //   3: HPACK  R3, H0, 2    (0x50: GAP-02 canonical u_guard word 2) -> 0x5030_2000
        //   4: HCRC   R4, H0, 0    (0x51: CRC32 over canonical pack)       -> 0x5140_0000
        //   5: HALT                                                        -> 0x0100_0000
        dut.u_hcpu_core.imem[0] = 32'h4000_001B;
        dut.u_hcpu_core.imem[1] = 32'h4E10_0000;
        dut.u_hcpu_core.imem[2] = 32'h5220_0000;
        dut.u_hcpu_core.imem[3] = 32'h5030_2000;
        dut.u_hcpu_core.imem[4] = 32'h5140_0000;
        dut.u_hcpu_core.imem[5] = 32'h0100_0000;
        // Pulse falling edge on btn_rst_n to trigger synchronous HCPU reset
        @(posedge clk_27m); #1;
        btn_rst_n = 1'b0;
        repeat (4) @(posedge clk_27m); #1;
        btn_rst_n = 1'b1;
        dut.live_hcpu_mode = 1'b0;
        repeat (60) @(posedge clk_27m); #1;
        check_cond(dut.u_hcpu_core.u_hcpu.u_regfile.gpr[1] == 32'd8 &&
                   dut.u_hcpu_core.u_hcpu.u_regfile.gpr[2] == 32'd69 &&
                   dut.u_hcpu_core.u_hcpu.u_regfile.gpr[3][15:8] == 8'h3F &&
                   dut.u_hcpu_core.u_hcpu.u_hisab.guard_status == 8'h3F &&
                   dut.u_hcpu_core.u_hcpu.u_regfile.gpr[4] != 32'd0 &&
                   dut.u_hcpu_core.halted_out == 1'b1,
                   "T27 Unified SoC HISA CTHETA(0x4E)=8, HDOT(0x52)=69 (14-cyc), and GAP-02 HISAB guard=0x3F");

        // ── T15 & T16: Simulate PLL lock loss during operation and relock recovery ──
        dut.u_tmds_rpll.pll.LOCK = 1'b0;
        repeat (10) begin @(posedge clk_27m); #1; end
        check_cond(dut.clkdiv_rst_n == 1'b0 && dut.oser_rst == 1'b1 && dut.vid_rst_n == 1'b0 &&
                   dut.u_reset_seq.in_lock_loss_27m == 1'b1,
                   "T15 PLL lock loss immediately asserts safe staged resets");

        dut.u_tmds_rpll.pll.LOCK = 1'b1;
        repeat (SIM_QUAL_CYCLES + 40) begin @(posedge clk_27m); #1; end
        repeat (20) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.relock_count_pix == 8'd1 && dut.clkdiv_rst_n == 1'b1 &&
                   dut.oser_rst == 1'b0 && dut.vid_rst_n == 1'b1,
                   "T16 PLL relock recovery increments relock_count_pix to 01");

        // ── T17: Reset assertion during active video scanline ──
        @(posedge dut.pixel_clk); #1;
        dut.u_timing.v_count = 12'd100;
        dut.u_timing.h_count = 12'd500;
        @(posedge dut.pixel_clk); #1;
        dut.sim_ext_rst_n = 1'b0;
        repeat (4) begin @(posedge clk_27m); #1; end
        check_cond(dut.vid_rst_n == 1'b0 && dut.snap_valid == 1'b0 &&
                   dut.h_count == 12'd0 && dut.v_count == 12'd0 &&
                   dut.red == 8'h00 && dut.green == 8'h00 && dut.blue == 8'h00,
                   "T17 Mid-scanline reset clears timing counters, snap_valid=0, and blanks RGB");
        dut.sim_ext_rst_n = 1'b1;
        repeat (SIM_QUAL_CYCLES + 40) begin @(posedge clk_27m); #1; end
        repeat (10) begin @(posedge dut.pixel_clk); #1; end
        repeat (6) begin @(posedge clk_27m); #1; end
        repeat (10) begin @(posedge dut.pixel_clk); #1; end

        // ── T11 & T19: Trigger fault injection + FIFO overflow (>8 events) and dump ERROR scanlines ──
        repeat (5) begin
            dut.sim_fault_inject = 1'b1;
            repeat (6) begin @(posedge dut.pixel_clk); #1; end
            dut.sim_fault_inject = 1'b0;
            repeat (6) begin @(posedge dut.pixel_clk); #1; end
        end
        dut.sim_fault_inject        = 1'b1;
        dut.u_uptime.sim_freeze     = 1'b1;
        dut.u_uptime.sub_cnt        = 1;
        dut.u_uptime.bcd_hold_27m   = 24'h001209;
        dut.u_uptime.uptime_bcd_pix = 24'h001209;
        dut.u_reset_seq.relock_count_27m = 8'h01;
        dut.u_reset_seq.relock_p1        = 8'h01;
        dut.u_reset_seq.relock_p2        = 8'h01;
        dut.u_events.ev0_ts         = 24'h000000;
        dut.u_events.ev1_ts         = 24'h000000;
        dut.u_events.ev2_ts         = 24'h000000;
        dut.u_events.ev3_ts         = 24'h000000;
        dut.u_events.ev4_ts         = 24'h000000;
        dut.u_events.ev5_ts         = 24'h001209;
        repeat (10) begin @(posedge dut.pixel_clk); #1; end

        check_cond(dut.screen_state == 2'd2 && dut.fifo_overflow == 1'b1 && dut.fifo_count == 4'd8,
                   "T11/T19 Fault state SCREEN_ERROR (2'd2) & FIFO overflow indicator set");

        dump_region_scanlines("../frame_previews/rtl_scanlines_error.raw");

        dut.sim_force_logo_fault = 1'b1;
        repeat (10) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.logo_rom_ok == 1'b0 && dut.st_logo_ok == 1'b0,
                   "T19b Logo ROM fault flag activates text fallback");
        dut.sim_force_logo_fault = 1'b0;

        // ── T21..T24f: Stage 1.4/1.5 Expanded 16-Entry Ecosystem & P0..P12 Inspector Verification ──
        dut.sim_fault_inject = 1'b0;
        repeat (20) begin @(posedge clk_27m); #1; end
        repeat (10) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.subsys_state_flat == 32'hAAAA_AAAA && dut.subsys_all_ready == 1'b1 &&
                   dut.subsys_any_fault == 1'b0,
                   "T21 All 16 CosmicTera ecosystem entries operational (32'hAAAA_AAAA)");

        dut.sim_ext_telem_en = 1'b1;
        dut.sim_ext_pc       = 12'h3F8;
        dut.sim_ext_instr    = 32'h4E03_0400;
        dut.sim_ext_cycles   = 32'h0010_8888;
        dut.sim_ext_flags    = 8'h0C;
        dut.sim_ext_guard    = 1'b0;
        dut.sim_ext_halted   = 1'b0;
        @(posedge dut.pixel_clk); #1;
        dut.u_timing.v_count = 12'd0;
        dut.u_timing.h_count = 12'd0;
        repeat (6) begin @(posedge clk_27m); #1; end
        repeat (10) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.snap_valid == 1'b1 && dut.snap_pc == 12'h3F8 &&
                   dut.snap_instr == 32'h4E03_0400 &&
                   dut.snap_cycles == 32'h0010_8888 && dut.snap_flags == 8'h0C,
                   "T22 Coherent 87-bit HCPU telemetry CDC captured PC=3F8 IN=4E030400 CY=00108888");
        dut.sim_ext_telem_en = 1'b0;

        dut.sim_subsys_fault_mask = 16'b0000_1000_0010_0000;
        repeat (4) begin @(posedge clk_27m); #1; end
        repeat (6) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.subsys_state_flat[11:10] == 2'd3 && dut.subsys_state_flat[23:22] == 2'd3 &&
                   dut.subsys_any_fault == 1'b1 && dut.subsys_all_ready == 1'b0 &&
                   dut.subsys_state_flat[1:0] == 2'd2,
                   "T23 16-bit fault mask isolates HMCL & HIJRAH faults while HCPU stays OK");
        dut.sim_subsys_fault_mask = 16'd0;
        repeat (4) begin @(posedge clk_27m); #1; end
        repeat (6) begin @(posedge dut.pixel_clk); #1; end

        repeat (8) begin
            mode_key = 1'b0;
            repeat (40) begin @(posedge dut.pixel_clk); #1; end
            mode_key = 1'b1;
            repeat (40) begin @(posedge dut.pixel_clk); #1; end
        end
        check_cond(dut.page == 4'd8,
                   "T24a Pin 88 mode_key reaches preserved PAGE 8 (KA'BAH / PORTAL 8888)");

        mode_key = 1'b0;
        repeat (40) begin @(posedge dut.pixel_clk); #1; end
        mode_key = 1'b1;
        repeat (40) begin @(posedge dut.pixel_clk); #1; end
        @(posedge dut.pixel_clk); #1;
        dut.u_timing.v_count = 12'd448;
        dut.u_timing.h_count = 12'd790;
        #1;
        check_cond(dut.page == 4'd9 && dut.comp_hit == 1'b1 && dut.comp_ch == "P",
                   "T24b Pin 88 transitions P8 -> P9 (COSMIC CODEX JIM / J-MACHINE)");

        mode_key = 1'b0;
        repeat (40) begin @(posedge dut.pixel_clk); #1; end
        mode_key = 1'b1;
        repeat (40) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.page == 4'd10,
                   "T24c Pin 88 transitions P9 -> P10 (HISAB & RAMAL)");

        mode_key = 1'b0;
        repeat (40) begin @(posedge dut.pixel_clk); #1; end
        mode_key = 1'b1;
        repeat (40) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.page == 4'd11,
                   "T24d Pin 88 transitions P10 -> P11 (FIVE ALGEBRAIC BRANCHES)");

        mode_key = 1'b0;
        repeat (40) begin @(posedge dut.pixel_clk); #1; end
        mode_key = 1'b1;
        repeat (40) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.page == 4'd12,
                   "T24e Pin 88 transitions P11 -> P12 (SOFTWARE COMPUTE ECOSYSTEM)");

        mode_key = 1'b0;
        repeat (40) begin @(posedge dut.pixel_clk); #1; end
        mode_key = 1'b1;
        repeat (40) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.page == 4'd0,
                   "T24f Pin 88 wraps around cleanly from P12 -> P0 (HOME)");

        // ── T28 (NEW — USSS Power-On BIST & 7-LUT Plane Verification) ──
        check_cond(dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.auth_grant_reg == 1'b1 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.auth_reject_reg == 1'b0 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.auth_error_reg == 1'b0 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.last_lut_snap == 7'b111_1111 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.sec_reason_rdata == 32'h0000_0001 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.sec_counter_rdata == 32'h0000_0001,
                   "T28 USSS 7-LUT BIST verified AUTH_OK=1, LUT[7:1]=7'b1111111, REASON=0x1, CNT=1");

        // ── T29 (NEW — HCPU MMIO Programmatic Write/Read to 0xFE8..0xFEC) ──
        // Dispatch SEC_CTRL write on Port 1 with letter=11 (0xB79) and wait 35 cycles
        @(posedge clk_27m); #1;
        force dut.u_hcpu_core.u_hcpu.u_mmio.sec_ctrl_we = 1'b1;
        force dut.u_hcpu_core.u_hcpu.u_mmio.wdata       = 32'h0000_0B79;
        @(posedge clk_27m); #1;
        release dut.u_hcpu_core.u_hcpu.u_mmio.sec_ctrl_we;
        release dut.u_hcpu_core.u_hcpu.u_mmio.wdata;
        repeat (35) @(posedge clk_27m); #1;

        // Now execute HCPU program that waits 32 loops for power-on BIST to settle,
        // then executes LOAD from 0xFE9..0xFEC into R5..R8:
        dut.u_hcpu_core.imem[0] = 32'h0420_0020; // MOVI R2, 32
        dut.u_hcpu_core.imem[1] = 32'h1122_0FFF; // ADDI R2, R2, -1
        dut.u_hcpu_core.imem[2] = 32'h2102_0000; // CMPI R2, 0
        dut.u_hcpu_core.imem[3] = 32'h2400_FFFE; // JNE  -2 (to imem[1])
        dut.u_hcpu_core.imem[4] = 32'h3050_0FE9; // LOAD R5, R0, 0xFE9 (SEC_STATUS)
        dut.u_hcpu_core.imem[5] = 32'h3060_0FEA; // LOAD R6, R0, 0xFEA (SEC_REASON)
        dut.u_hcpu_core.imem[6] = 32'h3070_0FEB; // LOAD R7, R0, 0xFEB (SEC_EVENT)
        dut.u_hcpu_core.imem[7] = 32'h3080_0FEC; // LOAD R8, R0, 0xFEC (SEC_COUNTER)
        dut.u_hcpu_core.imem[8] = 32'h0100_0000; // HALT
        @(posedge clk_27m); #1;
        btn_rst_n = 1'b0;
        repeat (4) @(posedge clk_27m); #1;
        btn_rst_n = 1'b1;
        repeat (250) @(posedge clk_27m); #1;
        check_cond(dut.u_hcpu_core.u_hcpu.u_regfile.gpr[5][2] == 1'b1 &&
                   dut.u_hcpu_core.u_hcpu.u_regfile.gpr[5][14:8] == 7'b111_1111 &&
                   dut.u_hcpu_core.u_hcpu.u_regfile.gpr[6] == 32'h0000_0001 &&
                   dut.u_hcpu_core.u_hcpu.u_regfile.gpr[8][15:0] >= 16'd1,
                   "T29 HCPU MMIO LOAD(0xFE9..0xFEC) verified SEC_STATUS AUTH_OK=1 & 7-LUT=7'b1111111");

        // ── T30 (NEW — Section 4 Security Check): Canonical kabah_verify_ok Expected Digest Mismatch ──
        // Launch request with `sim_kabah_forge = 1` (bit 17 of SEC_CTRL = 1):
        // Output state of 24-round Ka'bah sponge is NONZERO, but mismatches `kabah_expected_state`.
        // Verify that `kabah_verify_ok` is 0, `LUT7` is 0, `AUTH_OK` is 0, `REJECT` is 1,
        // and `SEC_REASON[5]` (`RSN_KABAH_MISMATCH`) is 1!
        @(posedge clk_27m); #1;
        force dut.u_hcpu_core.u_hcpu.u_mmio.sec_ctrl_we = 1'b1;
        force dut.u_hcpu_core.u_hcpu.u_mmio.wdata       = 32'h0002_0B39; // bit17=kabah_forge, letter=11, priv=1, gate=1, sec=1, start=1
        @(posedge clk_27m); #1;
        release dut.u_hcpu_core.u_hcpu.u_mmio.sec_ctrl_we;
        release dut.u_hcpu_core.u_hcpu.u_mmio.wdata;
        repeat (35) @(posedge clk_27m); #1;
        check_cond((|dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.kabah_sponge_state) == 1'b1 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.kabah_verify_ok == 1'b0 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.auth_grant_reg == 1'b0 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.auth_reject_reg == 1'b1 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.sec_reason_rdata[5] == 1'b1 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.sec_counter_rdata == 32'h0001_0002,
                   "T30 Canonical kabah_verify_ok rejects nonzero sponge state when expected digest mismatches (RSN_KABAH_MISMATCH=1)");

        // ── T31 (NEW — Key Protection & Jamrah 7-Node Gate Enforcement) ──
        // Disable secure_mode (`secure_mode_en = 0`, bit 3 = 0) -> LUT3-C = 0, key zeroed, REJECT=1, ERROR=1
        @(posedge clk_27m); #1;
        force dut.u_hcpu_core.u_hcpu.u_mmio.sec_ctrl_we = 1'b1;
        force dut.u_hcpu_core.u_hcpu.u_mmio.wdata       = 32'h0000_0531; // letter=5, priv=1, gate=1, sec=0, start=1
        @(posedge clk_27m); #1;
        release dut.u_hcpu_core.u_hcpu.u_mmio.sec_ctrl_we;
        release dut.u_hcpu_core.u_hcpu.u_mmio.wdata;
        repeat (35) @(posedge clk_27m); #1;
        check_cond(dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.last_lut_snap[2] == 1'b0 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.auth_grant_reg == 1'b0 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.auth_reject_reg == 1'b1 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.auth_error_reg == 1'b1 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.sec_reason_rdata[3] == 1'b1 &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.sec_status_rdata != dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.protected_key_vault[0][31:0] &&
                   dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.sec_event_rdata  != dut.u_hcpu_core.u_hcpu.u_mmio.u_usss.protected_key_vault[0][31:0],
                   "T31 LUT3-C key_enable=0 blocks internal key vault & triggers ERROR=1 with zero key leakage on MMIO");

        // ── T32 (NEW — Coherent CDC 27 MHz -> 74.25 MHz Security Telemetry Snapshot) ──
        // Re-authenticate cleanly on Port 2 so current verdict is AUTH_OK (req=4, fail=2)
        @(posedge clk_27m); #1;
        force dut.u_hcpu_core.u_hcpu.u_mmio.sec_ctrl_we = 1'b1;
        force dut.u_hcpu_core.u_hcpu.u_mmio.wdata       = 32'h0000_07B9; // letter=7, port=2, priv=1, gate=1, sec=1, start=1
        @(posedge clk_27m); #1;
        release dut.u_hcpu_core.u_hcpu.u_mmio.sec_ctrl_we;
        release dut.u_hcpu_core.u_hcpu.u_mmio.wdata;
        repeat (35) @(posedge clk_27m); #1;

        // Trigger frame_tick in pixel_clk to initiate toggle-handshake CDC across 27 MHz -> 74.25 MHz
        @(posedge dut.pixel_clk); #1;
        dut.u_timing.v_count = 12'd0;
        dut.u_timing.h_count = 12'd0;
        repeat (6) begin @(posedge clk_27m); #1; end
        repeat (10) begin @(posedge dut.pixel_clk); #1; end
        check_cond(dut.snap_sec_bus[1:0] == 2'd1 &&
                   dut.snap_sec_bus[23:16] == 8'd4 &&
                   dut.snap_sec_bus[31:24] == 8'd2 &&
                   dut.snap_sec_fault == 1'b0,
                   "T32 Coherent 32-bit Security CDC snapshot captured V=AUTH_OK, REQ=04, FAIL=02 in pixel_clk");

        // ── T33 (NEW — HDMI Boot Display Security Monitor Live Row 83 Rendering) ──
        // Position timing on Row 83 (`v_count = 83 * 8 = 664`), column 99 (`h_count = 99 * 8 - 2 = 790`)
        @(posedge dut.pixel_clk); #1;
        dut.u_timing.v_count = 12'd664;
        dut.u_timing.h_count = 12'd790; // la_col = 99 ('U' of "USSS ")
        @(posedge dut.pixel_clk); #1;
        check_cond(dut.u_compositor.comp_cell_s1[7:0] == "U",
                   "T33a HDMI Security Monitor Row 83 col 99 renders header 'U' of 'USSS'");
        dut.u_timing.h_count = 12'd1070; // la_col = 134 ('A' of "V:AUTH")
        @(posedge dut.pixel_clk); #1;
        check_cond(dut.u_compositor.comp_cell_s1[7:0] == "A",
                   "T33b HDMI Security Monitor Row 83 col 134 renders live verdict 'A' of 'V:AUTH'");
        dut.u_timing.h_count = 12'd1142; // la_col = 143 ('4' of "RQ:04")
        @(posedge dut.pixel_clk); #1;
        check_cond(dut.u_compositor.comp_cell_s1[7:0] == "4",
                   "T33c HDMI Security Monitor Row 83 col 143 renders live request counter '4' of 'RQ:04'");
        dut.u_timing.h_count = 12'd1190; // la_col = 149 ('2' of "FL:02")
        @(posedge dut.pixel_clk); #1;
        check_cond(dut.u_compositor.comp_cell_s1[7:0] == "2",
                   "T33d HDMI Security Monitor Row 83 col 149 renders live failure counter '2' of 'FL:02'");

        $display("=== UNIFIED SOC STAGE 1.5 + USSS SUMMARY: %0d PASS, %0d FAIL ===", pass_cnt, fail_cnt);
        if (fail_cnt != 0) $finish(1);
        $finish(0);
    end

endmodule
