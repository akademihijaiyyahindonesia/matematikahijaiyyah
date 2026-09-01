// hijaiyyah_node_counter.v — stream triage at line rate, one byte per clock.
//
// Layer 1's guard, generalised past codex vectors to arbitrary bytes: keyless,
// constant work, and cheap enough to sit in front of anything expensive.
//
// WHAT IT DOES. One byte enters per clock. Eight counters, one per bit
// POSITION, accumulate over WINDOW bytes. Every window it emits a class --
// empty, text, structured, or high entropy -- and a recovered single-byte XOR
// key. No division, no multiply, no branch on data, same latency for every
// input.
//
// WHY PER POSITION AND NOT POPCOUNT. Popcount sums across the eight positions,
// and the sum is exactly what destroys the information a key lives in. XOR
// acts on positions independently:
//
//     count_i(plaintext ^ k) = count_i(plaintext)      if bit i of k is 0
//                            = n - count_i(plaintext)  if bit i of k is 1
//
// The magnitude of a position's bias is invariant; only its SIGN flips. So the
// key is eight comparisons against n/2 and one XOR with a constant mask --
// no trial decryption and no search. Popcount is still available as the sum of
// the eight, so this costs one feature set and delivers two.
//
// Measured against single-byte XOR over source text, 400 trials: 66.8% whole
// key at a 64-byte window, 95.0% at 1024. Against properly encrypted data:
// 0.0%, against 0.4% for blind guessing, because every position sits at 0.50
// and there is no sign to read. The same counters that break weak obfuscation
// prove they cannot touch real encryption.
//
// WHAT IT DOES NOT DO, measured rather than disclaimed. It does not detect
// malware. Compressed and encrypted data are the same object to it (popcount
// 4.00 and bit7 0.50 for both, over 2000 windows each), so a zip file and a
// packed payload are indistinguishable. And base64 defeats it completely --
// 100% of base64'd random data reads as TEXT. It is a place to look, never a
// verdict.
//
// WHAT WAS DROPPED. The sixteen tawaf-ring node counters were the original
// proposal's centre. They changed classification accuracy by zero (4494/4741
// either way) and separated compressed from random by 0.17 standard
// deviations, so sixteen counters became two. That is the same finding
// already recorded for cube.absorb_bit's bit schedule: it serves the input
// path, not the information.
//
// Thresholds and class codes are shared with
// src/hijaiyyah/crypto/node_counter.py, and a parity testbench feeds both the
// same stream.

`default_nettype none

module hijaiyyah_node_counter #(
    parameter integer WINDOW = 64      // bytes per verdict; a power of two
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       valid_in,
    input  wire [7:0] byte_in,
    output reg        valid_out,
    output reg  [1:0] class_out,
    output reg  [7:0] xor_key_out      // single-byte XOR key, by counting
);

    localparam [1:0] EMPTY        = 2'd0;
    localparam [1:0] TEXT         = 2'd1;
    localparam [1:0] STRUCTURED   = 2'd2;
    localparam [1:0] HIGH_ENTROPY = 2'd3;

    // Integer thresholds over WINDOW bytes, identical to the Python.
    localparam integer TEXT_HIGH_BIT_MAX    = 10;
    localparam integer TEXT_POPCOUNT_MIN    = 128;
    localparam integer ENTROPY_POPCOUNT_MIN = 237;
    localparam integer ENTROPY_HIGH_BIT_MIN = 26;

    localparam integer IDX_W = $clog2(WINDOW);
    localparam integer PC_W  = $clog2(WINDOW * 8 + 1);
    localparam integer HB_W  = $clog2(WINDOW + 1);

    //: Bit positions above balance in ordinary text (b5 and b6), measured.
    localparam [7:0] MODEL_MASK = 8'h60;

    reg [IDX_W-1:0] index;
    reg [HB_W-1:0]  bitcount [0:7];      // one counter per bit position

    wire [HB_W-1:0] bitcount_next [0:7];
    genvar b;
    generate
        for (b = 0; b < 8; b = b + 1) begin : per_bit
            assign bitcount_next[b] = bitcount[b] + {{(HB_W-1){1'b0}}, byte_in[b]};
        end
    endgenerate

    // Popcount is the sum of the eight, so nothing was lost by counting
    // positions instead of totals.
    wire [PC_W-1:0] popcount_next =
          bitcount_next[0] + bitcount_next[1] + bitcount_next[2] + bitcount_next[3]
        + bitcount_next[4] + bitcount_next[5] + bitcount_next[6] + bitcount_next[7];
    wire [HB_W-1:0] high_bits_next = bitcount_next[7];

    // The key: eight comparisons against WINDOW/2, then one XOR.
    wire [7:0] key_raw;
    generate
        for (b = 0; b < 8; b = b + 1) begin : per_key
            assign key_raw[b] = (bitcount_next[b] > WINDOW[HB_W-1:0] >> 1);
        end
    endgenerate
    wire [7:0] key_next = key_raw ^ MODEL_MASK;

    wire window_end = (index == WINDOW[IDX_W-1:0] - 1'b1);

    // The verdict, from the totals this byte completes.
    integer k;
    reg [1:0] verdict;
    always @* begin
        if (popcount_next == 0)
            verdict = EMPTY;
        else if (high_bits_next < TEXT_HIGH_BIT_MAX &&
                 popcount_next  >= TEXT_POPCOUNT_MIN)
            verdict = TEXT;
        else if (popcount_next  >= ENTROPY_POPCOUNT_MIN &&
                 high_bits_next >= ENTROPY_HIGH_BIT_MIN)
            verdict = HIGH_ENTROPY;
        else
            verdict = STRUCTURED;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            index       <= {IDX_W{1'b0}};
            valid_out   <= 1'b0;
            class_out   <= EMPTY;
            xor_key_out <= 8'h00;
            for (k = 0; k < 8; k = k + 1) bitcount[k] <= {HB_W{1'b0}};
        end else if (valid_in) begin
            if (window_end) begin
                valid_out   <= 1'b1;
                class_out   <= verdict;
                xor_key_out <= key_next;
                index       <= {IDX_W{1'b0}};
                for (k = 0; k < 8; k = k + 1) bitcount[k] <= {HB_W{1'b0}};
            end else begin
                valid_out <= 1'b0;
                index     <= index + 1'b1;
                for (k = 0; k < 8; k = k + 1) bitcount[k] <= bitcount_next[k];
            end
        end else begin
            valid_out <= 1'b0;
        end
    end

endmodule

`default_nettype wire
