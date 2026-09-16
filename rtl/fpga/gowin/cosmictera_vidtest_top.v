// cosmictera_vidtest_top.v — video only, and nothing that reads a memory.
//
// DIAGNOSTIC, not a product. The display node put readable text on a real
// monitor and filled every pixel that was NOT part of a glyph with dense,
// flickering vertical stripes. Ink correct, background wrong, and changing
// frame to frame.
//
// That rules a lot out by itself -- the PLL locks, TMDS carries, the monitor
// syncs at 1280x720, and the character addressing is right or the text would
// be in the wrong places. What it does not separate is whether the fault is
// in the pixel path at all or in what feeds it.
//
// So this build removes everything that feeds it. No font ROM, no layout ROM,
// no compositor, no renderer, no text. The colour of a pixel is a function of
// its coordinates and nothing else:
//
//     four vertical bars: red, green, blue, white
//
// Solid primaries are the cleanest signal available. Each drives ONE
// lane to 0xFF and the other two to 0x00, so a lane that is swapped or
// mis-serialised names itself: red arriving as blue is mapping, red
// arriving as noise is serialisation, and all four correct means the
// encoder fix was the whole of it.
//
// If this screen is clean and steady, then the PLL, the pixel clock, the
// timing generator, DVI_TX and the TMDS pads are all healthy, and the fault
// is downstream of none of them -- it is in the font ROM, the layout ROM, the
// compositor or the renderer. If this screen flickers too, everything built
// on top of it was a distraction and the fault is in the video path itself.
//
// Either answer is worth a build. That is what a control is for.

