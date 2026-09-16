// tb_hcpu_text_render.v — does the right glyph land on the right pixels?
//
// This bench exists for one reason: the character generator looks ahead two
// pixels because both memories are registered, and an off-by-one there is
// invisible in a wave view and catastrophic on a screen. Everything is
// shifted by one pixel, or by one cell, or by a whole line, and it still
// looks like text.
//
// So nothing here trusts the renderer's own arithmetic. The bench writes
// characters into the text RAM, scans a frame, samples the RGB output at
// pixel positions it computes ITSELF from the font file, and compares.
//
// ── what each check defends ─────────────────────────────────────
//   glyph 'A' at cell (0,0)      the origin, and the line-crossing look-ahead
//                                that fetches it during the previous blanking
//   glyph '0' mid-row            a cell that is not the first, so the
//                                row*160+col address is exercised
//   a cell on row 1              row addressing, and the y[2:0] font row
//   colour                       the attribute travels with the character and
//                                arrives on the same pixel, not one early
//   blank outside de             nothing is drawn during blanking

`timescale 1ns/1ps
`default_nettype none

module tb_hcpu_text_render;

    localparam H_ACTIVE = 1280, H_FRONT = 110, H_SYNC = 40, H_BACK = 220;
    localparam V_ACTIVE = 720,  V_FRONT = 5,   V_SYNC = 5,  V_BACK = 20;
    localparam H_TOTAL  = H_ACTIVE + H_FRONT + H_SYNC + H_BACK;   // 1650
    localparam V_TOTAL  = V_ACTIVE + V_FRONT + V_SYNC + V_BACK;   // 750
    localparam COLS     = 160;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    wire hsync, vsync, de;
    wire [11:0] x, y, h_count, v_count;

    hcpu_video_timing #(
        .H_ACTIVE(H_ACTIVE), .H_FRONT(H_FRONT), .H_SYNC(H_SYNC), .H_BACK(H_BACK),
        .V_ACTIVE(V_ACTIVE), .V_FRONT(V_FRONT), .V_SYNC(V_SYNC), .V_BACK(V_BACK),
        .HSYNC_POL(1'b1), .VSYNC_POL(1'b1)
    ) u_timing (
        .pixel_clk(clk), .rst_n(rst_n), .hsync(hsync), .vsync(vsync),
        .de(de), .x(x), .y(y), .frame_tick(),
        .h_count_o(h_count), .v_count_o(v_count)
    );

    reg         txt_we = 1'b0;
    reg  [13:0] txt_waddr = 14'd0;
    reg  [15:0] txt_wdata = 16'd0;
    wire [13:0] cell_addr;
    wire [15:0] cell_data;

    // Blank, not the dashboard: this bench writes its own cells and must
    // not have a layout underneath them.
    hcpu_text_ram #(.INIT_HEX("blank_text.hex")) u_text (
        .clk(clk), .we(txt_we), .waddr(txt_waddr), .wdata(txt_wdata),
        .raddr(cell_addr), .rdata(cell_data)
    );

    wire [6:0] font_glyph;
    wire [2:0] font_row;
    wire [7:0] font_bits;

    hcpu_font_rom #(.FONT_HEX("../hcpu_font8x8.hex")) u_font (
        .clk(clk), .glyph(font_glyph), .row(font_row), .bits(font_bits)
    );

    wire [7:0] red, green, blue;

    hcpu_text_render #(
        .COLS(COLS), .ROWS(90), .H_TOTAL(H_TOTAL), .V_TOTAL(V_TOTAL)
    ) u_render (
        .clk(clk), .rst_n(rst_n),
        .h_count(h_count), .v_count(v_count), .de(de),
        .cell_addr(cell_addr), .cell_data(cell_data),
        .font_glyph(font_glyph), .font_row(font_row), .font_bits(font_bits),
        .red(red), .green(green), .blue(blue)
    );

    integer errors = 0;
    task check(input cond, input [255:0] what);
        begin
            if (!cond) begin
                $display("  GAGAL: %0s", what);
                errors = errors + 1;
            end else
                $display("  ok   : %0s", what);
        end
    endtask

    task put;                       // one character into one cell
        input integer col;
        input integer row;
        input [7:0]   ch;
        input [3:0]   attr;
        begin
            @(negedge clk);
            txt_waddr = row * COLS + col;
            txt_wdata = {4'd0, attr, ch};
            txt_we    = 1'b1;
            @(negedge clk);
            txt_we    = 1'b0;
        end
    endtask

    // The bench's own copy of the font, read from the same file but indexed
    // independently -- if the renderer and this disagree, one of them is wrong
    // and the bench says which pixel.
    reg [7:0] want_font [0:1023];
    initial $readmemh("../hcpu_font8x8.hex", want_font);

    // Sample the colour at one absolute pixel by waiting for the beam.
    //
    // THE `#1` INSIDE THE LOOP IS NOT COSMETIC, and leaving it out cost an
    // hour. Evaluating h_count at the instant of the edge reads the value
    // from BEFORE that edge, so the loop exited one cycle early and then
    // sampled the colour after settling -- reporting the pixel to the right
    // of the one it had matched. Every glyph came back shifted one pixel
    // left, which looks exactly like an off-by-one in the renderer's
    // look-ahead and was not: the renderer was correct throughout, and a
    // probe on its internal `ink` is what proved it.
    task sample;
        input integer px;
        input integer py;
        output [7:0]  r, g, b;
        output        lit;
        begin
            @(posedge clk); #1;
            while (!(h_count == px && v_count == py)) begin
                @(posedge clk); #1;
            end
            r = red; g = green; b = blue;
            lit = (red != 8'h06) || (green != 8'h0c) || (blue != 8'h16);
        end
    endtask

    integer i, bit_i;
    reg [7:0] r, g, b;
    reg [7:0] ink_r, ink_g, ink_b;
    reg lit;
    reg [7:0] want_row;
    reg row_match, col_match;

    initial begin
        $display("=== tb_hcpu_text_render: glyph ke pixel, 160x90 di 1280x720 ===");

        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (4) @(negedge clk);

        // 'A' at the origin, '0' at column 7 of row 0, 'A' at row 1 column 0.
        put(0, 0, 8'h41, 4'd3);     // GREEN
        put(7, 0, 8'h30, 4'd5);     // RED
        put(0, 1, 8'h41, 4'd1);     // WHITE

        // Everything below is sampled in increasing (y, x) order, one frame
        // for the lot. Jumping backwards costs a whole 12.4 ms frame per
        // sample, which is how the first version of this bench ran out of
        // simulated time before it reached its last check.

        // ── y=0: 'A' row 0 at cell (0,0), and its colour ────────
        want_row = want_font[{7'd65, 3'd0}];
        row_match = 1'b1;
        for (i = 0; i < 8; i = i + 1) begin
            sample(i, 0, r, g, b, lit);
            if (i == 2) begin ink_r = r; ink_g = g; ink_b = b; end
            if (lit !== ((want_row >> (7 - i)) & 1'b1)) begin
                $display("    x=%0d y=0: lit=%0b, font bilang %0b",
                         i, lit, (want_row >> (7 - i)) & 1'b1);
                row_match = 1'b0;
            end
        end
        check(row_match, "A di sel 0,0: baris 0 cocok");
        check(ink_r == 8'h30 && ink_g == 8'hd0 && ink_b == 8'h70,
              "warna GREEN pada pixel bertinta");

        // ── same line: cell (7,0), which exercises the column ───
        want_row = want_font[{7'd48, 3'd0}];
        col_match = 1'b1;
        for (i = 0; i < 8; i = i + 1) begin
            sample(7*8 + i, 0, r, g, b, lit);
            if (i == 2) begin ink_r = r; ink_g = g; ink_b = b; end
            if (lit !== ((want_row >> (7 - i)) & 1'b1)) col_match = 1'b0;
        end
        check(col_match, "0 di sel 7,0: alamat kolom benar");
        check(ink_r == 8'he0 && ink_g == 8'h50 && ink_b == 8'h50,
              "warna RED milik selnya sendiri");

        // ── y=4: the crossbar of the same 'A' ───────────────────
        want_row = want_font[{7'd65, 3'd4}];
        row_match = 1'b1;
        for (i = 0; i < 8; i = i + 1) begin
            sample(i, 4, r, g, b, lit);
            if (lit !== ((want_row >> (7 - i)) & 1'b1)) row_match = 1'b0;
        end
        check(row_match, "A di sel 0,0: baris 4 cocok");

        // ── y=8: cell row 1, which is row*160 addressing ────────
        want_row = want_font[{7'd65, 3'd0}];
        row_match = 1'b1;
        for (i = 0; i < 8; i = i + 1) begin
            sample(i, 8, r, g, b, lit);
            if (lit !== ((want_row >> (7 - i)) & 1'b1)) begin
                $display("    x=%0d y=8: lit=%0b, font bilang %0b",
                         i, lit, (want_row >> (7 - i)) & 1'b1);
                row_match = 1'b0;
            end
        end
        check(row_match, "A di sel 0,1: baris sel benar");

        // ── an untouched cell is blank, not garbage ─────────────
        row_match = 1'b1;
        for (i = 0; i < 8; i = i + 1) begin
            sample(80*8 + i, 40, r, g, b, lit);
            if (lit) row_match = 1'b0;
        end
        check(row_match, "sel yang tak ditulis: kosong");

        // ── nothing is drawn outside the active area ────────────
        sample(H_ACTIVE + 20, 40, r, g, b, lit);
        check(r == 8'h00 && g == 8'h00 && b == 8'h00,
              "blanking horizontal: hitam");

        if (errors == 0)
            $display("tb_hcpu_text_render: SEMUA LULUS (8 pemeriksaan)");
        else
            $display("tb_hcpu_text_render: %0d GAGAL", errors);
        $finish;
    end

    initial begin
        #120_000_000;
        $display("tb_hcpu_text_render: GAGAL -- waktu habis");
        $finish;
    end

endmodule

`default_nettype wire
