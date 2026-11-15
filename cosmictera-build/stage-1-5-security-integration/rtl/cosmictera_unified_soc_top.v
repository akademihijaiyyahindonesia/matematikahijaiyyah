// ============================================================================
// cosmictera_unified_soc_top.v — COSMICTERA CT-01-REV13 Stage 1.5 Unified SoC
//
// Target Device : Tang Nano 20K — Gowin GW2AR-LV18QN88C8/I7 (family=GW2A-18C)
// Baseline      : HEAD = ea3c5b22 (CTHETA=0x4E, HDOT=0x52, GAP-02 resolved)
//
// Unified Architecture:
//   1. `hcpu_gowin_core` (USE_PLL=0, USE_DSP=0, 27.000 MHz system clock,
//      115,200 baud UART TX/RX + cycle reporter, 1-bit SDIO controller,
//      6 active-low LEDs, and 84-bit live hardware telemetry sideband).
//   2. `cosmictera_boot_top` Stage 1.5 BSRAM-Optimized Boot Display Subsystem
//      (1280x720@60Hz HDMI via TMDS_rPLL 371.25 MHz + CLKDIV /5 74.25 MHz,
//      2ms PLL lock qualification & staged reset sequencer, 512x184 RLE Hero
//      Logo, 24x24 Header Mini-Emblem, 16-entry Compute Ecosystem grid with
//      canonical R2 labels, P0..P12 multi-page inspector via Pin 88 `mode_key`,
//      and BSRAM-backed compositor string & page ROM `boot_comp_rom.hex`).
//   3. Live 87-bit Toggle-Handshake CDC Telemetry Bridge (`clk_27m` -> `pixel_clk`)
//      connecting `hcpu_gowin_core` directly to Region 5 telemetry bar.
// ============================================================================

`include "hcpu_pkg.vh"
`default_nettype none

