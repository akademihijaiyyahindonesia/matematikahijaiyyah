// hijaiyyah_kabah_top.v — Ka'bah, whole, in gates.
//
// Every piece verified on its own already; this is the one place that says
// how they fit, which is the same thing kabah.py does for the Python. Bits
// arrive on a wire with no byte boundary and leave as a permuted 1600-bit
// state, with the stream's structure reported alongside.
//
//   bits, one per clock
//        |  CMASS: deserialise at the discovered phase       (hijaiyyah_wave)
//        v
//   bytes, one per 8 clocks
//        |--> jamrah gate: seven nodes, one pulse            (per byte, free)
//        |--> node counter: class + XOR key per 64 bytes     (triage)
//        |
//        |  in gate_mode the gate is a GATE: only bytes that pass reach the
//        |  sponge, and the POSITION of the first refusal is held on
//        |  break_at -- "the stream broke at byte 1,043", not "the stream
//        |  broke". Without that the gate was a reporter wired to nothing,
//        |  which is worse than no gate because the output looks like
//        |  enforcement.
//        v
//   lanes, one per 8 bytes
//        |  sponge: 16 lanes onto the tawaf ring             (rate = 1024 bit)
//        v
//   permutation: 28 rounds, paced by the impulser            (310 clocks)
//        v
//   state, 1600 bits, on out_state for the caller to squeeze
//
// WHAT CARRIES WHAT, because a diagram invites the wrong reading. The gate
// and the counter are keyless triage: they reject or classify cheaply so the
// expensive path is not spent on obvious cases, and they prove nothing about
// origin. The sponge is [EH] -- measured, not cryptanalysed. **Layer 3,
// HMAC-SHA256 over a seal-bound key, is the security, and it is NOT in this
// module**: there is no SHA-256 core in this repository. What comes out of
// here is unauthenticated until software signs it.
//
// Phase discovery is also software: finding the byte boundary needs a 256-bin
// index-of-coincidence histogram and runs once per stream, not per clock.
// `phase` is an input.
//
// So this is the line-rate half of Ka'bah, complete and honest about its
// edges. The other half is in src/hijaiyyah/crypto/.
//
// MEASURED, whole, on a Tang Nano 9K (GW1NR-9: 8,640 LUT4 / 6,693 FF).
// Generic 4-LUT mapping, flattened -- not a vendor fitting report, and Fmax
// is still unmeasured:
//
//     SLICE_BYTES    LUT4          FF     clocks per permutation
//               8   6,910 (80%)   2,009        786
//              25   8,096 (94%)   2,007        310
//
// Those were 6,231 (72%) and 7,426 (85%) when this header was first written,
// and they went stale in the very next commit: making the gate actually gate
// -- gate_mode, break_at, break_count, the bits_ready backpressure -- cost
// ~670 LUT4 and was never re-synthesised. At SLICE=25 the margin fell from
// 15% of the board to 6%, or 544 LUT4 spare. Re-measured with yosys 0.68,
// `synth -flatten` then `abc -lut 4`. A synthesis number that is not re-run
// after the module changes is a claim about a design that no longer exists.
//
// Both fit. At SLICE=25 and the board's own 27 MHz crystal -- no overclocking
// -- the sponge turns 87,097 permutations per second, which is 11.15 MB/s at
// its 128-byte rate.
//
// THAT IS NOT THIS MODULE'S THROUGHPUT, and quoting it as such overstated the
// system by 4x for many commits. This top is fed a BIT STREAM. The
// deserialiser takes one bit per clock, so a byte costs 8 clocks before the
// gate, the counter, or the sponge sees it -- 3.3x the sponge's own 2.42
// clocks per byte. The sponge is not the bottleneck here; the front end is.
//
// Worse, the permutation does not hide behind the deserialiser. It asserts
// backpressure and stalls it for the full 310 clocks, so the costs add:
//
//     deserialiser      8.00 clocks/byte
//     permutation       2.42 clocks/byte   (310 per 128)
//     ------------------------------------
//     system           10.42 clocks/byte    2.59 MB/s at 27 MHz
//
// MEASURED, not modelled: the end-to-end run below costs 3,698 clocks for 383
// bytes, 622 of them held. 622 is exactly 2 x 310 -- the two permutations that
// fired, each stalling in full. 8 + 622/383 = 9.62 against 9.66 observed; the
// gap is that 383 bytes is 2.99 rate blocks, so only two permutations ran.
//
// A FIFO between deserialiser and sponge would recover this: 310 clocks fit
// inside the 1,024 the next 128 bytes take to arrive, so the permutation could
// hide entirely and the system would run at the deserialiser's 8.00. Not
// built, not measured -- [EH].
//
// VERIFIED END TO END: 3,069 raw bits at an arbitrary offset, deserialised at
// the discovered phase, gated, classified, assembled, absorbed over 47 lanes
// and two permutations, landing on exactly the state cube.py computes. The
// backpressure is exercised in that run -- 622 clocks held -- because a source
// that ignores it loses every lane offered during a permutation.
//
// One bug this integration found that nothing before it could: the
// deserialiser put the first data bit at shifter[0] instead of shifter[7], so
// the very FIRST byte of every stream was wrong and every byte after it was
// right. tb_hijaiyyah_wave passed 78/78 with that present, because a
// classifier over 64-byte windows cannot see one wrong byte. Only assembling
// lanes and comparing them against cube.py exposed it.

