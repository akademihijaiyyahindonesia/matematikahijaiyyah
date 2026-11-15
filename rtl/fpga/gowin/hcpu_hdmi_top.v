// HCPU HDMI wrapper for Tang Nano 20K.
// The HDMI transport uses the board vendor's generated DVI TX IP.
//
// ── MEASURED, 13 September 2026, after EMITS ─────────────────────────────
//
// `make PROGRAM=../../programs/loader.hasm hdmi_bitstream` -- yosys 0.68
// (-nodsp) -> nextpnr-himbaechel 0.11.1 -> gowin_pack, GW2AR-LV18QN88C8/I7,
// loader baked in. Re-run because EMITS (0xA2) changed hcpu_pkg.vh,
// hcpu_decode.v, hcpu_execute.v and hcpu_top.v.
//
//     IOB           15 /    384    3%
//     LUT4      15,994 / 20,736   77%
//     DFF        5,134 / 15,552   33%
//     BSRAM         18 /     46   39%
//     Fmax      115.43 MHz  u_hcpu.clk_27m (PASS at the 12.00 MHz constraint)
//               392.16 MHz  pixel_clk
//
// RE-MEASURED 2026-09-14 for the second time that day, and PLACE AND ROUTE
// ONLY. This slot carries the SD controller whether it wants it or not:
// hcpu_hdmi_top instantiates hcpu_gowin_top, so the card arrived here with the
// widened peripheral window and its Ncc fix arrived here too.
//
// +9 DFF against 5,125, the same nine the bare HCPU slot gained: an eight-bit
// counter and one state, instantiated once because this wrapper holds one HCPU.
//
// LUT4 went DOWN 84, from 16,078, and the CPU clock went UP from 90.53 to
// 115.43 MHz. NEITHER IS A SAVING THIS CHANGE MADE. The placer is stochastic
// and this is the fullest slot in the rack; the same RTL placed differently.
// Recorded because it is what the run reported, not because it is an
// improvement anyone designed. Zero hold and zero setup violations.
//
// NO BITSTREAM WAS PACKED IN THIS RUN, and the line that used to record one
// is gone rather than carried over: `make hdmi_pnr.json` stops at the routed
// JSON. The previous entry's "7,261,470 bytes, gowin_pack exits 0" described a
// different design, and keeping it here would have been a measurement this
// file never took.
//
// The card's six pins are NOT constrained in hcpu_hdmi.cst. They are inputs
// and outputs of hcpu_gowin_top that this wrapper leaves unconnected, so
// nextpnr places them nowhere and the controller on this slot can never see a
// card. That is the honest state of the HDMI slot, not a defect to hide: the
// card path belongs to the HCPU slot, and this one exists to drive a display.
//
// +100 LUT4 and +30 DFF against this slot's previous 15,232 / 4,570, and the
// bare slot moved by +29 and the same +30. EMITS DOES add state, where FRD and
// FWR added none: a word address to walk the string with and a busy bit, plus
// three states on the print machine and a multiplexer on the data RAM's
// address port. No second transmitter -- hcpu_mmio.v refuses one and the
// refusal is kept.
//
// THE TWO BEFORE IT, the same day: after FRD and FWR, 15,232 LUT4 and 4,570
// DFF at 125.33 / 456.20 MHz (+70 LUT4, +18 DFF, and that DFF move was not
// explained by those two instructions); and after the TRAP_EPC bypass, 15,162
// and 4,552 at 127.05 / 457.25 MHz.
//
// THE TWO MEASUREMENTS BEFORE IT, the same day: after the TRAP_EPC bypass,
// 15,162 LUT4 and 4,552 DFF at 127.05 / 457.25 MHz (+21 LUT4, +0 DFF -- a mux,
// not a register); and after `pc_valid` stopped being tied high, 15,141 LUT4
// and 4,552 DFF at 63.21 / 476.87 MHz (+15 LUT4, +1 DFF).
//
// The measurement before it, 12 September, after the codex block: 15,126 LUT4
// (72%), 4,551 DFF, Fmax 70.80 / 549.15 MHz. That run was +413 LUT4 and +0 DFF
// over 14,713 -- CMOV and CZERO are muxes, CEQ a comparator, CU and CRHO are
// read out of the guard that already computes them, CMOD4 is a two-bit slice,
// and none of the six adds state.
//
// A SEVENTH WAS BUILT AND REMOVED, and the number that decided it was
// measured here. With CDOT (0x49) this slot placed at 16,727 LUT4 (80%) while
// hcpu_gowin_top on its own reached 16,015 (77%) and nextpnr refused: "Unable
// to find legal placement for all cells" -- twice, same message, so it was not
// placer variance. An inner product over fourteen components is fourteen 8x8
// multipliers. Without CDOT both slots place: 15,126 here and 14,714 there.
// The owner's decision and the named blocker are in cosmictera-build/OFF.md;
// CDOT still runs in the HVM.
//
// FLASHED AND RUN, 13 September 2026, over the wire through the baked loader:
//
//     emits         Hijaiyyah         THE ROW THIS BUILD EXISTS FOR: nine
//                                     characters and no newline, one ASCII
//                                     byte per word with a zero word ending
//                                     it. This machine had no way to put a
//                                     character on the wire until now.
//     shell         HIJAIYYAH         a banner, and a prompt with no newline
//                   > A               after it so the cursor waits where the
//                   > 2 0 1           typing goes. 'A' echoes as A, not 65;
//                   >                 'p' still answers in numbers.
//     flags_board   5 10 1 1          THE ROW THIS BUILD EXISTS FOR: pid 0 set
//                                     G and O, pid 1 set Z and LT, and after
//                                     two hundred preemptions each still reads
//                                     its OWN pattern, both still running. The
//                                     patterns share no bit, so a swap could
//                                     not be mistaken for a near miss.
//     trap_epc      1 1 1             THE ROW THIS BUILD EXISTS FOR: three
//                                     rounds at zero, one and two instructions
//                                     of distance between STORE TRAP_EPC and
//                                     ERET, each entering the handler exactly
//                                     once. Zero is the one that used to spin.
//     trap_resume   86 86 27          eight preemptions, handler never
//                                     touching epc: every resume correct and
//                                     the process still counting
//     trap_shadow   88 88 88 89 88    eight deadlines walked a cycle apart
//                   88 88 88 21
//     shell         A->65 p->2 0 1    the command path, unchanged
//                   0->48 z->122
//     syscall_io    42                and 99 still never reaches the wire
//     test_codex    8 0 0 1 1 0 1 5   the six codex opcodes, unchanged
//     test_cset     5 6 2 0
//     test_hfs      1 1 1 2 1
//     e3_sweep28    28 Theta values   identical to MASTER_TABLE
//
// mem_protect, user_mode, trap_timer, timer_poll and hal all halt and report
// their cycles, as they did before. Nothing that worked stopped working: the
// gate only ever holds the TIMER, and across syscall_io, mem_protect,
// user_mode, shell, kernel, branch_trap_race and the shadow sweep, the number
// of cycles an EXCEPTION was held by it is zero.
//
// ── RE-MEASURED, 5 November 2026, Option A (USE_DSP=1, Candidate B, Staged Reset) ──
//
// `make PROGRAM=../../programs/loader.hasm hdmi_bitstream` -- yosys 0.68+138
// (without -nodsp) -> nextpnr-himbaechel 0.11.1-19 -> gowin_pack (Apycula 0.34),
// GW2AR-LV18QN88C8/I7, loader baked in. Owner decision (Option A): align
// hcpu_hdmi_top.v and hcpu_hdmi.cst with the physical HDMI configuration
// proven on Unified SoC Stage 1.5 + USSS:
//   1. Hard-DSP: hcpu_gowin_core #(.USE_DSP(1)) maps the 14-lane 8x8 MAC in
//      hcpu_codex_alu and 32x32 multiply in hcpu_mul to 14 x MULT9X9 and
//      1 x MULT36X36 hard DSP blocks, saving 2,327 LUT4 (16,491 -> 14,164)
//      so the M5.2B display pipeline places and routes with 6,572 LUT4 spare.
//   2. Candidate B TMDS pins: 33, 35, 37, 39 with IO_TYPE=LVCMOS33D DRIVE=8
//      and standard Gowin/Sipeed lane order (_2 -> 35, _1 -> 37, _O -> 39).
//   3. Staged reset release (2.0 ms pll_locked qualification -> clkdiv_rst_n
//      -> oser_rst -> video_rst_n) and 1-cycle DVI pipeline registers
//      (red_dvi, green_dvi, blue_dvi, de_dvi, hsync_dvi, vsync_dvi).
//
//     IOB           16 /    384    4%
//     LUT4      15,349 / 20,736   74%
//     ALU        2,952 / 15,552   18%
//     DFF        6,178 / 15,552   39%
//     BSRAM         33 /     46   71%
//     MULT9X9       14 /     96   14%
//     MULT36X36      1 /     12    8%
//     Fmax      119.60 MHz  u_hcpu.clk_27m (PASS at the 12.00 MHz constraint)
//                86.01 MHz  pixel_clk      (PASS at the 12.00 MHz constraint)
//     Bitstream  7,261,470 bytes, sha256 7fe32ef6d41e6f371ea6ed1e1c5e648e9bcd8c98384476fdfcb42d8d92c199ab
//
// RTL FINGERPRINT: 5e8402deb52b82a4757f348009c9b9a53e0a09fa2d940eb2976e7c36cc4ce01d
//
`include "hcpu_pkg.vh"

module hcpu_hdmi_top #(
    parameter FONT_HEX             = "../../hcpu_font8x8.hex",
    parameter DASH_HEX             = "../../hcpu_dashboard.hex",
    parameter DASH_LOWER_HEX       = "../../hcpu_dashboard_lower.hex",
    parameter HOLO_HEX             = "../../hcpu_nui_holo.hex",
    parameter [0:0] BTN_ACTIVE_HIGH = 1'b1,
    parameter integer BTN_DEB_CLKS  = 270_000,    // 10.0 ms at 27.000 MHz
    parameter integer BTN_LONG_CLKS = 27_000_000  // 1.0 s at 27.000 MHz
) (
    input wire        clk_27m,
    input wire        btn_rst_n,   // Pin 87: S2 (KEY_S2 / PIN87_MODE1_KEY2) -> RESET / RECOVERY
    input wire        mode_key,    // Pin 88: S1 (KEY_S1 / PIN88_MODE0_KEY1) -> STOP / PAUSE
    input wire        uart_rxd,
    output wire       uart_txd,
    output wire [5:0] led,
    output wire       tmds_clk_p,
    output wire [2:0] tmds_data_p,
    output wire       sd_clk,
    inout  wire       sd_cmd,
    inout  wire [3:0] sd_dat
);
    wire serial_clk;
    wire pixel_clk;
    wire pll_locked;

    // ── Staged reset sequencer (aligned with Unified SoC Stage 1.5) ──
    localparam integer LOCK_QUAL_CYCLES   = 54_000;
    localparam integer CLKDIV_WAIT_CYCLES = 16;
    localparam integer TIMING_WAIT_CYCLES = 32;
    localparam integer QUAL_W = $clog2(LOCK_QUAL_CYCLES + 1);
    localparam integer WAIT_W = $clog2(TIMING_WAIT_CYCLES + 1);

    reg pll_s1 = 1'b0, pll_s2 = 1'b0;
    always @(posedge clk_27m) begin
        pll_s1 <= pll_locked;
        pll_s2 <= pll_s1;
    end

    reg [QUAL_W-1:0] qual_cnt       = {QUAL_W{1'b0}};
    reg [WAIT_W-1:0] seq_cnt        = {WAIT_W{1'b0}};
    reg              pll_qual_27m   = 1'b0;
    reg              clkdiv_rst_n   = 1'b0;
    reg              oser_rel_27m   = 1'b0;
    reg              timing_rel_27m = 1'b0;

    always @(posedge clk_27m) begin
        if (!pll_s2) begin
            qual_cnt       <= {QUAL_W{1'b0}};
            seq_cnt        <= {WAIT_W{1'b0}};
            pll_qual_27m   <= 1'b0;
            clkdiv_rst_n   <= 1'b0;
            oser_rel_27m   <= 1'b0;
            timing_rel_27m <= 1'b0;
        end else if (!pll_qual_27m) begin
            if (qual_cnt >= LOCK_QUAL_CYCLES - 1) begin
                pll_qual_27m <= 1'b1;
                clkdiv_rst_n <= 1'b1;
                seq_cnt      <= {WAIT_W{1'b0}};
            end else begin
                qual_cnt <= qual_cnt + 1'b1;
            end
        end else begin
            if (seq_cnt < TIMING_WAIT_CYCLES[WAIT_W-1:0])
                seq_cnt <= seq_cnt + 1'b1;
            if (seq_cnt >= CLKDIV_WAIT_CYCLES[WAIT_W-1:0] - 1'b1)
                oser_rel_27m <= 1'b1;
            if (seq_cnt >= TIMING_WAIT_CYCLES[WAIT_W-1:0] - 1'b1)
                timing_rel_27m <= 1'b1;
        end
    end

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
    wire oser_rst = oser_rst_s2;

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
    wire video_rst_n = vid_rst_s2;

    // ========================================================================
    // PHYSICAL BUTTON CONTROL (S1 PIN 88, S2 PIN 87) & FAULT RECOVERY FSM
    //   RAW BUTTON -> 2-FF SYNCHRONIZER -> DEBOUNCE -> EDGE DETECTOR -> FSM
    // ========================================================================
    // Tang Nano 20K (3921 schematic):
    //   - S1 (Pin 88, mode_key)  : idle LOW (0) via board pull-down, HIGH (1) when pressed
    //   - S2 (Pin 87, btn_rst_n) : idle LOW (0) via board pull-down, HIGH (1) when pressed
    //   - UPDATE (near HDMI)     : BL616 USB debugger DFU button (not wired to FPGA GPIO)
    localparam integer BDEB_W  = (BTN_DEB_CLKS  > 1) ? $clog2(BTN_DEB_CLKS  + 1) : 2;
    localparam integer BLONG_W = (BTN_LONG_CLKS > 1) ? $clog2(BTN_LONG_CLKS + 1) : 2;

    wire s1_raw = BTN_ACTIVE_HIGH ? mode_key  : ~mode_key;
    wire s2_raw = BTN_ACTIVE_HIGH ? btn_rst_n : ~btn_rst_n;

    reg s1_meta = 1'b0, s1_sync = 1'b0;
    reg s2_meta = 1'b0, s2_sync = 1'b0;
    always @(posedge clk_27m) begin
        s1_meta <= s1_raw;
        s1_sync <= s1_meta;
        s2_meta <= s2_raw;
        s2_sync <= s2_meta;
    end

    reg [BDEB_W-1:0]  s1_deb_cnt = {BDEB_W{1'b0}};
    reg               s1_deb     = 1'b0;
    reg [BDEB_W-1:0]  s2_deb_cnt = {BDEB_W{1'b0}};
    reg               s2_deb     = 1'b0;

    always @(posedge clk_27m or negedge video_rst_n) begin
        if (!video_rst_n) begin
            s1_deb_cnt <= {BDEB_W{1'b0}};
            s1_deb     <= 1'b0;
            s2_deb_cnt <= {BDEB_W{1'b0}};
            s2_deb     <= 1'b0;
        end else begin
            if (s1_sync != s1_deb) begin
                if (s1_deb_cnt >= BTN_DEB_CLKS[BDEB_W-1:0] - 1'b1) begin
                    s1_deb     <= s1_sync;
                    s1_deb_cnt <= {BDEB_W{1'b0}};
                end else begin
                    s1_deb_cnt <= s1_deb_cnt + 1'b1;
                end
            end else begin
                s1_deb_cnt <= {BDEB_W{1'b0}};
            end

            if (s2_sync != s2_deb) begin
                if (s2_deb_cnt >= BTN_DEB_CLKS[BDEB_W-1:0] - 1'b1) begin
                    s2_deb     <= s2_sync;
                    s2_deb_cnt <= {BDEB_W{1'b0}};
                end else begin
                    s2_deb_cnt <= s2_deb_cnt + 1'b1;
                end
            end else begin
                s2_deb_cnt <= {BDEB_W{1'b0}};
            end
        end
    end

    reg               s1_deb_d    = 1'b0;
    reg               s2_deb_d    = 1'b0;
    reg [BLONG_W-1:0] s1_hold_cnt = {BLONG_W{1'b0}};
    reg [BLONG_W-1:0] s2_hold_cnt = {BLONG_W{1'b0}};
    reg               s1_long_lat = 1'b0;
    reg               s2_long_lat = 1'b0;

    wire s1_rise = s1_deb & ~s1_deb_d;
    wire s1_fall = ~s1_deb & s1_deb_d;
    wire s2_rise = s2_deb & ~s2_deb_d;
    wire s2_fall = ~s2_deb & s2_deb_d;
    wire s1_long_pulse = s1_deb && !s1_long_lat && (s1_hold_cnt >= BTN_LONG_CLKS[BLONG_W-1:0] - 1'b1);
    wire s2_long_pulse = s2_deb && !s2_long_lat && (s2_hold_cnt >= BTN_LONG_CLKS[BLONG_W-1:0] - 1'b1);

    always @(posedge clk_27m or negedge video_rst_n) begin
        if (!video_rst_n) begin
            s1_deb_d    <= 1'b0;
            s2_deb_d    <= 1'b0;
            s1_hold_cnt <= {BLONG_W{1'b0}};
            s2_hold_cnt <= {BLONG_W{1'b0}};
            s1_long_lat <= 1'b0;
            s2_long_lat <= 1'b0;
        end else begin
            s1_deb_d <= s1_deb;
            s2_deb_d <= s2_deb;
            if (!s1_deb) begin
                s1_hold_cnt <= {BLONG_W{1'b0}};
                s1_long_lat <= 1'b0;
            end else begin
                if (s1_hold_cnt < BTN_LONG_CLKS[BLONG_W-1:0])
                    s1_hold_cnt <= s1_hold_cnt + 1'b1;
                if (s1_long_pulse)
                    s1_long_lat <= 1'b1;
            end
            if (!s2_deb) begin
                s2_hold_cnt <= {BLONG_W{1'b0}};
                s2_long_lat <= 1'b0;
            end else begin
                if (s2_hold_cnt < BTN_LONG_CLKS[BLONG_W-1:0])
                    s2_hold_cnt <= s2_hold_cnt + 1'b1;
                if (s2_long_pulse)
                    s2_long_lat <= 1'b1;
            end
        end
    end

    // Canonical Control & Fault FSM States:
    localparam [2:0] CTRL_RUNNING       = 3'd0,
                     CTRL_STOPPED       = 3'd1,
                     CTRL_PAUSED        = 3'd2,
                     CTRL_RESETTING     = 3'd3,
                     CTRL_FAULT         = 3'd4,
                     CTRL_FAULT_LATCHED = 3'd5,
                     CTRL_READY         = 3'd6;

    // Button Event Codes:
    localparam [2:0] EV_BTN_NONE        = 3'd0,
                     EV_BTN_USER_STOP   = 3'd1,
                     EV_BTN_USER_RESUME = 3'd2,
                     EV_BTN_USER_RESET  = 3'd3,
                     EV_BTN_FAULT_REC   = 3'd4,
                     EV_BTN_FLT_LATCHED = 3'd5,
                     EV_BTN_S1_S2_STOP  = 3'd6;

    // Fault Source Codes:
    localparam [2:0] FLT_NONE           = 3'd0,
                     FLT_GUARD          = 3'd1, // HGRD evaluated & FLAG_G == 0
                     FLT_HALTERR        = 3'd2, // Illegal opcode / invalid ROM index halt
                     FLT_EXT_ACTIVE     = 3'd3; // Persistent external / injected fault

    // Recovery Result Codes:
    localparam [2:0] REC_IDLE           = 3'd0,
                     REC_IN_PROGRESS    = 3'd1,
                     REC_OK_READY       = 3'd2,
                     REC_FAIL_ACTIVE    = 3'd3;

    // Simulation hook for testing persistent fault sources (Scenarios 3, 6, 7, 8)
    reg sim_fault_source_active = 1'b0;

    reg [2:0] ctrl_state      = CTRL_RUNNING;
    reg [2:0] pre_btn_state   = CTRL_RUNNING;
    reg [2:0] post_btn_state  = CTRL_RUNNING;
    reg [2:0] last_btn_event  = EV_BTN_NONE;
    reg [2:0] fault_code      = FLT_NONE;
    reg       fault_latched   = 1'b0;
    reg [2:0] recovery_result = REC_IDLE;
    reg [7:0] s1_press_cnt    = 8'd0;
    reg [7:0] s2_press_cnt    = 8'd0;
    reg [7:0] recovery_cnt    = 8'd0;
    reg [4:0] rst_seq_cnt     = 5'd0;
    reg       core_rst_trig   = 1'b0; // 1 -> 0 falling edge triggers hcpu_gowin_core reset

    // Forward declarations for HCPU telemetry signals (raw from u_hcpu + freeze-latched on S1 STOP/PAUSE)
    wire        hcpu_uart_txd;
    wire [5:0]  hcpu_led;
    wire [`CODE_ADDR_W-1:0] raw_tele_pc;
    wire [`ILEN-1:0]        raw_tele_instr;
    wire                    tele_halted;
    wire                    tele_guard;
    wire [31:0]             raw_tele_cycles;
    wire [7:0]              raw_tele_flags;

    wire cpu_run_enable = (ctrl_state == CTRL_RUNNING)
                       || (ctrl_state == CTRL_RESETTING)
                       || (ctrl_state == CTRL_READY);

    reg [`CODE_ADDR_W-1:0] tele_pc_lat     = {`CODE_ADDR_W{1'b0}};
    reg [`ILEN-1:0]        tele_instr_lat  = {`ILEN{1'b0}};
    reg [31:0]             tele_cycles_lat = 32'd0;
    reg [7:0]              tele_flags_lat  = 8'd0;
    always @(posedge clk_27m or negedge video_rst_n) begin
        if (!video_rst_n) begin
            tele_pc_lat     <= {`CODE_ADDR_W{1'b0}};
            tele_instr_lat  <= {`ILEN{1'b0}};
            tele_cycles_lat <= 32'd0;
            tele_flags_lat  <= 8'd0;
        end else if (cpu_run_enable) begin
            tele_pc_lat     <= raw_tele_pc;
            tele_instr_lat  <= raw_tele_instr;
            tele_cycles_lat <= raw_tele_cycles;
            tele_flags_lat  <= raw_tele_flags;
        end
    end
    wire [`CODE_ADDR_W-1:0] tele_pc     = cpu_run_enable ? raw_tele_pc     : tele_pc_lat;
    wire [`ILEN-1:0]        tele_instr  = cpu_run_enable ? raw_tele_instr  : tele_instr_lat;
    wire [31:0]             tele_cycles = cpu_run_enable ? raw_tele_cycles : tele_cycles_lat;
    wire [7:0]              tele_flags  = cpu_run_enable ? raw_tele_flags  : tele_flags_lat;
    wire                    hcpu_uart_rxd = cpu_run_enable ? uart_rxd : 1'b1;

    // Track whether OP_HGRD (0x43) or OP_HALT (0xFF)/OP_RET (0x2F) executed in the current run:
    // At reset, u_regfile.flags resets to 0x00 (FLAG_G = 0) and loader.hasm never executes HGRD.
    // Treating FLAG_G=0 before HGRD executes as a fault caused the false GUARD: FAULT lockup.
    reg       rtm_seen_hgrd        = 1'b0;
    reg [2:0] rtm_hgrd_pipe_cnt    = 3'd0;
    reg       rtm_seen_normal_halt = 1'b0;

    wire [7:0] rtm_cur_op = tele_instr[31:24];
    wire       hw_guard_evaluated = rtm_seen_hgrd && (rtm_hgrd_pipe_cnt == 3'd0);
    wire       hw_guard_fault     = hw_guard_evaluated && (~tele_guard);
    wire       hw_halterr_fault   = tele_halted && (~rtm_seen_normal_halt);
    wire       any_fault_active   = hw_guard_fault | hw_halterr_fault | sim_fault_source_active;

    always @(posedge clk_27m or negedge video_rst_n) begin
        if (!video_rst_n) begin
            ctrl_state      <= CTRL_RUNNING;
            pre_btn_state   <= CTRL_RUNNING;
            post_btn_state  <= CTRL_RUNNING;
            last_btn_event  <= EV_BTN_NONE;
            fault_code      <= FLT_NONE;
            fault_latched   <= 1'b0;
            recovery_result <= REC_IDLE;
            s1_press_cnt    <= 8'd0;
            s2_press_cnt    <= 8'd0;
            recovery_cnt    <= 8'd0;
            rst_seq_cnt     <= 5'd0;
            core_rst_trig   <= 1'b0;
        end else begin
            // Default: keep core_rst_trig HIGH so a 1->0 pulse triggers hcpu_gowin_core's edge detector
            core_rst_trig <= 1'b1;

            // 1. Hardware fault detection (never masked or faked)
            if (sim_fault_source_active) begin
                fault_latched <= 1'b1;
                fault_code    <= FLT_EXT_ACTIVE;
            end else if (hw_guard_fault && (ctrl_state != CTRL_RESETTING)) begin
                fault_latched <= 1'b1;
                fault_code    <= FLT_GUARD;
            end else if (hw_halterr_fault && (ctrl_state != CTRL_RESETTING)) begin
                fault_latched <= 1'b1;
                fault_code    <= FLT_HALTERR;
            end

            // 2. Highest priority application control: S1 (STOP / PAUSE)
            if (s1_rise) begin
                s1_press_cnt  <= s1_press_cnt + 8'd1;
                pre_btn_state <= ctrl_state;
                if (s2_deb) begin
                    // Simultaneous S1 + S2: S1 STOP priority wins
                    ctrl_state     <= CTRL_STOPPED;
                    post_btn_state <= CTRL_STOPPED;
                    last_btn_event <= EV_BTN_S1_S2_STOP;
                end else if ((ctrl_state == CTRL_STOPPED) && !fault_latched && !any_fault_active) begin
                    // Pressing S1 again from clean STOPPED resumes execution
                    ctrl_state     <= CTRL_RUNNING;
                    post_btn_state <= CTRL_RUNNING;
                    last_btn_event <= EV_BTN_USER_RESUME;
                end else begin
                    // S1 from RUNNING, HALTED, FAULT, or FAULT_LATCHED -> PAUSED/STOPPED
                    ctrl_state     <= CTRL_PAUSED;
                    post_btn_state <= CTRL_STOPPED;
                    last_btn_event <= EV_BTN_USER_STOP;
                end
            end else if (s1_fall && (ctrl_state == CTRL_PAUSED)) begin
                ctrl_state     <= CTRL_STOPPED;
                post_btn_state <= CTRL_STOPPED;
            end else if (s2_rise) begin
                // 3. S2 (RESET / RECOVERY)
                s2_press_cnt  <= s2_press_cnt + 8'd1;
                pre_btn_state <= ctrl_state;
                if (s1_deb) begin
                    // S1 is held: S1 STOP priority wins
                    ctrl_state     <= CTRL_STOPPED;
                    post_btn_state <= CTRL_STOPPED;
                    last_btn_event <= EV_BTN_S1_S2_STOP;
                end else if (sim_fault_source_active) begin
                    // Fault cause is STILL ACTIVE: refuse to clear fault, latch FAULT LATCHED!
                    ctrl_state      <= CTRL_FAULT_LATCHED;
                    post_btn_state  <= CTRL_FAULT_LATCHED;
                    last_btn_event  <= EV_BTN_FLT_LATCHED;
                    fault_latched   <= 1'b1;
                    fault_code      <= FLT_EXT_ACTIVE;
                    recovery_result <= REC_FAIL_ACTIVE;
                end else begin
                    // Fault source is no longer active (or normal reset from STOPPED/RUNNING):
                    // Execute hardware reset sequence!
                    ctrl_state      <= CTRL_RESETTING;
                    post_btn_state  <= CTRL_READY;
                    last_btn_event  <= (fault_latched || (ctrl_state == CTRL_FAULT) || (ctrl_state == CTRL_FAULT_LATCHED))
                                       ? EV_BTN_FAULT_REC : EV_BTN_USER_RESET;
                    recovery_result <= REC_IN_PROGRESS;
                    rst_seq_cnt     <= 5'd0;
                end
            end else begin
                // 4. Autonomous state transitions when no button edge occurs
                case (ctrl_state)
                    CTRL_RUNNING: begin
                        if (any_fault_active || fault_latched) begin
                            ctrl_state <= CTRL_FAULT;
                        end
                    end
                    CTRL_PAUSED: begin
                        if (!s1_deb)
                            ctrl_state <= CTRL_STOPPED;
                    end
                    CTRL_STOPPED: begin
                        // Remain safely stopped until S2 recovery or S1 resume (if no fault)
                    end
                    CTRL_FAULT: begin
                        // Remain in FAULT until S1 stops or S2 recovers
                    end
                    CTRL_FAULT_LATCHED: begin
                        // Remain in FAULT LATCHED until fault source clears and S2 recovers
                    end
                    CTRL_RESETTING: begin
                        rst_seq_cnt <= rst_seq_cnt + 5'd1;
                        // Drive 1 -> 0 falling edge on core_rst_trig at cycle 2..6 so hcpu_gowin_core resets
                        if (rst_seq_cnt >= 5'd2 && rst_seq_cnt <= 5'd6)
                            core_rst_trig <= 1'b0;
                        else
                            core_rst_trig <= 1'b1;

                        if (rst_seq_cnt == 5'd12) begin
                            if (!sim_fault_source_active) begin
                                fault_latched <= 1'b0;
                                fault_code    <= FLT_NONE;
                            end
                        end
                        if (rst_seq_cnt >= 5'd15) begin
                            if (sim_fault_source_active) begin
                                ctrl_state      <= CTRL_FAULT_LATCHED;
                                post_btn_state  <= CTRL_FAULT_LATCHED;
                                recovery_result <= REC_FAIL_ACTIVE;
                            end else begin
                                ctrl_state      <= CTRL_READY;
                                post_btn_state  <= CTRL_READY;
                                recovery_result <= REC_OK_READY;
                                recovery_cnt    <= recovery_cnt + 8'd1;
                                rst_seq_cnt     <= 5'd0;
                            end
                        end
                    end
                    CTRL_READY: begin
                        rst_seq_cnt <= rst_seq_cnt + 5'd1;
                        if (any_fault_active) begin
                            ctrl_state <= CTRL_FAULT;
                        end else if (rst_seq_cnt >= 5'd7) begin
                            ctrl_state     <= CTRL_RUNNING;
                            post_btn_state <= CTRL_RUNNING;
                        end
                    end
                    default: ctrl_state <= CTRL_RUNNING;
                endcase
            end
        end
    end

    // True hardware guard fault indicator: never faked, and never falsely triggered by loader.hasm or S1
    wire true_guard_fault = any_fault_active | fault_latched;

    // ── HCPU Core Instantiation ──────────────────────────────────
    hcpu_gowin_core #(.USE_DSP(1)) u_hcpu (
        .clk_27m(clk_27m), .btn_rst_n(core_rst_trig), .uart_rxd(hcpu_uart_rxd),
        .uart_txd(hcpu_uart_txd), .led(hcpu_led),
        .sd_clk(sd_clk), .sd_cmd(sd_cmd), .sd_dat(sd_dat),
        .tele_pc(raw_tele_pc), .tele_instr(raw_tele_instr),
        .tele_halted(tele_halted), .tele_guard(tele_guard),
        .tele_cycles(raw_tele_cycles), .tele_flags(raw_tele_flags)
    );

    TMDS_rPLL u_tmds_rpll (.clkin(clk_27m), .clkout(serial_clk), .lock(pll_locked));
    CLKDIV u_clkdiv (
        .RESETN(clkdiv_rst_n), .HCLKIN(serial_clk), .CLKOUT(pixel_clk), .CALIB(1'b1)
    );
    defparam u_clkdiv.DIV_MODE = "5";
    defparam u_clkdiv.GSREN = "false";

    wire hsync;
    wire vsync;
    wire de;
    wire [11:0] x;
    wire [11:0] y;
    wire [11:0] h_count;
    wire [11:0] v_count;
    wire        frame_tick;
    wire tmds_clk_serial;
    wire [2:0] tmds_data_serial;

    hcpu_video_timing #(
        .H_ACTIVE(1280), .H_FRONT(110), .H_SYNC(40), .H_BACK(220),
        .V_ACTIVE(720), .V_FRONT(5), .V_SYNC(5), .V_BACK(20),
        .HSYNC_POL(1'b1), .VSYNC_POL(1'b1)
    ) u_timing (
        .pixel_clk(pixel_clk), .rst_n(video_rst_n), .hsync(hsync), .vsync(vsync),
        .de(de), .x(x), .y(y), .frame_tick(frame_tick),
        .h_count_o(h_count), .v_count_o(v_count)
    );

    // Keep page locked to 0 so pressing S1 (STOP/PAUSE) never blanks the monitor to NOT INSTRUMENTED.
    // Instantiate hcpu_page_key with idle-high input so the module hierarchy remains unchanged.
    wire [3:0] page_unused;
    hcpu_page_key #(
        .DEBOUNCE(750_000), .LONG(74_250_000), .PAGES(9)
    ) u_page (
        .clk(pixel_clk), .rst_n(video_rst_n), .key_n(1'b1), .page(page_unused)
    );
    wire [3:0] page = 4'd0;

    wire        tele_sample = frame_tick;
    wire [`CODE_ADDR_W-1:0] snap_pc;
    wire [`ILEN-1:0]        snap_instr;
    wire                    snap_halted, snap_guard, snap_valid;
    wire [31:0]             snap_cycles;
    wire [7:0]              snap_flags;

    // Pass ~true_guard_fault into u_tele.guard so snap_guard=1 means OK and snap_guard=0 means FAULT
    hcpu_telemetry #(.PCW(`CODE_ADDR_W)) u_tele (
        .cpu_clk(clk_27m), .cpu_rst_n(video_rst_n),
        .pc(tele_pc), .instr(tele_instr), .halted(tele_halted),
        .guard(~true_guard_fault), .cycles(tele_cycles), .flags(tele_flags),
        .vid_clk(pixel_clk), .vid_rst_n(video_rst_n), .sample(tele_sample),
        .snap_pc(snap_pc), .snap_instr(snap_instr), .snap_halted(snap_halted),
        .snap_guard(snap_guard), .snap_cycles(snap_cycles),
        .snap_flags(snap_flags), .snap_valid(snap_valid)
    );

    // ── Full-Screen 90-Row Dual-BSRAM Layout ROMs (14,400 cells) ──
    wire [13:0] cell_addr;
    wire [11:0] layout_upper_data;
    wire [11:0] layout_lower_data;

    localparam [13:0] ROM_DIRECT_END = 14'd6720;  // Rows 0..41
    localparam [13:0] ROM_FOOT_FIRST = 14'd13440; // Rows 84..89
    localparam [13:0] ROM_SCREEN_END = 14'd14400;
    localparam [13:0] ROM_FOOT_SHIFT = 14'd6720;

    wire        rom_direct = (cell_addr < ROM_DIRECT_END);
    wire        rom_lower  = (cell_addr >= ROM_DIRECT_END) && (cell_addr < ROM_FOOT_FIRST);
    wire        rom_footer = (cell_addr >= ROM_FOOT_FIRST) && (cell_addr < ROM_SCREEN_END);
    wire        rom_valid  = rom_direct | rom_lower | rom_footer;
    wire [13:0] rom_folded = cell_addr - ROM_FOOT_SHIFT;
    wire [12:0] rom_upper_addr = rom_direct ? cell_addr[12:0]
                               : rom_footer ? rom_folded[12:0]
                               : 13'd7680;
    wire [12:0] rom_lower_addr = rom_lower ? rom_folded[12:0] : 13'd6720;

    hcpu_layout_rom #(.LAYOUT_HEX(DASH_HEX)) u_layout (
        .clk(pixel_clk), .addr(rom_upper_addr), .data(layout_upper_data)
    );

    hcpu_layout_rom #(.LAYOUT_HEX(DASH_LOWER_HEX)) u_layout_lower (
        .clk(pixel_clk), .addr(rom_lower_addr), .data(layout_lower_data)
    );

    wire       comp_hit;
    wire [7:0] comp_ch;
    wire [3:0] comp_at;
    wire       comp_guard_fault = ~snap_guard;

    hcpu_compositor #(.PCW(`CODE_ADDR_W)) u_comp (
        .cell_addr(cell_addr), .page(page),
        .snap_pc(snap_pc), .snap_instr(snap_instr), .snap_halted(snap_halted),
        .snap_guard(comp_guard_fault), .snap_cycles(snap_cycles),
        .snap_flags(snap_flags), .snap_valid(snap_valid),
        .hit(comp_hit), .ch(comp_ch), .at(comp_at)
    );

    // ========================================================================
    // REAL-TIME COMPUTING & NUI L0–L11 HARDWARE MONITOR
    // ========================================================================
    localparam integer RTM_PCW = `CODE_ADDR_W;
    localparam [3:0] RTM_C_DIM    = 4'd0, RTM_C_WHITE  = 4'd1, RTM_C_CYAN = 4'd2,
                     RTM_C_GREEN  = 4'd3, RTM_C_YELLOW = 4'd4, RTM_C_RED  = 4'd5,
                     RTM_C_BLUE   = 4'd6, RTM_C_GOLD   = 4'd7;

    reg [RTM_PCW-1:0] rtm_prev_pc;
    reg               rtm_prev_valid;
    wire [3:0]        rtm_cur_dst = tele_instr[23:20];
    wire [3:0]        rtm_cur_s1  = tele_instr[19:16];
    wire              rtm_step_en      = cpu_run_enable && !tele_halted && (!rtm_prev_valid || (tele_pc != rtm_prev_pc));
    wire              rtm_loader_entry = rtm_step_en && (tele_pc == 12'd64) && (rtm_prev_pc < 12'd63);
    wire              rtm_in_reset     = (ctrl_state == CTRL_RESETTING);

    wire rtm_is_letter_op = (rtm_cur_op >= 8'hE0) && (rtm_cur_op <= 8'hFB);
    wire rtm_is_codex_op  = ((rtm_cur_op >= 8'h40) && (rtm_cur_op <= 8'h4F))
                         || (rtm_cur_op == 8'h60)
                         || (rtm_cur_op == 8'h06)
                         || (rtm_cur_op == 8'h07)
                         || ((rtm_cur_op >= 8'h50) && (rtm_cur_op <= 8'h52));
    wire rtm_is_math_op   = rtm_is_letter_op | rtm_is_codex_op;

    reg [15:0]        rtm_step_cnt;
    reg [7:0]         rtm_last_op;
    reg [3:0]         rtm_last_dst;
    reg [3:0]         rtm_last_s1;
    reg [RTM_PCW-1:0] rtm_boot_pc;
    reg [7:0]         rtm_boot_op;
    reg               rtm_seen_boot;
    reg [7:0]         rtm_last_letter_op;
    reg [7:0]         rtm_last_codex_op;
    reg [15:0]        rtm_math_cnt;

    always @(posedge clk_27m or negedge video_rst_n) begin
        if (!video_rst_n) begin
            rtm_prev_pc          <= {RTM_PCW{1'b0}};
            rtm_prev_valid       <= 1'b0;
            rtm_step_cnt         <= 16'd0;
            rtm_last_op          <= 8'h00;
            rtm_last_dst         <= 4'd0;
            rtm_last_s1          <= 4'd0;
            rtm_boot_pc          <= {RTM_PCW{1'b0}};
            rtm_boot_op          <= 8'h00;
            rtm_seen_boot        <= 1'b0;
            rtm_last_letter_op   <= 8'h00;
            rtm_last_codex_op    <= 8'h00;
            rtm_math_cnt         <= 16'd0;
            rtm_seen_hgrd        <= 1'b0;
            rtm_hgrd_pipe_cnt    <= 3'd0;
            rtm_seen_normal_halt <= 1'b0;
        end else if (rtm_in_reset) begin
            rtm_prev_pc          <= {RTM_PCW{1'b0}};
            rtm_prev_valid       <= 1'b0;
            rtm_step_cnt         <= 16'd0;
            rtm_last_op          <= 8'h00;
            rtm_last_dst         <= 4'd0;
            rtm_last_s1          <= 4'd0;
            rtm_seen_boot        <= 1'b0;
            rtm_last_letter_op   <= 8'h00;
            rtm_last_codex_op    <= 8'h00;
            rtm_math_cnt         <= 16'd0;
            rtm_seen_hgrd        <= 1'b0;
            rtm_hgrd_pipe_cnt    <= 3'd0;
            rtm_seen_normal_halt <= 1'b0;
        end else begin
            if (cpu_run_enable) begin
                rtm_prev_pc    <= tele_pc;
                rtm_prev_valid <= 1'b1;
                if (rtm_hgrd_pipe_cnt != 3'd0)
                    rtm_hgrd_pipe_cnt <= rtm_hgrd_pipe_cnt - 3'd1;
            end
            if (rtm_loader_entry) begin
                rtm_step_cnt         <= 16'd1;
                if (rtm_cur_op != 8'h00) begin
                    rtm_last_op  <= rtm_cur_op;
                    rtm_last_dst <= rtm_cur_dst;
                    rtm_last_s1  <= rtm_cur_s1;
                end
                rtm_boot_pc          <= tele_pc;
                rtm_boot_op          <= rtm_cur_op;
                rtm_seen_boot        <= 1'b1;
                rtm_last_letter_op   <= rtm_is_letter_op ? rtm_cur_op : 8'h00;
                rtm_last_codex_op    <= rtm_is_codex_op  ? rtm_cur_op : 8'h00;
                rtm_math_cnt         <= rtm_is_math_op   ? 16'd1      : 16'd0;
                rtm_seen_hgrd        <= (rtm_cur_op == 8'h43);
                rtm_hgrd_pipe_cnt    <= (rtm_cur_op == 8'h43) ? 3'd5 : 3'd0;
                rtm_seen_normal_halt <= (rtm_cur_op == 8'hFF) || (rtm_cur_op == 8'h2F);
            end else if (rtm_step_en) begin
                rtm_step_cnt <= rtm_step_cnt + 16'd1;
                if (rtm_cur_op != 8'h00) begin
                    rtm_last_op  <= rtm_cur_op;
                    rtm_last_dst <= rtm_cur_dst;
                    rtm_last_s1  <= rtm_cur_s1;
                end
                if (!rtm_seen_boot) begin
                    rtm_boot_pc   <= tele_pc;
                    rtm_boot_op   <= rtm_cur_op;
                    rtm_seen_boot <= 1'b1;
                end
                if (rtm_is_letter_op) rtm_last_letter_op <= rtm_cur_op;
                if (rtm_is_codex_op)  rtm_last_codex_op  <= rtm_cur_op;
                if (rtm_is_math_op)   rtm_math_cnt       <= rtm_math_cnt + 16'd1;
                if (rtm_cur_op == 8'h43) begin
                    rtm_seen_hgrd     <= 1'b1;
                    rtm_hgrd_pipe_cnt <= 3'd5;
                end
                if ((rtm_cur_op == 8'hFF) || (rtm_cur_op == 8'h2F))
                    rtm_seen_normal_halt <= 1'b1;
            end
        end
    end

    // 2. UART TX Sniffer for OP_PRINT Decimal Stream
    wire [7:0] rtm_rx_byte;
    wire       rtm_rx_valid;
    wire       rtm_rx_err;

    hcpu_uart_rx #(
        .CLK_HZ(27_000_000), .BAUD(115200)
    ) u_mon_rx (
        .clk(clk_27m), .rst_n(video_rst_n), .rx_in(hcpu_uart_txd),
        .rx_data(rtm_rx_byte), .rx_valid(rtm_rx_valid), .rx_frame_err(rtm_rx_err)
    );

    reg [15:0] rtm_uart_byte_cnt;
    reg [7:0]  rtm_cur_dec;
    reg        rtm_in_num;
    reg        rtm_seen_eq;
    reg [7:0]  rtm_print_cnt;
    reg [7:0]  rtm_last_print;
    reg [7:0]  rtm_p0_titik;
    reg [7:0]  rtm_p1_garis;
    reg [7:0]  rtm_p2_lengkung;
    reg [7:0]  rtm_p3_theta;
    reg [7:0]  rtm_p4_rho;
    reg [7:0]  rtm_p5_hnrm2;
    reg [7:0]  rtm_p6_hdist;
    reg [7:0]  rtm_p7_hdot;

    wire [7:0] rtm_dec_mul10 = (rtm_cur_dec << 3) + (rtm_cur_dec << 1);

    always @(posedge clk_27m or negedge video_rst_n) begin
        if (!video_rst_n) begin
            rtm_uart_byte_cnt <= 16'd0;
            rtm_cur_dec       <= 8'd0;
            rtm_in_num        <= 1'b0;
            rtm_seen_eq       <= 1'b0;
            rtm_print_cnt     <= 8'd0;
            rtm_last_print    <= 8'd0;
            rtm_p0_titik      <= 8'd0;
            rtm_p1_garis      <= 8'd0;
            rtm_p2_lengkung   <= 8'd0;
            rtm_p3_theta      <= 8'd0;
            rtm_p4_rho        <= 8'd0;
            rtm_p5_hnrm2      <= 8'd0;
            rtm_p6_hdist      <= 8'd0;
            rtm_p7_hdot       <= 8'd0;
        end else if (rtm_loader_entry || rtm_in_reset) begin
            rtm_cur_dec     <= 8'd0;
            rtm_in_num      <= 1'b0;
            rtm_seen_eq     <= 1'b0;
            rtm_print_cnt   <= 8'd0;
            rtm_last_print  <= 8'd0;
            rtm_p0_titik    <= 8'd0;
            rtm_p1_garis    <= 8'd0;
            rtm_p2_lengkung <= 8'd0;
            rtm_p3_theta    <= 8'd0;
            rtm_p4_rho      <= 8'd0;
            rtm_p5_hnrm2    <= 8'd0;
            rtm_p6_hdist    <= 8'd0;
            rtm_p7_hdot     <= 8'd0;
        end else if (rtm_rx_valid && !rtm_rx_err) begin
            rtm_uart_byte_cnt <= rtm_uart_byte_cnt + 16'd1;
            if (rtm_rx_byte == "=") begin
                rtm_seen_eq <= 1'b1;
                rtm_in_num  <= 1'b0;
            end else if (rtm_rx_byte >= "0" && rtm_rx_byte <= "9" && !rtm_seen_eq) begin
                rtm_cur_dec <= rtm_dec_mul10 + {4'd0, rtm_rx_byte[3:0]};
                rtm_in_num  <= 1'b1;
            end else if (rtm_rx_byte == 8'h0A) begin
                if (rtm_in_num && !rtm_seen_eq) begin
                    rtm_last_print <= rtm_cur_dec;
                    case (rtm_print_cnt[2:0])
                        3'd0: rtm_p0_titik    <= rtm_cur_dec;
                        3'd1: rtm_p1_garis    <= rtm_cur_dec;
                        3'd2: rtm_p2_lengkung <= rtm_cur_dec;
                        3'd3: rtm_p3_theta    <= rtm_cur_dec;
                        3'd4: rtm_p4_rho      <= rtm_cur_dec;
                        3'd5: rtm_p5_hnrm2    <= rtm_cur_dec;
                        3'd6: rtm_p6_hdist    <= rtm_cur_dec;
                        3'd7: rtm_p7_hdot     <= rtm_cur_dec;
                    endcase
                    if (rtm_print_cnt < 8'hFF)
                        rtm_print_cnt <= rtm_print_cnt + 8'd1;
                end
                rtm_cur_dec <= 8'd0;
                rtm_in_num  <= 1'b0;
                rtm_seen_eq <= 1'b0;
            end
        end
    end

    // 3. Coherent 2-FF Toggle-Handshake CDC Snapshot (`clk_27m` -> `pixel_clk`)
    reg rtm_req;
    always @(posedge pixel_clk or negedge video_rst_n) begin
        if (!video_rst_n) rtm_req <= 1'b0;
        else if (tele_sample) rtm_req <= ~rtm_req;
    end

    reg rtm_req_s1, rtm_req_s2, rtm_req_s3;
    reg rtm_ack;
    always @(posedge clk_27m or negedge video_rst_n) begin
        if (!video_rst_n) begin
            rtm_req_s1 <= 1'b0; rtm_req_s2 <= 1'b0; rtm_req_s3 <= 1'b0;
            rtm_ack    <= 1'b0;
        end else begin
            rtm_req_s1 <= rtm_req; rtm_req_s2 <= rtm_req_s1; rtm_req_s3 <= rtm_req_s2;
            if (rtm_req_s2 ^ rtm_req_s3) rtm_ack <= ~rtm_ack;
        end
    end

    reg rtm_ack_s1, rtm_ack_s2, rtm_ack_s3;
    always @(posedge pixel_clk or negedge video_rst_n) begin
        if (!video_rst_n) begin
            rtm_ack_s1 <= 1'b0; rtm_ack_s2 <= 1'b0; rtm_ack_s3 <= 1'b0;
        end else begin
            rtm_ack_s1 <= rtm_ack; rtm_ack_s2 <= rtm_ack_s1; rtm_ack_s3 <= rtm_ack_s2;
        end
    end
    wire rtm_ack_edge = rtm_ack_s2 ^ rtm_ack_s3;

    reg [15:0]        rtm_s_step_cnt;
    reg [7:0]         rtm_s_last_op;
    reg [3:0]         rtm_s_last_dst, rtm_s_last_s1;
    reg [RTM_PCW-1:0] rtm_s_boot_pc;
    reg [7:0]         rtm_s_boot_op;
    reg [7:0]         rtm_s_last_letter_op, rtm_s_last_codex_op;
    reg [15:0]        rtm_s_math_cnt;
    reg [15:0]        rtm_s_uart_bytes;
    reg [7:0]         rtm_s_last_print, rtm_s_print_cnt;
    reg [7:0]         rtm_s_p0, rtm_s_p1, rtm_s_p2, rtm_s_p3;
    reg [7:0]         rtm_s_p4, rtm_s_p5, rtm_s_p6, rtm_s_p7;
    reg [15:0]        rtm_s_cdc_frames;

    // Button & Fault FSM CDC snapshot registers in pixel_clk
    reg [2:0]         rtm_s_ctrl_state;
    reg [2:0]         rtm_s_pre_state;
    reg [2:0]         rtm_s_post_state;
    reg [2:0]         rtm_s_last_ev;
    reg [2:0]         rtm_s_fault_code;
    reg               rtm_s_fault_lat;
    reg [2:0]         rtm_s_rec_res;
    reg [3:0]         rtm_s_s1_cnt, rtm_s_s2_cnt, rtm_s_rec_cnt;
    reg               rtm_s_s1_raw, rtm_s_s1_sync, rtm_s_s1_deb;
    reg               rtm_s_s2_raw, rtm_s_s2_sync, rtm_s_s2_deb;

    always @(posedge pixel_clk or negedge video_rst_n) begin
        if (!video_rst_n) begin
            rtm_s_step_cnt       <= 16'd0;
            rtm_s_last_op        <= 8'd0;
            rtm_s_last_dst       <= 4'd0;
            rtm_s_last_s1        <= 4'd0;
            rtm_s_boot_pc        <= {RTM_PCW{1'b0}};
            rtm_s_boot_op        <= 8'd0;
            rtm_s_last_letter_op <= 8'd0;
            rtm_s_last_codex_op  <= 8'd0;
            rtm_s_math_cnt       <= 16'd0;
            rtm_s_uart_bytes     <= 16'd0;
            rtm_s_last_print     <= 8'd0;
            rtm_s_print_cnt      <= 8'd0;
            rtm_s_p0 <= 8'd0; rtm_s_p1 <= 8'd0; rtm_s_p2 <= 8'd0; rtm_s_p3 <= 8'd0;
            rtm_s_p4 <= 8'd0; rtm_s_p5 <= 8'd0; rtm_s_p6 <= 8'd0; rtm_s_p7 <= 8'd0;
            rtm_s_cdc_frames     <= 16'd0;
            rtm_s_ctrl_state     <= CTRL_RUNNING;
            rtm_s_pre_state      <= CTRL_RUNNING;
            rtm_s_post_state     <= CTRL_RUNNING;
            rtm_s_last_ev        <= EV_BTN_NONE;
            rtm_s_fault_code     <= FLT_NONE;
            rtm_s_fault_lat      <= 1'b0;
            rtm_s_rec_res        <= REC_IDLE;
            rtm_s_s1_cnt         <= 4'd0;
            rtm_s_s2_cnt         <= 4'd0;
            rtm_s_rec_cnt        <= 4'd0;
            rtm_s_s1_raw <= 1'b0; rtm_s_s1_sync <= 1'b0; rtm_s_s1_deb <= 1'b0;
            rtm_s_s2_raw <= 1'b0; rtm_s_s2_sync <= 1'b0; rtm_s_s2_deb <= 1'b0;
        end else if (rtm_ack_edge) begin
            rtm_s_step_cnt       <= rtm_step_cnt;
            rtm_s_last_op        <= rtm_last_op;
            rtm_s_last_dst       <= rtm_last_dst;
            rtm_s_last_s1        <= rtm_last_s1;
            rtm_s_boot_pc        <= rtm_boot_pc;
            rtm_s_boot_op        <= rtm_boot_op;
            rtm_s_last_letter_op <= rtm_last_letter_op;
            rtm_s_last_codex_op  <= rtm_last_codex_op;
            rtm_s_math_cnt       <= rtm_math_cnt;
            rtm_s_uart_bytes     <= rtm_uart_byte_cnt;
            rtm_s_last_print     <= rtm_last_print;
            rtm_s_print_cnt      <= rtm_print_cnt;
            rtm_s_p0 <= rtm_p0_titik;    rtm_s_p1 <= rtm_p1_garis;
            rtm_s_p2 <= rtm_p2_lengkung; rtm_s_p3 <= rtm_p3_theta;
            rtm_s_p4 <= rtm_p4_rho;      rtm_s_p5 <= rtm_p5_hnrm2;
            rtm_s_p6 <= rtm_p6_hdist;    rtm_s_p7 <= rtm_p7_hdot;
            rtm_s_cdc_frames     <= rtm_s_cdc_frames + 16'd1;
            rtm_s_ctrl_state     <= ctrl_state;
            rtm_s_pre_state      <= pre_btn_state;
            rtm_s_post_state     <= post_btn_state;
            rtm_s_last_ev        <= last_btn_event;
            rtm_s_fault_code     <= fault_code;
            rtm_s_fault_lat      <= fault_latched;
            rtm_s_rec_res        <= recovery_result;
            rtm_s_s1_cnt         <= s1_press_cnt[3:0];
            rtm_s_s2_cnt         <= s2_press_cnt[3:0];
            rtm_s_rec_cnt        <= recovery_cnt[3:0];
            rtm_s_s1_raw <= s1_raw; rtm_s_s1_sync <= s1_sync; rtm_s_s1_deb <= s1_deb;
            rtm_s_s2_raw <= s2_raw; rtm_s_s2_sync <= s2_sync; rtm_s_s2_deb <= s2_deb;
        end
    end

    // 4. Pipelined Shared Hex Digit Formatter at pos = 4..7 + State Override at BLK_STATE (111)
    // Note: cell_addr = {rtm_blk, rtm_pos}, where rtm_blk changes only at rtm_pos == 0 (every 128 pixel_clk
    // cycles), and rtm_hex_hit only asserts at rtm_pos == 4..7 (32..63 pixel_clk cycles later).
    // Two pipeline stages on rtm_blk -> rtm_sel_val break the 16.27 ns combinational path into <10 ns stages
    // with zero functional change to any displayed character.
    wire [9:0] rtm_blk = cell_addr[13:4];
    wire [3:0] rtm_pos = cell_addr[3:0];

    reg [9:0] rtm_blk_q = 10'd0;
    always @(posedge pixel_clk) begin
        rtm_blk_q <= rtm_blk;
    end

    reg        rtm_blk_match;
    reg [15:0] rtm_sel_val;
    reg [3:0]  rtm_sel_at;

    wire [15:0] rtm_s1_rsdc  = {3'd0, rtm_s_s1_raw, 3'd0, rtm_s_s1_sync, 3'd0, rtm_s_s1_deb, rtm_s_s1_cnt};
    wire [15:0] rtm_s2_rsdc  = {3'd0, rtm_s_s2_raw, 3'd0, rtm_s_s2_sync, 3'd0, rtm_s_s2_deb, rtm_s_s2_cnt};
    wire [15:0] rtm_stev_val = {5'd0, rtm_s_ctrl_state, 5'd0, rtm_s_last_ev};
    wire [15:0] rtm_prpo_val = {5'd0, rtm_s_pre_state,  5'd0, rtm_s_post_state};
    wire [15:0] rtm_flrc_val = {3'd0, rtm_s_fault_lat, 1'b0, rtm_s_fault_code, 1'b0, rtm_s_rec_res, rtm_s_rec_cnt};
    wire [15:0] rtm_s1s2_cnt = {3'd0, rtm_s_s1_deb, rtm_s_s1_cnt, 3'd0, rtm_s_s2_deb, rtm_s_s2_cnt};

    always @* begin
        rtm_blk_match = 1'b1;
        rtm_sel_val   = 16'd0;
        rtm_sel_at    = RTM_C_WHITE;

        case (rtm_blk_q)
            // Header Row 5 (col 64 -> 54, col 80 -> 55)
            10'd54:  begin rtm_sel_val = rtm_stev_val;                                   rtm_sel_at = RTM_C_GREEN; end
            10'd55:  begin rtm_sel_val = rtm_s1s2_cnt;                                   rtm_sel_at = RTM_C_CYAN;  end
            // Panel A (col 16 -> blk = row*10 + 1)
            10'd181: begin rtm_sel_val = {rtm_s_last_op, rtm_s_last_dst, rtm_s_last_s1}; rtm_sel_at = RTM_C_CYAN;  end
            10'd191: begin rtm_sel_val = rtm_s_step_cnt;                                 rtm_sel_at = RTM_C_WHITE; end
            10'd201: begin rtm_sel_val = {8'd0, rtm_s_last_print};                       rtm_sel_at = RTM_C_GREEN; end
            // Panel B (col 64 -> blk = row*10 + 4)
            10'd114: begin rtm_sel_val = {8'd0, rtm_s_last_letter_op};                   rtm_sel_at = RTM_C_GREEN; end
            10'd124: begin rtm_sel_val = {8'd0, rtm_s_last_codex_op};                    rtm_sel_at = RTM_C_GREEN; end
            10'd134: begin rtm_sel_val = rtm_s_math_cnt;                                 rtm_sel_at = RTM_C_WHITE; end
            10'd144: begin rtm_sel_val = {8'd0, (rtm_s_print_cnt >= 8'd6) ? rtm_s_p5 : rtm_s_last_print}; rtm_sel_at = RTM_C_GREEN; end
            10'd154: begin rtm_sel_val = {8'd0, rtm_s_p6};                               rtm_sel_at = RTM_C_GREEN; end
            10'd164: begin rtm_sel_val = {8'd0, rtm_s_p7};                               rtm_sel_at = RTM_C_GREEN; end
            // Panel C (col 128 -> blk = row*10 + 8)
            10'd158: begin rtm_sel_val = {8'd0, rtm_s_print_cnt};                        rtm_sel_at = RTM_C_GREEN; end
            10'd168: begin rtm_sel_val = rtm_s_uart_bytes;                               rtm_sel_at = RTM_C_GREEN; end
            // Zone 6: NUI L0-L11 Layer Telemetry (col 16 -> blk = row*10 + 1, rows 28..33)
            10'd281: begin rtm_sel_val = {8'd0, rtm_s_p0};                               rtm_sel_at = RTM_C_GREEN; end
            10'd291: begin rtm_sel_val = {8'd0, rtm_s_p1};                               rtm_sel_at = RTM_C_GREEN; end
            10'd301: begin rtm_sel_val = {8'd0, rtm_s_p2};                               rtm_sel_at = RTM_C_GREEN; end
            10'd311: begin rtm_sel_val = {8'd0, rtm_s_p3};                               rtm_sel_at = RTM_C_GREEN; end
            10'd321: begin rtm_sel_val = {8'd0, rtm_s_p4};                               rtm_sel_at = RTM_C_GREEN; end
            10'd331: begin rtm_sel_val = {8'd0, rtm_s_print_cnt};                        rtm_sel_at = RTM_C_CYAN;  end
            // Zone 7A: Physical Button Control & Fault Recovery (col 128 -> blk = row*10 + 8, rows 28..34)
            10'd288: begin rtm_sel_val = rtm_s1_rsdc;                                    rtm_sel_at = rtm_s_s1_deb ? RTM_C_YELLOW : RTM_C_GREEN; end
            10'd298: begin rtm_sel_val = rtm_s2_rsdc;                                    rtm_sel_at = rtm_s_s2_deb ? RTM_C_CYAN   : RTM_C_GREEN; end
            10'd328: begin rtm_sel_val = rtm_stev_val;                                   rtm_sel_at = RTM_C_WHITE; end
            10'd338: begin rtm_sel_val = rtm_prpo_val;                                   rtm_sel_at = RTM_C_CYAN;  end
            10'd348: begin rtm_sel_val = rtm_flrc_val;                                   rtm_sel_at = rtm_s_fault_lat ? RTM_C_RED : RTM_C_GREEN; end
            // Zone 7B: Live Computation & Event Monitor (cols 112, 128 -> blk = row*10 + 7, 8, rows 39..48)
            10'd397: begin rtm_sel_val = {{(16-RTM_PCW){1'b0}}, rtm_s_boot_pc};          rtm_sel_at = RTM_C_WHITE; end
            10'd398: begin rtm_sel_val = {8'd0, rtm_s_boot_op};                          rtm_sel_at = RTM_C_CYAN;  end
            10'd407: begin rtm_sel_val = rtm_s_step_cnt;                                 rtm_sel_at = RTM_C_WHITE; end
            10'd408: begin rtm_sel_val = rtm_s_math_cnt;                                 rtm_sel_at = RTM_C_GREEN; end
            10'd417: begin rtm_sel_val = {8'd0, rtm_s_p0};                               rtm_sel_at = RTM_C_GREEN; end
            10'd418: begin rtm_sel_val = {8'd0, rtm_s_p1};                               rtm_sel_at = RTM_C_GREEN; end
            10'd427: begin rtm_sel_val = {8'd0, rtm_s_p2};                               rtm_sel_at = RTM_C_GREEN; end
            10'd428: begin rtm_sel_val = {8'd0, rtm_s_p3};                               rtm_sel_at = RTM_C_GREEN; end
            10'd437: begin rtm_sel_val = {8'd0, rtm_s_p4};                               rtm_sel_at = RTM_C_GREEN; end
            10'd438: begin rtm_sel_val = {8'd0, rtm_s_print_cnt};                        rtm_sel_at = RTM_C_CYAN;  end
            10'd447: begin rtm_sel_val = {8'd0, rtm_s_p5};                               rtm_sel_at = RTM_C_GREEN; end
            10'd448: begin rtm_sel_val = {8'd0, rtm_s_p6};                               rtm_sel_at = RTM_C_GREEN; end
            10'd457: begin rtm_sel_val = {8'd0, rtm_s_p7};                               rtm_sel_at = RTM_C_GREEN; end
            10'd458: begin rtm_sel_val = {8'd0, rtm_s_last_print};                       rtm_sel_at = RTM_C_GREEN; end
            10'd467: begin rtm_sel_val = rtm_s_uart_bytes;                               rtm_sel_at = RTM_C_CYAN;  end
            10'd468: begin rtm_sel_val = {8'd0, rtm_s_print_cnt};                        rtm_sel_at = RTM_C_GREEN; end
            10'd477: begin rtm_sel_val = {8'd0, snap_flags};                             rtm_sel_at = RTM_C_WHITE; end
            10'd487: begin rtm_sel_val = rtm_s_cdc_frames;                               rtm_sel_at = RTM_C_WHITE; end
            // Footer Row 84 (col 64 -> blk = 844)
            10'd844: begin rtm_sel_val = rtm_s_cdc_frames;                               rtm_sel_at = RTM_C_GREEN; end
            default: begin rtm_blk_match = 1'b0;                                         end
        endcase
    end

    reg        rtm_blk_match_q = 1'b0;
    reg [15:0] rtm_sel_val_q   = 16'd0;
    reg [3:0]  rtm_sel_at_q    = 4'd0;
    always @(posedge pixel_clk) begin
        rtm_blk_match_q <= rtm_blk_match;
        rtm_sel_val_q   <= rtm_sel_val;
        rtm_sel_at_q    <= rtm_sel_at;
    end

    reg [3:0] rtm_nib;
    always @* begin
        case (rtm_pos[1:0])
            2'd0: rtm_nib = rtm_sel_val_q[15:12];
            2'd1: rtm_nib = rtm_sel_val_q[11:8];
            2'd2: rtm_nib = rtm_sel_val_q[7:4];
            2'd3: rtm_nib = rtm_sel_val_q[3:0];
        endcase
    end

    reg [7:0] rtm_hex_ch;
    always @* begin
        case (rtm_nib)
            4'h0: rtm_hex_ch = "0"; 4'h1: rtm_hex_ch = "1"; 4'h2: rtm_hex_ch = "2"; 4'h3: rtm_hex_ch = "3";
            4'h4: rtm_hex_ch = "4"; 4'h5: rtm_hex_ch = "5"; 4'h6: rtm_hex_ch = "6"; 4'h7: rtm_hex_ch = "7";
            4'h8: rtm_hex_ch = "8"; 4'h9: rtm_hex_ch = "9"; 4'hA: rtm_hex_ch = "A"; 4'hB: rtm_hex_ch = "B";
            4'hC: rtm_hex_ch = "C"; 4'hD: rtm_hex_ch = "D"; 4'hE: rtm_hex_ch = "E"; default: rtm_hex_ch = "F";
        endcase
    end

    // Override Panel A STATE (blk 111) when ctrl_state != CTRL_RUNNING so S1/S2 states
    // ("STOPPED", "PAUSED ", "RESET  ", "FAULT  ", "FLT LAT", "READY  ") display directly!
    wire rtm_state_override = snap_valid && (rtm_blk == 10'd111) && (rtm_s_ctrl_state != CTRL_RUNNING);
    reg [7:0] rtm_state_ch;
    reg [3:0] rtm_state_at;
    always @* begin
        rtm_state_ch = " ";
        case (rtm_s_ctrl_state)
            CTRL_STOPPED: begin
                rtm_state_at = RTM_C_YELLOW;
                case (rtm_pos)
                    4'd0: rtm_state_ch = "S"; 4'd1: rtm_state_ch = "T"; 4'd2: rtm_state_ch = "O";
                    4'd3: rtm_state_ch = "P"; 4'd4: rtm_state_ch = "P"; 4'd5: rtm_state_ch = "E";
                    4'd6: rtm_state_ch = "D"; default: rtm_state_ch = " ";
                endcase
            end
            CTRL_PAUSED: begin
                rtm_state_at = RTM_C_YELLOW;
                case (rtm_pos)
                    4'd0: rtm_state_ch = "P"; 4'd1: rtm_state_ch = "A"; 4'd2: rtm_state_ch = "U";
                    4'd3: rtm_state_ch = "S"; 4'd4: rtm_state_ch = "E"; 4'd5: rtm_state_ch = "D";
                    default: rtm_state_ch = " ";
                endcase
            end
            CTRL_RESETTING: begin
                rtm_state_at = RTM_C_CYAN;
                case (rtm_pos)
                    4'd0: rtm_state_ch = "R"; 4'd1: rtm_state_ch = "E"; 4'd2: rtm_state_ch = "S";
                    4'd3: rtm_state_ch = "E"; 4'd4: rtm_state_ch = "T"; default: rtm_state_ch = " ";
                endcase
            end
            CTRL_FAULT: begin
                rtm_state_at = RTM_C_RED;
                case (rtm_pos)
                    4'd0: rtm_state_ch = "F"; 4'd1: rtm_state_ch = "A"; 4'd2: rtm_state_ch = "U";
                    4'd3: rtm_state_ch = "L"; 4'd4: rtm_state_ch = "T"; default: rtm_state_ch = " ";
                endcase
            end
            CTRL_FAULT_LATCHED: begin
                rtm_state_at = RTM_C_RED;
                case (rtm_pos)
                    4'd0: rtm_state_ch = "F"; 4'd1: rtm_state_ch = "L"; 4'd2: rtm_state_ch = "T";
                    4'd3: rtm_state_ch = " "; 4'd4: rtm_state_ch = "L"; 4'd5: rtm_state_ch = "A";
                    4'd6: rtm_state_ch = "T"; default: rtm_state_ch = " ";
                endcase
            end
            default: begin // CTRL_READY
                rtm_state_at = RTM_C_GREEN;
                case (rtm_pos)
                    4'd0: rtm_state_ch = "R"; 4'd1: rtm_state_ch = "E"; 4'd2: rtm_state_ch = "A";
                    4'd3: rtm_state_ch = "D"; 4'd4: rtm_state_ch = "Y"; default: rtm_state_ch = " ";
                endcase
            end
        endcase
    end

    wire       rtm_hex_hit = (page == 4'd0) && snap_valid && rtm_blk_match_q && (rtm_pos[3:2] == 2'b01);
    wire       rtm_hit     = rtm_state_override | rtm_hex_hit;
    wire [7:0] rtm_ch      = rtm_state_override ? rtm_state_ch : rtm_hex_ch;
    wire [3:0] rtm_at      = rtm_state_override ? rtm_state_at : rtm_sel_at_q;

    // rtm_state_override takes priority over u_comp on BLK_STATE when STOPPED/PAUSED/RESET/READY/FAULT
    wire       any_hit = comp_hit | rtm_hit;
    wire [7:0] any_ch  = rtm_state_override ? rtm_state_ch : (comp_hit ? comp_ch : rtm_ch);
    wire [3:0] any_at  = rtm_state_override ? rtm_state_at : (comp_hit ? comp_at : rtm_at);

    reg        hit_d;
    reg [7:0]  ch_d;
    reg [3:0]  at_d;
    reg        rom_valid_d;
    reg        rom_lower_d;
    always @(posedge pixel_clk or negedge video_rst_n) begin
        if (!video_rst_n) begin
            hit_d <= 1'b0; ch_d <= 8'h20; at_d <= 4'd0;
            rom_valid_d <= 1'b0; rom_lower_d <= 1'b0;
        end else begin
            hit_d <= any_hit; ch_d <= any_ch; at_d <= any_at;
            rom_valid_d <= rom_valid; rom_lower_d <= rom_lower;
        end
    end

    wire [11:0] selected_rom = rom_lower_d ? layout_lower_data : layout_upper_data;
    wire [11:0] rom_cell     = rom_valid_d ? selected_rom : 12'h020;
    wire [15:0] cell_data    = hit_d ? {4'd0, at_d, ch_d}
                                     : {4'd0, rom_cell};

    wire [6:0] font_glyph;
    wire [2:0] font_row;
    wire [7:0] font_bits;

    hcpu_font_rom #(.FONT_HEX(FONT_HEX)) u_font (
        .clk(pixel_clk), .glyph(font_glyph), .row(font_row), .bits(font_bits)
    );

    wire [7:0] text_red, text_green, text_blue;

    hcpu_text_render #(
        .COLS(160), .ROWS(90), .H_TOTAL(1650), .V_TOTAL(750)
    ) u_render (
        .clk(pixel_clk), .rst_n(video_rst_n),
        .h_count(h_count), .v_count(v_count), .de(de),
        .cell_addr(cell_addr), .cell_data(cell_data),
        .font_glyph(font_glyph), .font_row(font_row), .font_bits(font_bits),
        .red(text_red), .green(text_green), .blue(text_blue)
    );

    // ========================================================================
    // NUI HOLOGRAPHIC BRAIN & ORBITAL CORE BSRAM ENGINE (256x256 @ Center)
    //   Screen window: x = 464..719 (cols 58..89), y = 208..431 (rows 26..53)
    //   ROM: 8,192 x 8-bit (`hcpu_nui_holo.hex`), 2 4-bit pixels per byte
    //   2-stage pipeline (h_la2 = h_count + 2 -> BSRAM -> holo_rgb_q)
    // ========================================================================
    reg [7:0] nui_holo_rom [0:8191];
    initial if (HOLO_HEX != "") $readmemh(HOLO_HEX, nui_holo_rom);

    wire [11:0] h_la2     = h_count + 12'd2;
    wire [11:0] rel_x_nx  = h_la2 - 12'd464;
    wire [11:0] rel_y_nx  = v_count - 12'd208;
    wire [12:0] holo_addr = {rel_y_nx[7:1], rel_x_nx[7:2]};

    reg [7:0] holo_byte_q;
    reg       holo_x_odd_q;
    reg       in_holo_box_q;
    always @(posedge pixel_clk) begin
        holo_byte_q   <= nui_holo_rom[holo_addr];
        holo_x_odd_q  <= rel_x_nx[1];
        in_holo_box_q <= (h_la2 >= 12'd464) && (h_la2 < 12'd720)
                      && (v_count >= 12'd208) && (v_count < 12'd432);
    end

    wire [3:0] holo_nib_raw = holo_x_odd_q ? holo_byte_q[3:0] : holo_byte_q[7:4];

    // Clock-driven breathing pulse (only advances while CPU is actively running, never random)
    wire       holo_pulse_hi = (rtm_s_ctrl_state == CTRL_RUNNING) && rtm_s_cdc_frames[4];
    wire       holo_is_fault = (rtm_s_ctrl_state == CTRL_FAULT) || (rtm_s_ctrl_state == CTRL_FAULT_LATCHED) || rtm_s_fault_lat;
    wire       l0_active     = (rtm_s_math_cnt != 16'd0) || (rtm_s_print_cnt != 8'd0);

    reg [23:0] holo_rgb;
    always @* begin
        case (holo_nib_raw)
            4'd1:  holo_rgb = 24'h0a1a3a; // Deep Holographic Indigo aura
            4'd2:  holo_rgb = holo_pulse_hi ? 24'h143e8c : 24'h103478; // Dark Electric Blue brain mesh
            4'd3:  holo_rgb = holo_is_fault ? 24'h902838 : (holo_pulse_hi ? 24'h2078f0 : 24'h1864d8); // Electric Blue lobe filament
            4'd4:  holo_rgb = holo_is_fault ? 24'hd04050 : (holo_pulse_hi ? 24'h38c0ff : 24'h20a8f8); // Bright Cyan-Blue gyri ridge
            4'd5:  holo_rgb = holo_is_fault ? 24'hff5868 : 24'h50f0ff; // Neon Cyan holographic rim & beam
            4'd6:  holo_rgb = 24'hc8fcff; // White-Cyan synaptic node core
            4'd7:  holo_rgb = 24'h0e6838; // Deep Emerald Green bevel & orbit shadow
            4'd8:  holo_rgb = l0_active ? 24'h28d870 : 24'h1cb860; // Emerald Green orbital ring
            4'd9:  holo_rgb = 24'h48ff98; // Bright Neon Emerald circuit pad
            4'd10: holo_rgb = 24'h885810; // Deep Bronze-Gold orbit shadow
            4'd11: holo_rgb = l0_active ? 24'hf0b030 : 24'hd89820; // Metallic Gold orbital ring
            4'd12: holo_rgb = 24'hffe058; // Bright Gold orbital spark
            4'd13: holo_rgb = 24'h788898; // Brushed Chrome Steel crease
            4'd14: holo_rgb = 24'hc0d0e0; // Chrome Silver 'NUI' body
            4'd15: holo_rgb = 24'hf4f8ff; // Pure Specular Chrome White 'NUI' highlight
            default: holo_rgb = 24'h060c16;
        endcase
    end

    reg [23:0] holo_rgb_q   = 24'h060c16;
    reg        holo_valid_q = 1'b0;
    always @(posedge pixel_clk) begin
        holo_rgb_q   <= holo_rgb;
        holo_valid_q <= in_holo_box_q && (holo_nib_raw != 4'd0);
    end

    wire text_is_bg = (text_red == 8'h06) && (text_green == 8'h0c) && (text_blue == 8'h16);
    wire show_holo  = holo_valid_q && text_is_bg;

    wire [7:0] red   = show_holo ? holo_rgb_q[23:16] : text_red;
    wire [7:0] green = show_holo ? holo_rgb_q[15:8]  : text_green;
    wire [7:0] blue  = show_holo ? holo_rgb_q[7:0]   : text_blue;

    reg [7:0] red_dvi   = 8'h00;
    reg [7:0] green_dvi = 8'h00;
    reg [7:0] blue_dvi  = 8'h00;
    reg       de_dvi    = 1'b0;
    reg       hsync_dvi = 1'b0;
    reg       vsync_dvi = 1'b0;

    always @(posedge pixel_clk or negedge video_rst_n) begin
        if (!video_rst_n) begin
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

    DVI_TX_Top u_dvi_tx (
        .I_rst_n(~oser_rst), .I_serial_clk(serial_clk), .I_rgb_clk(pixel_clk),
        .I_rgb_vs(vsync_dvi), .I_rgb_hs(hsync_dvi), .I_rgb_de(de_dvi),
        .I_rgb_r(red_dvi), .I_rgb_g(green_dvi), .I_rgb_b(blue_dvi),
        .tmds_clk_serial(tmds_clk_serial), .tmds_data_serial(tmds_data_serial)
    );

    assign tmds_clk_p  = tmds_clk_serial;
    assign tmds_data_p = tmds_data_serial;

    assign uart_txd = hcpu_uart_txd;
    assign led = {hcpu_led[5], (ctrl_state == CTRL_STOPPED || ctrl_state == CTRL_PAUSED), hcpu_led[3:1], ~pll_locked};
endmodule
