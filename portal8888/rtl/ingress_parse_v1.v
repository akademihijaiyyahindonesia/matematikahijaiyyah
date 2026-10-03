// v1 PHY parser: last is finalized in the same cycle, allowing continuous frames.
`default_nettype none
module ingress_parse_v1 (
    input wire clk, input wire rst_n,
    input wire byte_valid, input wire [7:0] byte_in, input wire last,
    output reg done, output reg [1:0] status, output reg [3:0] ver,
    output reg [127:0] src_ip, output reg [15:0] sport, output reg [15:0] dport,
    output reg [7:0] proto, output reg [47:0] src_mac
);
    localparam [1:0] OK=0, NOT_IP=1, TRUNC=2, UNSUP=3;
    reg [13:0] n;
    reg [15:0] et;
    reg vlan;
    reg [5:0] ihl4;
    reg [7:0] pr;
    reg [127:0] ip;
    reg [15:0] sp, dp;
    reg [47:0] mac;
    reg [13:0] n_after, base, l4_start;
    reg [15:0] et_after;
    reg vlan_after;
    reg [5:0] ihl_after;
    reg [7:0] pr_after;
    reg [127:0] ip_after;
    reg [15:0] sp_after, dp_after;
    reg [47:0] mac_after;
    reg [1:0] st_after;
    reg [3:0] ver_after;
    reg keep_ip, keep_l4, keep_pr, v4, v6;
    always @* begin
        n_after=n+14'd1; et_after=et; vlan_after=vlan; ihl_after=ihl4; pr_after=pr;
        ip_after=ip; sp_after=sp; dp_after=dp; mac_after=mac;
        if(n>=14'd6 && n<=14'd11) mac_after={mac[39:0],byte_in};
        if(n==14'd12 || n==14'd13) et_after={et_after[7:0],byte_in};
        if(n==14'd13 && {et[7:0],byte_in}==16'h8100) vlan_after=1'b1;
        if(vlan && (n==14'd16 || n==14'd17)) et_after={et_after[7:0],byte_in};
        v4=(et_after==16'h0800); v6=(et_after==16'h86dd);
        base=vlan_after ? 14'd18 : 14'd14;
        if(v4 && n==base) ihl_after={byte_in[3:0],2'b00};
        if(v4 && n==base+14'd9) pr_after=byte_in;
        if(v4 && n>=base+14'd12 && n<=base+14'd15) ip_after={ip_after[119:0],byte_in};
        if(v6 && n==base+14'd6) pr_after=byte_in;
        if(v6 && n>=base+14'd8 && n<=base+14'd23) ip_after={ip_after[119:0],byte_in};
        l4_start=v4 ? base+ihl_after : base+14'd40;
        if((v4||v6) && (n==l4_start || n==l4_start+14'd1)) sp_after={sp_after[7:0],byte_in};
        if((v4||v6) && (n==l4_start+14'd2 || n==l4_start+14'd3)) dp_after={dp_after[7:0],byte_in};
        st_after=OK; ver_after=0; keep_ip=0; keep_l4=0; keep_pr=0;
        if(n_after<14'd14 || (vlan_after && n_after<14'd18)) st_after=TRUNC;
        else if(!(v4||v6)) st_after=NOT_IP;
        else begin
            ver_after=v4 ? 4'd4 : 4'd6;
            if(n_after<base+(v4 ? 14'd20 : 14'd40)) st_after=TRUNC;
            else if(v4 && ihl_after<14'd20) st_after=UNSUP;
            else begin
                keep_ip=1; keep_pr=1;
                if(pr_after!=8'd6 && pr_after!=8'd17) st_after=UNSUP;
                else if(n_after<l4_start+14'd4) st_after=TRUNC;
                else begin st_after=OK; keep_l4=1; end
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            n<=0; et<=0; vlan<=0; ihl4<=0; pr<=0; ip<=0; sp<=0; dp<=0; mac<=0;
            done<=0; status<=0; ver<=0; src_ip<=0; sport<=0; dport<=0; proto<=0; src_mac<=0;
        end else begin
            done<=0;
            if(byte_valid) begin
                if(last) begin
                    done<=1; status<=st_after; ver<=ver_after;
                    src_ip<=!keep_ip ? 128'd0 : v4 ? {80'd0,16'hffff,ip_after[31:0]} : ip_after;
                    proto<=keep_pr ? pr_after : 0; sport<=keep_l4 ? sp_after : 0; dport<=keep_l4 ? dp_after : 0;
                    src_mac<=(n_after>=14'd14) ? mac_after : 0;
                    n<=0; et<=0; vlan<=0; ihl4<=0; pr<=0; ip<=0; sp<=0; dp<=0; mac<=0;
                end else begin
                    n<=n_after; et<=et_after; vlan<=vlan_after; ihl4<=ihl_after; pr<=pr_after;
                    ip<=ip_after; sp<=sp_after; dp<=dp_after; mac<=mac_after;
                end
            end
        end
    end
endmodule
`default_nettype wire
