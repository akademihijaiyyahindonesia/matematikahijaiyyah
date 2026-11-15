// ============================================================================
// cosmictera_boot_render.v — 1280x720@60Hz Pixel Compositor & UI Frame Engine
// (Stage 1.5 Unified SoC: Dual-BSRAM Pixel Chrome Engine `boot_bg_x_rom.hex` +
//  `boot_bg_y_rom.hex` eliminating 160x90 combinational chrome decoders)
// ============================================================================

`default_nettype none

module cosmictera_boot_render #(
    parameter H_TOTAL  = 1650,
    parameter V_TOTAL  = 750,
    parameter BG_X_HEX = "boot_bg_x_rom.hex",
    parameter BG_Y_HEX = "boot_bg_y_rom.hex"
) (
    input  wire        clk,             // pixel_clk (74.25 MHz)
    input  wire        rst_n,

    input  wire [11:0] h_count,
    input  wire [11:0] v_count,
    input  wire        de,
    input  wire [1:0]  screen_state,    // 0 = STARTUP, 1 = READY, 2 = ERROR

    // Lookahead coordinates to text ROM & compositor (Stage 0)
    output wire [7:0]  la_col,
    output wire [6:0]  la_row,
    input  wire [11:0] text_rom_data,   // Stage 1 output from cosmictera_boot_text_rom
    input  wire        comp_hit,        // Stage 0 probe from cosmictera_boot_compositor
    input  wire [7:0]  comp_ch,
    input  wire [3:0]  comp_at,
    input  wire [11:0] comp_cell_s1,    // Stage 1 synchronous BSRAM/dynamic output from compositor

    // Font ROM interface (Stage 1 -> Stage 2)
    output wire [6:0]  font_glyph,
    output wire [2:0]  font_row,
    input  wire [7:0]  font_bits,

    // Logo engine interface (aligned to current h_count, v_count)
    input  wire        logo_pixel_valid,
    input  wire [23:0] logo_pixel_rgb,

    output reg  [7:0]  red,
    output reg  [7:0]  green,
    output reg  [7:0]  blue
);

    // ── Stage 0: 2-pixel lookahead across line wrap ──────────────
    wire        h_wrap     = (h_count[11:1] == 11'd824);
    wire        v_last     = (v_count == 12'd749);
    wire [11:0] vla        = h_wrap ? (v_last ? 12'd0 : (v_count + 12'd1)) : v_count;
    wire        col_inc    = (h_count[2:1] == 2'b11);
    assign      la_col     = h_wrap ? 8'd0 : (h_count[10:3] + {7'd0, col_inc});
    assign      la_row     = vla[9:3];

    // ── Stage 1: Latch glyph scanline row & select BSRAM cell ────
    reg [2:0] row_d;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            row_d <= 3'd0;
        end else begin
            row_d <= vla[2:0];
        end
    end

    wire [11:0] cell_s1 = (|comp_cell_s1[7:0]) ? comp_cell_s1 : text_rom_data;
    assign font_glyph   = cell_s1[6:0];
    assign font_row     = row_d;

    // ── Stage 2: Align color attribute with font_bits at h_count ─
    reg [3:0] attr_d2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) attr_d2 <= 4'd0;
        else        attr_d2 <= cell_s1[11:8];
    end

    wire text_ink = font_bits[3'd7 - h_count[2:0]];

    reg [23:0] text_rgb;
    always @* begin
        case (attr_d2)
            4'd1: text_rgb = 24'hd8e4f0; // C_WHITE
            4'd2: text_rgb = 24'h30c0d0; // C_CYAN
            4'd3: text_rgb = 24'h30d070; // C_GREEN
            4'd4: text_rgb = 24'he0b040; // C_YELLOW
            4'd5: text_rgb = 24'he05050; // C_RED
            4'd6: text_rgb = 24'h4080e0; // C_BLUE
            4'd7: text_rgb = 24'hf0c860; // C_GOLD
            default: text_rgb = 24'h7890a8; // C_DIM
        endcase
    end

    // ── Dual-BSRAM Pixel Chrome Engine (`boot_bg_x_rom` + `boot_bg_y_rom`) ──
    reg [7:0] bg_x_rom [0:2047];
    reg [7:0] bg_y_rom [0:1023];
    initial begin
        if (BG_X_HEX != "") $readmemh(BG_X_HEX, bg_x_rom);
        if (BG_Y_HEX != "") $readmemh(BG_Y_HEX, bg_y_rom);
    end

    reg [7:0] bg_x_q = 8'h00;
    reg [7:0] bg_y_q = 8'h01;
    always @(posedge clk) begin
        bg_x_q <= bg_x_rom[h_count[10:0]];
        bg_y_q <= bg_y_rom[vla[9:0]];
    end

    wire in_hdr_badge_x  = bg_x_q[0];
    wire hdr_badge_x_bdr = bg_x_q[1];
    wire in_any_r3_x     = bg_x_q[2];
    wire in_card_c_x     = bg_x_q[3];
    wire r3_x_bdr        = bg_x_q[4];
    wire in_r45_x        = bg_x_q[5];
    wire r45_x_bdr       = bg_x_q[6];
    wire in_r6_x         = bg_x_q[7];
    wire r6_x_bdr        = r45_x_bdr & in_any_r3_x;

    wire [3:0] y_zone       = bg_y_q[3:0];
    wire       ftr_top_line = bg_y_q[4];
    wire       in_footer    = bg_y_q[5];

    wire [23:0] state_accent = (screen_state == 2'd2) ? 24'he05050 :
                               (screen_state == 2'd1) ? 24'h30d070 : 24'he0b040;

    reg [23:0] bg_rgb;
    always @* begin
        bg_rgb = 24'h060c16;
        if (ftr_top_line)
            bg_rgb = 24'h1e3a5f;
        else if (in_footer)
            bg_rgb = 24'h091322;
        else case (y_zone)
            4'd1: bg_rgb = 24'hd69b2c;
            4'd2: bg_rgb = state_accent;
            4'd3: bg_rgb = in_hdr_badge_x ? state_accent : 24'h091322;
            4'd4: bg_rgb = in_hdr_badge_x ? (hdr_badge_x_bdr ? state_accent : 24'h0d1e36) : 24'h091322;
            4'd5: bg_rgb = 24'h091322;
            4'd6, 4'd7: if (in_any_r3_x) bg_rgb = in_card_c_x ? 24'hf0c860 : 24'h30c0d0;
            4'd8:       if (in_any_r3_x) bg_rgb = 24'h1e3a5f;
            4'd9:       if (in_any_r3_x) bg_rgb = r3_x_bdr ? 24'h1e3a5f : 24'h0a1526;
            4'd10:      if (in_r45_x)    bg_rgb = 24'h1e3a5f;
            4'd11:      if (in_r45_x)    bg_rgb = r45_x_bdr ? 24'h1e3a5f : 24'h162c48;
            4'd12:      if (in_r45_x)    bg_rgb = r45_x_bdr ? 24'h1e3a5f : 24'h091322;
            4'd13:      if (in_r6_x)     bg_rgb = (screen_state == 2'd2) ? 24'he05050 : 24'h1e3a5f;
            4'd14:      if (in_r6_x)     bg_rgb = r6_x_bdr ? ((screen_state == 2'd2) ? 24'he05050 : 24'h1e3a5f) : 24'h162c48;
            4'd15:      if (in_r6_x)     bg_rgb = r6_x_bdr ? ((screen_state == 2'd2) ? 24'he05050 : 24'h1e3a5f) : 24'h08101d;
            default:    bg_rgb = 24'h060c16;
        endcase
    end

    always @* begin
        if (!de || !rst_n) begin
            red   = 8'h00;
            green = 8'h00;
            blue  = 8'h00;
        end else if (logo_pixel_valid) begin
            red   = logo_pixel_rgb[23:16];
            green = logo_pixel_rgb[15:8];
            blue  = logo_pixel_rgb[7:0];
        end else if (text_ink) begin
            red   = text_rgb[23:16];
            green = text_rgb[15:8];
            blue  = text_rgb[7:0];
        end else begin
            red   = bg_rgb[23:16];
            green = bg_rgb[15:8];
            blue  = bg_rgb[7:0];
        end
    end

endmodule

`default_nettype wire
