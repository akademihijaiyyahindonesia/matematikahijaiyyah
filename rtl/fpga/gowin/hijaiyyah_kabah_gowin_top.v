// ============================================================================
// Ka'bah Gowin FPGA Wrapper — hijaiyyah_kabah_gowin_top.v
// (c) 2026 Maulana Amratulloh
// ============================================================================
//
// hijaiyyah_kabah_top.v cannot be placed on any board in this class as a raw
// top level: its interface is 1,665 port bits, of which out_state alone is
// 1,600 (96%) — a single verification-only port, read by nothing but a
// testbench's own comparison, that outnumbers the Tang Nano 20K's 384 IOB
// by 4x. No board this size will ever have that many
// pins; pin count does not scale with LUT capacity, so a bigger chip does not
// fix this. It needs exactly what hcpu_gowin_top.v is for the HCPU core: a
// wrapper that keeps the wide internal signal internal and pins out only
// what a board actually has wires for. rtl/hijaiyyah_kabah_top.v itself is
// unchanged — its raw interface is honestly wide, on purpose, the same way
// hcpu_top.v's is.
//
// ── The narrowed interface ──────────────────────────────────────────────
//
//   clk_27m, btn_rst_n, uart_rxd, uart_txd, led[5:0]   — 10 pins.
//
// Everything else — phase, gate_mode, standby, the byte-serial bit_in/
// bit_valid pump, and out_state itself — is wired internally to
// hijaiyyah_kabah_top and never reaches a package pin.
//
// ── The protocol ────────────────────────────────────────────────────────
//
// The host sends exactly 128 bytes over UART — one full rate block (16
// lanes x 8 bytes, matching src/hijaiyyah/crypto/cube.py's RATE=128 — and
// the wrapper answers with exactly 200 bytes: out_state, most-significant
// byte first (out_state[1599:1592] first, out_state[7:0] last). Built with
// KABAH_WITH_HMAC defined, as the UART slot is since 3 October 2026, 32 more
// bytes follow: the HMAC-SHA256 tag of those 200 bytes, most-significant byte
// first, so a reply is 232 bytes. It then waits for the next 128-byte block. `load` fires once, for one clock,
// right after reset — clearing the sponge — and never again, so a host that
// keeps sending blocks gets a real multi-block absorb, not 128 bytes
// re-hashed in isolation each time.
//
// phase is wired to a constant 0, not exposed as an input. hijaiyyah_
// deserialiser.v's phase input exists to find a byte boundary in a BIT
// stream with unknown alignment; that discovery is deliberately a software
// step done once per stream (see hijaiyyah_kabah_top.v's own header), not a
// hardware concern. UART has no such ambiguity — rx_valid pulses once per
// whole received byte — so feeding the deserialiser starting a fresh byte
// exactly when a UART byte arrives, with phase=0, reproduces the same byte
// boundary UART already established. Nothing is skipped or discovered
// because nothing needs to be.
//
// gate_mode is a compile-time parameter (default 0, pass every byte to the
// sponge) rather than a pin, because neither Tang Nano board breaks out a
// physical switch for it; changing it means re-synthesising, same as
// choosing SLICE_BYTES already does one level down.
//
// Bit order into bit_in is LSB-first, matching two things at once rather
// than one: hcpu_uart_rx.v's own DATA state comment (`shifter <=
// {rx_sync, shifter[7:1]}; // LSB first`) describes UART's native wire
// order, and hijaiyyah_deserialiser.v's `{bit_in, shifter[7:1]}` shift
// wants the same construction fed the same way — confirmed empirically
// against src/hijaiyyah/crypto/cube.py's absorb_lane/permute for
// bytes(range(128)): LSB-first through the full pipeline (deserialiser,
// jamrah gate, node counter, lane assembly, sponge, three permutations)
// lands on exactly cube.py's state; MSB-first does not (it reconstructs
// every byte bit-reversed within its lane position — a testbench bug this
// wrapper's own construction avoids by starting from the confirmed-correct
// order rather than re-deriving it). See tb_hijaiyyah_kabah_gowin_top.v.
//
// ── MEASURED, 4 September 2026 ──────────────────────────────────────────
//
// yosys 0.68 (-nodsp) -> nextpnr-himbaechel 0.11.1 -> gowin_pack. The IOB
// problem this wrapper exists to solve is what it solves: 1,665 port bits
// down to 10 pins.
//
//     GW2AR-18C (Tang Nano 20K)   IOB   10/  384    2%
//
// hijaiyyah_kabah_top.v alone measures 8,096 LUT4 at SLICE_BYTES=25 -- see
// this module's own header -- and the UART RX/TX plus feed/dump FSM sit on
// top of that:
//
//     GW2AR-18C  (Tang Nano 20K)  LUT4  12,061/ 20,736   58%   fits, routed
//                                  DFF   1,965/ 15,552   12%
//                                  BSRAM      0/     46    0%
//                                  Fmax           165.98 MHz
//         gowin_pack succeeded, a real 4.6 MB .fs bitstream -- the full
//         chain end to end, not placement alone.
//
//         Re-measured 2026-09-10, and this time the bitstream was RUN:
//         kabah_uart_test.py reports 2/2 frames, 400/400 bytes matching
//         cube.py, chained across frames with no reset between them. The
//         figures moved because the reset synchroniser below stopped being
//         an asynchronous level off pin 87 -- 117.91 -> 165.98 MHz, and
//         -41 LUT4 / +2 DFF, the +2 being btn_q. Fmax is the post-routing
//         number, not the 70.48 MHz nextpnr prints after placement.
//
// Same board as the HCPU core, arrived at independently from the Ka'bah
// side.
//
// Reproduced 5 September 2026 as `make -C rtl/fpga/gowin kabah_bitstream`,
// not a remembered command -- same figures, confirming they were never a
// one-off. Fingerprinted the same way hcpu_gowin_top.v is, but as its own
// hash over its own dependency set (see tests/test_integrity/
// test_place_and_route.py's KABAH_FINGERPRINTED): touching a file only
// HCPU uses should not demand this wrapper be re-measured, and touching
// hijaiyyah_sponge.v should not demand HCPU's own numbers be re-measured.
//
// Fingerprint restamped 2026-09-10 WITHOUT a new place-and-route run, and the
// justification is mechanical rather than a promise: the institution changed
// (HMCL became a research unit under Yayasan Akademi Hijaiyyah Indonesia, and
// the rights line became the inventor personally), which rewrote one comment
// line in every fingerprinted source. Reversing only those copyright lines in
// memory reproduces the previously recorded hash exactly, for this wrapper and
// for Ka'bah's -- so the sweep is provably the entire delta and no design byte
// moved. The measured figures above still describe this RTL.
//
// Fingerprint restamped again 2026-09-14, and this time WITH a fresh place and
// route -- the figures above are what it returned, unchanged to the last digit:
// 12,061 LUT4, 1,965 DFF, 0 BSRAM, 165.98 MHz after routing, zero hold and
// zero setup violations.
//
// WHY IT MOVED AT ALL, since no Ka'bah source changed: hcpu_gowin.cst is in
// this wrapper's dependency set, and H-ISA v1.2 added six TF-card pins to it.
// This design has no such ports, and nextpnr says so and carries on --
// `Info: Cell sd_clk not found`, six times, Info and not error. The
// constraints are inert here. The hash still had to move because the file did,
// which is the guard working as intended: it cannot tell a constraint that
// matters from one that does not, so it demands the measurement rather than
// guessing. The measurement was taken.
//
// Not packed in this run: `make hijaiyyah_kabah_gowin_top_pnr.json` stops at
// the routed JSON. The gowin_pack line above belongs to the 5 September run
// and is left standing as that run's record, not re-claimed as this one's.
//
// ── LAYER 3 ON THE WAY OUT, 3 October 2026 — owner's decision ───────────
//
// The owner's target: HMAC-SHA256 instantiated by the Ka'bah path, in the
// UART slot only, with a fixed test key. hijaiyyah_hmac is instantiated here,
// under `ifdef KABAH_WITH_HMAC, which only the UART slot's own build defines
// (KABAH_L3_DEFINE in the Makefile). hijaiyyah_kabah_top.v and
// hijaiyyah_wave.v are unchanged and still hold no SHA-256 core;
// kabah_hdmi_top.v and hijaiyyah_cosmictera_gowin_top.v are unchanged too,
// define nothing, and so build this wrapper as it was.
//
// THE KEY IS A PUBLIC TEST KEY: RFC 4231 test case 1, twenty bytes of 0x0b.
// A tag under it proves the path -- the bytes that left were the bytes that
// were signed -- and secures nothing, because anyone can compute it. Ka'bah's
// output stays unauthenticated until it is signed under a key that is secret.
//
// Everything above this block measures the wrapper WITHOUT layer 3 (what
// the macro left undefined still builds). With it, `make kabah_bitstream`, same flags:
//
//     GW2AR-18C  (Tang Nano 20K)  IOB       10/    384    2%
//                                  LUT4  15,030/ 20,736   72%   fits, routed
//                                  DFF    4,132/ 15,552   26%
//                                  ALU      604/ 15,552    3%
//                                  BSRAM      0/     46    0%
//
// +2,969 LUT4 and +2,167 DFF against 12,061 / 1,965. Place and route took
// about 14 minutes. The bitstream is 4,618,782 bytes, sha256
// fdc84e3d1cf2a565fa495ecbdd3b10d792464f1e8385240d77e3c39492a86b49.
//
// FMAX IS NOT QUOTED. nextpnr prints 97.93 MHz after routing and judges it
// against its default 12 MHz, not against a constraint of this design. What
// the number shows is a margin far above the 27 MHz the board runs at.
//
// In simulation, through the UART pins only (tb_hijaiyyah_kabah_gowin_top.v):
// two frames, 400/400 state bytes matching cube.py and 64/64 tag bytes
// matching hmac/hashlib. Eleven sabotages of the signing path turn that bench
// red. THIS BITSTREAM HAS NOT RUN ON THE BOARD: the board result above
// (2/2 frames, 400/400 bytes) belongs to the wrapper without layer 3.
// RTL FINGERPRINT: 76235f2e973b5881937ed5a6779dba08403cf895ad11a6c86aad5721d70c04c6
//
`include "hcpu_pkg.vh"

`default_nettype none