module cosmictera_vidtest_top (
    input  wire       clk_27m,
    input  wire       btn_rst_n,
    input  wire       mode_key,
    output wire       tmds_clk_p,
    output wire [2:0] tmds_data_p
);

    wire serial_clk;
    wire pixel_clk;
    wire pll_locked;

    // Same reset rule as every other wrapper here: not gated on btn_rst_n,
    // which is pin 87 = MODE1 and is held low on this board.
    wire video_rst_n = pll_locked;

    TMDS_rPLL u_tmds_rpll (.clkin(clk_27m), .clkout(serial_clk), .lock(pll_locked));
    CLKDIV u_clkdiv (
        // CALIB LOW, AND THIS IS THE ONE VARIABLE THIS BUILD CHANGES.
        // OSER10 requires PCLK and FCLK to hold a fixed phase; CLKDIV is what
        // holds it. CALIB is a calibration REQUEST, and every video wrapper in
        // this tree has held it asserted for ever -- which asks the divider to
        // keep re-aligning. A phase that moves under the serialiser shifts the
        // ten-bit TMDS word, and a shifted word is exactly what the monitor
        // showed: structure correct, colours wrong, dense per-pixel striping.
        // 0x060c16 arriving as near-white is a mangled word, not a mangled
        // pixel value.
        //
        // Changed HERE ONLY. hcpu_hdmi_top.v and kabah_hdmi_top.v carry the
        // same line and are fingerprinted; touching them demands a re-measured
        // place and route, and that is the owner's call once this build says
        // whether the guess was right.
        .RESETN(video_rst_n), .HCLKIN(serial_clk), .CLKOUT(pixel_clk), .CALIB(1'b0)
    );
    defparam u_clkdiv.DIV_MODE = "5";
    defparam u_clkdiv.GSREN = "false";

    wire hsync, vsync, de;
    wire [11:0] x, y, h_count, v_count;

    hcpu_video_timing #(
        .H_ACTIVE(1280), .H_FRONT(110), .H_SYNC(40), .H_BACK(220),
        .V_ACTIVE(720), .V_FRONT(5), .V_SYNC(5), .V_BACK(20),
        .HSYNC_POL(1'b1), .VSYNC_POL(1'b1)
    ) u_timing (
        .pixel_clk(pixel_clk), .rst_n(video_rst_n), .hsync(hsync), .vsync(vsync),
        .de(de), .x(x), .y(y), .frame_tick(),
        .h_count_o(h_count), .v_count_o(v_count)
    );

    // Registered one stage, deliberately. The display node drives DVI_TX from
    // a combinational function of h_count and a memory output; this drives it
    // from a register. If the stripes survive THIS, the combinational path is
    // not the difference either.
    reg [7:0] red, green, blue;

    always @(posedge pixel_clk or negedge video_rst_n) begin
        if (!video_rst_n) begin
            red <= 8'h00; green <= 8'h00; blue <= 8'h00;
        end else if (!de) begin
            red <= 8'h00; green <= 8'h00; blue <= 8'h00;
        end else if (h_count < 12'd320) begin
            red <= 8'hff; green <= 8'h00; blue <= 8'h00;     // MERAH penuh
        end else if (h_count < 12'd640) begin
            red <= 8'h00; green <= 8'hff; blue <= 8'h00;     // HIJAU penuh
        end else if (h_count < 12'd960) begin
            red <= 8'h00; green <= 8'h00; blue <= 8'hff;     // BIRU penuh
        end else begin
            red <= 8'hff; green <= 8'hff; blue <= 8'hff;     // PUTIH
        end
    end

    wire tmds_clk_serial;
    wire [2:0] tmds_data_serial;

    // BIT_REVERSE(0) -- BACK TO THE ORIGINAL ORDER, AND THE BOARD SETTLED IT.
    // Reversed, the monitor lost the link entirely: no signal at all, where
    // before it locked and showed a corrupt picture. A link that dies when the
    // word is reversed is a link whose word was in the right order. Bit order
    // is ruled OUT, and ruled out by evidence rather than by argument.
    DVI_TX_Top #(.BIT_REVERSE(0)) u_dvi_tx (
        .I_rst_n(video_rst_n), .I_serial_clk(serial_clk), .I_rgb_clk(pixel_clk),
        .I_rgb_vs(vsync), .I_rgb_hs(hsync), .I_rgb_de(de),
        .I_rgb_r(red), .I_rgb_g(green), .I_rgb_b(blue),
        .tmds_clk_serial(tmds_clk_serial), .tmds_data_serial(tmds_data_serial)
    );

    // ── THE OUTPUT STAGE, AND THE HYPOTHESIS IT KILLED ─────────
    // Back to P only, and NOT because the idea was abandoned. The suspicion
    // was specific and well formed: Sipeed's DVI TX for this board declares
    // O_tmds_clk_p AND O_tmds_clk_n, O_tmds_data_p[2:0] AND O_tmds_data_n[2:0]
    // -- eight signals -- while every wrapper here declares four and lets
    // LVCMOS33D in the .cst produce the complement. A receiver compares P
    // against N, so a complement made by a constraint rather than by a driver
    // could plausibly be skewed enough to close the eye on arbitrary data
    // while leaving the clock lane -- five ones, five zeros -- readable. Lock
    // yes, sync yes, pixels no. It fitted every symptom.
    //
    // Three ways to drive N from logic. All three were built, none reached a
    // bitstream, and the owner authorised the attempt:
    //
    //   ELVDS_OBUF at the top      synthesis  ELVDS_OBUF 4, OBUF 8
    //                              placement  ELVDS_OBUF 0, OBUF 8
    //                              yosys adds its own OBUF behind every
    //                              top-level output, so the netlist is
    //                              ELVDS_OBUF -> OBUF -> pad, and nextpnr
    //                              drops the differential cells. The same
    //                              failure 2e2e3cd measured for TLVDS_TBUF.
    //                              NOT FLASHED -- a bitstream missing the one
    //                              cell under test answers nothing.
    //
    //   invert the serial stream   nextpnr-himbaechel asserts
    //                              out_iob != nullptr && out_iob->bel != BelId()
    //                              (pack_iologic.cc:183). OSER10 must reach a
    //                              pad directly; one LUT1 is already too much.
    //
    //   a second OSER10 on the     ERROR: Can't place u_lane_r.u_oser at
    //   complement of the word     X39Y54/IOBB because it's already taken by
    //                              tmds_data_n_OBUF_O
    //
    // The third is the device speaking, not the toolchain. A 10:1 serialiser
    // occupies the IOLOGIC of BOTH halves of an IO pair, so the P lane's own
    // OSER10 claims the N pad's slot -- the pair has no B half left to drive.
    // One serialiser per pair is the maximum the silicon offers.
    //
    // Which settles the hypothesis by making it unbuildable ANYWHERE. Sipeed's
    // O_tmds_*_n cannot come from a second serialiser either; it comes from a
    // differential pad buffer fed by the one stream -- the same construction
    // as IO_LOC "..._OBUF_O" 33,34 at LVCMOS33D. The eight ports are one
    // stream per lane wearing two names. There was never a difference to test.
    //
    // So the output stage is ELIMINATED, and by a stronger argument than a
    // screen test: not "we drove N and it looked the same", but "N cannot be
    // driven, here and in the reference alike".
    assign tmds_clk_p  = tmds_clk_serial;
    assign tmds_data_p = tmds_data_serial;

endmodule
