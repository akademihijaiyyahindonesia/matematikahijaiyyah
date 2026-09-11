// Hijaiyyah Ka'bah HDMI wrapper for Tang Nano 20K.
//
// NEVER BUILT. Not synthesised, not placed, not flashed -- label AT. The
// video path is copied from hcpu_hdmi_top.v, which the board did prove:
// 1280x720 over TMDS on pins 33..40 while the HCPU answered over UART.
// This copy still carried that file's first, broken output stage -- a
// hand-placed TLVDS_TBUF per lane and LVDS25 in the .cst -- until it was
// brought in line with the fix below. Nothing has run it since, so the fix
// is inherited, not measured: build it and count TLVDS cells in the PNR
// JSON before reading anything into a dark monitor, either way.

module kabah_hdmi_top (
    input wire        clk_27m,
    input wire        btn_rst_n,
    input wire        mode_key,
    input wire        uart_rxd,
    output wire       uart_txd,
    output wire [5:0] led,
    // Only the P half is a port; LVCMOS33D in kabah_hdmi.cst drives both
    // pads of each pair from one IOB. See hcpu_hdmi_top.v.
    output wire       tmds_clk_p,
    output wire [2:0] tmds_data_p
);
    wire serial_clk;
    wire pixel_clk;
    wire pll_locked;
    // See hcpu_hdmi_top.v: btn_rst_n is pin 87 = MODE1 and this board holds
    // it low, so gating on its level held CLKDIV.RESETN and the pixel clock
    // never started. PLL lock is the real condition.
    wire video_rst_n = pll_locked;
    wire kabah_uart_txd;
    wire [5:0] kabah_led;

    hijaiyyah_kabah_gowin_top u_kabah (
        .clk_27m(clk_27m), .btn_rst_n(btn_rst_n), .uart_rxd(uart_rxd),
        .uart_txd(kabah_uart_txd), .led(kabah_led)
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
                red = mode ? 8'h80 : 8'h20;
                green = mode ? 8'h20 : 8'h70;
                blue = mode ? 8'h40 : 8'h10;
            end else if ((x[6:4] == 0) || (y[5:3] == 0)) begin
                red = kabah_led[0] ? 8'h30 : 8'hb0;
                green = kabah_led[1] ? 8'h80 : 8'h30;
                blue = kabah_led[2] ? 8'hc0 : 8'h20;
            end
        end
    end

    DVI_TX_Top u_dvi_tx (
        .I_rst_n(video_rst_n), .I_serial_clk(serial_clk), .I_rgb_clk(pixel_clk),
        .I_rgb_vs(vsync), .I_rgb_hs(hsync), .I_rgb_de(de),
        .I_rgb_r(red), .I_rgb_g(green), .I_rgb_b(blue),
        .tmds_clk_serial(tmds_clk_serial), .tmds_data_serial(tmds_data_serial)
    );

    // No TLVDS_TBUF. In hcpu_hdmi_top.v yosys still inserted its own OBUF
    // behind each one, nextpnr dropped all four, and eight single-ended
    // drivers reached pins 33..40 -- zero TLVDS cells placed, no TMDS, a
    // dark monitor. The pairs are made differential by the constraint.
    assign tmds_clk_p  = tmds_clk_serial;
    assign tmds_data_p = tmds_data_serial;

    assign uart_txd = kabah_uart_txd;
    assign led = {kabah_led[5], mode, kabah_led[3:1], ~pll_locked};
endmodule