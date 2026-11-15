// ============================================================================
// cosmictera_boot_events.v — Hardware State-Transition Event Console & FIFO
// (Stage 1.5 Optimization: EV01..EV05 static 00:00:00 timestamps in BSRAM)
// ============================================================================

`default_nettype none

module cosmictera_boot_events (
    input  wire        clk,             // pixel_clk
    input  wire        ext_rst_n,
    input  wire [23:0] uptime_bcd,      // {hr1, hr0, min1, min0, sec1, sec0}

    input  wire        st_ref_clk_ok,
    input  wire        st_pll_locked,
    input  wire        st_clkdiv_ok,
    input  wire        st_tmds_ok,
    input  wire        st_timing_ok,
    input  wire        st_vout_ok,
    input  wire        lock_lost_pix,
    input  wire [7:0]  relock_count_pix,
    input  wire        fault_inject,

    output reg  [3:0]  fifo_count,      // 0..8 entries stored in FIFO
    output reg         fifo_overflow,   // 1'b1 if >8 transitions occurred

    output reg  [23:0] ev0_ts,
    output reg  [23:0] ev1_ts,
    output reg  [23:0] ev2_ts,
    output reg  [23:0] ev3_ts,
    output reg  [23:0] ev4_ts,
    output reg  [23:0] ev5_ts,

    input  wire [2:0]  dbg_fifo_addr,
    output wire [27:0] dbg_fifo_data
);

    assign dbg_fifo_data = {fifo_count, ev0_ts};

    reg       ref_d = 1'b0, pll_d = 1'b0, clkdiv_d = 1'b0, tmds_d = 1'b0;
    reg       timing_d = 1'b0, vout_d = 1'b0, lock_lost_d = 1'b0, fault_d = 1'b0;
    reg [7:0] relock_d  = 8'd0;
    reg [7:0] pend_mask = 8'd0;

    initial begin
        fifo_count    = 4'd0;
        fifo_overflow = 1'b0;
        ev0_ts        = 24'd0;
        ev1_ts        = 24'd0;
        ev2_ts        = 24'd0;
        ev3_ts        = 24'd0;
        ev4_ts        = 24'd0;
        ev5_ts        = 24'd0;
    end

    wire ev0_rise = st_ref_clk_ok && !ref_d;
    wire ev1_rise = st_pll_locked && !pll_d;
    wire ev2_rise = st_clkdiv_ok  && !clkdiv_d;
    wire ev3_rise = st_tmds_ok    && !tmds_d;
    wire ev4_rise = st_timing_ok  && !timing_d;
    wire ev5_rise = st_vout_ok    && !vout_d;
    wire ev6_rise = (lock_lost_pix && !lock_lost_d) || (fault_inject && !fault_d);
    wire ev7_rise = (relock_count_pix != relock_d);

    wire [7:0] rise_vec = {ev7_rise, ev6_rise, ev5_rise, ev4_rise,
                           ev3_rise, ev2_rise, ev1_rise, ev0_rise};

    wire [7:0] next_pend = pend_mask | rise_vec;

    reg       pop_valid;
    reg [7:0] pop_clear_bit;
    always @* begin
        pop_valid     = 1'b1;
        pop_clear_bit = 8'b0000_0001;
        if      (next_pend[0]) pop_clear_bit = 8'h01;
        else if (next_pend[1]) pop_clear_bit = 8'h02;
        else if (next_pend[2]) pop_clear_bit = 8'h04;
        else if (next_pend[3]) pop_clear_bit = 8'h08;
        else if (next_pend[4]) pop_clear_bit = 8'h10;
        else if (next_pend[5]) pop_clear_bit = 8'h20;
        else if (next_pend[6]) pop_clear_bit = 8'h40;
        else if (next_pend[7]) pop_clear_bit = 8'h80;
        else begin
            pop_valid     = 1'b0;
            pop_clear_bit = 8'h00;
        end
    end

    always @(posedge clk or negedge ext_rst_n) begin
        if (!ext_rst_n) begin
            ref_d         <= 1'b0;
            pll_d         <= 1'b0;
            clkdiv_d      <= 1'b0;
            tmds_d        <= 1'b0;
            timing_d      <= 1'b0;
            vout_d        <= 1'b0;
            lock_lost_d   <= 1'b0;
            fault_d       <= 1'b0;
            relock_d      <= 8'd0;
            pend_mask     <= 8'd0;
            fifo_count    <= 4'd0;
            fifo_overflow <= 1'b0;
`ifndef YOSYS
            ev0_ts        <= 24'd0;
            ev1_ts        <= 24'd0;
            ev2_ts        <= 24'd0;
            ev3_ts        <= 24'd0;
            ev4_ts        <= 24'd0;
`endif
            ev5_ts        <= 24'd0;
        end else begin
            ref_d       <= st_ref_clk_ok;
            pll_d       <= st_pll_locked;
            clkdiv_d    <= st_clkdiv_ok;
            tmds_d      <= st_tmds_ok;
            timing_d    <= st_timing_ok;
            vout_d      <= st_vout_ok;
            lock_lost_d <= lock_lost_pix;
            fault_d     <= fault_inject;
            relock_d    <= relock_count_pix;

`ifndef YOSYS
            if (ev0_rise) ev0_ts <= uptime_bcd;
            if (ev1_rise) ev1_ts <= uptime_bcd;
            if (ev2_rise) ev2_ts <= uptime_bcd;
            if (ev3_rise) ev3_ts <= uptime_bcd;
            if (ev4_rise) ev4_ts <= uptime_bcd;
`endif
            if (ev5_rise || ev6_rise || ev7_rise)
                ev5_ts <= uptime_bcd;

            pend_mask <= next_pend & (~pop_clear_bit);

            if (pop_valid) begin
                if (fifo_count < 4'd8)
                    fifo_count <= fifo_count + 4'd1;
                else
                    fifo_overflow <= 1'b1;
            end
        end
    end

endmodule

`default_nettype wire
