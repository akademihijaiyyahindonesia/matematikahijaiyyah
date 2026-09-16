// cosmictera_display_top.v — the display node, and nothing else on the die.
//
// M5.3a, owner's decision 15 September 2026. Two attempts put the dashboard
// in the same placement as the CPU and nextpnr refused both:
//
//     control, HCPU + SDIO + HDMI     15,933 LUT4   placed, routed, 0/0
//     M5.2A, RAM + painter            16,882 LUT4   refused
//     M5.2B, ROM + compositor         16,849 LUT4   refused
//
// Two different display architectures, thirty-three LUT4 apart, both refused.
// Differential synthesis had already measured the whole display stack at 571
// LUT of synthesis against a gap of 916 post-route: the thing that had to be
// removed was larger than everything there was to remove. So the display
// stops sharing a die with the CPU.
//
// ── what this node can honestly claim ───────────────────────────
// Four things, and they are true by the fact that the screen is readable at
// all: the video timing, the renderer, the font ROM and the page key. If the
// characters are on the monitor, those four work -- there is no way to draw
// the words READY without them.
//
// Everything else says NOT INSTRUMENTED, because on this node there is no CPU
// to ask. `snap_valid` is tied low and hcpu_compositor.v turns all six live
// fields into NOT INSTRUMENTED when it is: a display node that printed PC as
// 0X000 would be printing a value with nothing behind it.
//
// ── the link is absent, not faked ───────────────────────────────
// M5.3b is BLOCKED on a second board. openFPGALoader sees one. Sequential
// rack slots -- the thing rtl/scripts/rack.py means by "rack" -- reconfigure
// the same fabric one at a time, so a compute slot and a display slot can
// never be alive together, and calling that live telemetry would be a lie
// about the machine's shape. The screen says NOT CONNECTED and means it.
//
// ── pins ────────────────────────────────────────────────────────
// hcpu_hdmi.cst, unchanged and shared. It also names uart, led and the card;
// this node has no such ports and nextpnr says `Cell ... not found` as Info
// and carries on, exactly as it does for Ka'bah against hcpu_gowin.cst. One
// constraint file, one truth about where the pins are.

`include "hcpu_pkg.vh"

module cosmictera_display_top #(
    parameter FONT_HEX   = "../../hcpu_font8x8.hex",
    parameter LAYOUT_HEX = "../../hcpu_display.hex"
) (
    input  wire       clk_27m,
    input  wire       btn_rst_n,
    input  wire       mode_key,
    output wire       tmds_clk_p,
    output wire [2:0] tmds_data_p
);

    wire serial_clk;
    wire pixel_clk;
    wire pll_locked;

    // Not gated on btn_rst_n: pin 87 is MODE1 and this board holds it low.
    // Gating on its level pinned the video reset at 0 and the pixel clock was
    // never generated at all -- the monitor saw no signal rather than a bad
    // picture. Measured on hcpu_hdmi_top.v and kept here for the same reason.
    wire video_rst_n = pll_locked;

    TMDS_rPLL u_tmds_rpll (.clkin(clk_27m), .clkout(serial_clk), .lock(pll_locked));
    CLKDIV u_clkdiv (
        .RESETN(video_rst_n), .HCLKIN(serial_clk), .CLKOUT(pixel_clk), .CALIB(1'b1)
    );
    defparam u_clkdiv.DIV_MODE = "5";
    defparam u_clkdiv.GSREN = "false";

    wire hsync, vsync, de;
    wire [11:0] x, y, h_count, v_count;
    wire        frame_tick;

    hcpu_video_timing #(
        .H_ACTIVE(1280), .H_FRONT(110), .H_SYNC(40), .H_BACK(220),
        .V_ACTIVE(720), .V_FRONT(5), .V_SYNC(5), .V_BACK(20),
        .HSYNC_POL(1'b1), .VSYNC_POL(1'b1)
    ) u_timing (
        .pixel_clk(pixel_clk), .rst_n(video_rst_n), .hsync(hsync), .vsync(vsync),
        .de(de), .x(x), .y(y), .frame_tick(frame_tick),
        .h_count_o(h_count), .v_count_o(v_count)
    );

    wire [3:0] page;

    hcpu_page_key #(
        .DEBOUNCE(750_000), .LONG(74_250_000), .PAGES(9)
    ) u_page (
        .clk(pixel_clk), .rst_n(video_rst_n), .key_n(mode_key), .page(page)
    );

    wire [13:0] cell_addr;
    wire [11:0] layout_data;

    hcpu_layout_rom #(.LAYOUT_HEX(LAYOUT_HEX)) u_layout (
        .clk(pixel_clk), .addr(cell_addr), .data(layout_data)
    );

    // Tied off, and that is the honest wiring of a node with no CPU. Every
    // live field becomes NOT INSTRUMENTED because snap_valid is low; the page
    // digit and the banner still work, because those are this node's own
    // state rather than someone else's.
    wire       comp_hit;
    wire [7:0] comp_ch;
    wire [3:0] comp_at;

    hcpu_compositor #(.PCW(`CODE_ADDR_W)) u_comp (
        .cell_addr(cell_addr), .page(page),
        .snap_pc({`CODE_ADDR_W{1'b0}}), .snap_instr({`ILEN{1'b0}}),
        .snap_halted(1'b0), .snap_guard(1'b0),
        .snap_cycles(32'd0), .snap_flags(8'd0), .snap_valid(1'b0),
        .hit(comp_hit), .ch(comp_ch), .at(comp_at)
    );

    reg        hit_d;
    reg [7:0]  ch_d;
    reg [3:0]  at_d;
    always @(posedge pixel_clk or negedge video_rst_n) begin
        if (!video_rst_n) begin
            hit_d <= 1'b0; ch_d <= 8'h20; at_d <= 4'd0;
        end else begin
            hit_d <= comp_hit; ch_d <= comp_ch; at_d <= comp_at;
        end
    end

    wire [15:0] cell_data = hit_d ? {4'd0, at_d, ch_d} : {4'd0, layout_data};

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

    wire tmds_clk_serial;
    wire [2:0] tmds_data_serial;

    DVI_TX_Top u_dvi_tx (
        .I_rst_n(video_rst_n), .I_serial_clk(serial_clk), .I_rgb_clk(pixel_clk),
        .I_rgb_vs(vsync), .I_rgb_hs(hsync), .I_rgb_de(de),
        .I_rgb_r(red), .I_rgb_g(green), .I_rgb_b(blue),
        .tmds_clk_serial(tmds_clk_serial), .tmds_data_serial(tmds_data_serial)
    );

    // No TLVDS_TBUF: yosys inserts its own OBUF on every top-level output, so
    // the netlist becomes TLVDS_TBUF -> OBUF -> pad, which is not a thing, and
    // nextpnr drops all four. The pairs are made differential by the .cst
    // instead -- one IOB per lane, LVCMOS33D, both pads in one IO_LOC. That is
    // how the Tang Nano boards drive TMDS, and hcpu_hdmi_top.v records the
    // measurement that settled it.
    assign tmds_clk_p  = tmds_clk_serial;
    assign tmds_data_p = tmds_data_serial;

endmodule
