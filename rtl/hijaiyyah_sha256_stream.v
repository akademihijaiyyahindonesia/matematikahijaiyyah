// hijaiyyah_sha256_stream.v — SHA-256 of a byte stream: padding, length, and blocks.
//
// hijaiyyah_sha256_core.v compresses blocks; this module turns a byte stream of any
// length into those blocks, then pads per FIPS 180-4 5.1.1:
//
//     message || 0x80 || 0x00 ... || bit length (64-bit, big-endian)
//
// It needs the length, and a stream only knows its length at the end, so the
// caller says `finish` when the last byte has gone in. An empty message is
// `start` followed directly by `finish`.
//
// PREFIX. With `use_prefix` high at `start`, one 512-bit block is compressed
// before the first byte, and the length counter starts at 512 bits. That is
// what HMAC needs -- H((K ^ ipad) || m) -- without a second copy of the core.
// Plain SHA-256 leaves `use_prefix` low.
//
// One byte per clock in; one block costs 66 clocks in the core, during which
// `byte_ready` is low. Nothing here depends on the data values.

`default_nettype none

module hijaiyyah_sha256_stream (
    input  wire         clk,
    input  wire         rst_n,

    input  wire         start,       // begin a new hash (pulse, needs idle)
    input  wire         use_prefix,  // sampled with start
    input  wire [511:0] prefix,      // sampled with start

    input  wire         byte_valid,
    input  wire [7:0]   byte_in,
    output wire         byte_ready,
    input  wire         finish,      // no more bytes (pulse, when byte_ready)

    output wire         idle,
    output reg          done,        // one-clock pulse; digest valid from here
    output wire [255:0] digest
);

    localparam [3:0] S_IDLE   = 4'd0;
    localparam [3:0] S_PREFIX = 4'd1;
    localparam [3:0] S_BYTES  = 4'd2;
    localparam [3:0] S_PAD    = 4'd3;
    localparam [3:0] S_ZERO   = 4'd4;
    localparam [3:0] S_COMP   = 4'd5;
    localparam [3:0] S_CWAIT  = 4'd6;
    localparam [3:0] S_DONE   = 4'd7;

    reg [3:0]   phase;
    reg [3:0]   ret;          // where S_CWAIT returns to
    reg [6:0]   idx;          // next free byte in buf, 0..64
    reg [63:0]  bitlen;
    reg [511:0] buf_q;

    reg         core_init;
    wire        core_next  = (phase == S_COMP);
    wire        core_ready;
    wire [511:0] core_block = buf_q;

    hijaiyyah_sha256_core u_core (
        .clk    (clk),
        .rst_n  (rst_n),
        .init   (core_init),
        .next   (core_next),
        .block  (core_block),
        .ready  (core_ready),
        .digest (digest)
    );

    assign idle       = (phase == S_IDLE);
    assign byte_ready = (phase == S_BYTES) && (idx != 7'd64);

    wire [8:0] bitpos = 9'd504 - {idx[5:0], 3'b000};   // top bit of byte idx

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase      <= S_IDLE;
            ret        <= S_IDLE;
            idx        <= 7'd0;
            bitlen     <= 64'd0;
            buf_q      <= 512'd0;
            core_init  <= 1'b0;
            done       <= 1'b0;
        end else begin
            core_init <= 1'b0;
            done      <= 1'b0;

            case (phase)
                S_IDLE: begin
                    if (start) begin
                        core_init  <= 1'b1;
                        idx        <= 7'd0;
                                    buf_q      <= 512'd0;
                        if (use_prefix) begin
                            buf_q  <= prefix;
                            bitlen <= 64'd512;
                            phase  <= S_PREFIX;
                        end else begin
                            bitlen <= 64'd0;
                            phase  <= S_BYTES;
                        end
                    end
                end

                // core_init lands this clock; compress the prefix next.
                S_PREFIX: begin
                    ret   <= S_BYTES;
                    phase <= S_COMP;
                end

                S_BYTES: begin
                    if (idx == 7'd64) begin
                        ret   <= S_BYTES;
                        phase <= S_COMP;
                    end else if (byte_valid) begin
                        buf_q[bitpos +: 8] <= byte_in;
                        idx    <= idx + 7'd1;
                        bitlen <= bitlen + 64'd8;
                    end else if (finish) begin
                        phase <= S_PAD;
                    end
                end

                S_PAD: begin
                    buf_q[bitpos +: 8] <= 8'h80;
                    idx   <= idx + 7'd1;
                    phase <= S_ZERO;
                end

                S_ZERO: begin
                    if (idx == 7'd64) begin
                        ret   <= S_ZERO;
                        phase <= S_COMP;
                    end else if (idx == 7'd56) begin
                        buf_q[63:0] <= bitlen;
                        ret         <= S_DONE;
                        phase       <= S_COMP;
                    end else begin
                        buf_q[bitpos +: 8] <= 8'h00;
                        idx <= idx + 7'd1;
                    end
                end

                // core_next is high this clock; the core leaves idle next.
                S_COMP: begin
                    phase <= S_CWAIT;
                end

                S_CWAIT: begin
                    if (core_ready) begin
                        idx   <= 7'd0;
                        phase <= ret;
                    end
                end

                S_DONE: begin
                    done  <= 1'b1;
                    phase <= S_IDLE;
                end

                default: phase <= S_IDLE;
            endcase
        end
    end

endmodule

`default_nettype wire
