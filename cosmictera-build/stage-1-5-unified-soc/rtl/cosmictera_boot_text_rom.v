// ============================================================================
// cosmictera_boot_text_rom.v — Compact 4,096 x 12-bit Boot Screen Text ROM
// (Stage 1.5 Optimization: LUT3 column decode + 7-bit row address adder)
// ============================================================================

`default_nettype none

module cosmictera_boot_text_rom #(
    parameter TEXT_HEX = "boot_text_rom.hex"
) (
    input  wire        clk,
    input  wire [7:0]  la_col,          // 0..159
    input  wire [6:0]  la_row,          // 0..89
    output reg  [11:0] data             // {attr[3:0], glyph[7:0]}
);

    // For la_col in 0..159, (la_col >= 96) is simply la_col[7] | (la_col[6] & la_col[5])
    wire in_r5_cols = la_col[7] | (la_col[6] & la_col[5]);
    reg [4:0] rom_row;
    reg       force_blank;

    always @* begin
        rom_row     = 5'd0;
        force_blank = 1'b0;
        case (la_row)
            7'd2 : rom_row = 5'd0;
            7'd4 : rom_row = 5'd1;
            7'd20: rom_row = 5'd2;
            7'd34: rom_row = 5'd3;
            7'd36: rom_row = 5'd4;
            7'd41: rom_row = 5'd5;
            7'd44: rom_row = 5'd6;
            7'd46: rom_row = 5'd7;
            7'd48: rom_row = 5'd8;
            7'd54: rom_row = 5'd9;
            7'd56: begin rom_row = 5'd22; force_blank = ~in_r5_cols; end
            7'd57: rom_row = 5'd10;
            7'd59: begin rom_row = 5'd23; force_blank = ~in_r5_cols; end
            7'd60: begin rom_row = 5'd11; force_blank =  in_r5_cols; end
            7'd61: begin rom_row = 5'd24; force_blank = ~in_r5_cols; end
            7'd63: rom_row = 5'd12;
            7'd65: begin rom_row = 5'd11; force_blank = ~in_r5_cols; end
            7'd66: begin rom_row = 5'd13; force_blank =  in_r5_cols; end
            7'd67: begin rom_row = 5'd13; force_blank = ~in_r5_cols; end
            7'd69: rom_row = 5'd14;
            7'd71: rom_row = 5'd15;
            7'd75: rom_row = 5'd16;
            7'd77: rom_row = 5'd17;
            7'd79: rom_row = 5'd18;
            7'd81: rom_row = 5'd19;
            7'd82: rom_row = 5'd20;
            7'd85: rom_row = 5'd21;
            default: force_blank = 1'b1;
        endcase
    end

    // rom_row * 160 + la_col = ((rom_row * 5) << 5) | la_col[4:0] + (la_col[7:5] << 5)
    wire [6:0]  row_x5   = {rom_row, 2'b00} + {2'b00, rom_row};
    wire [6:0]  addr_hi  = row_x5 + {4'd0, la_col[7:5]};
    wire [11:0] rom_addr = {addr_hi, la_col[4:0]};

    reg [11:0] rom [0:4095];
    initial if (TEXT_HEX != "") $readmemh(TEXT_HEX, rom);

    reg [11:0] rom_q;
    reg        blank_q;
    always @(posedge clk) begin
        rom_q   <= rom[rom_addr];
        blank_q <= force_blank;
    end

    always @* begin
        data = blank_q ? 12'h020 : rom_q;
    end

endmodule

`default_nettype wire
