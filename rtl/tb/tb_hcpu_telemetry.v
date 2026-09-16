// tb_hcpu_telemetry.v — does a snapshot belong to one instant?
//
// The monitor's whole claim is that its numbers are real. A CPU counter
// sampled across a clock boundary with plain synchronisers produces numbers
// that are plausible and never existed -- 0x0FFF reading as 0x0F7F because
// the bits crossed either side of an increment. That failure cannot be seen
// on a screen: it looks like a value.
//
// So this bench runs the two clocks at deliberately awkward rates, keeps the
// source fields moving every CPU cycle, and asks for snapshots from the video
// side. Then it checks the one property that matters:
//
//   COHERENCE   the six fields in a snapshot were all true together
//
// It can check that without a reference model because the stimulus makes the
// fields mutually predictable: cycles counts up, pc is cycles' low bits,
// instr is a fixed function of cycles. If a snapshot's fields disagree with
// each other, they came from different instants.

`timescale 1ns/1ps
`default_nettype none

module tb_hcpu_telemetry;

    // 27 MHz and 74.25 MHz, near enough, and deliberately not a ratio that
    // makes edges line up: a handshake that only works on aligned clocks is
    // a handshake that works in this bench and nowhere else.
    reg cpu_clk = 1'b0;
    reg vid_clk = 1'b0;
    always #18.5 cpu_clk = ~cpu_clk;
    always #6.73 vid_clk = ~vid_clk;

    reg rst_n = 1'b0;

    reg [11:0] pc;
    reg [31:0] instr;
    reg        halted, guard;
    reg [31:0] cycles;
    reg [7:0]  flags;

    // Everything moves every CPU clock, and everything is a function of
    // `cycles`. A coherent snapshot therefore satisfies three equations.
    always @(posedge cpu_clk or negedge rst_n) begin
        if (!rst_n) begin
            cycles <= 32'd0;
            pc     <= 12'd0;
            instr  <= 32'd0;
            flags  <= 8'd0;
            halted <= 1'b0;
            guard  <= 1'b0;
        end else begin
            cycles <= cycles + 32'd1;
            pc     <= cycles[11:0] + 12'd1;
            instr  <= ~(cycles + 32'd1);
            flags  <= cycles[7:0] + 8'd1;
            halted <= cycles[8];
            guard  <= cycles[9];
        end
    end

    reg  sample = 1'b0;
    wire [11:0] snap_pc;
    wire [31:0] snap_instr, snap_cycles;
    wire [7:0]  snap_flags;
    wire        snap_halted, snap_guard, snap_valid;

    hcpu_telemetry #(.PCW(12)) dut (
        .cpu_clk(cpu_clk), .cpu_rst_n(rst_n),
        .pc(pc), .instr(instr), .halted(halted), .guard(guard),
        .cycles(cycles), .flags(flags),
        .vid_clk(vid_clk), .vid_rst_n(rst_n), .sample(sample),
        .snap_pc(snap_pc), .snap_instr(snap_instr), .snap_halted(snap_halted),
        .snap_guard(snap_guard), .snap_cycles(snap_cycles),
        .snap_flags(snap_flags), .snap_valid(snap_valid)
    );

    integer errors = 0;
    task check(input cond, input [255:0] what);
        begin
            if (!cond) begin
                $display("  GAGAL: %0s", what);
                errors = errors + 1;
            end else
                $display("  ok   : %0s", what);
        end
    endtask

    integer i, taken;
    reg coherent, moved;
    reg [31:0] prev_cycles;

    initial begin
        $display("=== tb_hcpu_telemetry: satu snapshot, satu saat ===");

        repeat (8) @(posedge vid_clk);
        rst_n = 1'b1;

        check(snap_valid === 1'b0, "sebelum sample: tak berlaku");

        // ── fifty snapshots, each checked against itself ────────
        coherent    = 1'b1;
        moved       = 1'b0;
        prev_cycles = 32'hFFFF_FFFF;
        taken       = 0;

        for (i = 0; i < 50; i = i + 1) begin
            @(posedge vid_clk);
            sample = 1'b1;
            @(posedge vid_clk);
            sample = 1'b0;

            // The handshake is two synchronisers deep each way; twenty video
            // clocks is far more than it needs and far less than a frame.
            repeat (20) @(posedge vid_clk);
            #1;

            if (snap_valid) begin
                taken = taken + 1;
                if (snap_pc    !== snap_cycles[11:0]) coherent = 1'b0;
                if (snap_instr !== ~snap_cycles)      coherent = 1'b0;
                if (snap_flags !== snap_cycles[7:0])  coherent = 1'b0;
                if (snap_halted !== snap_cycles[8])   coherent = 1'b0;
                if (snap_guard  !== snap_cycles[9])   coherent = 1'b0;
                if (!coherent) begin
                    $display("    snapshot %0d tidak koheren: cycles=%08h pc=%03h instr=%08h flags=%02h",
                             i, snap_cycles, snap_pc, snap_instr, snap_flags);
                    i = 50;
                end
                if (snap_cycles !== prev_cycles) moved = 1'b1;
                prev_cycles = snap_cycles;
            end
        end

        check(taken == 50, "lima puluh snapshot terambil");
        check(coherent, "koheren: enam field satu saat");
        check(moved, "nilainya bergerak, bukan beku");

        // ── a snapshot is stable between requests ───────────────
        prev_cycles = snap_cycles;
        repeat (200) @(posedge vid_clk);
        #1;
        check(snap_cycles === prev_cycles,
              "tanpa sample: tak berubah");

        check(snap_valid === 1'b1, "sesudah sample: berlaku");

        if (errors == 0)
            $display("tb_hcpu_telemetry: SEMUA LULUS (6 pemeriksaan)");
        else
            $display("tb_hcpu_telemetry: %0d GAGAL", errors);
        $finish;
    end

    initial begin
        #2_000_000;
        $display("tb_hcpu_telemetry: GAGAL -- waktu habis, handshake menggantung");
        $finish;
    end

endmodule

`default_nettype wire
