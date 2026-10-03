// jim_sync.v -- Jim m-sequence frame marker detector (31-bit correlator).
// Marker = Jim's GF(2) wire sequence, cosmic-codex-jim/WAVE.md:
//   1111101110001010110100001100100   (first bit transmitted first)
// hit pulses on the clock the 31st marker bit arrives, when the Hamming
// distance between the last 31 bits and the marker is <= T.
`default_nettype none
module jim_sync #(parameter integer T = 2) (
    input  wire clk, input wire rst_n,
    input  wire bit_valid, input wire bit_in,
    output reg  hit, output reg [4:0] ham
);
    localparam [30:0] MARK = 31'b1111101110001010110100001100100;
    reg  [30:0] sh;                         // sh[30] = oldest bit
    wire [30:0] nxt = {sh[29:0], bit_in};
    wire [30:0] x   = nxt ^ MARK;
    integer i; reg [4:0] pc;
    always @* begin pc = 5'd0; for (i = 0; i < 31; i = i + 1) pc = pc + x[i]; end
    reg [4:0] seen;                         // bits received, saturating at 31
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin sh <= 31'd0; hit <= 1'b0; ham <= 5'd31; seen <= 5'd0; end
        else begin
            hit <= 1'b0;
            if (bit_valid) begin
                sh <= nxt; ham <= pc;
                if (seen != 5'd31) seen <= seen + 5'd1;
                hit <= (seen >= 5'd30) && (pc <= T);
            end
        end
    end
endmodule
`default_nettype wire
