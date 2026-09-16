// hcpu_layout_rom.v — the parts of the screen that never change.
//
// The headline, the panel titles, the labels, the rules, and every field the
// hardware cannot report -- NOT INSTRUMENTED, spelled out, one cell at a
// time. None of it moves between frame 60 and frame 216,000, so none of it is
// written at run time and none of it needs a write port.
//
// That last clause is the whole reason this file exists. M5.2A held the same
// characters in a 16,384 x 16 text RAM that a painter wrote into, and the
// write port is what made it a RAM: eleven BSRAM blocks with a second port,
// placed between the CPU and the video path. nextpnr refused the design at
// 16,882 LUT4 where the same board places a control at 15,933.
//
// Twelve bits per cell, not sixteen: eight of character, four of colour. The
// spare four were free in a RAM word and are not free 14,400 times.
//
// The live fields are NOT here. hcpu_compositor.v decides those from the
// telemetry snapshot as the beam reaches them, and overrides whatever this
// ROM holds at those addresses -- which is a row of dots, so a compositor
// that ever stopped overriding would show dots rather than a stale number.

`default_nettype none

module hcpu_layout_rom #(
    // Empty by default, like every other memory image in this tree: both
    // yosys and iverilog elaborate an uninstantiated module as a root with
    // default parameters, and the two builds run from directories two levels
    // apart. Each caller says where the one file is.
    parameter LAYOUT_HEX = "",
    // FORTY-EIGHT ROWS, NOT NINETY, AND THE BOARD IS WHY. A 16,384 x 12 ROM
    // is 196,608 bits; yosys gave it ten SPX9 blocks, which hold 184,320.
    // The top of the screen was correct on the monitor and the bottom was
    // dense repeating stripes -- addresses with no memory behind them,
    // returning bits that became arbitrary glyph indices.
    //
    // The screen never needed the depth. Rows 0..31 carry the dashboard and
    // row 88 carries the footer; rows 32..83 are blank and cost nothing to
    // leave out. The caller maps the footer rows into the top of this array
    // and answers blank for everything else, so 7,680 cells hold a 14,400
    // cell screen.
    parameter DEPTH      = 8192,
    parameter AW         = 13
) (
    input  wire          clk,
    input  wire [AW-1:0] addr,
    output reg  [11:0]   data
);

    reg [11:0] rom [0:DEPTH-1];

    initial if (LAYOUT_HEX != "") $readmemh(LAYOUT_HEX, rom);

    // Registered, like the font ROM and like the CPU's own memories: the
    // renderer already pays a pipeline stage for that and the alternative is
    // a 16,384:1 mux, which is the shape hcpu_sdio.v's buffer measured at
    // +656 LUT4 before it was moved back into a block.
    always @(posedge clk)
        data <= rom[addr];

endmodule

`default_nettype wire