module hijaiyyah_kabah_gowin_top #(
    parameter USE_PLL   = 0,        // 0: run at 27 MHz; 1: use the rPLL
    parameter BAUD      = 115200,
    parameter GATE_MODE = 1'b0      // compile-time; no board switch for it
) (
    input  wire        clk_27m,     // 27 MHz onboard oscillator
    input  wire        btn_rst_n,   // reset button — active low
    input  wire        uart_rxd,    // UART RX ← USB bridge, 128 bytes/frame
    output wire        uart_txd,    // UART TX → USB bridge, 200 bytes/frame
    output wire [5:0]  led          // 6 LEDs — active low
);

    localparam OSC_HZ = 27_000_000;
    localparam SYS_HZ = (USE_PLL != 0) ? (OSC_HZ * 2) : OSC_HZ;

    wire clk_sys;
    wire pll_locked;

    generate
        if (USE_PLL != 0) begin : g_pll
            // Replace with the Gowin IDE's generated rPLL for 27 -> 54 MHz.
            Gowin_rPLL u_pll (
                .clkout (clk_sys),
                .lock   (pll_locked),
                .clkin  (clk_27m)
            );
        end else begin : g_direct
            assign clk_sys    = clk_27m;
            assign pll_locked = 1'b1;
        end
    endgenerate

    // ── Reset synchronizer ──────────────────────────────────────
    // Edge-detected, not level-gated, and hcpu_gowin_top.v paid for the
    // lesson: btn_rst_n is pin 87 = MODE1 in the shared hcpu_gowin.cst, and
    // this board holds it low. As an asynchronous level it pinned sys_rst_n
    // at 0 forever -- the bitstream configures and then executes nothing,
    // with no UART and nothing on the board to say why. A stuck level now
    // costs one pulse instead of a deadlock, and a real press still resets.
    // The initial values matter: without them rst_sync starts X in
    // simulation, where the old async branch used to define it.
    reg [2:0] rst_sync = 3'b000;
    reg [1:0] btn_q    = 2'b00;
    wire      sys_rst_n = rst_sync[2];

    always @(posedge clk_sys) begin
        btn_q <= {btn_q[0], btn_rst_n};
        if (btn_q[1] & ~btn_q[0])
            rst_sync <= 3'b000;
        else
            rst_sync <= {rst_sync[1:0], pll_locked};
    end

    // ── UART ──────────────────────────────────────────────────
    wire [7:0] rx_data;
    wire       rx_valid;
    wire       rx_frame_err;

    hcpu_uart_rx #(.CLK_HZ(SYS_HZ), .BAUD(BAUD)) u_rx (
        .clk          (clk_sys),
        .rst_n        (sys_rst_n),
        .rx_in        (uart_rxd),
        .rx_data      (rx_data),
        .rx_valid     (rx_valid),
        .rx_frame_err (rx_frame_err)
    );

    wire [7:0] tx_data;
    reg        tx_start_r;
    wire       tx_busy;

    hcpu_uart_tx #(.CLK_HZ(SYS_HZ), .BAUD(BAUD)) u_tx (
        .clk      (clk_sys),
        .rst_n    (sys_rst_n),
        .tx_data  (tx_data),
        .tx_start (tx_start_r),
        .tx_out   (uart_txd),
        .tx_busy  (tx_busy)
    );

    // A one-deep buffer for a received byte. UART's byte spacing at this
    // baud (~2,344 clocks at 115200/27 MHz) is huge next to the handful of
    // clocks the feed FSM below needs to drain one, so this never overruns
    // in practice -- but it is written to be correct by construction, not
    // by that margin: rx_consume clears it the same cycle the FSM below
    // takes it, and a same-cycle new arrival still lands correctly for the
    // cycle after.
    reg       rx_pend;
    reg [7:0] rx_pend_byte;
    reg       frame_err_sticky;

    // ── Layer 3 is a compile-time choice: `KABAH_WITH_HMAC ─────
    //
    // Undefined, every line synthesis sees is the line this file had before
    // 3 October 2026: the `else branches below are that text, untouched, so
    // kabah_hdmi_top.v and hijaiyyah_cosmictera_gowin_top.v -- which
    // instantiate this module and define nothing -- build what was measured
    // and run on the board. A parameter was tried first and was not enough:
    // the same wrapper with the layer switched off by a parameter placed at
    // 11,728 LUT4 against the recorded 12,133, because synthesis is sensitive
    // to the text it is given, not only to the logic that text means.
    //
    // Defined -- `make kabah_bitstream` and `make sim_kabah` define it -- the
    // reply is the 200 state bytes and then their 32-byte HMAC-SHA256 tag.
