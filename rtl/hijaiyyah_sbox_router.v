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
// MEASURED, not estimated. yosys, `abc -lut 4`, flattened:
//
//   per S-box            tower-field logic    76 LUT4
//                        256-entry table     274 LUT4      3.6x larger
//
//   router, WIDTH=8      logic                605 LUT4
//                        table               2209 LUT4
//   router, WIDTH=25     logic               2023 LUT4     201 FF
//                        table               6743 LUT4
//
// WIDTH=25 is the whole 5x5 cube face substituting in one clock. On a Tang
// Nano 9K (GW1NR-9, 8640 LUT4) that is 23% of the device with logic and 78%
// with the table -- so the logic form is not only the one without the timing
// weakness, it is the one that leaves room for the rest of the sponge, the
// UART and the HCPU beside it. The table does not fit that design; this does.

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
