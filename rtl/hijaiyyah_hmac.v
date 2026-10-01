// hijaiyyah_hmac.v — HMAC-SHA256 (RFC 2104 / FIPS 198-1) over a byte stream.
//
//     MAC = H( (K ^ opad) || H( (K ^ ipad) || m ) )
//
// This is Ka'bah lapis 3 -- the one layer that carries the security -- moved
// from software (src/hijaiyyah/crypto/signing.py, hmac.new) into logic. It is
// the standard construction, unchanged; nothing here is new cryptography.
//
// KEY. `key` is K already padded to the 64-byte block, big-endian: the first
// key byte is key[511:504], zeros after the last. That covers every key of at
// most 64 bytes, which includes every key the repository derives (32 bytes).
// A longer key is, by RFC 2104, first replaced with H(K); the caller does
// that -- it is one more pass through hijaiyyah_sha256_stream, not a second design.
//
// One hijaiyyah_sha256_stream serves both passes: the inner hash takes the caller's
// bytes, the outer hash takes the 32 inner-digest bytes from here. Timing is
// the same for every key and message of a given length.

`default_nettype none

module hijaiyyah_hmac (
    input  wire         clk,
    input  wire         rst_n,

    input  wire         start,       // pulse, needs idle; samples key
    input  wire [511:0] key,

    input  wire         byte_valid,
    input  wire [7:0]   byte_in,
    output wire         byte_ready,
    input  wire         finish,      // message ended (pulse, when byte_ready)

    output wire         idle,
    output reg          done,        // one-clock pulse; mac valid from here
    output reg  [255:0] mac
);

    localparam [2:0] S_IDLE   = 3'd0;
    localparam [2:0] S_INNER  = 3'd1;
    localparam [2:0] S_OSTART = 3'd2;
    localparam [2:0] S_OFEED  = 3'd3;
    localparam [2:0] S_OFIN   = 3'd4;
    localparam [2:0] S_OWAIT  = 3'd5;

    localparam [511:0] IPAD = {64{8'h36}};
    localparam [511:0] OPAD = {64{8'h5c}};

    reg [2:0]   phase;
    reg [511:0] key_q;
    reg [255:0] inner;       // inner digest, shifted out a byte at a time
    reg [5:0]   sent;        // inner bytes fed to the outer hash

    wire         s_done, s_ready;
    wire [255:0] s_digest;

    wire         s_start  = (phase == S_IDLE  && start) || (phase == S_OSTART);
    wire [511:0] s_prefix = (phase == S_IDLE) ? (key ^ IPAD) : (key_q ^ OPAD);
    wire         s_bvalid = (phase == S_INNER) ? byte_valid : (phase == S_OFEED);
    wire [7:0]   s_byte   = (phase == S_INNER) ? byte_in    : inner[255:248];
    wire         s_finish = (phase == S_INNER) ? finish     : (phase == S_OFIN);

    hijaiyyah_sha256_stream u_stream (
        .clk        (clk),
        .rst_n      (rst_n),
        .start      (s_start),
        .use_prefix (1'b1),
        .prefix     (s_prefix),
        .byte_valid (s_bvalid && s_ready),
        .byte_in    (s_byte),
        .byte_ready (s_ready),
        .finish     (s_finish && s_ready),
        .idle       (),
        .done       (s_done),
        .digest     (s_digest)
    );

    assign idle       = (phase == S_IDLE);
    assign byte_ready = (phase == S_INNER) && s_ready;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase <= S_IDLE;
            key_q <= 512'd0;
            inner <= 256'd0;
            sent  <= 6'd0;
            done  <= 1'b0;
            mac   <= 256'd0;
        end else begin
            done <= 1'b0;
            case (phase)
                S_IDLE: begin
                    if (start) begin
                        key_q <= key;
                        phase <= S_INNER;
                    end
                end

                S_INNER: begin
                    if (s_done) begin
                        inner <= s_digest;
                        phase <= S_OSTART;
                    end
                end

                // s_start is high this clock (stream is idle again).
                S_OSTART: begin
                    sent  <= 6'd0;
                    phase <= S_OFEED;
                end

                S_OFEED: begin
                    if (s_ready) begin
                        inner <= {inner[247:0], 8'h00};
                        sent  <= sent + 6'd1;
                        if (sent == 6'd31)
                            phase <= S_OFIN;
                    end
                end

                S_OFIN: begin
                    if (s_ready)
                        phase <= S_OWAIT;
                end

                S_OWAIT: begin
                    if (s_done) begin
                        mac   <= s_digest;
                        done  <= 1'b1;
                        phase <= S_IDLE;
                    end
                end

                default: phase <= S_IDLE;
            endcase
        end
    end

endmodule

`default_nettype wire
