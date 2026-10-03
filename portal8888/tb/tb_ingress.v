`timescale 1ns/1ps
module tb_ingress;
  reg clk=0, rst_n=0; always #5 clk=~clk;
  reg bv=0, last=0; reg [7:0] bi=0;
  wire done; wire [1:0] status; wire [3:0] ver; wire [127:0] src_ip; wire [15:0] sport, dport; wire [7:0] proto; wire [47:0] src_mac;
  ingress_parse dut(.clk(clk),.rst_n(rst_n),.byte_valid(bv),.byte_in(bi),.last(last),.done(done),.status(status),
    .ver(ver),.src_ip(src_ip),.sport(sport),.dport(dport),.proto(proto),.src_mac(src_mac));
  integer ff, fe, r, nfr, k, len, i, bad=0, good=0; reg [7:0] mem [0:2047];
  integer est, ever; reg [127:0] eip; reg [15:0] esp, edp; reg [7:0] epr; reg [47:0] emac;
  initial begin
    #22 rst_n=1;
    ff=$fopen("build/frames.txt","r"); fe=$fopen("build/expect.txt","r");
    if (ff==0 || fe==0) $fatal(1,"vector files missing: python3 ref/vectors.py build");
    r=$fscanf(ff,"%d\n",nfr);
    for (k=0;k<nfr;k=k+1) begin
      r=$fscanf(ff,"%d\n",len); for (i=0;i<len;i=i+1) r=$fscanf(ff,"%h\n",mem[i]);
      r=$fscanf(fe,"%d %d %h %h %h %h %h\n",est,ever,eip,esp,edp,epr,emac);
      for (i=0;i<len;i=i+1) begin @(negedge clk); bv=1; bi=mem[i]; last=(i==len-1); end
      @(negedge clk); bv=0; last=0;
      while(!done) @(negedge clk);
      if (status==est && ver==ever && src_ip==eip && sport==esp && dport==edp && proto==epr && src_mac==emac) good=good+1;
      else begin bad=bad+1; if (bad<6) $display("frame %0d: got st=%0d v=%0d ip=%h sp=%h dp=%h pr=%h mac=%h | want st=%0d v=%0d ip=%h sp=%h dp=%h pr=%h mac=%h",
        k,status,ver,src_ip,sport,dport,proto,src_mac,est,ever,eip,esp,edp,epr,emac); end
    end
    $display("ingress_parse: %0d frames, %0d exact, %0d wrong", nfr, good, bad);
    if (bad) $fatal(1,"mismatch"); $finish;
  end
endmodule
