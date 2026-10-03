// ingress_parse.v -- what the wire says about where a frame came from,
// read by logic before any host software can touch it.
//
// Ethernet II (optionally one 802.1Q tag) -> IPv4 (any IHL) or IPv6 (no
// extension headers) -> TCP/UDP ports. One byte per clock; `last` marks the
// frame's final byte, and `done` pulses one clock later with the verdict:
//   status 0 OK, 1 NOT_IP, 2 TRUNCATED, 3 UNSUPPORTED (IHL<5, IPv6 extension
//   header, or L4 not TCP/UDP). Addresses are what the frame CLAIMS: the
//   observation is exact; the claim may have been spoofed upstream.
`default_nettype none
module ingress_parse (
    input  wire         clk, input wire rst_n,
    input  wire         byte_valid, input wire [7:0] byte_in, input wire last,
    output reg          done,
    output reg  [1:0]   status,
    output reg  [3:0]   ver,
    output reg  [127:0] src_ip,
    output reg  [15:0]  sport, output reg [15:0] dport,
    output reg  [7:0]   proto,
    output reg  [47:0]  src_mac
);
    localparam [1:0] OK = 2'd0, NOT_IP = 2'd1, TRUNC = 2'd2, UNSUP = 2'd3;
    reg [10:0]  n;            // bytes captured in this frame
    reg         fin;          // the last byte has been captured
    reg [15:0]  et;
    reg         vlan;
    reg [5:0]   ihl4;
    reg [7:0]   pr;
    reg [127:0] ip;
    reg [15:0]  sp, dp;
    reg [47:0]  mac;
    wire [10:0] b  = vlan ? 11'd18 : 11'd14;
    wire        v4 = (et == 16'h0800), v6 = (et == 16'h86DD);
    wire [10:0] l  = v4 ? (b + {5'd0, ihl4}) : (b + 11'd40);

    // verdict, computed from the captured registers (same order as packets.parse)
    reg [1:0] st; reg [3:0] vv; reg keep_ip, keep_l4, keep_pr;
    always @* begin
        st = OK; vv = 4'd0; keep_ip = 1'b0; keep_l4 = 1'b0; keep_pr = 1'b0;
        if (n < 11'd14 || (vlan && n < 11'd18))      st = TRUNC;
        else if (!(v4 || v6))                          st = NOT_IP;
        else begin
            vv = v4 ? 4'd4 : 4'd6;
            if (n < b + (v4 ? 11'd20 : 11'd40))        st = TRUNC;
            else if (v4 && ihl4 < 6'd20)               st = UNSUP;
            else begin
                keep_ip = 1'b1; keep_pr = 1'b1;
                if (pr != 8'd6 && pr != 8'd17)         st = UNSUP;
                else if (n < l + 11'd4)                st = TRUNC;
                else begin st = OK; keep_l4 = 1'b1; end
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n <= 0; fin <= 0; et <= 0; vlan <= 0; ihl4 <= 0; pr <= 0; ip <= 0; sp <= 0; dp <= 0; mac <= 0;
            done <= 0; status <= 0; ver <= 0; src_ip <= 0; sport <= 0; dport <= 0; proto <= 0; src_mac <= 0;
        end else begin
            done <= 1'b0;
            if (fin) begin
                done <= 1'b1; status <= st; ver <= vv;
                src_ip <= !keep_ip ? 128'd0 : v4 ? {80'd0, 16'hFFFF, ip[31:0]} : ip;
                proto  <= keep_pr ? pr : 8'd0;
                sport  <= keep_l4 ? sp : 16'd0;
                dport  <= keep_l4 ? dp : 16'd0;
                src_mac <= (n >= 11'd14) ? mac : 48'd0;
                n <= 0; fin <= 0; et <= 0; vlan <= 0; ihl4 <= 0; pr <= 0; ip <= 0; sp <= 0; dp <= 0; mac <= 0;
            end else if (byte_valid) begin
                if (n >= 11'd6 && n <= 11'd11) mac <= {mac[39:0], byte_in};
                if (n == 11'd12 || n == 11'd13) et <= {et[7:0], byte_in};
                if (n == 11'd14 && et == 16'h8100) vlan <= 1'b1;
                if (vlan && (n == 11'd16 || n == 11'd17)) et <= {et[7:0], byte_in};
                if (v4 && n == b)                                  ihl4 <= {byte_in[3:0], 2'b00};
                if (v4 && n == b + 11'd9)                          pr <= byte_in;
                if (v4 && n >= b + 11'd12 && n <= b + 11'd15)      ip <= {ip[119:0], byte_in};
                if (v6 && n == b + 11'd6)                          pr <= byte_in;
                if (v6 && n >= b + 11'd8 && n <= b + 11'd23)       ip <= {ip[119:0], byte_in};
                if ((v4 || v6) && n > b && (n == l || n == l + 11'd1))         sp <= {sp[7:0], byte_in};
                if ((v4 || v6) && n > b && (n == l + 11'd2 || n == l + 11'd3)) dp <= {dp[7:0], byte_in};
                n <= n + 11'd1;
                if (last) fin <= 1'b1;
            end
        end
    end
endmodule
`default_nettype wire
