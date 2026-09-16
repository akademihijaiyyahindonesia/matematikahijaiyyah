// hcpu_text_render.v — characters into pixels, two memories deep.
//
// Turns the text RAM and the font ROM into RGB, one cell per eight pixels,
// 160 x 90 cells over 1280 x 720.
//
// ── the whole difficulty is two cycles of memory latency ────────
// Both memories are registered, so the character for a pixel has to be asked
// for before that pixel arrives:
//
//   cycle t     address cell(h_count + 2) presented to the text RAM
//   cycle t+1   its character arrives; presented to the font ROM
//   cycle t+2   its glyph row arrives -- and h_count is now h_count+2
//
// So the byte on `bits` always belongs to the pixel being scanned right now,
// and no delay line is needed on de, hsync or vsync: those are combinational
// from the same counters and are already in step. What DOES need delaying is
// the colour, which leaves the text RAM a cycle before the glyph leaves the
// font ROM -- registered once, and that is the whole of it.
//
// THE LOOK-AHEAD HAS TO CROSS THE LINE BOUNDARY, and that is why this module
// takes the raw counters rather than x and y. At the last two pixels of a
// line the cell being fetched belongs to the NEXT line, which may also be the
// next row of cells. `x` and `y` are zero out there and would fetch cell zero
// of row zero, putting the top-left character at the start of every line.
//
// ── colour ──────────────────────────────────────────────────────
// Four bits per cell, resolved here rather than stored as RGB: 14,400 cells
// would otherwise carry 24 bits of colour each, and the palette is eight
// entries. The names are the ones the dashboard uses.

`default_nettype none

module hcpu_text_render #(
    parameter COLS     = 160,
    parameter ROWS     = 90,
    parameter H_TOTAL  = 1650,
    parameter V_TOTAL  = 750,
    parameter AW       = 14
) (
    input  wire        clk,            // pixel_clk
    input  wire        rst_n,

    input  wire [11:0] h_count,
    input  wire [11:0] v_count,
    input  wire        de,

    // text RAM read port
    output wire [AW-1:0] cell_addr,
    input  wire [15:0]   cell_data,

    // font ROM read port
    output wire [6:0]  font_glyph,
    output wire [2:0]  font_row,
    input  wire [7:0]  font_bits,

    output reg  [7:0]  red,
    output reg  [7:0]  green,
    output reg  [7:0]  blue
);

    // ── stage 0: where the beam will be in two pixels ───────────
    wire [12:0] ahead   = {1'b0, h_count} + 13'd2;
    wire        h_wrap  = (ahead >= H_TOTAL);
    wire [11:0] hla     = h_wrap ? (ahead - H_TOTAL) : ahead[11:0];
    wire [11:0] vla     = h_wrap ? ((v_count == V_TOTAL - 1) ? 12'd0
                                                             : v_count + 12'd1)
                                 : v_count;

    wire [7:0] la_col = hla[10:3];
    wire [6:0] la_row = vla[9:3];

    // row * 160 without a multiplier: 160 = 128 + 32, so row<<7 + row<<5.
    // Written once as <<6 + <<4, which is row*80 -- every line after the
    // first landed half a row early, and the bench caught it as "row 1 shows
    // the wrong cell" rather than as anything that looked like arithmetic.
    // la_row is 7 bits and 89*160 = 14,240, so 14 bits hold it without care.
    assign cell_addr = {la_row, 7'd0} + {2'd0, la_row, 5'd0} + {6'd0, la_col};

    // ── stage 1: the character is out, the glyph row goes in ────
    reg [2:0] row_d;
    always @(posedge clk) row_d <= vla[2:0];

    assign font_glyph = cell_data[6:0];
    assign font_row   = row_d;

    // ── stage 2: colour catches up with the glyph ───────────────
    reg [3:0] attr_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) attr_d <= 4'd0;
        else        attr_d <= cell_data[11:8];
    end

    wire ink = font_bits[7 - h_count[2:0]];

    // The palette. GRAY is deliberately dim rather than absent: a field that
    // is NOT INSTRUMENTED must be legible and obviously not live, which a
    // blank cell would fail at in both directions.
    localparam [3:0] C_DIM    = 4'd0,   // body text, quiet
                     C_WHITE  = 4'd1,   // headings
                     C_CYAN   = 4'd2,   // labels, rules
                     C_GREEN  = 4'd3,   // RUNNING / READY
                     C_YELLOW = 4'd4,   // WAIT / BUSY
                     C_RED    = 4'd5,   // ERROR
                     C_BLUE   = 4'd6,   // information
                     C_GOLD   = 4'd7;   // the headline

    reg [23:0] rgb;
    always @* begin
        case (attr_d)
            C_WHITE : rgb = 24'hd8e4f0;
            C_CYAN  : rgb = 24'h30c0d0;
            C_GREEN : rgb = 24'h30d070;
            C_YELLOW: rgb = 24'he0b040;
            C_RED   : rgb = 24'he05050;
            C_BLUE  : rgb = 24'h4080e0;
            C_GOLD  : rgb = 24'hf0c860;
            default : rgb = 24'h7890a8;   // C_DIM
        endcase
    end

    // Background is the same deep field the earlier test pattern used, so a
    // screen that comes up dark-blue rather than black is the display engine
    // running, not a monitor with no signal.
    always @* begin
        if (de && ink) begin
            red   = rgb[23:16];
            green = rgb[15:8];
            blue  = rgb[7:0];
        end else if (de) begin
            red   = 8'h06;
            green = 8'h0c;
            blue  = 8'h16;
        end else begin
            red   = 8'h00;
            green = 8'h00;
            blue  = 8'h00;
        end
    end

endmodule

`default_nettype wire
