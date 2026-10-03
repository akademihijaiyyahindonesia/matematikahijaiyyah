`timescale 1ns/1ps
module tb_jim;
  reg clk=0, rst_n=0; always #5 clk=~clk;
  reg bv=0, bi=0; wire hit; wire [4:0] ham;
  jim_sync #(.T(2)) s(.clk(clk),.rst_n(rst_n),.bit_valid(bv),.bit_in(bi),.hit(hit),.ham(ham));
  reg step=0; wire [2:0] d0,d1,d2,d3,d4;
  jim_index x(.clk(clk),.rst_n(rst_n),.step(step),.d0(d0),.d1(d1),.d2(d2),.d3(d3),.d4(d4));
  integer fb, fe, fi, r, n=0, i, want, got_hits=0, bad=0, k; reg b; reg [39:0] line; reg [2:0] e0,e1,e2,e3,e4;
  reg [8*5:1] s5;
  initial begin
    #22 rst_n=1;
    fb=$fopen("build/sync_bits.txt","r"); fe=$fopen("build/sync_expect.txt","r");
    if (fb==0 || fe==0) $fatal(1,"vector files missing: python3 ref/vectors.py build");
    r=$fscanf(fe,"%d\n",want);
    while (!$feof(fb)) begin
      r=$fscanf(fb,"%d\n",b); @(negedge clk); bv=1; bi=b; @(posedge clk); #1 bv=0;
      @(negedge clk);
      if (hit) begin got_hits=got_hits+1; if (n!=want) begin bad=bad+1; $display("hit at %0d, expected %0d",n,want); end
                     if (!$feof(fe)) r=$fscanf(fe,"%d\n",want); else want=-1; end
      n=n+1;
    end
    // an expected hit the correlator never raised is as wrong as a misplaced one;
    // want is -1 only once the last expected hit has been consumed
    if (want != -1) begin bad=bad+1; $display("missed hit, first expected at %0d", want); end
    $display("jim_sync: %0d bits, %0d hits, %0d wrong", n, got_hits, bad);
    fi=$fopen("build/idx_expect.txt","r");
    for (k=0;k<3124;k=k+1) begin
      r=$fscanf(fi,"%s\n",s5);
      e0=s5[40:33]-8'd48; e1=s5[32:25]-8'd48; e2=s5[24:17]-8'd48; e3=s5[16:9]-8'd48; e4=s5[8:1]-8'd48;
      if ({d0,d1,d2,d3,d4} !== {e0,e1,e2,e3,e4}) bad=bad+1;
      @(negedge clk); step=1; @(negedge clk); step=0;
    end
    $display("jim_index: back to start after 3124 steps: %0s", ({d0,d1,d2,d3,d4}==15'b001_000_000_000_000)?"YES":"NO");
    if ({d0,d1,d2,d3,d4} != 15'b001_000_000_000_000) bad=bad+1;
    $display("TOTAL wrong = %0d", bad);
    if (bad) $fatal(1,"jim mismatch"); $finish;
  end
endmodule