module cosmictera_unified_soc_top #(
    parameter PROGRAM_HEX              = "program.hex",
    parameter integer BAUD             = 115200,
    parameter integer USE_DSP          = 1,
    parameter FONT_HEX                 = "hcpu_font8x8.hex",
    parameter TEXT_HEX                 = "boot_text_rom.hex",
    parameter COMP_HEX                 = "boot_comp_rom.hex",
    parameter LOGO_HEX                 = "logo_rle_rom.hex",
    parameter integer LOCK_QUAL_CYCLES   = 54_000,     // 2.0 ms at 27.000 MHz
    parameter integer CLKDIV_WAIT_CYCLES = 16,
    parameter integer TIMING_WAIT_CYCLES = 32,
    parameter integer STARTUP_FRAMES     = 1,
    parameter integer CLKS_PER_SEC       = 27_000_000, // 1.0 s at 27.000 MHz
    parameter integer KEY_DEBOUNCE       = 750_000,
    parameter integer KEY_LONG           = 74_250_000
) (
    // ── Shared 27.000 MHz Reference Clock & Buttons ──────────────
    input  wire       clk_27m,      // Pin 4  (27 MHz onboard crystal)
    input  wire       btn_rst_n,    // Pin 87 (Button S2 / MODE1, edge-detected reset)
    input  wire       mode_key,     // Pin 88 (Button S1 / MODE0, P0..P12 page key)

    // ── HCPU UART & LEDs ─────────────────────────────────────────
    input  wire       uart_rxd,     // Pin 70 (USB-C UART RX)
    output wire       uart_txd,     // Pin 69 (USB-C UART TX)
    output wire [5:0] led,          // Pins 15..20 (6 active-low LEDs)

    // ── Onboard MicroSD / TF Card (SDIO) ─────────────────────────
    output wire       sd_clk,       // Pin 83
    inout  wire       sd_cmd,       // Pin 82
    inout  wire [3:0] sd_dat,       // Pins 84, 85, 80, 81

    // ── HDMI TMDS Differential Output Pairs (Candidate B) ────────
    output wire       tmds_clk_p,   // Pin 33 (paired with 34 via LVCMOS33D)
    output wire [2:0] tmds_data_p   // Pins 35, 37, 39 (paired with 36, 38, 40)
);

    // ========================================================================
    // 1. Shared Edge-Sensitive Reset Synchronizer (`clk_27m` domain)
    // ========================================================================
    reg [1:0] btn_q          = 2'b00;
    reg [2:0] soc_rst_sync   = 3'b111;
    reg       live_hcpu_mode = 1'b0;

    always @(posedge clk_27m) begin
        btn_q <= {btn_q[0], btn_rst_n};
        if (btn_q[1] & ~btn_q[0]) begin
            soc_rst_sync   <= 3'b000;
            live_hcpu_mode <= ~live_hcpu_mode;
        end else begin
            soc_rst_sync   <= {soc_rst_sync[1:0], 1'b1};
        end
    end
    wire btn_pulse_rst_n = soc_rst_sync[2];

    // Simulation hooks (preserved for 100% compatibility with Stage 1.4 testbench)
    reg        sim_ext_rst_n         = 1'b1;
    reg        sim_fault_inject      = 1'b0;
    reg        sim_force_logo_fault  = 1'b0;
    reg [15:0] sim_subsys_fault_mask = 16'd0;
    reg        sim_ext_telem_en      = 1'b0;
    reg        sim_use_live_hcpu     = 1'b0;
    reg [11:0] sim_ext_pc            = 12'h1A4;
    reg [31:0] sim_ext_instr         = 32'h4E01_0200;
    reg        sim_ext_halted        = 1'b0;
    reg        sim_ext_guard         = 1'b0;
    reg [31:0] sim_ext_cycles        = 32'h0002_C1C9;
    reg [7:0]  sim_ext_flags         = 8'h04;

    wire disp_ext_rst_n = sim_ext_rst_n;

    // ========================================================================
    // 2. HCPU Subsystem (`hcpu_gowin_core`)
    // ========================================================================
    wire [`CODE_ADDR_W-1:0] hcpu_tele_pc;
    wire [`ILEN-1:0]        hcpu_tele_instr;
    wire                    hcpu_tele_halted;
    wire                    hcpu_tele_guard;
    wire [31:0]             hcpu_tele_cycles;
    wire [7:0]              hcpu_tele_flags;
    wire [31:0]             hcpu_tele_sec_bus;
    wire                    hcpu_tele_sec_fault;

    hcpu_gowin_core #(
        .USE_PLL     (0),
        .USE_DSP     (USE_DSP),
        .PROGRAM_HEX (PROGRAM_HEX),
        .BAUD        (BAUD)
    ) u_hcpu_core (
        .clk_27m        (clk_27m),
        .btn_rst_n      (btn_rst_n & sim_ext_rst_n),
        .uart_rxd       (uart_rxd),
        .uart_txd       (uart_txd),
        .led            (led),
        .sd_clk         (sd_clk),
        .sd_cmd         (sd_cmd),
        .sd_dat         (sd_dat),
        .tele_pc        (hcpu_tele_pc),
        .tele_instr     (hcpu_tele_instr),
        .tele_halted    (hcpu_tele_halted),
        .tele_guard     (hcpu_tele_guard),
        .tele_cycles    (hcpu_tele_cycles),
        .tele_flags     (hcpu_tele_flags),
        .tele_sec_bus   (hcpu_tele_sec_bus),
        .tele_sec_fault (hcpu_tele_sec_fault)
    );

    // ========================================================================
    // 3. Boot Display Clocking & Staged Reset (`TMDS_rPLL` + `CLKDIV /5`)
    // ========================================================================
    wire serial_clk;
    wire pixel_clk;
    wire pll_locked;
    wire clkdiv_rst_n;
    wire oser_rst;
    wire vid_rst_n;

    TMDS_rPLL u_tmds_rpll (
        .clkin  (clk_27m),
        .clkout (serial_clk),
        .lock   (pll_locked)
    );

    CLKDIV u_clkdiv (
        .RESETN (clkdiv_rst_n),
        .HCLKIN (serial_clk),
        .CLKOUT (pixel_clk),
        .CALIB  (1'b1)
    );
    defparam u_clkdiv.DIV_MODE = "5";
    defparam u_clkdiv.GSREN = "false";

    wire        hsync, vsync, de, frame_tick;
    wire [11:0] x, y, h_count, v_count;
    wire        logo_rom_ok;

    wire        st_ref_clk_ok, st_pll_locked, st_pix_clk_ok, st_clkdiv_ok;
    wire        st_tmds_ok, st_timing_ok, st_font_ok, st_logo_ok, st_comp_ok, st_vout_ok;
    wire        lock_lost_pix, lock_lost_sticky_pix;
    wire [7:0]  relock_count_pix;
    wire [1:0]  screen_state;

    cosmictera_boot_reset_seq #(
        .LOCK_QUAL_CYCLES   (LOCK_QUAL_CYCLES),
        .CLKDIV_WAIT_CYCLES (CLKDIV_WAIT_CYCLES),
        .TIMING_WAIT_CYCLES (TIMING_WAIT_CYCLES),
        .STARTUP_FRAMES     (STARTUP_FRAMES)
    ) u_reset_seq (
        .clk_27m              (clk_27m),
        .ext_rst_n            (disp_ext_rst_n),
        .pll_lock             (pll_locked),
        .pixel_clk            (pixel_clk),
        .de                   (de),
        .frame_tick           (frame_tick),
        .logo_rom_ok          (logo_rom_ok),
        .fault_inject         (sim_fault_inject),
        .clkdiv_rst_n         (clkdiv_rst_n),
        .oser_rst             (oser_rst),
        .vid_rst_n            (vid_rst_n),
        .st_ref_clk_ok        (st_ref_clk_ok),
        .st_pll_locked        (st_pll_locked),
        .st_pix_clk_ok        (st_pix_clk_ok),
        .st_clkdiv_ok         (st_clkdiv_ok),
        .st_tmds_ok           (st_tmds_ok),
        .st_timing_ok          (st_timing_ok),
        .st_font_ok           (st_font_ok),
        .st_logo_ok           (st_logo_ok),
        .st_comp_ok           (st_comp_ok),
        .st_vout_ok           (st_vout_ok),
        .lock_lost_pix        (lock_lost_pix),
        .lock_lost_sticky_pix (lock_lost_sticky_pix),
        .relock_count_pix     (relock_count_pix),
        .screen_state         (screen_state)
    );

    hcpu_video_timing #(
        .H_ACTIVE  (1280), .H_FRONT (110), .H_SYNC (40), .H_BACK (220),
        .V_ACTIVE  (720),  .V_FRONT (5),   .V_SYNC (5),  .V_BACK (20),
        .HSYNC_POL (1'b1), .VSYNC_POL (1'b1)
    ) u_timing (
        .pixel_clk  (pixel_clk),
        .rst_n      (vid_rst_n),
        .hsync      (hsync),
        .vsync      (vsync),
        .de         (de),
        .x          (x),
        .y          (y),
        .frame_tick (frame_tick),
        .h_count_o  (h_count),
        .v_count_o  (v_count)
    );

    wire [3:0] page;
    hcpu_page_key #(
        .DEBOUNCE (KEY_DEBOUNCE),
        .LONG     (KEY_LONG),
        .PAGES    (13)
    ) u_page (
        .clk   (pixel_clk),
        .rst_n (vid_rst_n),
        .key_n (mode_key),
        .page  (page)
    );

    wire [23:0] uptime_bcd_pix;
    wire        sec_tick_pix;

    cosmictera_boot_uptime #(
        .CLKS_PER_SEC (CLKS_PER_SEC)
    ) u_uptime (
        .clk_27m        (clk_27m),
        .rst_n          (disp_ext_rst_n),
        .pixel_clk      (pixel_clk),
        .uptime_bcd_pix (uptime_bcd_pix),
        .sec_tick_pix   (sec_tick_pix)
    );

    wire [3:0]  fifo_count;
    wire        fifo_overflow;
    wire [23:0] ev0_ts, ev1_ts, ev2_ts, ev3_ts, ev4_ts, ev5_ts;
    wire [27:0] dbg_fifo_data;

    cosmictera_boot_events u_events (
        .clk              (pixel_clk),
        .ext_rst_n        (disp_ext_rst_n),
        .uptime_bcd       (uptime_bcd_pix),
        .st_ref_clk_ok    (st_ref_clk_ok),
        .st_pll_locked    (st_pll_locked),
        .st_clkdiv_ok     (st_clkdiv_ok),
        .st_tmds_ok       (st_tmds_ok),
        .st_timing_ok     (st_timing_ok),
        .st_vout_ok       (st_vout_ok),
        .lock_lost_pix    (lock_lost_pix),
        .relock_count_pix (relock_count_pix),
        .fault_inject     (sim_fault_inject),
        .fifo_count       (fifo_count),
        .fifo_overflow    (fifo_overflow),
        .ev0_ts           (ev0_ts),
        .ev1_ts           (ev1_ts),
        .ev2_ts           (ev2_ts),
        .ev3_ts           (ev3_ts),
        .ev4_ts           (ev4_ts),
        .ev5_ts           (ev5_ts),
        .dbg_fifo_addr    (3'd0),
        .dbg_fifo_data    (dbg_fifo_data)
    );

    wire        logo_pixel_valid;
    wire [23:0] logo_pixel_rgb;

    cosmictera_boot_logo_rom #(
        .LOGO_HEX (LOGO_HEX)
    ) u_logo (
        .clk              (pixel_clk),
        .rst_n            (vid_rst_n),
        .h_count          (h_count),
        .v_count          (v_count),
        .force_logo_fault (sim_force_logo_fault),
        .logo_rom_ok      (logo_rom_ok),
        .logo_pixel_valid (logo_pixel_valid),
        .logo_pixel_rgb   (logo_pixel_rgb)
    );

    wire [7:0]  la_col;
    wire [6:0]  la_row;
    wire [11:0] text_rom_data;

    cosmictera_boot_text_rom #(
        .TEXT_HEX (TEXT_HEX)
    ) u_text_rom (
        .clk    (pixel_clk),
        .la_col (la_col),
        .la_row (la_row),
        .data   (text_rom_data)
    );

    // ========================================================================
    // 4. Coherent 87-Bit HCPU Telemetry & 16-Entry Status Bridge
    // ========================================================================
    // Driven by hardware flip-flop `live_hcpu_mode` (or simulation hooks
    // `sim_ext_telem_en` / `sim_use_live_hcpu`) so neither the 16-stage BIST
    // nor the 84-bit live HCPU telemetry bus can be pruned during synthesis.
    wire        bridge_telem_en = live_hcpu_mode | sim_ext_telem_en | sim_use_live_hcpu;
    wire [11:0] bridge_pc       = sim_ext_telem_en ? sim_ext_pc     : hcpu_tele_pc;
    wire [31:0] bridge_instr    = sim_ext_telem_en ? sim_ext_instr  : hcpu_tele_instr;
    wire        bridge_halted   = sim_ext_telem_en ? sim_ext_halted : hcpu_tele_halted;
    wire        bridge_guard    = sim_ext_telem_en ? sim_ext_guard  : (~hcpu_tele_guard & hcpu_tele_halted);
    wire [31:0] bridge_cycles   = sim_ext_telem_en ? sim_ext_cycles : hcpu_tele_cycles;
    wire [7:0]  bridge_flags    = sim_ext_telem_en ? sim_ext_flags  : hcpu_tele_flags;

    wire [11:0] snap_pc;
    wire [31:0] snap_instr;
    wire        snap_halted;
    wire        snap_guard;
    wire [31:0] snap_cycles;
    wire [7:0]  snap_flags;
    wire        snap_valid;
    wire [31:0] snap_sec_bus;
    wire        snap_sec_fault;
    wire [31:0] subsys_state_flat;
    wire        subsys_all_ready;
    wire        subsys_any_fault;

    cosmictera_boot_subsys_bridge u_subsys_bridge (
        .clk_27m           (clk_27m),
        .ext_rst_n         (disp_ext_rst_n),
        .ext_telem_en      (bridge_telem_en),
        .ext_pc            (bridge_pc),
        .ext_instr         (bridge_instr),
        .ext_halted        (bridge_halted),
        .ext_guard         (bridge_guard),
        .ext_cycles        (bridge_cycles),
        .ext_flags         (bridge_flags),
        .ext_sec_bus       (hcpu_tele_sec_bus),
        .ext_sec_fault     (hcpu_tele_sec_fault),
        .pixel_clk         (pixel_clk),
        .vid_rst_n         (vid_rst_n),
        .sample_tick       (frame_tick),
        .screen_state      (screen_state),
        .fault_inject      (sim_fault_inject),
        .subsys_fault_mask (sim_subsys_fault_mask),
        .snap_pc           (snap_pc),
        .snap_instr        (snap_instr),
        .snap_halted       (snap_halted),
        .snap_guard        (snap_guard),
        .snap_cycles       (snap_cycles),
        .snap_flags        (snap_flags),
        .snap_valid        (snap_valid),
        .snap_sec_bus      (snap_sec_bus),
        .snap_sec_fault    (snap_sec_fault),
        .subsys_state_flat (subsys_state_flat),
        .subsys_all_ready  (subsys_all_ready),
        .subsys_any_fault  (subsys_any_fault)
    );

    wire        comp_hit;
    wire [7:0]  comp_ch;
    wire [3:0]  comp_at;
    wire [11:0] comp_cell_s1;

    cosmictera_boot_compositor #(
        .COMP_HEX (COMP_HEX)
    ) u_compositor (
        .clk               (pixel_clk),
        .la_col            (la_col),
        .la_row            (la_row),
        .screen_state      (screen_state),
        .uptime_bcd        (uptime_bcd_pix),
        .page              (page),
        .st_ref_clk_ok     (st_ref_clk_ok),
        .st_pll_locked     (st_pll_locked),
        .st_pix_clk_ok     (st_pix_clk_ok),
        .st_clkdiv_ok      (st_clkdiv_ok),
        .st_tmds_ok        (st_tmds_ok),
        .st_timing_ok      (st_timing_ok),
        .st_font_ok        (st_font_ok),
        .st_logo_ok        (st_logo_ok),
        .st_comp_ok        (st_comp_ok),
        .st_vout_ok        (st_vout_ok),
        .lock_lost_pix     (lock_lost_pix),
        .relock_count_pix  (relock_count_pix),
        .fifo_count        (fifo_count),
        .fifo_overflow     (fifo_overflow),
        .ev0_ts            (ev0_ts),
        .ev1_ts            (ev1_ts),
        .ev2_ts            (ev2_ts),
        .ev3_ts            (ev3_ts),
        .ev4_ts            (ev4_ts),
        .ev5_ts            (ev5_ts),
        .snap_pc           (snap_pc),
        .snap_instr        (snap_instr),
        .snap_halted       (snap_halted),
        .snap_guard        (snap_guard),
        .snap_cycles       (snap_cycles),
        .snap_flags        (snap_flags),
        .snap_valid        (snap_valid),
        .snap_sec_bus      (snap_sec_bus),
        .subsys_state_flat (subsys_state_flat),
        .subsys_all_ready  (subsys_all_ready),
        .subsys_any_fault  (subsys_any_fault),
        .hit               (comp_hit),
        .ch                (comp_ch),
        .at                (comp_at),
        .comp_cell_s1      (comp_cell_s1)
    );

    wire [6:0] font_glyph;
    wire [2:0] font_row;
    wire [7:0] font_bits;

    hcpu_font_rom #(
        .FONT_HEX (FONT_HEX)
    ) u_font (
        .clk   (pixel_clk),
        .glyph (font_glyph),
        .row   (font_row),
        .bits  (font_bits)
    );

    wire [7:0] red, green, blue;

    cosmictera_boot_render #(
        .H_TOTAL (1650),
        .V_TOTAL (750)
    ) u_render (
        .clk              (pixel_clk),
        .rst_n            (vid_rst_n),
        .h_count          (h_count),
        .v_count          (v_count),
        .de               (de),
        .screen_state     (screen_state),
        .la_col           (la_col),
        .la_row           (la_row),
        .text_rom_data    (text_rom_data),
        .comp_hit         (comp_hit),
        .comp_ch          (comp_ch),
        .comp_at          (comp_at),
        .comp_cell_s1     (comp_cell_s1),
        .font_glyph       (font_glyph),
        .font_row         (font_row),
        .font_bits        (font_bits),
        .logo_pixel_valid (logo_pixel_valid),
        .logo_pixel_rgb   (logo_pixel_rgb),
        .red              (red),
        .green            (green),
        .blue             (blue)
    );

    reg [7:0] red_dvi   = 8'h00;
    reg [7:0] green_dvi = 8'h00;
    reg [7:0] blue_dvi  = 8'h00;
    reg       de_dvi    = 1'b0;
    reg       hsync_dvi = 1'b0;
    reg       vsync_dvi = 1'b0;

    always @(posedge pixel_clk or negedge vid_rst_n) begin
        if (!vid_rst_n) begin
            red_dvi   <= 8'h00;
            green_dvi <= 8'h00;
            blue_dvi  <= 8'h00;
            de_dvi    <= 1'b0;
            hsync_dvi <= 1'b0;
            vsync_dvi <= 1'b0;
        end else begin
            red_dvi   <= red;
            green_dvi <= green;
            blue_dvi  <= blue;
            de_dvi    <= de;
            hsync_dvi <= hsync;
            vsync_dvi <= vsync;
        end
    end

    wire       tmds_clk_serial;
    wire [2:0] tmds_data_serial;

    DVI_TX_Top u_dvi_tx (
        .I_rst_n          (~oser_rst),
        .I_serial_clk     (serial_clk),
        .I_rgb_clk        (pixel_clk),
        .I_rgb_vs         (vsync_dvi),
        .I_rgb_hs         (hsync_dvi),
        .I_rgb_de         (de_dvi),
        .I_rgb_r          (red_dvi),
        .I_rgb_g          (green_dvi),
        .I_rgb_b          (blue_dvi),
        .tmds_clk_serial  (tmds_clk_serial),
        .tmds_data_serial (tmds_data_serial)
    );

    assign tmds_clk_p  = tmds_clk_serial;
    assign tmds_data_p = tmds_data_serial;

endmodule

`default_nettype wire
