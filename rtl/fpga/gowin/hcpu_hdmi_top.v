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
//     LUT4      14,164 / 20,736   68%
//     ALU        2,678 / 15,552   17%
//     DFF        5,520 / 15,552   35%
//     BSRAM         24 /     46   52%
//     MULT9X9       14 /     96   14%
//     MULT36X36      1 /     12    8%
//     Fmax      101.13 MHz  u_hcpu.clk_27m (PASS at the 12.00 MHz constraint)
//                97.51 MHz  pixel_clk      (PASS at the 12.00 MHz constraint)
//     Bitstream  7,261,470 bytes, sha256 a416ada780a50dc8262f4effc8cad61eaff8af4787fadb5f6211acca5f5b413f
//
// RTL FINGERPRINT: abfe1f5d03a5c56d9c9b29b98a57eff81595db0ba88873f180b0c36e29fab116
//
`include "hcpu_pkg.vh"

module hcpu_hdmi_top #(
    // ── where the two memory images live, stated once per build ──
    // NOT copied next to this file. $readmemh resolves against the working
    // directory, and the two builds run from different ones -- so the path is
    // a parameter and each build says where the single copy is, rather than
    // each build getting a copy of its own. Two files that must stay
    // byte-identical are two files that will not.
    parameter FONT_HEX = "../../hcpu_font8x8.hex",
    parameter DASH_HEX = "../../hcpu_dashboard.hex"
) (
    input wire        clk_27m,
    input wire        btn_rst_n,
    input wire        mode_key,
    input wire        uart_rxd,
    output wire       uart_txd,
    output wire [5:0] led,
    // Only the P half is a port. The N half is not driven by logic at all:
    // LVCMOS33D in the .cst makes one IOB drive both pads of the pair, which
    // is how the Tang Nano boards do TMDS. See the note above the assigns.
    output wire       tmds_clk_p,
    output wire [2:0] tmds_data_p,

    // ── the card, reaching this slot for the first time ─────────
    // hcpu_gowin_top has carried an SD controller since H-ISA v1.2, and this
    // wrapper instantiated it with the pins left dangling: the controller was
    // present and could never see a card. The owner connected them on 15
    // September 2026 so the monitor can report storage that is actually
    // there. hcpu_hdmi.cst has to name these six pins or nextpnr places them
    // wherever it likes -- which is the same as not having them.
    output wire       sd_clk,
    inout  wire       sd_cmd,
    inout  wire [3:0] sd_dat
);
    wire serial_clk;
    wire pixel_clk;
    wire pll_locked;

    // ── Staged reset sequencer (aligned with Unified SoC Stage 1.5) ──
    // 1. Synchronize raw rPLL lock into clk_27m and qualify for 2.0 ms
    //    (54,000 cycles at 27.000 MHz).
    // 2. Release clkdiv_rst_n (CLKDIV.RESETN) first so pixel_clk (74.25 MHz)
    //    oscillates cleanly before OSER10 or video timing leave reset.
    // 3. Wait 16 reference clocks, then release oser_rst synchronously in
    //    pixel_clk for DVI_TX_Top.
    // 4. Wait 32 reference clocks, then release video_rst_n synchronously in
    //    pixel_clk for video timing and the M5.2B display pipeline.
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

    wire hcpu_uart_txd;
    wire [5:0] hcpu_led;

    wire [`CODE_ADDR_W-1:0] tele_pc;
    wire [`ILEN-1:0]        tele_instr;
    wire                    tele_halted;
    wire                    tele_guard;
    wire [31:0]             tele_cycles;
    wire [7:0]              tele_flags;

    // The CORE, not the board slot. hcpu_gowin_top is a pin-level wrapper and
    // has no telemetry ports -- it cannot have any, because a top level must
    // find a pin for every output and this sideband is eighty-four bits wide.
    // hcpu_gowin_top.v carries the measurement that forced the split.
    // USE_DSP=1 maps the 14-lane 8x8 MAC in hcpu_codex_alu and 32x32 multiply
    // in hcpu_mul to GW2AR-18C hard MULT9X9/MULT36X36 blocks, freeing the
    // LUT4 headroom required for the M5.2B display pipeline to place and route.
    hcpu_gowin_core #(.USE_DSP(1)) u_hcpu (
        .clk_27m(clk_27m), .btn_rst_n(btn_rst_n), .uart_rxd(uart_rxd),
        .uart_txd(hcpu_uart_txd), .led(hcpu_led),
        .sd_clk(sd_clk), .sd_cmd(sd_cmd), .sd_dat(sd_dat),
        .tele_pc(tele_pc), .tele_instr(tele_instr),
        .tele_halted(tele_halted), .tele_guard(tele_guard),
        .tele_cycles(tele_cycles), .tele_flags(tele_flags)
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

    // ── the display pipeline ────────────────────────────────────
    // What stood here was a colour generator: a border, a grid, and three of
    // the CPU's LED bits deciding the grid's colour. It proved the TMDS path
    // and it could never show a number. This is the same path carrying
    // characters instead.
    //
    //   text RAM  ──►  font ROM  ──►  renderer  ──►  RGB
    //      ▲
    //   painter  ◄──  telemetry snapshot  ◄──  the CPU, at its own clock
    //
    // The card is wired to the CPU above but its CONTROLLER STATE is not on
    // this screen: card_ready, busy, the last command and the CRC results all
    // live inside hcpu_sdio.v and have no port out of it. The device panel
    // says NOT INSTRUMENTED for SDIO, and it will keep saying so until those
    // wires exist.
    wire [3:0] page;

    hcpu_page_key #(
        .DEBOUNCE(750_000), .LONG(74_250_000), .PAGES(9)
    ) u_page (
        .clk(pixel_clk), .rst_n(video_rst_n), .key_n(mode_key), .page(page)
    );

    // One snapshot per frame, asked for at the top of it, so every field on
    // the screen belongs to the same instant. The painter used to raise
    // this; with the painter gone the frame tick raises it directly.
    wire        tele_sample = frame_tick;
    wire [`CODE_ADDR_W-1:0] snap_pc;
    wire [`ILEN-1:0]        snap_instr;
    wire                    snap_halted, snap_guard, snap_valid;
    wire [31:0]             snap_cycles;
    wire [7:0]              snap_flags;

    hcpu_telemetry #(.PCW(`CODE_ADDR_W)) u_tele (
        .cpu_clk(clk_27m), .cpu_rst_n(video_rst_n),
        .pc(tele_pc), .instr(tele_instr), .halted(tele_halted),
        .guard(tele_guard), .cycles(tele_cycles), .flags(tele_flags),
        .vid_clk(pixel_clk), .vid_rst_n(video_rst_n), .sample(tele_sample),
        .snap_pc(snap_pc), .snap_instr(snap_instr), .snap_halted(snap_halted),
        .snap_guard(snap_guard), .snap_cycles(snap_cycles),
        .snap_flags(snap_flags), .snap_valid(snap_valid)
    );

    // ── layout ROM + compositor, in place of RAM + painter ──────
    // The character for a cell is decided as the beam reaches it: the ROM
    // holds everything fixed, the compositor overrides the eight live fields
    // from the telemetry snapshot, and nothing is stored between frames.
    // M5.2A wrote 128 cells a frame into a 16,384 x 16 RAM and read them back;
    // that design placed at 16,882 LUT4 and nextpnr refused it, against a
    // control of 15,933 that routes with zero violations.
    wire [13:0] cell_addr;
    wire [11:0] layout_data;

    // 14-bit screen address (0..14,399) -> 13-bit layout ROM (0..8,191).
    // Rows 0..41 (0..6,719) map directly; footer rows 84..89 (13,440..14,399)
    // fold to 6,720..7,679; rows 42..83 (6,720..13,439, including 8,191 and
    // 8,192 where cell_addr[13] flips) are blanked so cell_addr[13] is never
    // truncated into 0..6,207.
    localparam [13:0] ROM_DIRECT_END = 14'd6720;
    localparam [13:0] ROM_FOOT_FIRST = 14'd13440;
    localparam [13:0] ROM_SCREEN_END = 14'd14400;
    localparam [13:0] ROM_FOOT_SHIFT = 14'd6720;

    wire        rom_direct = (cell_addr < ROM_DIRECT_END);
    wire        rom_footer = (cell_addr >= ROM_FOOT_FIRST) && (cell_addr < ROM_SCREEN_END);
    wire        rom_valid  = rom_direct | rom_footer;
    wire [13:0] rom_folded = cell_addr - ROM_FOOT_SHIFT;
    wire [12:0] rom_addr   = rom_direct ? cell_addr[12:0]
                           : rom_footer ? rom_folded[12:0]
                           : 13'd7680;

    hcpu_layout_rom #(.LAYOUT_HEX(DASH_HEX)) u_layout (
        .clk(pixel_clk), .addr(rom_addr), .data(layout_data)
    );

    wire       comp_hit;
    wire [7:0] comp_ch;
    wire [3:0] comp_at;

    hcpu_compositor #(.PCW(`CODE_ADDR_W)) u_comp (
        .cell_addr(cell_addr), .page(page),
        .snap_pc(snap_pc), .snap_instr(snap_instr), .snap_halted(snap_halted),
        .snap_guard(snap_guard), .snap_cycles(snap_cycles),
        .snap_flags(snap_flags), .snap_valid(snap_valid),
        .hit(comp_hit), .ch(comp_ch), .at(comp_at)
    );

    // The compositor is combinational from cell_addr, and the ROM is one
    // cycle behind it, so the override is registered to meet it. Both then
    // arrive together at the renderer's font-address stage.
    reg        hit_d;
    reg [7:0]  ch_d;
    reg [3:0]  at_d;
    reg        rom_valid_d;
    always @(posedge pixel_clk or negedge video_rst_n) begin
        if (!video_rst_n) begin
            hit_d <= 1'b0; ch_d <= 8'h20; at_d <= 4'd0; rom_valid_d <= 1'b0;
        end else begin
            hit_d <= comp_hit; ch_d <= comp_ch; at_d <= comp_at; rom_valid_d <= rom_valid;
        end
    end

    wire [11:0] rom_cell  = rom_valid_d ? layout_data : 12'h020;
    wire [15:0] cell_data = hit_d ? {4'd0, at_d, ch_d}
                                  : {4'd0, rom_cell};

    wire [6:0] font_glyph;
    wire [2:0] font_row;
    wire [7:0] font_bits;

    hcpu_font_rom #(.FONT_HEX(FONT_HEX)) u_font (
        .clk(pixel_clk), .glyph(font_glyph), .row(font_row), .bits(font_bits)
    );

    wire [7:0] red, green, blue;

    hcpu_text_render #(
        .COLS(160), .ROWS(90), .H_TOTAL(1650), .V_TOTAL(750)
    ) u_render (
        .clk(pixel_clk), .rst_n(video_rst_n),
        .h_count(h_count), .v_count(v_count), .de(de),
        .cell_addr(cell_addr), .cell_data(cell_data),
        .font_glyph(font_glyph), .font_row(font_row), .font_bits(font_bits),
        .red(red), .green(green), .blue(blue)
    );

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

    // No TLVDS_TBUF here, and the board is what settled it. Instantiating one
    // per lane looked right and did not survive: yosys still inserts its own
    // OBUF on every top-level output, so the netlist became
    // TLVDS_TBUF -> OBUF -> pad, which is not a thing -- TLVDS_TBUF *is* the
    // pad buffer. nextpnr then dropped all four TLVDS_TBUF cells and left
    // eight plain single-ended OBUFs driving pins 33..40. Measured in
    // hdmi_pnr.json: zero TLVDS cells placed. The monitor saw no TMDS at all,
    // and OEN polarity never entered into it.
    //
    // The pairs are made differential by the constraint instead: one IOB per
    // lane, IO_TYPE=LVCMOS33D, with both pads named in a single IO_LOC
    // ("33,34"). That is how the Tang Nano boards drive TMDS -- pseudo
    // differential from a pair of LVCMOS33 drivers, not true LVDS -- so the
    // N half needs no logic and no port.
    assign tmds_clk_p  = tmds_clk_serial;
    assign tmds_data_p = tmds_data_serial;

    assign uart_txd = hcpu_uart_txd;
    // `mode` is gone: the button drives the page counter now, and the page
    // is shown on the screen rather than on an LED.
    assign led = {hcpu_led[5], page[0], hcpu_led[3:1], ~pll_locked};
endmodule