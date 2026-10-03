`timescale 1ns/1ps
// V1 integration: provision -> permanent lock -> PHY SOF -> replayed SHA -> seal.
module tb_portal8888_v1;
  reg clk=0, rst_n=0; always #5 clk=~clk;
  reg pps=0, provision_time=0; reg [31:0] provision_utc_sec=0, provision_uncert_ns=0;
  reg [1:0] phy_port=0; reg phy_byte_valid=0; reg [7:0] phy_byte=0; reg phy_last=0;
  reg prov_valid=0, prov_lock=0; reg [2:0] prov_slot=0; reg [7:0] prov_byte=0; integer kb;
  wire provisioned, provision_locked, busy, ready, record_done, record_dropped, overflow_drop;
  wire [4:0] provision_written; wire [999:0] sealed_body; wire [255:0] sealed_tag;
  wire [31:0] anc_round; wire [255:0] anc_root,tagA,tagB,tagC,tagD;
  hijaiyyah_portal8888 dut(
    .clk(clk),.rst_n(rst_n),.pps(pps),.provision_time(provision_time),
    .provision_utc_sec(provision_utc_sec),.provision_uncert_ns(provision_uncert_ns),
    .phy_port(phy_port),.phy_byte_valid(phy_byte_valid),.phy_byte(phy_byte),.phy_last(phy_last),
    .prov_valid(prov_valid),.prov_slot(prov_slot),.prov_byte(prov_byte),.prov_lock(prov_lock),
    .provisioned(provisioned),.provision_locked(provision_locked),.provision_written(provision_written),
    .busy(busy),.ready(ready),.record_done(record_done),.record_dropped(record_dropped),.overflow_drop(overflow_drop),
    .sealed_body(sealed_body),.sealed_tag(sealed_tag),.anc_round(anc_round),.anc_root(anc_root),
    .tagA(tagA),.tagB(tagB),.tagC(tagC),.tagD(tagD));

  integer fd,r,i,n,bad=0,slot,kbad; reg [8*16:1] word;
  reg [511:0] keys[0:4]; reg [7:0] frame[0:9215];
  reg [63:0] dev; reg [31:0] etsec,ettick,euncert; reg [7:0] esource;
  reg [999:0] ebody; reg [255:0] etag, ehash;
  task write_key(input integer which, input [511:0] key); begin
    for(kb=0;kb<64;kb=kb+1) begin
      @(negedge clk); prov_slot<=which; prov_byte<=key[511-8*kb -: 8]; prov_valid<=1;
    end
    @(negedge clk); prov_valid<=0;
  end endtask
  task send_frame; begin
    for(i=0;i<n;i=i+1) begin
      @(negedge clk); phy_port<=2; phy_byte<=frame[i]; phy_byte_valid<=1; phy_last<=(i==n-1);
    end
    @(negedge clk); phy_byte_valid<=0; phy_last<=0;
  end endtask
  initial begin
    fd=$fopen("build/portal_v1.txt","r"); if(fd==0) $fatal(1,"run portal_ref.py vec build");
    for(i=0;i<5;i=i+1) begin r=$fscanf(fd,"%s %d %h\n",word,slot,keys[i]); end
    r=$fscanf(fd,"%s %h\n",word,dev);
    r=$fscanf(fd,"%s %h %h %h %h\n",word,etsec,ettick,esource,euncert);
    r=$fscanf(fd,"%s %h\n",word,ebody); r=$fscanf(fd,"%s %h\n",word,etag); r=$fscanf(fd,"%s %h\n",word,ehash);
    fd=$fopen("build/portal_frame.txt","r"); r=$fscanf(fd,"%d\n",n);
    if(n!=9216) $fatal(1,"vector is not a 9216-byte jumbo frame");
    for(i=0;i<n;i=i+1) r=$fscanf(fd,"%h\n",frame[i]);
    #22 rst_n=1;
    for(i=0;i<5;i=i+1) write_key(i,keys[i]);
    @(negedge clk); prov_lock<=1; @(negedge clk); prov_lock<=0;
    if(!provisioned || !provision_locked || provision_written!==5'b11111) begin bad=bad+1; $display("provisioning did not lock five slots"); end
    // R3: a post-lock overwrite must not alter the port-2 sealing key.
    write_key(2,{512{1'b1}});
    kbad=0; for(kb=0;kb<64;kb=kb+1) if(dut.key_mem[{3'd2,kb[5:0]}]!==keys[2][511-8*kb -: 8]) kbad=kbad+1;
    if(kbad!=0) begin bad=bad+1; $display("post-lock key overwrite accepted"); end
    else $display("R3 key overwrite after lock: detected");
    @(negedge clk); provision_utc_sec<=etsec; provision_uncert_ns<=euncert; provision_time<=1;
    @(negedge clk); provision_time<=0;
    send_frame;
    while(!record_done) @(negedge clk);
    if(sealed_body!==ebody) begin
      bad=bad+1;
      $display("BODY MISMATCH time got=%h/%h/%h/%h want=%h/%h/%h/%h", sealed_body[927:896],sealed_body[895:864],sealed_body[863:856],sealed_body[855:824], ebody[927:896],ebody[895:864],ebody[863:856],ebody[855:824]);
      $display("BODY MISMATCH obs got=%h/%h/%h/%h hash=%h", sealed_body[759:752],sealed_body[751:744],sealed_body[743:616],sealed_body[615:568],sealed_body[527:272]);
    end
    if(sealed_tag!==etag) begin bad=bad+1; $display("TAG MISMATCH"); end
    if(sealed_body[527:272]!==ehash) begin bad=bad+1; $display("FRAME_HASH MISMATCH"); end
    if(record_dropped || overflow_drop) begin bad=bad+1; $display("valid jumbo frame was dropped"); end
    $display("portal8888 v1: frame=%0d body=%0d tag=%s lock=%s (%0d wrong)",n,125,
             (sealed_tag===etag)?"OK":"BAD",(provisioned&&provision_locked)?"OK":"BAD",bad);
    if(bad) $fatal(1,"Portal v1 mismatch"); $finish;
  end
endmodule
