// hcpu_font_rom.v — the 8x8 glyphs, finally read by something.
//
// rtl/hcpu_font8x8.hex has sat in this tree untracked and unreferenced since
// 11 September, named in AGENTS.md only inside the list of things not to be
// worked on without orders. M5 makes text rendering a requirement, and the
// owner opened it on 15 September 2026. Not one glyph byte is changed here.
//
// ── what the file actually contains, measured ───────────────────
// 1024 lines, two hex digits each: 128 glyphs of 8 rows, one byte per scan
// line, MSB leftmost. 51 glyphs carry ink:
//
//   1..5      five symbols in the control range
//   37 39     '%' and '\''
//   40..58    '(' ')' '*' '+' ',' '-' '.' '/' '0'..'9' ':'
//   65..90    'A'..'Z'
//
// THERE ARE NO LOWERCASE GLYPHS. Anything a dashboard prints has to be
// uppercase, and a renderer that is handed 'a' will draw blank rather than
// wrong -- blank is what index 97 holds.
//
// ── one cycle late, like every other memory here ────────────────
// The read is registered so this infers BSRAM rather than a 1024:1 mux of
// LUTs. hcpu_sdio.v's buffer records what the alternative costs: distributed
// LUT RAM added 656 LUT4 and made the slot unplaceable. The renderer pays for
// this with a pipeline stage, which it has to have anyway for the text RAM.
//
// ── the path is a parameter because the builds run from different places ──
// rtl/fpga/gowin runs yosys from its own directory, rtl/tb runs iverilog from
// its own, and $readmemh resolves against the working directory. One default
// cannot satisfy both, so each build states where the file is. A wrong path
// is not silent: $readmemh warns, and the screen fills with blanks.

`default_nettype none

module hcpu_font_rom #(
    // EMPTY BY DEFAULT, and every instantiation states the path. Both yosys
    // and iverilog elaborate an uninstantiated module as a root of its own,
    // with default parameters -- so a default that names a real file is read
    // from whatever directory the build happens to run in, and the two builds
    // run from different ones. Two levels apart, in fact, which no single
    // relative default can satisfy. An empty string reads nothing and copies
    // nothing; the file stays in rtl/ and each caller says where that is.
    parameter FONT_HEX = ""
) (
    input  wire       clk,
    input  wire [6:0] glyph,      // ASCII 0..127; bit 7 is dropped by the caller
    input  wire [2:0] row,        // which of the eight scan lines
    output reg  [7:0] bits        // one line of the glyph, MSB leftmost
);

    reg [7:0] rom [0:1023];

    initial if (FONT_HEX != "") $readmemh(FONT_HEX, rom);

    always @(posedge clk)
        bits <= rom[{glyph, row}];

endmodule

`default_nettype wire
