`timescale 1ns/1ps
// Two jumbo frames with no idle PHY cycle between them.
module tb_ingress_v1;
  reg clk=0,rst_n=0; always #5 clk=~clk;
  reg bv=0,last=0; reg [7:0] bi=0;
  wire done; wire [1:0] status; wire [3:0] ver; wire [127:0] ip;
  wire [15:0] sport,dport; wire [7:0] proto; wire [47:0] mac;
  ingress_parse_v1 dut(.clk(clk),.rst_n(rst_n),.byte_valid(bv),.byte_in(bi),.last(last),.done(done),.status(status),.ver(ver),.src_ip(ip),.sport(sport),.dport(dport),.proto(proto),.src_mac(mac));
  integer fd,r,n,i,frame,seen=0,bad=0; reg [7:0] mem[0:9215];
  task check_done; begin
    if(done) begin
      seen=seen+1;
      if(status!==0 || ver!==4 || ip!==128'h00000000000000000000ffffcb007163 || sport!==16'ha028 || dport!==16'h22b8 || proto!==17 || mac!==48'h001122334455) bad=bad+1;
    end
  end endtask
  initial begin
    fd=$fopen("build/portal_frame.txt","r"); if(fd==0) $fatal(1,"missing v1 frame");
    r=$fscanf(fd,"%d\n",n); if(n!=9216) $fatal(1,"not jumbo");
    for(i=0;i<n;i=i+1) r=$fscanf(fd,"%h\n",mem[i]);
    #22 rst_n=1;
    for(frame=0;frame<2;frame=frame+1) for(i=0;i<n;i=i+1) begin
      @(negedge clk); check_done; bv=1; bi=mem[i]; last=(i==n-1);
    end
    @(negedge clk); check_done; bv=0; last=0;
    $display("ingress_parse_v1: 2 contiguous jumbo frames, %0d done, %0d wrong",seen,bad);
    if(seen!=2 || bad) $fatal(1,"continuous jumbo mismatch"); $finish;
  end
endmodule
