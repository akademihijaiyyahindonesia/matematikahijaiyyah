// hcpu_telemetry.v — the CPU's state, carried to the video clock intact.
//
// The monitor runs at 74.25 MHz and the CPU at 27 MHz. Sampling a 32-bit
// counter across that boundary with nothing but a two-flop synchroniser per
// bit is the classic way to display a number that never existed: the bits
// arrive from either side of an increment and 0x0FFF reads as 0x0F7F. A
// dashboard whose whole claim is "these are real values" cannot do that.
//
// ── the handshake, and why it is a handshake ────────────────────
// The video side asks; the CPU side answers with a set of fields that were
// all true at the same instant:
//
//   video   toggles `req`                     once per frame is plenty
//   cpu     sees the toggle, latches EVERY field in one clock into `held`
//   cpu     toggles `ack`
//   video   sees the toggle, copies `held` into the snapshot
//
// Only the two toggles cross the boundary, and each is one bit through two
// flops. `held` is stable for many microseconds before it is read, so the
// copy needs no synchroniser of its own -- that is the entire reason for the
// handshake rather than a free-running sample.
//
// ── what this module does NOT invent ────────────────────────────
// It carries what it is given. Every field here comes from a signal that
// already existed at the wrapper boundary: PC from imem_addr, the instruction
// word from imem_data, halted and guard from hcpu_top's own outputs, the
// cycle counter from the wrapper's own, and FLAGS from the debug port that
// was tied off until now. Anything the hardware does not produce is absent
// from this module rather than defaulted -- the dashboard prints NOT
// INSTRUMENTED for those, and it prints it because there is no wire.

`default_nettype none

module hcpu_telemetry #(
    parameter PCW = 12
) (
    // ── CPU clock domain ────────────────────────────────────────
    input  wire            cpu_clk,
    input  wire            cpu_rst_n,
    input  wire [PCW-1:0]  pc,
    input  wire [31:0]     instr,
    input  wire            halted,
    input  wire            guard,
    input  wire [31:0]     cycles,
    input  wire [7:0]      flags,

    // ── video clock domain ──────────────────────────────────────
    input  wire            vid_clk,
    input  wire            vid_rst_n,
    input  wire            sample,        // one pulse: take a fresh snapshot

    output reg  [PCW-1:0]  snap_pc,
    output reg  [31:0]     snap_instr,
    output reg             snap_halted,
    output reg             snap_guard,
    output reg  [31:0]     snap_cycles,
    output reg  [7:0]      snap_flags,
    output reg             snap_valid     // a snapshot has been taken at least once
);

    // ── the request, raised on the video side ───────────────────
    reg req;
    always @(posedge vid_clk or negedge vid_rst_n) begin
        if (!vid_rst_n) req <= 1'b0;
        else if (sample) req <= ~req;
    end

    reg req_s1, req_s2, req_s3;
    always @(posedge cpu_clk or negedge cpu_rst_n) begin
        if (!cpu_rst_n) begin
            req_s1 <= 1'b0; req_s2 <= 1'b0; req_s3 <= 1'b0;
        end else begin
            req_s1 <= req; req_s2 <= req_s1; req_s3 <= req_s2;
        end
    end
    wire req_edge = req_s2 ^ req_s3;

    // ── one clock, every field ──────────────────────────────────
    // All six assignments happen on the same edge, which is what makes the
    // set coherent. A PC from one instruction beside a cycle count from the
    // next is worse than no number at all, because it looks plausible.
    reg [PCW-1:0] held_pc;
    reg [31:0]    held_instr;
    reg           held_halted;
    reg           held_guard;
    reg [31:0]    held_cycles;
    reg [7:0]     held_flags;
    reg           ack;

    always @(posedge cpu_clk or negedge cpu_rst_n) begin
        if (!cpu_rst_n) begin
            held_pc     <= {PCW{1'b0}};
            held_instr  <= 32'd0;
            held_halted <= 1'b0;
            held_guard  <= 1'b0;
            held_cycles <= 32'd0;
            held_flags  <= 8'd0;
            ack         <= 1'b0;
        end else if (req_edge) begin
            held_pc     <= pc;
            held_instr  <= instr;
            held_halted <= halted;
            held_guard  <= guard;
            held_cycles <= cycles;
            held_flags  <= flags;
            ack         <= ~ack;
        end
    end

    // ── the answer, collected on the video side ─────────────────
    reg ack_s1, ack_s2, ack_s3;
    always @(posedge vid_clk or negedge vid_rst_n) begin
        if (!vid_rst_n) begin
            ack_s1 <= 1'b0; ack_s2 <= 1'b0; ack_s3 <= 1'b0;
        end else begin
            ack_s1 <= ack; ack_s2 <= ack_s1; ack_s3 <= ack_s2;
        end
    end
    wire ack_edge = ack_s2 ^ ack_s3;

    always @(posedge vid_clk or negedge vid_rst_n) begin
        if (!vid_rst_n) begin
            snap_pc     <= {PCW{1'b0}};
            snap_instr  <= 32'd0;
            snap_halted <= 1'b0;
            snap_guard  <= 1'b0;
            snap_cycles <= 32'd0;
            snap_flags  <= 8'd0;
            snap_valid  <= 1'b0;
        end else if (ack_edge) begin
            snap_pc     <= held_pc;
            snap_instr  <= held_instr;
            snap_halted <= held_halted;
            snap_guard  <= held_guard;
            snap_cycles <= held_cycles;
            snap_flags  <= held_flags;
            snap_valid  <= 1'b1;
        end
    end

endmodule

`default_nettype wire
