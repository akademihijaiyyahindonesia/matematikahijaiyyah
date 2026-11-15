// ============================================================================
// Video timing generator — hcpu_video_timing.v
// First piece toward a live display for Tang Nano 20K (40-pin RGB LCD /
// HDMI) — the board is not in hand yet (arrives 2026-09-08), so this is
// built and verified as far as simulation alone can take it: the counting
// logic that produces hsync/vsync/data-enable at the right pixel/line
// positions. Wiring actual panel pins and picking a pixel clock the 27 MHz
// crystal (or the board's rPLL) can actually generate is a separate,
// hardware-specific step, not done here.
// (c) 2026 Maulana Amratulloh — HM-28-v1.2-HC18D / Tier 1.5
// ============================================================================
//
// Parameterized VESA-style timing: H_ACTIVE/H_FRONT/H_SYNC/H_BACK and the
// same four fields for V. Defaults are the published VESA 640x480@60Hz
// mode (industry standard, not invented here):
//
//   H: 640 active + 16 front porch + 96 sync + 48 back porch = 800/line
//   V: 480 active + 10 front porch +  2 sync + 33 back porch = 525/frame
//   800 x 525 x 60 Hz = 25,200,000 -- the standard's own ~25.175 MHz
//   pixel clock, rounded.
//
// `pixel_clk` is a single-rate clock already at the target pixel rate --
// generating 25.175 MHz (or any other mode's rate) from the board's 27 MHz
// crystal is exactly the "pick a pixel clock the hardware can generate"
// step the header above says is not done here; this module counts pixels
// and lines, it does not synthesize a clock.
//
// hsync/vsync polarity: NEGATIVE for this mode (VESA 640x480@60Hz's own
// standard polarity) -- HSYNC_POL/VSYNC_POL invert it for panels/modes
// that need the opposite.

`default_nettype none

module hcpu_video_timing #(
    parameter H_ACTIVE = 640,
    parameter H_FRONT  = 16,
    parameter H_SYNC   = 96,
    parameter H_BACK   = 48,
    parameter V_ACTIVE = 480,
    parameter V_FRONT  = 10,
    parameter V_SYNC   = 2,
    parameter V_BACK   = 33,
    parameter HSYNC_POL = 1'b0,   // 0 = active-low pulse (VESA 640x480@60 standard)
    parameter VSYNC_POL = 1'b0
) (
    input  wire        pixel_clk,
    input  wire        rst_n,

    output wire        hsync,
    output wire        vsync,
    output wire        de,          // data-enable: high while (x,y) is in the active area
    output wire [11:0] x,           // 0..H_ACTIVE-1 while de is high, else counting through blanking
    output wire [11:0] y,           // 0..V_ACTIVE-1 while de is high, else counting through blanking
    output wire        frame_tick,  // one pixel_clk pulse at the start of each frame (x==0 && y==0)

    // The raw counters, added for M5. `x` and `y` above are FORCED TO ZERO
    // outside the active area, which is right for anything that draws and
    // wrong for anything that must look ahead: a character generator has to
    // fetch the first cell of a line DURING the blanking that precedes it,
    // and a coordinate pinned at zero cannot say which line is coming. These
    // two never lie about where the beam is. Purely additive -- every
    // existing instantiation leaves them unconnected and is unchanged.
    output wire [11:0] h_count_o,
    output wire [11:0] v_count_o
);

    localparam H_TOTAL = H_ACTIVE + H_FRONT + H_SYNC + H_BACK;
    localparam V_TOTAL = V_ACTIVE + V_FRONT + V_SYNC + V_BACK;

    reg [11:0] h_count;
    reg [11:0] v_count;

    always @(posedge pixel_clk or negedge rst_n) begin
        if (!rst_n) begin
            h_count <= 12'd0;
            v_count <= 12'd0;
        end else begin
            if (h_count == H_TOTAL - 1) begin
                h_count <= 12'd0;
                v_count <= (v_count == V_TOTAL - 1) ? 12'd0 : v_count + 12'd1;
            end else begin
                h_count <= h_count + 12'd1;
            end
        end
    end

    // Sync pulses start right after the front porch and last H_SYNC/V_SYNC
    // counts -- the standard's own layout, active/front/sync/back in that
    // order every line and every frame.
    wire h_in_sync = (h_count >= H_ACTIVE + H_FRONT) &&
                      (h_count <  H_ACTIVE + H_FRONT + H_SYNC);
    wire v_in_sync = (v_count >= V_ACTIVE + V_FRONT) &&
                      (v_count <  V_ACTIVE + V_FRONT + V_SYNC);

    assign hsync = HSYNC_POL ? h_in_sync : ~h_in_sync;
    assign vsync = VSYNC_POL ? v_in_sync : ~v_in_sync;

    wire h_active = h_count < H_ACTIVE;
    wire v_active = v_count < V_ACTIVE;
    assign de = h_active && v_active;

    assign x = h_active ? h_count : 12'd0;
    assign y = v_active ? v_count : 12'd0;

    assign frame_tick = (h_count == 12'd0) && (v_count == 12'd0);

    assign h_count_o = h_count;
    assign v_count_o = v_count;

endmodule
