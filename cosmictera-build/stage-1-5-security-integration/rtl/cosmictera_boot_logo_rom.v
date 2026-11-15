// ============================================================================
// cosmictera_boot_logo_rom.v - Official COSMICTERA Chrome Orbit Logo Engine
// (Stage 1.5 Optimization: BSRAM 24x24 Header Emblem ROM `boot_emblem_rom.hex`
//  + BSRAM 512x184 Hero RLE Logo ROM `logo_rle_rom.hex`)
// ============================================================================

`default_nettype none

module cosmictera_boot_logo_rom #(
    parameter LOGO_HEX   = "logo_rle_rom.hex",
    parameter EMBLEM_HEX = "boot_emblem_rom.hex",
    parameter [11:0] LOGO_X0 = 12'd384,
    parameter [11:0] LOGO_Y0 = 12'd76,
    parameter [11:0] LOGO_W  = 12'd512,
    parameter [11:0] LOGO_H  = 12'd184
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [11:0] h_count,
    input  wire [11:0] v_count,
    input  wire        force_logo_fault,

    output wire        logo_rom_ok,
    output reg         logo_pixel_valid,
    output reg  [23:0] logo_pixel_rgb
);

    reg [8:0] rom [0:16383];
    initial if (LOGO_HEX != "") $readmemh(LOGO_HEX, rom);

    // Hero X: 384..895 -> h_count[11]==0 && h_count[10:7] in {3,4,5,6}
    wire in_hero_x = (h_count[11] == 1'b0) &&
                     ((h_count[10:7] == 4'd3) || (h_count[10:7] == 4'd4) ||
                      (h_count[10:7] == 4'd5) || (h_count[10:7] == 4'd6));

    // Hero Y: 76..259 -> v_count[11:9]==0 && v_count[8:2] in 19..64
    reg in_hero_y;
    always @* begin
        if (v_count[11:9] != 3'd0) in_hero_y = 1'b0;
        else case (v_count[8:2])
            7'd19, 7'd20, 7'd21, 7'd22, 7'd23, 7'd24, 7'd25, 7'd26, 7'd27, 7'd28, 7'd29, 7'd30, 7'd31, 7'd32, 7'd33, 7'd34, 7'd35, 7'd36, 7'd37, 7'd38, 7'd39, 7'd40, 7'd41, 7'd42, 7'd43, 7'd44, 7'd45, 7'd46, 7'd47, 7'd48, 7'd49, 7'd50, 7'd51, 7'd52, 7'd53, 7'd54, 7'd55, 7'd56, 7'd57, 7'd58, 7'd59, 7'd60, 7'd61, 7'd62, 7'd63, 7'd64: in_hero_y = 1'b1;
            default: in_hero_y = 1'b0;
        endcase
    end
    wire in_hero = in_hero_y && in_hero_x;

    wire is_y75     = (v_count == 12'd75);
    wire prime_cyc0 = is_y75 && (h_count == 12'd0);
    wire prime_cyc1 = is_y75 && (h_count == 12'd1);

    reg [13:0] rd_ptr;
    reg [4:0]  cur_code;
    reg [8:0]  cur_rem;
    reg        rom_ok_reg;

    wire advance_rle = in_hero && (cur_rem == 9'd1);
    wire [13:0] next_ptr = rd_ptr + 14'd1;
    wire [13:0] rom_addr = prime_cyc0  ? 14'd0 :
                           prime_cyc1  ? 14'd1 :
                           advance_rle ? next_ptr : rd_ptr;

    reg [8:0] rom_dout;
    always @(posedge clk) begin
        rom_dout <= rom[rom_addr];
    end

    wire [4:0] dout_code = rom_dout[8:4];
    wire [4:0] dout_cnt1 = {1'b0, rom_dout[3:0]} + 5'd1;
    wire [8:0] dout_len  = (dout_code == 5'd31) ? {dout_cnt1, 4'd0} : {4'd0, dout_cnt1};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_ptr     <= 14'd0;
            cur_code   <= 5'd0;
            cur_rem    <= 9'd1;
            rom_ok_reg <= 1'b1;
        end else if (prime_cyc0) begin
            rd_ptr <= 14'd0;
        end else if (prime_cyc1) begin
            cur_code   <= dout_code;
            cur_rem    <= dout_len;
            rd_ptr     <= 14'd1;
            rom_ok_reg <= (rom_dout != 9'h000);
        end else if (in_hero) begin
            if (cur_rem == 9'd1) begin
                cur_code <= dout_code;
                cur_rem  <= dout_len;
                rd_ptr   <= next_ptr;
            end else begin
                cur_rem  <= cur_rem - 9'd1;
            end
        end
    end

    assign logo_rom_ok = rom_ok_reg && (!force_logo_fault);

    wire [4:0] hero_pal_idx = (cur_code == 5'd31) ? 5'd0 : cur_code;
    reg [23:0] logo_rgb;
    always @* begin
        case (hero_pal_idx)
`include "logo_palette.vh"
        endcase
    end

    // 24x24 Header Mini-Emblem at x = 28..51, y = 18..41 via 4,096 x 4-bit BSRAM ROM
    reg [3:0] emblem_rom [0:4095];
    initial if (EMBLEM_HEX != "") $readmemh(EMBLEM_HEX, emblem_rom);

    reg [3:0] emb_code_q = 4'd0;
    always @(posedge clk) begin
        emb_code_q <= emblem_rom[{v_count[5:0], h_count[5:0]}];
    end

    wire emb_box      = (h_count[11:6] == 6'd0) && (v_count[11:6] == 6'd0);
    wire emblem_valid = emb_box && (emb_code_q != 4'd0);

    reg [23:0] emblem_rgb;
    always @* begin
        case (emb_code_q)
            4'd1: emblem_rgb = 24'h2dcd73;
            4'd2: emblem_rgb = 24'h14914e;
            4'd3: emblem_rgb = 24'hf6ce5f;
            4'd4: emblem_rgb = 24'hd69b2c;
            4'd5: emblem_rgb = 24'hf2f6fa;
            default: emblem_rgb = 24'h98a8b8;
        endcase
    end

    always @* begin
        if (in_hero && logo_rom_ok && (hero_pal_idx != 5'd0)) begin
            logo_pixel_valid = 1'b1;
            logo_pixel_rgb   = logo_rgb;
        end else if (emblem_valid) begin
            logo_pixel_valid = 1'b1;
            logo_pixel_rgb   = emblem_rgb;
        end else begin
            logo_pixel_valid = 1'b0;
            logo_pixel_rgb   = 24'h060c16;
        end
    end

endmodule

`default_nettype wire
