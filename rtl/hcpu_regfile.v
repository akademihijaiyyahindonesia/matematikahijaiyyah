// ============================================================================
// HCPU Register File — hcpu_regfile.v
// 18 GPR (32-bit) + 16 H-Reg (144-bit) + FLAGS + PC + SP
// Dual read ports, single write port per bank
// (c) 2026 Maulana Amratulloh — HM-28-v1.2-HC18D
// ============================================================================

`include "hcpu_pkg.vh"

module hcpu_regfile (
    input  wire                    clk,
    input  wire                    rst_n,

    // ── GPR read ports (dual) ───────────────────────────────────
    input  wire [4:0]              gpr_raddr1,
    input  wire [4:0]              gpr_raddr2,
    output wire [`XLEN-1:0]        gpr_rdata1,
    output wire [`XLEN-1:0]        gpr_rdata2,

    // ── GPR write port ──────────────────────────────────────────
    input  wire                    gpr_we,
    input  wire [4:0]              gpr_waddr,
    input  wire [`XLEN-1:0]        gpr_wdata,

    // ── H-Reg read ports (dual) ─────────────────────────────────
    input  wire [3:0]              hreg_raddr1,
    input  wire [3:0]              hreg_raddr2,
    output wire [`HREG_W-1:0]      hreg_rdata1,
    output wire [`HREG_W-1:0]      hreg_rdata2,

    // ── H-Reg write port ────────────────────────────────────────
    input  wire                    hreg_we,
    input  wire [3:0]              hreg_waddr,
    input  wire [`HREG_W-1:0]      hreg_wdata,

    // ── FLAGS ─────────────────────────────────────────────────
    input  wire                    flags_we,
    input  wire [7:0]              flags_in,
    output wire [7:0]              flags_out,

    // ── PC ──────────────────────────────────────────────────
    input  wire                    pc_we,
    input  wire [`XLEN-1:0]        pc_in,
    output wire [`XLEN-1:0]        pc_out,

    // ── Debug / Wishbone read-back port (3rd GPR read) ─────────
    input  wire [4:0]              dbg_gpr_raddr,
    output wire [`XLEN-1:0]        dbg_gpr_rdata,
    output wire [7:0]              dbg_flags
);

    // ── GPR storage ─────────────────────────────────────────────
    reg [`XLEN-1:0] gpr [0:`GPR_COUNT-1];

    // ── H-Reg storage (packed 144-bit per register) ─────────────
    reg [`HREG_W-1:0] hreg [0:`HREG_COUNT-1];

    // ── Special registers ───────────────────────────────────────
    reg [7:0]        flags;
    reg [`XLEN-1:0]  pc;

    // ── GPR read (with transparent write-through) ───────────────
    assign gpr_rdata1 = (gpr_we && gpr_waddr == gpr_raddr1) ? gpr_wdata : gpr[gpr_raddr1];
    assign gpr_rdata2 = (gpr_we && gpr_waddr == gpr_raddr2) ? gpr_wdata : gpr[gpr_raddr2];

    // ── H-Reg read (with transparent write-through) ─────────────
    assign hreg_rdata1 = (hreg_we && hreg_waddr == hreg_raddr1) ? hreg_wdata : hreg[hreg_raddr1];
    assign hreg_rdata2 = (hreg_we && hreg_waddr == hreg_raddr2) ? hreg_wdata : hreg[hreg_raddr2];

    // ── FLAGS / PC read ───────────────────────────────────────
    // FLAGS needs the same write-through GPR and H-Reg already have, above,
    // and did not have it: `flags_out` was a bare passthrough of last
    // cycle's committed value. GPR/H-Reg's forwarding chain in
    // hcpu_execute.v covers a consumer up to two stages behind a producer
    // (EX-forward, then MEM-forward) and falls back to the register file for
    // anything further -- which works for GPR because the register file
    // itself is transparent on the exact cycle a write lands. FLAGS' fallback
    // was the same `current_flags` wire, fed from this module, but with no
    // write-through here it was NOT transparent on that cycle: a consumer
    // reading flags on the exact cycle CMP's result reaches this stage read
    // the value from BEFORE that write, one full cycle stale.
    //
    // This is narrow enough that nothing else in this codebase had hit it:
    // every existing CMP/CMPI-then-branch pair here is adjacent (zero
    // instructions between them), which lands inside the EX-forward window
    // and never reaches this register at all. hos.hasm's `hos_alloc`
    // (rtl/programs/hos.hasm) was the first code with an intervening
    // instruction between a comparison and the branch reading it, ALSO
    // preceded by enough stalls (from the load-use interlock on adjacent
    // LOADs) to land the branch's read exactly on the collision cycle --
    // `CMP R1,R2 / MOVI R2,1 / JNE` read Z=1 for two GENUINELY DIFFERENT
    // operands (3587, 3594), because the correct Z=0/LT=1 result committed
    // to `flags` one cycle after JNE had already evaluated the stale one.
    assign flags_out = flags_we ? flags_in : flags;
    assign pc_out    = pc;

    // ── Debug read port (no write-through, read-only) ──────────
    assign dbg_gpr_rdata = gpr[dbg_gpr_raddr];
    assign dbg_flags     = flags;

    // ── Write logic (synchronous) ───────────────────────────────
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < `GPR_COUNT; i = i + 1)
                gpr[i] <= {`XLEN{1'b0}};
            for (i = 0; i < `HREG_COUNT; i = i + 1)
                hreg[i] <= {`HREG_W{1'b0}};
            flags <= 8'h00;
            pc    <= {`XLEN{1'b0}};
        end else begin
            if (gpr_we)
                gpr[gpr_waddr] <= gpr_wdata;
            if (hreg_we)
                hreg[hreg_waddr] <= hreg_wdata;
            if (flags_we)
                flags <= flags_in;
            if (pc_we)
                pc <= pc_in;
        end
    end

endmodule