`ifdef KABAH_WITH_HMAC
    // A TEST KEY, fixed in the bitstream and published: the key of RFC 4231
    // test case 1, twenty bytes of 0x0b, padded to the 64-byte block. It
    // proves the path; it is not a secret and not a root of trust.
    localparam [511:0] HMAC_KEY = {{20{8'h0b}}, 352'd0};

    localparam ST_RECV = 3'd0, ST_FEED = 3'd1, ST_PERM = 3'd2, ST_DUMP = 3'd3,
               ST_SIGN = 3'd4, ST_TAG = 3'd5;
    reg [2:0] st;
`else
    localparam ST_RECV = 2'd0, ST_FEED = 2'd1, ST_PERM = 2'd2, ST_DUMP = 2'd3;
    reg [1:0] st;
`endif

    wire rx_consume = rx_pend && (st == ST_RECV);

    always @(posedge clk_sys or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            rx_pend          <= 1'b0;
            rx_pend_byte     <= 8'h00;
            frame_err_sticky <= 1'b0;
        end else begin
            if (rx_valid) begin
                rx_pend_byte <= rx_data;
                rx_pend      <= 1'b1;
                if (rx_frame_err) frame_err_sticky <= 1'b1;
            end else if (rx_consume) begin
                rx_pend <= 1'b0;
            end
        end
    end

    // `load` fires exactly once, one clock after reset releases.
    reg did_load;
    reg load_pulse;

    always @(posedge clk_sys or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            did_load   <= 1'b0;
            load_pulse <= 1'b0;
        end else begin
            load_pulse <= 1'b0;
            if (!did_load) begin
                load_pulse <= 1'b1;
                did_load   <= 1'b1;
            end
        end
    end

    // ── Ka'bah core ───────────────────────────────────────────
    wire        kabah_bv, kabah_bi;
    wire        bits_ready, absorbing, permuting;
    wire [1599:0] out_state;

    hijaiyyah_kabah_top #(.SLICE_BYTES(25), .WINDOW(64)) u_kabah (
        .clk         (clk_sys),
        .rst_n       (sys_rst_n),
        .standby     (1'b0),
        .load        (load_pulse),
        .gate_mode   (GATE_MODE),
        .phase       (3'd0),
        .bit_valid   (kabah_bv),
        .bit_in      (kabah_bi),
        .gate_pulse  (),
        .gate_root   (),
        .break_valid (),
        .break_at    (),
        .break_count (),
        .class_valid (),
        .class_out   (),
        .xor_key_out (),
        .bits_ready  (bits_ready),
        .absorbing   (absorbing),
        .permuting   (permuting),
        .out_state   (out_state)
    );

    // ── Bit-feed / permute-wait / dump FSM ─────────────────────
    //
    // ST_RECV takes one buffered byte and moves to ST_FEED. ST_FEED shifts
    // it into bit_in LSB-first, one bit per clock it is granted -- bits_
    // ready low means hold, exactly the backpressure discipline
    // tb_hijaiyyah_kabah_top.v already exercises, not a new contract. After
    // the 128th byte's 8th bit, ST_PERM waits for `permuting` to assert and
    // then to fall -- it must wait for the ASSERT first: sampled too early,
    // `permuting` reads 0 because the permutation has not started yet, and
    // out_state comes back as raw absorbed lanes instead of the permuted
    // state. Then ST_DUMP ships out_state out 200 bytes, MSB first.
    reg [7:0] cur_byte;
    reg [2:0] bit_idx;
    reg [7:0] byte_count;
    reg [7:0] dump_idx;
    reg       kabah_bv_r, kabah_bi_r;
    reg       perm_started;
    reg [7:0] tx_data_r;

    assign kabah_bv = kabah_bv_r;
    assign kabah_bi = kabah_bi_r;
    assign tx_data  = tx_data_r;

    // Combinational and keyed off dump_idx directly, this raced: dump_idx
    // advances the SAME edge tx_start_r pulses, so by the next edge -- when
    // u_tx actually samples tx_data -- dump_idx already named the NEXT
    // byte. Every pulse shipped the byte after the one it meant to, and
    // dump_idx=0 was never sent at all. Latching the byte into tx_data_r at
    // pulse time, from dump_idx's pre-increment value, is what
    // tb_hijaiyyah_kabah_gowin_top.v caught: it failed on exactly this
    // before the fix -- byte 0 missing, every later byte one ahead.
    wire [10:0] dump_bit_hi = 11'd1599 - ({3'b0, dump_idx} * 11'd8);

`ifdef KABAH_WITH_HMAC
    // ── Layer 3: HMAC-SHA256 over the 200 bytes that leave ─────
    //
    // The message is exactly what the wire carries: out_state, most-
    // significant byte first, each byte handed to the HMAC on the same edge
    // it is handed to the UART. A UART byte takes ~2,344 clocks and a SHA-256
    // block well under 200, so the HMAC has always taken the last byte before
    // the next is offered; h_bv holds until it has, so that is by
    // construction and not by that margin. After the 200th byte the message
    // is finished, and the 32 tag bytes follow the state on the same wire.
    reg          h_start;
    reg          h_bv;
    reg  [7:0]   h_byte;
    reg          fin_sent;
    reg  [5:0]   tag_idx;
    wire         h_ready, h_done;
    wire [255:0] h_mac;
    wire         h_fin = (st == ST_SIGN) && !fin_sent && !h_bv && h_ready;
    wire [7:0]   tag_byte = h_mac[({2'b00, 6'd31 - tag_idx} * 8'd8) +: 8];

    hijaiyyah_hmac u_hmac (
        .clk        (clk_sys),
        .rst_n      (sys_rst_n),
        .start      (h_start),
        .key        (HMAC_KEY),
        .byte_valid (h_bv),
        .byte_in    (h_byte),
        .byte_ready (h_ready),
        .finish     (h_fin),
        .idle       (),
        .done       (h_done),
        .mac        (h_mac)
    );

    always @(posedge clk_sys or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            st           <= ST_RECV;
            cur_byte     <= 8'h00;
            bit_idx      <= 3'd0;
            byte_count   <= 8'd0;
            dump_idx     <= 8'd0;
            kabah_bv_r   <= 1'b0;
            kabah_bi_r   <= 1'b0;
            perm_started <= 1'b0;
            tx_start_r   <= 1'b0;
            tx_data_r    <= 8'h00;
            h_start      <= 1'b0;
            h_bv         <= 1'b0;
            h_byte       <= 8'h00;
            fin_sent     <= 1'b0;
            tag_idx      <= 6'd0;
        end else begin
            tx_start_r <= 1'b0;
            kabah_bv_r <= 1'b0;
            h_start    <= 1'b0;
            if (h_bv && h_ready) h_bv <= 1'b0;

            case (st)
                ST_RECV: begin
                    if (rx_consume) begin
                        cur_byte <= rx_pend_byte;
                        bit_idx  <= 3'd0;
                        st       <= ST_FEED;
                    end
                end

                ST_FEED: begin
                    if (bits_ready) begin
                        kabah_bi_r <= cur_byte[bit_idx];
                        kabah_bv_r <= 1'b1;
                        if (bit_idx == 3'd7) begin
                            if (byte_count == 8'd127) begin
                                byte_count   <= 8'd0;
                                st           <= ST_PERM;
                                perm_started <= 1'b0;
                            end else begin
                                byte_count <= byte_count + 8'd1;
                                st         <= ST_RECV;
                            end
                        end else begin
                            bit_idx <= bit_idx + 3'd1;
                        end
                    end
                end

                ST_PERM: begin
                    if (!perm_started) begin
                        if (permuting) perm_started <= 1'b1;
                    end else if (!permuting) begin
                        dump_idx <= 8'd0;
                        h_start  <= 1'b1;
                        st       <= ST_DUMP;
                    end
                end

                ST_DUMP: begin
                    if (dump_idx == 8'd200) begin
                        fin_sent <= 1'b0;
                        st       <= ST_SIGN;
                    end else if (!tx_busy && !tx_start_r && !h_bv) begin
                        tx_data_r  <= out_state[dump_bit_hi -: 8];
                        h_byte     <= out_state[dump_bit_hi -: 8];
                        h_bv       <= 1'b1;
                        tx_start_r <= 1'b1;
                        dump_idx   <= dump_idx + 8'd1;
                    end
                end

                // The message ends once the HMAC has taken the 200th byte;
                // then wait for the tag.
                ST_SIGN: begin
                    if (h_fin) fin_sent <= 1'b1;
                    if (h_done) begin
                        tag_idx <= 6'd0;
                        st      <= ST_TAG;
                    end
                end

                // 32 tag bytes, most-significant first, after the state.
                ST_TAG: begin
                    if (!tx_busy && !tx_start_r) begin
                        tx_data_r  <= tag_byte;
                        tx_start_r <= 1'b1;
                        tag_idx    <= tag_idx + 6'd1;
                        if (tag_idx == 6'd31) st <= ST_RECV;
                    end
                end

                default: st <= ST_RECV;
            endcase
        end
    end
`else
    always @(posedge clk_sys or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            st           <= ST_RECV;
            cur_byte     <= 8'h00;
            bit_idx      <= 3'd0;
            byte_count   <= 8'd0;
            dump_idx     <= 8'd0;
            kabah_bv_r   <= 1'b0;
            kabah_bi_r   <= 1'b0;
            perm_started <= 1'b0;
            tx_start_r   <= 1'b0;
            tx_data_r    <= 8'h00;
        end else begin
            tx_start_r <= 1'b0;
            kabah_bv_r <= 1'b0;

            case (st)
                ST_RECV: begin
                    if (rx_consume) begin
                        cur_byte <= rx_pend_byte;
                        bit_idx  <= 3'd0;
                        st       <= ST_FEED;
                    end
                end

                ST_FEED: begin
                    if (bits_ready) begin
                        kabah_bi_r <= cur_byte[bit_idx];
                        kabah_bv_r <= 1'b1;
                        if (bit_idx == 3'd7) begin
                            if (byte_count == 8'd127) begin
                                byte_count   <= 8'd0;
                                st           <= ST_PERM;
                                perm_started <= 1'b0;
                            end else begin
                                byte_count <= byte_count + 8'd1;
                                st         <= ST_RECV;
                            end
                        end else begin
                            bit_idx <= bit_idx + 3'd1;
                        end
                    end
                end

                ST_PERM: begin
                    if (!perm_started) begin
                        if (permuting) perm_started <= 1'b1;
                    end else if (!permuting) begin
                        dump_idx <= 8'd0;
                        st       <= ST_DUMP;
                    end
                end

                ST_DUMP: begin
                    if (dump_idx == 8'd200) begin
                        st <= ST_RECV;
                    end else if (!tx_busy && !tx_start_r) begin
                        tx_data_r  <= out_state[dump_bit_hi -: 8];
                        tx_start_r <= 1'b1;
                        dump_idx   <= dump_idx + 8'd1;
                    end
                end
            endcase
        end
    end
`endif

    // ── LED mapping (active low) ────────────────────────────────
    // LED[0]: absorbing (a lane is being taken)
    // LED[1]: permuting (the 310-clock crunch)
    // LED[2]: shipping the state back out over UART
    // LED[3]: reset held
    // LED[4]: PLL locked
    // LED[5]: a UART frame error happened, ever, since reset
    assign led[0] = ~absorbing;
    assign led[1] = ~permuting;
`ifdef KABAH_WITH_HMAC
    assign led[2] = ~(st == ST_DUMP || st == ST_SIGN || st == ST_TAG);
`else
    assign led[2] = ~(st == ST_DUMP);
`endif
    assign led[3] = ~sys_rst_n;
    assign led[4] = ~pll_locked;
    assign led[5] = ~frame_err_sticky;

endmodule

`default_nettype wire
