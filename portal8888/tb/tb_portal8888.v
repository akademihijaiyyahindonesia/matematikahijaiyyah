`timescale 1ns/1ps
// One round: feed A,B,C,D records, check TAG_A..D and the portal ROOT (head
// anchor) byte-exact against portal_ref.py.
module tb_portal8888;
  reg clk=0, rst_n=0; always #5 clk=~clk;
  reg rec_valid=0; reg [1:0] rec_port=0;
  reg [31:0] rec_tsec=0, rec_ttick=0; reg [127:0] rec_ip=0;
  reg [15:0] rec_sport=0, rec_dport=0; reg [7:0] rec_proto=0;
  reg [15:0] rec_idx=0, rec_pidx=0;
  wire busy, ready, round_done;
  reg [511:0] kA,kB,kC,kD,kP;
  wire [31:0] anc_round; wire [255:0] anc_root, tagA, tagB, tagC, tagD;
  hijaiyyah_portal8888 dut(.clk(clk),.rst_n(rst_n),.rec_valid(rec_valid),.rec_port(rec_port),
    .rec_tsec(rec_tsec),.rec_ttick(rec_ttick),.rec_ip(rec_ip),.rec_sport(rec_sport),
    .rec_dport(rec_dport),.rec_proto(rec_proto),.rec_idx(rec_idx),.rec_pidx(rec_pidx),
    .busy(busy),.ready(ready),.kA(kA),.kB(kB),.kC(kC),.kD(kD),.kP(kP),
    .anc_round(anc_round),.anc_root(anc_root),.tagA(tagA),.tagB(tagB),.tagC(tagC),.tagD(tagD),
    .round_done(round_done));

  integer fd, r, bad=0; reg [16*8:1] lbl; reg [3:0] pnum;
  reg [511:0] kv; reg [255:0] eTagA,eTagB,eTagC,eTagD,eRoot;
  reg [31:0] v_tsec[0:3], v_ttick[0:3]; reg [127:0] v_ip[0:3];
  reg [15:0] v_sport[0:3], v_dport[0:3], v_idx[0:3]; reg [7:0] v_proto[0:3];
  integer i, pp;
  task seal(input [1:0] p); begin
    @(negedge clk); while(!ready) @(negedge clk);
    rec_port<=p; rec_tsec<=v_tsec[p]; rec_ttick<=v_ttick[p]; rec_ip<=v_ip[p];
    rec_sport<=v_sport[p]; rec_dport<=v_dport[p]; rec_proto<=v_proto[p]; rec_idx<=v_idx[p];
    rec_valid<=1; @(negedge clk); rec_valid<=0;
    @(negedge clk); while(busy) @(negedge clk);
  end endtask

  initial begin
    fd=$fopen("build/portal_vec.txt","r");
    if (fd==0) $fatal(1,"run: python3 ref/portal_ref.py vec > build/portal_vec.txt");
    for (i=0;i<5;i=i+1) begin r=$fscanf(fd,"%s %h\n",lbl,kv);
      case(i) 0:kA=kv;1:kB=kv;2:kC=kv;3:kD=kv;4:kP=kv; endcase end
    for (i=0;i<4;i=i+1) begin
      r=$fscanf(fd,"%s %d %h %h %h %h %h %h %h\n",lbl,pp,v_tsec[i],v_ttick[i],v_ip[i],
                v_sport[i],v_dport[i],v_proto[i],v_idx[i]);
    end
    r=$fscanf(fd,"%s %h\n",lbl,rec_pidx);
    r=$fscanf(fd,"%s %h %h\n",lbl,pnum,eTagA);
    r=$fscanf(fd,"%s %h %h\n",lbl,pnum,eTagB);
    r=$fscanf(fd,"%s %h %h\n",lbl,pnum,eTagC);
    r=$fscanf(fd,"%s %h %h\n",lbl,pnum,eTagD);
    r=$fscanf(fd,"%s %h\n",lbl,eRoot);
    #22 rst_n=1;
    seal(0); seal(1); seal(2); seal(3);
    @(negedge clk); while(!round_done && anc_round==0) @(negedge clk);
    if (tagA!==eTagA) begin bad=bad+1; $display("TAG_A MISMATCH"); end
    if (tagB!==eTagB) begin bad=bad+1; $display("TAG_B MISMATCH"); end
    if (tagC!==eTagC) begin bad=bad+1; $display("TAG_C MISMATCH"); end
    if (tagD!==eTagD) begin bad=bad+1; $display("TAG_D MISMATCH"); end
    if (anc_root!==eRoot) begin bad=bad+1; $display("ROOT MISMATCH got=%h want=%h",anc_root,eRoot); end
    $display("portal8888: round=%0d  TAGs %s  ROOT %s  (%0d mismatch)",
             anc_round, (tagA===eTagA&&tagB===eTagB&&tagC===eTagC&&tagD===eTagD)?"OK":"BAD",
             (anc_root===eRoot)?"OK":"BAD", bad);
    if (bad) $fatal(1,"portal8888 mismatch"); $finish;
  end
endmodule
