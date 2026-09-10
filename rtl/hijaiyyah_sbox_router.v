// hijaiyyah_sbox_router.v — the substitution as a routed block, per clock.
//
// The cube takes bytes per clock. A table cannot: a lookup is a memory
// transaction with an address, a port and a latency, and twenty-five lanes
// wanting the same table is twenty-five serialised accesses or twenty-five
// copies of the ROM. hijaiyyah_sbox is pure logic, so it can be instantiated
// as many times as there are gates and every copy resolves in the same
// propagation delay.
//
// This module is that instantiation: WIDTH bytes enter, WIDTH bytes leave,
// one clock later, always one clock. No arbitration, no port contention, no
// stall path, and no branch on data anywhere in it. The constant-time
// property is not enforced by this module -- there is simply nothing here
// that could vary with the value.
//
// The registers exist to make the stage's timing its own: without them the
// whole absorb-permute path would be one combinational cone and Fmax would
// be set by the longest chain across it rather than by this block.
//
// MEASURED, not estimated -- and measured by a named method, because the
// method is where an area claim usually goes soft. All figures below are
// yosys with `abc -lut 4`, flattened: generic mapping to 4-input LUTs, the
// standard proxy for LUT4-FPGA area.
//
//   per S-box            tower-field logic    76 LUT4
//                        256-entry table     274 LUT4      3.6x larger
//
//   router, WIDTH=8      logic                605 LUT4
//                        table               2209 LUT4
//   router, WIDTH=25     logic               2023 LUT4     201 FF
//                        table               6743 LUT4
//
// SCALE, CORRECTED. An earlier version of this header called WIDTH=25 "the
// whole 5x5 cube face in one clock". That was wrong by a factor of eight and
// the error was repeated in three places before the arithmetic was checked
// against the state: the face is 25 LANES of 64 bits = 1600 bits = 200 BYTES,
// so WIDTH=25 substitutes one EIGHTH of a face, and a full face takes eight
// clocks at this width.
//
// A fully parallel face needs 200 S-boxes:
//     logic  200 x  76 = 15,200 LUT4   73% of a Tang Nano 20K (20,736)
//     table  200 x 274 = 54,800 LUT4   not close
//
// So the design that fits is one eighth of a face per clock, and the choice of
// form is what decides whether even that fits: 2023 LUT4 with logic against
// 6743 with the table, on a device with 8640.
//
// WHAT IS AND IS NOT VERIFIED. The ratio -- 3.6x per S-box, and 2023 against
// 6743 for the full face -- is solid: both sides went through one mapping,
// so the comparison is method-independent even if the absolute numbers move.
// Against a Tang Nano 20K's 20,736 LUT4 those figures read as 10% and 33%
// for one eighth of a face per clock, and
// THAT step assumes generic LUT4 count tracks Gowin LUT4 count. Vendor
// synthesis (`synth_gowin`) did not complete on this module here, and
// nextpnr is not installed, so no placed-and-routed number exists yet. The
// percentages are a proxy, not a fitting report. E1 (Fmax) has no value at
// all until the board arrives.
//
// What the ratio already settles is the design question: the table form
// costs more than three times the logic form, so the logic form is both the
// one without the timing weakness and the one that leaves room for the rest
// of the sponge, the UART and the HCPU beside it.

`default_nettype none

module hijaiyyah_sbox_router #(
    parameter integer WIDTH = 8          // bytes substituted per clock
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    valid_in,
    input  wire [WIDTH*8-1:0]      data_in,
    output reg                     valid_out,
    output reg  [WIDTH*8-1:0]      data_out
);

    wire [WIDTH*8-1:0] substituted;

    genvar i;
    generate
        for (i = 0; i < WIDTH; i = i + 1) begin : lane
            hijaiyyah_sbox u_sbox (
                .x (data_in    [i*8 +: 8]),
                .y (substituted[i*8 +: 8])
            );
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_out <= 1'b0;
            data_out  <= {WIDTH*8{1'b0}};
        end else begin
            valid_out <= valid_in;
            data_out  <= substituted;
        end
    end

endmodule

`default_nettype wire
