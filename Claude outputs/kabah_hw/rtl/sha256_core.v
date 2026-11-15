// sha256_core.v — the SHA-256 compression function, one round per clock.
//
// FIPS 180-4, section 6.2. This module is the engine only: it takes one
// 512-bit block and folds it into the 256-bit chaining value. It does not pad
// and it does not know the message length -- that is the caller's job
// (sha256_stream.v), for the same reason hijaiyyah_sponge.v leaves padding out.
//
//     init   load H0..H7 (the FIPS initial hash value) into the chain
//     next   compress `block` into the chain: 64 rounds, 64 clocks + 2
//     digest the chain, valid whenever `ready` is high after a block
//
// The message schedule is a 16-word sliding window, not a 64-word array:
// W[t] depends only on W[t-2], W[t-7], W[t-15], W[t-16], so sixteen registers
// hold everything the next round needs. 512 FF instead of 2048.
//
// Constant time by construction: every block takes exactly the same number of
// clocks whatever its contents. There is no data-dependent branch or table
// address anywhere below -- K is indexed by the round counter, never by data.

`default_nettype none

module sha256_core (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         init,       // chain := H0 (pulse; ignored while busy)
    input  wire         next,       // compress `block` (pulse; needs ready)
    input  wire [511:0] block,      // big-endian: block[511:480] is W[0]
    output wire         ready,      // idle: init/next accepted this clock
    output wire [255:0] digest      // H0 || H1 || ... || H7, big-endian
);

    localparam [1:0] S_IDLE  = 2'd0;
    localparam [1:0] S_ROUND = 2'd1;
    localparam [1:0] S_FOLD  = 2'd2;

    reg [1:0] phase;
    reg [5:0] t;                    // round index 0..63

    reg [31:0] h0, h1, h2, h3, h4, h5, h6, h7;   // chaining value
    reg [31:0] a, b, c, d, e, f, g, h;           // working variables
    reg [511:0] w;                  // W[t] at w[511:480], W[t+15] at w[31:0]

    assign ready  = (phase == S_IDLE);
    assign digest = {h0, h1, h2, h3, h4, h5, h6, h7};

    // ── round constant K[t] ─────────────────────────────────────
    // First 32 bits of the fractional parts of the cube roots of the first
    // 64 primes (FIPS 180-4, 4.2.2). Indexed by the round counter only.
    function [31:0] k_of;
        input [5:0] i;
        case (i)
            6'd0:  k_of = 32'h428a2f98; 6'd1:  k_of = 32'h71374491;
            6'd2:  k_of = 32'hb5c0fbcf; 6'd3:  k_of = 32'he9b5dba5;
            6'd4:  k_of = 32'h3956c25b; 6'd5:  k_of = 32'h59f111f1;
            6'd6:  k_of = 32'h923f82a4; 6'd7:  k_of = 32'hab1c5ed5;
            6'd8:  k_of = 32'hd807aa98; 6'd9:  k_of = 32'h12835b01;
            6'd10: k_of = 32'h243185be; 6'd11: k_of = 32'h550c7dc3;
            6'd12: k_of = 32'h72be5d74; 6'd13: k_of = 32'h80deb1fe;
            6'd14: k_of = 32'h9bdc06a7; 6'd15: k_of = 32'hc19bf174;
            6'd16: k_of = 32'he49b69c1; 6'd17: k_of = 32'hefbe4786;
            6'd18: k_of = 32'h0fc19dc6; 6'd19: k_of = 32'h240ca1cc;
            6'd20: k_of = 32'h2de92c6f; 6'd21: k_of = 32'h4a7484aa;
            6'd22: k_of = 32'h5cb0a9dc; 6'd23: k_of = 32'h76f988da;
            6'd24: k_of = 32'h983e5152; 6'd25: k_of = 32'ha831c66d;
            6'd26: k_of = 32'hb00327c8; 6'd27: k_of = 32'hbf597fc7;
            6'd28: k_of = 32'hc6e00bf3; 6'd29: k_of = 32'hd5a79147;
            6'd30: k_of = 32'h06ca6351; 6'd31: k_of = 32'h14292967;
            6'd32: k_of = 32'h27b70a85; 6'd33: k_of = 32'h2e1b2138;
            6'd34: k_of = 32'h4d2c6dfc; 6'd35: k_of = 32'h53380d13;
            6'd36: k_of = 32'h650a7354; 6'd37: k_of = 32'h766a0abb;
            6'd38: k_of = 32'h81c2c92e; 6'd39: k_of = 32'h92722c85;
            6'd40: k_of = 32'ha2bfe8a1; 6'd41: k_of = 32'ha81a664b;
            6'd42: k_of = 32'hc24b8b70; 6'd43: k_of = 32'hc76c51a3;
            6'd44: k_of = 32'hd192e819; 6'd45: k_of = 32'hd6990624;
            6'd46: k_of = 32'hf40e3585; 6'd47: k_of = 32'h106aa070;
            6'd48: k_of = 32'h19a4c116; 6'd49: k_of = 32'h1e376c08;
            6'd50: k_of = 32'h2748774c; 6'd51: k_of = 32'h34b0bcb5;
            6'd52: k_of = 32'h391c0cb3; 6'd53: k_of = 32'h4ed8aa4a;
            6'd54: k_of = 32'h5b9cca4f; 6'd55: k_of = 32'h682e6ff3;
            6'd56: k_of = 32'h748f82ee; 6'd57: k_of = 32'h78a5636f;
            6'd58: k_of = 32'h84c87814; 6'd59: k_of = 32'h8cc70208;
            6'd60: k_of = 32'h90befffa; 6'd61: k_of = 32'ha4506ceb;
            6'd62: k_of = 32'hbef9a3f7; default: k_of = 32'hc67178f2;
        endcase
    endfunction

    function [31:0] rotr;
        input [31:0] x;
        input [4:0]  n;
        rotr = (x >> n) | (x << (6'd32 - n));
    endfunction

    // ── one round, combinational ────────────────────────────────
    wire [31:0] w0   = w[511:480];                        // W[t]
    wire [31:0] big_s1 = rotr(e, 5'd6) ^ rotr(e, 5'd11) ^ rotr(e, 5'd25);
    wire [31:0] ch     = (e & f) ^ (~e & g);
    wire [31:0] t1     = h + big_s1 + ch + k_of(t) + w0;
    wire [31:0] big_s0 = rotr(a, 5'd2) ^ rotr(a, 5'd13) ^ rotr(a, 5'd22);
    wire [31:0] maj    = (a & b) ^ (a & c) ^ (b & c);
    wire [31:0] t2     = big_s0 + maj;

    // ── schedule: W[t+16] from the window ───────────────────────
    wire [31:0] w1   = w[479:448];                        // W[t+1]
    wire [31:0] w9   = w[223:192];                        // W[t+9]
    wire [31:0] w14  = w[63:32];                          // W[t+14]
    wire [31:0] sm0  = rotr(w1, 5'd7)   ^ rotr(w1, 5'd18)  ^ (w1 >> 3);
    wire [31:0] sm1  = rotr(w14, 5'd17) ^ rotr(w14, 5'd19) ^ (w14 >> 10);
    wire [31:0] w16  = sm1 + w9 + sm0 + w0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase <= S_IDLE;
            t     <= 6'd0;
            {h0, h1, h2, h3, h4, h5, h6, h7} <= 256'd0;
            {a, b, c, d, e, f, g, h}         <= 256'd0;
            w     <= 512'd0;
        end else begin
            case (phase)
                S_IDLE: begin
                    if (init) begin
                        h0 <= 32'h6a09e667; h1 <= 32'hbb67ae85;
                        h2 <= 32'h3c6ef372; h3 <= 32'ha54ff53a;
                        h4 <= 32'h510e527f; h5 <= 32'h9b05688c;
                        h6 <= 32'h1f83d9ab; h7 <= 32'h5be0cd19;
                    end else if (next) begin
                        {a, b, c, d, e, f, g, h} <= {h0, h1, h2, h3, h4, h5, h6, h7};
                        w     <= block;
                        t     <= 6'd0;
                        phase <= S_ROUND;
                    end
                end

                S_ROUND: begin
                    h <= g;
                    g <= f;
                    f <= e;
                    e <= d + t1;
                    d <= c;
                    c <= b;
                    b <= a;
                    a <= t1 + t2;
                    w <= {w[479:0], w16};
                    t <= t + 6'd1;
                    if (t == 6'd63)
                        phase <= S_FOLD;
                end

                S_FOLD: begin
                    h0 <= h0 + a; h1 <= h1 + b; h2 <= h2 + c; h3 <= h3 + d;
                    h4 <= h4 + e; h5 <= h5 + f; h6 <= h6 + g; h7 <= h7 + h;
                    phase <= S_IDLE;
                end

                default: phase <= S_IDLE;
            endcase
        end
    end

endmodule

`default_nettype wire