`default_nettype none

module hijaiyyah_kabah_top #(
    parameter integer SLICE_BYTES = 25,   // substitution width; 200 % it == 0
    parameter integer WINDOW      = 64    // bytes per classification verdict
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          standby,
    input  wire          load,          // clear the sponge state
    input  wire          gate_mode,     // 1 = only gated bytes reach the sponge

    // the wire
    input  wire [2:0]    phase,         // byte boundary, found in software
    input  wire          bit_valid,
    input  wire          bit_in,

    // triage, per byte and per window
    output wire          gate_pulse,    // this byte names a letter
    output wire [3:0]    gate_root,     // its popcount, the tree's root
    output reg           break_valid,   // the stream broke at least once
    output reg  [31:0]   break_at,      // byte position of the FIRST break
    output reg  [15:0]   break_count,   // how many bytes the gate refused
    output wire          class_valid,
    output wire [1:0]    class_out,
    output wire [7:0]    xor_key_out,

    // the sponge
    output wire          bits_ready,    // the source MUST hold bits when low
    output wire          absorbing,     // a lane can be taken
    output wire          permuting,
    output wire [1599:0] out_state
);

    // ---- CMASS: bits to bytes at the discovered boundary ---------------
    wire       byte_valid;
    wire [7:0] byte_out;

    hijaiyyah_deserialiser u_des (
        .clk(clk), .rst_n(rst_n), .phase(phase),
        .bit_valid(bit_valid), .bit_in(bit_in),
        .byte_valid(byte_valid), .byte_out(byte_out));

    // ---- triage: seven throws per byte, one class per window -----------
    wire [1:0] n0, n1, n2, n3;
    wire [2:0] n4, n5;
    wire [3:0] n6;

    hijaiyyah_jamrah_gate u_gate (
        .clk(clk), .rst_n(rst_n), .valid_in(byte_valid), .byte_in(byte_out),
        .pulse(gate_pulse), .root(gate_root),
        .node0(n0), .node1(n1), .node2(n2), .node3(n3),
        .node4(n4), .node5(n5), .node6(n6));

    hijaiyyah_node_counter #(.WINDOW(WINDOW)) u_count (
        .clk(clk), .rst_n(rst_n), .valid_in(byte_valid), .byte_in(byte_out),
        .valid_out(class_valid), .class_out(class_out),
        .xor_key_out(xor_key_out));

    // ---- the gate opens per parse, and the break point is joined -------
    //
    // Without this the gate was a REPORTER, not a gate: it published
    // `gate_pulse` on a port and the sponge absorbed every byte regardless.
    // That is a detector wired to nothing, which is worse than no detector,
    // because the output looks like enforcement.
    //
    // In `gate_mode` only bytes the gate passes reach the sponge. And a
    // refusal is not merely counted -- the POSITION of the first one is held,
    // because "the stream broke" is not actionable and "the stream broke at
    // byte 1,043" is. That is the break point joined back.
    //
    // The mode is a mode rather than always on, and deliberately: the gate's
    // check is that a byte names a letter, 1..28. That is true of a codex
    // record and false of almost every other byte, so enforcing it on
    // arbitrary data would reject nearly everything. Gate what is parsed as
    // letters; pass through what is not.

    reg [31:0] position;

    // The gate registers its verdict, so the byte it belongs to has already
    // moved on by the time `gate_pulse` is readable. Recompute the same
    // predicate combinationally for the admit decision -- one comparator, and
    // it keeps the decision in step with the byte it is about.
    wire gate_pulse_now = (byte_out != 8'd0) && (byte_out <= 8'd28);

    wire byte_admitted = byte_valid && (!gate_mode || gate_pulse_now);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            position    <= 32'd0;
            break_valid <= 1'b0;
            break_at    <= 32'd0;
            break_count <= 16'd0;
        end else if (load) begin
            position    <= 32'd0;
            break_valid <= 1'b0;
            break_at    <= 32'd0;
            break_count <= 16'd0;
        end else if (standby) begin
            position    <= position;
        end else if (byte_valid) begin
            position <= position + 32'd1;
            if (gate_mode && !gate_pulse_now) begin
                break_count <= break_count + 16'd1;
                if (!break_valid) begin
                    break_valid <= 1'b1;
                    break_at    <= position;
                end
            end
        end
    end

    // ---- bytes to lanes ------------------------------------------------
    reg [2:0]  lane_fill;
    reg [63:0] lane_shift;
    reg [63:0] lane_reg;
    reg        lane_valid;

    wire lane_ready;

    // BACKPRESSURE, because a permutation is 310 clocks and bytes do not stop
    // arriving on their own. Without it the sponge simply drops every lane
    // offered while it is busy -- and a dropped lane produces a state that is
    // fully defined and wrong, which is the shape of bug that hides best. The
    // source must hold `bit_valid` low whenever `bits_ready` is low; nothing
    // here can enforce that on a wire it does not drive.
    assign bits_ready = lane_ready;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lane_fill  <= 3'd0;
            lane_shift <= 64'd0;
            lane_reg   <= 64'd0;
            lane_valid <= 1'b0;
        end else if (standby) begin
            lane_valid <= lane_valid;
        end else begin
            lane_valid <= 1'b0;
            if (byte_admitted) begin
                // Little-endian within the lane, matching cube.py's
                // int.from_bytes(..., "little").
                lane_shift <= {byte_out, lane_shift[63:8]};
                if (lane_fill == 3'd7) begin
                    // Register the assembled lane with its valid. Driving
                    // `lane_in` combinationally from `byte_out` presented the
                    // NEXT byte by the time the registered valid arrived.
                    lane_reg   <= {byte_out, lane_shift[63:8]};
                    lane_fill  <= 3'd0;
                    lane_valid <= 1'b1;
                end else begin
                    lane_fill <= lane_fill + 3'd1;
                end
            end
        end
    end

    wire [63:0] lane_in = lane_reg;

    // ---- the sponge and the permutation --------------------------------
    wire        perm_start, perm_enable, perm_done;
    wire        absorb_valid, stall, idle;
    wire [4:0]  absorb_step;
    wire [63:0] absorb_data;
    wire        lin_pulse, sub_pulse;
    wire [7:0]  round_index;
    wire        sponge_busy;

    assign absorbing = lane_ready;
    assign permuting = sponge_busy;

    hijaiyyah_sponge u_sponge (
        .clk(clk), .rst_n(rst_n), .load(load),
        .lane_valid(lane_valid), .lane_in(lane_in),
        .lane_ready(lane_ready), .busy(sponge_busy), .out_state(out_state),
        .perm_start(perm_start), .perm_enable(perm_enable), .perm_done(perm_done),
        .absorb_valid(absorb_valid), .absorb_step(absorb_step),
        .absorb_data(absorb_data));

    hijaiyyah_ramal_impulse #(.ROUNDS(28), .MAX_STRIDE(1)) u_impulse (
        .clk(clk), .rst_n(rst_n), .start(perm_start), .enable(perm_enable),
        .stall(stall), .lin_pulse(lin_pulse), .sub_pulse(sub_pulse),
        .round_index(round_index), .done(perm_done));

    hijaiyyah_rotate_core #(.SLICE_BYTES(SLICE_BYTES)) u_core (
        .clk(clk), .rst_n(rst_n), .standby(standby), .load(load),
        .in_state({1600{1'b0}}),
        .absorb_valid(absorb_valid), .absorb_step(absorb_step),
        .absorb_data(absorb_data),
        .lin_pulse(lin_pulse), .sub_pulse(sub_pulse), .round_index(round_index),
        .stall(stall), .idle(idle), .out_state(out_state));

endmodule

`default_nettype wire
