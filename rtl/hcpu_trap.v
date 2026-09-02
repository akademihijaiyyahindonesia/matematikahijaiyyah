// ============================================================================
// HCPU Trap Unit — hcpu_trap.v
// Interrupt and exception entry, and the return from it
// (c) 2026 HMCL — Hybit Technology
// ============================================================================
//
// A trap is a branch the program did not write. Everything else follows from
// that: it redirects the fetch exactly the way a taken branch does, it flushes
// the same two stages, and it costs the same one-cycle penalty. What it adds
// is that the address it came from is remembered, so the handler can go back.
//
// FIVE PIECES OF STATE, all reachable from software through the peripheral
// window so no new instruction is needed to touch them:
//
//     vector    where to jump on a trap            writable
//     epc       the PC that was about to run       writable (so traps can nest)
//     cause     which cause fired, as an index     read-only
//     enable    per-cause mask                     writable
//     pending   per-cause raw source bits          read-only
//
// `cause` holds the INDEX, not the mask. A handler that wants to dispatch does
// `LOAD r, TRAP_CAUSE` and jumps on the number; with a mask it would have to
// find the set bit first, every single time.
//
// IN_TRAP IS THE WHOLE DIFFICULTY. The sources here are level-sensitive: UART
// rx_ready stays high until the byte is read, and the timer's expired flag is
// sticky until written. Without a latch saying "a trap is already running",
// the very next cycle would trap again, on the same cause, from inside the
// handler -- and the handler's first instruction would never retire. So
// `in_trap` blocks re-entry, and ERET is what clears it.
//
// That also means a handler MUST clear its source before ERET, or it will trap
// again immediately on returning. That is not a flaw to design around; it is
// how every real interrupt controller behaves, and making it silent would just
// hide a lost interrupt.
//
// PRIORITY is the lowest set index, which is arbitrary but has to be fixed:
// two causes arriving in the same cycle must resolve the same way every time,
// or the machine is not deterministic and nothing above it can be sealed.

`include "hcpu_pkg.vh"

module hcpu_trap (
    input  wire                     clk,
    input  wire                     rst_n,

    // ── Cause sources (level-sensitive) ─────────────────────────
    input  wire                     src_timer,
    input  wire                     src_uart_rx,
    input  wire                     src_illegal,

    // ── The PC a trap would return to ───────────────────────────
    input  wire [`XLEN-1:0]         pc_now,
    input  wire                     pc_valid,   // 0 while the front end is empty

    // ── Software access through the peripheral window ───────────
    input  wire                     reg_we,
    input  wire [3:0]               reg_sel,
    input  wire [`XLEN-1:0]         reg_wdata,
    output reg  [`XLEN-1:0]         reg_rdata,

    // ── ERET, from Execute ──────────────────────────────────────
    input  wire                     eret,

    // ── Redirect to the fetch stage ─────────────────────────────
    output wire                     trap_redirect,
    output wire [`XLEN-1:0]         trap_target,
    output wire                     in_trap
);

    reg [`XLEN-1:0]      vector;
    reg [`XLEN-1:0]      epc;
    reg [2:0]            cause;
    reg [`TRAP_MASK_W-1:0] enable;
    reg                  trap_active;

    assign in_trap = trap_active;

    // ── Pending: raw sources, one bit each ──────────────────────
    wire [`TRAP_MASK_W-1:0] pending;
    assign pending = { {(`TRAP_MASK_W-`TRAP_CAUSES){1'b0}},
                       src_illegal, src_uart_rx, src_timer };

    wire [`TRAP_MASK_W-1:0] armed = pending & enable;

    // A trap fires only when the front end has a real PC to come back to.
    // Redirecting to a handler that returns into a bubble loses an instruction.
    wire fire = (|armed) && !trap_active && pc_valid;

    // ── Priority: lowest index wins, fixed forever ──────────────
    reg [2:0] which;
    integer i;
    always @* begin
        which = 3'd0;
        for (i = `TRAP_CAUSES-1; i >= 0; i = i - 1)
            if (armed[i]) which = i[2:0];
    end

    // ── Redirect ────────────────────────────────────────────────
    // ERET beats a new trap: the return has already been decided by an
    // instruction that retired, and dropping it would strand the handler.
    assign trap_redirect = eret || fire;
    assign trap_target   = eret ? epc : vector;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            vector      <= {`XLEN{1'b0}};
            epc         <= {`XLEN{1'b0}};
            cause       <= 3'd0;
            enable      <= {`TRAP_MASK_W{1'b0}};
            trap_active <= 1'b0;
        end else begin
            if (eret) begin
                trap_active <= 1'b0;
            end else if (fire) begin
                epc         <= pc_now;
                cause       <= which;
                trap_active <= 1'b1;
            end

            // Software writes land after the hardware update, so a handler
            // that rewrites epc for nesting wins over the entry that put it
            // there. Entry and a same-cycle write cannot both be right.
            if (reg_we) begin
                case (reg_sel)
                    `REG_TRAP_VECTOR: vector <= reg_wdata;
                    `REG_TRAP_EPC:    epc    <= reg_wdata;
                    `REG_TRAP_ENABLE: enable <= reg_wdata[`TRAP_MASK_W-1:0];
                    default: ;   // CAUSE and PENDING are read-only
                endcase
            end
        end
    end

    // ── Read path ───────────────────────────────────────────────
    always @* begin
        case (reg_sel)
            `REG_TRAP_VECTOR:  reg_rdata = vector;
            `REG_TRAP_EPC:     reg_rdata = epc;
            `REG_TRAP_CAUSE:   reg_rdata = { {(`XLEN-3){1'b0}}, cause };
            `REG_TRAP_ENABLE:  reg_rdata = { {(`XLEN-`TRAP_MASK_W){1'b0}}, enable };
            `REG_TRAP_PENDING: reg_rdata = { {(`XLEN-`TRAP_MASK_W){1'b0}}, pending };
            default:           reg_rdata = {`XLEN{1'b0}};
        endcase
    end

endmodule
