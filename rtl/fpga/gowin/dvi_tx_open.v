// Open-source DVI/HDMI transmitter for Tang Nano 20K.
// Pixel clock is 1x, FCLK is 5x; OSER10 emits the 10-bit TMDS word.

module tmds_encode (
    input wire       clk,
    input wire       de,
    input wire       c0,
    input wire       c1,
    input wire [7:0] data,
    output reg [9:0] encoded
);
    reg [8:0] q_m;
    reg signed [5:0] disparity;
    integer ones;
    integer ones_qm;
    integer i;

    always @(posedge clk) begin
        ones = data[0] + data[1] + data[2] + data[3] +
               data[4] + data[5] + data[6] + data[7];
        q_m[0] = data[0];
        for (i = 1; i < 8; i = i + 1)
            q_m[i] = q_m[i-1] ^ data[i] ^ (ones > 4 || (ones == 4 && !data[0]));
        q_m[8] = !(ones > 4 || (ones == 4 && !data[0]));
        ones_qm = q_m[0] + q_m[1] + q_m[2] + q_m[3] +
                  q_m[4] + q_m[5] + q_m[6] + q_m[7];

        if (!de) begin
            disparity <= 0;
            case ({c1, c0})
                2'b00: encoded <= 10'b1101010100;
                2'b01: encoded <= 10'b0010101011;
                2'b10: encoded <= 10'b0101010100;
                default: encoded <= 10'b1010101011;
            endcase
        // ── THE RUNNING DISPARITY HAD TO MATCH WHAT IS SENT ─────
        // All three branches were wrong, and the code said so itself: each
        // one's disparity update branched on q_m[8] while its DATA did not,
        // or used the same arithmetic as a branch that sends different bits.
        // Accounting cannot describe an encoding the data path does not
        // perform.
        //
        // Measured against a decoder before and after (N0 = 8 - N1):
        //
        //   as written   30 of 256 bytes did not survive a round trip, and a
        //                run of 0xFF drove `disparity` to -10,240
        //   as here      0 of 1024 fail, and |disparity| never exceeds 8
        //
        // The second number is the one that reached the monitor. `disparity`
        // is signed [5:0] -- it holds -32..+31 -- so a count running to five
        // figures WRAPS, and a wrapped count picks the wrong branch for every
        // pixel after it. Structure survived because the control words in the
        // !de case never touch this; colour did not.
        end else if (disparity == 0 || ones_qm == 4) begin
            encoded <= {~q_m[8], q_m[8], q_m[8] ? q_m[7:0] : ~q_m[7:0]};
            disparity <= disparity + (q_m[8] ? (2 * ones_qm - 8) : (8 - 2 * ones_qm));
        end else if ((disparity > 0 && ones_qm > 4) ||
                     (disparity < 0 && ones_qm < 4)) begin
            encoded <= {1'b1, q_m[8], ~q_m[7:0]};
            disparity <= disparity + (2 * q_m[8]) + (8 - 2 * ones_qm);
        end else begin
            encoded <= {1'b0, q_m[8], q_m[7:0]};
            disparity <= disparity + (2 * ones_qm - 8) - (2 * (1 - q_m[8]));
        end
    end
endmodule

module dvi_tx_lane #(
    // ── which end of the word leaves first ──────────────────────
    // TMDS is sent LSB first. This maps word[0] to D0, which is right IF
    // OSER10 emits D0 first -- and that is the assumption under test, not a
    // fact this repository has ever checked.
    //
    // Reversed, the symptom is not silence. The clock lane's 1111100000
    // becomes 0000011111, still a fifty-percent clock, so the monitor still
    // locks. The control word 1101010100 becomes 0010101011, which is another
    // VALID control word, so sync still runs and the geometry still lands.
    // Only the pixel data comes out systematically wrong, repeating with the
    // ten-bit word -- which is every symptom the board has shown.
    //
    // Default 0 keeps hcpu_hdmi_top.v and kabah_hdmi_top.v behaving exactly
    // as they do today. Only the diagnostic build sets it.
    parameter BIT_REVERSE = 0
) (
    input wire       pixel_clk,
    input wire       serial_clk,
    input wire       reset,
    input wire [9:0] word,
    // ── ONE OUTPUT PER LANE, AND THE DEVICE INSISTS ─────────────
    // There is no `serialized_n` here, and two measured failures say there
    // cannot be. The N half of each TMDS pair is produced by the PAD, from
    // this one stream -- hcpu_hdmi.cst names both pads in a single IO_LOC at
    // LVCMOS33D -- and every attempt to drive it from logic instead was
    // refused before a bitstream existed:
    //
    //   invert the serial output      nextpnr-himbaechel asserts
    //                                 out_iob != nullptr && out_iob->bel != BelId()
    //                                 (himbaechel/uarch/gowin/pack_iologic.cc:183)
    //                                 -- OSER10 must reach a pad directly, and
    //                                 one LUT1 in between is already too much
    //
    //   a second OSER10 on the word   ERROR: Can't place u_lane_r.u_oser at
    //   complement, feeding the N pad  X39Y54/IOBB because it's already taken
    //                                 by tmds_data_n_OBUF_O
    //
    // The second one is the device, not the tool. A 10:1 serialiser occupies
    // the IOLOGIC of BOTH halves of an IO pair, so a pair that carries an
    // OSER10 has no B half left to drive. One serialiser per pair is the
    // maximum the silicon offers, which is precisely why a differential pad
    // buffer exists: it turns one stream into two pads because nothing else
    // can. Sipeed's IP exposes O_tmds_*_n for the same reason, and its N half
    // comes from such a buffer -- not from a second serialiser it could not
    // have placed either.
    output wire      serialized
);
    wire [9:0] w = BIT_REVERSE ? {word[0], word[1], word[2], word[3], word[4],
                                  word[5], word[6], word[7], word[8], word[9]}
                               : word;
    OSER10 u_oser (
        .PCLK(pixel_clk), .FCLK(serial_clk), .RESET(reset), .Q(serialized),
        .D0(w[0]), .D1(w[1]), .D2(w[2]), .D3(w[3]), .D4(w[4]),
        .D5(w[5]), .D6(w[6]), .D7(w[7]), .D8(w[8]), .D9(w[9])
    );
endmodule

module DVI_TX_Top #(
    parameter BIT_REVERSE = 0
) (
    input wire       I_rst_n,
    input wire       I_serial_clk,
    input wire       I_rgb_clk,
    input wire       I_rgb_vs,
    input wire       I_rgb_hs,
    input wire       I_rgb_de,
    input wire [7:0] I_rgb_r,
    input wire [7:0] I_rgb_g,
    input wire [7:0] I_rgb_b,
    output wire      tmds_clk_serial,
    output wire [2:0] tmds_data_serial
);
    wire [9:0] tmds_b;
    wire [9:0] tmds_g;
    wire [9:0] tmds_r;
    wire       reset = !I_rst_n;

    tmds_encode u_blue (.clk(I_rgb_clk), .de(I_rgb_de), .c0(I_rgb_hs), .c1(I_rgb_vs), .data(I_rgb_b), .encoded(tmds_b));
    tmds_encode u_green (.clk(I_rgb_clk), .de(I_rgb_de), .c0(1'b0), .c1(1'b0), .data(I_rgb_g), .encoded(tmds_g));
    tmds_encode u_red (.clk(I_rgb_clk), .de(I_rgb_de), .c0(1'b0), .c1(1'b0), .data(I_rgb_r), .encoded(tmds_r));

    dvi_tx_lane #(.BIT_REVERSE(BIT_REVERSE)) u_clock (
        .pixel_clk(I_rgb_clk), .serial_clk(I_serial_clk), .reset(reset),
        .word(10'b1111100000), .serialized(tmds_clk_serial)
    );
    dvi_tx_lane #(.BIT_REVERSE(BIT_REVERSE)) u_lane_b (
        .pixel_clk(I_rgb_clk), .serial_clk(I_serial_clk), .reset(reset),
        .word(tmds_b), .serialized(tmds_data_serial[0])
    );
    dvi_tx_lane #(.BIT_REVERSE(BIT_REVERSE)) u_lane_g (
        .pixel_clk(I_rgb_clk), .serial_clk(I_serial_clk), .reset(reset),
        .word(tmds_g), .serialized(tmds_data_serial[1])
    );
    dvi_tx_lane #(.BIT_REVERSE(BIT_REVERSE)) u_lane_r (
        .pixel_clk(I_rgb_clk), .serial_clk(I_serial_clk), .reset(reset),
        .word(tmds_r), .serialized(tmds_data_serial[2])
    );
endmodule
