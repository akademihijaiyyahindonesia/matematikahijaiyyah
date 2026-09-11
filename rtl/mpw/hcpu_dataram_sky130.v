// ============================================================================
// HCPU Data RAM, SKY130 ASIC target — hcpu_dataram_sky130.v
// (c) 2026 Maulana Amratulloh — HM-28-v1.2-HC18D / Tier 1.5
// ============================================================================
//
// NOT WORKING YET. NOT referenced by config.json (still
// dir::../../hcpu_dataram.v, unchanged) and must not be until the problem
// below is actually fixed. Kept in the tree because the address-decode
// and byte-mask logic ARE measured correct (see below) and the timing
// problem is a real, specific, now-documented finding, not a guess.
//
// What this file gets right, measured directly against the real
// behavioural model (Icarus Verilog, sky130_sram_1kbyte_1rw1r_32x256_8):
// address decoding across all sixteen macros, byte write-masking
// (wmask0 tied to 4'b1111 -- HISA's STORE=0x31 is the only store opcode,
// no byte/half variant, so every write is a full word), and the basic
// read-after-write round trip when there is at least one idle cycle
// between accesses to different macros.
//
// What is BROKEN, measured directly (not assumed): this module's read
// latency does not match ../hcpu_dataram.v's documented one-cycle
// contract ("rdata valid the cycle AFTER addr is presented") -- a direct
// side-by-side comparison (both modules, same stimulus, same clock)
// shows rdata_sky130 still X at the exact edge where rdata_orig is
// already correct. It needs a second cycle. Worse: even measured at its
// own two-cycle latency, continuous zero-gap access -- a new LOAD or
// STORE every single cycle, addresses landing on different macros, which
// is ordinary back-to-back code, not a corner case -- produces wrong
// results most of the time (a 500-cycle random differential test against
// ../hcpu_dataram.v showed >95% mismatches). Isolated cases (2-3
// back-to-back reads with no writes mixed in) measured correctly at two
// cycles; interleaving a write while a read is still in flight does not.
//
// Root cause, as far as measured: the vendored macro's own dout0 is only
// valid for a narrow window each cycle (its behavioural model resets
// dout0 to X on every posedge, T_HOLD after it) -- this module's sel_r/
// re_r are single registers shared by every in-flight access, and a new
// request landing while an earlier one's data has not yet been captured
// overwrites the information needed to capture it. Fixing this needs
// something that tracks more than one in-flight access (a short shift
// register of pending selects, sized to the real number of cycles a
// request stays in flight) -- not designed here.
//
// Consequence for the pipeline, not yet resolved either way: even once
// the above is fixed, this module needs TWO cycles from presenting addr
// to valid rdata, not the one ../hcpu_dataram.v's header documents and
// hcpu_memory.v's forwarding (`rdata_r IS the MEM/WB pipeline register
// for load data`) depends on. Using real SRAM macros here means either a
// stall cycle for LOAD/STORE or restructuring which stage issues the
// request -- a real architectural decision, not a drop-in swap.
//
// Address space: 4096 x 32-bit words = 16 KB. addr[11:8] selects one of
// sixteen 256-word macros; addr[7:0] is that macro's own address.

`include "hcpu_pkg.vh"

module hcpu_dataram (
    input  wire                     clk,
    input  wire                     re,
    input  wire                     we,
    input  wire [`DATA_ADDR_W-1:0]  addr,
    input  wire [`XLEN-1:0]         wdata,
    output wire [`XLEN-1:0]         rdata
);

    localparam MACRO_ADDR_W = 8;              // sky130_sram_1kbyte_1rw1r_32x256_8: 256 words
    localparam NUM_MACROS   = 16;              // 4096 / 256
    localparam SEL_W        = 4;               // $clog2(NUM_MACROS)

    wire [SEL_W-1:0]        sel      = addr[`DATA_ADDR_W-1 -: SEL_W];
    wire [MACRO_ADDR_W-1:0] mac_addr = addr[MACRO_ADDR_W-1:0];

    // sel_r/re_r: single registers, one in-flight access at a time. This
    // is the known-broken part -- see the file header. Correct for an
    // isolated access with an idle cycle on either side; NOT correct
    // under continuous back-to-back access to different macros, because
    // a new request overwrites the previous one's sel_r/re_r before its
    // two-cycle-delayed data has been captured into rdata_r below.
    reg [SEL_W-1:0] sel_r;
    reg             re_r;
    always @(posedge clk) begin
        if (re || we)
            sel_r <= sel;
        re_r <= re;
    end

    wire [`XLEN-1:0] dout0 [0:NUM_MACROS-1];

    genvar g;
    generate
        for (g = 0; g < NUM_MACROS; g = g + 1) begin : MACRO
            wire selected = (re || we) && (sel == g[SEL_W-1:0]);
            sky130_sram_1kbyte_1rw1r_32x256_8 u_macro (
                .clk0   (clk),
                .csb0   (~selected),
                .web0   (~we),
                .wmask0 (4'b1111),
                .addr0  (mac_addr),
                .din0   (wdata),
                .dout0  (dout0[g]),
                .clk1   (clk),
                .csb1   (1'b1),
                .addr1  ({MACRO_ADDR_W{1'b0}}),
                .dout1  ()
            );
        end
    endgenerate

    reg [`XLEN-1:0] rdata_r;
    always @(posedge clk)
        if (re_r)
            rdata_r <= dout0[sel_r];

    assign rdata = rdata_r;

endmodule
