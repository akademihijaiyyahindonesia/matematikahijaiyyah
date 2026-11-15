// hcpu_page_key.v — one button, two meanings.
//
// There is no keyboard on this board and none in this design. The audit that
// opened M5 found exactly one human input on the HDMI slot: `mode_key`, pin
// 88, a single active-low button. F1..F10 is not available and pretending
// otherwise would be inventing an input device.
//
// So the button carries both actions the owner asked for:
//
//   short press   next page, wrapping 0..PAGES-1
//   long  press   back to page 0, from wherever you are
//
// ── the press is measured on release, not on contact ────────────
// Holding the button down is not a short press that later becomes a long
// one: nothing happens until the button comes back up, and then the length
// of the press decides which action it was. A press that passes the long
// threshold fires immediately and marks itself spent, so releasing it does
// not also advance the page.
//
// ── debounce, and the number behind it ──────────────────────────
// A mechanical contact bounces for single-digit milliseconds. At 74.25 MHz
// one millisecond is 74,250 cycles, so the counter is sized in cycles rather
// than in guesses and both thresholds are parameters: the board build states
// them in its own clock, and a bench can shorten them to something it can
// simulate without running for a wall-clock second.

`default_nettype none

module hcpu_page_key #(
    parameter integer DEBOUNCE = 750_000,      // ~10 ms at 74.25 MHz
    parameter integer LONG     = 74_250_000,   // ~1 s
    parameter integer PAGES    = 9
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       key_n,          // active low, straight from the pad
    output reg  [3:0] page
);

    // ── the counters are as wide as their thresholds, and no wider ──
    // Both were `reg [31:0]` because that is the width `integer` suggests,
    // not because anything needed it. Measured on the synthesised netlist,
    // this module then cost 471 cells -- 168 LUT, 164 ALU, 127 DFF -- for a
    // debounced button, more than the painter, the telemetry and the
    // renderer put together. Two 32-bit counters compared against two 32-bit
    // constants is where all of it went.
    //
    // Derived from the parameters rather than written down, so a build that
    // changes a threshold gets the width that threshold needs. At the board's
    // numbers that is 20 bits and 27; at the bench's, 3 and 6.
    //
    // Behaviour is untouched: short press, long press, debounce, wrap and the
    // rule that a long press does not also advance on release all stand. This
    // is the same design in fewer bits.
    localparam integer DEB_W  = $clog2(DEBOUNCE + 1);
    localparam integer LONG_W = $clog2(LONG + 1);

    localparam [DEB_W-1:0]  DEB_MAX  = DEBOUNCE;
    localparam [LONG_W-1:0] LONG_MAX = LONG;

    // Two flops before anything looks at it: the button is asynchronous to
    // every clock in this design.
    reg key_s1, key_s2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin key_s1 <= 1'b1; key_s2 <= 1'b1; end
        else        begin key_s1 <= key_n; key_s2 <= key_s1; end
    end
    wire pressed_raw = ~key_s2;

    reg [DEB_W-1:0] stable_cnt;
    reg             pressed;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stable_cnt <= {DEB_W{1'b0}};
            pressed    <= 1'b0;
        end else if (pressed_raw != pressed) begin
            if (stable_cnt >= DEB_MAX) begin
                pressed    <= pressed_raw;
                stable_cnt <= {DEB_W{1'b0}};
            end else begin
                stable_cnt <= stable_cnt + 1'b1;
            end
        end else begin
            stable_cnt <= {DEB_W{1'b0}};
        end
    end

    reg              pressed_d;
    reg [LONG_W-1:0] held;
    reg              spent;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            page      <= 4'd0;
            pressed_d <= 1'b0;
            held      <= {LONG_W{1'b0}};
            spent     <= 1'b0;
        end else begin
            pressed_d <= pressed;

            if (pressed && !pressed_d) begin        // contact
                held  <= {LONG_W{1'b0}};
                spent <= 1'b0;
            end else if (pressed) begin
                if (held < LONG_MAX) held <= held + 1'b1;
                if (held == LONG_MAX - 1 && !spent) begin
                    page  <= 4'd0;                  // long: home, at once
                    spent <= 1'b1;
                end
            end else if (!pressed && pressed_d) begin   // release
                if (!spent)
                    page <= (page == PAGES - 1) ? 4'd0 : page + 4'd1;
            end
        end
    end

endmodule

`default_nettype wire
