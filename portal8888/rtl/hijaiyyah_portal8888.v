// Portal 8888 v1 operational top: PHY capture, replayed SHA-256, and HMAC seal.
// L1 seals exactly 125 MSB-first bytes. L1 v1 deliberately excludes LOC.
`default_nettype none
module hijaiyyah_portal8888 (
    input wire clk, input wire rst_n, input wire pps,
    input wire provision_time, input wire [31:0] provision_utc_sec,
    input wire [31:0] provision_uncert_ns,
    input wire [1:0] phy_port, input wire phy_byte_valid,
    input wire [7:0] phy_byte, input wire phy_last,
    input wire prov_valid, input wire [2:0] prov_slot,
    input wire [7:0] prov_byte, input wire prov_lock,
    output wire provisioned, output reg provision_locked,
    output reg [4:0] provision_written, output wire busy, output wire ready,
    output reg record_done, output reg record_dropped, output reg overflow_drop,
    output wire [999:0] sealed_body, output reg [255:0] sealed_tag,
    output reg [31:0] anc_round, output reg [255:0] anc_root,
    output reg [255:0] tagA, output reg [255:0] tagB,
    output reg [255:0] tagC, output reg [255:0] tagD
);
    localparam integer MAX_FRAME_BYTES = 9216;
    localparam [63:0] DEV = "PORT8888";
    localparam [3:0] S_IDLE=0, S_CAPTURE=1, S_OVERFLOW=2, S_PARSE=3,
                     S_HASH=4, S_HASH_WAIT=5, S_HSTREAM=6, S_HWAIT=7,
                     S_PSTREAM=8, S_PWAIT=9, S_UNPROVISIONED=10, S_KLOAD=11;

    reg [7:0] key_mem [0:511];          // {slot, byte}: five 64-byte key blocks
    reg [7:0] key_rd;
    reg [5:0] kcnt;
    reg [2:0] kslot, ksel;
    reg [6:0] kpos;
    reg kportal;
    reg [3:0] state;
    reg [7:0] frame_mem [0:MAX_FRAME_BYTES-1];
    reg [7:0] frame_rd;
    reg [13:0] frame_len, replay_pos;
    reg drop_active;

    wire [31:0] ts_sec, ts_tick, ts_uncert;
    wire [1:0] ts_source;
    hijaiyyah_timestamp u_timestamp (
        .clk(clk), .rst_n(rst_n), .pps(pps), .provision_time(provision_time),
        .provision_utc_sec(provision_utc_sec), .provision_uncert_ns(provision_uncert_ns),
        .sec(ts_sec), .tick(ts_tick), .locked(), .holdover(), .ppm_est(), .ppm_warn(),
        .time_source(ts_source), .uncert_ns(ts_uncert)
    );

    wire parse_done;
    wire [1:0] parse_status;
    wire [3:0] parse_ver;
    wire [127:0] parse_ip;
    wire [15:0] parse_sport, parse_dport;
    wire [7:0] parse_proto;
    wire [47:0] parse_mac;
    ingress_parse_v1 u_ingress (
        .clk(clk), .rst_n(rst_n), .byte_valid(phy_byte_valid), .byte_in(phy_byte), .last(phy_last),
        .done(parse_done), .status(parse_status), .ver(parse_ver), .src_ip(parse_ip),
        .sport(parse_sport), .dport(parse_dport), .proto(parse_proto), .src_mac(parse_mac)
    );

    reg sha_start, sha_finish;
    wire sha_ready, sha_done;
    wire [255:0] sha_digest;
    wire sha_take = state == S_HASH && sha_ready && replay_pos < frame_len;
    hijaiyyah_sha256_stream u_frame_sha256 (
        .clk(clk), .rst_n(rst_n), .start(sha_start), .use_prefix(1'b0), .prefix(512'd0),
        .byte_valid(sha_take), .byte_in(frame_rd), .byte_ready(sha_ready),
        .finish(sha_finish && sha_ready), .idle(), .done(sha_done), .digest(sha_digest)
    );

    reg h_start, h_finish;
    reg [511:0] h_key;
    wire h_ready, h_done;
    wire [255:0] h_mac;
    reg [7:0] h_pos;
    reg [1:0] cur_port;
    reg [31:0] cur_tsec, cur_ttick, cur_uncert;
    reg [1:0] cur_source;
    reg [63:0] cur_ctr;
    reg [1:0] cur_status;
    reg [3:0] cur_ver;
    reg [127:0] cur_ip;
    reg [15:0] cur_sport, cur_dport;
    reg [7:0] cur_proto;
    reg [47:0] cur_mac;
    reg [255:0] cur_prev;
    reg [15:0] cur_idx;
    reg [63:0] ctr;
    reg [15:0] idxA, idxB, idxC, idxD;
    reg [255:0] prevA, prevB, prevC, prevD, root;
    reg [3:0] got;

    wire [999:0] body_wire = {
        DEV, {6'd0,cur_port}, cur_tsec, cur_ttick, {6'd0,cur_source}, cur_uncert, cur_ctr,
        {6'd0,cur_status}, {4'd0,cur_ver}, cur_ip, cur_sport, cur_dport, cur_proto, cur_mac,
        sha_digest, cur_idx, cur_prev
    };
    // The sealed body is not copied into a register of its own: it is the
    // fields themselves, which hold from record_done until the next frame's
    // first byte. FRAME_HASH is the frame SHA-256 engine's digest, which holds
    // until that engine is started for the next frame.
    assign sealed_body = body_wire;
    wire [1295:0] portal_body = {anc_round[15:0], root, tagA, tagB, tagC, tagD};
    function [7:0] record_byte;
        input [7:0] pos;
        begin record_byte = body_wire[999 - pos * 8 -: 8]; end
    endfunction
    function [7:0] portal_byte;
        input [7:0] pos;
        begin portal_byte = portal_body[1295 - pos * 8 -: 8]; end
    endfunction
    wire record_stream = state == S_HSTREAM;
    wire h_take = (record_stream && h_ready && h_pos < 8'd125) ||
                  (state == S_PSTREAM && h_ready && h_pos < 8'd162);
    wire [7:0] h_byte = record_stream ? record_byte(h_pos) : portal_byte(h_pos);
    hijaiyyah_hmac u_hmac (
        .clk(clk), .rst_n(rst_n), .start(h_start), .key(h_key),
        .byte_valid(h_take), .byte_in(h_byte), .byte_ready(h_ready),
        .finish(h_finish && h_ready), .idle(), .done(h_done), .mac(h_mac)
    );

    function [255:0] prev_for;
        input [1:0] port;
        begin case (port)
            0: prev_for=prevA; 1: prev_for=prevB; 2: prev_for=prevC; default: prev_for=prevD;
        endcase end
    endfunction
    function [15:0] idx_for;
        input [1:0] port;
        begin case (port)
            0: idx_for=idxA; 1: idx_for=idxB; 2: idx_for=idxC; default: idx_for=idxD;
        endcase end
    endfunction

    assign provisioned = provision_locked && &provision_written;
    assign busy = state != S_IDLE;
    assign ready = provisioned && state == S_IDLE && !drop_active;

    // The frame buffer is a synchronous RAM with no reset (owner, 3 October 2026):
    // written in a block with an asynchronous reset it became 73,728 registers.
    // The read address runs one clock ahead, so frame_rd is frame_mem[replay_pos]
    // on every clock of S_HASH, as the combinational read was.
    wire frame_cap0 = state==S_IDLE && !drop_active && phy_byte_valid && provisioned;
    wire frame_capn = state==S_CAPTURE && phy_byte_valid && frame_len < MAX_FRAME_BYTES;
    wire [13:0] frame_wa = frame_cap0 ? 14'd0 : frame_len;
    wire [13:0] frame_ra = (state==S_PARSE && parse_done) ? 14'd0 :
                           (sha_take ? replay_pos+14'd1 : replay_pos);
    always @(posedge clk) begin
        if (frame_cap0 || frame_capn) frame_mem[frame_wa] <= phy_byte;
        frame_rd <= frame_mem[frame_ra];
    end

    // The five keys are a synchronous RAM too (owner, 3 October 2026), written a
    // byte at a time, most significant byte first. A slot takes exactly 64 bytes,
    // once: it is written only while unlocked and not yet complete, and a slot
    // begun must be finished before another is accepted. Sealing loads the
    // 64-byte block into h_key in S_KLOAD before the HMAC starts.
    wire key_we = prov_valid && !provision_locked && !prov_lock && prov_slot<3'd5 &&
                  !provision_written[prov_slot] && (kcnt==6'd0 || prov_slot==kslot);
    always @(posedge clk) begin
        if (key_we) key_mem[{prov_slot, kcnt}] <= prov_byte;
        key_rd <= key_mem[{ksel, kpos[5:0]}];
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state<=S_IDLE; provision_locked<=0; provision_written<=0; frame_len<=0; replay_pos<=0; drop_active<=0;
            sha_start<=0; sha_finish<=0; h_start<=0; h_finish<=0; h_key<=0; h_pos<=0;
            kcnt<=0; kslot<=0; ksel<=0; kpos<=0; kportal<=0;
            cur_port<=0; cur_tsec<=0; cur_ttick<=0; cur_source<=0; cur_uncert<=0; cur_ctr<=0;
            cur_status<=0; cur_ver<=0; cur_ip<=0; cur_sport<=0; cur_dport<=0; cur_proto<=0; cur_mac<=0;
            cur_prev<=0; cur_idx<=0; ctr<=0; idxA<=0; idxB<=0; idxC<=0; idxD<=0;
            prevA<=0; prevB<=0; prevC<=0; prevD<=0; root<=0; got<=0;
            sealed_tag<=0; record_done<=0; record_dropped<=0; overflow_drop<=0;
            anc_round<=0; anc_root<=0; tagA<=0; tagB<=0; tagC<=0; tagD<=0;
        end else begin
            sha_start<=0; sha_finish<=0; h_start<=0; h_finish<=0;
            record_done<=0; record_dropped<=0; overflow_drop<=0;
            if (prov_lock) provision_locked<=1'b1;
            if (key_we) begin
                kslot<=prov_slot; kcnt<=kcnt+6'd1;
                if (kcnt==6'd63) provision_written[prov_slot]<=1'b1;
            end
            if (state!=S_IDLE && state!=S_CAPTURE && state!=S_OVERFLOW && state!=S_UNPROVISIONED && phy_byte_valid) begin
                if (phy_last) begin record_dropped<=1'b1; drop_active<=0; end else drop_active<=1'b1;
            end
            case (state)
                S_IDLE: if (drop_active) begin
                    if (phy_byte_valid && phy_last) begin record_dropped<=1'b1; drop_active<=0; end
                end else if (phy_byte_valid) begin
                    if (!provisioned) begin
                        if (phy_last) record_dropped<=1'b1; else state<=S_UNPROVISIONED;
                    end else begin
                        frame_len<=14'd1; cur_port<=phy_port;
                        cur_tsec<=ts_sec; cur_ttick<=ts_tick; cur_source<=ts_source; cur_uncert<=ts_uncert;
                        cur_ctr<=ctr+64'd1; ctr<=ctr+64'd1; cur_prev<=prev_for(phy_port); cur_idx<=idx_for(phy_port);
                        if (phy_last) state<=S_PARSE; else state<=S_CAPTURE;
                    end
                end
                S_UNPROVISIONED: if (phy_byte_valid && phy_last) begin record_dropped<=1'b1; state<=S_IDLE; end
                S_CAPTURE: if (phy_byte_valid) begin
                    if (frame_len < MAX_FRAME_BYTES) begin
                        frame_len<=frame_len+14'd1;
                        if (phy_last) state<=S_PARSE;
                    end else begin
                        overflow_drop<=1'b1;
                        if (phy_last) begin record_dropped<=1'b1; state<=S_IDLE; end else state<=S_OVERFLOW;
                    end
                end
                S_OVERFLOW: if (phy_byte_valid && phy_last) begin record_dropped<=1'b1; overflow_drop<=1'b1; state<=S_IDLE; end
                S_PARSE: if (parse_done) begin
                    cur_status<=parse_status; cur_ver<=parse_ver; cur_ip<=parse_ip; cur_sport<=parse_sport;
                    cur_dport<=parse_dport; cur_proto<=parse_proto; cur_mac<=parse_mac;
                    replay_pos<=0; sha_start<=1'b1; state<=S_HASH;
                end
                S_HASH: begin
                    if (sha_take) replay_pos<=replay_pos+14'd1;
                    if (replay_pos==frame_len && sha_ready) begin sha_finish<=1'b1; state<=S_HASH_WAIT; end
                end
                S_HASH_WAIT: if (sha_done) begin ksel<={1'b0,cur_port}; kpos<=0; kportal<=1'b0; h_pos<=0; state<=S_KLOAD; end
                S_KLOAD: begin
                    kpos<=kpos+7'd1;
                    if (kpos!=7'd0) h_key<={h_key[503:0], key_rd};
                    if (kpos==7'd64) begin h_start<=1'b1; state<=kportal ? S_PSTREAM : S_HSTREAM; end
                end
                S_HSTREAM: begin
                    if (h_take) h_pos<=h_pos+8'd1;
                    if (h_pos==8'd125 && h_ready) begin h_finish<=1'b1; state<=S_HWAIT; end
                end
                S_HWAIT: if (h_done) begin
                    sealed_tag<=h_mac; record_done<=1'b1;
                    case (cur_port)
                        0: begin prevA<=h_mac; tagA<=h_mac; idxA<=idxA+16'd1; end
                        1: begin prevB<=h_mac; tagB<=h_mac; idxB<=idxB+16'd1; end
                        2: begin prevC<=h_mac; tagC<=h_mac; idxC<=idxC+16'd1; end
                        default: begin prevD<=h_mac; tagD<=h_mac; idxD<=idxD+16'd1; end
                    endcase
                    if ((got | (4'b0001<<cur_port))==4'b1111) begin got<=0; ksel<=3'd4; kpos<=0; kportal<=1'b1; h_pos<=0; state<=S_KLOAD; end
                    else begin got<=got|(4'b0001<<cur_port); state<=S_IDLE; end
                end
                S_PSTREAM: begin
                    if (h_take) h_pos<=h_pos+8'd1;
                    if (h_pos==8'd162 && h_ready) begin h_finish<=1'b1; state<=S_PWAIT; end
                end
                S_PWAIT: if (h_done) begin root<=h_mac; anc_root<=h_mac; anc_round<=anc_round+32'd1; state<=S_IDLE; end
                default: state<=S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire// hijaiyyah_portal8888.v -- the sealing FSM: four corners + portal, one HMAC
// engine time-shared, per-corner PREV chain, and a head anchor register.
//
// Sealed CORNER body (64 bytes, MSB-first) -- the exact layout Python matches:
//   [0] PORT | [1..4] T_sec(BE) | [5..8] T_tick(BE) | [9..24] SRC_IP(16)
//   [25..26] SPORT(BE) | [27..28] DPORT(BE) | [29] PROTO | [30..31] IDX(BE)
//   [32..63] PREV(32)
// Sealed PORTAL body (162 bytes):
//   [0..1] IDX_portal(BE) | [2..33] ROOT_prev(32) | [34..161] TAG_A..D (32 each)
//   TAG = HMAC(K_corner, corner body);  ROOT = HMAC(K_portal, portal body)
//   head anchor = {round, ROOT, TAG_A..D} -- a register, not host-writable.
`default_nettype none
module hijaiyyah_portal8888_legacy_unwired (
    input  wire         clk, input wire rst_n,
    input  wire         rec_valid,
    input  wire [1:0]   rec_port,
    input  wire [31:0]  rec_tsec, input wire [31:0] rec_ttick,
    input  wire [127:0] rec_ip,
    input  wire [15:0]  rec_sport, input wire [15:0] rec_dport,
    input  wire [7:0]   rec_proto,
    input  wire [15:0]  rec_idx, input wire [15:0] rec_pidx,
    output wire         busy, output wire ready,
    input  wire [511:0] kA, input wire [511:0] kB,
    input  wire [511:0] kC, input wire [511:0] kD, input wire [511:0] kP,
    output reg  [31:0]  anc_round,
    output reg  [255:0] anc_root,
    output reg  [255:0] tagA, output reg [255:0] tagB,
    output reg  [255:0] tagC, output reg [255:0] tagD,
    output reg          round_done
);
    reg          h_start, h_finish, feed;
    reg  [511:0] h_key;
    wire         h_ready, h_idle, h_done;
    wire [255:0] h_mac;
    reg  [1295:0] sr;
    reg  [10:0]   nleft;
    wire [7:0]    byte_in  = sr[1295:1288];
    wire          take     = feed && h_ready && (nleft != 0);
    hijaiyyah_hmac u_hmac (.clk(clk), .rst_n(rst_n), .start(h_start), .key(h_key),
        .byte_valid(take), .byte_in(byte_in), .byte_ready(h_ready),
        .finish(h_finish && h_ready), .idle(h_idle), .done(h_done), .mac(h_mac));
    
    reg  [255:0]  prevA, prevB, prevC, prevD, root;
    reg  [3:0]    got;
    reg  [1:0]    cur;
    localparam [3:0] S_IDLE=0,S_CSTART=1,S_CSTREAM=2,S_CFIN=3,S_CWAIT=4,
                     S_PSTART=5,S_PSTREAM=6,S_PFIN=7,S_PWAIT=8;
    reg [3:0] st;
    assign busy  = (st != S_IDLE);
    assign ready = (st == S_IDLE);
    function [255:0] prev_of; input [1:0] p;
        prev_of = (p==0)?prevA:(p==1)?prevB:(p==2)?prevC:prevD; endfunction
    function [511:0] key_of; input [1:0] p;
        key_of = (p==0)?kA:(p==1)?kB:(p==2)?kC:kD; endfunction
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st<=S_IDLE; h_start<=0; h_finish<=0; feed<=0; sr<=0; nleft<=0;
            prevA<=0; prevB<=0; prevC<=0; prevD<=0; root<=0; got<=0; cur<=0;
            anc_round<=0; anc_root<=0; round_done<=0; tagA<=0; tagB<=0; tagC<=0; tagD<=0;
        end else begin
            h_start<=0; h_finish<=0; round_done<=0;
            case (st)
                S_IDLE: if (rec_valid) begin
                    cur <= rec_port;
                    sr  <= { {6'd0,rec_port}, rec_tsec, rec_ttick, rec_ip,
                             rec_sport, rec_dport, rec_proto, rec_idx,
                             prev_of(rec_port), {(1296-512){1'b0}} };
                    nleft <= 11'd64; h_key <= key_of(rec_port);
                    h_start <= 1'b1; st <= S_CSTART;
                end
                S_CSTART: begin feed<=1'b1; st<=S_CSTREAM; end     // engine leaves idle
                S_CSTREAM: begin
                    if (take) begin sr<={sr[1287:0],8'd0}; nleft<=nleft-11'd1; end
                    if (nleft==0) begin feed<=1'b0; st<=S_CFIN; end
                end
                S_CFIN: if (h_ready) begin h_finish<=1'b1; st<=S_CWAIT; end
                S_CWAIT: if (h_done) begin
                    case (cur)
                      0: begin prevA<=h_mac; tagA<=h_mac; end
                      1: begin prevB<=h_mac; tagB<=h_mac; end
                      2: begin prevC<=h_mac; tagC<=h_mac; end
                      default: begin prevD<=h_mac; tagD<=h_mac; end
                    endcase
                    if ((got | (4'b0001<<cur)) == 4'b1111) begin got<=4'b0000; st<=S_PSTART; end
                    else begin got <= got | (4'b0001<<cur); st<=S_IDLE; end
                end
                S_PSTART: begin
                    sr <= { rec_pidx, root, prevA, prevB, prevC, prevD };
                    nleft <= 11'd162; h_key <= kP; h_start<=1'b1; st<=S_PSTREAM; feed<=1'b0;
                end
                S_PSTREAM: begin
                    if (!feed) feed<=1'b1;                        // one-cycle engine warmup
                    else begin
                        if (take) begin sr<={sr[1287:0],8'd0}; nleft<=nleft-11'd1; end
                        if (nleft==0) begin feed<=1'b0; st<=S_PFIN; end
                    end
                end
                S_PFIN: if (h_ready) begin h_finish<=1'b1; st<=S_PWAIT; end
                S_PWAIT: if (h_done) begin
                    root<=h_mac; anc_root<=h_mac; anc_round<=anc_round+32'd1;
                    round_done<=1'b1; st<=S_IDLE;
                end
                default: st<=S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
