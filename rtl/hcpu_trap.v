// ============================================================================
// HCPU Trap Unit — hcpu_trap.v
// Interrupt and exception entry, and the return from it
// (c) 2026 Maulana Amratulloh — Hybit Technology
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
    input  wire                     src_priv,      // privileged act in user mode
    input  wire                     src_mem,       // data access out of bounds
    input  wire                     src_syscall,   // ECALL retired

    // ── The PC a trap would return to ───────────────────────────
    input  wire [`XLEN-1:0]         pc_now,
    input  wire                     pc_valid,   // 0 while the front end is empty

    // An INTERRUPT returns to pc_now -- the instruction that has not run yet.
    // An EXCEPTION must name the instruction that caused it, which is already
    // past fetch, so Execute supplies its PC separately. Saving pc_now for a
    // fault would return to whatever happened to be in the front end and lose
    // the faulting instruction entirely.
    input  wire [`XLEN-1:0]         pc_fault,

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
    output wire                     in_trap,
    output wire                     in_user        // gates the peripheral window
);

    reg                  mode;      // MODE_USER / MODE_SUPER, current
    reg                  prev;      // what ERET will install
    reg [`XLEN-1:0]      vector;
    reg [`XLEN-1:0]      epc;
    reg [2:0]            cause;
    reg [`TRAP_MASK_W-1:0] enable;
    reg                  trap_active;

    assign in_trap = trap_active;
    assign in_user = (mode == `MODE_USER);

    // ── Pending: raw sources, one bit each ──────────────────────
    wire [`TRAP_MASK_W-1:0] pending;
    assign pending = { {(`TRAP_MASK_W-`TRAP_CAUSES){1'b0}},
                       src_syscall, src_mem, src_priv, src_illegal,
                       src_uart_rx, src_timer };

    // Exceptions ignore the mask; interrupts obey it. A timer or a UART byte
    // arrives from outside and software may say "not now". A privilege
    // violation is the instruction stream itself doing what it may not, and a
    // maskable protection is not a protection -- user code would disable it by
    // clearing one bit.
    // Both are EXCEPTIONS: the instruction stream doing what it may not.
    // A maskable memory boundary is not a boundary, for the same reason a
    // maskable privilege check is not a check.
    localparam [`TRAP_MASK_W-1:0] NONMASKABLE =
        (1 << `TRAP_PRIV) | (1 << `TRAP_MEM) | (1 << `TRAP_SYSCALL);

    wire [`TRAP_MASK_W-1:0] armed = (pending & enable) | (pending & NONMASKABLE);

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

    // A write to TRAP_MODE in the same cycle as an ERET has to be the value
    // that ERET returns to. `mode <= prev` reads the register before the write
    // lands, so an ERET one instruction after `STORE ... 0xFFD` returned to
    // SUPERVISOR -- silently, with nothing to see. Every program that drops to
    // user mode writes TRAP_MODE and then ERETs, because that is the obvious
    // way to write it, so on hardware none of them ever left privilege. The
    // interpreter has no pipeline and dropped correctly, so the two agreed on
    // every result they were asked for and disagreed on the one thing that
    // mattered. One NOP in between was enough to hide it; the fix is not to
    // require one.
    wire mode_write   = reg_we && (reg_sel == `REG_TRAP_MODE);
    wire prev_at_eret = mode_write ? reg_wdata[1] : prev;

    // AND THE SAME FOR TRAP_EPC, for the same reason and by the same shape.
    // The paragraph above ends "the fix is not to require one" -- meaning a
    // NOP -- and then only TRAP_MODE got the treatment. `trap_target` read
    // `epc` straight, so a handler that wrote its return address and ERETed on
    // the very next instruction returned to the OLD one.
    //
    // Measured before this line existed, sweeping the gap from 0 to 4 NOPs
    // over a 200-cycle window: at ZERO the trap fired FIFTEEN times and the
    // instruction after the SYSCALL was never reached; at ONE it was correct,
    // and so was everything above it. Exactly one instruction of distance is
    // what the hazard cost -- which is why rtl/programs/trap_flags.hasm, which
    // happened to use three, never saw it.
    //
    // Every handler in the tree already had the distance: hal_epc_set is
    // followed by hal_mode_user, hal_timer_arm and sixteen restore loads. So
    // nothing that worked changes. What changes is that a SHORT handler is no
    // longer silently wrong, and "silently" is the word that matters -- the
    // symptom is an instruction that repeats, not an error.
    wire epc_write    = reg_we && (reg_sel == `REG_TRAP_EPC);
    wire [`XLEN-1:0] epc_at_eret = epc_write ? reg_wdata : epc;

    // ── Redirect ────────────────────────────────────────────────
    // ERET beats a new trap: the return has already been decided by an
    // instruction that retired, and dropping it would strand the handler.
    assign trap_redirect = eret || fire;
    assign trap_target   = eret ? epc_at_eret : vector;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            vector      <= {`XLEN{1'b0}};
            epc         <= {`XLEN{1'b0}};
            cause       <= 3'd0;
            enable      <= {`TRAP_MASK_W{1'b0}};
            trap_active <= 1'b0;
            // Reset lands in supervisor. There is no other way in: entering
            // user mode is a deliberate act -- write `prev` then ERET -- and
            // if reset came up in user mode nothing could ever configure the
            // machine, because configuring it means touching the window that
            // user mode cannot touch.
            mode        <= `MODE_SUPER;
            prev        <= `MODE_SUPER;
        end else begin
            if (eret) begin
                trap_active <= 1'b0;
                mode        <= prev_at_eret;
            end else if (fire) begin
                // epc points AT the faulting instruction, not past it, so a
                // handler can emulate the operation and advance epc itself --
                // which is how the syscall step will work. A handler that does
                // neither will re-execute it and loop, and that is visible
                // rather than silent.
                epc         <= (which >= `TRAP_PRIV) ? pc_fault : pc_now;
                cause       <= which;
                trap_active <= 1'b1;
                prev        <= mode;      // remember it
                mode        <= `MODE_SUPER;  // a handler always runs privileged
            end

            // Software writes land after the hardware update, so a handler
            // that rewrites epc for nesting wins over the entry that put it
            // there. Entry and a same-cycle write cannot both be right.
            if (reg_we) begin
                case (reg_sel)
                    `REG_TRAP_VECTOR: vector <= reg_wdata;
                    `REG_TRAP_EPC:    epc    <= reg_wdata;
                    `REG_TRAP_ENABLE: enable <= reg_wdata[`TRAP_MASK_W-1:0];
                    // Bit 1 only. Bit 0 is the CURRENT mode and is read-only:
                    // if software could write it, dropping privilege and
                    // raising it again would be the same instruction.
                    `REG_TRAP_MODE:   prev   <= reg_wdata[1];
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
            `REG_TRAP_MODE:    reg_rdata = { {(`XLEN-2){1'b0}}, prev, mode };
            default:           reg_rdata = {`XLEN{1'b0}};
        endcase
    end

endmodule
