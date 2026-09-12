// HCPU HDMI wrapper for Tang Nano 20K.
// The HDMI transport uses the board vendor's generated DVI TX IP.
//
// ── MEASURED, 12 September 2026, after the codex block landed ────────────
//
// `make PROGRAM=../../programs/loader.hasm hdmi_bitstream` -- yosys 0.68
// (-nodsp) -> nextpnr-himbaechel 0.11.1 -> gowin_pack, GW2AR-LV18QN88C8/I7,
// loader baked in. Re-run because CMOV, CZERO, CEQ, CRHO, CU and CMOD4
// changed hcpu_pkg.vh, hcpu_codex_alu.v, hcpu_decode.v, hcpu_execute.v,
// hcpu_guard.v and hcpu_top.v.
//
//     IOB           15 /    384    3%
//     LUT4      15,126 / 20,736   72%
//     DFF        4,551 / 15,552   29%
//     BSRAM         17 /     46   36%
//     Fmax       70.80 MHz  u_hcpu.clk_27m (PASS at the 12.00 MHz constraint)
//               549.15 MHz  pixel_clk
//     Bitstream  7,261,470 bytes, gowin_pack exits 0
//
// +413 LUT4 and +0 DFF against this slot's previous 14,713 / 4,551. The six
// opcodes cost almost nothing -- CMOV and CZERO are muxes, CEQ a comparator,
// CU and CRHO are read out of the guard that already computes them, CMOD4 is
// a two-bit slice. DFF not moving at all is the check on that: none of the six
// adds state. The bare hcpu_gowin_top slot measured +483 for the same six.
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
// FLASHED AND RUN, 12 September 2026, over the wire through the baked loader:
//
//     test_codex    8 0 0 1 1 0 1 5   the six, matching the interpreter
//     test_cset     5 6 2 0           CSET still correct on this RTL
//     test_hfs      1 1 1 2 1         HFS write, clobber, read, guard
//     e3_sweep28    28 Theta values   identical to MASTER_TABLE
//
// e3_sweep28 was re-run precisely BECAUSE the RTL changed: the sealed ROM's
// 28 values still match, so the six new opcodes moved nothing on the old path.
//
// RTL FINGERPRINT: 46e4bc9f8888b3fc31d0a022b8beeb7d4bf91d9ecd671886509cc353185fd411
//
`include "hcpu_pkg.vh"

module hcpu_hdmi_top (
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
    output wire [2:0] tmds_data_p
);
    wire serial_clk;
    wire pixel_clk;
    wire pll_locked;
    // Not btn_rst_n & pll_locked. btn_rst_n is pin 87 = MODE1, which this
    // board holds low -- measured, it is what deadlocked the CPU before
    // hcpu_gowin_top.v's reset was made edge-sensitive. Gating on its level
    // pinned video_rst_n at 0, and because it also gates CLKDIV.RESETN below,
    // the pixel clock was never generated at all: the monitor saw no signal
    // rather than a bad picture. PLL lock is the condition that actually
    // matters here; the button's reset job belongs to the CPU, which now
    // handles it internally.
    wire video_rst_n = pll_locked;
    wire hcpu_uart_txd;
    wire [5:0] hcpu_led;

    hcpu_gowin_top u_hcpu (
        .clk_27m(clk_27m), .btn_rst_n(btn_rst_n), .uart_rxd(uart_rxd),
        .uart_txd(hcpu_uart_txd), .led(hcpu_led)
    );

    TMDS_rPLL u_tmds_rpll (.clkin(clk_27m), .clkout(serial_clk), .lock(pll_locked));
    CLKDIV u_clkdiv (
        .RESETN(video_rst_n), .HCLKIN(serial_clk), .CLKOUT(pixel_clk), .CALIB(1'b1)
    );
    defparam u_clkdiv.DIV_MODE = "5";
    defparam u_clkdiv.GSREN = "false";

    wire hsync;
    wire vsync;
    wire de;
    wire [11:0] x;
    wire [11:0] y;
    wire tmds_clk_serial;
    wire [2:0] tmds_data_serial;

    hcpu_video_timing #(
        .H_ACTIVE(1280), .H_FRONT(110), .H_SYNC(40), .H_BACK(220),
        .V_ACTIVE(720), .V_FRONT(5), .V_SYNC(5), .V_BACK(20),
        .HSYNC_POL(1'b1), .VSYNC_POL(1'b1)
    ) u_timing (
        .pixel_clk(pixel_clk), .rst_n(video_rst_n), .hsync(hsync), .vsync(vsync),
        .de(de), .x(x), .y(y), .frame_tick()
    );

    reg mode;
    reg mode_key_d;
    always @(posedge pixel_clk or negedge video_rst_n) begin
        if (!video_rst_n) begin
            mode <= 1'b0;
            mode_key_d <= 1'b1;
        end else begin
            mode_key_d <= mode_key;
            if (mode_key_d && !mode_key)
                mode <= ~mode;
        end
    end

    reg [7:0] red;
    reg [7:0] green;
    reg [7:0] blue;
    always @* begin
        red = 8'h08;
        green = 8'h10;
        blue = 8'h18;
        if (de) begin
            if ((y < 12'd96) || (x < 12'd24) || (x >= 12'd1256)) begin
                red = mode ? 8'h10 : 8'h00;
                green = mode ? 8'h70 : 8'h58;
                blue = mode ? 8'hb0 : 8'h90;
            end else if ((x[6:4] == 0) || (y[5:3] == 0)) begin
                red = hcpu_led[0] ? 8'h60 : 8'h20;
                green = hcpu_led[1] ? 8'h70 : 8'h30;
                blue = hcpu_led[4] ? 8'hb0 : 8'h30;
            end
        end
    end

    DVI_TX_Top u_dvi_tx (
        .I_rst_n(video_rst_n), .I_serial_clk(serial_clk), .I_rgb_clk(pixel_clk),
        .I_rgb_vs(vsync), .I_rgb_hs(hsync), .I_rgb_de(de),
        .I_rgb_r(red), .I_rgb_g(green), .I_rgb_b(blue),
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
    assign led = {hcpu_led[5], mode, hcpu_led[3:1], ~pll_locked};
endmodule