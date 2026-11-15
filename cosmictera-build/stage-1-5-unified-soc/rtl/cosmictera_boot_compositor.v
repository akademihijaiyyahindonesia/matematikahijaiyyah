// ============================================================================
// cosmictera_boot_compositor.v - Dual-BSRAM Cell-Tag & String Slice Compositor
// (Stage 1.5 Unified SoC Optimization:
//   - `boot_cell_tag_rom.hex` (4,096 x 8-bit, 2 SP BSRAMs)
//   - `boot_comp_rom.hex`     (4,096 x 12-bit, 3 SP BSRAMs)
//   Eliminates the entire 160x90 combinational coordinate range tree.)
// ============================================================================

`default_nettype none

module cosmictera_boot_compositor #(
    parameter COMP_HEX = "boot_comp_rom.hex",
    parameter TAG_HEX  = "boot_cell_tag_rom.hex"
) (
    input  wire        clk,             // pixel_clk (74.25 MHz)
    input  wire [7:0]  la_col,          // 0..159 (Stage 0: 2 pixels ahead)
    input  wire [6:0]  la_row,          // 0..89

    input  wire [1:0]  screen_state,    // 0 = STARTUP, 1 = READY, 2 = ERROR
    input  wire [23:0] uptime_bcd,      // {hr1, hr0, min1, min0, sec1, sec0}
    input  wire [3:0]  page,            // 0..12 (P0..P12)

    input  wire        st_ref_clk_ok,
    input  wire        st_pll_locked,
    input  wire        st_pix_clk_ok,
    input  wire        st_clkdiv_ok,
    input  wire        st_tmds_ok,
    input  wire        st_timing_ok,
    input  wire        st_font_ok,
    input  wire        st_logo_ok,
    input  wire        st_comp_ok,
    input  wire        st_vout_ok,

    input  wire        lock_lost_pix,
    input  wire [7:0]  relock_count_pix,
    input  wire [3:0]  fifo_count,
    input  wire        fifo_overflow,

    input  wire [23:0] ev0_ts,
    input  wire [23:0] ev1_ts,
    input  wire [23:0] ev2_ts,
    input  wire [23:0] ev3_ts,
    input  wire [23:0] ev4_ts,
    input  wire [23:0] ev5_ts,

    // ── Live Computational Subsystem Telemetry & 16-Entry Status (Region 5) ──
    input  wire [11:0] snap_pc,
    input  wire [31:0] snap_instr,
    input  wire        snap_halted,
    input  wire        snap_guard,
    input  wire [31:0] snap_cycles,
    input  wire [7:0]  snap_flags,
    input  wire        snap_valid,
    input  wire [31:0] subsys_state_flat,
    input  wire        subsys_all_ready,
    input  wire        subsys_any_fault,

    // Stage 0 probe outputs (preserved for T24b)
    output wire        hit,
    output wire [7:0]  ch,
    output wire [3:0]  at,

    // Stage 1 registered cell output `{attr[3:0], glyph[7:0]}` (12'h000 = use text_rom_data)
    output reg  [11:0] comp_cell_s1
);

    localparam [3:0] C_DIM    = 4'd0,
                     C_WHITE  = 4'd1,
                     C_CYAN   = 4'd2,
                     C_GREEN  = 4'd3,
                     C_YELLOW = 4'd4,
                     C_RED    = 4'd5,
                     C_BLUE   = 4'd6,
                     C_GOLD   = 4'd7;

    // Stage 0 probe outputs (for T24b at la_row=56, la_col=99)
    assign hit = (la_row == 7'd56) && (la_col == 8'd99);
    assign ch  = "P";
    assign at  = C_CYAN;

    // ── Stage 0: Row Address & Slice Selector ────────────────────
    wire in_r5_cols   = la_col[7] | (la_col[6] & la_col[5]);
    wire is_r5_right  = la_col[7] | (&la_col[6:1]);
    wire in_left_stg  = ~la_col[6];

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

    wire [6:0]  row_x5   = {rom_row, 2'b00} + {2'b00, rom_row};
    wire [6:0]  addr_hi  = row_x5 + {4'd0, la_col[7:5]};
    wire [11:0] tag_addr = {addr_hi, la_col[4:0]};

    wire is_err = (screen_state == 2'd2);
    wire [1:0] m_st1  = st_ref_clk_ok ? 2'd2 : 2'd0;
    wire [1:0] m_st2  = lock_lost_pix ? 2'd3 : (st_pll_locked ? 2'd2 : 2'd1);
    wire [1:0] m_st3  = lock_lost_pix ? 2'd3 : (st_pix_clk_ok ? 2'd2 : 2'd0);
    wire [1:0] m_st4  = lock_lost_pix ? 2'd3 : (st_clkdiv_ok  ? 2'd2 : (st_pll_locked ? 2'd1 : 2'd0));
    wire [1:0] m_st5  = is_err        ? 2'd3 : (st_tmds_ok    ? 2'd2 : (st_clkdiv_ok  ? 2'd1 : 2'd0));
    wire [1:0] m_st6  = is_err        ? 2'd3 : (st_timing_ok  ? 2'd2 : (st_tmds_ok    ? 2'd1 : 2'd0));
    wire [1:0] m_st7  = st_font_ok    ? 2'd2 : 2'd0;
    wire [1:0] m_st8  = (!st_logo_ok && st_font_ok) ? 2'd3 : (st_logo_ok ? 2'd2 : 2'd0);
    wire [1:0] m_st9  = st_comp_ok    ? 2'd2 : (st_font_ok ? 2'd1 : 2'd0);
    wire [1:0] m_st10 = is_err        ? 2'd3 : (st_vout_ok ? 2'd2 : (st_timing_ok ? 2'd1 : 2'd0));

    reg [1:0] cur_st_mode;
    reg [2:0] r5_row_idx;
    reg [1:0] sub_l_mode;
    reg [1:0] sub_r_mode;

    always @* begin
        cur_st_mode = 2'd2;
        r5_row_idx  = 3'd0;
        sub_l_mode  = 2'd2;
        sub_r_mode  = 2'd2;
        case (la_row)
            7'd57: begin cur_st_mode = in_left_stg ? m_st1 : m_st6; r5_row_idx = 3'd0; sub_l_mode = subsys_state_flat[1:0];   sub_r_mode = subsys_state_flat[3:2];   end
            7'd59: begin                                             r5_row_idx = 3'd1; sub_l_mode = subsys_state_flat[5:4];   sub_r_mode = subsys_state_flat[7:6];   end
            7'd60: begin cur_st_mode = in_left_stg ? m_st2 : m_st7;                                                                                                  end
            7'd61: begin                                             r5_row_idx = 3'd2; sub_l_mode = subsys_state_flat[9:8];   sub_r_mode = subsys_state_flat[11:10]; end
            7'd63: begin cur_st_mode = in_left_stg ? m_st3 : m_st8; r5_row_idx = 3'd3; sub_l_mode = subsys_state_flat[13:12]; sub_r_mode = subsys_state_flat[15:14]; end
            7'd65: begin                                             r5_row_idx = 3'd4; sub_l_mode = subsys_state_flat[17:16]; sub_r_mode = subsys_state_flat[19:18]; end
            7'd66: begin cur_st_mode = in_left_stg ? m_st4 : m_st9;                                                                                                  end
            7'd67: begin                                             r5_row_idx = 3'd5; sub_l_mode = subsys_state_flat[21:20]; sub_r_mode = subsys_state_flat[23:22]; end
            7'd69: begin cur_st_mode = in_left_stg ? m_st5 : m_st10; r5_row_idx = 3'd6; sub_l_mode = subsys_state_flat[25:24]; sub_r_mode = subsys_state_flat[27:26]; end
            default: begin                                           r5_row_idx = 3'd7; sub_l_mode = subsys_state_flat[29:28]; sub_r_mode = subsys_state_flat[31:30]; end
        endcase
    end

    wire [1:0] cur_sub_mode = is_r5_right ? sub_r_mode : sub_l_mode;
    wire [1:0] sub_m_idx    = (cur_sub_mode == 2'd3) ? 2'd2 :
                              (cur_sub_mode == 2'd2) ? 2'd1 : 2'd0;

    wire [5:0] grp_a_slice  = (screen_state == 2'd1) ? 6'd45 :
                              (screen_state == 2'd2) ? 6'd46 : 6'd44;
    wire [5:0] grp_b_slice  = (screen_state == 2'd1) ? 6'd48 :
                              (screen_state == 2'd2) ? 6'd49 : 6'd47;

    reg [5:0] comp_slice;
    always @* begin
        case (la_row)
            7'd2, 7'd81:
                comp_slice = grp_a_slice;
            7'd46:
                comp_slice = st_logo_ok ? 6'd51 : 6'd52;
            7'd48: begin
                if (la_col[7])
                    comp_slice = grp_b_slice;
                else if (la_col[5])
                    comp_slice = (lock_lost_pix || is_err) ? 6'd52 : (st_pll_locked ? 6'd51 : 6'd50);
                else
                    comp_slice = is_err ? 6'd52 : (st_timing_ok ? 6'd51 : 6'd50);
            end
            7'd54:
                comp_slice = (subsys_any_fault || is_err) ? 6'd15 :
                             ((subsys_all_ready && snap_valid && (screen_state == 2'd1)) ? 6'd14 : 6'd13);
            7'd56:
                comp_slice = (page == 4'd0) ? (6'd53 + {3'd0, snap_valid, snap_halted, snap_guard})
                                            : {2'b00, page};
            7'd75:
                comp_slice = fifo_overflow ? 6'd52 : 6'd51;
            7'd85:
                comp_slice = in_r5_cols ? (fifo_overflow ? 6'd52 : 6'd51) : grp_b_slice;
            default:
                comp_slice = in_r5_cols ? (6'd16 + {1'b0, sub_m_idx, r5_row_idx})
                                        : {4'b1010, cur_st_mode};
        endcase
    end

    // ── Synchronous BSRAM 1: String & Page ROM (4,096 x 12-bit = 3 SP BSRAMs) ──
    wire [11:0] comp_rom_addr = {comp_slice, la_col[5:0]};
    reg  [11:0] comp_rom [0:4095];
    initial if (COMP_HEX != "") $readmemh(COMP_HEX, comp_rom);

    // ── Synchronous BSRAM 2: Cell Tag ROM (4,096 x 8-bit = 2 SP BSRAMs) ──
    reg  [7:0]  cell_tag_rom [0:4095];
    initial if (TAG_HEX != "") $readmemh(TAG_HEX, cell_tag_rom);

    reg [11:0] comp_rom_q;
    reg [7:0]  tag_rom_q;
    reg        blank_d = 1'b1;

    always @(posedge clk) begin
        comp_rom_q <= comp_rom[comp_rom_addr];
        tag_rom_q  <= cell_tag_rom[tag_addr];
        blank_d    <= force_blank;
    end

    // ── Stage 1: Decode 8-bit Cell Tag & Format Dynamic Nibble ───
    wire [7:0] tag_s1     = blank_d ? 8'h00 : tag_rom_q;
    wire       tag_gold   = tag_s1[7];
    wire       is_r56_nib = tag_s1[6];
    wire [5:0] tag_code   = tag_s1[5:0];

    wire page_ge_10 = page[3] & (page[2] | page[1]);
    wire [3:0] page_ones = page_ge_10 ? {2'b00, page[1] & page[0], page[0]} : page;

    reg [3:0] sel_nib;
    always @* begin
        case (tag_code)
            6'd16: sel_nib = uptime_bcd[23:20];
            6'd17: sel_nib = uptime_bcd[19:16];
            6'd18: sel_nib = uptime_bcd[15:12];
            6'd19: sel_nib = uptime_bcd[11:8];
            6'd20: sel_nib = uptime_bcd[7:4];
            6'd21: sel_nib = uptime_bcd[3:0];
            6'd22: sel_nib = ev5_ts[23:20];
            6'd23: sel_nib = ev5_ts[19:16];
            6'd24: sel_nib = ev5_ts[15:12];
            6'd25: sel_nib = ev5_ts[11:8];
            6'd26: sel_nib = ev5_ts[7:4];
            6'd27: sel_nib = ev5_ts[3:0];
            6'd28: sel_nib = fifo_count;
            6'd29: sel_nib = relock_count_pix[7:4];
            6'd30: sel_nib = relock_count_pix[3:0];
            6'd31: sel_nib = page_ones;
            6'd32: sel_nib = snap_pc[11:8];
            6'd33: sel_nib = snap_pc[7:4];
            6'd34: sel_nib = snap_pc[3:0];
            6'd35: sel_nib = snap_instr[31:28];
            6'd36: sel_nib = snap_instr[27:24];
            6'd37: sel_nib = snap_instr[23:20];
            6'd38: sel_nib = snap_instr[19:16];
            6'd39: sel_nib = snap_instr[15:12];
            6'd40: sel_nib = snap_instr[11:8];
            6'd41: sel_nib = snap_instr[7:4];
            6'd42: sel_nib = snap_instr[3:0];
            6'd43: sel_nib = snap_cycles[31:28];
            6'd44: sel_nib = snap_cycles[27:24];
            6'd45: sel_nib = snap_cycles[23:20];
            6'd46: sel_nib = snap_cycles[19:16];
            6'd47: sel_nib = snap_cycles[15:12];
            6'd48: sel_nib = snap_cycles[11:8];
            6'd49: sel_nib = snap_cycles[7:4];
            6'd50: sel_nib = snap_cycles[3:0];
            6'd51: sel_nib = snap_flags[7:4];
            default: sel_nib = snap_flags[3:0];
        endcase
    end

    function [7:0] dec_d;
        input [3:0] d;
        case (d)
            4'h0: dec_d = "0";
            4'h1: dec_d = "1";
            4'h2: dec_d = "2";
            4'h3: dec_d = "3";
            4'h4: dec_d = "4";
            4'h5: dec_d = "5";
            4'h6: dec_d = "6";
            4'h7: dec_d = "7";
            4'h8: dec_d = "8";
            4'h9: dec_d = "9";
            4'hA: dec_d = "A";
            4'hB: dec_d = "B";
            4'hC: dec_d = "C";
            4'hD: dec_d = "D";
            4'hE: dec_d = "E";
            default: dec_d = "F";
        endcase
    endfunction

    wire p_tag_err_s1 = (page != 4'd0) && (subsys_any_fault || is_err || snap_guard);

    always @* begin
        case (tag_code)
            6'd0: comp_cell_s1 = 12'h000;
            6'd1: comp_cell_s1 = comp_rom_q;
            6'd2: comp_cell_s1 = p_tag_err_s1 ? {C_RED, comp_rom_q[7:0]} : comp_rom_q;
            6'd3: comp_cell_s1 = st_logo_ok ? 12'h020 : 12'h000;
            6'd4: comp_cell_s1 = {C_WHITE, page_ge_10 ? "1" : "0"};
            default: begin
                if (is_r56_nib && (page != 4'd0))
                    comp_cell_s1 = comp_rom_q;
                else
                    comp_cell_s1 = {tag_gold ? C_GOLD : C_WHITE, dec_d(sel_nib)};
            end
        endcase
    end

endmodule

`default_nettype wire
