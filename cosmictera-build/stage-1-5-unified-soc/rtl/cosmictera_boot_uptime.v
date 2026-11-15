// ============================================================================
// cosmictera_boot_uptime.v — Monotonic 1 Hz Hardware Uptime Counter & CDC
// ============================================================================

`default_nettype none

module cosmictera_boot_uptime #(
    parameter integer CLKS_PER_SEC = 27_000_000
) (
    input  wire        clk_27m,
    input  wire        rst_n,
    input  wire        pixel_clk,
    output reg  [23:0] uptime_bcd_pix, // {hr1, hr0, min1, min0, sec1, sec0}
    output reg         sec_tick_pix    // 1-cycle pulse in pixel_clk on each second update
);

    localparam integer CNT_W = $clog2(CLKS_PER_SEC + 1);

    reg [CNT_W-1:0] sub_cnt      = {CNT_W{1'b0}};
    reg [3:0]       sec0         = 4'd0, sec1 = 4'd0;
    reg [3:0]       min0         = 4'd0, min1 = 4'd0;
    reg [3:0]       hr0          = 4'd0, hr1  = 4'd0;
    reg [23:0]      bcd_hold_27m = 24'd0;
    reg             tog_27m      = 1'b0;
    reg             sim_freeze   = 1'b0;

    initial begin
        uptime_bcd_pix = 24'd0;
        sec_tick_pix   = 1'b0;
    end

    always @(posedge clk_27m or negedge rst_n) begin
        if (!rst_n) begin
            sub_cnt      <= {CNT_W{1'b0}};
            sec0         <= 4'd0; sec1 <= 4'd0;
            min0         <= 4'd0; min1 <= 4'd0;
            hr0          <= 4'd0; hr1  <= 4'd0;
            bcd_hold_27m <= 24'd0;
            tog_27m      <= 1'b0;
        end else if (!sim_freeze) begin
            if (sub_cnt >= CLKS_PER_SEC[CNT_W-1:0] - 1'b1) begin
                sub_cnt <= {CNT_W{1'b0}};
                if (sec0 == 4'd9) begin
                    sec0 <= 4'd0;
                    if (sec1 == 4'd5) begin
                        sec1 <= 4'd0;
                        if (min0 == 4'd9) begin
                            min0 <= 4'd0;
                            if (min1 == 4'd5) begin
                                min1 <= 4'd0;
                                if (hr0 == 4'd9) begin
                                    hr0 <= 4'd0;
                                    if (hr1 != 4'd9)
                                        hr1 <= hr1 + 4'd1;
                                end else begin
                                    hr0 <= hr0 + 4'd1;
                                end
                            end else begin
                                min1 <= min1 + 4'd1;
                            end
                        end else begin
                            min0 <= min0 + 4'd1;
                        end
                    end else begin
                        sec1 <= sec1 + 4'd1;
                    end
                end else begin
                    sec0 <= sec0 + 4'd1;
                end
            end else begin
                sub_cnt <= sub_cnt + 1'b1;
            end

            if (sub_cnt == {CNT_W{1'b0}}) begin
                bcd_hold_27m <= {hr1, hr0, min1, min0, sec1, sec0};
                tog_27m      <= ~tog_27m;
            end
        end
    end

    reg tog_p1 = 1'b0, tog_p2 = 1'b0, tog_p3 = 1'b0;
    always @(posedge pixel_clk or negedge rst_n) begin
        if (!rst_n) begin
            tog_p1         <= 1'b0;
            tog_p2         <= 1'b0;
            tog_p3         <= 1'b0;
            uptime_bcd_pix <= 24'd0;
            sec_tick_pix   <= 1'b0;
        end else begin
            tog_p1 <= tog_27m;
            tog_p2 <= tog_p1;
            tog_p3 <= tog_p2;
            if (tog_p2 ^ tog_p3) begin
                uptime_bcd_pix <= bcd_hold_27m;
                sec_tick_pix   <= 1'b1;
            end else begin
                sec_tick_pix   <= 1'b0;
            end
        end
    end

endmodule

`default_nettype wire
