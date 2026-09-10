// ============================================================================
// HCPU Pipeline Controller — hcpu_controller.v  (v2.0)
// Global stall/flush management, hazard resolution, halt detection
// (c) 2026 Maulana Amratulloh — Hybit Technology
// ============================================================================
//
// Stall policy:
//   - PRINT instruction → stall entire pipeline until UART tx_busy deasserts
//   - Load-use hazard   → stall front-end (PC+IF), bubble into EX
//   - Store-load hazard → stall front-end (PC+IF), bubble into EX
//
// Flush policy:
//   - Taken branch/jump → flush IF and ID stages (1-cycle penalty)
//
// Halt:
//   - HALT instruction reaches writeback → assert halted, freeze everything
//

`include "hcpu_pkg.vh"

module hcpu_controller (
    input  wire        clk,
    input  wire        rst_n,

    // ── Instruction info from decode/execute ────────────────────
    input  wire        ex_is_print,
    input  wire        branch_taken,
    input  wire        wb_halt,

    // ── Dependency info ─────────────────────────────────────────
    input  wire        load_use_hazard,
    input  wire        store_load_hazard,

    // ── UART status ─────────────────────────────────────────────
    input  wire        uart_busy,

    // ── Pipeline control outputs ────────────────────────────────
    output wire        pc_stall,       // Freeze Fetch (PC + IF/ID)
    output wire        id_stall,       // Freeze Decode (ID/EX)
    output wire        ex_stall,       // Freeze EX/MEM/WB 
    output wire        if_flush,       // Flush IF/ID (insert NOP to Decode)
    output wire        id_flush,       // Flush ID/EX (insert bubble directly)
    output reg         halted          // Processor halted
);

    // ── PRINT blocking stall ────────────────────────────────────
    // Stall the entire pipeline for as long as a print is in flight.
    //
    // `ex_is_print` already IS that signal, correctly, for its whole
    // duration: hcpu_top.v wires it from `print_active`, which its own
    // print_state FSM holds high from the cycle a PRINT is accepted
    // (P_IDLE -> P_CONV) until the cycle it returns to P_IDLE, spanning
    // every digit AND the trailing newline.
    //
    // A second latch used to be layered on top of it here -- `print_pending`,
    // cleared the moment `uart_busy` (hcpu_uart_tx's OWN per-byte busy flag)
    // went low. uart_busy drops between a print's two bytes -- after the
    // digit finishes, before the newline's transmission starts -- which is
    // exactly mid-print, not end-of-print. `print_pending` cleared there,
    // global_stall dropped, and the pipeline resumed a cycle or more before
    // the print FSM actually reached P_IDLE. One PRINT on its own never
    // showed it: nothing queued behind it needed to wait. Two PRINTs close
    // together did -- the second one's single-cycle `ex_is_print` pulse
    // landed while print_state was still finishing the FIRST print's
    // newline, not in P_IDLE, so the FSM's own `if (ex_is_print...)` guard
    // (P_IDLE case only) never saw it and the second value was silently
    // never sent. rtl/programs/nui_embedding.hasm -- five PRINTs, nothing
    // before this had ever issued more than one -- is what found it.
    wire print_stall = ex_is_print;

    // ── Halt latch ──────────────────────────────────────────────
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            halted <= 1'b0;
        else if (wb_halt)
            halted <= 1'b1;
    end

    // ── Global Stall: a print in flight OR halted ───────────────
    wire global_stall = print_stall || halted;

    // ── Front-end Hazard Stall ──────────────────────────────────
    // Load-use and store-load hazards use the same mechanism:
    //   - Freeze PC + IF (hold current instruction in fetch)
    //   - Flush decode → NOP into ID/EX pipeline register
    //   - Decode is NOT stalled so the LOAD flows from ID → EX
    //   - EX is NOT stalled so the current EX instruction → MEM
    wire data_hazard = load_use_hazard || store_load_hazard;

    // ── Pipeline Control Equations ──────────────────────────────
    assign pc_stall = global_stall || data_hazard;
    assign id_stall = global_stall;
    assign ex_stall = global_stall;

    // ── Flushes ─────────────────────────────────────────────────
    // branch_taken: flush IF/ID and ID/EX (kill speculative path)
    // data_hazard:  flush ID/EX only (insert 1-cycle bubble into EX)
    assign if_flush = branch_taken && !global_stall;
    assign id_flush = (branch_taken || data_hazard) && !global_stall;

endmodule
