`timescale 1ns/1ps
// Crystal model: module expects TPS ticks/sec; the REAL crystal runs fast, so one
// real second = TPS_real = TPS*(1+ppm/1e6) ticks, and PPS comes once per real second.
//  (1) disciplined: at each PPS, ppm_est should read the true ppm; sec tracks UTC.
//  (2) holdover: drop PPS for 3 s -> error grows at ppm*t (why T_source+uncertainty
//      must ride in the sealed record).
module tb_timestamp;
  localparam integer TPS = 200000;        // large enough that 50 ppm = 10 ticks
  localparam integer PPM = 50;
  localparam integer TPS_REAL = TPS + (TPS*PPM)/1000000;   // crystal ticks per real second
  reg clk=0, rst_n=0, pps=0, prov=0; reg [31:0] utc=1700000000, uncert=4000; always #5 clk=~clk;
  wire [31:0] sec, tick, uncert_out; wire [1:0] source; wire locked, holdover; wire signed [31:0] ppm_est; wire ppm_warn;
  hijaiyyah_timestamp #(.TPS(TPS),.PPM_WARN(100)) dut(.clk(clk),.rst_n(rst_n),.pps(pps),
    .provision_time(prov),.provision_utc_sec(utc),.provision_uncert_ns(uncert),
    .sec(sec),.tick(tick),.locked(locked),.holdover(holdover),.ppm_est(ppm_est),.ppm_warn(ppm_warn),
    .time_source(source),.uncert_ns(uncert_out));
  integer s, i, holdover_ns, bad=0; real t_dut; reg [31:0] before_return;
  task one_real_second; begin
    for (i=0;i<TPS_REAL-1;i=i+1) @(negedge clk);   // crystal ticks for one real second
    @(negedge clk); pps=1; @(negedge clk); pps=0;  // PPS at the boundary
  end endtask
  initial begin
    #22 rst_n=1;
    @(negedge clk); prov=1; @(negedge clk); prov=0;
    if (sec !== utc || source !== 0 || uncert_out !== uncert) bad = bad + 1;
    for (s=0; s<6; s=s+1) begin
      one_real_second;
      $display("disc sec %0d: sec=%0d tick=%0d locked=%0d ppm_est=%0d warn=%0d",
               s, sec, tick, locked, ppm_est, ppm_warn);
      if (sec !== utc+s+1 || tick !== 0 || locked !== 1 || holdover !== 0 || source !== 2 || ppm_est !== PPM || ppm_warn !== 0)
        bad = bad + 1;
    end
    // drop PPS for 3 real seconds
    for (s=0; s<3; s=s+1) for (i=0;i<TPS_REAL;i=i+1) @(negedge clk);
    t_dut = sec + (tick*1.0/TPS);
    holdover_ns = (t_dut - (utc + 9.0))*1e9; if (holdover_ns<0) holdover_ns=-holdover_ns;
    $display("holdover 3s: locked=%0d holdover=%0d drift=%0d ns  (expect ~%0d ns = %0d ppm x 3 s)",
             locked, holdover, holdover_ns, PPM*3*1000, PPM);
    // drift within one tick of ppm x 3 s; the PPS-return path is not exercised here
    if (locked !== 0 || holdover !== 1 || source !== 0 || uncert_out < uncert) bad = bad + 1;
    if (holdover_ns - PPM*3*1000 > 1000000000/TPS || PPM*3*1000 - holdover_ns > 1000000000/TPS) bad = bad + 1;
    before_return = sec;
    one_real_second;
    if (sec < before_return || locked !== 1 || holdover !== 0 || source !== 2 || ppm_warn !== 1) bad = bad + 1;
    $display("RESULT: ppm_est=%0d (true %0d), disciplined read exact to 1 tick = %0d ns, %0d wrong",
             ppm_est, PPM, 1000000000/TPS, bad);
    if (bad) $fatal(1,"timestamp mismatch"); $finish;
  end
endmodule
