// hcpu_text_ram.v — the screen as characters, not as pixels.
//
// ── why this is not a framebuffer, and never will be on this board ──
// 1280x720 at one bit per pixel is 921,600 bits. The Tang Nano 20K has 46
// BSRAM blocks and 18 of them are already spent on instruction memory, data
// memory, the letter ROM and the SD sector buffer. A framebuffer is not
// tight here, it is impossible by a factor of six.
//
// 8x8 cells turn the same screen into 160 x 90 = 14,400 characters. At 16
// bits each that is 230,400 bits, which fits in what is left. The owner set
// this geometry on 15 September 2026, and the arithmetic above is the reason
// it is a text display rather than a graphical one.
//
// ── sixteen bits per cell, and what the other eight are for ──────
//
//   [7:0]   the character, ASCII, and only uppercase has glyphs
//   [11:8]  colour index, resolved to RGB by the renderer
//   [15:12] unused, reads back as written
//
// Colour lives beside the character rather than being derived from position
// because a status field changes colour without moving: GREEN for RUNNING and
// RED for ERROR are the same cell on the same row. Deriving it from x and y
// would mean the layout decides the colour, which is exactly backwards for a
// monitor whose whole job is to show state.
//
// ── one writer, one reader, and they never wait for each other ───
// The renderer reads one cell per eight pixels, all frame long. The painter
// writes whenever it has something new. Simple dual port: separate clocked
// read and write, no arbitration, no stall. Both sides run on pixel_clk, so
// there is no crossing here -- the crossing happens upstream, where telemetry
// leaves the CPU's clock.
//
// A read and a write to the SAME address in the same cycle returns the OLD
// value. That is read-before-write, it is what BSRAM does, and it does not
// matter: a cell the painter is writing is a cell whose previous character
// was displayed one frame ago and whose new one will be displayed on the
// next. Nothing here is a race; it is a frame of latency on a screen that
// refreshes sixty times a second.

`default_nettype none

module hcpu_text_ram #(
    parameter COLS  = 160,
    parameter ROWS  = 90,
    parameter DEPTH = 16384,      // 14,400 rounded up to a power of two
    parameter AW    = 14,
    // EMPTY BY DEFAULT, and every instantiation states the path. Both yosys
    // and iverilog elaborate an uninstantiated module as a root of its own,
    // with default parameters -- so a default that names a real file is read
    // from whatever directory the build happens to run in, and the two builds
    // run from different ones. Two levels apart, in fact, which no single
    // relative default can satisfy. An empty string reads nothing and copies
    // nothing; the file stays in rtl/ and each caller says where that is.
    parameter INIT_HEX = ""
) (
    input  wire           clk,

    // painter side
    input  wire           we,
    input  wire [AW-1:0]  waddr,
    input  wire [15:0]    wdata,

    // renderer side
    input  wire [AW-1:0]  raddr,
    output reg  [15:0]    rdata
);

    // Not named `cell`: that is a Verilog keyword (config declarations),
    // and iverilog rejects the whole port list rather than the one line.
    reg [15:0] screen [0:DEPTH-1];

    // The layout arrives as initial contents rather than being painted.
    // Almost every cell on this screen is a label, a rule, or the words NOT
    // INSTRUMENTED, and none of them ever change; drawing them from logic
    // would cost a string engine to produce a picture identical in frame 60
    // and frame 216,000. rtl/scripts/gen_dashboard.py writes the image and
    // the live-field addresses together, so a label cannot move away from
    // its own value.
    //
    // An uninitialised text RAM powers up holding whatever the BSRAM holds,
    // which on a screen reads as noise and looks like a broken renderer. This
    // way the first frame after configuration is already the dashboard.
    initial if (INIT_HEX != "") $readmemh(INIT_HEX, screen);

    always @(posedge clk) begin
        if (we) screen[waddr] <= wdata;
        rdata <= screen[raddr];
    end

endmodule

`default_nettype wire
