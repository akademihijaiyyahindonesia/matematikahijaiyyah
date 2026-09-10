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
        end else if (disparity == 0 || ones_qm == 4) begin
            encoded <= {~q_m[8], q_m[8], q_m[7:0]};
            disparity <= disparity + (q_m[8] ? (2 * ones_qm - 8) : (8 - 2 * ones_qm));
        end else if ((disparity > 0 && ones_qm > 4) ||
                     (disparity < 0 && ones_qm < 4)) begin
            encoded <= {1'b1, q_m[8], ~q_m[7:0]};
            disparity <= disparity + (q_m[8] ? (16 - 2 * ones_qm) : (-2 * ones_qm));
        end else begin
            encoded <= {1'b0, q_m[8], q_m[7:0]};
            disparity <= disparity + (q_m[8] ? (2 * ones_qm - 8) : (8 - 2 * ones_qm));
        end
    end
endmodule

module dvi_tx_lane (
    input wire       pixel_clk,
    input wire       serial_clk,
    input wire       reset,
    input wire [9:0] word,
    output wire      serialized
);
    OSER10 u_oser (
        .PCLK(pixel_clk), .FCLK(serial_clk), .RESET(reset), .Q(serialized),
        .D0(word[0]), .D1(word[1]), .D2(word[2]), .D3(word[3]), .D4(word[4]),
        .D5(word[5]), .D6(word[6]), .D7(word[7]), .D8(word[8]), .D9(word[9])
    );
endmodule

module DVI_TX_Top (
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

    dvi_tx_lane u_clock (
        .pixel_clk(I_rgb_clk), .serial_clk(I_serial_clk), .reset(reset),
        .word(10'b1111100000), .serialized(tmds_clk_serial)
    );
    dvi_tx_lane u_lane_b (
        .pixel_clk(I_rgb_clk), .serial_clk(I_serial_clk), .reset(reset),
        .word(tmds_b), .serialized(tmds_data_serial[0])
    );
    dvi_tx_lane u_lane_g (
        .pixel_clk(I_rgb_clk), .serial_clk(I_serial_clk), .reset(reset),
        .word(tmds_g), .serialized(tmds_data_serial[1])
    );
    dvi_tx_lane u_lane_r (
        .pixel_clk(I_rgb_clk), .serial_clk(I_serial_clk), .reset(reset),
        .word(tmds_r), .serialized(tmds_data_serial[2])
    );
endmodule
