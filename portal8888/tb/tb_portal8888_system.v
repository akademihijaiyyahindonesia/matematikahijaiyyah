`timescale 1ns/1ps
// SYSTEM test: GPS-PPS -> hijaiyyah_timestamp -> hijaiyyah_portal8888.
// Seals one round whose timestamps come LIVE from the GPS-disciplined clock --
// read by this bench at the cycle the FSM accepts each record, not latched at a
// frame's first byte -- writes build/portal_sys_result.txt (the exact fields +
// tags sealed), reports per-corner clock counts and GPS state, and, with +vcd,
// dumps every signal to build/portal8888_system.vcd.
// ref/portal_sys_check.py then verifies every byte against hashlib/hmac.
module tb_portal8888_system;
  localparam integer TPS = 200000, PPM = 50, TPS_REAL = TPS + (TPS*PPM)/1000000;
  reg clk=0, rst_n=0; always #5 clk=~clk;
  reg pps=0;
  wire [31:0] ts_sec, ts_tick; wire ts_locked, ts_holdover; wire signed [31:0] ts_ppm; wire ts_warn;
  hijaiyyah_timestamp #(.TPS(TPS)) u_ts(.clk(clk),.rst_n(rst_n),.pps(pps),
    .sec(ts_sec),.tick(ts_tick),.locked(ts_locked),.holdover(ts_holdover),.ppm_est(ts_ppm),.ppm_warn(ts_warn));
  reg rec_valid=0; reg [1:0] rec_port=0;
  reg [31:0] rec_tsec=0, rec_ttick=0; reg [127:0] rec_ip=0;
  reg [15:0] rec_sport=0, rec_dport=0; reg [7:0] rec_proto=0; reg [15:0] rec_idx=0, rec_pidx=0;
  wire busy, ready, round_done;
  reg [511:0] kA,kB,kC,kD,kP;
  wire [31:0] anc_round; wire [255:0] anc_root, tagA,tagB,tagC,tagD;
  hijaiyyah_portal8888_legacy_unwired dut(.clk(clk),.rst_n(rst_n),.rec_valid(rec_valid),.rec_port(rec_port),
    .rec_tsec(rec_tsec),.rec_ttick(rec_ttick),.rec_ip(rec_ip),.rec_sport(rec_sport),
    .rec_dport(rec_dport),.rec_proto(rec_proto),.rec_idx(rec_idx),.rec_pidx(rec_pidx),
    .busy(busy),.ready(ready),.kA(kA),.kB(kB),.kC(kC),.kD(kD),.kP(kP),
    .anc_round(anc_round),.anc_root(anc_root),.tagA(tagA),.tagB(tagB),.tagC(tagC),.tagD(tagD),
    .round_done(round_done));

  integer fd,fo,r,i,pp,c0,c_round; reg [16*8:1] lbl; reg [511:0] kv;
  reg [127:0] v_ip[0:3]; reg [15:0] v_sport[0:3],v_dport[0:3],v_idx[0:3]; reg [7:0] v_proto[0:3];
  integer cyc=0; always @(posedge clk) cyc=cyc+1;
  reg [31:0] cs, ct; reg [255:0] tg;

  task gps_second; begin
    for (i=0;i<TPS_REAL-1;i=i+1) @(negedge clk);
    @(negedge clk); pps=1; @(negedge clk); pps=0;
  end endtask
  task seal(input [1:0] p); begin
    @(negedge clk); while(!ready) @(negedge clk);
    cs=ts_sec; ct=ts_tick;
    rec_port<=p; rec_tsec<=cs; rec_ttick<=ct; rec_ip<=v_ip[p];
    rec_sport<=v_sport[p]; rec_dport<=v_dport[p]; rec_proto<=v_proto[p]; rec_idx<=v_idx[p];
    rec_valid<=1; c0=cyc; @(negedge clk); rec_valid<=0;
    @(negedge clk); while(busy) @(negedge clk);
    tg = (p==0)?tagA:(p==1)?tagB:(p==2)?tagC:tagD;
    $fwrite(fo,"COR %0d %0d %0d %h\n", p, cs, ct, tg);
    $display("  corner %0d: T=%0d.%09ds (tick=%0d) sealed in %0d clocks  tag=%h..",
             p, cs, ct*(1000000000/TPS), ct, cyc-c0, tg[255:224]);
  end endtask

  initial begin
    if ($test$plusargs("vcd")) begin $dumpfile("build/portal8888_system.vcd"); $dumpvars(0, tb_portal8888_system); end
    fd=$fopen("build/portal_sys_keys.txt","r"); if (fd==0) $fatal(1,"need: python3 ref/portal_sys_keys.py > build/portal_sys_keys.txt");
    fo=$fopen("build/portal_sys_result.txt","w");
    for (i=0;i<5;i=i+1) begin r=$fscanf(fd,"%s %h\n",lbl,kv);
      case(i) 0:kA=kv;1:kB=kv;2:kC=kv;3:kD=kv;4:kP=kv; endcase end
    for (i=0;i<4;i=i+1) r=$fscanf(fd,"%s %d %h %h %h %h %h\n",lbl,pp,v_ip[i],v_sport[i],v_dport[i],v_proto[i],v_idx[i]);
    r=$fscanf(fd,"%s %h\n",lbl,rec_pidx);

    #22 rst_n=1;
    $display("== GPS-PPS discipline (crystal %0d ppm fast) ==", PPM);
    gps_second; $display("  PPS 1: sec=%0d tick=%0d locked=%0d ppm_est=%0d holdover=%0d", ts_sec,ts_tick,ts_locked,ts_ppm,ts_holdover);
    gps_second; $display("  PPS 2: sec=%0d tick=%0d locked=%0d ppm_est=%0d holdover=%0d", ts_sec,ts_tick,ts_locked,ts_ppm,ts_holdover);
    for (i=0;i<TPS/4;i=i+1) @(negedge clk);           // move into sub-second

    $display("== seal one round, timestamps live from GPS ==");
    c_round=cyc; seal(0); seal(1); seal(2); seal(3);
    @(negedge clk); while(anc_round==0) @(negedge clk);
    $fwrite(fo,"ROOT %h\n", anc_root);
    $display("  portal: round=%0d  total round=%0d clocks  root=%h..", anc_round, cyc-c_round, anc_root[255:224]);
    $display("== GPS still locked: ppm_est=%0d holdover=%0d ==", ts_ppm, ts_holdover);
    $fclose(fo);
    $display("wrote build/portal_sys_result.txt -- verify with ref/portal_sys_check.py");
    $finish;
  end
endmodule
